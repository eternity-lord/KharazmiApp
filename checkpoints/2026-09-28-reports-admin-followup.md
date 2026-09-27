# گزارش تکمیل batch گزارش‌ها و پنل ادمین — 2026-09-28

## اصلاحات انجام‌شده

- گزارش مالی با دادهٔ legacy سازگار شد: فیلتر شعبه از `branch_scope_clause` استفاده می‌کند تا تراکنش‌های `branch_id=NULL` برای شعبه‌دار حذف نشوند، بدون اینکه ردیف شعبهٔ دیگر نشت کند.
- بازهٔ ماه/سال جلالی در `financial_summary` دیگر روز ۳۱ نامعتبر را برای ماه‌های ۷ تا ۱۲ تولید نمی‌کند؛ علت صفر شدن گزارش در این حالت اصلاح شد.
- نمودار بدون فیلتر همچنان قرارداد ۳۰ روز اخیر را حفظ می‌کند، اما وقتی هیچ ردیف تاریخ‌داری در این بازه نیست، به قدیمی‌ترین دادهٔ legacy fallback می‌کند تا نمودار صفر کاذب نباشد.
- `/reports/financial` جزئیات transaction، دانش‌آموز، معلم، کلاس، شعبه، کیف مقصد، سهم‌ها و لینک صورت‌حساب را برمی‌گرداند.
- `/reports/financial/excel` اضافه شد و همان scope و بازهٔ گزارش مالی را با ستون‌های مدیریتی export می‌کند؛ فیلتر `teacher_id` نیز دارد.
- صورت‌حساب دانش‌آموز اکنون `teachers` تفصیلی، بدهی معلم/آموزشگاه در هر کلاس، tuition، وضعیت enrollment و مسیر پروفایل معلم/دانش‌آموز را علاوه بر timeline و قسط بعدی برمی‌گرداند.
- بدهی کارت کلاس معلم از کیف کل دانش‌آموز برای همهٔ کلاس‌ها کپی نمی‌شود؛ helper خواندنی `calculate_enrollment_debt_breakdown` فقط paymentهای لینک‌شده و charge همان enrollment/course را می‌خواند و ledger/wallet را تغییر نمی‌دهد.
- صف تأیید کلاس در UI قدیمی نیز به conflict preview، ظرفیت/شعبه، تأیید و رد تکی، رد با علت، عملیات گروهی و ActivityLog متصل شد. approve تکی همان conflict guard مسیر گروهی را دارد.
- تاریخچهٔ جلسات ادمین فیلتر تاریخ/جست‌وجو/وضعیت، attendance جزئی، وضعیت مالی charge/billed/penalty، اطلاعات معلم و export Excel را نمایش می‌دهد؛ reopen همچنان فقط با guard مالی انجام می‌شود.
- audit trail برای `course_id`/`branch_id` در UI برچسب خوانا و نام کلاس/شعبه را نمایش می‌دهد؛ سند خام audit دست‌نخورده باقی می‌ماند.

## بررسی و تست

- `ast.parse` روی همهٔ فایل‌های Python موفق.
- import واقعی `main` روی copy از `Kharazmi_Server/gaj_db.db` موفق؛ OpenAPI مسیرهای settlement، financial، financial Excel و session history را ثبت کرد. DB اصلی برای probe تغییر نکرد.
- سوئیت کامل backend با virtualenv موقت و DB خارج از repository: **1183 passed, 75 warnings**.
- `git diff --check` موفق.
- Android compile طبق قرارداد پروژه اجرا نشد؛ بررسی Android با مدل‌های backward-compatible، routeها و تست‌های static انجام شد.

## نکتهٔ عملیاتی settlement

کپی فعلی `gaj_db.db` هیچ Teacher/Settlement/UserSession نداشت؛ بنابراین 404 برای شناسهٔ settlement خاص با دادهٔ خالی قابل بازتولید نیست. routeهای reverse/edit/history در OpenAPI حاضرند. برای دادهٔ واقعی باید `settlement_id` متعلق به همان `teacher_id` و نسخهٔ backend فعلی استفاده شود؛ route عمداً settlement ناموجود را 404 می‌کند.
