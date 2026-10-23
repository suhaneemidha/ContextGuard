"""Command-line interface for ContextGuard review workflows."""

import argparse
import json
import sys
from pathlib import Path

from contextguard.llm import generate_review_response
from contextguard.repository_source import open_repository
from contextguard.review_workflow import (
    prepare_review_request,
    process_review_response,
)
from contextguard.schemas import ReviewFinding


def _add_finding_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments shared by review commands."""
    parser.add_argument("--title", required=True, help="Candidate finding title")
    parser.add_argument(
        "--description",
        required=True,
        help="Description of the suspected issue",
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Repository-relative file path",
    )
    parser.add_argument(
        "--line",
        type=int,
        default=None,
        help="Suspected issue line number",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.0,
        help="Initial reported confidence, from 0.0 to 1.0",
    )


def _make_finding(args: argparse.Namespace) -> ReviewFinding:
    """Build a finding after validating CLI inputs."""
    if args.line is not None and args.line < 1:
        raise ValueError("--line must be at least 1")

    if not 0.0 <= args.confidence <= 1.0:
        raise ValueError("--confidence must be between 0.0 and 1.0")

    return ReviewFinding(
        title=args.title,
        description=args.description,
        file_path=args.file,
        line_number=args.line,
        confidence=args.confidence,
    )


def _add_context_arguments(parser: argparse.ArgumentParser) -> None:
    """Add options controlling retrieved repository context."""
    parser.add_argument("--query", help="Optional context-retrieval query")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--window", type=int, default=3)
    parser.add_argument("--max-characters", type=int, default=8000)


def _print_result(result) -> None:
    """Print a verification result as JSON."""
    output = {
        "status": result.status.value,
        "actionable": result.is_actionable(),
        "reason": result.reason,
        "finding": {
            "title": result.finding.title,
            "file_path": result.finding.file_path,
            "confidence": result.finding.confidence,
        },
        "evidence_references": [
            {
                "file_path": reference.file_path,
                "start_line": reference.start_line,
                "end_line": reference.end_line,
                "excerpt": reference.excerpt,
                "explanation": reference.explanation,
            }
            for reference in result.evidence_references
        ],
    }
    print(json.dumps(output, indent=2))


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="contextguard",
        description="Prepare and verify repository-grounded code reviews.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    prepare_parser = commands.add_parser(
        "prepare",
        help="Build a review prompt using repository context",
    )
    prepare_parser.add_argument(
        "--repository",
        required=True,
        help="Local repository path or public HTTPS GitHub URL",
    )
    _add_context_arguments(prepare_parser)
    _add_finding_arguments(prepare_parser)

    verify_parser = commands.add_parser(
        "verify",
        help="Validate a saved model response against repository source",
    )
    verify_parser.add_argument(
        "--repository",
        required=True,
        help="Local repository path or public HTTPS GitHub URL",
    )
    verify_parser.add_argument(
        "--response-file",
        required=True,
        help="Path to a JSON file containing the model response",
    )
    _add_finding_arguments(verify_parser)

    review_parser = commands.add_parser(
        "review",
        help="Generate an AI review and verify its source evidence",
    )
    review_parser.add_argument(
        "--repository",
        required=True,
        help="Local repository path or public HTTPS GitHub URL",
    )
    review_parser.add_argument(
        "--model",
        help="Groq model name (defaults to GROQ_MODEL or the configured default)",
    )
    _add_context_arguments(review_parser)
    _add_finding_arguments(review_parser)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run a ContextGuard CLI command."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        finding = _make_finding(args)

        with open_repository(args.repository) as repository_root:
            if args.command in {"prepare", "review"}:
                request = prepare_review_request(
                    repository_root=repository_root,
                    finding=finding,
                    query=args.query,
                    top_k=args.top_k,
                    window=args.window,
                    max_characters=args.max_characters,
                )

                if args.command == "prepare":
                    print(request.prompt)
                    return 0

                # This is the only CLI path that calls the external LLM.
                raw_response = generate_review_response(
                    request.prompt,
                    model=args.model,
                )
            else:
                response_path = Path(args.response_file)
                raw_response = response_path.read_text(encoding="utf-8")

            result = process_review_response(
                repository_root=repository_root,
                finding=finding,
                raw_response=raw_response,
            )
            _print_result(result)
            return 0

    except (OSError, ValueError, RuntimeError) as exc:
        print(f"contextguard: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
