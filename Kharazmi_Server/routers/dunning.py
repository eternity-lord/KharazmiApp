"""
Smart Auto-Dunning (Human-in-the-Loop) - Isolated Router
- NO Auto-Send: only drafts
- Idempotency: filter installments with reminder in last 48h via ActivityLog/SmsLog
- Isolation: no modification to finance.py / timeline.py
- Security: Admin only (check_admin_access)
- Buckets: Upcoming 1-3d future / Overdue 1-7d past / Critical >7d past (via parse_project_date)
- Optimized: single query with joinedload(enrollment->student/course) to avoid N+1
"""
import datetime
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from models import ActivityLog, Enrollment, Installment, SmsLog, Student, User
from dependencies import get_db, check_admin_access, get_session_from_token
from today_summary import parse_project_date, jalali_date_string

router = APIRouter()


class DunningDraft(BaseModel):
    installment_id: int
    student_name: str
    parent_mobile: str
    amount: int
    due_date: str
    category: str  # upcoming | overdue | critical
    suggested_message: str


class SendBatchRequest(BaseModel):
    installment_ids: List[int]


def _jalali_now_str() -> str:
    _now = datetime.datetime.now()
    return jalali_date_string(_now.date()) + _now.strftime(" %H:%M")


def _get_admin_username(db: Session, authorization: Optional[str]) -> str:
    try:
        if not authorization:
            return "admin"
        parts = authorization.split()
        token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else None
        if not token:
            return "admin"
        sess, _ = get_session_from_token(db, token)
        if sess is not None and getattr(sess, "user_id", None):
            u = db.query(User).filter(User.id == sess.user_id).first()
            if u is not None and u.username:
                return u.username
    except Exception:
        pass
    return "admin"


def _categorize(due_date_str: Optional[str], today: datetime.date):
    d = parse_project_date(due_date_str)
    if not d:
        return None, None
    diff = (d - today).days  # due - today
    if 1 <= diff <= 3:
        return "upcoming", diff
    elif -7 <= diff <= -1:
        return "overdue", diff
    elif diff < -7:
        return "critical", diff
    else:
        return None, diff


def _suggested_message(category: str, student_name: str, amount: int, due_date: str, diff: int) -> str:
    amt = f"{amount:,}"
    if category == "upcoming":
        return f"سلام ولی محترم {student_name}، یادآوری: قسط شهریه فرزند شما به مبلغ {amt} تومان سررسید {due_date} (تا {diff} روز آینده) می‌باشد. لطفاً نسبت به پرداخت اقدام فرمایید. با تشکر - آموزشگاه خوارزمی"
    elif category == "overdue":
        overdue = -diff
        return f"سلام ولی محترم {student_name}، قسط شهریه فرزند شما به مبلغ {amt} تومان سررسید {due_date} ({overdue} روز گذشته) معوق شده است. لطفاً در اسرع وقت پرداخت فرمایید. - خوارزمی"
    else:  # critical
        overdue = -diff
        return f"⚠️ هشدار: قسط شهریه فرزند شما {student_name} به مبلغ {amt} تومان از تاریخ {due_date} ({overdue} روز گذشته) پرداخت نشده است. جهت جلوگیری از محدودیت ثبت‌نام، سریعاً اقدام فرمایید. - آموزشگاه خوارزمی"


