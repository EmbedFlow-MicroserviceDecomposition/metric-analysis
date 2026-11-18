#!/usr/bin/env python3
"""Runtime-check helper (added only to the scratchpad copy): after the integration tests, read every running
boulder server's Prometheus /metrics and record which gRPC methods each process called as a CLIENT
(grpc_client_handled_total / grpc_client_started_total) and served (grpc_server_handled_total)."""
import json, re, sys, urllib.request
sys.path.insert(0, "test")
import startservers
out = {}
for s in startservers.SERVICES:
    # The Service tuple's debug_port is not always the debug listener (boulder-wfe2 lists its ACME port 4001),
    # so use the process's own --debug-addr argument when present.
    args = list(s.cmd); port = s.debug_port
    if "--debug-addr" in args: port = args[args.index("--debug-addr") + 1].rsplit(":", 1)[-1]
    url = f"http://localhost:{port}/metrics"
    try:
        body = urllib.request.urlopen(url, timeout=10).read().decode()
    except Exception as e:
        out[s.name] = {"error": str(e)}; continue
    rec = {"client": {}, "server": {}}
    for line in body.splitlines():
        m = re.match(r'grpc_(client|server)_(?:handled|started)_total\{([^}]*)\}\s+([0-9.e+]+)', line)
        if not m or float(m[3]) == 0: continue
        labels = dict(re.findall(r'(\w+)="([^"]*)"', m[2]))
        key = f'/{labels.get("grpc_service")}/{labels.get("grpc_method")}'
        side = rec[m[1]]; side[key] = max(side.get(key, 0), float(m[3]))
    out[s.name] = rec
json.dump(out, open("/boulder/runtime_metrics.json", "w"), indent=1)
print("scraped", len(out), "servers;", sum(1 for v in out.values() if "error" not in v), "ok")
