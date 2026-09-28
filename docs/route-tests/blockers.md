# Blockers و موارد مسدود

این فایل وضعیت «نمی‌توانم بدون حدس/تغییر کد تست معتبر بنویسم» را از باگ جدا می‌کند.

| شناسه | scope | علت مسدودشدن | راه ادامه |
|---|---|---|---|
| BLK-001 | 192 route غیر finance/attendance/classes | تست رفتاری هر route هنوز در نوبت router خودش ساخته نشده؛ فقط registry و route doc scaffold وجود دارد. | اجرای ترتیب progress و commit مستقل بعد از هر router. |
| BLK-002 | Android UI | compile مجاز/درخواست‌شده نیست و قرارداد با شبیه‌ساز Python بررسی می‌شود؛ رفتار واقعی Gson سفارشی باید در source تأیید شود. | تکمیل parser و device-checklist؛ بدون ادعای runtime UI. |
| BLK-003 | پیامک، push، gateway | باید network mock شود؛ seed فقط دادهٔ محلی می‌سازد و endpointهای side-effect در تست finance هنوز functional sweep نشده‌اند. | patch مرزی service در test fixture و assert DB log/rollback. |
| BLK-004 | PDF/Excel | مسیرهای exports هنوز functional audit نشده‌اند؛ خروجی باید با openpyxl/reportlab خوانده شود، نه فقط status code. | router exports در اولویت بعدی reports/analytics. |
| BLK-005 | business decisions | Q-001 تا Q-005 پاسخ قطعی ندارند. | تصمیم محصول ثبت شود؛ تا آن زمان تست فقط source-defined behavior را می‌سنجد. |


## ۳۳ route بدون assertion مقداری مستقل در سه router انجام‌شده

این‌ها صادقانه **مسدود** شده‌اند؛ status/JSON آن‌ها در sweep ثبت شده، اما sweep جای assertion کسب‌وکار/DB را نمی‌گیرد. برای هر ردیف دلیل و گام بعدی آمده است.

