"""Mutation tests for scripts/verify_ground_truth.py.

Each case breaks one of the verified ground truths in a specific way and checks that the named gate
reports it. A gate that cannot detect these is not evidence of correctness.

    uv run python benchmarks/curation/mutation_tests.py
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from verify_ground_truth import CURATION_DIR, gate_a, gate_b, gate_c  # noqa: E402

from fyp_cdq.config import GROUND_TRUTH_DIR, OUTPUTS_DIR  # noqa: E402
from fyp_cdq.models import Partition  # noqa: E402
from fyp_cdq.pipeline import resolve_system_codebase  # noqa: E402

_cache = {}
results = []


def load(sid):
    if sid not in _cache:
        _, ms = resolve_system_codebase(sid)
        part = Partition.from_json(OUTPUTS_DIR / sid / "output.json")
        gt = json.loads((GROUND_TRUTH_DIR / f"{sid}.json").read_text())
        ex_file = CURATION_DIR / f"{sid}.exclusions.json"
        ex = json.loads(ex_file.read_text()) if ex_file.exists() else {}
        _cache[sid] = (ms, part, gt, ex)
    return _cache[sid]


def mut(sid, desc, fn, gate):
    ms, part, gt, ex = load(sid)
    g = copy.deepcopy(gt)
    fn(g)
    if gate == "A":
        n = len(gate_a(g, part))
    elif gate == "B":
        n = len(gate_b(g, ms)[0])
    else:
        n = len(gate_c(g, ms, gate_b(g, ms)[1], ex))
    results.append(bool(n))
    print(f"{'CAUGHT' if n else 'MISSED'}  {sid} gate {gate}: {desc}")


def ifs(g, svc):
    return g["microservices"][svc]["exposed_interfaces"]


def calls(g):
    return g["inter_service_calls"]


def drop_iface(svc, pred):
    def f(g):
        lst = ifs(g, svc)
        lst.pop(next(i for i, e in enumerate(lst) if pred(e)))
    return f


def drop_call(pred):
    def f(g):
        lst = calls(g)
        lst.pop(next(i for i, c in enumerate(lst) if pred(c)))
    return f


# MS032: REST + Kafka
mut("MS032", "short class name", lambda g: calls(g)[0].__setitem__("dst_class", "UserController"), "A")
mut("MS032", "call under wrong service", lambda g: calls(g)[0].__setitem__("dst_service", "recommendation-service"), "A")
mut("MS032", "unknown dst interface", lambda g: calls(g)[0].__setitem__("dst_interface_id", "UserController.deleteUser"), "A")
mut("MS032", "evidence line off by one", lambda g: calls(g)[1].__setitem__("evidence", calls(g)[1]["evidence"].replace(":55 ", ":56 ")), "B")
mut("MS032", "fabricated snippet", lambda g: calls(g)[0].__setitem__("evidence", "friend-service/src/main/java/io/example/domain/user/UserClient.java:22 `restTemplate.getForObject(url)`"), "B")
mut("MS032", "Kafka call deleted", drop_call(lambda c: c["protocol"] == "Messaging" and c["src_method"] == "removeFriend"), "C")
mut("MS032", "REST call to user-service deleted", drop_call(lambda c: c["dst_service"] == "user-service"), "C")
mut("MS032", "Kafka handler deleted", drop_iface("recommendation-service", lambda e: e["id"] == "FriendProcessor.apply"), "C")
# MS020: Feign
mut("MS020", "Feign call to statistics deleted", drop_call(lambda c: c["dst_service"] == "statistics-service"), "C")
mut("MS020", "controller endpoint deleted", drop_iface("account-service", lambda e: e["id"] == "AccountController.getCurrentAccount"), "C")
# MS078: ASP.NET
mut("MS078", "two Get endpoints share an id", lambda g: ifs(g, "accounts-api")[2].__setitem__("id", "V1.Accounts.GetAccount.AccountsController.Get"), "A")
mut("MS078", "made-up id prefix", lambda g: ifs(g, "accounts-api")[0].__setitem__("id", "Foo.AccountsController.Close"), "A")
mut("MS078", "Close endpoint deleted", drop_iface("accounts-api", lambda e: e["id"] == "AccountsController.Close"), "C")
mut("MS078", "Transfer (behind #pragma) deleted", drop_iface("accounts-api", lambda e: e["id"] == "TransactionsController.Transfer"), "C")
# MS021: shared client library, inherited endpoints, overloads
P21 = "services/tools.descartes.teastore.persistence"
mut("MS021", "inherited ProductEndpoint.findById deleted", drop_iface(P21, lambda e: e["id"] == "ProductEndpoint.findById"), "C")
mut("MS021", "inherited CategoryEndpoint.listAll deleted", drop_iface(P21, lambda e: e["id"] == "CategoryEndpoint.listAll"), "C")
mut("MS021", "UserEndpoint.findById(String) overload deleted", drop_iface(P21, lambda e: e["id"] == "UserEndpoint.findById(String)"), "C")
mut("MS021", "recommender TrainEndpoint.train deleted", drop_iface("services/tools.descartes.teastore.recommender", lambda e: e["id"] == "TrainEndpoint.train"), "C")
mut("MS021", "webui ProductServlet -> recommender call deleted", drop_call(lambda c: c["src_class"].endswith("ProductServlet") and "recommender" in c["dst_service"]), "C")
mut("MS021", "auth -> persistence order creation deleted", drop_call(lambda c: c["src_method"] == "placeOrder" and c["dst_interface_id"] == "OrderEndpoint.create"), "C")
mut("MS021", "image SetupController inline call deleted", drop_call(lambda c: c["src_method"] == "fetchCategories"), "C")
mut("MS021", "call attributed to library class", lambda g: calls(g)[0].__setitem__("src_class", "tools.descartes.teastore.registryclient.rest.LoadBalancedCRUDOperations"), "A")
# MS070: Go/gRPC (type-checked sites file)
mut("MS070", "wfe2 -> ra NewOrder call deleted", drop_call(lambda c: c["src_class"] == "wfe2.WebFrontEndImpl" and c["dst_interface_id"] == "RegistrationAuthorityImpl.NewOrder"), "C")
mut("MS070", "library-mediated ra -> publisher call deleted", drop_call(lambda c: c["dst_service"] == "publisher" and c["src_method"] == "GetSCTs"), "C")
mut("MS070", "key-policy wfe2 -> sa KeyBlocked deleted", drop_call(lambda c: c["dst_interface_id"] == "SQLStorageAuthorityRO.KeyBlocked" and c["src_method"] == "validKeyRollover"), "C")
mut("MS070", "served RPC SQLStorageAuthorityRO.GetRegistration deleted", drop_iface("sa", lambda e: e["id"] == "SQLStorageAuthorityRO.GetRegistration"), "C")
mut("MS070", "wfe2 HTTP handler NewAccount deleted", drop_iface("wfe2", lambda e: e["id"] == "WebFrontEndImpl.NewAccount"), "C")
mut("MS070", "RO call misattributed to the full SA type", lambda g: [c.__setitem__("dst_class", "sa.SQLStorageAuthority") for c in calls(g) if c["dst_class"] == "sa.SQLStorageAuthorityRO"][:1], "A")
mut("MS070", "caller class from a CLI (admin.admin)", lambda g: calls(g)[0].__setitem__("src_class", "admin.admin"), "A")

print(f"\n{sum(results)}/{len(results)} mutations caught")
sys.exit(0 if all(results) else 1)
