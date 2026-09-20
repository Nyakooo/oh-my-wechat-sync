#!/usr/bin/env python3
"""Run the repository-local P0 preflight without touching WeChat runtime data."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from .report_import_package import build_report
    from .validate_import_package import ValidationError
except ImportError:  # pragma: no cover - used when invoked as a script
    from report_import_package import build_report
    from validate_import_package import ValidationError


REQUIRED_DOCS = (
    "docs/p0-feasibility-report.md",
    "docs/p0-route-assessment.md",
    "docs/p0-import-package-draft.md",
    "docs/p0-external-sample-intake.md",
    "docs/p0-route-decision-template.md",
    "docs/p0-evidence-index.md",
)


def check(name: str, status: str, detail: str) -> dict[str, str]:
    return {"name": name, "status": status, "detail": detail}


def build_preflight(repo_root: Path, sample_path: Path | None = None, run_tests: bool = True) -> dict[str, Any]:
    checks: list[dict[str, str]] = []

    missing_docs = [path for path in REQUIRED_DOCS if not (repo_root / path).is_file()]
    if missing_docs:
        checks.append(check("required_docs", "failed", "missing: " + ", ".join(missing_docs)))
    else:
        checks.append(check("required_docs", "passed", f"{len(REQUIRED_DOCS)} P0 documents present"))

    fixture = repo_root / "tests" / "fixtures" / "import-v0-minimal"
    try:
        fixture_report = build_report(fixture)
    except (ValidationError, OSError, KeyError) as exc:
        checks.append(check("synthetic_fixture", "failed", str(exc)))
        fixture_report = None
    else:
        checks.append(
            check(
                "synthetic_fixture",
                "passed",
                f"{fixture_report['records']['messages.ndjson']} message and {fixture_report['media']['attachment_count']} attachment records",
            )
        )

    if sample_path is None:
        checks.append(check("external_sample", "blocked", "no Windows Agent export or real redacted import sample supplied"))
    else:
        try:
            sample_report = build_report(sample_path)
        except (ValidationError, OSError, KeyError) as exc:
            checks.append(check("external_sample", "failed", str(exc)))
        else:
            checks.append(check("external_sample", "passed", "supplied sample passed read-only validation"))
            fixture_report = fixture_report or {}
            fixture_report["external_sample"] = sample_report

    if run_tests:
        result = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            checks.append(check("automated_tests", "passed", "unittest discovery completed successfully"))
        else:
            checks.append(check("automated_tests", "failed", f"unittest exited with code {result.returncode}"))

    # A human review is intentionally required even when a sample is supplied.
    checks.append(check("p0_manual_review", "blocked", "P0-02 and P0-06..P0-12 evidence still require human review"))
    statuses = {item["status"] for item in checks}
    overall = "failed" if "failed" in statuses else "blocked" if "blocked" in statuses else "passed"
    return {
        "status": overall,
        "phase1_allowed": False,
        "checks": checks,
        "synthetic_fixture_report": fixture_report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--sample", type=Path, help="optional external redacted import package")
    parser.add_argument("--skip-tests", action="store_true", help="skip unittest discovery")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    args = parser.parse_args()
    report = build_preflight(args.repo_root.resolve(), args.sample.resolve() if args.sample else None, not args.skip_tests)
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
