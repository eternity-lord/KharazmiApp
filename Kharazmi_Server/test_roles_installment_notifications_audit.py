"""
ممیزی نقش/دسترسی + mapping اعلان اقساط — TEST-ONLY
(هیچ تغییری در کد اصلی پروژه انجام نشده است؛ DB واقعی هم لمس نمی‌شود.)

## نگاشت سناریوهای درخواستی ← تست‌ها

### بخش اول — دسترسی نقش‌ها
| # | سناریو | تست |
|---|--------|-----|
| ۱ | بدون token ⇒ 401 | `test_role_01_*` |
| ۲ | token نامعتبر ⇒ 401 | `test_role_02_*` |
| ۳ | admin: دسترسی مدیریتی مجاز | `test_role_03_*` |
| ۴ | secretary: بدون دسترسی admin-only | `test_role_04_*` |
| ۵ | teacher: فقط دانش‌آموزان کلاس‌های خودش | `test_role_05_*` |
| ۶ | teacher: تغییر student_id/course_id ⇒ عدم دسترسی به کلاس معلم دیگر | `test_role_06_*` |
| ۷ | parent: فقط فرزند خودش | `test_role_07_*` |
| ۸ | parent: تغییر ID ⇒ عدم دسترسی به فرزند دیگر | `test_role_08_*` |
| ۹ | student: فقط اطلاعات خودش | `test_role_09_*` |
| ۱۰ | student/parent: بدون write مالی | `test_role_10_*` |
| ۱۱ | teacher: بدون تنظیم تعرفه/refund/settlement مدیریتی | `test_role_11_*` |
| ۱۲ | نقش ناشناخته/temp_parent بدون انتخاب فرزند ⇒ بدون bypass | `test_role_12_*` |
| ۱۳ | mark notification as read فقط برای اعلان خودِ کاربر | `test_role_13_*` |

### بخش دوم — mapping اعلان قسط
Student.id=101, Student.user_id=501, Student.parent_user_id=601 (عمداً متفاوت)
| # | سناریو | تست |
|---|--------|-----|
| ۱-۴ | قسط overdue ⇒ اعلان شاگرد (501/student) و ولی (601/parent) | `test_installment_notifications_use_user_ids_not_student_id` |
| ۵ | هیچ اعلانی با recipient_user_id=101 | `test_installment_notification_never_targets_student_id_namespace`, `test_installment_notification_actual_recipient_is_student_id` |
| ۶ | بدون user_id/parent_user_id ⇒ نه fallback به Student.id | `test_recipient_resolver_*`, `test_auto_reminder_without_user_ids_*` |
| ۷ | هر کاربر فقط اعلان خودش را می‌بیند | `test_each_user_only_sees_own_installment_notification` |
| ۸ | تست باگ با نام واضح | `test_installment_notifications_use_user_ids_not_student_id` |
| ۹ | expected/actual/محل کد | در docstring هر تست + CHK |

اجرا (طبق قانون پروژه: فقط DB موقت/تست — هرگز gaj_db.db واقعی):
    cd /home/user/KharazmiApp && DATABASE_URL=sqlite:////tmp/roles_audit.db \\
        PYTHONPATH=/home/user/KharazmiApp/Kharazmi_Server \\
        python3 -m pytest Kharazmi_Server/test_roles_installment_notifications_audit.py -q
"""
from __future__ import annotations

import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from dependencies import create_jwt_token, get_db, resolve_notification_recipient
from main import app
from routers import finance
from today_summary import gregorian_to_jalali

TODAY = datetime.date.today()
TODAY_JALALI = "%04d/%02d/%02d" % gregorian_to_jalali(TODAY)
PAST_JALALI = "%04d/%02d/%02d" % gregorian_to_jalali(TODAY - datetime.timedelta(days=5))


# ==========================================
# زیرساخت مشترک
# ==========================================
def _engine(url="sqlite:///:memory:", **kwargs):
    eng = create_engine(url, connect_args={"check_same_thread": False}, **kwargs)
    models.Base.metadata.create_all(eng)
    return eng


def _mk_user(uid, username, sub_role, role=None, branch_id=1):
    return models.User(id=uid, username=username, password="x", full_name=f"u{uid}",
                       role=role or sub_role, sub_role=sub_role, branch_id=branch_id)


