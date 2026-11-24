# Agent Extraction Validation Report

## 1. Aggregate Summary
- **Systems Evaluated**: 15
- **Schema & Partition Conformance**: 15/15 (100.0%)
- **Macro Interface Identification F1**: `0.6320` (Signature F1: `0.6049`)
- **Macro Inter-Service Class Edge F1 (SM)**: `0.5725`
- **Macro Inter-Service Interface Call F1 (IFN)**: `0.8393`

## 2. Per-System Breakdown

| System | Schema | GT Ifaces | Pred Ifaces | Iface F1 | Class Edge F1 | Iface Call F1 | ΔCHD | ΔCHM | ΔIFN | ΔSM |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `MS001` | PASS | 13 | 13 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS004` | PASS | 56 | 56 | `0.9464` | `1.0000` | `1.0000` | 0.0000 | 0.0556 | 0.0000 | 0.0000 |
| `MS010` | PASS | 7 | 8 | `0.9333` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS016` | PASS | 18 | 18 | `0.0000` | `0.0000` | `0.9811` | 0.0000 | 0.0000 | 0.1111 | 0.0000 |
| `MS017` | PASS | 4 | 4 | `0.0000` | `1.0000` | `1.0000` | 0.2333 | 0.0000 | 0.0000 | 0.0000 |
| `MS020` | PASS | 11 | 11 | `1.0000` | `0.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS021` | PASS | 58 | 58 | `1.0000` | `0.9905` | `0.9231` | 0.0000 | 0.0065 | 0.1667 | 0.0004 |
| `MS031` | PASS | 16 | 16 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS032` | PASS | 11 | 11 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS039` | PASS | 27 | 16 | `0.5116` | `0.6667` | `0.9048` | 0.0708 | 0.0000 | 0.0000 | 0.0000 |
| `MS047` | PASS | 28 | 28 | `0.2143` | `0.0000` | `0.0000` | 0.0488 | 0.0679 | 0.0000 | 0.0000 |
| `MS070` | PASS | 125 | 97 | `0.8739` | `0.9302` | `0.8182` | 0.0133 | 0.0005 | 0.4118 | 0.0001 |
| `MS078` | PASS | 8 | 8 | `1.0000` | `0.0000` | `0.0000` | 0.0000 | 0.0000 | 2.3333 | 0.0003 |
| `MS098` | PASS | 128 | 137 | `0.0000` | `0.0000` | `0.9630` | 0.1054 | 0.0166 | 0.4444 | 0.0001 |
| `MS106` | PASS | 28 | 26 | `0.0000` | `0.0000` | `1.0000` | 0.0217 | 0.0846 | 0.0000 | 0.0000 |

## 3. Diagnostic Error Analysis (False Positives & False Negatives)

### `MS001`: Perfect Match (0 Errors)

### `MS004`
- **Interface False Positives (3)**:
  - `('ftgo-order-service', 'net.chrisrichardson.ftgo.orderservice.grpc.OrderServiceServer.OrderServiceImpl', 'cancelOrder')`
  - `('ftgo-order-service', 'net.chrisrichardson.ftgo.orderservice.grpc.OrderServiceServer.OrderServiceImpl', 'createOrder')`
  - `('ftgo-order-service', 'net.chrisrichardson.ftgo.orderservice.grpc.OrderServiceServer.OrderServiceImpl', 'reviseOrder')`
- **Interface False Negatives (3)**:
  - `('ftgo-order-service', 'net.chrisrichardson.ftgo.orderservice.grpc.OrderServiceImpl', 'cancelOrder')`
  - `('ftgo-order-service', 'net.chrisrichardson.ftgo.orderservice.grpc.OrderServiceImpl', 'createOrder')`
  - `('ftgo-order-service', 'net.chrisrichardson.ftgo.orderservice.grpc.OrderServiceImpl', 'reviseOrder')`

