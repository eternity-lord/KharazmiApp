# ممیزی routeهای `audit`

> The route ledger below is the current generated audit snapshot and supersedes any older status/count matrix above.

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `GET /audit/suspicious_patterns` | handler `routers.audit.get_suspicious_patterns`؛ منبع `Kharazmi_Server/routers/audit.py:87` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |

<!-- GENERATED ROUTE LEDGER START -->
## Route ledger — map input + current isolated probes

Generated from `docs/app-map/server-routes.csv`; branch `arena/01a10aa8-kharazmiapp`. Static DB columns and response keys are the supplied map's AST/OpenAPI summary, not runtime proof. ‘Probe actor’ is the role intentionally selected by the sweep; it is not a substitute for a complete authorization contract.

| Route | One-sentence purpose / handler | Probe actor + observed result | Current Android caller / screen | Inputs → response values | Static DB reads → writes | Side effects | Audit evidence/status |
|---|---|---|---|---|---|---|---|
| `GET /audit/suspicious_patterns` | Runs `get suspicious patterns` for `GET /audit/suspicious_patterns`. Source: `Kharazmi_Server/routers/audit.py:87`. | admin / 200 list;<br> invalid=200 | `AuditApi.getSuspiciousPatterns` — `ApiInterfaces.kt`:146 | Input: header:authorization:{'anyOf': [{'type': 'string'},<br>{'type': 'null'}],<br>'title': 'Authorization'}:optional<br>Server response: List[AuditAlert];<br> static_return_keys=نامشخص<br>Android model: `List<AuditAlert>` (type:json=type:String;<br>severity:json=severity:String;<br>title:json=title:String;<br>description:json=description:String;<br>entityId:json=entity_id:Int;<br>entityName:json=entity_name:String;<br>detectedAt:json=detected_at:String) | Read: ActivityLog;<br>Attendance;<br>Course;<br>SessionLog;<br>Transaction<br>Write: نامشخص | نامشخص | 221-route smoke only;<br> business values/DB effects need a focused test or an explicit blocker. Map note: استخراج خودکار از app.openapi()+AST؛ موارد نامشخص در ستون مربوطه. |

**Interpretation:** a 2xx/4xx smoke result only records the observed response for this isolated seed. It does not prove the listed static DB effect or business invariant. Direct test references are navigation aids, not a claim that every requested edge case is covered.
<!-- GENERATED ROUTE LEDGER END -->
