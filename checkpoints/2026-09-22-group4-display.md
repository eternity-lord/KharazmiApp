# گروه ۴ — نمایش خراب

## وضعیت این تحویل: آیتم ۱۷ تمام شد

- **آیتم:** ۱۷ — `[پنل ادمین]` لیست دانش‌آموزان کلاس خالی نمایش داده می‌شد
- **تاریخ:** ۲۰۲۶-۰۹-۲۲
- **برنچ کاری جلسه:** `arena/01a0c9b8-kharazmiapp`
- **محدوده:** فقط مسیر مشترک جزئیات کلاس که از پنل ادمین باز می‌شود؛ endpoint/سرور تغییر نکرد.

> نکتهٔ محیطی: سندهای قبلی گروه ۳ نام برنچ `arena/01a0c867-kharazmiapp` را ثبت کرده‌اند، اما checkout این جلسه طبق قفل Arena روی `arena/01a0c9b8-kharazmiapp` است و تغییر برنچ انجام نشد.

---

## ۱) بازتولید قرمز و لاگ endpoint واقعی

فایل واقعی `Kharazmi_Server/gaj_db.db` فقط برای خواندن بررسی شد و قبل/بعد md5 آن
`f048f8d118b33c4eaa944490594121d7` بود. تست endpoint روی کپی زیر انجام شد:

```text
/tmp/group4_item17.db
```

دادهٔ واقعی کپی‌شده حداقل یک کلاس فعال و یک enrollment فعال داشت:

```text
course_id=1, title=ریاضی کنکور, code=3406, active_students=1
```

مسیر واقعی `/classes/{id}/students_full` با همان route و serialization سرور پاسخ غیرخالی داد:

```text
GET /classes/1/students_full -> 200
course_info.id=1, title=ریاضی کنکور, code=3406
students.length=1
student_id=1, student_name=الارا صیامی, enrollment_id=1
```

دو مسیر مرتبط نیز داده داشتند:

```text
GET /classes/1/details     -> 200, students.length=1
GET /classes/1/full_report -> 200, total_students=1, students.length=1
```

به‌دلیل اینکه DB واقعیِ موجود برای تست انتشار‌یافته کاربر/`user_sessions` ندارد، احراز هویت
زنده با token واقعی ممکن نبود؛ برای بررسی handler واقعی فقط dependency احراز هویت در
`TestClient` به `admin` override شد. درخواست بدون session نیز عمداً بررسی شد و پاسخ مورد
انتظار `401` داد. هیچ داده‌ای در DB واقعی نوشته نشد.

### تست قرمز

تست جدید:

```text
Kharazmi_Server/tests/test_group4_display_fixes.py
```

قبل از فیکس:

```text
1 failed, 2 passed
```

تست شکست‌خورده ثابت کرد مشکل از endpoint خالی نیست، بلکه قرارداد نمایش `RecyclerView`
در `ClassDetailActivity.updateUI` شکسته است.

---

## ۲) ریشهٔ باگ

در `ClassDetailActivity.onCreate`، همان `RecyclerView` متصل به adapter با این خط مخفی می‌شد:

```kotlin
rvStudents.visibility = View.GONE
```

اما در شاخهٔ تب «لیست دانش‌آموزان» (`updateUI(1)`) فقط container نمایش داده می‌شد:

```kotlin
tabContainer.visibility = View.VISIBLE
```

و خود `rvStudents` دوباره `VISIBLE` نمی‌شد. در نتیجه endpoint پاسخ دارای دانش‌آموز بود،
adapter هم داده می‌گرفت، اما ویجت binding‌شده تمام مدت `GONE` می‌ماند و کاربر لیست را
خالی می‌دید.

---

## ۳) فیکس حداقلی

در `KharazmiAdmin/app/src/main/java/com/example/kharazmiadmin/ClassDetailActivity.kt`
داخل شاخهٔ تب دانش‌آموزان فقط این خط اضافه شد:

```kotlin
rvStudents.visibility = View.VISIBLE
```

endpointها، مدل سرور، adapter و layout تغییر نکردند.

---

## ۴) راستی‌آزمایی بعد از فیکس

- تست آیتم ۱۷: **۳ passed**
- `ast.parse` روی **۱۳۹ فایل Python**: موفق
- `import main` روی کپی `/tmp`: موفق
- سوئیت کامل روی کپی `/tmp`: **۱۱۵۱ passed**
- md5 فایل واقعی قبل/بعد: یکسان و برابر با
  `f048f8d118b33c4eaa944490594121d7`
- کامپایل اندروید: طبق قانون پروژه انجام نشد
- `git diff --check`: موفق

تست‌های آیتم ۱۷ علاوه بر visibility، اتصال adapter و استفادهٔ Activity از endpoint واقعی
`classes/{id}/students_full` را نیز قفل می‌کنند.

---

## ۵) تغییرات این تحویل

```text
KharazmiAdmin/app/src/main/java/com/example/kharazmiadmin/ClassDetailActivity.kt
Kharazmi_Server/tests/test_group4_display_fixes.py
checkpoints/2026-09-22-group4-display.md
```

## ۶) وضعیت ادامهٔ گروه ۴

- [x] ۱۷ — پنل ادمین: لیست دانش‌آموزان کلاس
- [ ] ۱۸ — پنل معلم: همان لیست، با تأیید جداگانهٔ مسیر پنل معلم
- [ ] ۱۹ — پنل معلم: تم/اسم کلاس روی بنر
- [ ] ۲۰ — پنل معلم: بدهی به معلم/بدهی کل روی بنر
- [ ] ۲۱ — پنل ادمین: حذف متن جنسیت مختلط از بنر مدیریت کلاس‌ها

آیتم ۱۸ هنوز جداگانه اجرا و گزارش نشده است؛ اگرچه ریشهٔ آیتم ۱۷ در `ClassDetailActivity`
مشترک به نظر می‌رسد، مسیر پنل معلم باید در آیتم ۱۸ به‌طور مستقل تأیید شود.
