# ممیزی routeهای `parent`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `GET /parent/child_profile` | handler `routers.parent.get_parent_child_profile`؛ منبع `Kharazmi_Server/routers/parent.py:299` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /parent/login` | handler `routers.parent.parent_login`؛ منبع `Kharazmi_Server/routers/parent.py:114` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /parent/portal` | handler `routers.parent.get_parent_portal_page`؛ منبع `Kharazmi_Server/routers/parent.py:448` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /parent/request_otp` | handler `routers.parent.request_parent_otp`؛ منبع `Kharazmi_Server/routers/parent.py:30` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /parent/select_child` | handler `routers.parent.parent_select_child`؛ منبع `Kharazmi_Server/routers/parent.py:212` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
