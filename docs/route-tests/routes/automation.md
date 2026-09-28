# ممیزی routeهای `automation`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `GET /automation/logs` | handler `routers.automation.get_automation_logs`؛ منبع `Kharazmi_Server/routers/automation.py:125` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /automation/rules` | handler `routers.automation.get_automation_rules`؛ منبع `Kharazmi_Server/routers/automation.py:117` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /automation/rules` | handler `routers.automation.create_automation_rule`؛ منبع `Kharazmi_Server/routers/automation.py:66` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `PUT /automation/rules/{rule_id}` | handler `routers.automation.update_automation_rule`؛ منبع `Kharazmi_Server/routers/automation.py:93` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /automation/run_rules` | handler `routers.automation.run_automation_engine`؛ منبع `Kharazmi_Server/routers/automation.py:143` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