def _seed(db):
    db.add(models.Branch(id=1, name="شعبه تست", active=True))
    db.flush()
    # کاربران هر پنج نقش + یک نقش ناشناخته
    db.add_all([
        _mk_user(1, "09120000000", "admin"),
        _mk_user(2, "09120000002", "secretary"),
        _mk_user(3, "09120000003", "teacher"),
        _mk_user(4, "09120000004", "teacher"),
        _mk_user(501, "student:101", "student"),
        _mk_user(601, "parent:101", "parent"),
        _mk_user(502, "student:102", "student"),
        _mk_user(602, "parent:102", "parent"),
        _mk_user(7, "mystery", "mystery_role"),          # نقش ناشناخته
    ])
    db.add_all([
        models.Teacher(id=1, first_name="معلم", last_name="الف", national_code="T-1",
                       mobile="09120000003", teacher_code=101, is_approved=True, branch_id=1),
        models.Teacher(id=2, first_name="معلم", last_name="ب", national_code="T-2",
                       mobile="09120000004", teacher_code=102, is_approved=True, branch_id=1),
    ])
    # student_id عمداً با user_id/parent_user_id فرق دارد (۱۰۱ در برابر ۵۰۱/۶۰۱)
    db.add_all([
        models.Student(id=101, first_name="شاگرد", last_name="الف", national_code="S-101",
                       student_mobile="09120000501", parent_mobile="09120000601",
                       user_id=501, parent_user_id=601, branch_id=1),
        models.Student(id=102, first_name="شاگرد", last_name="ب", national_code="S-102",
                       student_mobile="09120000502", parent_mobile="09120000602",
                       user_id=502, parent_user_id=602, branch_id=1),
    ])
    db.add_all([
        models.Course(id=1, title="کلاس الف", code="C-1", teacher_id=1, branch_id=1,
                      grade_level="دهم", teacher_session_price=100, is_admin_approved=True),
        models.Course(id=2, title="کلاس ب", code="C-2", teacher_id=2, branch_id=1,
                      grade_level="دهم", teacher_session_price=100, is_admin_approved=True),
    ])
    db.add_all([
        models.Enrollment(id=1, student_id=101, course_id=1, branch_id=1,
                          total_tuition=1000, total_paid=0, register_date=TODAY_JALALI),
        models.Enrollment(id=2, student_id=102, course_id=2, branch_id=1,
                          total_tuition=1000, total_paid=0, register_date=TODAY_JALALI),
    ])
    db.add_all([
        models.UserSession(token="tok_admin", user_id=1, sub_role="admin",
                           created_at=datetime.datetime.now()),
        models.UserSession(token="tok_secretary", user_id=2, sub_role="secretary",
                           created_at=datetime.datetime.now()),
        models.UserSession(token="tok_teacher_a", user_id=3, sub_role="teacher",
                           created_at=datetime.datetime.now()),
        models.UserSession(token="tok_teacher_b", user_id=4, sub_role="teacher",
                           created_at=datetime.datetime.now()),
        models.UserSession(token="tok_student", user_id=501, sub_role="student",
                           created_at=datetime.datetime.now()),
        models.UserSession(token="tok_parent", user_id=601, sub_role="parent",
                           created_at=datetime.datetime.now()),
        models.UserSession(token="tok_unknown", user_id=7, sub_role="mystery_role",
                           created_at=datetime.datetime.now()),
        # temp_parent قبل از انتخاب فرزند (الگوی واقعی پروژه: user_id = -1)
        models.UserSession(token="tok_temp_parent", user_id=-1,
                           sub_role="temp_parent:09120000601", created_at=datetime.datetime.now()),
    ])
    db.add_all([
        models.Notification(id=1, recipient_user_id=501, recipient_role="student",
                            type="installment", title="اعلان شاگرد", body="...", is_read=False),
        models.Notification(id=2, recipient_user_id=601, recipient_role="parent",
                            type="installment", title="اعلان ولی", body="...", is_read=False),
        # همان کاربر ۵۰۱ ولی با نقش parent — اثبات اینکه فیلتر role هم لازم است
        models.Notification(id=3, recipient_user_id=501, recipient_role="parent",
                            type="installment", title="اعلان نقش دیگر", body="...", is_read=False),
    ])
    db.commit()


@pytest.fixture
def api():
    """کلاینت HTTP + DB درون‌حافظه‌ای ایزوله برای سناریوهای نقش/دسترسی."""
    engine = _engine(poolclass=StaticPool)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    _seed(db)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield SimpleNamespace(client=client, db=db, engine=engine, Session=Session)
    app.dependency_overrides.clear()
    db.close()
    engine.dispose()


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


def call(api, method, path, token=None, payload=None, params=None):
    """فراخوانی HTTP با هدر اختیاری و body اختیاری (GET/DELETE body نمی‌گیرند)."""
    kwargs = {}
    if token is not None:
        kwargs["headers"] = hdr(token)
    if payload is not None and method.lower() in ("post", "put", "patch"):
        kwargs["json"] = payload
    if params:
        kwargs["params"] = params
    return getattr(api.client, method.lower())(path, **kwargs)


# ==========================================
# بخش اول — سناریو ۱ و ۲: بدون token / token نامعتبر
# ==========================================
@pytest.mark.parametrize("path,method", [
    ("/students/my_profile", "get"),
    ("/notifications", "get"),
    ("/finance/pay", "post"),
    ("/admin/pricing_table", "get"),
])
def test_role_01_no_token_is_401(api, path, method):
    """سناریو ۱: بدون هدر Authorization هیچ مسیر محافظت‌شده‌ای باز نمی‌شود ⇒ 401."""
    r = call(api, method, path)
    assert r.status_code == 401, f"{method.upper()} {path} بدون توکن = {r.status_code}"


@pytest.mark.parametrize("bad", [
    "garbage",
    "aaa.bbb.ccc",                       # JWT-شکل ولی امضای نامعتبر
    "Bearer",                            # قالب ناقص
])
def test_role_02_invalid_token_is_401(api, bad):
    """سناریو ۲: توکن نامعتبر/جعلی ⇒ 401 (بدون fallback به lookup همگانی)."""
    r = api.client.get("/students/my_profile", headers={"Authorization": f"Bearer {bad}"})
    assert r.status_code == 401, f"توکن نامعتبر {bad!r} = {r.status_code}"


