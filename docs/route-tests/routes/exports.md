# ممیزی routeهای `exports`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `GET /exports/audit_alerts` | handler `routers.exports.export_audit_alerts`؛ منبع `Kharazmi_Server/routers/exports.py:228` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /exports/debtors` | handler `routers.exports.export_debtors`؛ منبع `Kharazmi_Server/routers/exports.py:99` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /exports/overdue_installments` | handler `routers.exports.export_overdue_installments`؛ منبع `Kharazmi_Server/routers/exports.py:192` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
