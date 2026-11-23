# Microservice Interface & Inter-Service Call Extraction Prompt (`antigravity-cli` — Gemini Flash 3.8)

## Task Parameters
- **System ID**: `{{SYSTEM_ID}}`
- **Microservice Codebase Directory**: `{{CODEBASE_PATH}}`
- **Canonical Service Manifest**: `{{MANIFEST_PATH}}` (default: `codebases/microservices/microservices.json`)
- **Output Destination**: `{{OUTPUT_PATH}}`
- **Extractor Tool Identifier**: `"antigravity-cli"`
- **Prompt Version**: `"v2.0"`

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
     - *Java (Spring / JAX-RS / Micronaut / Quarkus)*: Methods in `@RestController`, `@Controller`, `@Path` classes annotated with `@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`, `@PatchMapping`, `@RequestMapping`, `@GET`, `@POST`, etc. Also include Spring Data REST repository query methods inside interfaces annotated with `@RepositoryRestResource` (exposed automatically over HTTP without a controller).
     - *C# (ASP.NET Core)*: Action methods in `[ApiController]` / `ControllerBase` subclasses (`[HttpGet]`, `[HttpPost]`, etc.) or Minimal API `MapGet`/`MapPost` handlers.
     - *Go*: HTTP handler methods/functions registered on routers (`gin`, `echo`, `chi`, `mux`, `net/http`), including BFF/frontend servers handling business actions and client API/form submissions (`*Server`).
     - *Python (FastAPI / Flask / Django / Nameko)*: All active (non-commented) routed views mapped in `urls.py` (`path(...)`/`url(...)`) or decorator-routed handlers (`@app.get`, `@router.post`, `@blueprint.route`, `APIView`/`ViewSet` actions, and both class-based and function-based Django views).
     - *PHP (Symfony / Laravel)*: Controller action methods annotated with `@Route` / `#[Route]` or registered in framework routes.
     - *Node.js / TypeScript (Express / NestJS / Fastify / GraphQL)*: `@Controller` methods (`@Get`, `@Post`, `@MessagePattern`, `@EventPattern`), NestJS GraphQL `@Resolver` leaf query/mutation/field operations (`@Query`, `@Mutation`, `@ResolveField`), or Express `router.*`/`app.*` handlers. For **anonymous inline Express route callbacks** (`app.get('/cart/:id', (req, res) => ...)` or `app.get('/api/orders/:id', ...)`), set `class_name` to `"server.js"` (or the route filename), derive `method_name` in lowercase snake_case as `<http_verb>_<route_tokens>` (stripping a generic leading `/api` prefix and replacing `/` and `:param` colons with `_`, e.g., `GET /api/orders` $\to$ `get_orders`, `GET /api/orders/:id` $\to$ `get_orders_id`, `GET /cart/:id` $\to$ `get_cart_id`, `POST /shipping/:id` $\to$ `post_shipping_id`, `GET /add/:id/:sku/:qty` $\to$ `get_add_id_sku_qty`), and set `id` to `"server.<method_name>"`.
   - **gRPC / RPC Services**:
     - Include **all** declared service implementation methods overriding/implementing generated gRPC contracts (`*ImplBase`, `Unimplemented*Server`, `*Servicer`, `@GrpcService`, `@GrpcMethod`, and Go structs registered on a gRPC server), including unimplemented/placeholder RPC methods that satisfy the `.proto` interface contract.
     - In Go gRPC services where a server struct embeds another sub-struct (e.g., an RO/read-only implementation struct embedded in a composite server struct), attribute each RPC method to its concrete **declaring receiver struct** (`<pkg>.<DeclaringStruct>`) rather than re-attributing promoted methods.
   - **Asynchronous Message / Event Consumers**:
     - Methods handling cross-service events/commands (`@KafkaListener`, `@RabbitListener`, `@StreamListener`, Eventuate Tram command/domain-event handlers via `CommandHandlersBuilder.onMessage`/`DomainEventHandlersBuilder.forAggregateType`, C# `IIntegrationEventHandler.Handle` / `IMessageHandlerCallback.HandleMessageAsync`, active NestJS CQRS `@Saga()` handlers subscribed to cross-service EventStoreDB streams via `EventStoreModule.registerFeature`, Python Celery `@shared_task` / `@app.task`, and Go/Node RabbitMQ/AMQP consumer handlers—for a consumer loop inside Go `func main()`, use `class_name: "main"`, `method_name: "main"`, `id: "main.main"`).
3. **Exclude Internal Classes, Boilerplate, Client Stubs & Static SPAs**:
   - Do NOT include internal JPA/ORM entities, DTOs, plain repositories/DAOs (without `@RepositoryRestResource`), configuration classes, HTTP server `main()` bootstrap methods, worker lifecycle hooks (`StartAsync`/`StopAsync`), or internal helper/utility methods that are not service entrypoints.
   - Do NOT include outbound client interfaces/stubs (`@FeignClient`, Refit client interfaces, generated gRPC `*Client`/`*Stub` interfaces) in `exposed_interfaces`—they are outbound callers, not inbound endpoints.
   - Do NOT include implicit, health, readiness, metrics, profiler, fault-injection, build/status, scaffold boilerplate, or framework error/fallback endpoints (`/health`, `/healthz`, `/_healthz`, `/ready`, `ReadyRest`, gRPC `Health.Check`/`Watch`, `/metrics`, `/debug/*`, `/memory`, `/free`, `/oups`, `/build`, `/static/*`, `/robots.txt`, scaffold `AppController.getHello` (`GET /`), static welcome/greeting `GET /` handlers, debug status servlets like `IndexServlet`, framework exception-handler views like `CustomErrorController`/`UseExceptionHandler`, or circuit-breaker fallback handlers like `FallbackController`/`/fallback`).
   - Do NOT include empty NestJS GraphQL namespace-grouping resolvers that simply return `{}` (e.g., `@Mutation(() => ...) accessTokenMutation() { return {}; }`) or commented-out/no-op `@Saga()` methods whose queue/command body is commented out and only `return null`.
   - Client-side Single-Page Applications (React/Vue/Angular browser bundles served via `webpack`/`react-scripts`/`nginx`/`express.static`) and traditional OOP server-rendered MVC `View()` page/JSP controllers (`WebApp` Razor MVC, Java `HttpServlet` JSP frontends, auxiliary HTML self-service portals without API contracts) MUST have `"exposed_interfaces": []`. *(Traditional MVC backends still record their server-side outbound backend calls in `inter_service_calls`; browser SPAs do not—see Step 3.5.)*
4. **Type Normalization Rules for `param_types` and `return_type`**:
   - **Unwrap transport/async wrappers**:
     - `ResponseEntity<Owner>`, `Optional<Owner>`, `Mono<Owner>`, `CompletableFuture<Owner>`, `Task<ActionResult<Owner>>`, `ActionResult<Owner>` $\to$ `"Owner"`.
     - `Flux<Visit>`, `IEnumerable<Visit>`, `Collection<Visit>`, `Visit[]` $\to$ `"List<Visit>"`.
     - `ResponseEntity<Void>`, `Mono<Void>`, `Task`, `IActionResult` (with no domain payload) $\to$ `"void"`.
   - **Exclude framework plumbing parameters** from `param_types`:
     - Omit `HttpServletRequest`, `HttpServletResponse`, `BindingResult`, `Model`, `Principal`, `Pageable`, `CancellationToken`, `ServerCallContext`, `context.Context`, `http.ResponseWriter`, `*http.Request`, `*gin.Context`.
   - Use simple domain type names (e.g., `"Owner"`, `"PetRequest"`, `"int"`, `"String"`, `"List<Visit>"`).
   - Format `id` as `"<SimpleClassName>.<method_name>"` (unique within the service; disambiguate overloaded methods with a suffix, e.g. `"VisitResource.readByPetId"`).

### Step 3: Identify Inter-Service Call Edges (`inter_service_calls`)
Search across the service directories listed in `{{MANIFEST_PATH}}["{{SYSTEM_ID}}"]["services"]` for all cross-service communication mechanisms where a class in `src_service` invokes or sends a message to `dst_service` (`src_service != dst_service`):
1. **HTTP / REST Clients**:
   - `WebClient`, `RestTemplate`, `RestClient`, `@FeignClient`, `@HttpExchange`, `Retrofit`, `OkHttpClient`, `HttpClient` (C#/Java), Refit interfaces, server-side `axios`/`fetch`/`requests`/`httpx`/`http.Get`/`http.Post`.
   - Resolve service discovery hostnames (e.g. `http://customers-service/owners/{ownerId}`, `http://vets-service/vets`) or configuration URL properties (`application.yml`, `bootstrap.yml`, `appsettings.json`, `docker-compose.yml`, `.env`) to the target `dst_service` and the target controller/repository method (`dst_class`, `dst_interface_id`).
2. **API Gateway Programmatic Calls**:
   - Extract **only programmatic inter-service calls** in coded BFF/composition gateways (e.g., `CustomersServiceClient` in `api-gateway` calling `customers-service`).
   - Do **not** extract declarative reverse-proxy route rules (`GatewayRoute`, YAML Zuul / Spring Cloud Gateway routes, or fluent `.route(r -> r.path(...).uri(...))` proxy pass-throughs), and do **not** explode wildcard (`/**`) proxy routes into per-endpoint calls.
3. **gRPC Stubs / RPC Clients**:
   - Match gRPC client stub calls (`*BlockingStub`, `*FutureStub`, `New*Client`, `.svc.*` RPC clients) in `src_class` to the concrete implementing gRPC server struct/class (`dst_class`, `<pkg>.<DeclaringStruct>`) and method (`dst_interface_id`) in `dst_service`.
4. **Asynchronous Messaging (Publish $\to$ Subscribe)**:
   - Match active event/command publishers (`KafkaTemplate.send`, `RabbitTemplate.convertAndSend`, `DomainEventPublisher.publish`, `CommandProducer.send`, `EventBus.PublishAsync`, NestJS `eventBus.publish`, `PublishMessageAsync`, Celery `.delay()`) in `src_class` (`src_service`) to active cross-service consumer/handler methods (`dst_class`, `dst_interface_id`) in `dst_service`. Ignore events whose publisher or subscriber queue action is commented out.
5. **Exclusions & Evidence Format**:
   - **NEVER extract calls from client-side Single-Page Applications (SPAs)**: React/Vue/Angular browser apps (`react-scripts`, `webpack`, `src/store/*Service.js` browser `axios`/`fetch` bundles) execute in the user's browser, not as server-to-server calls, so SPA services MUST have `0` outgoing `inter_service_calls`.
   - Ignore unimplemented stub callers (e.g., throwing `UnsupportedOperationException`), self-calls (`src_service == dst_service`), external third-party API calls, and infrastructure plumbing calls (OAuth2 token introspection/validation middleware, authorization-guard RBAC/policy middleware calls such as `hasRights`/`addPolicy` in NestJS guards, service registry discovery/heartbeat calls such as `RegistryREST.getInstances`, and periodic background configuration or rate-limit reloaders).
   - Format `"evidence"` as `"<relative_file>:<line> <concise_code_snippet>"`.

---

## 3. Output Format Requirements
Write the resulting JSON object to `{{OUTPUT_PATH}}` conforming strictly to `prompts/schema.json`:

```json
{
  "system_id": "{{SYSTEM_ID}}",
  "extractor_tool": "antigravity-cli",
  "prompt_version": "v2.0",
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
