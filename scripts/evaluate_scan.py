"""Run ContextGuard against a small, controlled vulnerability benchmark."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "scan_benchmark"

CASES = {
    "path_traversal": {
        "query": (
            "path traversal user-controlled filename escaping "
            "DATA_DIR directory"
        ),
        "expect_vulnerability": True,
        "keywords": ("path traversal", "directory traversal"),
    },
    "command_injection": {
        "query": (
            "command injection shell=True user-controlled query "
            "subprocess command execution"
        ),
        "expect_vulnerability": True,
        "keywords": ("command injection", "shell injection"),
    },
    "unsafe_deserialization": {
        "query": (
            "unsafe deserialization pickle.loads untrusted bytes "
            "arbitrary code execution"
        ),
        "expect_vulnerability": True,
        "keywords": ("deserialization", "pickle"),
    },
    "safe_control": {
        "query": (
            "path validation subprocess shell injection "
            "unsafe deserialization pickle json"
        ),
        "expect_vulnerability": False,
        "keywords": (),
    },
}



def score_findings(findings: list[dict], settings: dict) -> dict:
    """Score detection and penalize unexpected actionable findings."""
    actionable = [item for item in findings if item.get("actionable") is True]
    uncertain = [item for item in findings if item.get("status") == "uncertain"]

    if settings["expect_vulnerability"]:
        relevant_actionable = [
            item for item in actionable
            if any(
                keyword in (
                    str(item.get("title", ""))
                    + " "
                    + str(item.get("description", ""))
                ).lower()
                for keyword in settings["keywords"]
            )
        ]
        unexpected_actionable = [
            item for item in actionable if item not in relevant_actionable
        ]
        passed = bool(relevant_actionable) and not unexpected_actionable
    else:
        relevant_actionable = []
        unexpected_actionable = actionable
        passed = not actionable

    return {
        "passed": passed,
        "findings_returned": len(findings),
        "actionable_findings": len(actionable),
        "uncertain_findings": len(uncertain),
        "expected_issue_detected": bool(relevant_actionable),
        "unexpected_actionable_findings": [
            {
                "title": item.get("title", ""),
                "file_path": item.get("file_path", ""),
            }
            for item in unexpected_actionable
        ],
    }


def evaluate_case(name: str, settings: dict) -> dict:
    """Run one scan and compare its result with the fixture expectation."""
    repository = FIXTURES / name
    if not repository.is_dir():
        return {
            "case": name,
            "passed": False,
            "error": f"Fixture directory not found: {repository}",
        }

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(ROOT / "src")
        + (os.pathsep + existing_pythonpath if existing_pythonpath else "")
    )

    command = [
        sys.executable,
        "-m",
        "contextguard.cli",
        "scan",
        "--repository",
        str(repository),
        "--query",
        settings["query"],
        "--top-k",
        "5",
        "--window",
        "4",
        "--max-characters",
        "8000",
    ]

    try:
        process = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "case": name,
            "passed": False,
            "error": str(exc),
        }

    if process.returncode != 0:
        return {
            "case": name,
            "passed": False,
            "error": process.stderr.strip()
            or f"Scan exited with code {process.returncode}",
        }

    try:
        output = json.loads(process.stdout)
    except json.JSONDecodeError:
        return {
            "case": name,
            "passed": False,
            "error": "Scan did not return valid JSON.",
        }

    findings = output.get("findings", [])
    scoring = score_findings(findings, settings)

    return {
        "case": name,
        "expected_vulnerability": settings["expect_vulnerability"],
        **scoring,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate ContextGuard using controlled local fixtures."
    )
    parser.add_argument(
        "--case",
        choices=(*CASES.keys(), "all"),
        default="all",
        help="Choose one fixture or run the full benchmark.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available cases without making API requests.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optionally write the JSON report to a file.",
    )
    args = parser.parse_args()

    if args.list:
        print("Available benchmark cases:")
        for name, settings in CASES.items():
            expected = (
                "vulnerability expected"
                if settings["expect_vulnerability"]
                else "safe control; no actionable finding expected"
            )
            print(f"  {name}: {expected}")
        return 0

    selected = (
        list(CASES.items())
        if args.case == "all"
        else [(args.case, CASES[args.case])]
    )

    results = [evaluate_case(name, settings) for name, settings in selected]
    report = {
        "benchmark": "ContextGuard controlled scan fixtures",
        "cases_run": len(results),
        "cases_passed": sum(result["passed"] for result in results),
        "cases_failed": sum(not result["passed"] for result in results),
        "results": results,
    }

    rendered = json.dumps(report, indent=2)
    print(rendered)

    if args.output:
        destination = args.output.expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered + "\n", encoding="utf-8")
        print(f"\nReport saved to: {destination}", file=sys.stderr)

    return 0 if report["cases_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