def _collect_recent_ids(db: Session, candidate_ids: List[int], today: datetime.date) -> set:
    """Idempotency helper: ActivityLog OR SmsLog within 48h."""
    if not candidate_ids:
        return set()
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=48)
    recent = set()
    # ActivityLog: action like %dunning% or %remind%
    try:
        logs = (
            db.query(ActivityLog)
            .filter(ActivityLog.timestamp >= cutoff, ActivityLog.target_id.in_(candidate_ids))
            .filter(or_(ActivityLog.action.like("%dunning%"), ActivityLog.action.like("%remind%"), ActivityLog.action.like("%Reminder%"), ActivityLog.action.like("%reminder%")))
            .all()
        )
        for lg in logs:
            if lg.target_id in candidate_ids:
                recent.add(lg.target_id)
    except Exception as e:
        print(f"[Dunning] ActivityLog recent query failed: {e}")

    # SmsLog bulk: target_group contains candidate id, date within 48h via Jalali parsing
    try:
        sms_filters = [SmsLog.target_group.contains(str(cid)) for cid in candidate_ids]
        sms_logs = db.query(SmsLog).filter(or_(*sms_filters)).all() if sms_filters else []
        now_dt = datetime.datetime.now()
        for sms in sms_logs:
            # find matching candidate ids
            tg = sms.target_group or ""
            nums = re.findall(r"\d+", tg)
            matching = []
            for n in nums:
                try:
                    v = int(n)
                    if v in candidate_ids:
                        matching.append(v)
                except:
                    pass
            if not matching:
                # fallback substring
                matching = [cid for cid in candidate_ids if str(cid) in tg]
            if not matching:
                continue
            d = parse_project_date(sms.date)
            if not d:
                continue
            is_recent = False
            m = re.search(r"(\d{1,2})[:٫.](\d{2})", sms.date or "")
            if m:
                try:
                    hh = int(m.group(1)); mm = int(m.group(2))
                    sms_dt = datetime.datetime.combine(d, datetime.time(hh, mm))
                    delta = now_dt - sms_dt
                    if 0 <= delta.total_seconds() <= 48 * 3600:
                        is_recent = True
                except:
                    pass
            if not is_recent:
                diff_days = (today - d).days
                if 0 <= diff_days <= 2:
                    # if diff 2 with time we already checked precise; without time conservatively include
                    if diff_days < 2 or m is None:
                        is_recent = True
            if is_recent:
                for mid in matching:
                    recent.add(mid)
    except Exception as e:
        print(f"[Dunning] SmsLog recent query failed: {e}")
    return recent


@router.get("/dunning/drafts", response_model=List[DunningDraft])
def get_dunning_drafts(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    _: str = Depends(check_admin_access),
):
    """
    Human-in-the-Loop drafts: unpaid installments bucketed, filtered 48h idempotency.
    Optimized: single query with joinedload(enrollment->student/course).
    """
    today = datetime.datetime.now().date()

    # Single optimized query: Installment + Enrollment + Student/Course via joinedload (no N+1)
    installments = (
        db.query(Installment)
        .join(Enrollment, Installment.enrollment_id == Enrollment.id)
        .join(Student, Enrollment.student_id == Student.id)
        .options(
            joinedload(Installment.enrollment).joinedload(Enrollment.student),
            joinedload(Installment.enrollment).joinedload(Enrollment.course),
        )
        .filter(
            Installment.is_deleted == False,
            Installment.is_paid == False,
            Enrollment.is_deleted == False,
            Student.is_deleted == False,
        )
        .all()
    )

    candidates = []  # list of (inst, category, diff)
    for inst in installments:
        category, diff = _categorize(inst.due_date, today)
        if category is None:
            continue
        student = inst.enrollment.student if inst.enrollment else None
        if not student or not student.parent_mobile or not str(student.parent_mobile).strip():
            continue
        candidates.append((inst, category, diff))

    if not candidates:
        return []

    # Sort by diff ascending: critical oldest (-30) -> overdue -> upcoming (1-3)
    candidates.sort(key=lambda x: x[2])

    candidate_ids = [c[0].id for c in candidates]
    recent_ids = _collect_recent_ids(db, candidate_ids, today)

    drafts: List[DunningDraft] = []
    for inst, category, diff in candidates:
        if inst.id in recent_ids:
            continue
        student = inst.enrollment.student
        student_name = f"{student.first_name or ''} {student.last_name or ''}".strip() or "دانش‌آموز"
        parent_mobile = (student.parent_mobile or "").strip()
        amount = int(inst.amount or 0)
        suggested = _suggested_message(category, student_name, amount, inst.due_date or "", diff)
        drafts.append(
            DunningDraft(
                installment_id=inst.id,
                student_name=student_name,
                parent_mobile=parent_mobile,
                amount=amount,
                due_date=inst.due_date or "",
                category=category,
                suggested_message=suggested,
            )
        )
    return drafts


