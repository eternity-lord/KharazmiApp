# Blockers و موارد مسدود

این فایل وضعیت «نمی‌توانم بدون حدس/تغییر کد تست معتبر بنویسم» را از باگ جدا می‌کند.

| شناسه | scope | علت مسدودشدن | راه ادامه |
|---|---|---|---|
| BLK-001 | 195 route غیر finance | تست رفتاری هر route هنوز در نوبت router خودش ساخته نشده؛ فقط registry و route doc scaffold وجود دارد. | اجرای ترتیب progress و commit مستقل بعد از هر router. |
| BLK-002 | Android UI | compile مجاز/درخواست‌شده نیست و قرارداد با شبیه‌ساز Python بررسی می‌شود؛ رفتار واقعی Gson سفارشی باید در source تأیید شود. | تکمیل parser و device-checklist؛ بدون ادعای runtime UI. |
| BLK-003 | پیامک، push، gateway | باید network mock شود؛ seed فقط دادهٔ محلی می‌سازد و endpointهای side-effect در تست finance هنوز functional sweep نشده‌اند. | patch مرزی service در test fixture و assert DB log/rollback. |
| BLK-004 | PDF/Excel | مسیرهای exports هنوز functional audit نشده‌اند؛ خروجی باید با openpyxl/reportlab خوانده شود، نه فقط status code. | router exports در اولویت بعدی reports/analytics. |
| BLK-005 | business decisions | Q-001 تا Q-005 پاسخ قطعی ندارند. | تصمیم محصول ثبت شود؛ تا آن زمان تست فقط source-defined behavior را می‌سنجد. |
