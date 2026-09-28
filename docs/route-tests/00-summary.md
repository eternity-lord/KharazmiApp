# خلاصهٔ ممیزی تست‌محور routeها

**snapshot:** 2026-09-28 — **branch:** `arena/01a0c9b8-kharazmiapp`

## شمارش

| شاخص | مقدار | توضیح |
|---|---:|---|
| کل routeهای inventory | 221 | از `docs/app-map/server-routes.csv` |
| route دارای registry تست | 221 | meta-test اجباری است و missing route را fail می‌کند |
| route با functional assertion مقداری در این نوبت | 29 | finance: 11؛ attendance: 10؛ classes: 8 route با read، state و Excel |
| route از همین سه router بدون assertion مستقل | 33 | فهرست کامل و دلیل هر مورد در `blockers.md` آمده است؛ sweep جای assertion کسب‌وکار را نگرفته است |
| route functional باقی‌ماندهٔ سایر routerها | 192 | سه router اول بستهٔ صادقانه دارند؛ routerهای بعدی هنوز در انتظارند |
| router پردازش‌شده | 3 | finance، attendance و classes، ممیزی اولیه |
| تست‌های pass | 50 | آخرین اجرای `pytest tests/route_audit -q` |
| تست‌های strict xfail | 8 | 4 مورد قبلی O-02/O-12/O-14/O-19 + 4 مورد `RA-sweep-01..04` |
| باگ‌های sweep contract | 4 entry | `RA-sweep-01` تا `RA-sweep-04`؛ 6 NPE issue instance و 1 missing-list instance |
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
| retry تسویهٔ معلم | 0 سناریوی صریح | route settlement در این سه router assertion مستقل ندارد |
| تعارض شروع جلسهٔ زنده | 1 | شروع دوبارهٔ live، 409 و بدون جلسهٔ دوم |
| تعارض پایان/لغو جلسه | 1 replay cancel | cancel دوباره idempotent است؛ پایان دوباره در blockers است |
| truncation/limit لیست | 0 assertion عمیق | seed حجیم ساخته می‌شود اما حد/ترتیب لیست‌ها هنوز تست نشده است |
| تومان/ریال | 0 assertion قطعی | Q-003 باز است؛ فقط متن source/مبلغ عددی بررسی شده و تبدیل حدس زده نشده است |
| باگ جدید server/financial در 29 route | 0 | تست‌های مقداری finance/attendance/classes و oracle مستقل سبز بودند |
| باگ contract در همین scope sweep | 1 entry مستقیم classes (`RA-sweep-01`) | response bulk approve کلید `message` مورد انتظار Android را ندارد؛ در `bugs.md` ثبت و xfail شده است |

## جاروب ۲۲۱ route و ۱۵۱ تماس Retrofit

جزئیات کامل در [`sweep-report.md`](sweep-report.md) و artifactهای `tests/route_audit/sweep/` است:

- route smoke: **221/221**؛ status 500 برابر **0**؛ پاسخ‌های non-JSON مورد انتظار **13**.
- invalid OpenAPI probes: **220/220 target**؛ status 500 برابر **0**.
- empty probes: **11**؛ list=`null` برابر **0**.
- Retrofit contract: **151 unique call**، dynamic=`1`، unmatched=`0`.
- contract issueها: parse/overflow=`0`، NPE بالقوه=`6` issue instance، missing-list=`1`، silent-zero=`0`؛ چهار entry به `RA-sweep-01..04` تبدیل شدند.

## سؤال‌های باز

تعداد سؤال‌ها: **5**. متن کوتاه هرکدام:

1. **Q-001:** «درآمد» وصول نقدی است، تعهد شهریه است، یا هر دو با نام جدا؟
2. **Q-002:** برای `target_wallet=both` کل receipt در statement بیاید یا سهم‌های explicit؟
3. **Q-003:** واحد مبلغ تومان است، ریال است، یا ذخیره بدون تبدیل با label مستقل؟
4. **Q-004:** پرداخت بی‌تاریخ خارج از بازه باشد، سبد بی‌تاریخ داشته باشد، یا رد شود؟
5. **Q-005:** restore کلاس metadata-only، full ledger، یا فقط با snapshot ledger باشد؟

جزئیات گزینه‌ها در `questions.md` است.

## موارد ناتمام

- ۱۵۹ route functional باقی مانده است: ۸ route admin در blocker و ۱۵۱ route سایر routerها باید طبق ترتیب `progress.md` تکمیل شوند.
- ۳۳ route سه router اول در `blockers.md` assertion مستقل ندارند.
- exports هنوز به openpyxl/PDF value audit عمیق نشده است؛ sweep فقط response/shape را ثبت کرده است.
- device checklist عددهای screenهای مهم را دارد، اما اجرای گوشی/compile انجام نشده است.
- CI remote برای commit sweep سبز است: [run 36408060558](https://github.com/eternity-lord/KharazmiApp/actions/runs/36408060558). Android compile اجرا نشده است.
