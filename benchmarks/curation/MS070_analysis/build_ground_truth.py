"""Build benchmarks/ground_truth/MS070.json (+ curation/MS070.sites.json) from the type-checked analyzer output.

Inputs: ms070_analyzer/out.json (go/packages, type-resolved), ms070_rpcs.json (proto RPCs), the boulder sources.
Every mapping below was reviewed against the code (see benchmarks/curation/MS070.md).
"""
import json, re
from pathlib import Path

SP = Path("/private/tmp/claude-501/-Users-ravishan-Desktop-FYP/d847329e-7971-4487-8e02-93587adeb48b/scratchpad")
CB = Path("codebases/microservices/MS070_boulder")
B = "github.com/letsencrypt/boulder/"
an = json.load(open(SP / "ms070_analyzer/out.json"))
rpcs = json.load(open(SP / "ms070_rpcs.json"))
part = json.load(open("outputs/MS070/output.json"))["microservices"]
svc_of = {c: s for s, v in part.items() for c in v}

def src_line(path, n): return (CB / path).read_text().splitlines()[n - 1]
def ev(path, n, snippet):
    line = src_line(path, n)
    assert "`" not in snippet and snippet in line, (path, n, snippet, line)
    return f"{path}:{n} `{snippet}`"
def find(path, needle, start=1):
    for i, l in enumerate((CB / path).read_text().splitlines(), 1):
        if i >= start and needle in l: return i
    raise KeyError((path, needle))
def pname(full):  # go type path -> partition class (package NAME + type)
    path, typ = full.rsplit(".", 1); last = path.rsplit("/", 1)[-1]
    return ("notmain" if last == "bad-key-revoker" else last) + "." + typ
def short(t):
    t = t.strip(); stream = t.startswith("stream ")
    t = t.replace("stream ", "").split(".")[-1]
    return f"List<{t}>" if stream else t

# ---------------- gRPC interfaces: registered impl x RPCs of its proto service ----------------
ifaces = {}; iface_by = {}      # (impl_class, rpc) -> interface
for r in an["registrations"]:
    if not r["impl_type"].startswith(B) or r["file"].startswith("cmd/remoteva"):
        continue  # grpc health server (library); remoteva = same va impl (role of va)
    svc_name = r["desc"].split(".")[-1].replace("_ServiceDesc", "")
    proto_dir = r["desc_pkg"].replace(B, "")
    cls = pname(r["impl_type"]); svc = svc_of[cls]
    methods = [x for x in rpcs if x["service"] == svc_name and x["proto"].startswith(proto_dir + "/")]
    assert methods, r
    for m in methods:
        assert m["rpc"] in r["methods"], (cls, m["rpc"])   # impl really has it (incl. promoted)
        full = (m["package"] + "." if m["package"] else "") + svc_name
        e = {"id": f"{cls.split('.')[-1]}.{m['rpc']}", "class_name": cls, "method_name": m["rpc"],
             "param_types": [short(m["req"])], "return_type": short(m["resp"]), "protocol": "gRPC",
             "endpoint": f"/{full}/{m['rpc']}"}
        if (cls, m["rpc"]) in iface_by:  # same impl serving two gRPC services with the same rpc name
            raise SystemExit(f"collision {cls}.{m['rpc']}")
        ifaces.setdefault(svc, []).append(e); iface_by[(cls, m["rpc"])] = e
        e["_proto"] = (m["proto"], m["line"])

# ---------------- HTTP interfaces: wfe2 (ACME API) and sfe (self-service portal) ----------------
WFE_PATHS = {}
for m in re.finditer(r'^\s*(\w+Path)\s*=\s*"([^"]+)"', (CB / "wfe2/wfe.go").read_text(), re.M): WFE_PATHS[m[1]] = m[2]
routes = {}
for i, l in enumerate((CB / "wfe2/wfe.go").read_text().splitlines(), 1):
    m = re.search(r'wfe\.HandleFunc\(m, (\w+), wfe\.(\w+), (.+)\)', l)
    if m: routes.setdefault(m[2], []).append((" ".join(re.findall(r'"(\w+)"', m[3])), WFE_PATHS[m[1]], i))
    if 'm.Handle("/", web.NewTopHandler(wfe.log, web.WFEHandlerFunc(wfe.Index)))' in l: routes.setdefault("Index", []).append(("GET", "/", i))
sfe_src = (CB / "sfe/sfe.go").read_text()
SFE_C = {"unpause.GetForm": "/sfe/v1/unpause"}
for m in re.finditer(r'^\s*(unpause\w+|overrides\w+)\s*=\s*(\w+(?:\.\w+)?)\s*\+\s*"([^"]+)"', sfe_src, re.M):
    SFE_C[m[1]] = {"unpause.APIPrefix": "/sfe/v1", "overridesAPIPrefix": "/sfe/v1"}[m[2]] + m[3]
