"""Strip secrets and identifiers from free text before it is stored."""
import re

# Case-sensitive, prefix-specific key shapes: a loose `(?i)sk...` redacted words like "skip_validation",
# and the <blob> rule needs upper, lower and digit so 40/64-char hex git SHAs survive.
_PATTERNS = [
    (re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}"), "<secret>"),
    (re.compile(r"\b[spr]k_(?:live|test)_[A-Za-z0-9]{16,}"), "<secret>"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"), "<secret>"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}"), "<secret>"),
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}"), "<secret>"),
    (re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{10,}"), "<secret>"),
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "<secret>"),
    (re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}"), "<jwt>"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "<private-key>"),
    (re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key|client[_-]?secret)\s*[:=]\s*\S+"), r"\1=<redacted>"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "<email>"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"), "<uuid>"),
    (re.compile(r"\b(?=[A-Za-z0-9+/]*[A-Z])(?=[A-Za-z0-9+/]*[a-z])(?=[A-Za-z0-9+/]*[0-9])[A-Za-z0-9+/]{40,}={0,2}"), "<blob>"),
]

def redact(text):
    if not text: return text
    for pat, rep in _PATTERNS: text = pat.sub(rep, text)
    return text
