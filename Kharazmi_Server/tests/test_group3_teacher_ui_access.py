# test_group3_teacher_ui_access.py
# ═══════════════════════════════════════════════════════════════════════════════
# گروه ۳ — دسترسی نادرست معلم در اپ ادمین (آیتم‌های ۱۰ تا ۱۵)
#
#   ۱۰) پاپ‌آپ بعد از تسویه: «ثبت مجدد برای دانش‌آموز دیگر» فقط در مسیر ثبت حوالهٔ
#       دانش‌آموز بماند و در تسویهٔ حساب معلم (پروفایل عملکرد معلم) حذف شود
#   ۱۱) داشبورد معلم: دکمهٔ «ثبت حواله» حذف
#   ۱۲) بنر کلاس در پنل معلم: تعلیق + ثبت حواله مخفی
#   ۱۳) صفحهٔ کلاس در پنل معلم: «امور مدیریتی» مخفی، فقط اصلاح اطلاعات + حذف کلاس
#   ۱۴) تاریخچهٔ جلسات معلم: امور مدیریتی/تعلیق/ثبت حواله مخفی
#   ۱۵) پاپ‌آپ نهایی ثبت کلاس برای معلم: دکمهٔ «رفتن به کلاس‌های منتظر تأیید» حذف
#
# چرا تست ایستا (اسکن متن کد کاتلین)؟
#   طبق قانون پروژه در این سندباکس Gradle/JDK/Android SDK وجود ندارد و اندروید هرگز
#   کامپایل نمی‌شود ⇒ قرارداد UI با همان الگوی موجودِ پروژه قفل می‌شود:
#   `test_class_restore_metadata.py::test_13_android_client_surfaces_restore_warnings`
#   و `test_android_resources_static.py` (گاردهای ایستا روی res/ و R.string/R.id).
#   اینجا هم «چه چیزی باید مخفی/حذف شود» و «چه چیزی باید سر جایش بماند» با assertRegex
#   روی تابعِ مربوطه قفل می‌شود تا رگرسیون (پنهان‌شدن دکمه در مسیر ادمین) دیده شود.
#
# اجرا (DB موقت — هرگز gaj_db.db واقعی):
#   DATABASE_URL=sqlite:////tmp/g3.db JWT_SECRET_KEY=test \
#     python3 -m pytest Kharazmi_Server/tests/test_group3_teacher_ui_access.py -q
# ═══════════════════════════════════════════════════════════════════════════════
import os
import re
import unittest

SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(SERVER_DIR)
KT_DIR = os.path.join(REPO_ROOT, "KharazmiAdmin", "app", "src", "main", "java",
                      "com", "example", "kharazmiadmin")
RES_DIR = os.path.join(REPO_ROOT, "KharazmiAdmin", "app", "src", "main", "res")


def kt(name: str) -> str:
    path = os.path.join(KT_DIR, name)
    assert os.path.exists(path), f"فایل کاتلین پیدا نشد: {path}"
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def layout(name: str) -> str:
    path = os.path.join(RES_DIR, "layout", name)
    assert os.path.exists(path), f"لی‌اوت پیدا نشد: {path}"
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def strip_comments(source: str) -> str:
    """کامنت‌ها را حذف می‌کند تا گارد روی کد واقعی باشد، نه توضیحات (الگوی test_android_resources_static)."""
    source = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), source, flags=re.S)
    return re.sub(r"^\s*//.*$", "", source, flags=re.M)


def function_body(source: str, name: str) -> str:
    """بدنهٔ یک تابع کاتلین تا شروع تابع هم‌سطح بعدی (برای گاردِ «فقط در این مسیر»)."""
    code = strip_comments(source)
    match = re.search(r"\n\s*(?:(?:private|internal|public|override|open|suspend)\s+)*fun\s+"
                      + re.escape(name) + r"\s*\(", code)
    assert match, f"تابع {name} در سورس پیدا نشد"
    rest = code[match.end():]
    nxt = re.search(r"\n\s{0,4}(?:private |internal |public |override )*fun\s+\w+", rest)
    return rest[:nxt.start()] if nxt else rest


GONE = r"R\.id\.{btn}\)\.visibility\s*=\s*View\.GONE"