@router.post("/dunning/send_batch")
def send_dunning_batch(
    req: SendBatchRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    _: str = Depends(check_admin_access),
):
    """
    Mock SMS batch send: iterates installment_ids, creates SmsLog + ActivityLog, returns summary.
    Idempotency: skips if reminder within 48h.
    Admin only.
    """
    if not req.installment_ids:
        raise HTTPException(status_code=400, detail="لیست اقساط خالی است")

    # Deduplicate preserve order
    seen = set()
    unique_ids: List[int] = []
    for i in req.installment_ids:
        if i not in seen:
            seen.add(i)
            unique_ids.append(i)

    # Bulk fetch with joinedload to avoid N+1
    installments = (
        db.query(Installment)
        .join(Enrollment, Installment.enrollment_id == Enrollment.id)
        .join(Student, Enrollment.student_id == Student.id)
        .options(
            joinedload(Installment.enrollment).joinedload(Enrollment.student),
            joinedload(Installment.enrollment).joinedload(Enrollment.course),
        )
        .filter(
            Installment.id.in_(unique_ids),
            Installment.is_deleted == False,
        )
        .all()
    )
    inst_map = {inst.id: inst for inst in installments}
    today = datetime.datetime.now().date()
    recent_ids = _collect_recent_ids(db, unique_ids, today)
    admin_username = _get_admin_username(db, authorization)

    sent_ids: List[int] = []
    skipped_ids: List[int] = []
    skipped_reasons = {}

    for iid in unique_ids:
        inst = inst_map.get(iid)
        if not inst:
            skipped_ids.append(iid)
            skipped_reasons[str(iid)] = "یافت نشد"
            continue
        if inst.is_paid:
            skipped_ids.append(iid)
            skipped_reasons[str(iid)] = "پرداخت شده"
            continue
        if inst.enrollment and inst.enrollment.is_deleted:
            skipped_ids.append(iid)
            skipped_reasons[str(iid)] = "ثبت‌نام حذف شده"
            continue
        student = inst.enrollment.student if inst.enrollment else None
        if not student or not student.parent_mobile or not str(student.parent_mobile).strip():
            skipped_ids.append(iid)
            skipped_reasons[str(iid)] = "موبایل ولی یافت نشد"
            continue
        if iid in recent_ids:
            skipped_ids.append(iid)
            skipped_reasons[str(iid)] = "۴۸ ساعت گذشته یادآوری شده"
            continue

        category, diff = _categorize(inst.due_date, today)
        # Allow any unpaid even if not in bucket (fallback to overdue template)
        if category is None:
            category = "overdue"
            diff = -1 if diff is None else diff
            # if diff still None (unparseable) keep -1
            if diff is None or diff >= 0:
                diff = -1

        student_name = f"{student.first_name or ''} {student.last_name or ''}".strip() or "دانش‌آموز"
        amount = int(inst.amount or 0)
        suggested = _suggested_message(category, student_name, amount, inst.due_date or "", diff)

        # Mock SMS + ActivityLog (human-in-the-loop executed send)
        try:
            db.add(
                SmsLog(
                    target_group=f"dunning_{inst.id}",
                    message_text=suggested,
                    sent_count=1,
                    date=_jalali_now_str(),
                )
            )
            db.add(
                ActivityLog(
                    admin_username=admin_username,
                    action="dunning_reminder",
                    target_id=inst.id,
                    target_name=student_name,
                    details=suggested,
                    timestamp=datetime.datetime.utcnow(),
                )
            )
            sent_ids.append(iid)
            # add to recent set to avoid duplicate within same batch if duplicate ids were not deduped
            recent_ids.add(iid)
        except Exception as e:
            print(f"[Dunning send] failed for {iid}: {e}")
            skipped_ids.append(iid)
            skipped_reasons[str(iid)] = str(e)

    if sent_ids:
        db.commit()
    else:
        # commit skipped logs? none, but ensure session clean
        try:
            db.commit()
        except:
            db.rollback()

    return {
        "sent_count": len(sent_ids),
        "skipped_count": len(skipped_ids),
        "sent_ids": sent_ids,
        "skipped_ids": skipped_ids,
        "skipped_reasons": skipped_reasons,
        "message": f"{len(sent_ids)} پیام ارسال شد، {len(skipped_ids)} مورد رد شد (تکراری یا نامعتبر)",
    }
