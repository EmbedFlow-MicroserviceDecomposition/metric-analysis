# Agent Extraction Validation Report

## 1. Aggregate Summary
- **Systems Evaluated**: 15
- **Schema & Partition Conformance**: 15/15 (100.0%)
- **Macro Interface Identification F1**: `0.9870` (Signature F1: `0.8633`)
- **Macro Inter-Service Class Edge F1 (SM)**: `0.8798`
- **Macro Inter-Service Interface Call F1 (IFN)**: `0.9810`

## 2. Per-System Breakdown

| System | Schema | GT Ifaces | Pred Ifaces | Iface F1 | Class Edge F1 | Iface Call F1 | ΔCHD | ΔCHM | ΔIFN | ΔSM |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `MS001` | PASS | 13 | 13 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS004` | PASS | 56 | 56 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0556 | 0.0000 | 0.0000 |
| `MS010` | PASS | 7 | 7 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS016` | PASS | 18 | 18 | `1.0000` | `0.7907` | `0.9811` | 0.0000 | 0.0000 | 0.1111 | 0.0000 |
| `MS017` | PASS | 4 | 4 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS020` | PASS | 11 | 11 | `1.0000` | `0.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS021` | PASS | 58 | 58 | `1.0000` | `0.9905` | `0.9846` | 0.0000 | 0.0065 | 0.1667 | 0.0001 |
| `MS031` | PASS | 16 | 16 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS032` | PASS | 11 | 11 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS039` | PASS | 27 | 27 | `0.9259` | `0.8667` | `0.9048` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS047` | PASS | 28 | 28 | `1.0000` | `0.6667` | `1.0000` | 0.0336 | 0.0619 | 0.0000 | 0.0000 |
| `MS070` | PASS | 125 | 98 | `0.8789` | `0.9000` | `0.8442` | 0.0052 | 0.0005 | 0.4118 | 0.0000 |
| `MS078` | PASS | 6 | 6 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS098` | PASS | 128 | 128 | `1.0000` | `0.9831` | `1.0000` | 0.0193 | 0.0025 | 0.0000 | 0.0000 |
| `MS106` | PASS | 28 | 28 | `1.0000` | `1.0000` | `1.0000` | 0.0231 | 0.0147 | 0.0000 | 0.0000 |

## 3. Diagnostic Error Analysis (False Positives & False Negatives)

### `MS001`: Perfect Match (0 Errors)

### `MS004`: Perfect Match (0 Errors)

### `MS010`: Perfect Match (0 Errors)

### `MS016`
- **Inter-Service Call False Positives (1)**:
  - `('WebApp', 'WorkshopManagementAPI', 'refdatacontroller.getcustomers')`

### `MS017`: Perfect Match (0 Errors)

### `MS020`: Perfect Match (0 Errors)

### `MS021`
- **Inter-Service Call False Positives (1)**:
  - `('services/tools.descartes.teastore.webui', 'services/tools.descartes.teastore.recommender', 'trainendpoint.train')`

### `MS031`: Perfect Match (0 Errors)

### `MS032`: Perfect Match (0 Errors)

### `MS039`
- **Interface False Positives (2)**:
  - `('emailservice', 'dummyemailservice', 'SendOrderConfirmation')`
  - `('paymentservice', 'hipstershopserver', 'ChargeServiceHandler')`
- **Interface False Negatives (2)**:
  - `('emailservice', 'emailservice', 'SendOrderConfirmation')`
  - `('paymentservice', 'server', 'ChargeServiceHandler')`
- **Inter-Service Call False Positives (2)**:
  - `('checkoutservice', 'emailservice', 'dummyemailservice.sendorderconfirmation')`
  - `('checkoutservice', 'paymentservice', 'hipstershopserver.chargeservicehandler')`
- **Inter-Service Call False Negatives (2)**:
  - `('checkoutservice', 'emailservice', 'emailservice.sendorderconfirmation')`
  - `('checkoutservice', 'paymentservice', 'server.chargeservicehandler')`

### `MS047`: Perfect Match (0 Errors)

### `MS070`
- **Interface False Negatives (27)**:
  - `('sa', 'sqlstorageauthorityro', 'CheckIdentifiersPaused')`
  - `('sa', 'sqlstorageauthorityro', 'FQDNSetTimestampsForWindow')`
  - `('sa', 'sqlstorageauthorityro', 'GetAuthorization2')`
  - `('sa', 'sqlstorageauthorityro', 'GetCertificate')`
  - `('sa', 'sqlstorageauthorityro', 'GetCertificateStatus')`
  - `('sa', 'sqlstorageauthorityro', 'GetEnabledRateLimitOverrides')`
  - `('sa', 'sqlstorageauthorityro', 'GetLintPrecertificate')`
  - `('sa', 'sqlstorageauthorityro', 'GetOrder')`
  - `('sa', 'sqlstorageauthorityro', 'GetOrderAuthorizations')`
  - `('sa', 'sqlstorageauthorityro', 'GetOrderForNames')`
- **Inter-Service Call False Positives (12)**:
  - `('crl-storer', 'sa', 'sqlstorageauthority.getserialsmetadata')`
  - `('wfe2', 'sa', 'sqlstorageauthority.checkidentifierspaused')`
  - `('wfe2', 'sa', 'sqlstorageauthority.fqdnsettimestampsforwindow')`
  - `('wfe2', 'sa', 'sqlstorageauthority.getcertificate')`
  - `('wfe2', 'sa', 'sqlstorageauthority.getcertificatestatus')`
  - `('wfe2', 'sa', 'sqlstorageauthority.getorder')`
  - `('wfe2', 'sa', 'sqlstorageauthority.getregistration')`
  - `('wfe2', 'sa', 'sqlstorageauthority.getregistrationbykey')`
  - `('wfe2', 'sa', 'sqlstorageauthority.getserialmetadata')`
  - `('wfe2', 'sa', 'sqlstorageauthority.incidentsforserial')`
- **Inter-Service Call False Negatives (12)**:
  - `('crl-storer', 'sa', 'sqlstorageauthorityro.getserialsmetadata')`
  - `('wfe2', 'sa', 'sqlstorageauthorityro.checkidentifierspaused')`
  - `('wfe2', 'sa', 'sqlstorageauthorityro.fqdnsettimestampsforwindow')`
  - `('wfe2', 'sa', 'sqlstorageauthorityro.getcertificate')`
  - `('wfe2', 'sa', 'sqlstorageauthorityro.getcertificatestatus')`
  - `('wfe2', 'sa', 'sqlstorageauthorityro.getorder')`
  - `('wfe2', 'sa', 'sqlstorageauthorityro.getregistration')`
  - `('wfe2', 'sa', 'sqlstorageauthorityro.getregistrationbykey')`
  - `('wfe2', 'sa', 'sqlstorageauthorityro.getserialmetadata')`
  - `('wfe2', 'sa', 'sqlstorageauthorityro.incidentsforserial')`

### `MS078`: Perfect Match (0 Errors)

### `MS098`: Perfect Match (0 Errors)

### `MS106`: Perfect Match (0 Errors)