### `MS010`
- **Interface False Positives (1)**:
  - `('spring-petclinic-rest-system', 'org.springframework.samples.petclinic.system.ApplicationController', 'home')`

### `MS016`
- **Interface False Positives (18)**:
  - `('AuditlogService', 'Pitstop.AuditlogService.AuditLogWorker', 'HandleMessageAsync')`
  - `('CustomerManagementAPI', 'Pitstop.Application.CustomerManagementAPI.Controllers.CustomersController', 'GetAllAsync')`
  - `('CustomerManagementAPI', 'Pitstop.Application.CustomerManagementAPI.Controllers.CustomersController', 'GetByCustomerId')`
  - `('CustomerManagementAPI', 'Pitstop.Application.CustomerManagementAPI.Controllers.CustomersController', 'RegisterAsync')`
  - `('InvoiceService', 'Pitstop.InvoiceService.InvoiceWorker', 'HandleMessageAsync')`
  - `('NotificationService', 'Pitstop.NotificationService.NotificationWorker', 'HandleMessageAsync')`
  - `('VehicleManagementAPI', 'Pitstop.VehicleManagement.Controllers.VehiclesController', 'GetAllAsync')`
  - `('VehicleManagementAPI', 'Pitstop.VehicleManagement.Controllers.VehiclesController', 'GetByLicenseNumber')`
  - `('VehicleManagementAPI', 'Pitstop.VehicleManagement.Controllers.VehiclesController', 'RegisterAsync')`
  - `('WorkshopManagementAPI', 'Pitstop.WorkshopManagementAPI.Controllers.RefDataController', 'GetCustomerByCustomerId')`
- **Interface False Negatives (18)**:
  - `('AuditlogService', 'AuditLogWorker', 'HandleMessageAsync')`
  - `('CustomerManagementAPI', 'CustomersController', 'GetAllAsync')`
  - `('CustomerManagementAPI', 'CustomersController', 'GetByCustomerId')`
  - `('CustomerManagementAPI', 'CustomersController', 'RegisterAsync')`
  - `('InvoiceService', 'InvoiceWorker', 'HandleMessageAsync')`
  - `('NotificationService', 'NotificationWorker', 'HandleMessageAsync')`
  - `('VehicleManagementAPI', 'VehiclesController', 'GetAllAsync')`
  - `('VehicleManagementAPI', 'VehiclesController', 'GetByLicenseNumber')`
  - `('VehicleManagementAPI', 'VehiclesController', 'RegisterAsync')`
  - `('WorkshopManagementAPI', 'RefDataController', 'GetCustomerByCustomerId')`
- **Inter-Service Call False Positives (1)**:
  - `('WebApp', 'WorkshopManagementAPI', 'RefDataController.GetCustomers')`

### `MS017`
- **Interface False Positives (4)**:
  - `('orders', 'server', 'getOrderById')`
  - `('orders', 'server', 'getOrders')`
  - `('products', 'server', 'getProductById')`
  - `('products', 'server', 'getProducts')`
- **Interface False Negatives (4)**:
  - `('orders', 'server.js', 'get_orders')`
  - `('orders', 'server.js', 'get_orders_id')`
  - `('products', 'server.js', 'get_products')`
  - `('products', 'server.js', 'get_products_id')`

### `MS020`: Perfect Match (0 Errors)

### `MS021`
- **Inter-Service Call False Positives (3)**:
  - `('services/tools.descartes.teastore.auth', 'services/tools.descartes.teastore.persistence', 'UserEndpoint.findByIdByName')`
  - `('services/tools.descartes.teastore.webui', 'services/tools.descartes.teastore.persistence', 'UserEndpoint.findById')`
  - `('services/tools.descartes.teastore.webui', 'services/tools.descartes.teastore.registry', 'RegistryREST.getInstances')`
- **Inter-Service Call False Negatives (2)**:
  - `('services/tools.descartes.teastore.auth', 'services/tools.descartes.teastore.persistence', 'UserEndpoint.findById(String)')`
  - `('services/tools.descartes.teastore.webui', 'services/tools.descartes.teastore.persistence', 'UserEndpoint.findById(Long)')`

