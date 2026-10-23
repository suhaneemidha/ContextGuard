"""Build broad, file-diverse context for automatic repository scans."""

import ast
import re
from pathlib import Path, PurePosixPath

from contextguard.context import ContextSnippet, RepositoryFile
from contextguard.context_builder import AssembledContext, assemble_context
from contextguard.repository import load_repository
from contextguard.retrieval import expand_context, retrieve_context


SOURCE_SUFFIXES = {
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx",
    ".go", ".java", ".rs", ".rb", ".php", ".c", ".h",
    ".cpp", ".cc", ".cxx", ".cs", ".swift", ".kt",
    ".scala", ".sh", ".sql", ".vue",
}

RISKY_OPERATION = re.compile(
    r"\b(open|exec|eval|compile|read_text|write_text|"
    r"subprocess|execute|fetch|requests|unlink)\b",
    re.IGNORECASE,
)

CONTROL_STATEMENTS = (
    ast.If,
    ast.Try,
    ast.With,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Raise,
    ast.Assert,
)

ASSIGNMENT_STATEMENTS = (
    ast.Assign,
    ast.AnnAssign,
    ast.AugAssign,
)


def _is_test_file(file_path: str) -> bool:
    """Identify test files that should not dominate initial bug discovery."""
    path = PurePosixPath(file_path)
    parts = {part.lower() for part in path.parts[:-1]}
    name = path.name.lower()

    return (
        bool(parts & {"test", "tests"})
        or name.startswith("test_")
        or name.endswith("_test.py")
    )


def _fallback_line(file: RepositoryFile) -> int | None:
    """Choose a representative code line when lexical retrieval has no match."""
    lines = file.content.splitlines()

    if file.path.lower().endswith(".py"):
        try:
            tree = ast.parse(file.content)
        except SyntaxError:
            tree = None

        if tree is not None:
            candidates: list[tuple[int, int]] = []

            for node in ast.walk(tree):
                line_number = getattr(node, "lineno", None)
                if not isinstance(line_number, int) or line_number < 1:
                    continue

                if isinstance(node, CONTROL_STATEMENTS):
                    priority = 0
                elif isinstance(node, (ast.Return, ast.Await, ast.Yield)):
                    priority = 1
                elif isinstance(node, ASSIGNMENT_STATEMENTS):
                    priority = 2
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    priority = 4
                elif isinstance(node, ast.Expr) and not (
                    isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)
                ):
                    priority = 2
                else:
                    continue

                source_line = lines[line_number - 1].strip()
                if RISKY_OPERATION.search(source_line):
                    priority = -1

                candidates.append((priority, line_number))

            if candidates:
                return min(candidates)[1]

    # Lightweight fallback for non-Python source files or unparseable Python.
    candidates = []
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("#", "//", "/*", "*", "<!--")):
            continue
        if stripped.startswith(("import ", "from ")):
            continue

        if RISKY_OPERATION.search(stripped):
            priority = 0
        elif re.match(
            r"^(if|else|elif|try|catch|except|throw|raise|return|"
            r"for|while|with|await|function|def|class)\b",
            stripped,
            re.IGNORECASE,
        ):
            priority = 1
        elif "=" in stripped or "(" in stripped:
            priority = 2
        else:
            priority = 3

        candidates.append((priority, index))

    return min(candidates)[1] if candidates else None


def _fallback_snippet(file: RepositoryFile) -> ContextSnippet | None:
    """Create a one-line seed from a file not matched by the scan query."""
    line_number = _fallback_line(file)
    if line_number is None:
        return None

    lines = file.content.splitlines()
    return ContextSnippet(
        file_path=file.path,
        content=lines[line_number - 1],
        start_line=line_number,
        end_line=line_number,
        relevance_score=0.0,
    )



