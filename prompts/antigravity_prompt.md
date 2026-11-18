# Microservice Interface & Inter-Service Call Extraction Prompt (`antigravity-cli` — Gemini Flash 3.8)

## Task Parameters
- **System ID**: `{{SYSTEM_ID}}`
- **Microservice Codebase Directory**: `{{CODEBASE_PATH}}`
- **Canonical Service Manifest**: `{{MANIFEST_PATH}}` (default: `codebases/microservices/microservices.json`)
- **Output Destination**: `{{OUTPUT_PATH}}`
- **Extractor Tool Identifier**: `"antigravity-cli"`
- **Prompt Version**: `"v1.0"`

---

## 1. Strict Context & Anti-Contamination Rules
1. You MUST ONLY read files inside `{{CODEBASE_PATH}}`, `{{MANIFEST_PATH}}` (for the `{{SYSTEM_ID}}` entry), and `prompts/schema.json`.
2. You are STRICTLY FORBIDDEN from reading `benchmarks/ground_truth/`, `benchmarks/GROUND_TRUTH_GUIDE.md`, `codebases/monoliths/`, `benchmarks/calibration_runs/`, or `outputs/`.
3. Every microservice ID (`microservices` keys, `src_service`, `dst_service`) MUST exactly match a key in `microservices.json["{{SYSTEM_ID}}"]["services"]` (no missing services, no invented services).
4. Every `class_name`, `src_class`, and `dst_class` MUST accurately reflect the declared fully qualified class name (or module/file identifier in dynamic languages) inside that service's directory.

---

## 2. Step-by-Step Extraction Workflow

### Step 1: Load the Canonical Service Directory Map
Read `{{MANIFEST_PATH}}` and extract the `"services"` map under `"{{SYSTEM_ID}}"`. Note each canonical `service_id` and its relative directory inside `{{CODEBASE_PATH}}`.

### Step 2: Identify Exposed Interfaces (`exposed_interfaces`) per Microservice
For each `(service_id, rel_dir)` in `{{MANIFEST_PATH}}["{{SYSTEM_ID}}"]["services"]`:
1. Inspect the source files inside `{{CODEBASE_PATH}}/<rel_dir>`.
2. Identify **published/exposed interface operations** that the microservice exposes across its boundary to external callers (other microservices, API gateways, or external clients):
   - **REST / HTTP Endpoints**:
     - *Java (Spring / JAX-RS / Micronaut / Quarkus)*: Methods in `@RestController`, `@Controller`, `@Path` classes annotated with `@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`, `@PatchMapping`, `@RequestMapping`, `@GET`, `@POST`, etc.
     - *C# (ASP.NET Core)*: Action methods in `[ApiController]` / `ControllerBase` subclasses (`[HttpGet]`, `[HttpPost]`, etc.) or Minimal API `MapGet`/`MapPost` handlers.
     - *Go*: HTTP handler methods/functions registered on routers (`gin`, `echo`, `chi`, `mux`, `net/http`).
     - *Python (FastAPI / Flask / Django / Nameko)*: Active (non-commented) route-decorated functions/methods (`@app.get`, `@router.post`, `@blueprint.route`, `APIView`/`ViewSet` actions).
     - *Node.js / TypeScript (Express / NestJS / Fastify)*: `@Controller` methods (`@Get`, `@Post`, `@MessagePattern`, `@EventPattern`) or `router.get`/`app.post` handlers.
   - **gRPC / RPC Services**:
     - Service implementation methods overriding generated gRPC servicer bases (`*ImplBase`, `Unimplemented*Server`, `*Servicer`, `@GrpcService`, `@GrpcMethod`).
   - **Asynchronous Message / Event Consumers**:
     - Methods handling cross-service events/commands (`@KafkaListener`, `@RabbitListener`, `@StreamListener`, Eventuate Tram command/event handlers, `IIntegrationEventHandler.Handle`, Celery `@shared_task`, RabbitMQ/NATS/AMQP consumers).
3. **Exclude Internal Classes & Plumbing**:
   - Do NOT include internal JPA/ORM entities, DTOs, repositories/DAOs, configuration classes, `main` bootstrap methods, `/health` probes, or internal helper/utility methods that are not service entrypoints.
   - If a microservice is a static frontend or worker with no inbound backend API operations exposed to other services, its `exposed_interfaces` array should be `[]`.
