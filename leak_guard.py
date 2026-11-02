"""Stop real customer data from reaching a public repo.

Scans files for things that look like real personal or payment data:
- email addresses outside reserved example domains
- phone numbers
- IBANs that pass the mod-97 checksum
- card numbers that pass the Luhn check
Exit code 1 if anything is found, so it works as a pre-commit hook or CI step.
Allow a known value by adding it to .leakguard-allow. Standard library only.
"""
import os
import re
import sys

SAFE_DOMAINS = ("example.com", "example.org", "example.net", "example.test", "invalid", "localhost")
EMAIL = re.compile(r"\b[\w.+-]+@([\w-]+(?:\.[\w-]+)+)\b")
PHONE = re.compile(r"(?<![\w.])\+\d{1,3}[ \-]?\d{2,3}[ \-]?\d{3}[ \-]?\d{3,4}\b")
IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,3})?\b")
CARD = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules"}


def iban_ok(raw):
    s = raw.replace(" ", "")
    if not 15 <= len(s) <= 34:
        return False
    n = "".join(str(int(c, 36)) for c in s[4:] + s[:4])
    return int(n) % 97 == 1


def luhn_ok(raw):
    digits = [int(d) for d in re.sub(r"\D", "", raw)]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2:
            d *= 2
            d -= 9 if d > 9 else 0
        total += d
    return total % 10 == 0


def scan_text(text, allow=()):
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        for m in EMAIL.finditer(line):
            domain = m.group(1).lower()
            if not domain.endswith(SAFE_DOMAINS) and m.group(0) not in allow:
                hits.append((n, "email", m.group(0)))
        for m in PHONE.finditer(line):
            if m.group(0) not in allow:
                hits.append((n, "phone", m.group(0)))
        for m in IBAN.finditer(line):
            if iban_ok(m.group(0)) and m.group(0) not in allow:
                hits.append((n, "iban", m.group(0)))
        for m in CARD.finditer(line):
            if luhn_ok(m.group(0)) and m.group(0) not in allow:
                hits.append((n, "card", m.group(0)))
    return hits


def mask(value):
    return value[:2] + "…" + value[-2:] if len(value) > 6 else "…"


def scan_tree(root, allow):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            path = os.path.join(dirpath, f)
            try:
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
            except (UnicodeDecodeError, OSError):
                continue
            found += [(path, *h) for h in scan_text(text, allow)]
    return found


def main(root="."):
    allow = set()
    if os.path.exists(os.path.join(root, ".leakguard-allow")):
        with open(os.path.join(root, ".leakguard-allow"), encoding="utf-8") as fh:
            allow = {l.strip() for l in fh if l.strip() and not l.startswith("#")}
    found = scan_tree(root, allow)
    for path, line, kind, value in found:
        print(f"{path}:{line}  {kind:<5} {mask(value)}")
    print(f"\n{len(found)} possible leak(s)" if found else "clean: no personal or payment data found")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
