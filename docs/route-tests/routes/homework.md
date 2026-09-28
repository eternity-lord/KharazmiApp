# ممیزی routeهای `homework`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `POST /homework/create` | handler `routers.homework.create_homework`؛ منبع `Kharazmi_Server/routers/homework.py:64` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /homework/parent/child/{student_id}` | handler `routers.homework.get_parent_child_homework`؛ منبع `Kharazmi_Server/routers/homework.py:300` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /homework/student/list` | handler `routers.homework.get_student_homework_list`؛ منبع `Kharazmi_Server/routers/homework.py:147` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /homework/submissions/{homework_id}/submit` | handler `routers.homework.submit_homework_file`؛ منبع `Kharazmi_Server/routers/homework.py:186` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /homework/submissions/{sub_id}/grade` | handler `routers.homework.grade_homework_submission`؛ منبع `Kharazmi_Server/routers/homework.py:253` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `DELETE /homework/{id}` | handler `routers.homework.delete_homework`؛ منبع `Kharazmi_Server/routers/homework.py:124` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
