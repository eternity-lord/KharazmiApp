# ممیزی routeهای `teachers`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `GET /teachers/list` | handler `routers.teachers.get_all_teachers`؛ منبع `Kharazmi_Server/routers/teachers.py:103` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /teachers/list/excel` | handler `routers.teachers.get_teachers_excel`؛ منبع `Kharazmi_Server/routers/teachers.py:668` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /teachers/register` | handler `routers.teachers.register_teacher`؛ منبع `Kharazmi_Server/routers/teachers.py:33` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `PUT /teachers/update/{teacher_id}` | handler `routers.teachers.update_teacher`؛ منبع `Kharazmi_Server/routers/teachers.py:499` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /teachers/{id}/full_profile` | handler `routers.teachers.get_teacher_full_profile`؛ منبع `Kharazmi_Server/routers/teachers.py:386` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /teachers/{id}/today_summary` | handler `routers.teachers.get_teacher_today_summary`؛ منبع `Kharazmi_Server/routers/teachers.py:200` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /teachers/{id}/upload_photo` | handler `routers.teachers.upload_teacher_photo`؛ منبع `Kharazmi_Server/routers/teachers.py:612` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /teachers/{teacher_id}` | handler `routers.teachers.get_teacher_profile`؛ منبع `Kharazmi_Server/routers/teachers.py:466` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /teachers/{teacher_id}/classes` | handler `routers.teachers.get_my_classes`؛ منبع `Kharazmi_Server/routers/teachers.py:231` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /teachers/{teacher_id}/collaboration_summary` | handler `routers.teachers.get_teacher_collaboration_summary`؛ منبع `Kharazmi_Server/routers/teachers.py:185` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /teachers/{teacher_id}/communication_history` | handler `routers.teachers.get_teacher_communication_history`؛ منبع `Kharazmi_Server/routers/teachers.py:152` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /teachers/{teacher_id}/incomplete_classes` | handler `routers.teachers.get_teacher_incomplete_classes`؛ منبع `Kharazmi_Server/routers/teachers.py:343` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /teachers/{teacher_id}/pending_classes` | handler `routers.teachers.get_teacher_pending_classes`؛ منبع `Kharazmi_Server/routers/teachers.py:1233` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /teachers/{teacher_id}/pending_settlement` | handler `routers.teachers.get_pending_settlement`؛ منبع `Kharazmi_Server/routers/teachers.py:741` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /teachers/{teacher_id}/settle` | handler `routers.teachers.settle_teacher_sessions`؛ منبع `Kharazmi_Server/routers/teachers.py:893` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /teachers/{teacher_id}/settlement_history` | handler `routers.teachers.get_settlement_history`؛ منبع `Kharazmi_Server/routers/teachers.py:1046` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `PUT /teachers/{teacher_id}/settlements/{settlement_id}/edit` | handler `routers.teachers.edit_teacher_settlement`؛ منبع `Kharazmi_Server/routers/teachers.py:1182` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /teachers/{teacher_id}/settlements/{settlement_id}/reverse` | handler `routers.teachers.reverse_teacher_settlement`؛ منبع `Kharazmi_Server/routers/teachers.py:1163` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
