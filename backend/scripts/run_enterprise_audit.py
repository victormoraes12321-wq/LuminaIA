from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.enterprise_audit_engine import run_enterprise_audit  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the LuminaAI deterministic enterprise audit.")
    parser.add_argument(
        "--output-dir",
        default=str(BACKEND_ROOT / "reports"),
        help="Directory where JSON and Markdown audit reports will be written.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a compact JSON execution summary to stdout.",
    )
    args = parser.parse_args()

    report, paths = run_enterprise_audit(output_dir=args.output_dir)
    summary = {
        "audit_version": report.audit_version,
        "status": report.certification["certification_status"],
        "score": report.score_panel["Score Geral da Plataforma LuminaAI"],
        "evidence_objects": report.executive_summary["evidence_objects"],
        "critical_path_coverage_percent": report.coverage_matrix["critical_path_coverage_percent"],
        "ivr_consolidado_percent": report.repeatability["ivr_consolidado_percent"],
        "reports": paths,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("LuminaAI enterprise audit completed.")
        print(f"Status: {summary['status']}")
        print(f"Score: {summary['score']}")
        print(f"Evidence objects: {summary['evidence_objects']}")
        print(f"Critical path coverage: {summary['critical_path_coverage_percent']}%")
        print(f"IVR: {summary['ivr_consolidado_percent']}%")
        print(f"JSON report: {paths['json']}")
        print(f"Markdown report: {paths['markdown']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
