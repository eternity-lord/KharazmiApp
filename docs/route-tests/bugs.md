# فهرست باگ‌های route audit

قانون این پرونده: باگ ثبت می‌شود و در این مرحله fix نمی‌شود. هر reproduction رفتار درست را assert می‌کند و برای باگ شناخته‌شده `xfail(strict=True)` دارد.

| شناسه | سمت | دسته | شدت | تست تکثیرکننده | انتظار | رفتار واقعی/وضعیت | علت احتمالی | صفحه‌های متأثر |
|---|---|---|---|---|---|---|---|---|
| RA-auth-02 (O-02) | اندروید | نمایش/قابلیت | بالا | `test_O02_android_push_client_registers_FCM_token` | Android باید FCM client و registration قابل اتصال داشته باشد | در source Kotlin نماد `FirebaseMessaging` و registration قابل اثبات پیدا نشد؛ xfail | محدودهٔ source بررسی‌شده `KharazmiAdmin/app/src/main/AndroidManifest.xml:1-223` و `KharazmiAdmin/app/src/main/java/com/example/kharazmiadmin/LiveApi.kt:1-66`؛ route ثبت token در `Kharazmi_Server/routers/auth.py:597` | اعلان‌ها و هر صفحهٔ وابسته به push |
| RA-exams-02 (O-12) | سرور/محصول | منطق | متوسط | `test_O12_unpublished_exam_is_hidden_from_student` | شاگرد فقط آزمون `status=published` را ببیند | `/exams/student/list` آزمون pending را هم برمی‌گرداند؛ xfail | `Kharazmi_Server/routers/exams.py:132-158`، فیلتر status ندارد | `ParentPortalActivity` / screenهای آزمون |
| RA-parent-01 (O-14) | اندروید | قرارداد | پایین | `test_O14_parent_exam_decimal_max_score_is_not_parsed_as_Int` | `max_score=12.5` بدون parse failure در مدل Android خوانده شود | `ParentExamItem.max_score` نوع `Int` است و simulator `int-parse` گزارش می‌کند؛ xfail | `ParentPortalActivity.kt:66` در برابر مدل/response آزمون | `ParentPortalActivity` |
| RA-admin-19 (O-19) | هر دو/طراحی | یکپارچگی داده/مالی | متوسط | `test_O19_restore_class_restores_financial_history_atomically` | restore کامل باید ledger و ثبت‌نام‌ها را اتمیک بازیابی کند یا قرارداد کامل دیگری داشته باشد | endpoint فعلی عمدی `metadata_only` است و history مالی را restore نمی‌کند؛ xfail | `Kharazmi_Server/routers/admin.py:1915-2036` | صفحهٔ deleted classes و گزارش‌های مالی |

## نتیجهٔ finance در این نوبت

در ۱۱ route finance که assertion مقداری اجرا شد، با seed فعلی failure جدیدی ثبت نشد. ۱۵ route finance باقی‌مانده در جدول route و inventory حضور دارند ولی functional sweep آن‌ها هنوز انجام نشده است؛ این «بدون باگ» محسوب نمی‌شود.
