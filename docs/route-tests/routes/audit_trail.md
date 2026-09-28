# ممیزی routeهای `audit_trail`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `GET /audit-trail/logs` | handler `routers.audit_trail.list_audit_logs`؛ منبع `Kharazmi_Server/routers/audit_trail.py:754` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
