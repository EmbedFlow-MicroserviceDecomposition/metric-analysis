# Agent Extraction Validation Report

## 1. Aggregate Summary
- **Systems Evaluated**: 15
- **Schema & Partition Conformance**: 15/15 (100.0%)
- **Macro Interface Identification F1**: `0.7683` (Signature F1: `0.6038`)
- **Macro Inter-Service Class Edge F1 (SM)**: `0.7528`
- **Macro Inter-Service Interface Call F1 (IFN)**: `0.7683`

## 2. Per-System Breakdown

| System | Schema | GT Ifaces | Pred Ifaces | Iface F1 | Class Edge F1 | Iface Call F1 | ΔCHD | ΔCHM | ΔIFN | ΔSM |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `MS001` | PASS | 13 | 14 | `0.9630` | `1.0000` | `1.0000` | 0.2000 | 0.2000 | 0.0000 | 0.0000 |
| `MS004` | PASS | 56 | 53 | `0.9725` | `0.9231` | `0.9492` | 0.0379 | 0.1027 | 0.3333 | 0.0001 |
| `MS010` | PASS | 7 | 3 | `0.2000` | `0.0000` | `0.0000` | 0.0821 | 0.4000 | 0.2000 | 0.0003 |
| `MS016` | PASS | 18 | 18 | `1.0000` | `0.7907` | `0.9811` | 0.0000 | 0.0000 | 0.1111 | 0.0000 |
| `MS017` | PASS | 4 | 4 | `0.0000` | `1.0000` | `1.0000` | 0.2333 | 0.0000 | 0.0000 | 0.0000 |
| `MS020` | PASS | 11 | 11 | `1.0000` | `0.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS021` | PASS | 58 | 72 | `0.8923` | `0.9444` | `0.8649` | 0.0982 | 0.2408 | 0.3333 | 0.0017 |
| `MS031` | PASS | 16 | 16 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS032` | PASS | 11 | 11 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0278 | 0.0000 | 0.0000 |
| `MS039` | PASS | 27 | 27 | `0.9630` | `0.8966` | `0.9268` | 0.0000 | 0.0000 | 0.0909 | 0.0002 |
| `MS047` | PASS | 28 | 32 | `0.2333` | `0.8333` | `0.0000` | 0.1909 | 0.2050 | 0.0000 | 0.0000 |
| `MS070` | PASS | 125 | 106 | `0.8485` | `0.9524` | `0.8212` | 0.0440 | 0.0142 | 0.4706 | 0.0000 |
| `MS078` | PASS | 6 | 17 | `0.5217` | `0.0000` | `0.0000` | 0.3082 | 0.1227 | 2.3333 | 0.0003 |
| `MS098` | PASS | 128 | 147 | `0.9309` | `0.9508` | `0.9811` | 0.0921 | 0.0167 | 0.2222 | 0.0000 |
| `MS106` | PASS | 28 | 28 | `1.0000` | `1.0000` | `1.0000` | 0.0113 | 0.0051 | 0.0000 | 0.0000 |

## 3. Diagnostic Error Analysis (False Positives & False Negatives)

### `MS001`
- **Interface False Positives (1)**:
  - `('spring-petclinic-api-gateway', 'fallbackcontroller', 'fallback')`

### `MS004`
- **Interface False Negatives (3)**:
  - `('ftgo-order-service', 'orderserviceimpl', 'cancelOrder')`
  - `('ftgo-order-service', 'orderserviceimpl', 'createOrder')`
  - `('ftgo-order-service', 'orderserviceimpl', 'reviseOrder')`
- **Inter-Service Call False Positives (3)**:
  - `('ftgo-api-gateway', 'ftgo-consumer-service', 'consumercontroller.create')`
  - `('ftgo-api-gateway', 'ftgo-order-history-service', 'orderhistorycontroller.getorders')`
  - `('ftgo-api-gateway', 'ftgo-order-service', 'ordercontroller.create')`

### `MS010`
- **Interface False Positives (2)**:
  - `('spring-petclinic-rest-system', 'applicationcontroller', 'home')`
  - `('spring-petclinic-rest-system', 'crashcontroller', 'triggerException')`
- **Interface False Negatives (6)**:
  - `('spring-petclinic-rest-owner', 'ownerrepository', 'findById')`
  - `('spring-petclinic-rest-owner', 'ownerrepository', 'findByLastName')`
  - `('spring-petclinic-rest-pet', 'petrepository', 'findById')`
  - `('spring-petclinic-rest-pet', 'petrepository', 'findPetTypes')`
  - `('spring-petclinic-rest-vet', 'vetrepository', 'findAll')`
  - `('spring-petclinic-rest-visit', 'visitrepository', 'findByPetId')`
- **Inter-Service Call False Negatives (1)**:
  - `('spring-petclinic-rest-owner', 'spring-petclinic-rest-pet', 'petrepository.findbyid')`

### `MS016`
- **Inter-Service Call False Positives (1)**:
  - `('WebApp', 'WorkshopManagementAPI', 'refdatacontroller.getcustomers')`

### `MS017`
- **Interface False Positives (4)**:
  - `('orders', 'server', 'getOrderById')`
  - `('orders', 'server', 'getOrders')`
  - `('products', 'server', 'getProductById')`
  - `('products', 'server', 'getProducts')`
- **Interface False Negatives (4)**:
  - `('orders', 'server', 'get_orders')`
  - `('orders', 'server', 'get_orders_id')`
  - `('products', 'server', 'get_products')`
  - `('products', 'server', 'get_products_id')`

### `MS020`: Perfect Match (0 Errors)

### `MS021`
- **Interface False Positives (14)**:
  - `('services/tools.descartes.teastore.webui', 'aboutusservlet', 'handleGETRequest')`
  - `('services/tools.descartes.teastore.webui', 'cartactionservlet', 'handleGETRequest')`
  - `('services/tools.descartes.teastore.webui', 'cartservlet', 'handleGETRequest')`
  - `('services/tools.descartes.teastore.webui', 'categoryservlet', 'handleGETRequest')`
  - `('services/tools.descartes.teastore.webui', 'categoryservlet', 'handlePOSTRequest')`
  - `('services/tools.descartes.teastore.webui', 'databaseactionservlet', 'handleGETRequest')`
  - `('services/tools.descartes.teastore.webui', 'databaseservlet', 'handleGETRequest')`
  - `('services/tools.descartes.teastore.webui', 'loginactionservlet', 'handleGETRequest')`
  - `('services/tools.descartes.teastore.webui', 'loginactionservlet', 'handlePOSTRequest')`
  - `('services/tools.descartes.teastore.webui', 'loginservlet', 'handleGETRequest')`
- **Inter-Service Call False Positives (10)**:
  - `('services/tools.descartes.teastore.auth', 'services/tools.descartes.teastore.registry', 'registryrest.register')`
  - `('services/tools.descartes.teastore.auth', 'services/tools.descartes.teastore.registry', 'registryrest.unregister')`
  - `('services/tools.descartes.teastore.image', 'services/tools.descartes.teastore.registry', 'registryrest.register')`
  - `('services/tools.descartes.teastore.image', 'services/tools.descartes.teastore.registry', 'registryrest.unregister')`
  - `('services/tools.descartes.teastore.persistence', 'services/tools.descartes.teastore.registry', 'registryrest.register')`
  - `('services/tools.descartes.teastore.persistence', 'services/tools.descartes.teastore.registry', 'registryrest.unregister')`
  - `('services/tools.descartes.teastore.recommender', 'services/tools.descartes.teastore.registry', 'registryrest.register')`
  - `('services/tools.descartes.teastore.recommender', 'services/tools.descartes.teastore.registry', 'registryrest.unregister')`
  - `('services/tools.descartes.teastore.webui', 'services/tools.descartes.teastore.registry', 'registryrest.register')`
  - `('services/tools.descartes.teastore.webui', 'services/tools.descartes.teastore.registry', 'registryrest.unregister')`

### `MS031`: Perfect Match (0 Errors)

### `MS032`: Perfect Match (0 Errors)

### `MS039`
- **Interface False Positives (1)**:
  - `('paymentservice', 'hipstershopserver', 'ChargeServiceHandler')`
- **Interface False Negatives (1)**:
  - `('paymentservice', 'server', 'ChargeServiceHandler')`
- **Inter-Service Call False Positives (1)**:
  - `('checkoutservice', 'paymentservice', 'hipstershopserver.chargeservicehandler')`
- **Inter-Service Call False Negatives (2)**:
  - `('checkoutservice', 'paymentservice', 'server.chargeservicehandler')`
  - `('frontend', 'checkoutservice', 'checkoutservice.placeorder')`

### `MS047`
- **Interface False Positives (25)**:
  - `('cart', 'server', 'addShipping')`
  - `('cart', 'server', 'addToCart')`
  - `('cart', 'server', 'deleteCart')`
  - `('cart', 'server', 'getCart')`
  - `('cart', 'server', 'getMetrics')`
  - `('cart', 'server', 'renameCart')`
  - `('cart', 'server', 'updateCart')`
  - `('catalogue', 'server', 'getCategories')`
  - `('catalogue', 'server', 'getProductBySku')`
  - `('catalogue', 'server', 'getProducts')`
- **Interface False Negatives (21)**:
  - `('cart', 'server', 'delete_cart_id')`
  - `('cart', 'server', 'get_add_id_sku_qty')`
  - `('cart', 'server', 'get_cart_id')`
  - `('cart', 'server', 'get_rename_from_to')`
  - `('cart', 'server', 'get_update_id_sku_qty')`
  - `('cart', 'server', 'post_shipping_id')`
  - `('catalogue', 'server', 'get_categories')`
  - `('catalogue', 'server', 'get_product_sku')`
  - `('catalogue', 'server', 'get_products')`
  - `('catalogue', 'server', 'get_products_cat')`
- **Inter-Service Call False Positives (7)**:
  - `('cart', 'catalogue', 'server.getproductbysku')`
  - `('payment', 'cart', 'server.deletecart')`
  - `('payment', 'dispatch', 'main.createspan')`
  - `('payment', 'user', 'server.addorder')`
  - `('payment', 'user', 'server.checkuser')`
  - `('ratings', 'catalogue', 'server.getproductbysku')`
  - `('shipping', 'cart', 'server.addshipping')`
- **Inter-Service Call False Negatives (7)**:
  - `('cart', 'catalogue', 'server.get_product_sku')`
  - `('payment', 'cart', 'server.delete_cart_id')`
  - `('payment', 'dispatch', 'main.main')`
  - `('payment', 'user', 'server.get_check_id')`
  - `('payment', 'user', 'server.post_order_id')`
  - `('ratings', 'catalogue', 'server.get_product_sku')`
  - `('shipping', 'cart', 'server.post_shipping_id')`

### `MS070`
- **Interface False Positives (8)**:
  - `('sfe', 'selfservicefrontendimpl', 'UnpauseForm')`
  - `('sfe', 'selfservicefrontendimpl', 'UnpauseStatus')`
  - `('sfe', 'selfservicefrontendimpl', 'UnpauseSubmit')`
  - `('sfe', 'selfservicefrontendimpl', 'makeOverrideRequestFormHandler')`
  - `('sfe', 'selfservicefrontendimpl', 'overrideAutoApprovedSuccessHandler')`
  - `('sfe', 'selfservicefrontendimpl', 'overrideRequestSubmittedSuccessHandler')`
  - `('sfe', 'selfservicefrontendimpl', 'submitOverrideRequestHandler')`
  - `('sfe', 'selfservicefrontendimpl', 'validateOverrideFieldHandler')`
- **Interface False Negatives (27)**:
  - `('sa', 'sqlstorageauthority', 'CheckIdentifiersPaused')`
  - `('sa', 'sqlstorageauthority', 'FQDNSetTimestampsForWindow')`
  - `('sa', 'sqlstorageauthority', 'GetAuthorization2')`
  - `('sa', 'sqlstorageauthority', 'GetCertificate')`
  - `('sa', 'sqlstorageauthority', 'GetCertificateStatus')`
  - `('sa', 'sqlstorageauthority', 'GetEnabledRateLimitOverrides')`
  - `('sa', 'sqlstorageauthority', 'GetLintPrecertificate')`
  - `('sa', 'sqlstorageauthority', 'GetOrder')`
  - `('sa', 'sqlstorageauthority', 'GetOrderAuthorizations')`
  - `('sa', 'sqlstorageauthority', 'GetOrderForNames')`
- **Inter-Service Call False Positives (12)**:
  - `('crl-updater', 'sa', 'sqlstorageauthorityro.getrevokedcertsbyshard')`
  - `('ra', 'sa', 'sqlstorageauthorityro.fqdnsettimestampsforwindow')`
  - `('ra', 'sa', 'sqlstorageauthorityro.getauthorization2')`
  - `('ra', 'sa', 'sqlstorageauthorityro.getcertificate')`
  - `('ra', 'sa', 'sqlstorageauthorityro.getcertificatestatus')`
  - `('ra', 'sa', 'sqlstorageauthorityro.getlintprecertificate')`
  - `('ra', 'sa', 'sqlstorageauthorityro.getorder')`
  - `('ra', 'sa', 'sqlstorageauthorityro.getorderfornames')`
  - `('ra', 'sa', 'sqlstorageauthorityro.getregistration')`
  - `('ra', 'sa', 'sqlstorageauthorityro.getserialmetadata')`
- **Inter-Service Call False Negatives (15)**:
  - `('ca', 'sa', 'sqlstorageauthority.keyblocked')`
  - `('crl-updater', 'sa', 'sqlstorageauthority.getrevokedcertsbyshard')`
  - `('ra', 'sa', 'sqlstorageauthority.fqdnsettimestampsforwindow')`
  - `('ra', 'sa', 'sqlstorageauthority.getauthorization2')`
  - `('ra', 'sa', 'sqlstorageauthority.getcertificate')`
  - `('ra', 'sa', 'sqlstorageauthority.getcertificatestatus')`
  - `('ra', 'sa', 'sqlstorageauthority.getlintprecertificate')`
  - `('ra', 'sa', 'sqlstorageauthority.getorder')`
  - `('ra', 'sa', 'sqlstorageauthority.getorderfornames')`
  - `('ra', 'sa', 'sqlstorageauthority.getregistration')`

### `MS078`
- **Interface False Positives (11)**:
  - `('identity-server', 'accountcontroller', 'AccessDenied')`
  - `('identity-server', 'accountcontroller', 'Login')`
  - `('identity-server', 'accountcontroller', 'Logout')`
  - `('identity-server', 'consentcontroller', 'Index')`
  - `('identity-server', 'devicecontroller', 'Callback')`
  - `('identity-server', 'devicecontroller', 'Index')`
  - `('identity-server', 'devicecontroller', 'UserCodeCapture')`
  - `('identity-server', 'externalcontroller', 'Callback')`
  - `('identity-server', 'externalcontroller', 'Challenge')`
  - `('identity-server', 'grantscontroller', 'Index')`
- **Inter-Service Call False Positives (6)**:
  - `('wallet-spa', 'accounts-api', 'accountscontroller.close')`
  - `('wallet-spa', 'accounts-api', 'accountscontroller.get')`
  - `('wallet-spa', 'accounts-api', 'accountscontroller.post')`
  - `('wallet-spa', 'accounts-api', 'transactionscontroller.deposit')`
  - `('wallet-spa', 'accounts-api', 'transactionscontroller.transfer')`
  - `('wallet-spa', 'accounts-api', 'transactionscontroller.withdraw')`

### `MS098`
- **Interface False Positives (19)**:
  - `('api-admin', 'accesstokenresolver', 'accessTokenMutation')`
  - `('api-admin', 'accountsresolver', 'account')`
  - `('api-admin', 'appcontroller', 'getHello')`
  - `('api-admin', 'billingsresolver', 'billing')`
  - `('api-admin', 'billingsresolver', 'billingQuery')`
  - `('api-admin', 'cardsresolver', 'cardMutation')`
  - `('api-admin', 'tenantmembersresolver', 'memberMutations')`
  - `('api-admin', 'tenantsresolver', 'tenantMutation')`
  - `('api-admin', 'usersresolver', 'profileMutation')`
  - `('api-admin', 'webhooksresolver', 'webhookMutations')`
- **Inter-Service Call False Positives (2)**:
  - `('api-admin', 'service-role', 'rolescontroller.addpolicy')`
  - `('service-account', 'service-notification', 'authsagas.userloggedin')`

### `MS106`: Perfect Match (0 Errors)
