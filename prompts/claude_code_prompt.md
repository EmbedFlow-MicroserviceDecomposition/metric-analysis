# Microservice Interface & Inter-Service Call Extraction Prompt (`claude-code` — Claude Sonnet 5.5)

## Input Parameters
- `SYSTEM_ID`: `{{SYSTEM_ID}}`
- `CODEBASE_PATH`: `{{CODEBASE_PATH}}`
- `MANIFEST_PATH`: `{{MANIFEST_PATH}}` (default: `codebases/microservices/microservices.json`)
- `OUTPUT_PATH`: `{{OUTPUT_PATH}}`
- `extractor_tool`: `"claude-code"`
- `prompt_version`: `"v4.2"`
- `status`: `"pending_manual_review"`

This prompt is used on many systems written in many languages, with no answer key. Apply the **principles** below to whatever framework you meet; the framework lists are examples, not limits. Prefer evidence over guessing: record a record only when the source code shows it.

---

## 1. Scope & Firewall
- **Read only**: `{{CODEBASE_PATH}}`, `{{MANIFEST_PATH}}` (entry for `{{SYSTEM_ID}}`), `prompts/schema.json`.
- **Never read, list or search**: `benchmarks/`, `codebases/monoliths/`, `outputs/`, other systems' codebases, git history.
- **Write only** `{{OUTPUT_PATH}}`. If you write helper scripts, put them in a scratch/temp directory and prefix their names with `{{SYSTEM_ID}}`.
- **Canonical services**: the keys of `microservices.json["{{SYSTEM_ID}}"]["services"]` are the only service IDs. Every one of them appears in `microservices` (use `"exposed_interfaces": []` when it exposes nothing, its directory is missing, or it contains no application code). Never invent services; code outside the listed directories (shared libraries, tests, tooling, infra) is not a service.

---

## 2. Workflow (follow in order; it scales to systems with dozens of services)
1. **Inventory.** For each `(service_id, rel_dir)`, open `{{CODEBASE_PATH}}/<rel_dir>` and identify its language and framework from build files (`pom.xml`, `build.gradle(.kts)`, `package.json`, `go.mod`, `requirements.txt`/`pyproject.toml`, `*.csproj`, `Gemfile`, `composer.json`, `Cargo.toml`, `mix.exs`, `build.sbt`, `cpanfile`, `CMakeLists.txt`) and entry points.
2. **Build a name map.** Map every way other code can address each service to its `service_id`: directory name, container/compose service name, Kubernetes/Helm service name, discovery name (`spring.application.name`, Eureka/Consul IDs), env vars and config keys holding its URL/host/port, gRPC service names, queue/topic/exchange names it consumes.
3. **Exposed interfaces.** Search each service for the registration markers in §3 (grep first, then read the files), and record every eligible operation (§3–§5).
4. **Outbound calls.** Search each service for client calls and producers (§6), resolve each target with the name map, and match it to the exact exposed interface (verb + path, RPC method, or message type).
5. **Write and check.** Write the JSON (for large systems, generate it with a script), then run the checks in §7.

---

## 3. What Counts as an Exposed Interface
**Decision test** — record an operation when **all** hold:
1. It is a handler the framework or runtime invokes for traffic arriving **from outside the process**: an HTTP route, an RPC method, a GraphQL field resolver, a SOAP/WebSocket/hub method, or a consumer bound to a named queue/topic/channel/task.
2. It is **registered** (annotation/decorator, router table, route file, server registration, binding) in active code — not commented out.
3. It is not one of the exclusions in §4.

An operation counts even if no other service calls it, and even if its body is a placeholder (`NotImplemented`, returns `undefined`/`null`), as long as it is registered.

