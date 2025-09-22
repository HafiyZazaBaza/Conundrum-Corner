# conundrum/utils/profanity_filter.py
import re
import json
import os

# Default fallback rules
DEFAULT_RULES = [
    {"id": "default-1", "match": "fuck", "severity": 3, "tags": ["swear"], "partial_match": "true"},
    {"id": "default-2", "match": "shit", "severity": 3, "tags": ["swear"], "partial_match": "true"},
    {"id": "default-3", "match": "bitch", "severity": 2, "tags": ["insult"], "partial_match": "true"},
]


def _wildcard_to_regex(s: str) -> str:
    """Turn simple patterns using '*' and '|' into regex."""
    if not s:
        return ""
    s = str(s).strip()
    esc = re.escape(s)
    esc = esc.replace(r"\|", "|")
    esc = esc.replace(r"\*", ".*")
    return esc


class ProfanityFilter:
    """Profanity filter with JSON-configurable rules."""
    def __init__(self, rules=None):
        self.rules = rules if isinstance(rules, list) else DEFAULT_RULES.copy()
        self._compile()

    @classmethod
    def from_json(cls, path):
        """Load rules from JSON file; fallback to defaults on error."""
        try:
            abspath = os.path.abspath(path)
            with open(abspath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("profanity JSON must be a list of rules")
            return cls(data)
        except Exception as e:
            print(f"[ProfanityFilter] failed to load '{path}': {e}. Using defaults.")
            return cls(DEFAULT_RULES.copy())

    def _compile(self):
        self.compiled = []
        for r in self.rules:
            raw = r.get("match", "")
            partial = str(r.get("partial_match", "true")).lower() != "false"
            pat = _wildcard_to_regex(raw)
            if not partial:
                pat = r"\b(?:" + pat + r")\b"

            try:
                cre = re.compile(pat, re.IGNORECASE)
            except re.error:
                cre = re.compile(re.escape(raw), re.IGNORECASE)

            exceptions = []
            for ex in r.get("exceptions", []) or []:
                ex_pat = _wildcard_to_regex(ex)
                try:
                    exceptions.append(re.compile(ex_pat, re.IGNORECASE))
                except re.error:
                    exceptions.append(re.compile(re.escape(ex), re.IGNORECASE))

            self.compiled.append((r, cre, exceptions))

    def check(self, text):
        """Return list of violations in text."""
        violations = []
        text = text or ""
        for rule, cre, ex_list in self.compiled:
            m = cre.search(text)
            if not m:
                continue
            if any(ex.search(text) for ex in ex_list):
                continue
            violations.append({
                "id": rule.get("id"),
                "severity": rule.get("severity"),
                "tags": rule.get("tags", []),
                "match": m.group(0),
                "rule_match": rule.get("match")
            })
        return violations

    def censor(self, text, mask_char="*"):
        """Replace matched spans with mask_char."""
        if not text:
            return text
        out = text
        hits = []
        for _, cre, ex_list in self.compiled:
            for m in cre.finditer(out):
                if any(ex.search(out) for ex in ex_list):
                    continue
                hits.append((m.start(), m.end()))
        if not hits:
            return out
        hits.sort()
        merged = []
        s, e = hits[0]
        for ns, ne in hits[1:]:
            if ns <= e:
                e = max(e, ne)
            else:
                merged.append((s, e))
                s, e = ns, ne
        merged.append((s, e))
        res, last = [], len(out)
        for s, e in reversed(merged):
            res.append(out[e:last])
            res.append(mask_char * (e - s))
            last = s
        res.append(out[:last])
        return "".join(reversed(res))

    def clean(self, text, mask_char="*"):
        """Return (censored_text, violations)."""
        return self.censor(text, mask_char), self.check(text)
