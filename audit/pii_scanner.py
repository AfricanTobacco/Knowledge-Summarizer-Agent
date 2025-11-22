"""
PII (Personally Identifiable Information) scanner for data audit.
Detects emails, phone numbers, API keys, and other sensitive data.
"""
import re
import json
from typing import List, Dict, Set, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import structlog

logger = structlog.get_logger()


@dataclass
class PIIMatch:
    """Represents a PII match found in text."""
    type: str
    value: str
    context: str
    line_number: int = 0
    file_path: str = ""


@dataclass
class PIIScanResult:
    """Results of a PII scan."""
    total_items_scanned: int
    pii_matches_found: int
    pii_types_detected: Set[str]
    matches_by_type: Dict[str, int]
    critical_matches: List[PIIMatch]
    warnings: List[str]
    passed: bool


class PIIScanner:
    """Scanner for detecting PII in text data."""

    # Regex patterns for common PII types
    PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'\b(?:\+?27|0)(?:\s*\d){9}\b',  # South African phone numbers
        "api_key": r'\b(?:api[_-]?key|apikey|access[_-]?token|secret[_-]?key)[\s:=]+["\']?([A-Za-z0-9_\-]{20,})["\']?\b',
        "slack_token": r'\bxox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9]{24,}\b',
        "aws_key": r'\b(?:AKIA|A3T|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}\b',
        "openai_key": r'\bsk-[A-Za-z0-9]{48}\b',
        "anthropic_key": r'\bsk-ant-[A-Za-z0-9\-]{95,}\b',
        "id_number": r'\b(?:(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01]))\d{7}\b',  # SA ID numbers
        "credit_card": r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b',
        "ip_address": r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
        "jwt_token": r'\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b'
    }

    # Critical PII types that must not appear in embeddings
    CRITICAL_TYPES = {
        "api_key", "slack_token", "aws_key", "openai_key",
        "anthropic_key", "id_number", "credit_card", "jwt_token"
    }

    def __init__(self, anonymize: bool = True):
        """
        Initialize PII scanner.

        Args:
            anonymize: Whether to anonymize detected PII in output.
        """
        self.anonymize = anonymize

    def scan_text(self, text: str, context: str = "") -> List[PIIMatch]:
        """
        Scan text for PII.

        Args:
            text: Text to scan.
            context: Context description (e.g., file path, message ID).

        Returns:
            List of PII matches found.
        """
        matches = []

        for pii_type, pattern in self.PATTERNS.items():
            regex = re.compile(pattern, re.IGNORECASE)
            for match in regex.finditer(text):
                pii_match = PIIMatch(
                    type=pii_type,
                    value=match.group(0),
                    context=context,
                    line_number=text[:match.start()].count('\n') + 1
                )
                matches.append(pii_match)

                logger.debug(
                    "pii_detected",
                    type=pii_type,
                    context=context,
                    line=pii_match.line_number
                )

        return matches

    def scan_json_file(self, file_path: str) -> PIIScanResult:
        """
        Scan a JSON file for PII.

        Args:
            file_path: Path to JSON file.

        Returns:
            PII scan results.
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            return self.scan_data(data, file_path)
        except Exception as e:
            logger.error("pii_scan_file_failed", file_path=file_path, error=str(e))
            return PIIScanResult(
                total_items_scanned=0,
                pii_matches_found=0,
                pii_types_detected=set(),
                matches_by_type={},
                critical_matches=[],
                warnings=[f"Failed to scan file: {e}"],
                passed=False
            )

    def scan_data(
        self,
        data: Any,
        source: str = "unknown"
    ) -> PIIScanResult:
        """
        Scan structured data for PII.

        Args:
            data: Data to scan (list, dict, or primitive).
            source: Data source identifier.

        Returns:
            PII scan results.
        """
        all_matches = []
        items_scanned = 0

        def scan_recursive(obj: Any, path: str = ""):
            nonlocal items_scanned

            if isinstance(obj, dict):
                for key, value in obj.items():
                    scan_recursive(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                items_scanned += len(obj)
                for idx, item in enumerate(obj):
                    scan_recursive(item, f"{path}[{idx}]")
            elif isinstance(obj, str):
                matches = self.scan_text(obj, context=f"{source}:{path}")
                all_matches.extend(matches)
            else:
                items_scanned += 1

        scan_recursive(data)

        # Categorize matches
        matches_by_type = {}
        critical_matches = []

        for match in all_matches:
            matches_by_type[match.type] = matches_by_type.get(match.type, 0) + 1
            if match.type in self.CRITICAL_TYPES:
                critical_matches.append(match)

        pii_types = set(match.type for match in all_matches)
        passed = len(critical_matches) == 0

        result = PIIScanResult(
            total_items_scanned=items_scanned,
            pii_matches_found=len(all_matches),
            pii_types_detected=pii_types,
            matches_by_type=matches_by_type,
            critical_matches=critical_matches,
            warnings=[
                f"Found {len(critical_matches)} critical PII matches that must be removed"
            ] if critical_matches else [],
            passed=passed
        )

        logger.info(
            "pii_scan_complete",
            source=source,
            items_scanned=items_scanned,
            matches_found=len(all_matches),
            critical_matches=len(critical_matches),
            passed=passed
        )

        return result

    def anonymize_text(self, text: str) -> str:
        """
        Anonymize PII in text.

        Args:
            text: Text to anonymize.

        Returns:
            Text with PII anonymized.
        """
        anonymized = text

        for pii_type, pattern in self.PATTERNS.items():
            regex = re.compile(pattern, re.IGNORECASE)
            anonymized = regex.sub(f"[{pii_type.upper()}_REDACTED]", anonymized)

        return anonymized

    def generate_report(
        self,
        results: PIIScanResult,
        output_file: str = "pii_scan_report.json"
    ) -> None:
        """
        Generate PII scan report.

        Args:
            results: Scan results.
            output_file: Output file path.
        """
        report = {
            "total_items_scanned": results.total_items_scanned,
            "pii_matches_found": results.pii_matches_found,
            "pii_types_detected": list(results.pii_types_detected),
            "matches_by_type": results.matches_by_type,
            "critical_matches_count": len(results.critical_matches),
            "critical_matches": [
                {
                    "type": match.type,
                    "value": match.value[:10] + "..." if self.anonymize else match.value,
                    "context": match.context,
                    "line_number": match.line_number
                }
                for match in results.critical_matches
            ],
            "warnings": results.warnings,
            "passed": results.passed,
            "recommendation": "APPROVED for embeddings" if results.passed else "REJECTED - Remove critical PII before proceeding"
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info("pii_report_generated", output_file=output_file, passed=results.passed)


def scan_sample_exports():
    """Scan all sample export files for PII."""
    scanner = PIIScanner(anonymize=True)
    results_summary = []

    sample_files = [
        "sample_slack_messages.json",
        "sample_notion_pages.json",
        "sample_drive_docs.json"
    ]

    for file_path in sample_files:
        if Path(file_path).exists():
            print(f"\n📄 Scanning {file_path}...")
            result = scanner.scan_json_file(file_path)

            print(f"   Items scanned: {result.total_items_scanned}")
            print(f"   PII matches: {result.pii_matches_found}")
            print(f"   Critical matches: {len(result.critical_matches)}")
            print(f"   Status: {'✅ PASSED' if result.passed else '❌ FAILED'}")

            if result.matches_by_type:
                print(f"   PII types found: {', '.join(result.pii_types_detected)}")

            results_summary.append({
                "file": file_path,
                "result": result
            })

            # Generate individual report
            report_file = file_path.replace(".json", "_pii_report.json")
            scanner.generate_report(result, report_file)
        else:
            print(f"⚠️  {file_path} not found - skipping")

    # Generate combined report
    all_passed = all(r["result"].passed for r in results_summary)
    print(f"\n{'='*60}")
    print(f"Overall PII Scan: {'✅ PASSED' if all_passed else '❌ FAILED'}")
    print(f"{'='*60}")

    return all_passed


if __name__ == "__main__":
    # Run PII scan on sample exports
    scan_sample_exports()
