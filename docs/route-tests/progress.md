# پیشرفت ممیزی routeها

**شروع پروژهٔ ممیزی:** 2026-09-28 — **snapshot فعلی:** 2026-10-05 — **branch ثابت این نشست:** `arena/01a10aa8-kharazmiapp` (از branch ارائه‌شدهٔ اولیه متفاوت است؛ branch عوض نشده است).

## زیرساخت و مرحلهٔ صفر

- `docs/app-map/*` به‌عنوان ورودی اصلی حفظ شده است؛ هیچ فایل آن تغییر نکرده.
- بررسی map جاری: server inventory برابر 221/221 با routeهای runtime است؛ ورودی Retrofit تاریخی 162 declaration دارد، در برابر 169 declaration در Kotlin فعلی. مقایسهٔ جاری 158 زوج یکتای method/path، 156 route ثابت یکتا و 1 `@Url` پویا را نشان می‌دهد. 7 declaration جاری در map تاریخی نیستند؛ overlayهای `android-api-current.csv` و `android-route-diff.md` اختلاف را ثبت می‌کنند. 65 server-only و 0 Android-only route باقی است.
- seed canonical فقط DB موقت را می‌سازد؛ salted password hash، JWT، timestampهای ORM و داده‌های business ثابت‌اند. `test_seed_reproducibility.py` دو DB را با schema/row canonical digest مقایسه می‌کند.
- seed عادی 30 دانش‌آموز و seed حجیم 300 دانش‌آموز/30 کلاس دارد. role fixtures: admin, secretary, teacher, student, parent؛ شماره‌های دانش‌آموز/والد در seed با قالب 11 رقمی معتبرند.
- ساعت سرور در `clock.py` روی `2026-09-28 09:00:00` ثابت است. sweep، contract، boundary، large و pytest هرکدام DB موقت استفاده می‌کنند؛ `requests`, `urllib` و اتصال socket خروجی مسدود است (subprocess regression در `test_sweep_network_guard.py`)، FCM key خالی است و worker زنده برای runnerهای مستقل start نمی‌شود.
- oracle مالی مستقل، simulator Kotlin/Gson، route registry و 25 گزارش per-router موجودند. گزارش‌های per-router اکنون از ورودی map، caller فعلی Kotlin، actor probe، پاسخ/نمونه، static DB effects، sweep و test-reference استفاده می‌کنند؛ probe actor را به‌عنوان مجوز نهایی endpoint معرفی نمی‌کنند.

## routerها

۱۶ router دارای suite متمرکز/مقداری هستند، اما پوشش هنوز **partial** است و تمام branchهای 175 route این گروه deep نشده‌اند:

| router | routes | وضعیت فعلی |
|---|---:|---|
| ai | 1 | tool values برای admin/teacher/student/parent و no-write بررسی شد؛ cap مکالمه در `RA-ai-01` strict xfail است |
| audit | 1 | empty/read-only، early/delayed attendance، <30-day and <1h rapid-delete (exactly 1h rejected)، last-10 perfect-attendance transition؛ باگ باز تأیید نشد |
| audit_trail | 1 | Android response/display values، filters/search، ISO/Jalali bounds، pagination 205-row، orphan/deleted refs، rollback; reversed date-only range strict xfail `RA-audit_trail-01` |
| finance | 26 | oracle مالی/پرداخت و invoice، retry/FIFO؛ route والد معتبر باگ `RA-finance-02` را بازتولید می‌کند؛ side-effect/gateway و چند CRUD هنوز blocker دارند |
| attendance | 15 | read/history، live start/status/cancel، retry مالی، suspended guard و QR stale/same-day success با DB restore |
| classes | 21 | list/detail/debt/export و subset state/approval؛ create/bulk/delete/enrollment transitionها هنوز عمیق نیستند |
| admin | 41 | مقدار/KPI/state/export/guard، coverage مقداری پیشین؛ `RA-admin-01` فعلی سبز است |
| teachers | 18 | settlement/wallet slice، incomplete-class minimum fields؛ fractional live timestamp strict xfail |
| students | 13 | profile/grade/access/version conflict؛ `parent_mobile` در StudentPortal فعلاً فقط Q-007 است |
| dashboard | 2 | KPI exact values و local push status؛ fixed clock overdue/dunning values asserted |
| reports | 9 | debtor/statement/chart subset و date/order assertions |
| analytics | 6 | filter/date/limit/funnel subset |
| exports | 3 | CSV header/rows subset؛ PDF/XLSX کامل هنوز مانع دارد |
| exams | 7 | list/attempt subset؛ O-12 strict xfail؛ O-14 در این checkout fixed/سبز |
| homework | 6 | scope/optional defaults؛ graded parent row با `max_score` غایب در strict xfail |
| parent | 5 | profile/portal values و role slice؛ OTP/select-child transitionها هنوز deep نشده‌اند |