def test_role_02b_expired_jwt_is_401(api):
    """سناریو ۲ (تکمیلی): JWT امضاشده‌ی منقضی — حتی با سشن موجود در DB — نباید معتبر باشد."""
    expired = create_jwt_token(user_id=501, sub_role="student", expires_days=-1)
    api.db.add(models.UserSession(token=expired, user_id=501, sub_role="student",
                                  created_at=datetime.datetime.now()))
    api.db.commit()
    r = api.client.get("/notifications", headers=hdr(expired))
    assert r.status_code == 401, f"JWT منقضی = {r.status_code}"


# ==========================================
# سناریو ۳: admin
# ==========================================
def test_role_03_admin_has_administrative_access(api):
    """سناریو ۳: admin به مسیرهای مدیریتیِ admin-only دسترسی دارد (نه ۴۰۳)."""
    settings = api.client.put("/admin/institute_settings", headers=hdr("tok_admin"), json={
        "name": "آموزشگاه تست", "address": "تهران", "phone": "021000000",
        "official_email": "a@a.com"})
    assert settings.status_code == 200, settings.text

    pricing = api.client.get("/admin/pricing_table", headers=hdr("tok_admin"))
    assert pricing.status_code == 200, pricing.text

    tx_list = api.client.get("/admin/transactions/list", headers=hdr("tok_admin"))
    assert tx_list.status_code == 200, tx_list.text

    revenue = api.client.get("/finance/reports/revenue_summary", headers=hdr("tok_admin"))
    assert revenue.status_code == 200, revenue.text

    settle = api.client.post("/teachers/1/settle", headers=hdr("tok_admin"),
                             json={"session_ids": []})
    assert settle.status_code != 403, "admin نباید از settle منع شود (کد: %s)" % settle.status_code


# ==========================================
# سناریو ۴: secretary
# ==========================================
def test_role_04_secretary_has_no_admin_only_access(api):
    """سناریو ۴: منشی به مسیرهای admin-only دسترسی ندارد (۴۰۳) ولی در مسیرهای admin/secretary عبور می‌کند."""
    for method, path, payload in [
        ("put", "/admin/institute_settings", {"name": "x", "address": "y", "phone": "z", "official_email": "a@b.c"}),
        ("get", "/admin/pricing_table", None),
        ("get", "/admin/transactions/list", None),
        ("get", "/config/share", None),
        ("delete", "/admin/students/101", None),
    ]:
        r = call(api, method, path, "tok_secretary", payload)
        assert r.status_code == 403, f"منشی در {method.upper()} {path} = {r.status_code} (باید ۴۰۳)"

    # مسیرهای admin/secretary باید برای منشی باز باشند
    sms = api.client.get("/sms/history", headers=hdr("tok_secretary"))
    assert sms.status_code == 200, sms.text
    contacts = api.client.get("/admin/parent_contacts", headers=hdr("tok_secretary"))
    assert contacts.status_code == 200, contacts.text

    # پرداخت دستی (admin/secretary) برای منشی مجاز است — رگرسیون مثبت
    pay = api.client.post("/finance/pay", headers=hdr("tok_secretary"), json={
        "student_id": 101, "amount": 100, "target_wallet": "institute",
        "description": "پرداخت منشی", "payment_method": "cash", "date": TODAY_JALALI})
    assert pay.status_code == 200, pay.text


# ==========================================
# سناریو ۵ و ۶: teacher (scoping)
# ==========================================
def test_role_05_teacher_reads_only_own_class_students(api):
    """سناریو ۵: معلم الف فقط شاگرد کلاس خودش (۱۰۱) را می‌بیند."""
    own = api.client.get("/students/101", headers=hdr("tok_teacher_a"))
    assert own.status_code == 200, own.text
    own_grades = api.client.get("/students/101/grades", headers=hdr("tok_teacher_a"))
    assert own_grades.status_code == 200, own_grades.text


def test_role_06_teacher_cannot_reach_other_teachers_student_or_class(api):
    """سناریو ۶: با تغییر student_id / course_id / teacher_id معلم الف به داده‌ی معلم ب نمی‌رسد."""
    other = api.client.get("/students/102", headers=hdr("tok_teacher_a"))
    assert other.status_code == 403, f"student_id دیگر = {other.status_code}"

    other_full = api.client.get("/admin/students/102/full_profile", headers=hdr("tok_teacher_a"))
    assert other_full.status_code == 403, f"full_profile شاگرد دیگر = {other_full.status_code}"

    other_grades = api.client.get("/students/102/grades", headers=hdr("tok_teacher_a"))
    assert other_grades.status_code == 403, f"grades شاگرد دیگر = {other_grades.status_code}"

    other_money = api.client.get("/finance/student/102/dashboard", headers=hdr("tok_teacher_a"))
    assert other_money.status_code == 403, f"dashboard مالی شاگرد دیگر = {other_money.status_code}"

    other_classes = api.client.get("/teachers/2/classes", headers=hdr("tok_teacher_a"))
    assert other_classes.status_code == 403, f"کلاس‌های معلم دیگر = {other_classes.status_code}"

    other_settle = api.client.get("/teachers/2/pending_settlement", headers=hdr("tok_teacher_a"))
    assert other_settle.status_code == 403, f"طلب معلم دیگر = {other_settle.status_code}"

    own_settle = api.client.get("/teachers/1/pending_settlement", headers=hdr("tok_teacher_a"))
    assert own_settle.status_code == 200, "معلم باید طلب خودش را ببیند: %s" % own_settle.status_code