def _expand_to_code_block(
    snippet: ContextSnippet,
    file: RepositoryFile,
    files: list[RepositoryFile],
    window: int,
) -> ContextSnippet:
    """Include a complete code block and relevant module-level dependencies."""
    if file.path.lower().endswith(".py"):
        try:
            tree = ast.parse(file.content)
        except SyntaxError:
            tree = None

        if tree is not None:
            lines = file.content.splitlines()
            enclosing = []

            for node in ast.walk(tree):
                if not isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    continue

                start_line = min(
                    [node.lineno]
                    + [
                        decorator.lineno
                        for decorator in getattr(node, "decorator_list", [])
                    ]
                )
                end_line = getattr(node, "end_lineno", node.lineno)

                if start_line <= snippet.start_line <= end_line:
                    enclosing.append(
                        (end_line - start_line, start_line, end_line, node)
                    )

            if enclosing:
                _, start_line, end_line, target_node = min(
                    enclosing, key=lambda item: item[:3]
                )

                referenced_names = {
                    node.id
                    for node in ast.walk(target_node)
                    if isinstance(node, ast.Name)
                    and isinstance(node.ctx, ast.Load)
                }

                module_dependencies = []
                for statement in tree.body:
                    defined_names = set()

                    if isinstance(
                        statement, (ast.Assign, ast.AnnAssign, ast.AugAssign)
                    ):
                        targets = (
                            statement.targets
                            if isinstance(statement, ast.Assign)
                            else [statement.target]
                        )
                        defined_names.update(
                            target.id
                            for target in targets
                            for target in ast.walk(target)
                            if isinstance(target, ast.Name)
                        )
                    elif isinstance(statement, ast.Import):
                        defined_names.update(
                            alias.asname or alias.name.split(".")[0]
                            for alias in statement.names
                        )
                    elif isinstance(statement, ast.ImportFrom):
                        defined_names.update(
                            alias.asname or alias.name
                            for alias in statement.names
                        )
                    else:
                        continue

                    loaded_names = {
                        node.id
                        for node in ast.walk(statement)
                        if isinstance(node, ast.Name)
                        and isinstance(node.ctx, ast.Load)
                    }
                    module_dependencies.append(
                        (
                            statement,
                            defined_names,
                            loaded_names,
                        )
                    )

                dependency_spans = []
                included_statements = set()
                changed = True

                while changed:
                    changed = False
                    for statement, defined_names, loaded_names in module_dependencies:
                        if (
                            statement.lineno in included_statements
                            or not defined_names.intersection(referenced_names)
                        ):
                            continue

                        included_statements.add(statement.lineno)
                        dependency_spans.append(
                            (
                                statement.lineno,
                                getattr(statement, "end_lineno", statement.lineno),
                            )
                        )
                        previous_count = len(referenced_names)
                        referenced_names.update(loaded_names)
                        if len(referenced_names) > previous_count:
                            changed = True

                if dependency_spans:
                    start_line = min(
                        [start_line]
                        + [span[0] for span in dependency_spans]
                    )
                    end_line = max(
                        [end_line]
                        + [span[1] for span in dependency_spans]
                    )

                content = "\n".join(lines[start_line - 1:end_line])

                # Keep context bounded even when dependencies are far apart.
                if len(content) <= 5000:
                    return ContextSnippet(
                        file_path=file.path,
                        content=content,
                        start_line=start_line,
                        end_line=end_line,
                        relevance_score=snippet.relevance_score,
                    )

    return expand_context(snippet, files, window=window)

def _fallback_file_key(file: RepositoryFile) -> tuple[int, int, str]:
    """Prioritize source code and conventional source directories."""
    path = PurePosixPath(file.path)
    source_priority = 0 if path.suffix.lower() in SOURCE_SUFFIXES else 1
    directory_priority = (
        0 if path.parts and path.parts[0].lower() in {"src", "lib", "app", "packages"}
        else 1
    )
    return source_priority, directory_priority, file.path


def build_scan_context(
    repository_root: str | Path,
    query: str,
    top_k: int = 20,
    window: int = 2,
    max_characters: int = 16000,
) -> AssembledContext:
    """Retrieve relevant snippets, then fill coverage gaps across source files."""
    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    if window < 0:
        raise ValueError("window must be non-negative")

    if not query.strip():
        return assemble_context([], max_characters=max_characters)

    files = [
        file
        for file in load_repository(repository_root)
        if not _is_test_file(file.path)
    ]

    total_nonblank_lines = sum(
        1
        for file in files
        for line in file.content.splitlines()
        if line.strip()
    )

    if total_nonblank_lines == 0:
        return assemble_context([], max_characters=max_characters)

    candidates = retrieve_context(
        query=query,
        files=files,
        top_k=total_nonblank_lines,
    )

    # Preserve file ranking, but choose a representative implementation line
    # instead of an import or other high-scoring line outside a function.
    selected: list[ContextSnippet] = []
    selected_paths: set[str] = set()
    files_by_path = {file.path: file for file in files}

    for candidate in candidates:
        if candidate.file_path in selected_paths:
            continue

        source_file = files_by_path[candidate.file_path]
        representative = _fallback_snippet(source_file)

        if representative is not None:
            candidate = ContextSnippet(
                file_path=representative.file_path,
                content=representative.content,
                start_line=representative.start_line,
                end_line=representative.end_line,
                relevance_score=candidate.relevance_score,
            )

        selected.append(candidate)
        selected_paths.add(candidate.file_path)

        if len(selected) >= top_k:
            break

    # Fill remaining slots with representative source from unmatched files.
    # This prevents a keyword-heavy prompt or test fixture from monopolizing
    # the scan context when other implementation files have no query matches.
    if len(selected) < top_k:
        remaining_files = sorted(
            (file for file in files if file.path not in selected_paths),
            key=_fallback_file_key,
        )

        for file in remaining_files:
            snippet = _fallback_snippet(file)
            if snippet is None:
                continue

            selected.append(snippet)
            selected_paths.add(file.path)

            if len(selected) >= top_k:
                break

    files_by_path = {file.path: file for file in files}
    expanded = [
        _expand_to_code_block(
            snippet,
            files_by_path[snippet.file_path],
            files,
            window,
        )
        for snippet in selected
    ]

    return assemble_context(
        expanded,
        max_characters=max_characters,
    )
