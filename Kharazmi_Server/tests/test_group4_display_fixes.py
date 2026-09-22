# گروه ۴ — نمایش خراب، آیتم ۱۷ (پنل ادمین)
#
# بازتولید آیتم ۱۷:
# endpoint واقعی /classes/{id}/students_full روی کپی DB پاسخ غیرخالی می‌دهد؛
# بنابراین خالی‌بودن لیست در پنل ادمین از داده/endpoint نیست. در ClassDetailActivity
# RecyclerView در onCreate عمداً GONE می‌شود، اما شاخهٔ تب «لیست دانش‌آموزان» آن را
# دوباره VISIBLE نمی‌کند. این تست قرارداد binding/visibility را قفل می‌کند.
#
# طبق قانون پروژه این تست ایستا است: در این sandbox کامپایل اندروید انجام نمی‌شود.
import os
import re
import unittest


SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(SERVER_DIR)
KT_DIR = os.path.join(
    REPO_ROOT,
    "KharazmiAdmin",
    "app",
    "src",
    "main",
    "java",
    "com",
    "example",
    "kharazmiadmin",
)


def kt(name: str) -> str:
    path = os.path.join(KT_DIR, name)
    assert os.path.exists(path), f"فایل کاتلین پیدا نشد: {path}"
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def function_body(source: str, name: str) -> str:
    """بدنهٔ تابع تا تابع هم‌سطح بعدی؛ همان الگوی گاردهای ایستای پروژه."""
    match = re.search(
        r"\n\s*(?:(?:private|internal|public|override|open|suspend)\s+)*fun\s+"
        + re.escape(name)
        + r"\s*\(",
        source,
    )
    assert match, f"تابع {name} در سورس پیدا نشد"
    rest = source[match.end() :]
    nxt = re.search(r"\n\s{0,4}(?:private |internal |public |override )*fun\s+\w+", rest)
    return rest[: nxt.start()] if nxt else rest


class TestItem17AdminClassStudentList(unittest.TestCase):
    """آیتم ۱۷ — لیست دانش‌آموزان کلاس در پنل ادمین نباید با دادهٔ موجود ناپدید شود."""

    def test_17a_student_tab_makes_the_bound_recycler_view_visible(self):
        src = kt("ClassDetailActivity.kt")
        body = function_body(src, "updateUI")
        student_tab_start = body.index("1 ->")
        student_tab = body[student_tab_start:]
        self.assertIn("rvStudents", src)
        self.assertRegex(
            student_tab,
            r"rvStudents\.visibility\s*=\s*View\.VISIBLE",
            "شاخهٔ تب لیست دانش‌آموزان باید RecyclerView متصل به adapter را نمایش دهد",
        )

    def test_17b_the_adapter_is_bound_to_the_same_recycler_view(self):
        body = function_body(kt("ClassDetailActivity.kt"), "onCreate")
        self.assertIn("rvStudents = findViewById(R.id.rvStudents)", body)
        self.assertIn("rvStudents.adapter = studentAdapter", body)
        self.assertIn("rvStudents.visibility = View.GONE", body)

    def test_17c_the_admin_class_detail_uses_the_real_students_endpoint(self):
        src = kt("ClassDetailActivity.kt")
        self.assertIn('@GET("classes/{id}/students_full")', src)
        self.assertIn("api.getClassStudentsFull(classId)", src)


if __name__ == "__main__":
    unittest.main()
