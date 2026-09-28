# ممیزی routeهای `dashboard`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `GET /dashboard/kpis` | handler `routers.dashboard.get_dashboard_kpis`؛ منبع `Kharazmi_Server/routers/dashboard.py:56` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /dashboard/push_status` | handler `routers.dashboard.get_push_status`؛ منبع `Kharazmi_Server/routers/dashboard.py:157` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