class TestItem10SettlementPopupButton(unittest.TestCase):
    """آیتم ۱۰ — «ثبت مجدد برای دانش‌آموز دیگر» در پاپ‌آپ تسویهٔ معلم.

    ریشه (قبل از فیکس): `TeacherProfileActivity.performSettlement()` همان لی‌اوت
    `dialog_remittance_success` را inflate می‌کند و فقط `btnPrintRemittance` و
    `btnSaveAsPdf` را GONE می‌کرد ⇒ دکمهٔ «ثبت مجدد برای دانش‌آموز دیگر» در پاپ‌آپ
    تسویهٔ **معلم** دیده می‌شد (و چون اینجا listener ندارد، کلیکش هیچ کاری نمی‌کرد).
    الگوی درستِ موجود: `AttendanceActivity` همان دکمه را GONE می‌کند.
    """

    def test_10a_the_button_text_is_the_one_the_owner_sees(self):
        """اطمینان از اینکه سراغ همان دکمه رفته‌ایم (متن لی‌اوت، نه یک دکمهٔ دیگر)."""
        xml = layout("dialog_remittance_success.xml")
        block = xml[xml.index('android:id="@+id/btnRegisterAgain"'):]
        self.assertIn("ثبت مجدد برای دانش‌آموز دیگر", block[:400], block[:400])

    def test_10b_teacher_settlement_popup_hides_register_again(self):
        body = function_body(kt("TeacherProfileActivity.kt"), "performSettlement")
        self.assertIn("dialog_remittance_success", body,
                      "مسیر تسویهٔ معلم همان پاپ‌آپ حواله را inflate می‌کند")
        self.assertRegex(body, GONE.format(btn="btnRegisterAgain"),
                         "دکمهٔ «ثبت مجدد برای دانش‌آموز دیگر» باید در پاپ‌آپ تسویهٔ معلم پنهان شود")

    def test_10c_student_remittance_popup_keeps_the_button(self):
        """مسیر ثبت حوالهٔ دانش‌آموز (InvoiceActivity) باید دکمه را نگه دارد و کلیک‌پذیر کند."""
        src = strip_comments(kt("InvoiceActivity.kt"))
        self.assertIn("R.id.btnRegisterAgain", src)
        self.assertIn("btnRegisterAgain.setOnClickListener", src,
                      "در مسیر دانش‌آموز دکمه باید فعال بماند")
        self.assertNotRegex(src, GONE.format(btn="btnRegisterAgain"),
                            "دکمه در صفحهٔ ثبت حوالهٔ دانش‌آموز نباید پنهان شود")

    def test_10d_attendance_popup_still_hides_it(self):
        """الگوی موجود (جلسه/حضوروغیاب) نباید رگرسیون کند."""
        src = strip_comments(kt("AttendanceActivity.kt"))
        self.assertRegex(src, GONE.format(btn="btnRegisterAgain"))


class TestItem11TeacherDashboardInvoiceButton(unittest.TestCase):
    """آیتم ۱۱ — حذف «ثبت حواله» از داشبورد معلم.

    ریشه: `TeacherDashboardActivity` کارت `cardFastInvoice` را **بدون هیچ چک نقشی**
    به `InvoiceActivity` وصل می‌کرد، در حالی که این صفحه فقط پنل معلم است
    (`LoginActivity` تنها وقتی `response.role == "teacher"` باشد اینجا می‌آید و
    `EditStudentActivity.returnToDashboard` هم فقط برای `userRole == "teacher"`).
    ثبت حواله/وصول پول کار ادمین/منشی است ⇒ نباید در پنل معلم دیده شود.
    چک نقش، همان الگوی غالب پروژه است: `UserCreds` → `USER_SUB_ROLE`
    (مثل `ClassDetailActivity:334` و `StudentProfileActivity:275`) — الگوی جدید نساختیم.
    """

    def test_11a_fast_invoice_card_is_role_gated_and_hidden(self):
        body = function_body(kt("TeacherDashboardActivity.kt"), "onCreate")
        self.assertIn("R.id.cardFastInvoice", body, "کارت ثبت حواله در همین صفحه است")
        # چک نقش موجود پروژه خوانده می‌شود (نه یک سازوکار جدید)
        self.assertRegex(body, r'getSharedPreferences\("UserCreds"')
        self.assertRegex(body, r'getString\("USER_SUB_ROLE",\s*"admin"\)')
        gate = body[body.index("USER_SUB_ROLE"):]
        self.assertRegex(gate, r'subRole\s*!=\s*"admin"',
                         "باید شاخهٔ «غیر ادمین» داشته باشد")
        self.assertRegex(gate, r"cardFastInvoice\.visibility\s*=\s*(android\.view\.)?View\.GONE",
                         "کارت ثبت حواله باید برای معلم پنهان شود")

    def test_11b_the_invoice_shortcut_only_stays_for_admin(self):
        """listener باید **بعد از** گارد نقش بیاید ⇒ برای معلم هرگز ثبت نمی‌شود."""
        body = function_body(kt("TeacherDashboardActivity.kt"), "onCreate")
        gate = body[body.index("USER_SUB_ROLE"):]
        self.assertGreater(gate.index("cardFastInvoice.setOnClickListener"),
                           gate.index('subRole != "admin"'),
                           "ثبت listener باید داخل شاخهٔ ادمین باشد، نه قبل از گارد نقش")

    def test_11c_other_teacher_dashboard_shortcuts_are_untouched(self):
        """فقط «ثبت حواله» حذف می‌شود؛ بقیهٔ میان‌برهای پنل معلم سر جایشان می‌مانند."""
        body = function_body(kt("TeacherDashboardActivity.kt"), "onCreate")
        for card in ("cardRegisterStudent", "cardRegisterClass", "cardAttendance",
                     "cardIncompleteClasses", "cardReports"):
            self.assertIn(f"R.id.{card}", body, f"میان‌بر {card} نباید حذف شود")
            self.assertRegex(body, r"R\.id\." + card + r"\)\.setOnClickListener",
                             f"listener {card} باید سر جایش بماند")


