# ممیزی routeهای `admin`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `POST /admin/approve_class/{course_id}` | handler `routers.admin.approve_class`؛ منبع `Kharazmi_Server/routers/admin.py:703` | 1 | conflict,state | سبز؛ pending course با schedule conflict، 409 و بدون mutation | — |
| `POST /admin/classes/suspend_bulk` | handler `routers.admin.suspend_bulk_classes`؛ منبع `Kharazmi_Server/routers/admin.py:1534` | 1 | success,value,state,restore | سبز؛ success/failed و restore flags assert شد | — |
| `GET /admin/deleted_classes` | handler `routers.admin.get_deleted_classes`؛ منبع `Kharazmi_Server/routers/admin.py:1770` | 1 | success,value,DB,shape | سبز؛ آرشیو فقط شامل کلاس حذف‌شده و شمارش‌هاست | — |
| `GET /admin/deleted_classes/{course_id}` | handler `routers.admin.get_deleted_class_detail`؛ منبع `Kharazmi_Server/routers/admin.py:1849` | 1 | success,value,DB,shape | سبز؛ جزئیات کلاس آرشیوی و counters دقیق است | — |
| `POST /admin/deleted_classes/{course_id}/restore` | handler `routers.admin.restore_deleted_class`؛ منبع `Kharazmi_Server/routers/admin.py:1915` | 1 | state,DB,idempotency | سبز؛ metadata_only و بدون اثر مالی؛ restore دوباره هنوز در نوبت conflict کامل است | — |
| `GET /admin/institute_settings` | handler `routers.admin.get_institute_settings`؛ منبع `Kharazmi_Server/routers/admin.py:1557` | 1 | success,value,role,shape | سبز؛ admin کامل و teacher بدون card fields | — |
| `PUT /admin/institute_settings` | handler `routers.admin.update_institute_settings`؛ منبع `Kharazmi_Server/routers/admin.py:1575` | 1 | success,value,DB,restore | سبز؛ مقدار تغییر و restore seed assert شد | — |
| `POST /admin/institute_settings/upload_logo` | handler `routers.admin.upload_institute_logo`؛ منبع `Kharazmi_Server/routers/admin.py:1614` | 1 | validation,side-effect | سبز؛ extension نامعتبر 400 و بدون write | — |
| `GET /admin/parent_contacts` | handler `routers.admin.get_parent_contacts`؛ منبع `Kharazmi_Server/routers/admin.py:739` | 1 | success,value,filter,shape | سبز؛ class_id=1 فیلتر و parent contact assert شد | — |
| `GET /admin/pending_classes` | handler `routers.admin.get_pending_classes`؛ منبع `Kharazmi_Server/routers/admin.py:632` | 1 | success,value,shape | سبز؛ کلاس pending id=5 و conflict metadata assert شد | — |
| `GET /admin/pricing_table` | handler `routers.admin.get_pricing_table`؛ منبع `Kharazmi_Server/routers/admin.py:2044` | 1 | success,value,shape | سبز؛ مقادیر seed جدول assert شد | — |
| `PUT /admin/pricing_table` | handler `routers.admin.update_pricing_table`؛ منبع `Kharazmi_Server/routers/admin.py:2050` | 1 | success,value,DB,restore | سبز؛ update و restore ردیف seed assert شد | — |
| `DELETE /admin/reject_class/{course_id}` | handler `routers.admin.reject_class`؛ منبع `Kharazmi_Server/routers/admin.py:339` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /admin/session_history` | handler `routers.admin.admin_session_history`؛ منبع `Kharazmi_Server/routers/admin.py:2285` | 1 | success,value,filter,shape | سبز؛ count/items و export mode assert شد | — |
| `POST /admin/session_history/{session_id}/reopen` | handler `routers.admin.reopen_admin_session`؛ منبع `Kharazmi_Server/routers/admin.py:2378` | 1 | success,state,conflict | سبز؛ session بدون اثر مالی reopen و billed session با 409 | — |
| `GET /admin/students/search` | handler `routers.admin.search_admin_students`؛ منبع `Kharazmi_Server/routers/admin.py:2067` | 1 | success,value,filter,shape | سبز؛ query ملی و رکورد دقیق assert شد | — |
| `DELETE /admin/students/{id}` | handler `routers.admin.delete_student`؛ منبع `Kharazmi_Server/routers/admin.py:1293` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /admin/students/{id}/full_profile` | handler `routers.admin.get_student_full_profile`؛ منبع `Kharazmi_Server/routers/admin.py:406` | 1 | success,value,DB,shape | سبز؛ enrollment ids و total debt assert شد | — |
| `POST /admin/students/{id}/toggle_suspend` | handler `routers.admin.toggle_suspend_student`؛ منبع `Kharazmi_Server/routers/admin.py:1315` | 1 | success,state,restore | سبز؛ toggle و restore flag assert شد | — |
| `GET /admin/teachers/search` | handler `routers.admin.search_admin_teachers`؛ منبع `Kharazmi_Server/routers/admin.py:2097` | 1 | success,value,filter,shape | سبز؛ query ملی و نام دقیق assert شد | — |
| `GET /admin/teachers/{id}/credentials` | handler `routers.admin.get_teacher_credentials`؛ منبع `Kharazmi_Server/routers/admin.py:2144` | 1 | success,value,shape | سبز؛ credentials seed assert شد | — |
| `PUT /admin/teachers/{id}/credentials` | handler `routers.admin.update_teacher_credentials`؛ منبع `Kharazmi_Server/routers/admin.py:2209` | 1 | success,state,restore | سبز؛ card update و shadow restore assert شد | — |
| `POST /admin/teachers/{id}/credentials/reset_password` | handler `routers.admin.reset_teacher_password`؛ منبع `Kharazmi_Server/routers/admin.py:2161` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `DELETE /admin/teachers/{teacher_id}` | handler `routers.admin.delete_teacher`؛ منبع `Kharazmi_Server/routers/admin.py:313` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /admin/teachers/{teacher_id}/suspend` | handler `routers.admin.suspend_teacher`؛ منبع `Kharazmi_Server/routers/admin.py:299` | 1 | success,state,restore | سبز؛ toggle معلم و restore flag assert شد | — |
| `GET /admin/today_summary` | handler `routers.admin.get_admin_today_summary`؛ منبع `Kharazmi_Server/routers/admin.py:34` | 1 | success,value,shape | سبز؛ تاریخ canonical و scheduled count assert شد | — |
| `GET /admin/transactions/list` | handler `routers.admin.get_all_transactions`؛ منبع `Kharazmi_Server/routers/admin.py:893` | 1 | success,value,filter,shape | سبز؛ ترتیب، حذف reversed و نام کلاس assert شد | — |
| `GET /admin/transactions/list/excel` | handler `routers.admin.get_transactions_excel`؛ منبع `Kharazmi_Server/routers/admin.py:793` | 1 | success,non-JSON,shape | سبز؛ XLSX content-type و non-empty body assert شد | — |
| `DELETE /admin/transactions/{id}` | handler `routers.admin.delete_transaction`؛ منبع `Kharazmi_Server/routers/admin.py:935` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `PUT /admin/transactions/{id}` | handler `routers.admin.update_transaction`؛ منبع `Kharazmi_Server/routers/admin.py:1113` | 1 | success,value,DB,ledger,restore | سبز؛ delta مبلغ، wallet invariant و restore assert شد | — |
| `GET /config/share` | handler `routers.admin.get_share_config`؛ منبع `Kharazmi_Server/routers/admin.py:591` | 1 | success,value,shape | سبز؛ count_1/count_15 دقیق assert شد | — |
| `POST /config/share/update` | handler `routers.admin.update_share_config`؛ منبع `Kharazmi_Server/routers/admin.py:604` | 1 | success,value,DB,restore | سبز؛ update و restore سهم‌ها assert شد | — |
| `GET /dashboard/stats` | handler `routers.admin.get_dashboard_stats`؛ منبع `Kharazmi_Server/routers/admin.py:51` | 1 | success,value,shape | سبز؛ count/last course/transaction shape assert شد؛ RA-admin-01 xfail جداست | RA-admin-01 |
| `GET /sms/history` | handler `routers.admin.get_sms_history`؛ منبع `Kharazmi_Server/routers/admin.py:183` | 1 | success,value,redaction,shape | سبز؛ log و mask عددی assert شد | — |
| `POST /sms/send` | handler `routers.admin.send_sms`؛ منبع `Kharazmi_Server/routers/admin.py:151` | 1 | success,value,DB,local-only | سبز؛ فقط SmsLog محلی و cleanup؛ شبکه/SMS واقعی ممنوع | — |
| `POST /sms/send_bulk` | handler `routers.admin.send_bulk_sms`؛ منبع `Kharazmi_Server/routers/admin.py:1495` | 1 | success,value,DB,local-only | سبز؛ success/failed و SmsLog محلی assert شد | — |
| `POST /teachers/approve/{teacher_id}` | handler `routers.admin.approve_teacher`؛ منبع `Kharazmi_Server/routers/admin.py:271` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /teachers/pending` | handler `routers.admin.get_pending_teachers`؛ منبع `Kharazmi_Server/routers/admin.py:203` | 1 | success,empty,shape | سبز؛ empty list صریح assert شد | — |
| `DELETE /teachers/reject/{teacher_id}` | handler `routers.admin.reject_teacher`؛ منبع `Kharazmi_Server/routers/admin.py:284` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /test/debt_calculation` | handler `routers.admin.test_debt_calculation`؛ منبع `Kharazmi_Server/routers/admin.py:98` | 1 | success,value,oracle | سبز؛ wallet و debt قراردادی assert شد | — |
| `POST /test/transaction_logic` | handler `routers.admin.test_transaction_logic`؛ منبع `Kharazmi_Server/routers/admin.py:1338` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |

## تست‌های این نوبت

- `tests/route_audit/test_audit_admin.py:60-81` dashboard، debt، transaction list، search دانش‌آموز/معلم را با مقدار seed بررسی می‌کند؛ RA-admin-01 در خط 83 با fallback مستقیم `student_id` سبز شده است.
- `tests/route_audit/test_audit_admin.py:88-118` settings، share، pricing، session history، export، pending و parent contacts را بررسی می‌کند.
- `tests/route_audit/test_audit_admin.py:121-142` profile، deleted classes، today summary و credentials را بررسی می‌کند.
- `tests/route_audit/test_audit_admin.py:145-183` SMS محلی، mask عددی، share/pricing update و restoration را بررسی می‌کند.
- `tests/route_audit/test_audit_admin.py:184-218` XLSX، upload validation، credential update و conflict approval را بدون شبکه/فایل valid production بررسی می‌کند.
- `tests/route_audit/test_audit_admin.py:220-311` transaction delta، bulk state، session reopen، metadata-only restore و toggleهای دانش‌آموز/معلم را بررسی می‌کند.

هر ۴۱ route admin حداقل یک assertion دارد. چند route با guard منفی یا round-trip پوشش داده شده‌اند (نه همهٔ شاخه‌های happy-path): حذف‌های hard-delete، approval/rejection با دادهٔ pending واقعی، و gateway/مدیریت چندحالته هنوز می‌توانند در ممیزی عمقی بعدی گسترش یابند.
