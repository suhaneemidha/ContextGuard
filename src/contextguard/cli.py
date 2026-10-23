"""Command-line interface for ContextGuard review workflows."""

import argparse
import json
import sys
from pathlib import Path

from contextguard.engine import DEFAULT_CONFIDENCE_THRESHOLD, verify_finding
from contextguard.llm import generate_review_response, generate_scan_response
from contextguard.repository_source import open_repository
from contextguard.review_context import build_review_context
from contextguard.review_prompt import build_review_prompt
from contextguard.review_workflow import (
    prepare_review_request,
    process_review_response,
)
from contextguard.scan_prompt import build_scan_prompt
from contextguard.scan_response import parse_scan_response
from contextguard.schemas import ReviewFinding


DEFAULT_SCAN_QUERY = (
    "bug defect security correctness error handling authorization "
    "validation edge case"
)


def _add_finding_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments shared by individual-finding commands."""
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
    parser.add_argument("--line", type=int, default=None)
    parser.add_argument("--confidence", type=float, default=0.0)


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


def _add_model_argument(parser: argparse.ArgumentParser) -> None:
    """Add options for the optional LLM provider."""
    parser.add_argument("--model", help="Groq model name")
    parser.add_argument(
        "--debug-response",
        action="store_true",
        help="Print raw model JSON to stderr for troubleshooting",
    )


def _reference_dict(reference) -> dict:
    """Convert a validated evidence reference to JSON-compatible data."""
    return {
        "file_path": reference.file_path,
        "start_line": reference.start_line,
        "end_line": reference.end_line,
        "excerpt": reference.excerpt,
        "explanation": reference.explanation,
    }


def _print_result(result) -> None:
    """Print an individual-finding verification result as JSON."""
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
            _reference_dict(reference)
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
    _add_model_argument(review_parser)
    _add_context_arguments(review_parser)
    _add_finding_arguments(review_parser)

    scan_parser = commands.add_parser(
        "scan",
        help="Discover potential bugs in a repository automatically",
    )
    scan_parser.add_argument(
        "--repository",
        required=True,
        help="Local repository path or public HTTPS GitHub URL",
    )
    _add_model_argument(scan_parser)
    scan_parser.add_argument("--query", help="Optional retrieval query")
    scan_parser.add_argument("--top-k", type=int, default=20)
    scan_parser.add_argument("--window", type=int, default=2)
    scan_parser.add_argument("--max-characters", type=int, default=16000)
    scan_parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=DEFAULT_CONFIDENCE_THRESHOLD,
        help="Minimum confidence for actionable findings (0.0 to 1.0)",
    )

    return parser


def _run_scan(args: argparse.Namespace, repository_root: Path) -> int:
    """Generate candidate findings and validate their source evidence."""
    if not 0.0 <= args.confidence_threshold <= 1.0:
        raise ValueError("--confidence-threshold must be between 0.0 and 1.0")

    context = build_review_context(
        repository_root=repository_root,
        query=args.query or DEFAULT_SCAN_QUERY,
        top_k=args.top_k,
        window=args.window,
        max_characters=args.max_characters,
    )

    if not context.text.strip():
        raise ValueError(
            "No relevant source context was retrieved. Try another --query "
            "or increase --top-k."
        )

    prompt = build_scan_prompt(context)
    raw_response = generate_scan_response(prompt, model=args.model)

    if args.debug_response:
        print("Raw Groq scan response:", file=sys.stderr)
        print(raw_response, file=sys.stderr)

    parsed = parse_scan_response(raw_response)
    results = []

    for scanned_finding in parsed.findings:
        finding = ReviewFinding(
            title=scanned_finding.title,
            description=scanned_finding.description,
            file_path=scanned_finding.file_path,
            line_number=scanned_finding.line_number,
            confidence=scanned_finding.confidence,
        )

        verification = verify_finding(
            finding=finding,
            confidence_threshold=args.confidence_threshold,
            evidence_references=list(scanned_finding.evidence_references),
            repository_root=repository_root,
        )

        results.append(
            {
                "title": finding.title,
                "description": finding.description,
                "file_path": finding.file_path,
                "line_number": finding.line_number,
                "confidence": finding.confidence,
                "status": verification.status.value,
                "actionable": verification.is_actionable(),
                "reason": verification.reason,
                "evidence_references": [
                    _reference_dict(reference)
                    for reference in verification.evidence_references
                ],
            }
        )

    actionable_count = sum(item["actionable"] for item in results)

    print(
        json.dumps(
            {
                "repository": str(args.repository),
                "summary": {
                    "findings_returned": len(results),
                    "actionable_findings": actionable_count,
                    "uncertain_findings": len(results) - actionable_count,
                },
                "findings": results,
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run a ContextGuard CLI command."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "scan":
            with open_repository(args.repository) as repository_root:
                return _run_scan(args, repository_root)

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

                raw_response = generate_review_response(
                    request.prompt,
                    model=args.model,
                )
                if args.debug_response:
                    print("Raw Groq response:", file=sys.stderr)
                    print(raw_response, file=sys.stderr)
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
