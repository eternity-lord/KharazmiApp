# ممیزی routeهای `students`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `POST /admin/students/{id}/send_portal_link` | handler `routers.students.send_portal_link`؛ منبع `Kharazmi_Server/routers/students.py:903` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /grades/submit` | handler `routers.students.submit_grade`؛ منبع `Kharazmi_Server/routers/students.py:338` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /students/my_profile` | handler `routers.students.get_student_my_profile`؛ منبع `Kharazmi_Server/routers/students.py:559` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /students/register` | handler `routers.students.register_student`؛ منبع `Kharazmi_Server/routers/students.py:40` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /students/register_and_enroll` | handler `routers.students.register_and_enroll_student`؛ منبع `Kharazmi_Server/routers/students.py:83` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /students/search` | handler `routers.students.search_students`؛ منبع `Kharazmi_Server/routers/students.py:264` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /students/search_simple` | handler `routers.students.search_students_simple`؛ منبع `Kharazmi_Server/routers/students.py:279` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `PUT /students/update/{student_id}` | handler `routers.students.update_student`؛ منبع `Kharazmi_Server/routers/students.py:724` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /students/{id}/upload_photo` | handler `routers.students.upload_student_photo`؛ منبع `Kharazmi_Server/routers/students.py:814` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /students/{student_id}` | handler `routers.students.get_student_profile`؛ منبع `Kharazmi_Server/routers/students.py:699` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /students/{student_id}/communication_history` | handler `routers.students.get_student_communication_history`؛ منبع `Kharazmi_Server/routers/students.py:476` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /students/{student_id}/grades` | handler `routers.students.get_student_grades`؛ منبع `Kharazmi_Server/routers/students.py:401` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /students/{student_id}/installments` | handler `routers.students.get_student_installments`؛ منبع `Kharazmi_Server/routers/students.py:868` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
