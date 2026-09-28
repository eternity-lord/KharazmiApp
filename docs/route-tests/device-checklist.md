# device-checklist برای دادهٔ `seed_demo`

این چک‌لیست برای مقایسهٔ چشمی صاحب پروژه است؛ compile و اجرای گوشی در این ممیزی انجام نشده است.

| صفحه | دادهٔ مورد انتظار روی seed | مرجع خواندن/نمایش | وضعیت |
|---|---|---|---|
| StudentPortalActivity | نام `دانش‌آموز تست 1`؛ کد `2001`؛ wallet `-5,000`؛ debt پاسخ profile | `StudentPortalActivity.kt:199-209`؛ route `Kharazmi_Server/routers/students.py:559-697` | آمادهٔ بررسی دستی |
| ParentPortalActivity | نام کودک `دانش‌آموز تست 1`؛ wallet `-5,000`؛ debt؛ لیست‌های classes/attendance/grades/homework/exams | `ParentPortalActivity.kt:288-298,312-406`؛ route `Kharazmi_Server/routers/parent.py:299-446` | آمادهٔ بررسی دستی |
| InvoiceActivity | شهریه ناخالص `1,000,000`؛ پرداخت `300,000`؛ باقیمانده `700,000`؛ دو قسط `350,000` | `InvoiceActivity.kt:305-365`؛ `Kharazmi_Server/routers/finance.py:2264-2484` | آمادهٔ بررسی دستی |
| StudentProfileActivity | enrollmentهای active؛ قسط‌های course 1 و 2؛ مبلغ‌ها بر اساس dashboard | `StudentProfileActivity.kt:1094-1103`؛ `ApiInterfaces.kt:117-120` | آمادهٔ بررسی دستی |
| ReportActivity | receipt split باید سهم‌های explicit را حفظ کند؛ مقدار Gregorian legacy جداگانه بررسی شود | `ReportActivity.kt:450-530` | functional audit pending |
| AdminDashboardActivity | KPI نقدی باید با تعریف تصمیم‌گیری‌شدهٔ Q-001 مقایسه شود | `AdminDashboardActivity.kt:310-369`؛ `financial_calculations.py:114` | business question pending |
| Exam/Parent exam | `max_score=12.5` باید بدون Int parse failure باشد | `ParentPortalActivity.kt:66` | xfail RA-parent-01 |