| # | router | route | source | دلیل blocker |
|---:|---|---|---|---|
| 1 | `finance` | `POST /finance/debtors/remind` | `Kharazmi_Server/routers/finance.py:2576` | sweep status/shape انجام شده، اما assertion مقداری برای gateway/side-effect/role یا گزارش مستقل این route هنوز جدا نشده است؛ تست بعدی باید mock شبکه و snapshot DB داشته باشد. |
| 2 | `finance` | `POST /finance/installments` | `Kharazmi_Server/routers/finance.py:1646` | sweep status/shape انجام شده، اما assertion مقداری برای gateway/side-effect/role یا گزارش مستقل این route هنوز جدا نشده است؛ تست بعدی باید mock شبکه و snapshot DB داشته باشد. |
| 3 | `finance` | `DELETE /finance/installments/{installment_id}` | `Kharazmi_Server/routers/finance.py:1764` | sweep status/shape انجام شده، اما assertion مقداری برای gateway/side-effect/role یا گزارش مستقل این route هنوز جدا نشده است؛ تست بعدی باید mock شبکه و snapshot DB داشته باشد. |
| 4 | `finance` | `PUT /finance/installments/{installment_id}` | `Kharazmi_Server/routers/finance.py:1698` | sweep status/shape انجام شده، اما assertion مقداری برای gateway/side-effect/role یا گزارش مستقل این route هنوز جدا نشده است؛ تست بعدی باید mock شبکه و snapshot DB داشته باشد. |
| 5 | `finance` | `POST /finance/installments/{installment_id}/remind` | `Kharazmi_Server/routers/finance.py:1960` | sweep status/shape انجام شده، اما assertion مقداری برای gateway/side-effect/role یا گزارش مستقل این route هنوز جدا نشده است؛ تست بعدی باید mock شبکه و snapshot DB داشته باشد. |
| 6 | `finance` | `GET /finance/mock_payment_page` | `Kharazmi_Server/routers/finance.py:1355` | sweep status/shape انجام شده، اما assertion مقداری برای gateway/side-effect/role یا گزارش مستقل این route هنوز جدا نشده است؛ تست بعدی باید mock شبکه و snapshot DB داشته باشد. |
| 7 | `finance` | `GET /finance/parent/dashboard` | `Kharazmi_Server/routers/finance.py:2189` | sweep status/shape انجام شده، اما assertion مقداری برای gateway/side-effect/role یا گزارش مستقل این route هنوز جدا نشده است؛ تست بعدی باید mock شبکه و snapshot DB داشته باشد. |
| 8 | `finance` | `GET /finance/payment/callback` | `Kharazmi_Server/routers/finance.py:879` | sweep status/shape انجام شده، اما assertion مقداری برای gateway/side-effect/role یا گزارش مستقل این route هنوز جدا نشده است؛ تست بعدی باید mock شبکه و snapshot DB داشته باشد. |
| 9 | `finance` | `POST /finance/payment/initiate` | `Kharazmi_Server/routers/finance.py:799` | sweep status/shape انجام شده، اما assertion مقداری برای gateway/side-effect/role یا گزارش مستقل این route هنوز جدا نشده است؛ تست بعدی باید mock شبکه و snapshot DB داشته باشد. |
| 10 | `finance` | `POST /finance/receipt/pdf` | `Kharazmi_Server/routers/finance.py:609` | sweep status/shape انجام شده، اما assertion مقداری برای gateway/side-effect/role یا گزارش مستقل این route هنوز جدا نشده است؛ تست بعدی باید mock شبکه و snapshot DB داشته باشد. |
| 11 | `finance` | `POST /finance/receipt/print` | `Kharazmi_Server/routers/finance.py:566` | sweep status/shape انجام شده، اما assertion مقداری برای gateway/side-effect/role یا گزارش مستقل این route هنوز جدا نشده است؛ تست بعدی باید mock شبکه و snapshot DB داشته باشد. |
| 12 | `finance` | `GET /finance/reports/debtors_grouped` | `Kharazmi_Server/routers/finance.py:2500` | sweep status/shape انجام شده، اما assertion مقداری برای gateway/side-effect/role یا گزارش مستقل این route هنوز جدا نشده است؛ تست بعدی باید mock شبکه و snapshot DB داشته باشد. |
| 13 | `finance` | `GET /finance/reports/teacher_settlements_summary` | `Kharazmi_Server/routers/finance.py:2709` | sweep status/shape انجام شده، اما assertion مقداری برای gateway/side-effect/role یا گزارش مستقل این route هنوز جدا نشده است؛ تست بعدی باید mock شبکه و snapshot DB داشته باشد. |
| 14 | `finance` | `GET /finance/student/{student_id}/payments` | `Kharazmi_Server/routers/finance.py:2021` | sweep status/shape انجام شده، اما assertion مقداری برای gateway/side-effect/role یا گزارش مستقل این route هنوز جدا نشده است؛ تست بعدی باید mock شبکه و snapshot DB داشته باشد. |
| 15 | `finance` | `POST /finance/transaction/{transaction_id}/refund` | `Kharazmi_Server/routers/finance.py:1394` | sweep status/shape انجام شده، اما assertion مقداری برای gateway/side-effect/role یا گزارش مستقل این route هنوز جدا نشده است؛ تست بعدی باید mock شبکه و snapshot DB داشته باشد. |
| 16 | `attendance` | `POST /attendance/qr_check-in` | `Kharazmi_Server/routers/attendance.py:1353` | sweep انجام شده، اما mutation/تعارض وضعیت یا rollback این route هنوز assertion مستقل ندارد؛ تست بعدی باید snapshot SessionLog/Attendance/Transaction بگیرد. |
| 17 | `attendance` | `DELETE /attendance/session/{session_code}` | `Kharazmi_Server/routers/attendance.py:1288` | sweep انجام شده، اما mutation/تعارض وضعیت یا rollback این route هنوز assertion مستقل ندارد؛ تست بعدی باید snapshot SessionLog/Attendance/Transaction بگیرد. |
| 18 | `attendance` | `PUT /attendance/session/{session_code}` | `Kharazmi_Server/routers/attendance.py:1051` | sweep انجام شده، اما mutation/تعارض وضعیت یا rollback این route هنوز assertion مستقل ندارد؛ تست بعدی باید snapshot SessionLog/Attendance/Transaction بگیرد. |
| 19 | `attendance` | `POST /attendance/submit_session` | `Kharazmi_Server/routers/attendance.py:631` | sweep انجام شده، اما mutation/تعارض وضعیت یا rollback این route هنوز assertion مستقل ندارد؛ تست بعدی باید snapshot SessionLog/Attendance/Transaction بگیرد. |
| 20 | `attendance` | `POST /attendance/{session_id}/end_live` | `Kharazmi_Server/routers/attendance.py:369` | sweep انجام شده، اما mutation/تعارض وضعیت یا rollback این route هنوز assertion مستقل ندارد؛ تست بعدی باید snapshot SessionLog/Attendance/Transaction بگیرد. |
| 21 | `classes` | `POST /admin/classes/{course_id}/suspend_s` | `Kharazmi_Server/routers/classes.py:370` | sweep انجام شده، اما write/state transition این route هنوز assertion مستقل ندارد؛ تست بعدی باید pre/post rows و rollback/تعارض approval را assert کند. |
| 22 | `classes` | `POST /classes/create` | `Kharazmi_Server/routers/classes.py:83` | sweep انجام شده، اما write/state transition این route هنوز assertion مستقل ندارد؛ تست بعدی باید pre/post rows و rollback/تعارض approval را assert کند. |
| 23 | `classes` | `POST /classes/deletion_requests/{request_id}/approve` | `Kharazmi_Server/routers/classes.py:1164` | sweep انجام شده، اما write/state transition این route هنوز assertion مستقل ندارد؛ تست بعدی باید pre/post rows و rollback/تعارض approval را assert کند. |
| 24 | `classes` | `POST /classes/deletion_requests/{request_id}/reject` | `Kharazmi_Server/routers/classes.py:1191` | sweep انجام شده، اما write/state transition این route هنوز assertion مستقل ندارد؛ تست بعدی باید pre/post rows و rollback/تعارض approval را assert کند. |
| 25 | `classes` | `POST /classes/pending_approval/bulk_approve` | `Kharazmi_Server/routers/classes.py:1330` | sweep انجام شده، اما write/state transition این route هنوز assertion مستقل ندارد؛ تست بعدی باید pre/post rows و rollback/تعارض approval را assert کند. |
| 26 | `classes` | `POST /classes/pending_approval/bulk_reject` | `Kharazmi_Server/routers/classes.py:1354` | sweep انجام شده، اما write/state transition این route هنوز assertion مستقل ندارد؛ تست بعدی باید pre/post rows و rollback/تعارض approval را assert کند. |
| 27 | `classes` | `PUT /classes/update` | `Kharazmi_Server/routers/classes.py:1371` | sweep انجام شده، اما write/state transition این route هنوز assertion مستقل ندارد؛ تست بعدی باید pre/post rows و rollback/تعارض approval را assert کند. |
| 28 | `classes` | `PUT /classes/update_info/{course_id}` | `Kharazmi_Server/routers/classes.py:1226` | sweep انجام شده، اما write/state transition این route هنوز assertion مستقل ندارد؛ تست بعدی باید pre/post rows و rollback/تعارض approval را assert کند. |
| 29 | `classes` | `DELETE /classes/{course_id}` | `Kharazmi_Server/routers/classes.py:960` | sweep انجام شده، اما write/state transition این route هنوز assertion مستقل ندارد؛ تست بعدی باید pre/post rows و rollback/تعارض approval را assert کند. |
| 30 | `classes` | `POST /classes/{course_id}/request_delete` | `Kharazmi_Server/routers/classes.py:1080` | sweep انجام شده، اما write/state transition این route هنوز assertion مستقل ندارد؛ تست بعدی باید pre/post rows و rollback/تعارض approval را assert کند. |
| 31 | `classes` | `POST /enrollments/add` | `Kharazmi_Server/routers/classes.py:391` | sweep انجام شده، اما write/state transition این route هنوز assertion مستقل ندارد؛ تست بعدی باید pre/post rows و rollback/تعارض approval را assert کند. |
| 32 | `classes` | `POST /enrollments/add_bulk` | `Kharazmi_Server/routers/classes.py:525` | sweep انجام شده، اما write/state transition این route هنوز assertion مستقل ندارد؛ تست بعدی باید pre/post rows و rollback/تعارض approval را assert کند. |
| 33 | `classes` | `DELETE /enrollments/{enrollment_id}` | `Kharazmi_Server/routers/classes.py:573` | sweep انجام شده، اما write/state transition این route هنوز assertion مستقل ندارد؛ تست بعدی باید pre/post rows و rollback/تعارض approval را assert کند. |
