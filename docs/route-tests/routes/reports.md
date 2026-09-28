# ممیزی routeهای `reports`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `GET /reports/chart-data` | handler `routers.reports.get_chart_data`؛ منبع `Kharazmi_Server/routers/reports.py:162` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /reports/debtors` | handler `routers.reports.get_debtors_report`؛ منبع `Kharazmi_Server/routers/reports.py:446` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /reports/debtors/excel` | handler `routers.reports.get_debtors_excel`؛ منبع `Kharazmi_Server/routers/reports.py:477` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /reports/financial` | handler `routers.reports.get_financial_report`؛ منبع `Kharazmi_Server/routers/reports.py:314` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /reports/financial/excel` | handler `routers.reports.get_financial_report_excel`؛ منبع `Kharazmi_Server/routers/reports.py:392` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /reports/financial_summary` | handler `routers.reports.get_financial_summary`؛ منبع `Kharazmi_Server/routers/reports.py:610` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /reports/student_profile/print` | handler `routers.reports.print_student_profile`؛ منبع `Kharazmi_Server/routers/reports.py:1067` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /reports/student_statement` | handler `routers.reports.get_student_statement`؛ منبع `Kharazmi_Server/routers/reports.py:743` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /reports/student_statement/print` | handler `routers.reports.print_student_statement`؛ منبع `Kharazmi_Server/routers/reports.py:883` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
