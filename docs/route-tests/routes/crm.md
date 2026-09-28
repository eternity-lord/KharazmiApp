# ممیزی routeهای `crm`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `POST /crm/leads/create` | handler `routers.crm.create_crm_lead`؛ منبع `Kharazmi_Server/routers/crm.py:92` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /crm/leads/list` | handler `routers.crm.get_crm_leads_list`؛ منبع `Kharazmi_Server/routers/crm.py:133` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /crm/leads/{id}/convert` | handler `routers.crm.convert_lead_to_student`؛ منبع `Kharazmi_Server/routers/crm.py:167` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /crm/leads/{id}/notes` | handler `routers.crm.add_lead_notes`؛ منبع `Kharazmi_Server/routers/crm.py:145` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /crm/register_online` | handler `routers.crm.public_online_registration`؛ منبع `Kharazmi_Server/routers/crm.py:253` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