def test_role_05b_teacher_owned_endpoints_are_ownership_checked(api):
    """سناریو ۵/۶ (تکمیلی): خلاصه‌ی امروز/تاریخچه‌ی ارتباطات/لیست معلم‌ها برای معلم فقط «خودش»."""
    other_today = api.client.get("/teachers/2/today_summary", headers=hdr("tok_teacher_a"))
    assert other_today.status_code == 403, f"today_summary معلم دیگر = {other_today.status_code}"

    other_comm = api.client.get("/teachers/2/communication_history", headers=hdr("tok_teacher_a"))
    assert other_comm.status_code == 403, f"communication_history معلم دیگر = {other_comm.status_code}"

    own_today = api.client.get("/teachers/1/today_summary", headers=hdr("tok_teacher_a"))
    assert own_today.status_code == 200, own_today.text

    lst = api.client.get("/teachers/list", headers=hdr("tok_teacher_a"))
    assert lst.status_code == 200, lst.text
    assert [t["id"] for t in lst.json()] == [1], f"معلم فقط خودش را باید ببیند: {lst.json()}"


def test_role_09b_student_and_parent_cannot_search_all_people(api):
    """سناریو ۷/۹ (تکمیلی): جستجوی سراسری شاگردان/معلمان برای شاگرد و ولی بسته است (۴۰۳)."""
    # (مسیر /students/my_profile جداگانه در test_role_09 بررسی می‌شود — یافته‌ی F-R1)
    staff_only = ["/students/search?query=شاگرد", "/students/search_simple?query=شاگرد",
                  "/admin/students/search?query=شاگرد", "/admin/teachers/search?query=معلم",
                  "/teachers/list"]
    for token in ("tok_student", "tok_parent"):
        for path in staff_only:
            r = api.client.get(path, headers=hdr(token))
            assert r.status_code == 403, f"{token} در {path} = {r.status_code} (باید ۴۰۳)"


# ==========================================
# سناریو ۷ و ۸: parent
# ==========================================
def test_role_07_parent_reads_only_own_child(api):
    """سناریو ۷: ولی ۶۰۱ فقط فرزند خودش (۱۰۱) را می‌بیند."""
    profile = api.client.get("/parent/child_profile", headers=hdr("tok_parent"))
    assert profile.status_code == 200, profile.text
    assert "شاگرد الف" in profile.text or "101" in profile.text

    own = api.client.get("/students/101", headers=hdr("tok_parent"))
    assert own.status_code == 200, own.text


def test_role_08_parent_cannot_read_other_child_by_id_swap(api):
    """سناریو ۸: با تغییر ID (student_id در URL یا انتخاب فرزند دیگر) ولی به داده‌ی فرزند دیگر نمی‌رسد."""
    for path in ("/students/102", "/students/102/grades", "/students/102/installments",
                 "/finance/student/102/dashboard", "/finance/invoice/2"):
        r = api.client.get(path, headers=hdr("tok_parent"))
        assert r.status_code == 403, f"ولی در {path} = {r.status_code} (باید ۴۰۳)"

    # تلاش برای انتخاب فرزندِ ولیِ دیگر با توکن موقت (IDOR کلاسیک)
    switch = api.client.post("/parent/select_child", json={"temp_token": "tok_temp_parent",
                                                           "student_id": 102})
    assert switch.status_code == 403, f"select_child فرزند دیگر = {switch.status_code}"

    # انتخاب فرزند خودش باید موفق باشد
    own_switch = api.client.post("/parent/select_child", json={"temp_token": "tok_temp_parent",
                                                               "student_id": 101})
    assert own_switch.status_code == 200, own_switch.text


# ==========================================
# سناریو ۹: student
# ==========================================
def test_role_09_student_reads_only_self(api):
    """سناریو ۹: شاگرد فقط داده‌ی خودش را می‌خواند؛ با تغییر ID به شاگرد دیگر نمی‌رسد.

    نکته‌ی یافته‌محور (F-R1): مسیر اختصاصی `/students/my_profile` توسط route داینامیک
    `/students/{student_id}` (ثبت‌شده در خط ۴۳۷، قبل از خط ۶۷۴) سایه افتاده و همیشه ۴۲۲ می‌دهد ⇒
    این endpoint برای شاگرد عملاً مرده است. در همین تست رفتار واقعی هم مستند می‌شود.
    """
    mine = api.client.get("/students/my_profile", headers=hdr("tok_student"))
    assert mine.status_code == 200, (
        f"F-R1: /students/my_profile برای شاگرد = {mine.status_code} (route shadowing) — {mine.text[:120]}")

    own = api.client.get("/students/101", headers=hdr("tok_student"))
    assert own.status_code == 200, own.text

    for path in ("/students/102", "/students/102/grades", "/students/102/installments",
                 "/finance/student/102/dashboard"):
        r = api.client.get(path, headers=hdr("tok_student"))
        assert r.status_code == 403, f"شاگرد در {path} = {r.status_code} (باید ۴۰۳)"

    own = api.client.get("/students/101", headers=hdr("tok_student"))
    assert own.status_code == 200, own.text


