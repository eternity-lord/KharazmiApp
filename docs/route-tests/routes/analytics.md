# ممیزی routeهای `analytics`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `GET /analytics/classes` | handler `routers.analytics.get_classes_performance_analytics`؛ منبع `Kharazmi_Server/routers/analytics.py:355` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /analytics/dashboard` | handler `routers.analytics.get_analytics_dashboard`؛ منبع `Kharazmi_Server/routers/analytics.py:152` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /analytics/enrollment_funnel` | handler `routers.analytics.get_enrollment_funnel`؛ منبع `Kharazmi_Server/routers/analytics.py:78` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /analytics/export/excel` | handler `routers.analytics.export_analytics_excel`؛ منبع `Kharazmi_Server/routers/analytics.py:396` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /analytics/export/pdf` | handler `routers.analytics.export_analytics_pdf`؛ منبع `Kharazmi_Server/routers/analytics.py:529` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /analytics/teachers` | handler `routers.analytics.get_teachers_performance_analytics`؛ منبع `Kharazmi_Server/routers/analytics.py:294` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
