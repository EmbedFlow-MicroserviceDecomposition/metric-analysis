# Microservice Interface & Inter-Service Call Extraction Prompt (`codex` — Codex Sol 6.1)

## Target Configuration
- `SYSTEM_ID`: `{{SYSTEM_ID}}`
- `CODEBASE_PATH`: `{{CODEBASE_PATH}}`
- `MANIFEST_PATH`: `{{MANIFEST_PATH}}` (default: `codebases/microservices/microservices.json`)
- `OUTPUT_PATH`: `{{OUTPUT_PATH}}`
- `extractor_tool`: `"codex"`
- `prompt_version`: `"v1.0"`

---

## 1. Hard Constraints
1. **Read Scope**: Only read `{{MANIFEST_PATH}}` (the `{{SYSTEM_ID}}` entry), `prompts/schema.json`, and files inside `{{CODEBASE_PATH}}`. Never access `benchmarks/ground_truth/`, `benchmarks/GROUND_TRUTH_GUIDE.md`, `codebases/monoliths/`, `benchmarks/calibration_runs/`, or `outputs/`.
2. **Canonical Service Identifiers**:
   - Every key in `"microservices"`, `"src_service"`, and `"dst_service"` MUST be an exact key from `microservices.json["{{SYSTEM_ID}}"]["services"]`.
   - Every `"class_name"`, `"src_class"`, and `"dst_class"` MUST reflect the declared class or module name in that service's source directory.

---

## 2. Extraction Rules

### Part 1: `microservices[service_id].exposed_interfaces`
For each `(service_id, rel_dir)` in `microservices.json["{{SYSTEM_ID}}"]["services"]`, inspect `{{CODEBASE_PATH}}/<rel_dir>` and extract all operations exposed to external callers:
- **Included Operations**:
  - HTTP/REST controller & router handlers (Spring `@GetMapping`/`@PostMapping`/`@PutMapping`/`@DeleteMapping`/`@RequestMapping`, JAX-RS `@Path`/`@GET`/`@POST`, ASP.NET `[HttpGet]`/`[HttpPost]`/`MapGet`, Go HTTP handlers, active Python FastAPI/Flask/Django routes, JS/TS Express/NestJS routes).
  - gRPC / RPC service implementation methods.
  - Cross-service message/event/command listener methods (`@KafkaListener`, `@RabbitListener`, Eventuate Tram handlers, RabbitMQ integration event handlers, Celery `@shared_task`).
- **Excluded Methods**:
  - Entities, DTOs, repositories/DAOs, configuration classes, `/health` probes, `main()` methods, constructors, getters/setters, and internal private/helper methods.
- **Type Formatting**:
  - Unwrap `ResponseEntity<T>`, `Optional<T>`, `Mono<T>`, `CompletableFuture<T>`, `Task<T>`, `ActionResult<T>` to `T`.
  - Normalize collection types (`Flux<T>`, `IEnumerable<T>`, `Set<T>`, `T[]`) to `List<T>`.
  - Remove framework context parameters (`HttpServletRequest`, `HttpServletResponse`, `BindingResult`, `Pageable`, `Principal`, `CancellationToken`, `ServerCallContext`, `context.Context`, `http.ResponseWriter`, `*http.Request`, `*gin.Context`).
  - Set `"id": "<SimpleClassName>.<method_name>"` (unique within the service).

### Part 2: `inter_service_calls`
Find all directed cross-service invocations (`src_service != dst_service`):
- Trace HTTP client calls (`WebClient`, `RestTemplate`, `@FeignClient`, `@HttpExchange`, `HttpClient`, `axios`, `fetch`, `requests`), gateway routes, gRPC client stub calls, and message/event producer calls from `src_class` (in `src_service`) to `dst_class` and `dst_interface_id` (in `dst_service`).
- Ensure every `"dst_interface_id"` matches an `"id"` declared in `microservices[dst_service].exposed_interfaces`.

---

## 3. Write & Validate Output
Write the JSON document to `{{OUTPUT_PATH}}` following `prompts/schema.json`.
