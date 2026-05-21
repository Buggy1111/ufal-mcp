"""Per-category verifiers.

Kazdy verifier dostane:
- test (dict z test_cases.py)
- result (CallResult)
- payload (parsed tool output, dict | str | None)

Vraci tuple (status, note) kde status je:
- "pass" — test prosel
- "fail" — bug (chybny vystup)
- "expected_fail" — failed jak ocekavano (validation error u empty input)
- "error" — neocekavany crash
"""

from __future__ import annotations

from typing import Any


def _is_validation_error(result, payload) -> bool:
    """ValidationError v UFAL MCP se propaguje jako server JSON-RPC error,
    nebo jako isError=True s text content."""
    keywords = ("validation", "empty", "too large", "must be", "whitespace-only", "whitespace only")
    if result.error:
        msg = str(result.error.get("message", "")).lower()
        return any(k in msg for k in keywords)
    if result.response and result.response.get("isError"):
        content = result.response.get("content", [])
        for c in content:
            t = str(c.get("text", "")).lower()
            if any(k in t for k in keywords):
                return True
    if isinstance(payload, str) and any(k in payload.lower() for k in keywords):
        return True
    return False


def _payload_is_empty(payload) -> bool:
    if not isinstance(payload, dict):
        return False
    # extract_entities: count=0
    if "entities" in payload and isinstance(payload["entities"], list):
        return len(payload["entities"]) == 0
    # anonymize: anonymized == ""
    if "anonymized" in payload:
        return not payload["anonymized"].strip()
    return False


def verify_expect_validation_error(test, result, payload):
    if _is_validation_error(result, payload):
        return "expected_fail", "validation error as expected"
    if not result.ok:
        return "expected_fail", f"failed (not strictly validation): {result.exception or result.error}"
    return "fail", "expected ValidationError but call succeeded"


def verify_expect_validation_error_or_empty(test, result, payload):
    if _is_validation_error(result, payload):
        return "expected_fail", "validation error"
    if result.ok and _payload_is_empty(payload):
        return "pass", "passed through, empty output"
    if result.ok:
        return "pass", "passed through, non-empty output (acceptable for whitespace)"
    return "fail", f"unexpected failure: {result.exception or result.error}"


def verify_expect_no_crash(test, result, payload):
    if result.ok:
        return "pass", "no crash"
    if result.exception and "timeout" in result.exception.lower():
        return "error", f"timeout — possible hang: {result.exception}"
    if result.exception:
        return "error", f"crash: {result.exception}"
    if result.error:
        # JSON-RPC error from server (could be validation, which is OK)
        if _is_validation_error(result, payload):
            return "pass", "graceful validation rejection"
        return "fail", f"server error: {result.error}"
    return "fail", "isError=true returned"


def verify_expect_warning_or_strip(test, result, payload):
    """For PUA chars — server should strip and warn."""
    if not result.ok:
        return "fail", f"unexpected failure: {result.exception or result.error}"
    if isinstance(payload, dict):
        warnings = payload.get("warnings", [])
        if any("pua" in str(w).lower() or "private use" in str(w).lower() for w in warnings):
            return "pass", f"PUA warning present: {warnings}"
        return "fail", f"PUA chars passed without warning. warnings={warnings}"
    return "fail", "payload not dict"


def verify_expect_no_pii_leak(test, result, payload):
    """Check 'forbidden' substrings nejsou v anonymized output."""
    if not result.ok:
        return "error", f"call failed: {result.exception or result.error}"
    if not isinstance(payload, dict):
        return "error", "payload not dict"
    anonymized = payload.get("anonymized", "")
    forbidden = test.get("expected", {}).get("forbidden", [])
    leaked = [s for s in forbidden if s in anonymized]
    if leaked:
        return "fail", f"PII LEAK: {leaked} ({len(leaked)}/{len(forbidden)})"
    return "pass", f"no leak of {len(forbidden)} forbidden strings"


# Default — no crash + no isError
def verify_default(test, result, payload):
    return verify_expect_no_crash(test, result, payload)


VERIFIERS = {
    "expect_validation_error": verify_expect_validation_error,
    "expect_validation_error_or_empty": verify_expect_validation_error_or_empty,
    "expect_no_crash": verify_expect_no_crash,
    "expect_warning_or_strip": verify_expect_warning_or_strip,
    "expect_no_pii_leak": verify_expect_no_pii_leak,
}


def verify(test: dict, result, payload) -> tuple[str, str]:
    vname = test.get("verifier")
    if vname is None:
        return verify_default(test, result, payload)
    fn = VERIFIERS.get(vname, verify_default)
    return fn(test, result, payload)