### `MS031`: Perfect Match (0 Errors)

### `MS032`: Perfect Match (0 Errors)

### `MS039`
- **Interface False Positives (5)**:
  - `('adservice', 'hipstershop.AdService.AdServiceImpl', 'getAds')`
  - `('currencyservice', 'server', 'convert')`
  - `('currencyservice', 'server', 'getSupportedCurrencies')`
  - `('emailservice', 'email_server.DummyEmailService', 'SendOrderConfirmation')`
  - `('paymentservice', 'HipsterShopServer', 'ChargeServiceHandler')`
- **Interface False Negatives (16)**:
  - `('adservice', 'hipstershop.AdServiceImpl', 'getAds')`
  - `('currencyservice', 'server.js', 'convert')`
  - `('currencyservice', 'server.js', 'getSupportedCurrencies')`
  - `('emailservice', 'email_server.EmailService', 'SendOrderConfirmation')`
  - `('frontend', 'main.frontendServer', 'addToCartHandler')`
  - `('frontend', 'main.frontendServer', 'assistantHandler')`
  - `('frontend', 'main.frontendServer', 'chatBotHandler')`
  - `('frontend', 'main.frontendServer', 'emptyCartHandler')`
  - `('frontend', 'main.frontendServer', 'getProductByID')`
  - `('frontend', 'main.frontendServer', 'homeHandler')`
- **Inter-Service Call False Positives (2)**:
  - `('checkoutservice', 'emailservice', 'DummyEmailService.SendOrderConfirmation')`
  - `('checkoutservice', 'paymentservice', 'HipsterShopServer.ChargeServiceHandler')`
- **Inter-Service Call False Negatives (2)**:
  - `('checkoutservice', 'emailservice', 'EmailService.SendOrderConfirmation')`
  - `('checkoutservice', 'paymentservice', 'server.ChargeServiceHandler')`

### `MS047`
- **Interface False Positives (22)**:
  - `('cart', 'server', 'addShipping')`
  - `('cart', 'server', 'addToCart')`
  - `('cart', 'server', 'deleteCart')`
  - `('cart', 'server', 'getCart')`
  - `('cart', 'server', 'renameCart')`
  - `('cart', 'server', 'updateCart')`
  - `('catalogue', 'server', 'getCategories')`
  - `('catalogue', 'server', 'getProduct')`
  - `('catalogue', 'server', 'getProducts')`
  - `('catalogue', 'server', 'getProductsByCategory')`
- **Interface False Negatives (22)**:
  - `('cart', 'server.js', 'delete_cart_id')`
  - `('cart', 'server.js', 'get_add_id_sku_qty')`
  - `('cart', 'server.js', 'get_cart_id')`
  - `('cart', 'server.js', 'get_rename_from_to')`
  - `('cart', 'server.js', 'get_update_id_sku_qty')`
  - `('cart', 'server.js', 'post_shipping_id')`
  - `('catalogue', 'server.js', 'get_categories')`
  - `('catalogue', 'server.js', 'get_product_sku')`
  - `('catalogue', 'server.js', 'get_products')`
  - `('catalogue', 'server.js', 'get_products_cat')`
- **Inter-Service Call False Positives (7)**:
  - `('cart', 'catalogue', 'server.getProduct')`
  - `('payment', 'cart', 'server.deleteCart')`
  - `('payment', 'dispatch', 'main.createSpan')`
  - `('payment', 'user', 'server.addOrder')`
  - `('payment', 'user', 'server.checkUser')`
  - `('ratings', 'catalogue', 'server.getProduct')`
  - `('shipping', 'cart', 'server.addShipping')`