class TestItem12TeacherClassBannerButtons(unittest.TestCase):
    """آیتم ۱۲ — مخفی‌شدن «تعلیق» و «ثبت حواله» روی بنر کلاس‌ها در پنل معلم.

    ریشه: `item_class_row.xml` دو دکمهٔ `btnSuspend` (تعلیق) و `btnRegisterInvoice`
    (ثبت حواله) را **بدون `android:visibility`** یعنی به‌صورت پیش‌فرض نمایان دارد و
    همین layout مشترک هم در `ClassManagementActivity` (ادمین) و هم در آداپتر
    `TeacherClassAdapter` داخل `TeacherDashboardActivity` (پنل معلم) inflate می‌شود.
    سمت ادمین این دو را مدیریت می‌کند (`holder.btnSuspend.visibility =
    if (isAdminUser) View.VISIBLE else View.GONE` و listener ثبت حواله)، ولی آداپتر
    معلم هرگز به آن‌ها دست نمی‌زد ⇒ در پنل معلم دو دکمهٔ نمایانِ **بی‌عملکرد**
    روی هر بنر کلاس می‌نشست.

    چون layout مشترک است، تغییر باید سمت آداپتر معلم باشد (نه خود layout)، و با همان
    چک نقش موجود (`USER_SUB_ROLE`) — همان الگوی `isAdminUser` در ClassManagementActivity.
    """

    def test_12a_both_banner_buttons_are_hidden_for_teachers(self):
        src = kt("TeacherDashboardActivity.kt")
        body = function_body(src, "onBindViewHolder")
        for btn in ("btnSuspend", "btnRegisterInvoice"):
            self.assertIn(f"R.id.{btn}", src, f"آداپتر معلم باید {btn} را پیدا کند")
            self.assertRegex(body,
                             rf"{btn}\.visibility\s*=\s*if\s*\(isAdminUser\)\s*(android\.view\.)?View\.VISIBLE\s*else\s*(android\.view\.)?View\.GONE",
                             f"{btn} باید با گارد isAdminUser روی بنر معلم پنهان شود")

    def test_12b_the_role_flag_reaches_the_adapter(self):
        """پرچم نقش از Activity (همان `USER_SUB_ROLE`) به آداپتر می‌رسد."""
        src = strip_comments(kt("TeacherDashboardActivity.kt"))
        self.assertRegex(src, r"class TeacherClassAdapter\([\s\S]{0,200}?isAdminUser\s*:\s*Boolean",
                         "آداپتر باید پرچم isAdminUser را بگیرد")
        # lambda انتهایی باید به onClick بخورد ⇒ پرچم نقش نباید آخرین پارامتر باشد
        head = re.search(r"class TeacherClassAdapter\([\s\S]*?\n\) :", src).group(0)
        self.assertLess(head.index("isAdminUser"), head.index("onClick"),
                        "onClick باید آخرین پارامتر بماند (lambda انتهاییِ محل ساخت)")
        self.assertRegex(src, r"TeacherClassAdapter\([^\n]*isAdminUser",
                         "محل ساخت آداپتر باید پرچم را پاس بدهد")
        self.assertRegex(src, r"isAdminUser\s*=\s*subRole\s*==\s*\"admin\"",
                         "پرچم باید از همان USER_SUB_ROLE موجود ساخته شود")

    def test_12c_admin_side_is_untouched(self):
        """layout مشترک و گارد ادمین در ClassManagementActivity دست‌نخورده می‌ماند."""
        row = layout("item_class_row.xml")
        self.assertIn('@+id/btnSuspend', row)
        self.assertIn('@+id/btnRegisterInvoice', row)
        cm = strip_comments(kt("ClassManagementActivity.kt"))
        self.assertRegex(cm, r"btnSuspend\.visibility\s*=\s*if\s*\(isAdminUser\)\s*View\.VISIBLE\s*else\s*View\.GONE")
        self.assertRegex(cm, r"btnRegisterInvoice\.setOnClickListener")


if __name__ == "__main__":
    unittest.main()