**Registration markers (examples by ecosystem)**
- **Java/Kotlin**: Spring `@RestController`/`@Controller` + `@*Mapping`; JAX-RS/Jersey/Dropwizard `@Path` + `@GET`…; Micronaut/Quarkus controllers; Spring Data REST interfaces annotated `@RepositoryRestResource` (each declared query method is an endpoint: `findById` → `/<path>/{id}`, custom finder → `/<path>/search/<method>`, `findAll` → `/<path>`; plain repositories without the annotation are not exposed); Vert.x/Camel/Spark/Javalin route registrations; Ktor `routing { get(...) }`; JAX-WS `@WebService`/`@WebMethod`; functional routers (`RouterFunctions.route(...)`) — the handler method is the interface.
- **C#**: `[ApiController]`/`ControllerBase` actions with `[Http*]`; Minimal API `Map*` (use the registering helper's name as `method_name` when the lambda is anonymous); gRPC `*Base` overrides; SignalR hub methods.
- **Go**: handlers registered on `net/http`, `gin`, `echo`, `chi`, `gorilla/mux`, `fiber`, `go-kit`, `twirp`; gRPC server structs registered with `Register*Server` (the struct exposes **every RPC of its service, including methods promoted from embedded structs**; list promoted methods under the embedding struct, and also under the embedded struct if it is separately registered for its own service).
- **Python**: Django `urls.py` + views/DRF `APIView`/`ViewSet`; Flask/FastAPI/aiohttp/Tornado/Sanic route decorators; Nameko `@rpc`/`@event_handler`; Celery tasks (see **Celery tasks** below); gRPC `*Servicer` methods.
- **Node.js/TypeScript**: Express/Koa/Hapi/Fastify `app|router.<verb>(...)`; NestJS `@Controller` + `@Get`…, `@MessagePattern`/`@EventPattern`, `@GrpcMethod`; GraphQL resolvers (`@Query`/`@Mutation`/`@ResolveField`, Apollo resolver maps); gRPC handlers passed to `server.addService`.
- **Ruby**: Rails `config/routes.rb` → `Controller#action` (`resources :users` expands to the actions the controller defines); Sinatra/Grape route blocks; Sidekiq/Sneakers/Karafka workers bound to queues.
- **PHP**: Laravel `routes/*.php` → controller methods; Symfony `@Route`/`#[Route]`; Slim/Lumen route registrations; queue job handlers.
- **Scala**: Play `conf/routes` → controller actions; Akka HTTP / Pekko / http4s / Finch route definitions; Akka/Alpakka consumers bound to topics.
- **Rust**: actix-web/axum/rocket/warp route attributes or router registrations; tonic gRPC trait impls.
- **Elixir**: Phoenix `router.ex` → `Controller.action`; Absinthe resolvers; Broadway/GenStage consumers.
- **Perl**: Mojolicious/Dancer/Catalyst route registrations.
- **C++ and others**: gRPC/Thrift service implementations, registered HTTP handlers.
- **Single entry-point dispatchers** (any language): one script/handler that switches on an `action`/`method`/`op`/`cmd` parameter, JSON-RPC method tables, `module/action` style RPC routers. Record one interface per dispatched action; `method_name` = the function that handles the action (or the action name if it is handled inline), `endpoint` = `"<VERB> <path>?<param>=<action>"` or the RPC method name. Do not expand generic CRUD-by-category parameters into hundreds of records.
- **Messaging consumers** (any language): `@KafkaListener`, `@RabbitListener`, `@StreamListener`/functional `Consumer` beans bound to destinations, Eventuate Tram handlers (one record per handler registered via `CommandHandlersBuilder.onMessage` / `DomainEventHandlersBuilder.onEvent`), `IIntegrationEventHandler.Handle` / `HandleMessageAsync` (record the one public entry point, not private per-event overloads), MassTransit/NServiceBus consumers, NATS/AMQP/SQS/SNS/Pub-Sub subscriber callbacks (a consumer loop inside Go `main()` → `class_name` `"main"`, `method_name` `"main"`), and NestJS CQRS `@Saga()`/EventStore handlers that react to events **published by another service**. A handler bound to a named channel counts even if the only current sender is in the same service.

