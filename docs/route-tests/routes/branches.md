# ممیزی routeهای `branches`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `GET /branches` | handler `routers.branches.list_branches`؛ منبع `Kharazmi_Server/routers/branches.py:113` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /branches` | handler `routers.branches.create_branch`؛ منبع `Kharazmi_Server/routers/branches.py:52` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `PUT /branches/{branch_id}` | handler `routers.branches.update_branch`؛ منبع `Kharazmi_Server/routers/branches.py:75` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /branches/{branch_id}/suspend` | handler `routers.branches.suspend_branch`؛ منبع `Kharazmi_Server/routers/branches.py:96` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /dashboard/branch_stats` | handler `routers.branches.get_branch_stats`؛ منبع `Kharazmi_Server/routers/branches.py:229` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /resources` | handler `routers.branches.list_resources`؛ منبع `Kharazmi_Server/routers/branches.py:171` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /resources` | handler `routers.branches.create_resource`؛ منبع `Kharazmi_Server/routers/branches.py:125` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /resources/bookings` | handler `routers.branches.book_resource`؛ منبع `Kharazmi_Server/routers/branches.py:183` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `PUT /resources/{id}` | handler `routers.branches.update_resource`؛ منبع `Kharazmi_Server/routers/branches.py:149` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
