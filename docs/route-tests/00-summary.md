# خلاصهٔ ممیزی تست‌محور routeها و قرارداد Android

**Snapshot:** 2026-10-05 · **Branch:** `arena/01a10aa8-kharazmiapp` · **Application code:** بدون تغییر. این سند وضعیت آزمون‌های همین checkout را گزارش می‌کند؛ اجرای smoke روی هر route معادل deep audit همهٔ branchها نیست.

**پایگاه اصلی:** MD5 قبل و بعد از اجرای pytest و runnerهای ایزوله `f048f8d118b33c4eaa944490594121d7` است. همهٔ seedها در DB موقت ساخته شده‌اند؛ SMS/push/network واقعی فراخوانی نشده است.

## دامنه و مرحلهٔ صفر

- ورودی اصلی نگاشت، `docs/app-map/*` است و دست‌نخورده مانده. server map، 221 route در 25 router را inventory می‌کند.
- مقایسهٔ Android جاری با نگاشت تاریخی در `android-api-current.csv` و `android-route-diff.md`: 169 declaration در Kotlin جاری، 162 در map تاریخی، 158 زوج یکتای method/path، 156 مسیر static یکتا، 1 `@Url` پویا، 65 server-only و 0 Android-only.
- این map، retrofit caller/screen، response data class/field، handler/source، ورودی OpenAPI، DB read/write استاتیک و side effect را کنار هم قرار می‌دهد. 25 ledger در `routes/*.md`، 221 route را پوشش می‌دهند.
- seed canonical پایدار و مستقل است: 30 دانش‌آموز، 7 کلاس، 7 enrollment، 6 transaction، 3 session، 4 attendance، 4 installment، 2 grade، 1 homework و 2 exam؛ timestamp/JWT/hash deterministic هستند. fixture حجیم مستقل 300 دانش‌آموز، 30 کلاس، 300 transaction و 300 session دارد.
- زمان seed روی `2026-09-28 09:00:00` freeze است. guard از اتصال به `Kharazmi_Server/gaj_db.db` جلوگیری می‌کند؛ فقط temporary DB استفاده می‌شود. `requests`, `urllib`, `socket` در pytest و runnerهای مستقل fail-closed هستند؛ subprocess regression در `test_sweep_network_guard.py` این مسدودسازی را بررسی می‌کند و worker زمان‌بندی‌شده نیز در test اجرا نمی‌شود.

## نتایج واقعی آخرین sweep / runnerها

| Probe | نتیجه |
|---|---|
| Route smoke | 221/221 route اجرا شد؛ status 500 = 0 |
| Status اصلی | `200:182`, `400:17`, `422:8`, `404:7`, `409:5`, `403:1`, `401:1` |
| Actor probe | admin=168، teacher=21، student=18، public=9، parent=5؛ این نقش‌ها probe هستند، نه اثبات کامل مجوز route |
| Invalid-input | 220/221 route هدف invalid-target دارند؛ invalid status 500 = 0 |
| Empty probes | 11؛ null-list مشاهده‌شده = 0 |
| Non-JSON | 14 پاسخ در sweep؛ endpointهایی که HTML/file/empty response دارند باید با contract خودشان تفسیر شوند |
| Boundary | 4 route، 500=0؛ `Exam.max_score=12.5`, transaction=`2147483649`, empty string/null/list بررسی شد؛ 5 خام Gson-candidate، 0 مورد تأییدشده |
| Large | هر 8 check مربوط به limit/order/filter/count/debtors/session سبز؛ تمام statusها 200 |

تنها 403 اجرای اصلی، `GET /finance/parent/dashboard` با parent session معتبر است (`RA-finance-02`). Handler در `routers/finance.py`، `get_student_financial_dashboard(...)` را مستقیم صدا می‌زند و `_role` را منتقل نمی‌کند. این باگ ثبت و strict-xfail است؛ application code تغییر نکرده.

## Retrofit ↔ Kotlin/Gson simulator