# ==========================================
# سناریو ۱۰: بدون write مالی برای student/parent
# ==========================================
@pytest.mark.parametrize("role_token", ["tok_student", "tok_parent"])
def test_role_10_student_and_parent_cannot_write_finance(api, role_token):
    """سناریو ۱۰: شاگرد و ولی هیچ عملیات نوشتاریِ مالی ندارند (۴۰۳)."""
    attempts = [
        ("post", "/finance/pay", {"student_id": 101, "amount": 100, "target_wallet": "institute",
                                  "description": "x", "payment_method": "cash", "date": TODAY_JALALI}),
        ("post", "/finance/installments", {"enrollment_id": 1, "amount": 100, "due_date": TODAY_JALALI}),
        ("put", "/finance/installments/1", {"amount": 100, "due_date": TODAY_JALALI}),
        ("delete", "/finance/installments/1", None),
        ("post", "/finance/installments/1/pay", {"amount": 100}),
        ("post", "/finance/installments/1/remind", None),
        ("post", "/finance/transaction/1/refund", {"reason": "x"}),
    ]
    for method, path, payload in attempts:
        before = (api.db.query(func.count(models.Transaction.id)).scalar(),
                  api.db.query(func.count(models.Installment.id)).scalar())
        r = call(api, method, path, role_token, payload)
        after = (api.db.query(func.count(models.Transaction.id)).scalar(),
                 api.db.query(func.count(models.Installment.id)).scalar())
        assert r.status_code == 403, f"{role_token} در {method.upper()} {path} = {r.status_code}"
        assert before == after, f"{method.upper()} {path} نباید نوشتن مالی داشته باشد"


# ==========================================
# سناریو ۱۱: teacher و عملیات مالی مدیریتی
# ==========================================
def test_role_11_teacher_cannot_set_tariff_refund_or_admin_settlement(api):
    """سناریو ۱۱: معلم تعرفه/refund/settlement مدیریتی ندارد (policy پروژه: admin-only)."""
    cases = [
        ("put", "/admin/pricing_table", {"elementary": {"count_1": 1}}, 403),
        ("put", "/admin/institute_settings", {"name": "x", "address": "y", "phone": "z",
                                              "official_email": "a@b.c"}, 403),
        ("post", "/finance/transaction/1/refund", {"reason": "x"}, 403),
        ("post", "/teachers/1/settle", {"session_ids": []}, 403),
        ("post", "/finance/pay", {"student_id": 101, "amount": 100, "target_wallet": "institute",
                                  "description": "x", "payment_method": "cash", "date": TODAY_JALALI}, 403),
        ("put", "/teachers/update/1", {"first_name": "hack"}, 403),
        ("post", "/automation/rules", {"name": "r", "condition_type": "installment_due",
                                       "threshold": 1, "action_type": "sms"}, 403),
        ("delete", "/admin/transactions/1", None, 403),
    ]
    for method, path, payload, expected in cases:
        r = call(api, method, path, "tok_teacher_a", payload)
        assert r.status_code == expected, f"معلم در {method.upper()} {path} = {r.status_code} (باید {expected})"

    # policy: معلم فقط-readown مالی خودش مجاز است (مستند در همین تست)
    own = api.client.get("/teachers/1/pending_settlement", headers=hdr("tok_teacher_a"))
    assert own.status_code == 200, own.text


# ==========================================
# سناریو ۱۲: نقش ناشناخته / temp_parent / جعل نقش در JWT
# ==========================================
def test_role_12_unknown_role_and_temp_parent_get_no_bypass(api):
    """سناریو ۱۲: نقش ناشناخته و temp_parentِ بدون انتخاب فرزند هیچ دسترسی‌ای باز نمی‌کنند."""
    # نقش ناشناخته (User.sub_role = mystery_role) — check_student_access باید 403 بدهد
    for path in ("/students/101", "/students/101/grades", "/students/101/installments",
                 "/finance/student/101/dashboard"):
        r = api.client.get(path, headers=hdr("tok_unknown"))
        assert r.status_code in (401, 403), f"نقش ناشناخته در {path} = {r.status_code}"

    for path in ("/students/search?query=شاگرد", "/admin/students/search?query=شاگرد",
                 "/teachers/1/classes", "/finance/reports/debtors_list"):
        r = api.client.get(path, headers=hdr("tok_unknown"))
        assert r.status_code == 403, f"نقش ناشناخته در {path} = {r.status_code} (باید ۴۰۳)"

    # temp_parent بدون انتخاب فرزند: نه پروفایل فرزند، نه داده‌ی شاگرد
    r_profile = api.client.get("/parent/child_profile", headers=hdr("tok_temp_parent"))
    assert r_profile.status_code in (401, 403), f"temp_parent در child_profile = {r_profile.status_code}"
    r_student = api.client.get("/students/101", headers=hdr("tok_temp_parent"))
    assert r_student.status_code in (401, 403), f"temp_parent در students/101 = {r_student.status_code}"
    r_my = api.client.get("/students/my_profile", headers=hdr("tok_temp_parent"))
    assert r_my.status_code == 401, f"temp_parent در my_profile = {r_my.status_code}"