- **Inter-Service Call False Negatives (7)**:
  - `('cart', 'catalogue', 'server.get_product_sku')`
  - `('payment', 'cart', 'server.delete_cart_id')`
  - `('payment', 'dispatch', 'main.main')`
  - `('payment', 'user', 'server.get_check_id')`
  - `('payment', 'user', 'server.post_order_id')`
  - `('ratings', 'catalogue', 'server.get_product_sku')`
  - `('shipping', 'cart', 'server.post_shipping_id')`

### `MS070`
- **Interface False Negatives (28)**:
  - `('mtcb', 'mtcb.mtcb', 'GetLandmarkRelative')`
  - `('sa', 'sa.SQLStorageAuthority', 'CheckIdentifiersPaused')`
  - `('sa', 'sa.SQLStorageAuthority', 'FQDNSetTimestampsForWindow')`
  - `('sa', 'sa.SQLStorageAuthority', 'GetAuthorization2')`
  - `('sa', 'sa.SQLStorageAuthority', 'GetCertificate')`
  - `('sa', 'sa.SQLStorageAuthority', 'GetCertificateStatus')`
  - `('sa', 'sa.SQLStorageAuthority', 'GetEnabledRateLimitOverrides')`
  - `('sa', 'sa.SQLStorageAuthority', 'GetLintPrecertificate')`
  - `('sa', 'sa.SQLStorageAuthority', 'GetOrder')`
  - `('sa', 'sa.SQLStorageAuthority', 'GetOrderAuthorizations')`
- **Inter-Service Call False Positives (14)**:
  - `('ca', 'sa', 'SQLStorageAuthorityRO.KeyBlocked')`
  - `('crl-updater', 'sa', 'SQLStorageAuthorityRO.GetRevokedCertsByShard')`
  - `('ra', 'sa', 'SQLStorageAuthorityRO.FQDNSetTimestampsForWindow')`
  - `('ra', 'sa', 'SQLStorageAuthorityRO.GetAuthorization2')`
  - `('ra', 'sa', 'SQLStorageAuthorityRO.GetCertificate')`
  - `('ra', 'sa', 'SQLStorageAuthorityRO.GetCertificateStatus')`
  - `('ra', 'sa', 'SQLStorageAuthorityRO.GetLintPrecertificate')`
  - `('ra', 'sa', 'SQLStorageAuthorityRO.GetOrder')`
  - `('ra', 'sa', 'SQLStorageAuthorityRO.GetOrderForNames')`
  - `('ra', 'sa', 'SQLStorageAuthorityRO.GetRegistration')`
- **Inter-Service Call False Negatives (14)**:
  - `('ca', 'sa', 'SQLStorageAuthority.KeyBlocked')`
  - `('crl-updater', 'sa', 'SQLStorageAuthority.GetRevokedCertsByShard')`
  - `('ra', 'sa', 'SQLStorageAuthority.FQDNSetTimestampsForWindow')`
  - `('ra', 'sa', 'SQLStorageAuthority.GetAuthorization2')`
  - `('ra', 'sa', 'SQLStorageAuthority.GetCertificate')`
  - `('ra', 'sa', 'SQLStorageAuthority.GetCertificateStatus')`
  - `('ra', 'sa', 'SQLStorageAuthority.GetLintPrecertificate')`
  - `('ra', 'sa', 'SQLStorageAuthority.GetOrder')`
  - `('ra', 'sa', 'SQLStorageAuthority.GetOrderForNames')`
  - `('ra', 'sa', 'SQLStorageAuthority.GetRegistration')`

### `MS078`
- **Inter-Service Call False Positives (7)**:
  - `('wallet-spa', 'accounts-api', 'AccountsController.Close')`
  - `('wallet-spa', 'accounts-api', 'AccountsController.Get')`
  - `('wallet-spa', 'accounts-api', 'AccountsController.GetByAccountId')`
  - `('wallet-spa', 'accounts-api', 'AccountsController.Post')`
  - `('wallet-spa', 'accounts-api', 'TransactionsController.Deposit')`
  - `('wallet-spa', 'accounts-api', 'TransactionsController.Transfer')`
  - `('wallet-spa', 'accounts-api', 'TransactionsController.Withdraw')`

