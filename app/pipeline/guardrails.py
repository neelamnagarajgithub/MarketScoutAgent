import hashlib
import json
import re
import unicodedata
from urllib.parse import urlparse
from typing import Any, Dict, List, Tuple

from app.pipeline.types import RetrievedItem


class GuardrailEngine:
    """Sanitize, filter unsafe or low-signal content, and remove duplicates."""

    def __init__(self):
        self.block_patterns = [
            r"ignore\s+previous\s+instructions",
            r"system\s+prompt",
            r"jailbreak",
            r"developer\s+message",
            r"<script.*?>.*?</script>",
            r"prompt\s+injection",
            r"bypass\s+guardrails",
            r"reveal\s+hidden\s+instructions",
            r"act\s+as\s+if\s+you\s+are\s+the\s+system",
        ]
        self.suspicious_patterns = [
            r"sk-[A-Za-z0-9]{16,}",
            r"github_pat_[A-Za-z0-9_]{20,}",
            r"glpat-[A-Za-z0-9\-_.]{10,}",
            r"bearer\s+[A-Za-z0-9\-_.]{15,}",
            r"api[_-]?key[=:]\s*[A-Za-z0-9\-_.]{8,}",
        ]
        self.allowed_url_schemes = {"http", "https"}

    def _normalize_text(self, text: str) -> str:
        t = unicodedata.normalize("NFKC", text or "")
        t = t.replace("\x00", " ")
        return t

    def sanitize(self, text: str) -> str:
        t = self._normalize_text(text).strip()
        t = re.sub(r"<[^>]+>", " ", t)
        t = re.sub(r"```.*?```", " ", t, flags=re.DOTALL)
        t = re.sub(r"\bdata:text/html[^\s]*", " ", t)
        t = re.sub(r"\s+", " ", t)
        return t[:6000]

    def sanitize_metadata(self, metadata: Any) -> Dict[str, Any]:
        if not isinstance(metadata, dict):
            return {}
        out: Dict[str, Any] = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                out[str(key)] = self.redact_sensitive_data(str(value)) if isinstance(value, str) else value
            elif isinstance(value, list):
                out[str(key)] = [self.redact_sensitive_data(str(v))[:300] for v in value[:20]]
            elif isinstance(value, dict):
                out[str(key)] = self.sanitize_metadata(value)
            else:
                out[str(key)] = str(value)[:300]
        return out

    def redact_sensitive_data(self, text: str) -> str:
        t = text or ""
        t = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", t)
        t = re.sub(r"\+?\d[\d\s().-]{7,}\d", "[REDACTED_PHONE]", t)
        for pattern in self.suspicious_patterns:
            t = re.sub(pattern, "[REDACTED_SECRET]", t, flags=re.IGNORECASE)
        return t

    def is_blocked(self, text: str) -> bool:
        t = (text or "").lower()
        return any(re.search(p, t, flags=re.IGNORECASE) for p in self.block_patterns)

    def is_valid_url(self, url: str) -> bool:
        if not url:
            return False
        try:
            parsed = urlparse(url.strip())
            return parsed.scheme in self.allowed_url_schemes and bool(parsed.netloc)
        except Exception:
            return False

    def normalized_url(self, url: str) -> str:
        if not url:
            return ""
        try:
            parsed = urlparse(url.strip().lower())
            path = re.sub(r"/+", "/", parsed.path.rstrip("/"))
            return f"{parsed.scheme}://{parsed.netloc}{path}"
        except Exception:
            return url.strip().lower()

    def text_quality_score(self, item: RetrievedItem) -> float:
        title = (item.title or "").strip()
        content = (item.content or "").strip()
        score = 0.0
        if len(title) >= 12:
            score += 0.2
        if len(content) >= 80:
            score += 0.25
        if len(content) >= 180:
            score += 0.15
        if self.is_valid_url(item.url):
            score += 0.15
        alpha_ratio = (sum(ch.isalpha() for ch in content) / max(len(content), 1)) if content else 0.0
        if alpha_ratio >= 0.45:
            score += 0.15
        if item.published_at:
            score += 0.05
        if item.metadata:
            score += 0.05
        return round(min(score, 1.0), 3)

    def classify_item_risks(self, item: RetrievedItem) -> List[str]:
        risks: List[str] = []
        title = item.title or ""
        content = item.content or ""
        if self.is_blocked(title) or self.is_blocked(content):
            risks.append("prompt_injection_or_policy_bypass")
        if not self.is_valid_url(item.url):
            risks.append("invalid_or_missing_url")
        if len(title.strip()) < 8:
            risks.append("weak_title")
        if len(content.strip()) < 40:
            risks.append("thin_content")
        if re.search(r"[{}<>]{6,}", content):
            risks.append("markup_or_payload_noise")
        if any(re.search(p, content, flags=re.IGNORECASE) for p in self.suspicious_patterns):
            risks.append("contains_sensitive_pattern")
        return risks

    def _fingerprint(self, item: RetrievedItem) -> str:
        normalized_title = re.sub(r"\W+", " ", (item.title or "").lower()).strip()
        normalized_content = re.sub(r"\W+", " ", (item.content or "")[:320].lower()).strip()
        key_raw = f"{self.normalized_url(item.url)}|{normalized_title}|{normalized_content}"
        return hashlib.sha256(key_raw.encode()).hexdigest()

    def deduplicate(self, items: List[RetrievedItem]) -> Tuple[List[RetrievedItem], int]:
        seen = set()
        out = []
        dropped = 0
        for it in items:
            key = self._fingerprint(it)
            if key in seen:
                dropped += 1
                continue
            seen.add(key)
            out.append(it)
        return out, dropped

    def enforce(self, items: List[RetrievedItem]) -> Tuple[List[RetrievedItem], int, List[str]]:
        flags = []
        clean = []
        blocked = 0
        low_quality = 0
        invalid_urls = 0
        redacted = 0

        for it in items:
            original_title = it.title
            original_content = it.content
            it.title = self.redact_sensitive_data(self.sanitize(it.title))
            it.content = self.redact_sensitive_data(self.sanitize(it.content))
            it.metadata = self.sanitize_metadata(it.metadata)

            if it.title != original_title or it.content != original_content:
                redacted += 1

            risks = self.classify_item_risks(it)
            quality_score = self.text_quality_score(it)
            it.metadata = it.metadata or {}
            it.metadata["guardrails"] = {
                "risks": risks,
                "quality_score": quality_score,
                "normalized_url": self.normalized_url(it.url),
            }

            if "prompt_injection_or_policy_bypass" in risks:
                blocked += 1
                continue

            if "invalid_or_missing_url" in risks:
                invalid_urls += 1
                if quality_score < 0.45:
                    continue

            if quality_score < 0.30:
                low_quality += 1
                continue

            clean.append(it)

        clean, dup = self.deduplicate(clean)
        if blocked:
            flags.append(f"blocked_items={blocked}")
        if invalid_urls:
            flags.append(f"invalid_urls_detected={invalid_urls}")
        if low_quality:
            flags.append(f"low_quality_items_removed={low_quality}")
        if dup:
            flags.append(f"duplicates_removed={dup}")
        if redacted:
            flags.append(f"sanitized_or_redacted_items={redacted}")
        return clean, blocked + dup + low_quality, flags