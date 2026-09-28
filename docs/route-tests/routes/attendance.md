# ممیزی routeهای `attendance`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `GET /admin/live_sessions` | handler `routers.attendance.get_admin_live_sessions`؛ منبع `Kharazmi_Server/routers/attendance.py:1434` | 1 | inventory/fixture | success,value,DB,state,role | سبزِ اولیه |
| `GET /admin/live_sessions/{session_id}/roster` | handler `routers.attendance.get_admin_live_session_roster`؛ منبع `Kharazmi_Server/routers/attendance.py:1492` | 1 | inventory/fixture | success,value,DB,state,role | سبزِ اولیه |
| `POST /attendance/get` | handler `routers.attendance.get_class_attendance`؛ منبع `Kharazmi_Server/routers/attendance.py:585` | 1 | inventory/fixture | success,value,DB,state,role | سبزِ اولیه |
| `POST /attendance/get_history` | handler `routers.attendance.get_history`؛ منبع `Kharazmi_Server/routers/attendance.py:881` | 1 | inventory/fixture | success,value,DB,state,role | سبزِ اولیه |
| `GET /attendance/live/current` | handler `routers.attendance.get_current_live_session`؛ منبع `Kharazmi_Server/routers/attendance.py:551` | 1 | inventory/fixture | success,value,DB,state,role | سبزِ اولیه |
| `POST /attendance/qr_check-in` | handler `routers.attendance.qr_student_check_in`؛ منبع `Kharazmi_Server/routers/attendance.py:1353` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `DELETE /attendance/session/{session_code}` | handler `routers.attendance.delete_session_endpoint`؛ منبع `Kharazmi_Server/routers/attendance.py:1288` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /attendance/session/{session_code}` | handler `routers.attendance.get_session_details`؛ منبع `Kharazmi_Server/routers/attendance.py:1003` | 1 | inventory/fixture | success,value,DB,state,role | سبزِ اولیه |
| `PUT /attendance/session/{session_code}` | handler `routers.attendance.edit_past_session`؛ منبع `Kharazmi_Server/routers/attendance.py:1051` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /attendance/student_history` | handler `routers.attendance.get_student_attendance_history`؛ منبع `Kharazmi_Server/routers/attendance.py:926` | 1 | inventory/fixture | success,value,DB,state,role | سبزِ اولیه |
| `POST /attendance/submit_session` | handler `routers.attendance.submit_session_and_calculate`؛ منبع `Kharazmi_Server/routers/attendance.py:631` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /attendance/{course_id}/start_live` | handler `routers.attendance.start_live_session`؛ منبع `Kharazmi_Server/routers/attendance.py:313` | 1 | inventory/fixture | success,value,DB,state,role | سبزِ اولیه |
| `POST /attendance/{session_id}/cancel_live` | handler `routers.attendance.cancel_live_session`؛ منبع `Kharazmi_Server/routers/attendance.py:449` | 1 | inventory/fixture | success,value,DB,state,role | سبزِ اولیه |
| `POST /attendance/{session_id}/end_live` | handler `routers.attendance.end_live_session`؛ منبع `Kharazmi_Server/routers/attendance.py:369` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /attendance/{session_id}/live_status` | handler `routers.attendance.save_live_status`؛ منبع `Kharazmi_Server/routers/attendance.py:509` | 1 | inventory/fixture | success,value,DB,state,role | سبزِ اولیه |

## تست‌های این نوبت

- `tests/route_audit/test_audit_attendance.py:29-45` خواندن مقداری session/class/student history را بررسی می‌کند.
- `tests/route_audit/test_audit_attendance.py:48-78` چرخهٔ start/status/cancel و بدون اثر مالی را بررسی می‌کند.
- `tests/route_audit/test_audit_attendance.py:81-92` live read/roster و دسترسی نقش‌ها را بررسی می‌کند.
- `tests/route_audit/test_audit_attendance.py:95-103` کلاس معلق را بررسی می‌کند.
