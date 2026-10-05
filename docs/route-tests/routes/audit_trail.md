# ممیزی routeهای `audit_trail`

> The route ledger below is the current generated audit snapshot and supersedes any older status/count matrix above.

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `GET /audit-trail/logs` | handler `routers.audit_trail.list_audit_logs`؛ منبع `Kharazmi_Server/routers/audit_trail.py:754` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |

<!-- GENERATED ROUTE LEDGER START -->
## Route ledger — map input + current isolated probes

Generated from `docs/app-map/server-routes.csv`; branch `arena/01a10aa8-kharazmiapp`. Static DB columns and response keys are the supplied map's AST/OpenAPI summary, not runtime proof. ‘Probe actor’ is the role intentionally selected by the sweep; it is not a substitute for a complete authorization contract.

| Route | One-sentence purpose / handler | Probe actor + observed result | Current Android caller / screen | Inputs → response values | Static DB reads → writes | Side effects | Audit evidence/status |
|---|---|---|---|---|---|---|---|
| `GET /audit-trail/logs` | Runs `list audit logs` for `GET /audit-trail/logs`. Source: `Kharazmi_Server/routers/audit_trail.py:754`. | admin / 200 object;<br> invalid=200 | `AuditTrailApi.getLogs` — `ApiInterfaces.kt`:200<br>`AuditTrailApi.exportLogsCsv` — `ApiInterfaces.kt`:216 | Input: query:entity_type:{'anyOf': [{'type': 'string'},<br>{'type': 'null'}],<br>'description': 'transaction<br>installment',<br>'title': 'Entity Type'}:optional<br>query:entity_id:{'anyOf': [{'type': 'integer',<br>'minimum': 1},<br>{'type': 'null'}],<br>'description': 'شناسه\u200cی رکورد مالی',<br>'title': 'Entity Id'}:optional<br>query:action:{'anyOf': [{'type': 'string'},<br>{'type': 'null'}],<br>'description': 'create<br>update<br>delete',<br>'title': 'Action'}:optional<br>query:user_id:{'anyOf': [{'type': 'integer',<br>'minimum': 1},<br>{'type': 'null'}],<br>'description': 'فیلتر بر اساس کاربر',<br>'title': 'User Id'}:optional<br>query:start_date:{'anyOf': [{'type': 'string'},<br>{'type': 'null'}],<br>'description': 'از تاریخ (ISO یا جلالی)',<br>'title': 'Start Date'}:optional<br>query:end_date:{'anyOf': [{'type': 'string'},<br>{'type': 'null'}],<br>'description': 'تا تاریخ (ISO یا جلالی، شامل کل روز)',<br>'title': 'End Date'}:optional<br>query:search:{'anyOf': [{'type': 'string'},<br>{'type': 'null'}],<br>'description': 'جست\u200cوجوی نام دانش\u200cآموز/معلم/کلاس/شعبه/گیرنده',<br>'title': 'Search'}:optional<br>query:page:integer:optional<br>query:limit:integer:optional<br>header:authorization:{'anyOf': [{'type': 'string'},<br>{'type': 'null'}],<br>'title': 'Authorization'}:optional<br>Server response: AuditTrailResponse;<br> static_return_keys=نامشخص<br>Android model: `AuditTrailResponse` (logs:json=logs:List<AuditTrailLog>;<br>total:json=total:Int;<br>page:json=page:Int;<br>limit:json=limit:Int;<br>pages:json=pages:Int)<br>`Response<ResponseBody>` () | Read: FinancialAuditLog<br>Write: نامشخص | نامشخص | 221-route smoke only;<br> business values/DB effects need a focused test or an explicit blocker. Map note: استخراج خودکار از app.openapi()+AST؛ موارد نامشخص در ستون مربوطه. |

**Interpretation:** a 2xx/4xx smoke result only records the observed response for this isolated seed. It does not prove the listed static DB effect or business invariant. Direct test references are navigation aids, not a claim that every requested edge case is covered.
<!-- GENERATED ROUTE LEDGER END -->