sroutes = {}
lines = sfe_src.splitlines()
for i, l in enumerate(lines, 1):
    m = re.search(r'sfe\.handle(Get|Post)\(mux, ("[^"]*"|[\w.]+), (?:http\.HandlerFunc\(sfe\.(\w+)\)|sfe\.(\w+)\()', l)
    if m:
        path = m[2].strip('"') if m[2].startswith('"') else SFE_C[m[2]]
        sroutes.setdefault(m[3] or m[4], []).append((m[1].upper(), path, i))
# GROUND_TRUTH_GUIDE.md: sfe only serves browser pages (UI-only service -> no interfaces); /healthz probes are excluded.
for svc, cls, rt in (("wfe2", "wfe2.WebFrontEndImpl", routes),):
    for meth, rs in rt.items():
        if meth == "Healthz": continue
        ifaces.setdefault(svc, []).append({"id": f"{cls.split('.')[-1]}.{meth}", "class_name": cls, "method_name": meth,
            "param_types": [], "return_type": "void", "protocol": "REST",
            "endpoint": " | ".join(f"{v.replace(' ', '|')} {p}" for v, p, _ in rs), "_route": rs})

# ---------------- calls ----------------
BIN = {"ca": "boulder-ca", "ra": "boulder-ra", "wfe2": "boulder-wfe2", "sfe": "sfe", "crl-updater": "crl-updater",
       "crl-storer": "crl-storer", "bad-key-revoker": "bad-key-revoker"}
# client type (as declared at the call site) -> (destination impl class, constructor used in the caller's main)
CLIENT = {
 "sa/proto.StorageAuthorityClient": ("sa.SQLStorageAuthority", "sapb.NewStorageAuthorityClient("),
 "sa/proto.StorageAuthorityCertificateClient": ("sa.SQLStorageAuthority", "sapb.NewStorageAuthorityClient("),
 "sa/proto.StorageAuthorityReadOnlyClient": ("sa.SQLStorageAuthorityRO", "sapb.NewStorageAuthorityReadOnlyClient("),
 "ra/proto.RegistrationAuthorityClient": ("ra.RegistrationAuthorityImpl", "rapb.NewRegistrationAuthorityClient("),
 "cmd/bad-key-revoker.revoker": ("ra.RegistrationAuthorityImpl", "rapb.NewRegistrationAuthorityClient("),
 "ra/proto.SCTProviderClient": ("ra.RegistrationAuthorityImpl", "rapb.NewSCTProviderClient("),
 "ca/proto.CertificateAuthorityClient": ("ca.certificateAuthorityImpl", "capb.NewCertificateAuthorityClient("),
 "ca/proto.CRLGeneratorClient": ("ca.crlImpl", "capb.NewCRLGeneratorClient("),
 "crl/storer/proto.CRLStorerClient": ("storer.crlStorer", "cspb.NewCRLStorerClient("),
 "va/proto.VAClient": ("va.ValidationAuthorityImpl", "vapb.NewVAClient("),
 "va/proto.CAAClient": ("va.ValidationAuthorityImpl", "vapb.NewCAAClient("),
 "mtca/proto.MTCAClient": ("mtca.mtca", "mtcapb.NewMTCAClient("),
 "mtcb/proto.MTCBClient": ("mtcb.mtcb", "mtcbpb.NewMTCBClient("),
 "salesforce/email/proto.ExporterClient": ("salesforce.ExporterImpl", "emailpb.NewExporterClient("),
 "nonce.Getter": ("nonce.NonceService", "nonce.NewGetter("),
 "nonce.Redeemer": ("nonce.NonceService", "nonce.NewRedeemer("),
}
calls = {}; excluded = []
def add(src_cls, src_meth, dst_cls, rpc, parts):
    d = iface_by[(dst_cls, rpc)]; key = (src_cls, src_meth, d["id"], svc_of[dst_cls])
    c = calls.setdefault(key, {"src_service": svc_of[src_cls], "src_class": src_cls, "src_method": src_meth,
                               "dst_service": svc_of[dst_cls], "dst_class": dst_cls, "dst_interface_id": d["id"],
                               "protocol": "gRPC", "_ev": []})
    pf, pl = d["_proto"]
    for p in parts + [ev(pf, pl, f"rpc {rpc}")]:
        if p not in c["_ev"]: c["_ev"].append(p)

for x in an["calls"]:
    if not x["caller_recv"].startswith(B):
        excluded.append((x, "caller outside boulder service code")); continue
    src_cls = pname(x["caller_recv"]); src_svc = svc_of.get(src_cls)
    callee = x["callee_type"].replace(B, "")
    if src_svc is None:
        excluded.append((x, "caller not in a service (CLI/test/library)")); continue
    dst_cls, ctor = CLIENT[callee]
    if svc_of[dst_cls] == src_svc:
        excluded.append((x, "same service (va -> remote va perspectives)")); continue
    snip = re.search(r"[\w.\[\]()]*\b%s\(" % x["method"], x["text"])[0]
    main = f"cmd/{BIN[src_svc]}/main.go"
    parts = [ev(x["file"], x["line"], snip), ev(main, find(main, ctor), ctor)]
    if callee in ("nonce.Getter", "nonce.Redeemer"):  # the wrappers build a noncepb client inside the nonce package
        fn = "func NewGetter(" if callee == "nonce.Getter" else "func NewRedeemer("
        parts.append(ev("nonce/nonce.go", find("nonce/nonce.go", "noncepb.NewNonceServiceClient(", find("nonce/nonce.go", fn)), "noncepb.NewNonceServiceClient("))
    add(src_cls, x["caller_func"], dst_cls, x["method"], parts)

