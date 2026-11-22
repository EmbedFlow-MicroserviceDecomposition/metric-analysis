# Human Ground-Truth Curation Guide (`fyp-cdq`)

This guide explains how researchers (Anuja, Eshin, Ravishan, Yumeth) manually verify microservice boundaries and curate **ground-truth interface & inter-service call graphs** for the 20 calibration benchmark systems.

---

## Step 1: Audit `codebases/microservices/microservices.json` First

Before extracting interfaces or call edges, verify that the `"services"` object for your `<MS_ID>` in [`codebases/microservices/microservices.json`](../codebases/microservices/microservices.json) lists **only real, coded application microservices**.

### What to KEEP
- Deployable backend microservices (`orders`, `catalogue`, `cartservice`, `ftgo-order-service`, etc.).
- Coded BFF / API-composition gateways that implement application orchestration or aggregation logic in code (`spring-petclinic-api-gateway`, `ftgo-api-gateway`, `coolstore-gw`, `frontend`, `WebApp`).

### What to REMOVE from `microservices.json`
1. **Uncoded Backing Data Stores & DB Scripts** (Bucket A):
   - `mysql`, `mongodb` (or seed-script folders), `redis`, `elasticsearch`, SQL/Docker/LICENSE directories.
2. **Test Suites, Contract Harnesses & Load Generators** (Bucket B):
   - `*-tests`, `e2e`, `integration_tests`, `*-contracts`, `testutil`, `loadgenerator`.
3. **Shared Library / DTO / API-Spec Submodules & Internal Architecture Layers** (Bucket C):
   - Shared common libraries (`common`, `ftgo-common`, `EventBus`, `Shared`) or `*-api` DTO-only jars.
   - Internal DDD layer projects belonging to a single deployable service (unless merged, do not count them as separate microservices).
4. **Off-the-Shelf Infrastructure Plumbing & Pure Proxy Servers** (Bucket D):
   - 1-class Spring Boot `@Enable*` wrapper servers with 0 domain endpoints (`config-server`, `discovery-server` / `eureka` / `registry`, `admin-server`, `zipkin-service`, `monitoring`, `turbine`).
   - Pure reverse-proxy / YAML-only routing gateways with 1–2 boilerplate classes and zero domain/aggregation logic (`nginx`, Zuul / Spring Cloud Gateway proxy wrappers like `MS011/gateway`, `MS020/gateway`, `MS030/gateway-service`, `MS031/gateway-service`, `MS032/edge-service`).

> **Why this matters**: All 5 evaluation metrics (`NED`, `CHD`, `CHM`, `IFN`, `SM`) divide by $K$ (the service count). Leaving databases, test folders, DTO jars, or 1-class plumbing servers in `microservices.json` distorts $K$, penalizes `NED`, inflates `CHD`/`CHM`, and dilutes `IFN`/`SM`.

---

## Step 2: Populate `benchmarks/ground_truth/<MS_ID>.json`

An initial scaffold for each system already exists at `benchmarks/ground_truth/<MS_ID>.json` conforming to [`prompts/schema.json`](../prompts/schema.json). Inspect the source directories mapped in `microservices.json` and replace the scaffold entries with hand-verified truth.

### A. Root Metadata Fields
- `"system_id"`: `"MSxxx"`
- `"extractor_tool"`: `"ground_truth"`
- `"prompt_version"`: `"v1.0"`
- `"status"`: Flip `"pending_manual_review"` $\to$ **`"verified"`** once finished.
- `"microservices"`: MUST contain the **exact same set of keys** as `codebases/microservices/microservices.json[<MS_ID>]["services"]`.

### B. `exposed_interfaces` Rules (Used by `CHD` & `CHM`)
For each microservice `<service_id>`, extract **only operations exposed across the service boundary** to external callers:
1. **Include**:
   - **REST / HTTP handlers**: `@RestController`/`@Controller` endpoints, JAX-RS `@Path`, ASP.NET `[ApiController]`/Minimal API `MapGet`/`MapPost`, Go router handlers, Python FastAPI/Flask/Django routed views, Express/NestJS route handlers, AWS Lambda request handlers. *(Exclude commented-out routes and static asset handlers.)*
   - **gRPC / RPC operations**: Methods implementing `.proto` service contracts (`*ImplBase`, `*Servicer`, `Unimplemented*Server`, etc.).
   - **Async Message / Command Consumers**: Cross-service listeners (`@KafkaListener`, `@RabbitListener`, Eventuate Tram command/domain-event handlers, `IIntegrationEventHandler.Handle`, Celery `@shared_task`).
