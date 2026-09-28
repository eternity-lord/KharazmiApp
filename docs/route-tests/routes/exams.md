# ممیزی routeهای `exams`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `POST /exams/attempts/{attempt_id}/submit` | handler `routers.exams.submit_exam_attempt`؛ منبع `Kharazmi_Server/routers/exams.py:229` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /exams/attempts/{exam_id}/start` | handler `routers.exams.start_exam_attempt`؛ منبع `Kharazmi_Server/routers/exams.py:163` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /exams/create` | handler `routers.exams.create_exam`؛ منبع `Kharazmi_Server/routers/exams.py:45` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /exams/student/list` | handler `routers.exams.get_student_exams_list`؛ منبع `Kharazmi_Server/routers/exams.py:125` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /exams/{id}/questions` | handler `routers.exams.add_exam_question`؛ منبع `Kharazmi_Server/routers/exams.py:95` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /students/{student_id}/report_card` | handler `routers.exams.get_student_report_card`؛ منبع `Kharazmi_Server/routers/exams.py:319` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /students/{student_id}/report_card/pdf` | handler `routers.exams.export_report_card_pdf`؛ منبع `Kharazmi_Server/routers/exams.py:383` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