4. **Type Normalization Rules for `param_types` and `return_type`**:
   - **Unwrap transport/async wrappers**:
     - `ResponseEntity<Owner>`, `Optional<Owner>`, `Mono<Owner>`, `CompletableFuture<Owner>`, `Task<ActionResult<Owner>>`, `ActionResult<Owner>` $\to$ `"Owner"`.
     - `Flux<Visit>`, `IEnumerable<Visit>`, `Collection<Visit>`, `Visit[]` $\to$ `"List<Visit>"`.
     - `ResponseEntity<Void>`, `Mono<Void>`, `Task`, `IActionResult` (with no domain payload) $\to$ `"void"`.
   - **Exclude framework plumbing parameters** from `param_types`:
     - Omit `HttpServletRequest`, `HttpServletResponse`, `BindingResult`, `Model`, `Principal`, `Pageable`, `CancellationToken`, `ServerCallContext`, `context.Context`, `http.ResponseWriter`, `*http.Request`, `*gin.Context`.
   - Use simple domain type names (e.g., `"Owner"`, `"PetRequest"`, `"int"`, `"String"`, `"List<Visit>"`).
   - Format `id` as `"<SimpleClassName>.<method_name>"` (unique within the service; disambiguate overloaded methods).

### Step 3: Identify Inter-Service Call Edges (`inter_service_calls`)
Search across the service directories listed in `{{MANIFEST_PATH}}["{{SYSTEM_ID}}"]["services"]` for all cross-service communication mechanisms where a class in `src_service` invokes or sends a message to `dst_service` (`src_service != dst_service`):
1. **HTTP / REST Clients**:
   - `WebClient`, `RestTemplate`, `RestClient`, `@FeignClient`, `@HttpExchange`, `Retrofit`, `OkHttpClient`, `HttpClient` (C#/Java), `axios`, `fetch`, `requests`, `httpx`, `http.Get`/`http.Post`.
   - Resolve service discovery hostnames (e.g. `http://customers-service/owners/{ownerId}`, `http://vets-service/vets`) or configuration URL properties (`application.yml`, `bootstrap.yml`, `appsettings.json`, `docker-compose.yml`, `.env`) to the target `dst_service` and the target controller method (`dst_class`, `dst_interface_id`).
2. **API Gateway Programmatic Calls & Route Aggregators**:
   - If an API Gateway class programmatically calls downstream services or defines declarative `RouteLocator` routes, record each call edge from the gateway caller class to the downstream service's exposed interface.
3. **gRPC Stubs / RPC Clients**:
   - Match gRPC client stub calls (`*BlockingStub`, `*FutureStub`, `New*Client`) in `src_class` to the implementing gRPC server class (`dst_class`) and method (`dst_interface_id`) in `dst_service`.
4. **Asynchronous Messaging (Publish $\to$ Subscribe)**:
   - Match event/command publishers (`KafkaTemplate.send`, `RabbitTemplate.convertAndSend`, `DomainEventPublisher.publish`, `CommandProducer.send`, `EventBus.PublishAsync`, Celery `.delay()`) in `src_class` (`src_service`) to the corresponding event/command handler method (`dst_class`, `dst_interface_id`) in `dst_service`.

---

## 3. Output Format Requirements
Write the resulting JSON object to `{{OUTPUT_PATH}}` conforming strictly to `prompts/schema.json`:

```json
{
  "system_id": "{{SYSTEM_ID}}",
  "extractor_tool": "antigravity-cli",
  "prompt_version": "v1.0",
  "status": "verified",
  "microservices": {
    "<canonical_service_id>": {
      "exposed_interfaces": [
        {
          "id": "<SimpleClass>.<methodName>",
          "class_name": "<declared_class_or_module_name>",
          "method_name": "<methodName>",
          "param_types": ["<Type1>", "<Type2>"],
          "return_type": "<ReturnType>",
          "protocol": "REST | gRPC | Messaging | GraphQL | RPC | WebSocket",
          "endpoint": "<VERB /path or topic/Method>"
        }
      ]
    }
  },
  "inter_service_calls": [
    {
      "src_service": "<caller_service_id>",
      "src_class": "<declared_caller_class_or_module>",
      "src_method": "<caller_method_name>",
      "dst_service": "<callee_service_id>",
      "dst_class": "<declared_callee_class_or_module>",
      "dst_interface_id": "<SimpleCalleeClass>.<calleeMethodName>",
      "protocol": "REST | gRPC | Messaging | GraphQL | RPC | GatewayRoute",
      "evidence": "<concise code snippet or file:line showing the call>"
    }
  ]
}
```

### Final Self-Check Before Writing `{{OUTPUT_PATH}}`
- Every key in `"microservices"` matches `microservices.json["{{SYSTEM_ID}}"]["services"]` 1-to-1 (no missing services, no invented services).
- All `"id"` values inside each microservice's `exposed_interfaces` list are unique.
- Every `"dst_interface_id"` in `"inter_service_calls"` matches an `"id"` in `microservices[dst_service].exposed_interfaces`.
- No `"inter_service_calls"` entry has `src_service == dst_service`.