2. **Exclude**:
   - Implicit, health, debug status, and framework error-handler/meta endpoints (`/health`, `/_healthz`, `/metrics`, debug `IndexServlet` status pages, ASP.NET `UseExceptionHandler` error views like `CustomErrorController`).
   - Internal domain entities, DTOs, repositories/DAOs, configuration/DI wiring, internal private/helper methods, getters/setters, and `main()` entrypoints.
   - Services that only expose outbound UI/browser pages with no backend API (`"exposed_interfaces": []`).
3. **Identifier & Type Normalization**:
   - `"id"`: Unique **within that microservice**, formatted `"<SimpleClassName>.<method_name>"` (e.g., `"OwnerResource.findOwner"`). Disambiguate overloaded methods with a suffix (e.g., `"VisitResource.readByPetId"`, `"VisitResource.readByPetIds"`).
   - `"class_name"`: Exact declared FQN / module/file identifier from the source code (e.g., `"org.springframework.samples.petclinic.customers.web.OwnerResource"`, `"main.frontendServer"`, `"server.js"`).
   - `"param_types"` & `"return_type"`:
     - Unwrap async/transport wrappers (`ResponseEntity<T>`, `Optional<T>`, `Mono<T>`, `CompletableFuture<T>`, `Task<ActionResult<T>>` $\to$ `T`; `Flux<T>`, `IEnumerable<T>`, `Set<T>`, `T[]` $\to$ `List<T>`; empty response $\to$ `"void"`).
     - Omit framework context plumbing arguments (`HttpServletRequest`, `HttpServletResponse`, `BindingResult`, `Pageable`, `Principal`, `CancellationToken`, `ServerCallContext`, `context.Context`, `http.ResponseWriter`, `*http.Request`, `*gin.Context`).

### C. `inter_service_calls` Rules (Used by `IFN` & `SM`)
Record every directed call crossing a microservice boundary (**`src_service != dst_service`**):
1. **Supported Mechanisms**:
   - **REST / HTTP**: `WebClient`, `RestTemplate`, `RestClient`, `@FeignClient`, `@HttpExchange`, `HttpClient`, `axios`, `fetch`, `requests`, `http.Get`/`Post`.
   - **API Gateway Programmatic Calls**: Only programmatic inter-service calls in coded BFF/composition gateways (e.g., `CustomersServiceClient`, `OrderServiceProxy`). Do **not** explode declarative wildcard reverse-proxy rules (`/**` in Zuul / Spring Cloud Gateway YAML) into per-endpoint calls.
   - **gRPC / RPC**: Generated gRPC stub / client invocations mapped to the target service's implementing server method.
   - **Asynchronous Messaging**: Published domain events / commands / Celery `.delay()` calls mapped to every cross-service listener handling that event/command/task.
2. **Exclusions**:
   - Ignore unimplemented stub methods (e.g., throwing `UnsupportedOperationException`) unless real transport code backs them.
   - Ignore self-test scripts or standalone sample clients inside the same service (`src_service == dst_service`).
   - Ignore browser-side JavaScript `fetch()` calls originating from static frontend assets rather than server code.
   - Ignore infrastructure plumbing calls such as OAuth2 token introspection/validation middleware and background configuration reloaders.
3. **Referential Integrity & Evidence**:
   - `"dst_interface_id"` MUST exactly match an `"id"` inside `microservices[dst_service].exposed_interfaces`.
   - `"evidence"` MUST cite `"<relative_file>:<line> <concise_code_snippet>"`.

---

## Step 3: Validate Your Ground Truth Locally

Run the validator from the repository root after editing any `<MS_ID>.json`:

```bash
uv run python scripts/validate_extraction.py \
  --system <MS_ID> \
  --pred benchmarks/ground_truth/<MS_ID>.json
```

Confirm:
- `Schema`: **`PASS`** (all service keys match `microservices.json`, no duplicate interface IDs, all `dst_interface_id` references resolve).
- Inspect the computed `CHD`, `CHM`, `IFN`, `SM` scores in the output table (or run `uv run python scripts/run_eval.py <MS_ID> <metric> --extraction-path benchmarks/ground_truth/<MS_ID>.json`) for sanity.

---

## Step 4: Ground-Truth PR Contents

Open a branch (e.g., `gt/<your-name>-datasets`) from `main` and include **only**:
1. Your verified `benchmarks/ground_truth/<MS_ID>.json` files (`"status": "verified"`).
2. Updates to [`codebases/microservices/microservices.json`](../codebases/microservices/microservices.json) if you fixed service boundaries for your assigned systems.

Do **not** commit `outputs/`, temporary CSVs, or edits to `prompts/` or `src/` in a Ground-Truth PR.