def test_role_12b_forged_jwt_sub_role_does_not_escalate(api):
    """سناریو ۱۲ (تکمیلی، حیاتی): JWT امضاشده با sub_role جعلی «admin» برای کاربر شاگرد
    نباید دسترسی مدیریتی بدهد — نقش همیشه از User.sub_role دیتابیس خوانده می‌شود."""
    forged = create_jwt_token(user_id=501, sub_role="admin")
    api.db.add(models.UserSession(token=forged, user_id=501, sub_role="admin",
                                  created_at=datetime.datetime.now()))
    api.db.commit()

    r = api.client.get("/admin/pricing_table", headers=hdr(forged))
    assert r.status_code == 403, (
        f"JWT با sub_role جعلی admin = {r.status_code} — باید ۴۰۳ باشد (نقش از DB خوانده می‌شود)")

    r2 = api.client.get("/admin/transactions/list", headers=hdr(forged))
    assert r2.status_code == 403, f"JWT جعلی در transactions/list = {r2.status_code}"


# ==========================================
# سناریو ۱۳: mark notification as read
# ==========================================
def test_role_13_notification_read_is_scoped_to_owner(api):
    """سناریو ۱۳: کاربر الف نمی‌تواند اعلان کاربر ب را خوانده‌شده کند (و برعکس)."""
    # شاگرد: فقط اعلان نقش student خودش (id=1) را می‌بیند، نه id=2 (ولی) و نه id=3 (نقش parent با همان user_id)
    inbox = api.client.get("/notifications", headers=hdr("tok_student"))
    assert inbox.status_code == 200, inbox.text
    assert [n["id"] for n in inbox.json()] == [1], inbox.text

    # تلاش برای خواندن اعلان ولی (id=2) با توکن شاگرد
    steal = api.client.post("/notifications/2/read", headers=hdr("tok_student"))
    api.db.expire_all()
    assert api.db.get(models.Notification, 2).is_read is False, "اعلان کاربر دیگر تغییر کرد!"
    assert steal.status_code in (200, 404), steal.text  # پاسخ ۲۰۰ کاذب مجاز است ولی نباید اثر بگذارد

    # تلاش معکوس: ولی اعلان شاگرد را تغییر دهد
    steal2 = api.client.post("/notifications/1/read", headers=hdr("tok_parent"))
    api.db.expire_all()
    assert api.db.get(models.Notification, 1).is_read is False, "اعلان شاگرد با توکن ولی تغییر کرد!"

    # read_all ولی نباید اعلان شاگرد/نقش دیگر را دست بزند
    api.client.post("/notifications/read_all", headers=hdr("tok_parent"))
    api.db.expire_all()
    assert api.db.get(models.Notification, 2).is_read is True, "اعلان خودِ ولی باید خوانده شود"
    assert api.db.get(models.Notification, 1).is_read is False, "read_all ولی روی اعلان شاگرد اثر گذاشت"
    assert api.db.get(models.Notification, 3).is_read is False, "read_all روی نقش دیگر اثر گذاشت"


# ==========================================
# بخش دوم — mapping اعلان قسط
# ==========================================
@pytest.fixture
def notif_world(tmp_path, monkeypatch):
    """DB ایزوله + monkeypatch روی SessionLocal/engine تا auto_patch_database (شامل reminder واقعی)
    روی همین DB اجرا شود — الگوی test_priority2_financial."""
    engine = create_engine(f"sqlite:///{tmp_path / 'notif.db'}",
                           connect_args={"check_same_thread": False})
    models.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    db.add(models.Branch(id=1, name="شعبه", active=True))
    db.flush()
    db.add_all([_mk_user(1, "09120000000", "admin"),
                _mk_user(501, "student:101", "student"),      # sub_role=student
                _mk_user(601, "parent:101", "parent"),        # sub_role=parent
                _mk_user(504, "student:104", "student"),
                _mk_user(604, "parent:104", "parent"),
                _mk_user(505, "student:105", "student"),
                _mk_user(605, "parent:105", "parent")])
    db.add(models.Teacher(id=1, first_name="معلم", last_name="الف", national_code="T-1",
                          mobile="09120000009", teacher_code=101, is_approved=True, branch_id=1))
    db.add_all([
        # shomareha-ye user/parent عمداً با student_id فرق دارند
        models.Student(id=101, first_name="شاگرد", last_name="صد و یک", national_code="S-101",
                       student_mobile="09120000501", parent_mobile="09120000601",
                       user_id=501, parent_user_id=601, branch_id=1),
        # بدون user_id/parent_user_id (سناریو ۶)
        models.Student(id=104, first_name="شاگرد", last_name="صد و چهار", national_code="S-104",
                       student_mobile="09120000504", parent_mobile="09120000604",
                       branch_id=1),
        # بدون parent_mobile (probe سیاست)
        models.Student(id=105, first_name="شاگرد", last_name="صد و پنج", national_code="S-105",
                       student_mobile="09120000505", parent_mobile=None,
                       user_id=505, parent_user_id=605, branch_id=1),
    ])
    db.add(models.Course(id=1, title="کلاس", code="C-1", teacher_id=1, branch_id=1,
                         grade_level="دهم", teacher_session_price=100, is_admin_approved=True))
    db.commit()
    db.add_all([
        models.Enrollment(id=1, student_id=101, course_id=1, branch_id=1, total_tuition=1000,
                          total_paid=0, register_date=TODAY_JALALI),
        models.Enrollment(id=2, student_id=104, course_id=1, branch_id=1, total_tuition=1000,
                          total_paid=0, register_date=TODAY_JALALI),
        models.Enrollment(id=3, student_id=105, course_id=1, branch_id=1, total_tuition=1000,
                          total_paid=0, register_date=TODAY_JALALI),
    ])
    # سه قسط overdue (سررسید گذشته، پرداخت‌نشده)
    db.add_all([
        models.Installment(id=1, enrollment_id=1, amount=250000, due_date=PAST_JALALI,
                           is_paid=False, is_deleted=False),
        models.Installment(id=2, enrollment_id=2, amount=250000, due_date=PAST_JALALI,
                           is_paid=False, is_deleted=False),
        models.Installment(id=3, enrollment_id=3, amount=250000, due_date=PAST_JALALI,
                           is_paid=False, is_deleted=False),
    ])
    db.commit()

    monkeypatch.setattr(models, "engine", engine)
    monkeypatch.setattr(models, "SessionLocal", Session)
    yield SimpleNamespace(db=db, engine=engine, Session=Session)
    db.close()
    engine.dispose()


