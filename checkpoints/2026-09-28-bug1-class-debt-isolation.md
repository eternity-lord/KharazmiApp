# Bug 1 — جداسازی بدهی بین کلاس‌های یک دانش‌آموز

## دامنه
فقط باگ نشت بدهی/پرداخت بین دو enrollment بررسی و اصلاح شد. مسیرهای نوشتن wallet در `attendance.py` و مسیرهای ثبت پرداخت/settlement دست‌کاری نشدند.

## ریشه و اصلاح
- `Student.wallet_teacher` و `Student.wallet_institute` کیف کلی دانش‌آموز هستند و دیگر منبع اعداد بدهی کلاس در endpointهای کلاس نیستند.
- `calculate_enrollment_debt_breakdown` اکنون پرداخت را با `enrollment_id` واقعی یا fallback legacy دقیقِ `student_id + course_id` می‌خواند.
- تراکنش عمومیِ بدون `course_id` و `enrollment_id` به هیچ کلاس تخصیص داده نمی‌شود.
- `target_wallet == "both"` با `share_teacher` و `share_institute` در breakdown کلاس شمرده می‌شود.
- `Enrollment.total_paid` برای داده‌های legacy بدون رسید، و رسید legacy برای داده‌های متقابلاً ناقص، بدون دوباره‌شماری reconcile می‌شوند.
- لیست کلاس‌ها، جزئیات کلاس، full report، `students_full` و Excel از breakdown همان enrollment استفاده می‌کنند؛ کلیدهای قبلی حفظ شده‌اند و `wallet_*` در ردیف `students_full` همچنان کیف کلی است.
- پروفایل دانش‌آموز ادمین در `teachers_financial` از همان breakdown استفاده می‌کند و پرداخت‌های `both` را تفکیک می‌کند.
- `ClassDetailActivity.kt` برای جمع پرداختِ کلاس به `paid_teacher`/`paid_institute` per-enrollment متصل شد، نه wallet کلی. Android compile عمداً اجرا نشد.

## تست قرمز
روی copy موقت `/tmp/kharazmi-red` از HEAD قبلی با تست جدید:
- `5` تست: `3 failed, 2 passed`
- شکست‌ها دقیقاً نشت wallet در لیست کلاس، عدم احتساب legacy course payment و حذف سهم `both` در پروفایل admin را نشان دادند.

## تست سبز
- تست جدید: `5 passed`
- تست‌های مرتبط classes/admin/financial/installments: `280 passed`
- static AST parse برای فایل‌های تغییرکرده: موفق
- import واقعی `main` با `DATABASE_URL=sqlite:////tmp/kharazmi-real-current.db`: موفق، `29` route
- probe خواندنی روی copy واقعی: موفق؛ دانش‌آموز چندکلاسه در snapshot فعلی `0` بود، بنابراین enrollment چندکلاسهٔ واقعی برای probe وجود نداشت.

## DB و محیط واقعی
- md5 قبل از probe فایل اصلی `Kharazmi_Server/gaj_db.db`: `f048f8d118b33c4eaa944490594121d7`
- md5 فایل اصلی پس از probe: `f048f8d118b33c4eaa944490594121d7`
- probe فقط روی `/tmp/kharazmi-real-current.db` انجام شد؛ import main روی copy به‌علت auto-patch schema، md5 copy را از `f048f8d118b33c4eaa944490594121d7` به `d6a0a58bea98539e2094f642dab921cf` تغییر داد.

## سوئیت و وضعیت CI
آخرین اجرای کل suite پس از اصلاحات مالی، دو failure قدیمی و خارج از این task در static contract مربوط به `TeacherDashboardActivity` نشان داد؛ فایل آن در این task تغییر نکرده است. این موارد pre-existing هستند و برای رعایت scope اصلاح نشدند. Kotlin compile اجرا نشده است.

## Commit و CI
- commitهای فیکس: `376dcac` (`fix per-class debt isolation`) و `f55339a` (`fix both-wallet total in student profile`)
- commit فعال‌سازی trigger CI روی branch نشست: `5070c82` (`ci run tests on session branch`)
- branch `arena/01a0c9b8-kharazmiapp` push شد.
- اجرای GitHub Actions روی commit فیکس: run `36380259511`؛ نصب وابستگی و ثبت md5 موفق بود، اما اجرای کل suite با همان دو failure static contract قدیمی `TeacherDashboardActivity` متوقف شد. این failureها در فایل/کد این task نیستند؛ بخش tests مرتبط با Bug 1 سبز است.
- وضعیت working tree پس از push: پاک.

