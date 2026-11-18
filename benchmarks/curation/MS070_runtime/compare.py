"""Compare boulder runtime gRPC client metrics (runtime_metrics.json) with the MS070 ground truth."""
import json, re, sys, collections
metrics = json.load(open(sys.argv[1])); gt = json.load(open(sys.argv[2]))
PROC = [(r"^remoteva-", "va"), (r"^boulder-va-", "va"), (r"^boulder-sa-", "sa"), (r"^boulder-publisher-", "publisher"),
        (r"^boulder-ca-", "ca"), (r"^boulder-ra-", "ra"), (r"^crl-storer$", "crl-storer"), (r"^bad-key-revoker$", "bad-key-revoker"),
        (r"^nonce-service-", "nonce"), (r"^email-exporter$", "email-exporter"), (r"^boulder-wfe2$", "wfe2"), (r"^sfe$", "sfe"),
        (r"^log-validator$", "log-validator"), (r"^boulder-mtca-", "mtca"), (r"^boulder-mtcb$", "mtcb"), (r"^boulder-mtpublisher-", "mtpublisher")]
def svc(proc): return next((s for rx, s in PROC if re.search(rx, proc)), None)   # None = test fake (ct/s3/salesforce/zendesk)
by_endpoint = {i["endpoint"]: (s, i["id"]) for s, o in gt["microservices"].items() for i in o["exposed_interfaces"] if i["protocol"] == "gRPC"}
gt_pairs = {(c["src_service"], c["dst_service"], c["dst_interface_id"]) for c in gt["inter_service_calls"]}

observed = collections.Counter(); unmapped = collections.Counter(); self_calls = collections.Counter(); errors = []
server_seen = collections.Counter()
for proc, rec in metrics.items():
    s = svc(proc)
    if "error" in rec: errors.append((proc, rec["error"])); continue
    if s is None: continue
    for ep, n in rec["server"].items(): server_seen[(s, ep)] += n
    for ep, n in rec["client"].items():
        if ep.startswith("/grpc.health"): continue
        if ep not in by_endpoint: unmapped[(s, ep)] += n; continue
        d, iid = by_endpoint[ep]
        (self_calls if d == s else observed)[(s, d, iid)] += n
print("== processes not scraped:", errors or "none")
print(f"\n== Observed caller-service -> interface pairs ({len(observed)})")
for k, n in sorted(observed.items()): print(f"  {'IN GT    ' if k in gt_pairs else 'NOT IN GT'} {k[0]:16} -> {k[1]:14} {k[2]:58} x{int(n)}")
print("\n== Same-service calls (excluded by rule):"); [print(f"  {k[0]} -> {k[2]} x{int(n)}") for k, n in sorted(self_calls.items())]
print("\n== Client calls to methods with no GT interface:"); [print(f"  {k[0]} -> {k[1]} x{int(n)}") for k, n in sorted(unmapped.items())]
callers_scraped = {svc(p) for p, r in metrics.items() if "error" not in r and svc(p)}
missing = sorted(p for p in gt_pairs - set(observed))
print("\n== GT pairs NOT observed (caller process scraped?):")
for p in missing:
    ep = next(e for e, v in by_endpoint.items() if v == (p[1], p[2]))
    print(f"  {p[0]:16} -> {p[1]:14} {p[2]:58} caller scraped={p[0] in callers_scraped}  server-side count={int(server_seen.get((p[1], ep), 0))}")
print(f"\nSUMMARY: GT pairs {len(gt_pairs)} | observed {len(set(observed) & gt_pairs)} | observed-but-not-in-GT {len(set(observed) - gt_pairs)} "
      f"| not observed {len(missing)} (of which caller not a scraped long-running process: {sum(1 for p in missing if p[0] not in callers_scraped)})")