**Celery tasks.** Every task registered in active, non-test code (`@shared_task`, `@app.task`, `@celery.task` or any alias of the app's task decorator, class-based `Task` subclasses that are registered, `app.register_task`) is an exposed interface of the service that **defines and runs** it, because a worker receives it through a broker. This holds even when only that same service enqueues it, when it is started only by Celery beat, or when no caller exists. Record one interface per task, not per call site or schedule entry: `class_name` = the module (or the task class), `method_name` = the function (`run` for a class-based task), `endpoint` = the registered task name (the explicit `name=` argument, else `<module>.<function>`), `param_types` = the task arguments without the bound `self`. A plain function that is never registered as a task is not one. An enqueue (`.delay()`, `.apply_async()`, `send_task`, `.s()`/`.si()` inside a dispatched chain/group/chord) is a call **only** when the task belongs to a different canonical service.

**Server-rendered pages.** Handlers in view-based MVC/servlet frameworks whose job is to return a page (ASP.NET MVC `View()`, Razor Pages, JSP, Thymeleaf/`ModelAndView`, `HttpServlet` `handleGET`/`handlePOST` forwarding to a page, identity-provider login/consent/logout UI flows) are **not** exposed interfaces; a service made only of these has `[]`. Handlers registered on a router in Go, Node.js, Python, Ruby, PHP, Rust, Elixir or Scala **are** exposed interfaces even when they render HTML (only §4 meta endpoints are dropped).

---

## 4. Exclusions
- Entities, DTOs, plain repositories/DAOs, configuration/DI wiring, `main()` bootstrap of servers, worker lifecycle hooks (`StartAsync`/`StopAsync`, `@PostConstruct`), getters/setters, constructors, private helpers.
- Outbound client stubs (`@FeignClient`, Refit, generated gRPC `*Client`/`*Stub`): callers, not exposed interfaces.
- **Meta endpoints** (but an endpoint that another canonical service calls in code is never a meta endpoint — a readiness/state/status endpoint polled by a sibling service is an interface): `/health`, `/healthz`, `/_healthz`, `/ready`, `/readiness`, `/live`, gRPC `Health.Check`/`Watch`, `/metrics`, `/debug/*`, profiling, `/memory`, `/free`, `/build`, `/version` banners, `/oups` and other fault injectors, `/robots.txt`, `/favicon.ico`, static-asset routes, scaffold `GET /` hello/banner handlers, debug status servlets, framework exception-handler/error views, circuit-breaker fallback handlers (`/fallback`).
- **Browser SPAs** (React/Vue/Angular/Svelte bundles served by `webpack`, `react-scripts`, `vite`, `nginx`, `express.static`, including a catch-all `GET /*` returning `index.html`): `[]`.
- Empty namespace-grouping GraphQL resolvers that only `return {}`; handlers whose body is commented out or a no-op (`return null` with the real work commented out); the unused duplicate when a real and a dummy/test implementation exist for one RPC.
- Purely in-process events (Spring `@EventListener`/`ApplicationEvent`, an event bus used only inside the service) and internal job queues (Bull/BullMQ `@Process`, in-process worker pools) whose producer and consumer are in the same service. **Celery tasks are not covered by this exclusion** (§3). An event bus that is **bridged to a broker or event store** (e.g. NestJS CQRS with `EventStoreModule`/stream subscriptions, Kafka/NATS/Redis/RabbitMQ transports, Axon, MassTransit) is cross-service messaging: its handlers that react to another service's events are exposed interfaces and the publishing handlers are callers.
- Test code, examples, benchmarks, load generators, migrations, scripts.

---

## 5. Signatures and Identifiers

### 5.1 Types (`param_types`, `return_type`)
- **Keep the source language's own spelling** of primitive and built-in types: Java `String`/`int`/`boolean`; Kotlin `String`/`Int`; C# `string`/`int`/`bool`/`decimal`/`Guid`; TypeScript `string`/`number`/`boolean`/`object`; Python `str`/`int`/`dict`/`list`; Go `string`/`int64`/`bool`; Rust `String`/`i64`; Ruby/PHP/Elixir/Perl (untyped) as below. Never translate one language's spelling into another's.
- **Unwrap transport/async containers**, recursively: `ResponseEntity<T>`, `Optional<T>`, `Mono<T>`, `CompletableFuture<T>`, `Task<T>`, `ValueTask<T>`, `ActionResult<T>`, `Promise<T>`, `Observable<T>`, `Future<T>`, `Result<T, E>` → `T`. `Flux<T>`, `Collection<T>`, `IEnumerable<T>`, `Set<T>`, `T[]`, server-streaming RPC results → `List<T>`. Keep other declared generic types as declared (`Map<K,V>`, `HashMap<K,V>`), written **without spaces** inside the brackets.
- **Framework response envelopes** (`IActionResult`, raw `ResponseEntity`, JAX-RS `Response`, DRF `Response`, `HttpResponse`, `JsonResponse`, Eventuate reply `Message`, `Result`): use the payload type the handler actually returns in the body (`Ok(new TransferResponse(...))` → `TransferResponse`, `Response(serializer.data)` → its serializer/model type or `dict`); with no body payload → `"void"`. Empty wrappers (`ResponseEntity<Void>`, `Mono<Void>`, `Task`, `NoContent()`) → `"void"`.
- **RPC/gRPC**: use the declared request/response message types exactly as named in code or the `.proto` (including `Empty`; do not turn `Empty` into `void` or drop an `Empty` parameter).
- **Framework request objects are not parameters**: drop `HttpServletRequest`/`HttpServletResponse`, `ServerRequest`, `HttpRequest`, `BindingResult`, `Model`, `Pageable`, `Principal`, `CancellationToken`, `ServerCallContext`, `context.Context`, `http.ResponseWriter`, `*http.Request`, `*gin.Context`, `echo.Context`, Express/Koa `req`/`res`/`ctx`/`next`, Flask/Django `request`, Vert.x `RoutingContext`, Lambda event/context objects, Rails `params`. **Instead list the domain inputs the handler reads from them**, in order: path and query values (their declared/parsed type; `string` in untyped languages unless parsed to a number), then the request body (its DTO/serializer/model type; `object` in untyped languages when no type is evident).
- **Untyped languages** (JavaScript, Python without hints, Ruby, PHP, Elixir, Perl): path/query values → `string` (or the number type they are parsed to); body → the model/serializer/schema class if one is used, else `object`. For the return type, name the domain entity when the code makes it evident (a model/serializer/schema class, or a collection whose records are clearly one entity: `res.json(orders)` from an `orders` store → `List<Order>`, one of them → `Order`); otherwise `string` for plain text, `object` for unidentified JSON, `"void"` when nothing is returned.
- Messaging handlers: use the payload type `T` (not `CommandMessage<T>` / `DomainEventEnvelope<T>`); return the declared domain type, or `"void"` when the handler only acknowledges or replies with a framework message.

### 5.2 Identifiers
- `class_name`: the declaring class / FQN / struct (`<pkg>.<Struct>` in Go) / module. For handlers that are plain functions, use the module or file identifier (`views`, `tasks`, `server.js`, `payment`). In plain Node.js (not NestJS), a handler that is a method of a helper class defined inside the server/route file still uses the file (`server.js`, id `server.<method>`). gRPC/RPC implementations are often **nested or inner classes**; search all files for `*ImplBase`/`*Servicer`/`Unimplemented*Server` including inner classes.
- `method_name`: the declared method/function name (Rails/Phoenix/Laravel: the controller action).
- `id`: `"<SimpleClassName>.<method_name>"`, unique within the service; disambiguate same-name methods (overloads, API versions, one handler per verb) by appending a short descriptive suffix **directly to the method part, never with an extra dot** (`VisitResource.readByPetId`, `AccountsController.GetV2`, `WebFrontEndImpl.CertificatePost`).
- **Anonymous inline route callbacks** (e.g. Express `app.get('/cart/:id', (req, res) => ...)`): `class_name` = the route file (`server.js`), `method_name` = lowercase snake_case `<verb>_<route_tokens>` (drop a leading generic `/api`, replace `/` and `:` with `_`: `GET /api/orders/:id` → `get_orders_id`, `POST /shipping/:id` → `post_shipping_id`), `id` = `"server.<method_name>"`. Apply the same pattern to anonymous handlers in any language; never invent camelCase names.
- `endpoint`: `"<VERB> <full path>"` for HTTP (combine router/class/method path segments; omit deployment context paths), `Service/Method` for RPC, the queue/topic/exchange/event type for messaging.

---

## 6. Inter-Service Call Edges (`inter_service_calls`)
Record every call where code running in `src_service` invokes an exposed interface of another service (`src_service != dst_service`).

1. **Synchronous HTTP**: `WebClient`, `RestTemplate`, `RestClient`, `@FeignClient`, `@HttpExchange`, `HttpClient`, Refit, OkHttp/Retrofit, server-side `axios`/`fetch`/`got`/`superagent`/`request`, Python `requests`/`httpx`/`aiohttp`, Go `http.Get`/`Post`/`Do`, Ruby `Net::HTTP`/Faraday/HTTParty, PHP Guzzle/curl, Rust `reqwest`, Elixir `HTTPoison`/`Tesla`/`Req`, programmatic clients in coded BFF/composition gateways. Resolve the URL (literal, config, env var, discovery name) through the name map, then match **verb + path** to one exposed interface (path parameters match any value; tolerate a leading context path or `/api` prefix difference when the rest is unambiguous).
2. **RPC/gRPC/Thrift**: match each client-stub call to the server class registered for **that stub's service type**, and its method. A client of the full service resolves to the struct registered for the full service (including promoted methods); a read-only client type resolves to the read-only struct.
3. **Messaging**: match each publisher (`KafkaTemplate.send`, `RabbitTemplate.convertAndSend`, `StreamBridge.send`, `DomainEventPublisher.publish`, `CommandProducer.send`, `EventBus.PublishAsync`, `eventBus.publish`, `IPublishEndpoint.Publish`, Celery `.delay()`/`.apply_async()`/direct task call across services, AMQP/NATS/SQS/SNS publish) to **every** active cross-service consumer of the same topic/queue/exchange/event type. One edge per distinct publisher method and consumer interface.
4. **`src_class` / `src_method`**: the class and method **inside the src service's directory** whose code performs the invocation.
   - Declarative clients (`@FeignClient`, Refit interfaces) have no invocation code: use the class/method that calls the client method. A wrapper class that only delegates to a declarative proxy (e.g. holds `RestService.For<IX>()` or a Feign client and forwards to it) is part of the declarative client: go one level up to the class that calls the wrapper.
   - A concrete class that itself builds the request with an HTTP client library is its own `src_class`.
   - If the network call happens inside shared-library code outside the service directories (for example a common client/load-balancer package or a library that receives a callback), attribute it to the service-owned class and method that invoke that library code. Record one edge per distinct (calling class, calling method, target interface): do not merge calls from different calling classes or to different target interfaces into one edge.
   - `dst_class` = the `class_name` of the target interface.
5. **Do NOT record**:
   - Declarative reverse-proxy / gateway route rules (`GatewayRoute`, Zuul / Spring Cloud Gateway YAML, fluent `.route(r -> r.path(...).uri(...))`, nginx/Envoy/Traefik config, `proxy_pass`) and wildcard (`/**`) routes.
   - Browser-side code (SPA bundles, static frontend `fetch`/`axios`).
   - Infrastructure plumbing: service-registry registration/heartbeat/discovery (Eureka, Consul, `register`/`unregister`/`getInstances`), tracing/metrics exporters, config servers and reloaders, OAuth2/OIDC token introspection, JWT middleware, and authorization-guard / RBAC / policy calls (`hasRights`, `addPolicy`, `checkPermission`) whether made from a guard, middleware or a registration hook.
   - Same-service calls, calls to external third-party APIs or databases/caches, unimplemented stubs, commented-out code, and any call whose target operation you cannot identify among the canonical services' exposed interfaces. When unsure about the exact target, leave the edge out and mention it in your final reply; never fabricate a target.
6. **Evidence**: `"<file path relative to CODEBASE_PATH>:<line> <short code snippet>"`, citing the caller's line (the line must exist and contain the snippet); optionally append ` -> <target file>:<line>`.

---

## 7. Output & Self-Check
Write `{{OUTPUT_PATH}}` conforming to `prompts/schema.json`, with `"system_id": "{{SYSTEM_ID}}"`, `"extractor_tool": "claude-code"`, `"prompt_version": "v4.2"`, `"status": "pending_manual_review"`, and no extra fields. Always write a valid file, even if some services could not be fully analyzed (record what is supported).

Before finishing, run a script that verifies:
1. `microservices` keys equal the manifest's service keys exactly.
2. Interface `id`s are unique per service; every `dst_interface_id` exists in `microservices[dst_service].exposed_interfaces` and `dst_class` equals that interface's `class_name`.
3. `src_service != dst_service`; no duplicate calls (same `src_service`, `src_class`, `src_method`, `dst_service`, `dst_interface_id`).
4. Every evidence path exists and its line contains (or is within 3 lines of) the cited snippet.
5. **Coverage review**: for each service, compare the number of registration markers you found (routes, RPC methods, consumers) with the number of interfaces recorded, and the number of outbound client call sites with the number of edges recorded; re-inspect any service where they differ without a §4 reason.

In your final reply, report interface counts per service, the call count, and any unresolved or ambiguous items (as names only).
