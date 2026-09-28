# ممیزی routeهای `finance`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `POST /finance/debtors/remind` | handler `routers.finance.remind_debtors`؛ منبع `Kharazmi_Server/routers/finance.py:2576` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /finance/installments` | handler `routers.finance.get_all_installments`؛ منبع `Kharazmi_Server/routers/finance.py:1588` | 1 | success,value,oracle | سبزِ اولیه | — |
| `POST /finance/installments` | handler `routers.finance.create_installment`؛ منبع `Kharazmi_Server/routers/finance.py:1646` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت تکمیل finance نوشته می‌شود | — |
| `DELETE /finance/installments/{installment_id}` | handler `routers.finance.delete_installment`؛ منبع `Kharazmi_Server/routers/finance.py:1764` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `PUT /finance/installments/{installment_id}` | handler `routers.finance.update_installment`؛ منبع `Kharazmi_Server/routers/finance.py:1698` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /finance/installments/{installment_id}/pay` | handler `routers.finance.pay_installment_manually`؛ منبع `Kharazmi_Server/routers/finance.py:1809` | 1 | success,value,DB,oracle,idempotency | سبزِ اولیه | — |
| `POST /finance/installments/{installment_id}/remind` | handler `routers.finance.send_installment_payment_reminder`؛ منبع `Kharazmi_Server/routers/finance.py:1960` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /finance/invoice/{enrollment_id}` | handler `routers.finance.get_invoice_details`؛ منبع `Kharazmi_Server/routers/finance.py:2264` | 1 | success,value,oracle | سبزِ اولیه | — |
| `GET /finance/mock_payment_page` | handler `routers.finance.mock_payment_page`؛ منبع `Kharazmi_Server/routers/finance.py:1355` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /finance/parent/dashboard` | handler `routers.finance.get_parent_financial_dashboard`؛ منبع `Kharazmi_Server/routers/finance.py:2189` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /finance/pay` | handler `routers.finance.submit_payment`؛ منبع `Kharazmi_Server/routers/finance.py:222` | 1 | success,value,DB,oracle,idempotency | سبزِ اولیه | — |
| `GET /finance/payment/callback` | handler `routers.finance.payment_callback`؛ منبع `Kharazmi_Server/routers/finance.py:879` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /finance/payment/initiate` | handler `routers.finance.initiate_online_payment`؛ منبع `Kharazmi_Server/routers/finance.py:799` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /finance/receipt/pdf` | handler `routers.finance.generate_pdf_receipt`؛ منبع `Kharazmi_Server/routers/finance.py:609` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /finance/receipt/print` | handler `routers.finance.print_receipt`؛ منبع `Kharazmi_Server/routers/finance.py:566` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /finance/receipt/{transaction_id}` | handler `routers.finance.get_receipt_details`؛ منبع `Kharazmi_Server/routers/finance.py:2214` | 1 | success,value,oracle | سبزِ اولیه | — |
| `GET /finance/reports/debtors_grouped` | handler `routers.finance.get_debtors_grouped`؛ منبع `Kharazmi_Server/routers/finance.py:2500` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /finance/reports/debtors_list` | handler `routers.finance.get_debtors_list`؛ منبع `Kharazmi_Server/routers/finance.py:2486` | 1 | success,value,oracle | سبزِ اولیه | — |
| `GET /finance/reports/revenue_summary` | handler `routers.finance.get_revenue_summary`؛ منبع `Kharazmi_Server/routers/finance.py:2654` | 1 | success,value,oracle | سبزِ اولیه | — |
| `GET /finance/reports/teacher_settlements_summary` | handler `routers.finance.get_teacher_settlements_summary`؛ منبع `Kharazmi_Server/routers/finance.py:2709` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /finance/search_advanced` | handler `routers.finance.search_finance_advanced`؛ منبع `Kharazmi_Server/routers/finance.py:49` | 1 | success,value,oracle | سبزِ اولیه | — |
| `GET /finance/student/{student_id}/dashboard` | handler `routers.finance.get_student_financial_dashboard`؛ منبع `Kharazmi_Server/routers/finance.py:2076` | 1 | success,value,oracle | سبزِ اولیه | — |
| `GET /finance/student/{student_id}/payments` | handler `routers.finance.get_student_online_payments`؛ منبع `Kharazmi_Server/routers/finance.py:2021` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /finance/student/{student_id}/transactions` | handler `routers.finance.get_student_physical_transactions`؛ منبع `Kharazmi_Server/routers/finance.py:2047` | 1 | success,value,oracle | سبزِ اولیه | — |
| `GET /finance/student_class_status` | handler `routers.finance.get_student_class_status`؛ منبع `Kharazmi_Server/routers/finance.py:656` | 1 | success,value,oracle | سبزِ اولیه | — |
| `POST /finance/transaction/{transaction_id}/refund` | handler `routers.finance.refund_transaction`؛ منبع `Kharazmi_Server/routers/finance.py:1394` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
