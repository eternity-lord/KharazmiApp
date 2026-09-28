# فهرست باگ‌های route audit

قانون این پرونده: باگ ثبت می‌شود و در این مرحله fix نمی‌شود. هر reproduction رفتار درست را assert می‌کند و برای باگ شناخته‌شده `xfail(strict=True)` دارد.

| شناسه | سمت | دسته | شدت | تست تکثیرکننده | انتظار | رفتار واقعی/وضعیت | علت احتمالی | صفحه‌های متأثر |
|---|---|---|---|---|---|---|---|---|
| RA-auth-02 (O-02) | اندروید | نمایش/قابلیت | بالا | `test_O02_android_push_client_registers_FCM_token` | Android باید FCM client و registration قابل اتصال داشته باشد | در source Kotlin نماد `FirebaseMessaging` و registration قابل اثبات پیدا نشد؛ xfail | محدودهٔ source بررسی‌شده `KharazmiAdmin/app/src/main/AndroidManifest.xml:1-223` و `KharazmiAdmin/app/src/main/java/com/example/kharazmiadmin/LiveApi.kt:1-66`؛ route ثبت token در `Kharazmi_Server/routers/auth.py:597` | اعلان‌ها و هر صفحهٔ وابسته به push |
| RA-exams-02 (O-12) | سرور/محصول | منطق | متوسط | `test_O12_unpublished_exam_is_hidden_from_student` | شاگرد فقط آزمون `status=published` را ببیند | `/exams/student/list` آزمون pending را هم برمی‌گرداند؛ xfail | `Kharazmi_Server/routers/exams.py:132-158`، فیلتر status ندارد | `ParentPortalActivity` / screenهای آزمون |
| RA-parent-01 (O-14) | اندروید | قرارداد | پایین | `test_O14_parent_exam_decimal_max_score_is_not_parsed_as_Int` | `max_score=12.5` بدون parse failure در مدل Android خوانده شود | نوع حداقلی `ParentExamItem.max_score` از `Int` به `Float` تغییر کرد؛ تست عادی سبز است؛ Android compile عمداً اجرا نشد | `ParentPortalActivity.kt:66` در برابر مدل/response آزمون | `ParentPortalActivity` |
| RA-admin-19 (O-19) | هر دو/طراحی | یکپارچگی داده/مالی | متوسط | `test_O19_restore_class_restores_financial_history_atomically` | restore کامل باید ledger و ثبت‌نام‌ها را اتمیک بازیابی کند یا قرارداد کامل دیگری داشته باشد | endpoint فعلی عمدی `metadata_only` است و history مالی را restore نمی‌کند؛ xfail | `Kharazmi_Server/routers/admin.py:1915-2036` | صفحهٔ deleted classes و گزارش‌های مالی |

| RA-sweep-01 | اندروید/سرور | قرارداد، نمایش | بالا | `test_gson_contract_issue_is_absent[RA-sweep-01]` | پاسخ bulk approve باید `message` غیرnull سازگار با `SimpleResponse` داشته باشد | با افزودن `message` ثابت به پاسخ سرور، contract simulator سبز شد؛ test عادی است | `ApiInterfaces.kt:82`؛ handler `Kharazmi_Server/routers/classes.py:1330` | PendingClassesActivity |
| RA-sweep-02 | اندروید/سرور | قرارداد، نمایش | بالا | `test_gson_contract_issue_is_absent[RA-sweep-02]` | هر item آزمون باید فیلدهای لازم مدل Android را داشته باشد یا مدل درست آزمون مصرف شود | سرور اکنون `description` و `due_date` را به‌صورت رشتهٔ خالی صریح برمی‌گرداند؛ contract simulator سبز شد؛ test عادی است | `ExamNetworkApi`/`HomeworkItem`؛ `Kharazmi_Server/routers/exams.py:132-162` | ExamActivity و ParentPortalActivity |
| RA-sweep-03 | اندروید/سرور | قرارداد، نمایش | بالا | `test_gson_contract_issue_is_absent[RA-sweep-03]` | `HomeworkItem.description` باید در response وجود داشته باشد یا nullable باشد | سرور اکنون `description` را برای homework والد با مقدار پیش‌فرض رشتهٔ خالی برمی‌گرداند؛ contract simulator سبز شد؛ test عادی است | `HomeworkActivity.kt:45-55,86-87`؛ `Kharazmi_Server/routers/homework.py:331-340` | HomeworkActivity / ParentPortalActivity |
| RA-sweep-04 | اندروید/سرور | قرارداد، نمایش | متوسط | `test_gson_contract_issue_is_absent[RA-sweep-04]` | `students_preview` در پاسخ باشد یا UI نبودنش را به‌صورت صریح مدیریت کند | سرور اکنون برای کلاس ناقص بدون ثبت‌نام `students_preview: []` را صریح برمی‌گرداند؛ contract simulator سبز شد؛ test عادی است | `TeacherDashboardActivity.kt:23-35,48`؛ `Kharazmi_Server/routers/teachers.py:343-375` | TeacherDashboardActivity |
| RA-admin-01 | سرور/داشبورد | مقدار/قرارداد | متوسط | `test_dashboard_last_transaction_uses_direct_student_link` | `last_transaction.student_name` باید با `Transaction.student_id` هم resolve شود، حتی اگر `enrollment_id` خالی باشد | fallback مستقیم به `student_id` اضافه شد؛ transaction id=6 اکنون نام `دانش‌آموز تست 8` را برمی‌گرداند؛ test عادی و dashboard audit سبز است | `Kharazmi_Server/routers/admin.py:51-99`؛ seed transaction id=6 | Dashboard و summary مالی |

## نتیجهٔ finance/attendance/classes در این نوبت

در ۲۹ route دارای assertion مقداری finance/attendance/classes، failure جدید سمت سرور ثبت نشد. deep audit admin و sliceهای پرریسک نیز سبز هستند؛ RA-admin-01، RA-parent-01 و RA-sweep-01..04 بسته شده‌اند و فقط O-02/O-12/O-19 عمداً xfail باقی مانده‌اند.

## نتیجهٔ sweep

- route sweep: ۲۲۱/۲۲۱، status 500 برابر صفر، invalid-input status 500 برابر صفر.
- contract sweep post-fix: ۱۵۱ call یکتا، ۰ entry دارای issue؛ `RA-sweep-01` تا `RA-sweep-04` assertion عادی هستند.
