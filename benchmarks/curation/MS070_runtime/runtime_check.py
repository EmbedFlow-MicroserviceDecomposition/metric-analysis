#!/usr/bin/env python3
"""Runtime-check wrapper (scratchpad copy only): same steps as test/integration-test.py --chisel --gotest,
but the metrics scrape always runs, even if a test fails, and the outcome of each phase is recorded."""
import importlib.util, json, subprocess, sys, time, traceback
sys.path.insert(0, "test")
spec = importlib.util.spec_from_file_location("it", "test/integration-test.py"); it = importlib.util.module_from_spec(spec); spec.loader.exec_module(it)
import startservers
log = {}
def phase(name, fn):
    t = time.time()
    try: fn(); log[name] = {"ok": True}
    except BaseException as e: log[name] = {"ok": False, "error": repr(e)[:500]}; traceback.print_exc()
    log[name]["seconds"] = round(time.time() - t)
    print(f"=== PHASE {name}: {log[name]}", flush=True)
phase("install", lambda: startservers.install(race_detection=False) or (_ for _ in ()).throw(Exception("build failed")))
phase("start", lambda: startservers.start(coverage_dir=None) or (_ for _ in ()).throw(Exception("startservers failed")))
if log["start"]["ok"]:
    phase("chisel", lambda: it.run_chisel(""))
    phase("gotest", lambda: it.run_go_tests("", False))
    phase("scrape", lambda: subprocess.run(["python3", "scrape_metrics.py"], check=True))
json.dump(log, open("/boulder/runtime_phases.json", "w"), indent=1)
startservers.stop() if hasattr(startservers, "stop") else None
