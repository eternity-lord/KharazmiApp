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
| 1 | `finance` | `POST /finance/debtors/remind` | `Kharazmi_Server/routers/finance.py:2576` | تنها sweep و status ثبت شده؛ باید mock SMS و recipientهای بدهکار، `SmsLog.sent_count` و تکرارپذیری درخواست را با snapshot DB assert کرد؛ network واقعی ممنوع است. |
| 2 | `finance` | `POST /finance/installments` | `Kharazmi_Server/routers/finance.py:1646` | هنوز مقدار amount/due_date، تعلق enrollment، audit log و rollback روی خطای اعتبارسنجی در تست مستقل سنجیده نشده است. |
| 3 | `finance` | `DELETE /finance/installments/{installment_id}` | `Kharazmi_Server/routers/finance.py:1764` | اثر واقعی حذف قسط (paid/archived guard، audit log و تغییر بدهی) و retry در DB تست مستقل ندارد. |
| 4 | `finance` | `PUT /finance/installments/{installment_id}` | `Kharazmi_Server/routers/finance.py:1698` | شاخه‌های تغییر قسط تسویه‌شده (`force`/`reason`)، تغییر سررسید و optimistic/concurrent conflict هنوز با pre/post row assertion پوشش داده نشده‌اند. |
| 5 | `finance` | `POST /finance/installments/{installment_id}/remind` | `Kharazmi_Server/routers/finance.py:1960` | فقط شکل پاسخ sweep شده؛ ارسال mock باید recipient، ثبت `SmsLog` و رفتار retry/rate-limit را بدون gateway واقعی assert کند. |
| 6 | `finance` | `GET /finance/mock_payment_page` | `Kharazmi_Server/routers/finance.py:1355` | این endpoint HTML تست‌شدهٔ معنایی ندارد؛ gateway/authority/amount و escape شدن callback باید بدون redirect واقعی بررسی شود. |
| 7 | `finance` | `GET /finance/parent/dashboard` | `Kharazmi_Server/routers/finance.py:2189` | محدودهٔ دقیق فرزند، empty/full فهرست مالی و redaction نقش والد هنوز value assertion مستقل ندارد. |
| 8 | `finance` | `GET /finance/payment/callback` | `Kharazmi_Server/routers/finance.py:879` | درگاه عمداً خاموش است؛ state machine کال‌بک، authority mismatch، transition و replay تا زمان mock gateway قابل ادعا نیست. |
| 9 | `finance` | `POST /finance/payment/initiate` | `Kharazmi_Server/routers/finance.py:799` | initiate عمداً 400 برمی‌گرداند و هیچ Payment نمی‌سازد؛ قرارداد آیندهٔ gateway/idempotency باید با mock مستقل تعیین و تست شود. |
| 10 | `finance` | `POST /finance/receipt/pdf` | `Kharazmi_Server/routers/finance.py:609` | status کافی نیست؛ بایت‌های PDF، مبلغ/نام/شناسهٔ حواله و IDOR باید با parser و fixture محلی بررسی شوند. |
| 11 | `finance` | `POST /finance/receipt/print` | `Kharazmi_Server/routers/finance.py:566` | چاپ واقعی مجاز نیست؛ receipt_data، مجوز مالک و عدم ایجاد side effect باید با mock printer و snapshot assert شود. |
| 12 | `finance` | `GET /finance/reports/debtors_grouped` | `Kharazmi_Server/routers/finance.py:2500` | گروه‌بندی teacher/age باید با oracle مستقل جمع بدهی و order/empty/filter تطبیق داده شود؛ خروجی فعلاً فقط smoke است. |
| 13 | `finance` | `GET /finance/reports/teacher_settlements_summary` | `Kharazmi_Server/routers/finance.py:2709` | جمع settled/pending و payoutهای معلم هنوز با session scope و reversal مستقل تطبیق داده نشده است. |
| 14 | `finance` | `GET /finance/student/{student_id}/payments` | `Kharazmi_Server/routers/finance.py:2021` | ترتیب، filter دانش‌آموز/تاریخ، برگشتی‌ها و amountهای transaction هنوز row-by-row با oracle مستقل assert نشده‌اند. |
| 15 | `finance` | `POST /finance/transaction/{transaction_id}/refund` | `Kharazmi_Server/routers/finance.py:1394` | refund باید reversal، مبلغ/کیف پول، allocation و retry را در DB نشان دهد؛ status تنها برای این مسیر کافی نیست. |
| 16 | `attendance` | `POST /attendance/qr_check-in` | `Kharazmi_Server/routers/attendance.py:1353` | QR check-in به snapshot قبل/بعد Attendance/SessionLog و duplicate/conflict نیاز دارد؛ side effect فعلی جداگانه assert نشده است. |
| 17 | `attendance` | `DELETE /attendance/session/{session_code}` | `Kharazmi_Server/routers/attendance.py:1288` | حذف session باید وضعیت archived، attendance/ledger مرتبط، restore/retry و تعارض state را در DB نشان دهد؛ فعلاً فقط route smoke است. |
| 18 | `attendance` | `PUT /attendance/session/{session_code}` | `Kharazmi_Server/routers/attendance.py:1051` | ویرایش session باید تاریخ/زمان/حضور و اثر احتمالی مالی را با conflict و rollback بررسی کند؛ assertion مقداری مستقل ندارد. |
| 19 | `attendance` | `POST /attendance/submit_session` | `Kharazmi_Server/routers/attendance.py:631` | guard retry موجود است، اما oracle مبلغ جلسه، سهم معلم/آموزشگاه، همهٔ attendance statusها و rollback کامل هنوز اجرا نشده است. |
| 20 | `attendance` | `POST /attendance/{session_id}/end_live` | `Kharazmi_Server/routers/attendance.py:369` | end_live باید transition نهایی، auto-end، roster و پایان/تکرار هم‌زمان را snapshot کند؛ این route هنوز فقط sweep شده است. |
| 21 | `classes` | `POST /admin/classes/{course_id}/suspend_s` | `Kharazmi_Server/routers/classes.py:370` | suspend باید is_suspended، reason/log، دسترسی کلاس و retry را قبل/بعد assert کند؛ پاسخ موفقیت به‌تنهایی کافی نیست. |
| 22 | `classes` | `POST /classes/create` | `Kharazmi_Server/routers/classes.py:83` | create باید sequence code، branch، conflict schedule، ظرفیت و rollback خطای validation را در DB assert کند. |
| 23 | `classes` | `POST /classes/deletion_requests/{request_id}/approve` | `Kharazmi_Server/routers/classes.py:1164` | approve deletion باید request state، is_deleted کلاس/وابستگان و اثر مالی را اتمیک بررسی کند؛ test مستقل ندارد. |
| 24 | `classes` | `POST /classes/deletion_requests/{request_id}/reject` | `Kharazmi_Server/routers/classes.py:1191` | reject deletion باید status/reason و idempotency درخواست را با مقدار دقیق DB بررسی کند؛ فقط status route ثبت شده است. |
| 25 | `classes` | `POST /classes/pending_approval/bulk_approve` | `Kharazmi_Server/routers/classes.py:1330` | response `message` در RA-sweep-01 اصلاح شده، اما transition approval، conflict و commit اتمیک bulk هنوز pre/post assertion مستقل ندارد. |
| 26 | `classes` | `POST /classes/pending_approval/bulk_reject` | `Kharazmi_Server/routers/classes.py:1354` | bulk reject باید الزام reason، همهٔ course stateها و رفتار partial/duplicate را با snapshot DB بررسی کند؛ هنوز نشده است. |
| 27 | `classes` | `PUT /classes/update` | `Kharazmi_Server/routers/classes.py:1371` | update باید capacity، schedule conflict و guard انتقال معلم پس از billing/settlement را همراه با rollback assert کند. |
| 28 | `classes` | `PUT /classes/update_info/{course_id}` | `Kharazmi_Server/routers/classes.py:1226` | update_info باید فیلدهای قابل‌تغییر، version/conflict و log را دقیقاً مقایسه کند؛ smoke اثر DB را ثابت نمی‌کند. |
| 29 | `classes` | `DELETE /classes/{course_id}` | `Kharazmi_Server/routers/classes.py:960` | delete کلاس باید soft-delete، enrollment/session/ledger scope و retry را assert کند؛ رفتار archive هنوز deep-test نشده است. |
| 30 | `classes` | `POST /classes/{course_id}/request_delete` | `Kharazmi_Server/routers/classes.py:1080` | request_delete باید یک درخواست یکتا با state و actor بسازد و retry/تعارض approval را نشان دهد؛ فقط route inventory موجود است. |
| 31 | `classes` | `POST /enrollments/add` | `Kharazmi_Server/routers/classes.py:391` | add enrollment باید ظرفیت، duplicate، tuition/discount/payment و اثر بدهی را با oracle مستقل و rollback خطا assert کند. |
| 32 | `classes` | `POST /enrollments/add_bulk` | `Kharazmi_Server/routers/classes.py:525` | add_bulk باید atomicity، added/rejected lists، duplicate/limit و عدم ثبت نیمه‌کاره را row-by-row بررسی کند. |
| 33 | `classes` | `DELETE /enrollments/{enrollment_id}` | `Kharazmi_Server/routers/classes.py:573` | delete enrollment باید archive، پرداخت/قسط و بدهی را بدون hard-delete تاریخچه تغییر دهد؛ retry و conflict هنوز assertion ندارد. |