def _run_real_auto_reminder():
    """اجرای همان job واقعی boot (شامل بلوک یادآوری اقساط در main.auto_patch_database)."""
    import main as server_main
    server_main.auto_patch_database()


def _installment_notifications(db):
    db.expire_all()
    return db.query(models.Notification).filter(models.Notification.type == "installment").all()


def test_installment_notifications_use_user_ids_not_student_id(notif_world):
    """🔎 سناریو ۱-۴ و ۸ (باگ قطعی): اعلان قسط باید با **user_id** ساخته شود، نه Student.id.

    expected:  (recipient_user_id=501, recipient_role="student") و (601, "parent")
    actual:    main.py:461 و main.py:470 هر دو `recipient_user_id=st.id` می‌فرستند ⇒ (101, "parent") و (101, "student")
    محل کد:    Kharazmi_Server/main.py:461 و 470 (بلوک «یادآوری اقساط» داخل auto_patch_database)
    """
    _run_real_auto_reminder()
    rows = _installment_notifications(notif_world.db)
    pairs = sorted((r.recipient_user_id, r.recipient_role) for r in rows)

    assert (501, "student") in pairs, (
        "اعلان شاگرد باید به user_id=501 برود (Student.id=101 اشتباه است)؛ actual=%r" % (pairs,))
    assert (601, "parent") in pairs, (
        "اعلان ولی باید به parent_user_id=601 برود (Student.id=101 اشتباه است)؛ actual=%r" % (pairs,))


def test_installment_notification_never_targets_student_id_namespace(notif_world):
    """🔎 سناریو ۵: هیچ اعلان قسطی نباید recipient_user_id=101 (Student.id) داشته باشد.

    خطر: ۱۰۱ در فضای User.id یک کاربر دیگر است ⇒ اعلان ولی/شاگرد در صندوق کاربر بی‌ربط می‌افتد
    (نشت اطلاعات مالی به کاربر دیگر) و خودِ صاحب اعلان هیچ‌وقت آن را نمی‌بیند.
    """
    _run_real_auto_reminder()
    rows = _installment_notifications(notif_world.db)
    wrong = [(r.id, r.recipient_user_id, r.recipient_role) for r in rows if r.recipient_user_id == 101]
    assert wrong == [], f"اعلان‌هایی با recipient_user_id=Student.id ساخته شد: {wrong}"


def test_installment_notification_actual_recipient_is_student_id(notif_world):
    """📌 مستندسازی actual باگ (این تست خودِ رفتار باگ‌دار را ثبت می‌کند تا در گزارش قابل ارجاع باشد):
    در نسخه‌ی فعلی اعلان‌ها با recipient_user_id=101 و نقش‌های parent/student ثبت می‌شوند."""
    _run_real_auto_reminder()
    rows = _installment_notifications(notif_world.db)
    pairs = sorted((r.recipient_user_id, r.recipient_role) for r in rows if r.recipient_user_id == 101)
    assert (101, "parent") in pairs and (101, "student") in pairs, (
        "انتظار می‌رفت رفتار فعلی (باگ) دقیقاً (101,parent)+(101,student) باشد؛ actual=%r" % (pairs,))

    # شاهد مکمل: ردیف SmsLog این اعلان‌ها هم شناسه‌ی اشتباه (فضای Student.id) را در audit trail دارد
    sms_groups = {s.target_group for s in notif_world.db.query(models.SmsLog)
                  .filter(models.SmsLog.target_group.like("notif_%")).all()}
    assert {"notif_parent_101", "notif_student_101"} <= sms_groups, (
        f"SmsLog نیز شناسه‌ی اشتباه را ثبت می‌کند؛ actual={sorted(sms_groups)}")


