import re

from app.pipeline.guardrails import GuardrailEngine


PROMPT_INJECTION_PATTERNS = [
    r"\b(ignore|disregard|bypass|override)\b.{0,80}\b(instruction|system|policy|guardrail)\b",
    r"\b(you are now|act as|pretend to be)\b.{0,80}\b(system|developer|admin)\b",
    r"\b(reveal|show|print|dump|exfiltrate|leak)\b.{0,80}\b(prompt|secret|token|api key|credential)\b",
    r"\b(do not follow|stop following)\b.{0,80}\b(rules|safety|policy|instructions)\b",
    r"<\s*(system|developer|assistant)\s*>",
    r"\bBEGIN\s+(SYSTEM|DEVELOPER)\s+PROMPT\b",
    r"\b(base64|rot13|hex)\b.{0,60}\b(decode|execute|run)\b",
    r"\b(tool|function|mcp)\b.{0,80}\b(call|invoke|execute)\b",
]


def _normalized_for_detection(text: str) -> str:
    """Normalize text to catch lightly-obfuscated prompt-injection payloads."""
    t = str(text or "").lower()
    t = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", t)  # remove zero-width chars
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _has_prompt_injection_signal(query: str) -> bool:
    q = _normalized_for_detection(query)
    return any(re.search(pattern, q, flags=re.IGNORECASE | re.DOTALL) for pattern in PROMPT_INJECTION_PATTERNS)


class QuerySafetyError(ValueError):
    """Raised when a user query fails prompt-safety validation."""


def assert_safe_query(query: str) -> str:
    """
    Validate and sanitize incoming user query before orchestration.
    Raises QuerySafetyError for clearly unsafe prompt-injection patterns.
    """
    engine = GuardrailEngine()

    q = str(query or "").strip()
    if not q:
        raise QuerySafetyError("Query cannot be empty")

    if len(q) > 4000:
        raise QuerySafetyError("Query too long")

    # Explicit prompt-injection/hijacking prevention at API boundary.
    if _has_prompt_injection_signal(q):
        raise QuerySafetyError("Unsafe query blocked: prompt-injection signal detected")

    if engine.is_blocked(q):
        raise QuerySafetyError("Unsafe query blocked by prompt safety guardrail")

    # Also block obvious secret-like payload attempts in user prompts.
    for pattern in engine.suspicious_patterns:
        if re.search(pattern, q, flags=re.IGNORECASE):
            raise QuerySafetyError("Query contains suspicious secret-like content")

    return engine.sanitize(q)
