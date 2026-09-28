# ممیزی routeهای `auth`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `POST /auth/change-mobile` | handler `routers.auth.change_mobile`؛ منبع `Kharazmi_Server/routers/auth.py:699` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /auth/change-password` | handler `routers.auth.change_password`؛ منبع `Kharazmi_Server/routers/auth.py:308` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /auth/device_token` | handler `routers.auth.register_device_token`؛ منبع `Kharazmi_Server/routers/auth.py:597` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /auth/login` | handler `routers.auth.login_user`؛ منبع `Kharazmi_Server/routers/auth.py:23` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /auth/logout` | handler `routers.auth.logout_user`؛ منبع `Kharazmi_Server/routers/auth.py:368` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /auth/me` | handler `routers.auth.get_me`؛ منبع `Kharazmi_Server/routers/auth.py:393` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /auth/student/login` | handler `routers.auth.student_login`؛ منبع `Kharazmi_Server/routers/auth.py:529` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /auth/student/request_otp` | handler `routers.auth.request_student_otp`؛ منبع `Kharazmi_Server/routers/auth.py:459` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /notifications` | handler `routers.auth.get_notifications`؛ منبع `Kharazmi_Server/routers/auth.py:622` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /notifications/read_all` | handler `routers.auth.mark_all_notifications_read`؛ منبع `Kharazmi_Server/routers/auth.py:684` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /notifications/unread_count` | handler `routers.auth.get_unread_notifications_count`؛ منبع `Kharazmi_Server/routers/auth.py:652` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /notifications/{id}/read` | handler `routers.auth.mark_notification_read`؛ منبع `Kharazmi_Server/routers/auth.py:669` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