### `MS098`
- **Interface False Positives (137)**:
  - `('api-admin', 'AccessTokenMutationResolver', 'create')`
  - `('api-admin', 'AccessTokenMutationResolver', 'delete')`
  - `('api-admin', 'AccessTokenResolver', 'accessToken')`
  - `('api-admin', 'AccessTokenResolver', 'accessTokenMutation')`
  - `('api-admin', 'AccessTokenResolver', 'accessTokens')`
  - `('api-admin', 'AccountsController', 'facebookAuth')`
  - `('api-admin', 'AccountsController', 'githubAuth')`
  - `('api-admin', 'AccountsController', 'googleAuth')`
  - `('api-admin', 'AccountsMutationResolver', 'changePassword')`
  - `('api-admin', 'AccountsMutationResolver', 'login')`
- **Interface False Negatives (128)**:
  - `('api-admin', 'src/access-token/access-token-mutation.resolver.ts', 'create')`
  - `('api-admin', 'src/access-token/access-token-mutation.resolver.ts', 'delete')`
  - `('api-admin', 'src/access-token/access-token.resolver.ts', 'accessToken')`
  - `('api-admin', 'src/access-token/access-token.resolver.ts', 'accessTokens')`
  - `('api-admin', 'src/accounts/accounts-mutation.resolver.ts', 'changePassword')`
  - `('api-admin', 'src/accounts/accounts-mutation.resolver.ts', 'login')`
  - `('api-admin', 'src/accounts/accounts-mutation.resolver.ts', 'logout')`
  - `('api-admin', 'src/accounts/accounts-mutation.resolver.ts', 'refreshTokens')`
  - `('api-admin', 'src/accounts/accounts-mutation.resolver.ts', 'register')`
  - `('api-admin', 'src/accounts/accounts-mutation.resolver.ts', 'sendResetPasswordEmail')`
- **Inter-Service Call False Positives (4)**:
  - `('api-admin', 'service-access', 'AccessTokenController.hasRights')`
  - `('api-admin', 'service-role', 'RolesController.addPolicy')`
  - `('api-admin', 'service-role', 'RolesController.hasRights')`
  - `('service-account', 'service-notification', 'AuthSagas.userLoggedIn')`

### `MS106`
- **Interface False Positives (26)**:
  - `('api', 'api.views.SendMail', 'post')`
  - `('api', 'api.views.SendMailWithTemplate', 'post')`
  - `('awsmail', 'awsmail.tasks', 'send_aws_mail')`
  - `('awsmail', 'awsmail.tasks', 'send_aws_mail_attachment')`
  - `('awsmail', 'awsmail.views.AwsMailAttachmentView', 'post')`
  - `('awsmail', 'awsmail.views.AwsMailView', 'post')`
  - `('bounce_notification', 'bounce_notification.views.BounceNotification', 'post')`
  - `('confirmation', 'confirmation.tasks', 'send_mail')`
  - `('confirmation', 'confirmation.views.SendConfirmationLink', 'post')`
  - `('info', 'info.views.InfoView', 'get')`
- **Interface False Negatives (28)**:
  - `('api', 'views.SendMail', 'post')`
  - `('api', 'views.SendMailWithTemplate', 'post')`
  - `('awsmail', 'tasks', 'send_aws_mail')`
  - `('awsmail', 'tasks', 'send_aws_mail_attachment')`
  - `('awsmail', 'views.AwsMailAttachmentView', 'post')`
  - `('awsmail', 'views.AwsMailView', 'post')`
  - `('bounce_notification', 'views.BounceNotification', 'post')`
  - `('confirmation', 'tasks', 'send_mail')`
  - `('confirmation', 'views.SendConfirmationLink', 'post')`
  - `('info', 'views.InfoView', 'get')`