# Library-mediated calls, attributed to the in-service caller (MS021 D1 rule).
pub_ctor = ev("cmd/boulder-ra/main.go", find("cmd/boulder-ra/main.go", "pubpb.NewPublisherClient("), "pubpb.NewPublisherClient(")
ctp = {x["caller_func"]: x for x in an["calls"] if x["caller_pkg"].endswith("/ctpolicy")}
for ra_meth, ctp_entry, inner in (("GetSCTs", "ra.ctpolicy.GetSCTs(", "getOne"), ("issueCertificateInner", "ra.ctpolicy.SubmitFinalCert(", "submitAllBestEffort")):
    site = next(x for x in an["library_callers"] if x["caller_func"] == ra_meth)
    lib = ctp[inner]
    add("ra.RegistrationAuthorityImpl", ra_meth, "publisher.Impl", "SubmitToSingleCTWithResult",
        [ev(site["file"], site["line"], ctp_entry), ev(lib["file"], lib["line"], "SubmitToSingleCTWithResult("), pub_ctor])
KB = [("ca.certificateAuthorityImpl", "IssueCertificate", "ca/ca.go", 236, "csrlib.VerifyCSR(", "sa.SQLStorageAuthority", "cmd/boulder-ca/main.go", "sa.KeyBlocked"),
      ("ra.RegistrationAuthorityImpl", "NewRegistration", "ra/ra.go", 505, "ra.keyPolicy.GoodKey(", "sa.SQLStorageAuthority", "cmd/boulder-ra/main.go", "sac.KeyBlocked"),
      ("ra.RegistrationAuthorityImpl", "validateFinalizeRequest", "ra/ra.go", 1078, "csrlib.VerifyCSR(", "sa.SQLStorageAuthority", "cmd/boulder-ra/main.go", "sac.KeyBlocked"),
      ("wfe2.WebFrontEndImpl", "validSelfAuthenticatedPOST", "wfe2/verify.go", 721, "wfe.keyPolicy.GoodKey(", "sa.SQLStorageAuthorityRO", "cmd/boulder-wfe2/main.go", "sac.KeyBlocked"),
      ("wfe2.WebFrontEndImpl", "validKeyRollover", "wfe2/verify.go", 779, "wfe.keyPolicy.GoodKey(", "sa.SQLStorageAuthorityRO", "cmd/boulder-wfe2/main.go", "sac.KeyBlocked")]
mv = {(x["file"], x["method"]) for x in an["method_values"]}
for src_cls, meth, f, ln, snip, dst, main, wire in KB:
    wl = find(main, wire); assert (main, "KeyBlocked") in mv
    extra = [ev("csr/csr.go", find("csr/csr.go", "keyPolicy.GoodKey("), "keyPolicy.GoodKey(")] if "VerifyCSR" in snip else []
    add(src_cls, meth, dst, "KeyBlocked", [ev(f, ln, snip)] + extra + [ev("goodkey/good_key.go", find("goodkey/good_key.go", "blockedCheck(ctx"), "blockedCheck(ctx"), ev(main, wl, wire)])

out_calls = []
for c in calls.values():
    c["evidence"] = " | ".join(c.pop("_ev")); out_calls.append(c)
for lst in ifaces.values():
    for e in lst: e.pop("_proto", None); e.pop("_route", None)
gt = {"system_id": "MS070", "extractor_tool": "ground_truth", "prompt_version": "v1.0", "status": "pending_manual_review",
      "microservices": {s: {"exposed_interfaces": ifaces.get(s, [])} for s in part}, "inter_service_calls": out_calls}
json.dump(gt, open("benchmarks/ground_truth/MS070.json", "w"), indent=2)

# Sites file for Gate C: every type-resolved gRPC client call / method value, and every served entry point.
sites = {"system_id": "MS070", "generated_by": "benchmarks/curation/MS070_analysis (go/packages, type-checked, 0 load errors)",
         "outbound": [{"path": x["file"], "line": x["line"], "what": x["callee_type"].replace(B, "") + "." + x["method"]}
                      for x in an["calls"] + an["method_values"] + an["library_callers"] if not x["file"].startswith("grpc/")],
         "entrypoints": [{"class": e["class_name"], "method": e["method_name"]} for lst in ifaces.values() for e in lst]}
json.dump(sites, open("benchmarks/curation/MS070.sites.json", "w"), indent=2)
from collections import Counter
print("interfaces:", {s: len(v) for s, v in ifaces.items()}, "total", sum(len(v) for v in ifaces.values()))
print("calls:", len(out_calls)); print(Counter((c["src_service"], c["dst_service"]) for c in out_calls))
print("excluded direct call sites:", Counter(r for _, r in excluded))
