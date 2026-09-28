# ممیزی routeهای `admin`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `POST /admin/approve_class/{course_id}` | handler `routers.admin.approve_class`؛ منبع `Kharazmi_Server/routers/admin.py:703` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /admin/classes/suspend_bulk` | handler `routers.admin.suspend_bulk_classes`؛ منبع `Kharazmi_Server/routers/admin.py:1534` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /admin/deleted_classes` | handler `routers.admin.get_deleted_classes`؛ منبع `Kharazmi_Server/routers/admin.py:1770` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /admin/deleted_classes/{course_id}` | handler `routers.admin.get_deleted_class_detail`؛ منبع `Kharazmi_Server/routers/admin.py:1849` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /admin/deleted_classes/{course_id}/restore` | handler `routers.admin.restore_deleted_class`؛ منبع `Kharazmi_Server/routers/admin.py:1915` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /admin/institute_settings` | handler `routers.admin.get_institute_settings`؛ منبع `Kharazmi_Server/routers/admin.py:1557` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `PUT /admin/institute_settings` | handler `routers.admin.update_institute_settings`؛ منبع `Kharazmi_Server/routers/admin.py:1575` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /admin/institute_settings/upload_logo` | handler `routers.admin.upload_institute_logo`؛ منبع `Kharazmi_Server/routers/admin.py:1614` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /admin/parent_contacts` | handler `routers.admin.get_parent_contacts`؛ منبع `Kharazmi_Server/routers/admin.py:739` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /admin/pending_classes` | handler `routers.admin.get_pending_classes`؛ منبع `Kharazmi_Server/routers/admin.py:632` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /admin/pricing_table` | handler `routers.admin.get_pricing_table`؛ منبع `Kharazmi_Server/routers/admin.py:2044` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `PUT /admin/pricing_table` | handler `routers.admin.update_pricing_table`؛ منبع `Kharazmi_Server/routers/admin.py:2050` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `DELETE /admin/reject_class/{course_id}` | handler `routers.admin.reject_class`؛ منبع `Kharazmi_Server/routers/admin.py:339` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /admin/session_history` | handler `routers.admin.admin_session_history`؛ منبع `Kharazmi_Server/routers/admin.py:2285` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /admin/session_history/{session_id}/reopen` | handler `routers.admin.reopen_admin_session`؛ منبع `Kharazmi_Server/routers/admin.py:2378` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /admin/students/search` | handler `routers.admin.search_admin_students`؛ منبع `Kharazmi_Server/routers/admin.py:2067` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `DELETE /admin/students/{id}` | handler `routers.admin.delete_student`؛ منبع `Kharazmi_Server/routers/admin.py:1293` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /admin/students/{id}/full_profile` | handler `routers.admin.get_student_full_profile`؛ منبع `Kharazmi_Server/routers/admin.py:406` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /admin/students/{id}/toggle_suspend` | handler `routers.admin.toggle_suspend_student`؛ منبع `Kharazmi_Server/routers/admin.py:1315` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /admin/teachers/search` | handler `routers.admin.search_admin_teachers`؛ منبع `Kharazmi_Server/routers/admin.py:2097` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /admin/teachers/{id}/credentials` | handler `routers.admin.get_teacher_credentials`؛ منبع `Kharazmi_Server/routers/admin.py:2144` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `PUT /admin/teachers/{id}/credentials` | handler `routers.admin.update_teacher_credentials`؛ منبع `Kharazmi_Server/routers/admin.py:2209` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /admin/teachers/{id}/credentials/reset_password` | handler `routers.admin.reset_teacher_password`؛ منبع `Kharazmi_Server/routers/admin.py:2161` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `DELETE /admin/teachers/{teacher_id}` | handler `routers.admin.delete_teacher`؛ منبع `Kharazmi_Server/routers/admin.py:313` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /admin/teachers/{teacher_id}/suspend` | handler `routers.admin.suspend_teacher`؛ منبع `Kharazmi_Server/routers/admin.py:299` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /admin/today_summary` | handler `routers.admin.get_admin_today_summary`؛ منبع `Kharazmi_Server/routers/admin.py:34` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /admin/transactions/list` | handler `routers.admin.get_all_transactions`؛ منبع `Kharazmi_Server/routers/admin.py:893` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /admin/transactions/list/excel` | handler `routers.admin.get_transactions_excel`؛ منبع `Kharazmi_Server/routers/admin.py:793` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `DELETE /admin/transactions/{id}` | handler `routers.admin.delete_transaction`؛ منبع `Kharazmi_Server/routers/admin.py:935` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `PUT /admin/transactions/{id}` | handler `routers.admin.update_transaction`؛ منبع `Kharazmi_Server/routers/admin.py:1113` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /config/share` | handler `routers.admin.get_share_config`؛ منبع `Kharazmi_Server/routers/admin.py:591` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /config/share/update` | handler `routers.admin.update_share_config`؛ منبع `Kharazmi_Server/routers/admin.py:604` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /dashboard/stats` | handler `routers.admin.get_dashboard_stats`؛ منبع `Kharazmi_Server/routers/admin.py:51` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /sms/history` | handler `routers.admin.get_sms_history`؛ منبع `Kharazmi_Server/routers/admin.py:183` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /sms/send` | handler `routers.admin.send_sms`؛ منبع `Kharazmi_Server/routers/admin.py:151` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /sms/send_bulk` | handler `routers.admin.send_bulk_sms`؛ منبع `Kharazmi_Server/routers/admin.py:1495` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /teachers/approve/{teacher_id}` | handler `routers.admin.approve_teacher`؛ منبع `Kharazmi_Server/routers/admin.py:271` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /teachers/pending` | handler `routers.admin.get_pending_teachers`؛ منبع `Kharazmi_Server/routers/admin.py:203` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `DELETE /teachers/reject/{teacher_id}` | handler `routers.admin.reject_teacher`؛ منبع `Kharazmi_Server/routers/admin.py:284` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /test/debt_calculation` | handler `routers.admin.test_debt_calculation`؛ منبع `Kharazmi_Server/routers/admin.py:98` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /test/transaction_logic` | handler `routers.admin.test_transaction_logic`؛ منبع `Kharazmi_Server/routers/admin.py:1338` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
