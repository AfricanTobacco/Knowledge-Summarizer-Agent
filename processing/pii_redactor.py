"""
PII redaction module for protecting sensitive information.
"""
import re
from typing import List, Tuple, Dict
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


@dataclass
class RedactionResult:
    """Result of PII redaction."""
    redacted_text: str
    redactions: List[Dict[str, str]]
    redaction_count: int


class PIIRedactor:
    """Redacts personally identifiable information from text."""
    
    # Regex patterns for PII detection
    PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
        "api_key": r'\b(?:sk-|pk_|key-)[a-zA-Z0-9]{20,}\b',
        "aws_key": r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
        "credit_card": r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        "ip_address": r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
        "bearer_token": r'\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b',
    }
    
    REPLACEMENTS = {
        "email": "[EMAIL_REDACTED]",
        "phone": "[PHONE_REDACTED]",
        "api_key": "[API_KEY_REDACTED]",
        "aws_key": "[AWS_KEY_REDACTED]",
        "credit_card": "[CREDIT_CARD_REDACTED]",
        "ssn": "[SSN_REDACTED]",
        "ip_address": "[IP_REDACTED]",
        "bearer_token": "[BEARER_TOKEN_REDACTED]",
    }
    
    def __init__(self, enabled: bool = True):
        """
        Initialize PII redactor.
        
        Args:
            enabled: Whether redaction is enabled
        """
        self.enabled = enabled
        
    def redact(self, text: str, log_redactions: bool = True) -> RedactionResult:
        """
        Redact PII from text.
        
        Args:
            text: Text to redact
            log_redactions: Whether to log redaction events
            
        Returns:
            RedactionResult with redacted text and metadata
        """
        if not self.enabled:
            return RedactionResult(
                redacted_text=text,
                redactions=[],
                redaction_count=0
            )
        
        if not text:
            return RedactionResult(
                redacted_text="",
                redactions=[],
                redaction_count=0
            )
        
        redacted_text = text
        redactions = []
        
        for pii_type, pattern in self.PATTERNS.items():
            matches = list(re.finditer(pattern, redacted_text))
            
            for match in matches:
                original_value = match.group(0)
                replacement = self.REPLACEMENTS[pii_type]
                
                # Record redaction
                redactions.append({
                    "type": pii_type,
                    "position": match.start(),
                    "length": len(original_value),
                    "replacement": replacement
                })
                
                # Perform redaction
                redacted_text = redacted_text.replace(original_value, replacement, 1)
        
        if redactions and log_redactions:
            logger.info(
                "pii_redacted",
                redaction_count=len(redactions),
                types=[r["type"] for r in redactions]
            )
        
        return RedactionResult(
            redacted_text=redacted_text,
            redactions=redactions,
            redaction_count=len(redactions)
        )
    
    def scan_for_pii(self, text: str) -> Dict[str, int]:
        """
        Scan text for PII without redacting.
        
        Args:
            text: Text to scan
            
        Returns:
            Dictionary of PII types found and their counts
        """
        if not text:
            return {}
        
        findings = {}
        
        for pii_type, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                findings[pii_type] = len(matches)
        
        return findings


if __name__ == "__main__":
    # Test the redactor
    redactor = PIIRedactor()
    
    test_text = """
    Contact me at john.doe@example.com or call 555-123-4567.
    My API key is sk-1234567890abcdefghijklmnopqrstuv.
    AWS key: AKIAIOSFODNN7EXAMPLE
    Bearer token: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
    IP: 192.168.1.1
    """
    
    result = redactor.redact(test_text)
    
    print("Original text:")
    print(test_text)
    print("\nRedacted text:")
    print(result.redacted_text)
    print(f"\nRedactions made: {result.redaction_count}")
    for redaction in result.redactions:
        print(f"  - {redaction['type']} at position {redaction['position']}")
    
    print("\nPII Scan:")
    findings = redactor.scan_for_pii(test_text)
    for pii_type, count in findings.items():
        print(f"  {pii_type}: {count}")
