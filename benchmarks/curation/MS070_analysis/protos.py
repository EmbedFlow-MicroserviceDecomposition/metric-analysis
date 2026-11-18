"""Parse boulder .proto files: package, services, and rpcs with request/response types."""
import re, sys, json
from pathlib import Path
root = Path(sys.argv[1]); out = []
for f in sorted(root.rglob("*.proto")):
    rel = f.relative_to(root)
    if rel.parts[0] in ("vendor", "test") or "test_proto" in str(rel): continue
    src = re.sub(r"//[^\n]*", "", f.read_text())
    pkg = re.search(r"\bpackage\s+([\w.]+)\s*;", src)
    for sm in re.finditer(r"\bservice\s+(\w+)\s*\{", src):
        depth, i = 1, sm.end()
        while depth: depth += {"{": 1, "}": -1}.get(src[i], 0); i += 1
        body = src[sm.end(): i]
        for r in re.finditer(r"\brpc\s+(\w+)\s*\(\s*(stream\s+)?([\w.]+)\s*\)\s*returns\s*\(\s*(stream\s+)?([\w.]+)\s*\)", body):
            out.append({"proto": str(rel), "package": pkg[1] if pkg else "", "service": sm[1], "rpc": r[1],
                        "req": ("stream " if r[2] else "") + r[3], "resp": ("stream " if r[4] else "") + r[5],
                        "line": src[: sm.end()].count("\n") + body[: r.start()].count("\n") + 1})
json.dump(out, open(sys.argv[2], "w"), indent=1)
from collections import Counter
for (p, s), n in Counter((o["proto"], o["service"]) for o in out).items(): print(f"{p:44} {s:28} {n}")
print("total rpcs:", len(out))
