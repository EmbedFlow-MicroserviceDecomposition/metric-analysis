# MS070 static analysis (type-checked)

`main.go` loads every non-test boulder package with `golang.org/x/tools/go/packages` (full type checking,
vendored deps, cgo on) and reports, by type rather than by text:

- every call whose callee takes a trailing `...grpc.CallOption` (gRPC client calls, including through
  custom narrower interfaces), with the enclosing type and method;
- gRPC client methods passed as function values (e.g. `sac.KeyBlocked` handed to a library in `main()`);
- calls from service code into the call-making libraries `ctpolicy`, `goodkey.GoodKey`, `csr.VerifyCSR`;
- every gRPC server registration (`&X_ServiceDesc, impl`) with the implementing type and its method set.

`protos.py` lists every service and RPC declared in the `.proto` files.

Run (boulder at `cf6406d`, Go 1.27, no local Go needed):

    docker run --rm -e GOTOOLCHAIN=local -v <boulder>:/src:ro -v $PWD:/a -w /a golang:1.27 \
        sh -c 'go run . /src > out.json'
    python3 protos.py <boulder> rpcs.json

Result on 2026-11-18: 0 load errors, 115 direct gRPC call sites, 7 method values (5 boulder + 2 gRPC plumbing),
13 library invocations, 18 registrations. `../MS070.sites.json` is derived from this output and drives
Gate C for MS070.
