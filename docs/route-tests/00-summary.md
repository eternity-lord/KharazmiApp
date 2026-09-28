# خلاصهٔ ممیزی تست‌محور routeها

**snapshot:** 2026-09-28 — **branch:** `arena/01a0c9b8-kharazmiapp`

**checksum واقعی دیتابیس اصلی:** `md5sum Kharazmi_Server/gaj_db.db` → `f048f8d11833c4eaa944490594121d7` (دیتابیس اصلی تغییر نکرده است).

## شمارش

| شاخص | مقدار | توضیح |
|---|---:|---|
| کل routeهای inventory | 221 | از `docs/app-map/server-routes.csv` |
| route دارای registry تست | 221 | meta-test اجباری است و missing route را fail می‌کند |
| route با functional assertion مقداری در این نوبت | 70 | finance: 11؛ attendance: 10؛ classes: 8؛ admin: 41 route با read، state، ledger، export، conflict و guard |
| route از همین سه router بدون assertion مستقل | 33 | فهرست کامل و دلیل هر مورد در `blockers.md` آمده است؛ sweep جای assertion کسب‌وکار را نگرفته است |
| route functional باقی‌ماندهٔ سایر routerها | 151 | 80 تست route-audit اکنون شامل deep audit teachers/students/dashboard/reports/analytics/exports/exams/homework/parent و fixtureهای مرزی/حجیم است؛ همهٔ routeها هنوز deep نشده‌اند |
| router پردازش‌شده | 13 | finance، attendance، classes، admin و deep sliceهای teachers/students/dashboard/reports/analytics/exports/exams/homework/parent؛ calendar/branches/timeline/audit فقط sweep |
| تست‌های pass | 80 | آخرین اجرای `pytest tests/route_audit -q` |
| تست‌های strict xfail | 3 | فقط O-02، O-12 و O-19؛ O-14، RA-sweep-01..04 و RA-admin-01 سبز و assertion عادی هستند |
| باگ‌های contract/deep audit | 0 issue باز | هر 4 sweep، RA-admin-01 و RA-parent-01 اصلاح شدند؛ contract post-fix هیچ issue ندارد |
| باگ‌های status 500 در sweep | 0 | در 221 اجرای معتبر و 220 payload نامعتبر، status 500 مشاهده نشد |

## پوشش این نوبت

- مقدار response و متن فارسی در مسیرهای read finance بررسی شد.
- جزئیات session، history حضور، live start/status/cancel، roster و اثر صفر مالی بررسی شد.
- کلاس‌ها: list/detail/full report/students، pending/deletion، suspend و Excel با openpyxl بررسی شد.
- oracle مستقل برای tuition/discount/payment/due و wallet سهم‌ها استفاده شد.
- atomic update و retry برای پرداخت مستقیم، پرداخت قسط و شارژ جلسه بررسی شد؛ retry تسویه در این سه router route ندارد.
- invalid amount بررسی شد و عدم ایجاد transaction assert شد.
- پاسخ خالی installments به‌صورت `[]` بررسی شد.
- dynamic URL، امنیت token و نفوذ خارج از scope باقی ماندند.

## نتیجهٔ صریح برای ۶۲ route سه router اول

| آزمون/موضوع | نتیجهٔ عددی | تفسیر |
|---|---:|---|
| payload نامعتبر تولیدشده از OpenAPI | 220 route دارای body/parameter؛ 0 status 500 | sweep در `report.json` ثبت شده؛ assertion معنایی 29 route سه router اول و 33 route admin جداگانه ثبت شده است |
| retry پرداخت مستقیم/قسط | 2 سناریوی صریح، `/finance/pay` و `/finance/installments/{id}/pay` | پرداخت مستقیم دوباره همان `transaction_id` را می‌دهد و فقط 1 transaction ساخته می‌شود؛ retry قسط 400 و receipt دوم ندارد |
| retry شارژ جلسه | 1 سناریوی صریح، `/attendance/submit_session` | retry همان تاریخ 409؛ فقط یک SessionLog/Attendance/ledger جدید و wallet به‌صورت snapshot بازگردانده شد؛ این guard جای value audit کامل route نیست |
| retry تسویهٔ معلم | 1 سناریوی صریح | settle مبلغ 300,000، retry=400، reversal مبلغ 300,000، retry reversal=409 و wallet بدون تغییر assert شد |
| تعارض شروع جلسهٔ زنده | 1 | شروع دوبارهٔ live، 409 و بدون جلسهٔ دوم |
| تعارض پایان/لغو جلسه | 1 replay cancel | cancel دوباره idempotent است؛ پایان دوباره در blockers است |
| truncation/limit لیست | 8 assertion scale | seed مستقل 300 دانش‌آموز/30 کلاس + 300 transaction/session؛ limit/order/filter دانش‌آموز، کلاس، transaction، بدهکار و session سبز شد |
| تومان/ریال | 0 assertion قطعی | Q-003 باز است؛ فقط متن source/مبلغ عددی بررسی شده و تبدیل حدس زده نشده است |
| باگ جدید server/financial در 29 route | 0 | تست‌های مقداری finance/attendance/classes و oracle مستقل سبز بودند |
| باگ contract در همین scope sweep | 0 post-fix issue | `RA-sweep-01..04` با responseهای server صریح سبز هستند؛ `bugs.md` status هر مورد را ثبت می‌کند |