def test_auto_reminder_without_user_ids_never_falls_back_to_student_id(notif_world):
    """🔎 سناریو ۶: شاگرد بدون user_id/parent_user_id ⇒ نه fallback به Student.id و نه اعلان بی‌صاحب."""
    _run_real_auto_reminder()
    rows = _installment_notifications(notif_world.db)
    for_104 = [r for r in rows if r.recipient_user_id in (104,)]
    assert for_104 == [], f"برای شاگرد ۱۰۴ اعلان با Student.id ساخته شد: {[(r.id, r.recipient_role) for r in for_104]}"

    # سیاست درست: یا رزولو به shadow-user (User.id واقعی) یا skip — نکته‌ی مهم: هیچ ردیفی با id=104
    st104 = notif_world.db.get(models.Student, 104)
    if st104.user_id:
        assert notif_world.db.get(models.User, st104.user_id) is not None, "user_id باید به یک User واقعی اشاره کند"
    if st104.parent_user_id:
        assert notif_world.db.get(models.User, st104.parent_user_id) is not None


def test_recipient_resolver_creates_shadow_user_not_student_id(notif_world):
    """🔎 سناریو ۶ (واحد): resolve_notification_recipient برای user_id خالی، shadow-user می‌سازد — نه Student.id."""
    db = notif_world.db
    resolved = resolve_notification_recipient(db, 104, "student")
    db.commit()
    assert resolved is not None and resolved != 104, f"resolver مقدار Student.id برگرداند: {resolved}"
    u = db.get(models.User, resolved)
    assert u is not None and u.sub_role == "student", "resolver باید User.id با sub_role=student برگرداند"

    resolved_parent = resolve_notification_recipient(db, 104, "parent")
    db.commit()
    assert resolved_parent not in (None, 104), f"resolver نقش parent اشتباه: {resolved_parent}"
    up = db.get(models.User, resolved_parent)
    assert up is not None and up.sub_role == "parent"


def test_recipient_resolver_missing_subject_returns_none(notif_world):
    """سناریو ۶ (واحد): subject ناموجود ⇒ None (نه id خام)."""
    assert resolve_notification_recipient(notif_world.db, 99999, "student") is None
    assert resolve_notification_recipient(notif_world.db, 99999, "parent") is None


def test_each_user_only_sees_own_installment_notification(notif_world):
    """🔎 سناریو ۷: صندوق اعلان هر کاربر فقط ردیف‌های recipient_user_id خودش (+ نقش خودش) را نشان می‌دهد.

    تحت باگ: ۵۰۱ و ۶۰۱ هیچ اعلان قسطی نمی‌بینند (چون همه با ۱۰۱ ثبت شده) ⇒ این تست هم red می‌شود.
    """
    _run_real_auto_reminder()
    db = notif_world.db
    student_inbox = db.query(models.Notification).filter(
        models.Notification.recipient_user_id == 501,
        models.Notification.recipient_role == "student",
        models.Notification.type == "installment").all()
    parent_inbox = db.query(models.Notification).filter(
        models.Notification.recipient_user_id == 601,
        models.Notification.recipient_role == "parent",
        models.Notification.type == "installment").all()
    assert len(student_inbox) == 1, "صندوق شاگرد ۵۰۱ باید دقیقاً یک اعلان قسط داشته باشد"
    assert len(parent_inbox) == 1, "صندوق ولی ۶۰۱ باید دقیقاً یک اعلان قسط داشته باشد"


def test_auto_reminder_silently_skips_student_when_parent_mobile_missing(notif_world):
    """📌 probe سیاست (سؤال محصولی): اگر parent_mobile خالی باشد، کل بلوک یادآوری رد می‌شود ⇒
    شاگردی که user_id دارد و قسطش معوق است **هیچ** اعلانی نمی‌گیرد (حتی اعلان شاگردی).
    این تست رفتار فعلی را مستند می‌کند (سیاست مبهم، نه لزوماً باگ)."""
    _run_real_auto_reminder()
    rows = [r for r in _installment_notifications(notif_world.db) if r.recipient_user_id in (505, 605, 105)]
    assert rows == [], f"برای شاگرد بدون parent_mobile اعلانی نیامده (رفتار فعلی): {rows}"


def test_manual_reminder_endpoint_uses_user_ids(notif_world):
    """✅ کنترل مثبت: مسیر دستی «یادآوری قسط» (finance.send_installment_payment_reminder)
    همان سیاست درست را دارد: user_id=501 برای شاگرد و parent_user_id=601 برای ولی."""
    db = notif_world.db
    result = finance.send_installment_payment_reminder(1, db=db, _="admin")
    assert result["status"] == "success"
    db.expire_all()
    pairs = {(r.recipient_user_id, r.recipient_role) for r in
             db.query(models.Notification).filter(models.Notification.type == "installment").all()}
    assert {(501, "student"), (601, "parent")} <= pairs, f"مسیر دستی اشتباه است: {pairs}"
    assert not any(p[0] == 101 for p in pairs), f"مسیر دستی Student.id فرستاده: {pairs}"
