# ممیزی routeهای `dunning`

> The route ledger below is the current generated audit snapshot and supersedes any older status/count matrix above.

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `GET /dunning/drafts` | handler `routers.dunning.get_dunning_drafts`؛ منبع `Kharazmi_Server/routers/dunning.py:184` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /dunning/send_batch` | handler `routers.dunning.send_dunning_batch`؛ منبع `Kharazmi_Server/routers/dunning.py:256` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |

<!-- GENERATED ROUTE LEDGER START -->
## Route ledger — map input + current isolated probes

Generated from `docs/app-map/server-routes.csv`; branch `arena/01a10aa8-kharazmiapp`. Static DB columns and response keys are the supplied map's AST/OpenAPI summary, not runtime proof. ‘Probe actor’ is the role intentionally selected by the sweep; it is not a substitute for a complete authorization contract.

| Route | One-sentence purpose / handler | Probe actor + observed result | Current Android caller / screen | Inputs → response values | Static DB reads → writes | Side effects | Audit evidence/status |
|---|---|---|---|---|---|---|---|
| `GET /dunning/drafts` | Runs `get dunning drafts` for `GET /dunning/drafts`. Source: `Kharazmi_Server/routers/dunning.py:184`. | admin / 200 list;<br> invalid=200 | `DunningApi.getDrafts` — `ApiInterfaces.kt`:162 | Input: header:authorization:{'anyOf': [{'type': 'string'},<br>{'type': 'null'}],<br>'title': 'Authorization'}:optional<br>Server response: List[DunningDraft];<br> static_return_keys=نامشخص<br>Android model: `List<DunningDraft>` (installmentId:json=installment_id:Int;<br>studentName:json=student_name:String;<br>parentMobile:json=parent_mobile:String;<br>amount:json=amount:Long;<br>dueDate:json=due_date:String;<br>category:json=category:String;<br>suggestedMessage:json=suggested_message:String) | Read: Installment<br>Write: نامشخص | نامشخص | 221-route smoke only;<br> business values/DB effects need a focused test or an explicit blocker. Map note: استخراج خودکار از app.openapi()+AST؛ موارد نامشخص در ستون مربوطه. |
| `POST /dunning/send_batch` | Runs `send dunning batch` for `POST /dunning/send_batch`. Source: `Kharazmi_Server/routers/dunning.py:256`. | admin / 200 object;<br> invalid=400 | `DunningApi.sendBatch` — `ApiInterfaces.kt`:165 | Input: header:authorization:{'anyOf': [{'type': 'string'},<br>{'type': 'null'}],<br>'title': 'Authorization'}:optional<br>body:SendBatchRequest:required<br>Server response: نامشخص;<br> static_return_keys=sent_count,<br>skipped_count,<br>sent_ids,<br>skipped_ids,<br>skipped_reasons,<br>message<br>Android model: `DunningSendResponse` (sentCount:json=sent_count:Int;<br>skippedCount:json=skipped_count:Int;<br>sentIds:json=sent_ids:List<Int>;<br>skippedIds:json=skipped_ids:List<Int>;<br>message:json=message:String;<br>skippedReasons:json=skipped_reasons:Map<String,<br>String>?) | Read: Installment<br>Write: ActivityLog(admin_username=admin_username,<br>action='dunning_reminder',<br>target_id=inst.id,<br>target_name=student_name,<br>details=suggested,<br>timestamp=datetime.datetime.utcnow());<br>SmsLog(target_group=f'dunning_{inst.id}',<br>message_text=suggested,<br>sent_count=1,<br>date=_jalali_now_str()) | SmsLog;<br>db.add;<br>db.commit | 221-route smoke only;<br> business values/DB effects need a focused test or an explicit blocker. Map note: استخراج خودکار از app.openapi()+AST؛ موارد نامشخص در ستون مربوطه. |

**Interpretation:** a 2xx/4xx smoke result only records the observed response for this isolated seed. It does not prove the listed static DB effect or business invariant. Direct test references are navigation aids, not a claim that every requested edge case is covered.
<!-- GENERATED ROUTE LEDGER END -->