## نتیجهٔ deep audit admin و بخش‌های پرریسک

- **41/41 route** admin حداقل یک assertion مقداری، state، conflict، export یا negative guard دارند؛ route بدون assertion باقی نمانده است.
- `/dashboard/stats` در RA-admin-01 اصلاح شد: transaction دارای `student_id` ولی بدون `enrollment_id` اکنون نام مستقیم دانش‌آموز را برمی‌گرداند؛ dashboard audit سبز است.
- settings/share/pricing، transaction delta، metadata-only restore، session reopen، bulk state، SMS log محلی، role redaction، credentials و XLSX بررسی شدند؛ SMS/network واقعی ارسال نشد.
- teachers: تسویهٔ 300,000، payout منفی، retry، reversal، بازگشت attendance و عدم تغییر wallet assert شد.
- students: profile/grade oracle، دسترسی parent، empty search و optimistic conflict/version assert شد.
- dashboard/analytics/reports/exports: KPI، date/filter/limit، debt oracle و CSV header/rows assert شد.
- exams/homework/parent: response shape، attempt retry، IDOR، empty defaults و child portal values assert شد.

## جاروب ۲۲۱ route و ۱۵۱ تماس Retrofit

جزئیات کامل در [`sweep-report.md`](sweep-report.md) و artifactهای `tests/route_audit/sweep/` است:

- route smoke: **221/221**؛ status 500 برابر **0**؛ پاسخ‌های non-JSON مورد انتظار **13**.
- invalid OpenAPI probes: **220/220 target**؛ status 500 برابر **0**.
- empty probes: **11**؛ list=`null` برابر **0**.
- Retrofit contract: **151 unique call**، dynamic=`1`، unmatched=`0`.
- contract post-fix: parse/overflow=`0`، NPE بالقوه=`0`، missing-list=`0`، silent-zero=`0`؛ 4 assertion عادی sweep و 1 assertion عادی O-14 سبز هستند.

## سؤال‌های باز

تعداد سؤال‌ها: **5**. متن کوتاه هرکدام:

1. **Q-001:** «درآمد» وصول نقدی است، تعهد شهریه است، یا هر دو با نام جدا؟
2. **Q-002:** برای `target_wallet=both` کل receipt در statement بیاید یا سهم‌های explicit؟
3. **Q-003:** واحد مبلغ تومان است، ریال است، یا ذخیره بدون تبدیل با label مستقل؟
4. **Q-004:** پرداخت بی‌تاریخ خارج از بازه باشد، سبد بی‌تاریخ داشته باشد، یا رد شود؟
5. **Q-005:** restore کلاس metadata-only، full ledger، یا فقط با snapshot ledger باشد؟

جزئیات گزینه‌ها در `questions.md` است.

## موارد ناتمام

- ۱۵۱ route functional سایر routerها باید طبق ترتیب `progress.md` تکمیل شوند؛ admin اکنون assertion پایه برای هر 41 route دارد.
- ۳۳ route سه router اول در `blockers.md` assertion مستقل ندارند.
- exports هنوز به openpyxl/PDF value audit عمیق نشده است؛ sweep فقط response/shape را ثبت کرده است.
- device checklist عددهای screenهای مهم را دارد، اما اجرای گوشی/compile انجام نشده است.
- CI post-fix سبز است: [run 36411439389](https://github.com/eternity-lord/KharazmiApp/actions/runs/36411439389). Android compile عمداً اجرا نشده است.
