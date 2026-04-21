"""Encuentra catch-blocks en web/js sin llamada a logError / console.error."""
import os
import re
import sys

if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BS = chr(92)  # backslash

findings = []
for root, _, files in os.walk("web/js"):
    for f in files:
        if not f.endswith(".js"):
            continue
        p = os.path.join(root, f)
        src = open(p, encoding="utf-8").read()
        i = 0
        while True:
            m = re.search(r"catch\s*(?:\([^)]*\))?\s*\{", src[i:])
            if not m:
                break
            start = i + m.start()
            body_start = i + m.end()
            depth = 1
            j = body_start
            while j < len(src) and depth > 0:
                c = src[j]
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                elif c == "/" and j + 1 < len(src) and src[j + 1] == "/":
                    while j < len(src) and src[j] != "\n":
                        j += 1
                elif c == "/" and j + 1 < len(src) and src[j + 1] == "*":
                    j += 2
                    while j + 1 < len(src) and not (src[j] == "*" and src[j + 1] == "/"):
                        j += 1
                    j += 1
                elif c in ('"', "'", "`"):
                    q = c
                    j += 1
                    while j < len(src) and src[j] != q:
                        if src[j] == BS:
                            j += 1
                        j += 1
                j += 1
            body = src[body_start : j - 1]
            line = src[:start].count("\n") + 1
            if all(k not in body for k in ("logError", "console.error", "console.warn")):
                findings.append((p, line, body.strip()[:150]))
            i = j

for p, l, b in findings:
    print(f"{p}:{l}  body={b!r}")
print("total:", len(findings))
