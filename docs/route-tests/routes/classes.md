# ممیزی routeهای `classes`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `POST /admin/classes/{course_id}/suspend_s` | handler `routers.classes.suspend_class_admin`؛ منبع `Kharazmi_Server/routers/classes.py:370` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /classes/create` | handler `routers.classes.create_class`؛ منبع `Kharazmi_Server/routers/classes.py:83` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /classes/deletion_requests` | handler `routers.classes.list_class_deletion_requests`؛ منبع `Kharazmi_Server/routers/classes.py:1123` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /classes/deletion_requests/{request_id}/approve` | handler `routers.classes.approve_class_deletion`؛ منبع `Kharazmi_Server/routers/classes.py:1164` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /classes/deletion_requests/{request_id}/reject` | handler `routers.classes.reject_class_deletion`؛ منبع `Kharazmi_Server/routers/classes.py:1191` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /classes/list` | handler `routers.classes.get_all_classes`؛ منبع `Kharazmi_Server/routers/classes.py:150` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /classes/pending_approval` | handler `routers.classes.pending_classes_for_admin`؛ منبع `Kharazmi_Server/routers/classes.py:1304` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /classes/pending_approval/bulk_approve` | handler `routers.classes.bulk_approve_classes`؛ منبع `Kharazmi_Server/routers/classes.py:1330` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /classes/pending_approval/bulk_reject` | handler `routers.classes.bulk_reject_classes`؛ منبع `Kharazmi_Server/routers/classes.py:1354` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `PUT /classes/update` | handler `routers.classes.update_class_by_admin`؛ منبع `Kharazmi_Server/routers/classes.py:1371` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `PUT /classes/update_info/{course_id}` | handler `routers.classes.update_class_info`؛ منبع `Kharazmi_Server/routers/classes.py:1226` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /classes/{class_id}/students_full/excel` | handler `routers.classes.get_class_students_excel`؛ منبع `Kharazmi_Server/routers/classes.py:710` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `DELETE /classes/{course_id}` | handler `routers.classes.delete_class_endpoint`؛ منبع `Kharazmi_Server/routers/classes.py:960` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /classes/{course_id}/details` | handler `routers.classes.get_class_details`؛ منبع `Kharazmi_Server/routers/classes.py:301` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /classes/{course_id}/request_delete` | handler `routers.classes.request_class_deletion`؛ منبع `Kharazmi_Server/routers/classes.py:1080` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /classes/{course_id}/suspend` | handler `routers.classes.suspend_class`؛ منبع `Kharazmi_Server/routers/classes.py:353` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /classes/{id}/full_report` | handler `routers.classes.get_class_full_report`؛ منبع `Kharazmi_Server/routers/classes.py:588` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /classes/{id}/students_full` | handler `routers.classes.get_class_students_full`؛ منبع `Kharazmi_Server/routers/classes.py:819` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /enrollments/add` | handler `routers.classes.add_enrollment`؛ منبع `Kharazmi_Server/routers/classes.py:391` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /enrollments/add_bulk` | handler `routers.classes.add_enrollments_bulk`؛ منبع `Kharazmi_Server/routers/classes.py:525` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `DELETE /enrollments/{enrollment_id}` | handler `routers.classes.delete_enrollment`؛ منبع `Kharazmi_Server/routers/classes.py:573` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