۹ router باقی‌مانده و **46 route** هنوز deep suite ندارند: `auth(12)`, `automation(5)`, `branches(9)`, `calendar(4)`, `crm(5)`, `dunning(2)`, `messages(7)`, `serve_upload(1)`, `timeline(1)`. گزارش‌هایشان smoke و map را دارند؛ این معادل audit رفتاری نیست.

## آخرین اجراهای واقعی

```text
PYTHONPATH=. /tmp/kharazmi-route-audit-venv/bin/pytest -q tests/route_audit
118 passed, 12 xfailed, 4 warnings

route sweep: 221/221; main 500=0; 220/221 invalid-target probes; invalid 500=0
invalid observations: 422=146, 200=70, 400=3, 403=1, 404=1
empty probes: 11; null-list observations=0; non-JSON responses=14
status: 200=182, 400=17, 422=8, 404=7, 409=5, 403=1, 401=1
403 با role/fixture معتبر: فقط GET /finance/parent/dashboard (RA-finance-02)

roles: admin=168, teacher=21, student=18, public=9, parent=5
contract: declarations=169, unique_calls=158, unique_static_routes=156,
          dynamic=1, unmatched=0, route_non_success=28, successful_non_json=4,
          parse=4, NPE-candidates=5, silent-zero-candidates=8,
          missing_key=0, simulation_gap=0
boundary: 4 routes, 500=0, raw candidates=5, confirmed contract bugs=0 (Q-006)
large seed: 300 students/30 classes + 300 transaction/session rows; 8/8 limit/order/filter checks pass
Markdown generator: 25 ledgers, every generated row has 8 intact cells and no unwrapped segment >300 chars
```

۱۱ strict xfail علت/ID فعلی: O-02/RA-auth-02, O-12/RA-exams-02, O-19/RA-admin-19, RA-ai-01, RA-audit_trail-01 (دو قالب ISO/Jalali), RA-finance-02, RA-homework-01, RA-attendance-01/02/03 و RA-teachers-01؛ در pytest دوازده مورد xfailed دیده می‌شود. O-14 xfail نیست. contract simulator خام candidate ثبت می‌کند؛ `bugs.md`/Q-006..008 آن را از باگ قابل‌مشاهده جدا می‌کنند.

`docs/route-tests/routes/*.md` برای هر route: یک جملهٔ purpose/handler، actor و status probe، caller/screen جاری، ورودی و response schema، DB read/write statically extracted، side effect و test-reference یا smoke-only status دارد. 105 route test source literal request reference دارند؛ این شمارش به‌تنهایی عمق assertion را اثبات نمی‌کند. 116 مسیر literal match ندارند؛ ledger per-route قید هر مورد را نشان می‌دهد.

## دیتابیس اصلی و commit

در اجرای نهایی، `md5sum Kharazmi_Server/gaj_db.db` قبل و بعد از pytest برابر `f048f8d118b33c4eaa944490594121d7` ثبت شد؛ sweep/contract/boundary/large نیز هرکدام DB موقت داشتند. این snapshot شامل زیرساخت deterministic seed، audit QR، socket blocking، oracle invoice و ledgerهای جاری است. این checkpoint روی branch ثابت نشست نگهداری می‌شود؛ 46 route هنوز به deep behavioral audit نیاز دارند و باگ application code عمداً اصلاح نشده است.
