"""
Run comprehensive data audit including PII scan and volume estimation.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from audit.pii_scanner import PIIScanner
from audit.volume_estimator import VolumeEstimator
import json
import structlog

logger = structlog.get_logger()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)


def run_pii_scan():
    """Run PII scan on sample data."""
    print("\n" + "=" * 60)
    print("PII SCAN")
    print("=" * 60)

    scanner = PIIScanner(anonymize=True)
    sample_files = [
        "sample_slack_messages.json",
        "sample_notion_pages.json",
        "sample_drive_docs.json"
    ]

    all_results = []
    all_passed = True

    for file_path in sample_files:
        if not Path(file_path).exists():
            print(f"\n⚠️  {file_path} not found - skipping")
            continue

        print(f"\n📄 Scanning {file_path}...")
        result = scanner.scan_json_file(file_path)

        print(f"   Items scanned: {result.total_items_scanned}")
        print(f"   PII matches found: {result.pii_matches_found}")
        print(f"   Critical matches: {len(result.critical_matches)}")
        print(f"   Status: {'✅ PASSED' if result.passed else '❌ FAILED'}")

        if result.pii_types_detected:
            print(f"   PII types: {', '.join(result.pii_types_detected)}")

        if not result.passed:
            all_passed = False
            print(f"\n   ⚠️  CRITICAL PII DETECTED:")
            for match in result.critical_matches[:5]:  # Show first 5
                print(f"      - {match.type}: {match.context}")

        # Generate report
        report_file = file_path.replace(".json", "_pii_report.json")
        scanner.generate_report(result, report_file)
        print(f"   Report saved: {report_file}")

        all_results.append({
            "file": file_path,
            "result": result
        })

    print("\n" + "-" * 60)
    print(f"Overall PII Scan: {'✅ PASSED' if all_passed else '❌ FAILED'}")

    if not all_passed:
        print("\n⚠️  CRITICAL: PII detected in embeddings!")
        print("   Action required: Remove PII before proceeding to production")

    return all_passed


def run_volume_estimation():
    """Run token volume estimation."""
    print("\n" + "=" * 60)
    print("VOLUME ESTIMATION")
    print("=" * 60)

    estimator = VolumeEstimator()
    report = estimator.generate_report("volume_estimate_report.json")

    print("\n📊 Sample Statistics:")
    stats = report['estimates']['sample_stats']
    print(f"   Total items: {stats['total_items']}")
    print(f"   Total tokens: {stats['total_tokens']:,}")
    print(f"   Avg tokens/item: {stats['avg_tokens_per_item']:.2f}")

    print("\n📈 Monthly Projection:")
    monthly = report['estimates']['monthly_estimate']
    print(f"   New items: {monthly['new_items']:,.0f}")
    print(f"   Tokens: {monthly['tokens']:,.0f}")

    print("\n💰 Cost Projections:")
    costs = report['estimates']['cost_projections']
    print(f"   Embeddings (OpenAI): ${costs['embedding_generation']['cost_usd']}")
    print(f"   Summarization (Claude): ${costs['summarization_claude']['total_cost_usd']}")
    print(f"   Total monthly: ${costs['total_estimated_monthly']}")

    print("\n💵 Budget Compliance:")
    budget = report['budget_compliance']
    print(f"   Budget limit: ${budget['budget_limit_usd']}")
    print(f"   Estimated cost: ${budget['estimated_cost_usd']}")
    print(f"   Utilization: {budget['utilization_percent']:.1f}%")
    print(f"   Status: {budget['status']}")

    if budget['within_budget']:
        print(f"   Remaining: ${budget['remaining_budget_usd']}")
    else:
        overage = budget['estimated_cost_usd'] - budget['budget_limit_usd']
        print(f"   ⚠️  Over budget by: ${overage}")

    print("\n💡 Recommendations:")
    for rec in report['recommendations']:
        print(f"   {rec}")

    print(f"\nDetailed report saved: volume_estimate_report.json")

    return budget['within_budget']


def generate_combined_report(pii_passed: bool, budget_passed: bool):
    """Generate combined audit report."""
    print("\n" + "=" * 60)
    print("DATA AUDIT SUMMARY")
    print("=" * 60)

    report = {
        "pii_scan": {
            "status": "PASSED" if pii_passed else "FAILED",
            "recommendation": "Approved for embeddings" if pii_passed else "Remove PII before proceeding"
        },
        "volume_estimation": {
            "status": "WITHIN BUDGET" if budget_passed else "OVER BUDGET",
            "recommendation": "Approved for pilot" if budget_passed else "Reduce scope or increase budget"
        },
        "overall_status": "✅ GO" if (pii_passed and budget_passed) else "🛑 NO-GO",
        "go_no_go_decision": {
            "pii_check": pii_passed,
            "budget_check": budget_passed,
            "ready_for_pilot": pii_passed and budget_passed
        }
    }

    with open("data_audit_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n🔍 PII Scan: {'✅ PASSED' if pii_passed else '❌ FAILED'}")
    print(f"💰 Budget Check: {'✅ PASSED' if budget_passed else '❌ FAILED'}")
    print(f"\n{'='*60}")
    print(f"DECISION: {report['overall_status']}")
    print(f"{'='*60}")

    if pii_passed and budget_passed:
        print("\n🎉 Data audit complete - APPROVED for pilot deployment!")
        print("\nNext steps:")
        print("  1. Review compliance checklist: docs/COMPLIANCE.md")
        print("  2. Set up infrastructure: See docs/ARCHITECTURE.md")
        print("  3. Configure API credentials: cp .env.example .env")
    else:
        print("\n⚠️  Data audit identified issues - NOT APPROVED")
        print("\nAction items:")
        if not pii_passed:
            print("  • Remove critical PII from sample data")
            print("  • Update PII detection rules")
            print("  • Re-run export and audit")
        if not budget_passed:
            print("  • Reduce message volume or batch size")
            print("  • Optimize embedding strategy")
            print("  • Request budget increase")

    print(f"\nFull report saved: data_audit_report.json")

    return report


def main():
    """Run complete data audit."""
    print("=" * 60)
    print("Knowledge Summarizer Agent - Data Audit")
    print("=" * 60)

    # Check if sample files exist
    sample_files = [
        "sample_slack_messages.json",
        "sample_notion_pages.json",
        "sample_drive_docs.json"
    ]

    existing_files = [f for f in sample_files if Path(f).exists()]

    if not existing_files:
        print("\n❌ No sample data files found!")
        print("\nPlease run sample export first:")
        print("  python scripts/export_samples.py")
        return 1

    print(f"\nFound {len(existing_files)}/{len(sample_files)} sample files")

    # Run PII scan
    pii_passed = run_pii_scan()

    # Run volume estimation
    budget_passed = run_volume_estimation()

    # Generate combined report
    report = generate_combined_report(pii_passed, budget_passed)

    # Return exit code
    return 0 if (pii_passed and budget_passed) else 1


if __name__ == "__main__":
    sys.exit(main())