اسکریپت شبیه‌ساز، declarationها و data classهای Kotlin فعلی را با payloadهای واقعی route مقایسه می‌کند؛ **Gradle/Gson runtime یا گوشی اجرا نشده است**.

```text
169 declarations; 158 unique calls; 156 unique static method/path routes
 dynamic=1; unmatched=0; route_non_success=28; successful_non_json=4
 empty_json_body=0; parse=4; npe=5; silent_zero=8
 missing_key=0; simulation_gap=0
```

این شمارنده‌ها candidate detector هستند، نه تعداد باگ قطعی. یافته‌های مصرف‌شده/نامطمئن در Q-006..Q-008 طبقه‌بندی شده‌اند: incomplete-class fields با caller مصرف‌کنندهٔ فقط `id/title/code`؛ نبود `parent_mobile` در screen دانش‌آموز؛ و فیلدهای اختیاری/غایب transaction که screen فعلی از آنها استفاده نمی‌کند. `max_score` غایب در حالت homework نمره‌دار جداگانه به `RA-homework-01` ارتقا یافته است.

## پوشش رفتاری و مالی

- 13 router دارای testهای متمرکز هستند: finance, attendance, classes, admin, teachers, students, dashboard, reports, analytics, exports, exams, homework, parent. پوشش این 172 route **partial** است و تمام transitionها/branchهایشان عمیق نشده‌اند.
- 102 route در test sourceها literal client request reference دارند؛ این شمارش، عمق assertion را ثابت نمی‌کند. 119 مسیر literal match ندارند. ledger هر route test-reference یا smoke-only را مشخص می‌کند.
- finance دارای oracle مستقل tuition/discount/payment/due، split wallet، FIFO installment allocation و receipt/reversal است. invariantهای retry شامل direct payment، installment payment، session charge و teacher settlement/reversal بررسی شده‌اند؛ `target_wallet=both`، معنای income، واحد مبلغ، بی‌تاریخی و restore در questions ثبت‌اند.
- attendance: history/detail، snapshot هزینه، same-day QR check-in، stale QR، live start/status/cancel، conflict/retry و بی‌اثری مالی cancellation تست شده‌اند. مبلغ 260,000 در oracle جلسه با DB assert می‌شود.
- علاوه بر آن KPIهای dashboard، date/filter/order/limit subset، CSV، exam-attempt retry، homework scope، parent/child access و student optimistic version conflict آزمون شده‌اند.

## باگ‌ها و xfailها

آخرین اجرای کامل pytest بعد از افزودن socket-level blocking:

```text
98 passed, 9 xfailed, 4 warnings
```

این اجرای کامل شامل regressionهای generator و oracle دقیق invoice enrollment 2 است.

۹ strict xfail فعلی: O-02/RA-auth-02، O-12/RA-exams-02، O-19/RA-admin-19، RA-finance-02، RA-homework-01، RA-attendance-01/02/03 و RA-teachers-01. O-14 در این checkout بسته/سبز است و xfail نشده است. فهرست و reproduction در `bugs.md` است؛ هیچ باگی در application code اصلاح نشده.

## ناتمام‌ها و مراجع

- 49 route از 12 router هنوز deep value/DB/state-machine suite ندارند: `ai(1)`, `audit(1)`, `audit_trail(1)`, `auth(12)`, `automation(5)`, `branches(9)`, `calendar(4)`, `crm(5)`, `dunning(2)`, `messages(7)`, `serve_upload(1)`, `timeline(1)`؛ blockerها در `blockers.md`.
- 8 تصمیم محصول همچنان باز است: Q-001..Q-008 در `questions.md`؛ تست‌ها rule مبهمی را حدس نمی‌زنند.
- Android compile/runtime و device execution انجام نشده. Checklist دستی با seed values در `device-checklist.md` آمده است.
- شمارش و فایل‌های خام: `sweep/report.json`, `contract-report.json`, `boundary-report.json`, `large-report.json`; runnerهای مستقل در `tests/route_audit/sweep/`.
- تست کامل: `PYTHONPATH=. /tmp/kharazmi-route-audit-venv/bin/pytest -q tests/route_audit`.
