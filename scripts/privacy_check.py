#!/usr/bin/env python3
"""
Privacy gate for anything that goes into this public repo.

Usage:
  python3 scripts/privacy_check.py [--terms FILE] PATH [PATH ...]
  PATH may be files or directories (recursed; .html .json .md .txt .js .py .svg .css).
  Exit 0 = clean, exit 1 = findings (printed as  file:line  rule  snippet).

Built-in rules (always on):
  email addresses, phone numbers, API keys/tokens (AWS, GitHub, OpenAI, Slack, generic 32+ hex/base64 secrets),
  AWS account IDs, private IPv4 addresses, Windows/Unix home paths with a username, street-address shapes,
  SSN shape, credit-card shape, and "password/secret/token =" assignments with a literal.

Optional --terms FILE: one term per line (case-insensitive substring; lines starting with # ignored).
Keep that file OUTSIDE the repo — it is the list of names you never want published, so it must never be published.
"""
import argparse, re, sys
from pathlib import Path

EXTS = {".html", ".htm", ".json", ".md", ".txt", ".js", ".py", ".svg", ".css", ".yml", ".yaml"}
ALLOW_EMAIL_DOMAINS = ("example.com", "example.org", "w3.org", "anthropic.com", "github.com", "giscus.app")

RULES = [
    ("email",        re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("phone",        re.compile(r"(?<![\d.])(?:\+1[ .-]?)?\(?\b[2-9]\d{2}\)?[ .-]\d{3}[ .-]\d{4}\b")),
    ("aws-key",      re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}\b")),
    ("openai-key",   re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{20,}\b")),
    ("slack-token",  re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("aws-account",  re.compile(r"(?<![\d.])\d{12}(?![\d.])")),
    ("private-ip",   re.compile(r"\b(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}(?:\.\d{1,3})?\b")),
    ("home-path",    re.compile(r"(?:[A-Za-z]:\\(?:Users|Clients)\\[^\\\s\"']+|/(?:Users|home)/[a-z0-9_-]+/)", re.I)),
    ("street-addr",  re.compile(r"\b\d{2,5}\s+[A-Z][a-z]+(?:\s[A-Z][a-z]+)?\s(?:St|Street|Ave|Avenue|Blvd|Dr|Drive|Rd|Road|Ln|Lane|Way|Ct|Court)\b\.?")),
    ("ssn",          re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("card",         re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    ("secret-assign",re.compile(r"(?i)\b(?:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*['\"][^'\"]{6,}['\"]")),
    ("long-secret",  re.compile(r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+]{40,}={0,2}(?![A-Za-z0-9/+=])")),
]
# patterns that are obviously code, not secrets, for the long-secret rule
CODE_NOISE = re.compile(r"^(?:[A-Za-z0-9]{40,})$")  # pure alnum blob of 40+ (base64 images, hashes) -> still flag; tuned below

def scan_text(text, terms):
    out = []
    for ln, line in enumerate(text.splitlines(), 1):
        for t, trx in terms:
            if trx.search(line):
                out.append((ln, f"term:{t}", line.strip()[:120]))
        for name, rx in RULES:
            for m in rx.finditer(line):
                s = m.group(0)
                if name == "email" and s.lower().endswith(ALLOW_EMAIL_DOMAINS): continue
                if name == "card":
                    digits = re.sub(r"\D", "", s)
                    if not luhn(digits): continue
                if name == "long-secret":
                    # skip data URIs / svg paths / minified code lines (very long lines are code)
                    if "data:image" in line or len(line) > 400 or "base64" in line: continue
                out.append((ln, name, s[:80]))
    return out

def luhn(d):
    if not 13 <= len(d) <= 16: return False
    tot, alt = 0, False
    for ch in reversed(d):
        n = int(ch)
        if alt: n = n * 2 - 9 if n * 2 > 9 else n * 2
        tot += n; alt = not alt
    return tot % 10 == 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--terms")
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args()
    terms = []
    if a.terms and Path(a.terms).exists():
        terms = [(t, re.compile(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", re.I))
                 for t in (l.strip() for l in Path(a.terms).read_text(encoding="utf-8", errors="ignore").splitlines())
                 if t and not t.startswith("#")]
    files = []
    for p in map(Path, a.paths):
        if p.is_dir():
            files += [f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in EXTS and ".git" not in f.parts]
        elif p.is_file():
            files.append(p)
    findings = 0
    for f in files:
        try: text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception: continue
        for ln, rule, snip in scan_text(text, terms):
            print(f"{f}:{ln}  {rule}  {snip}")
            findings += 1
    print(f"\n{'CLEAN' if not findings else f'{findings} finding(s)'} — {len(files)} file(s) scanned")
    sys.exit(1 if findings else 0)

if __name__ == "__main__":
    main()
