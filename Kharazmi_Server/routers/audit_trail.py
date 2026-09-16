"""Financial Audit Trail — ردگیری کامل تغییرات مالی (Transaction / Installment).

## چرا این‌طور پیاده شد
- **لاگ‌گیری خودکار**: listener روی `Session.before_flush` + `Session.after_flush_postexec`.
  هیچ اندپوینتی لاگ نمی‌زند؛ هر مسیری که از ORM بنویسد (finance, classes, automation, admin, ...)
  خودکار لاگ می‌شود و هیچ‌کدام از روترهای موجود دست نمی‌خورند.
- **before_flush** = مقادیر «قبلی»: در این لحظه هنوز UPDATE/DELETE اجرا نشده، پس اسنپ‌شات
  از ردیف دیتابیس (`SELECT`) دقیقاً مقدار قبلی است. (reading از state آبجکت غلط است: بعد از
  commit، آبجکت‌ها expire‌اند و مقدار قبلی در حافظه وجود ندارد.)
- **after_flush_postexec** = مقادیر «جدید» + `entity_id`: در create، PK تازه بعد از INSERT تعیین
  می‌شود (در before_flush هنوز None است) و defaultهای ستون‌ها هم فقط بعد از INSERT اعمال شده‌اند.
- **درج لاگ با Core-insert روی `session.connection()`**: در همان تراکنشِ نوشتن ⇒ rollback
  ⇒ لاگ هم برمی‌گردد (هیچ تغییر commit‌نشده‌ای لاگ نمی‌شود). درج از مسیر ORM انجام نمی‌شود تا
  خودِ ردیف لاگ دوباره باعث flush/recursion نشود.
- **UPDATE بی‌اثر لاگ نمی‌شود**: اگر کسی بعد از commit دوباره همان مقدار را set کند، SQLAlchemy
  یک UPDATE می‌فرستد؛ با مقایسه‌ی اسنپ‌شات قبلی/جدید این نویز حذف می‌شود.
- **مقاوم‌بودن**: هیچ استثنایی از listener بیرون نمی‌زند؛ خطای لاگ ⇒ هشدار در لاگ سرور و
  نوشتن بیزینس سالم می‌ماند.
- **محدودیت آگاهانه**: bulk update/delete سبک Core (`query.update()`, `query.delete()`) رویداد
  ORM تولید نمی‌کند ⇒ لاگ نمی‌شود. مسیرهای مالی این پروژه از ORM استفاده می‌کنند.
- **زمان**: `timestamp` به UTC ذخیره می‌شود (استاندارد پروژه) و اندپوینت آن را به وقت محلی سرور
  برمی‌گرداند؛ فیلترهای تاریخ هم به‌صورت تاریخ محلی/جلالی گرفته و به UTC تبدیل می‌شوند.
"""
import contextvars
import datetime
import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import event, inspect, select
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

import models
from dependencies import check_admin_access, get_db, get_session_from_token
from models import FinancialAuditLog, Installment, Transaction, User

router = APIRouter()

# مدل‌های تحت نظر + مقادیر مجاز فیلترها
AUDITED_MODELS = (Transaction, Installment)
ENTITY_TYPES = ("transaction", "installment")
ACTIONS = ("create", "update", "delete")

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
_MAX_CELL_CHARS = 1000          # سقف طول هر مقدار در JSON (محافظت از سلول‌های غول)
_PENDING_KEY = "_kharazmi_audit_pending"


# ==========================================
# 1) زمینه‌ی درخواست (کاربر/IP) برای listener ها
# ==========================================
# چرا ContextVar و نه request.state: listener های SQLAlchemy به درخواست دسترسی ندارند و
# میدل‌ور/اندپوینت در تسک‌های متفاوت اجرا می‌شوند؛ ContextVar در async و به‌صورت خودکار در
# threadpool (اندپوینت‌های sync) کپی می‌شود ⇒ امن و بی‌نیاز از global mutable.
_audit_context: "contextvars.ContextVar[Optional[Dict[str, Any]]]" = contextvars.ContextVar(
    "kharazmi_audit_context", default=None
)


def set_audit_context(user_id: Optional[int], username: Optional[str], ip_address: Optional[str]):
    return _audit_context.set({"user_id": user_id, "username": username, "ip_address": ip_address})


def reset_audit_context(token) -> None:
    try:
        _audit_context.reset(token)
    except (ValueError, LookupError):
        # token متعلق به context دیگری است (تسک‌های فرزند) — بی‌خطر
        pass


def current_audit_context() -> Dict[str, Any]:
    return _audit_context.get() or {}


def _client_ip(request) -> Optional[str]:
    """IP کاربر: اولین مقدار X-Forwarded-For (پشت ریورس‌پروکسی) وگرنه هاست اتصال."""
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if forwarded:
        return forwarded[:45]
    client = getattr(request, "client", None)
    host = getattr(client, "host", None) if client is not None else None
    return host[:45] if host else None


class AuditContextMiddleware(BaseHTTPMiddleware):
    """برای درخواست‌های تغییردهنده، کاربر توکن را در ContextVar می‌گذارد تا listener ها
    بتوانند «چه کسی» را ثبت کنند.

    - فقط متدهای POST/PUT/PATCH/DELETE ⇒ روی خواندن‌ها (GET) صفر سربار/صفر کوئری.
    - کش کوتاه ۳۰ ثانیه‌ای توکن→کاربر: درخواست‌های نوشتنِ پشت‌سرهم یک کاربر، یک کوئری اضافه ندارند.
    - این میدل‌ور فقط «برچسب» لاگ را می‌سازد؛ احراز هویت واقعی همان Depends(check_admin_access)/get_db است.
    """

    _MUTATING = frozenset({"POST", "PUT", "PATCH", "DELETE"})
    _TTL_SECONDS = 30
    _MAX_CACHE = 256
    _cache: Dict[str, Tuple[float, Optional[int], Optional[str]]] = {}

    async def dispatch(self, request, call_next):
        token = self._bearer_token(request) if request.method in self._MUTATING else None
        context_token = None
        if token:
            identity = self._resolve_identity(token)
            if identity is not None:
                context_token = set_audit_context(identity[0], identity[1], _client_ip(request))
        try:
            return await call_next(request)
        finally:
            # پاک‌سازی لازم است: در غیر این‌صورت کاربرِ درخواست قبلی به درخواست بعدی «نشت» می‌کرد.
            if context_token is not None:
                reset_audit_context(context_token)

    @staticmethod
    def _bearer_token(request) -> Optional[str]:
        parts = (request.headers.get("authorization") or "").split()
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1]:
            return parts[1]
        return None

    @classmethod
    def _resolve_identity(cls, token: str) -> Optional[Tuple[Optional[int], Optional[str]]]:
        now = time.monotonic()
        cached = cls._cache.get(token)
        if cached is not None and cached[0] > now:
            return cached[1], cached[2]

        db = models.SessionLocal()
        try:
            session, _ = get_session_from_token(db, token)
            if not session:
                return None
            user = db.query(User).filter(User.id == session.user_id).first()
            if not user:
                return None
            if len(cls._cache) >= cls._MAX_CACHE:
                cls._cache.clear()
            cls._cache[token] = (now + cls._TTL_SECONDS, user.id, user.username)
            return user.id, user.username
        except Exception as exc:  # توکن خراب/دیتابیس در دسترس نباشد ⇒ لاگ بی‌کاربر، نه 500
            print(f"⚠️ Audit Trail: resolve user failed: {exc}")
            return None
        finally:
            db.close()


# ==========================================
# 2) اسنپ‌شات‌گیری و listener های SQLAlchemy
# ==========================================
def _column_keys(obj) -> List[str]:
    try:
        return [attr.key for attr in inspect(obj).mapper.column_attrs]
    except Exception:
        return []


def _db_snapshot(session: Session, obj) -> Optional[Dict[str, Any]]:
    """اسنپ‌شات ردیف فعلی دیتابیس (در before_flush = مقادیر قبلی) با یک SELECT."""
    pk = getattr(obj, "id", None)
    if pk is None:
        return None
    table = obj.__table__
    keys = [key for key in _column_keys(obj) if key in table.c]
    if not keys:
        return None
    try:
        row = session.connection().execute(
            select(*[table.c[key] for key in keys]).where(table.c.id == pk)
        ).mappings().first()
    except Exception as exc:
        print(f"⚠️ Audit Trail: old snapshot failed: {exc}")
        return None
    return dict(row) if row is not None else None


def _state_snapshot(obj) -> Dict[str, Any]:
    """اسنپ‌شات state آبجکت (در after_flush_postexec = مقادیر نهایی، شامل defaultهای ستون)."""
    snapshot: Dict[str, Any] = {}
    for key in _column_keys(obj):
        try:
            snapshot[key] = getattr(obj, key)
        except Exception:
            # آبجکت حذف‌شده/expire‌شده — مقدار در دسترس نیست (نمی‌خواهیم اینجا خطا بدهیم)
            snapshot[key] = None
    return snapshot


def _comparable(payload: Optional[Dict[str, Any]]) -> Any:
    """نرمال‌سازی برای مقایسه (DateTime/Decimal → رشته) تا مقایسه‌ی قبلی/جدید معتبر باشد."""
    if payload is None:
        return None
    try:
        return json.loads(json.dumps(payload, default=str, ensure_ascii=False, sort_keys=True))
    except Exception:
        return str(payload)


def _dump(payload: Optional[Dict[str, Any]]) -> Optional[str]:
    if payload is None:
        return None
    safe: Dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, str) and len(value) > _MAX_CELL_CHARS:
            value = value[:_MAX_CELL_CHARS] + "…"
        safe[key] = value
    try:
        return json.dumps(safe, ensure_ascii=False, default=str)
    except Exception:
        try:
            return json.dumps({key: str(value) for key, value in payload.items()}, ensure_ascii=False)
        except Exception as exc:
            print(f"⚠️ Audit Trail: dump failed: {exc}")
            return None


def _entity_type(obj) -> str:
    return "transaction" if isinstance(obj, Transaction) else "installment"


def _capture_financial_changes(session: Session, flush_context, instances) -> None:
    """before_flush: مقادیر قبلی را از DB می‌خواند و رکوردها را در session.info نگه می‌دارد."""
    try:
        records = session.info.setdefault(_PENDING_KEY, [])
        for obj in list(session.new):
            if isinstance(obj, AUDITED_MODELS):
                records.append({"obj": obj, "action": "create", "old": None})
        for obj in list(session.dirty):
            if not isinstance(obj, AUDITED_MODELS) or obj in session.deleted:
                continue
            old = _db_snapshot(session, obj)
            if old is not None and _comparable(old) == _comparable(_state_snapshot(obj)):
                # UPDATE بی‌اثر (مقدار هم‌مقدار ست‌شده بعد از expire) ⇒ نویز لاگ نمی‌شود
                continue
            records.append({"obj": obj, "action": "update", "old": old})
        for obj in list(session.deleted):
            if isinstance(obj, AUDITED_MODELS):
                old = _db_snapshot(session, obj)
                records.append({
                    "obj": obj,
                    "action": "delete",
                    "old": old if old is not None else _state_snapshot(obj),
                })
    except Exception as exc:
        print(f"⚠️ Audit Trail: capture failed (نوشتن بیزینس ادامه می‌یابد): {exc}")


def _persist_financial_logs(session: Session, flush_context) -> None:
    """after_flush_postexec: PK/مقادیر نهایی مشخص است ⇒ درج لاگ در همان تراکنش."""
    records = session.info.pop(_PENDING_KEY, None)
    if not records:
        return
    context = current_audit_context()
    now = datetime.datetime.utcnow()
    rows = []
    for record in records:
        obj = record["obj"]
        action = record["action"]
        new_values = None if action == "delete" else _state_snapshot(obj)
        rows.append({
            "timestamp": now,
            "user_id": context.get("user_id"),
            "username": context.get("username"),
            "action": action,
            "entity_type": _entity_type(obj),
            "entity_id": getattr(obj, "id", None),
            "old_values": _dump(record["old"]),
            "new_values": _dump(new_values),
            "ip_address": context.get("ip_address"),
        })
    try:
        session.connection().execute(FinancialAuditLog.__table__.insert(), rows)
    except Exception as exc:
        # تصمیم آگاهانه: «در‌دسترس‌بودن» مهم‌تر از «کامل‌بودن» است — یک خطای لاگ نباید
        # ثبت پرداخت/قسط را ۵۰۰ کند. با هشدار در لاگ سرور کاملاً قابل رصد است.
        print(f"⚠️ Audit Trail: insert failed, {len(rows)} record(s) skipped: {exc}")


def _drop_pending_records(session: Session, *args) -> None:
    """rollback (کامل یا savepoint) ⇒ رکوردهای معلق دور ریخته می‌شوند."""
    session.info.pop(_PENDING_KEY, None)


_LISTENERS_INSTALLED = False


def setup_audit_listeners(engine=None) -> bool:
    """ثبت listener ها (idempotent) + اطمینان از وجود جدول `financial_audit_logs`.

    برمی‌گرداند True اگر همین حالا نصب شد (برای تست/گزارش).
    """
    global _LISTENERS_INSTALLED
    if _LISTENERS_INSTALLED:
        return False
    event.listen(Session, "before_flush", _capture_financial_changes)
    event.listen(Session, "after_flush_postexec", _persist_financial_logs)
    event.listen(Session, "after_rollback", _drop_pending_records)
    event.listen(Session, "after_soft_rollback", _drop_pending_records)
    _LISTENERS_INSTALLED = True
    # مایگریشن: فقط همین جدول جدید (idempotent، بدون دست‌زدن به جداول موجود).
    try:
        FinancialAuditLog.__table__.create(bind=engine or models.engine, checkfirst=True)
    except Exception as exc:
        print(f"⚠️ Audit Trail: create table failed: {exc}")
    return True


# ==========================================
# 3) اندپوینت کوئری — GET /audit-trail/logs (admin only)
# ==========================================
class AuditLogEntry(BaseModel):
    id: int
    timestamp: str
    username: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    changed_fields: List[str] = []


class AuditTrailResponse(BaseModel):
    logs: List[AuditLogEntry]
    total: int
    page: int
    limit: int
    pages: int


def _load_json(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    """JSON خراب ⇒ هرگز ۵۰۰ نمی‌دهد."""
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except Exception:
        return {"raw": raw[:_MAX_CELL_CHARS]}
    return value if isinstance(value, dict) else {"value": value}


def _changed_fields(action: str, old: Optional[Dict[str, Any]], new: Optional[Dict[str, Any]]) -> List[str]:
    # کلید مصنوعی «raw» (JSON خراب که قابل تفسیر نبود) ستون واقعی نیست ⇒ نویز گزارش نشود.
    old = {key: value for key, value in (old or {}).items() if key != "raw"}
    new = {key: value for key, value in (new or {}).items() if key != "raw"}
    if action == "create":
        return sorted(key for key, value in new.items() if value is not None)
    if action == "delete":
        return sorted(key for key, value in old.items() if value is not None)
    keys = set(old) | set(new)
    return sorted(key for key in keys if old.get(key) != new.get(key))


def _to_local_naive(value: datetime.datetime) -> datetime.datetime:
    """UTC ذخیره‌شده → وقت محلی سرور (برای نمایش درست در اپ)."""
    try:
        return value.replace(tzinfo=datetime.timezone.utc).astimezone().replace(tzinfo=None)
    except Exception:
        return value


def _to_utc_naive(value: datetime.datetime) -> datetime.datetime:
    """تاریخ/ساعت محلی سرور → UTC (برای فیلتر روی ستون UTC)."""
    try:
        return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    except Exception:
        return value


_JALALI_DATE_RE = re.compile(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$")


def _parse_bound(value: Optional[str], *, is_end: bool) -> Tuple[Optional[datetime.datetime], bool]:
    """پارامتر تاریخ/ساعت را به UTC تبدیل می‌کند.

    پذیرش: ISO (`2026-09-16` یا `2026-09-16T14:30[:00]`)، Jalali (`1405/06/25` — سال < 1700).
    برمی‌گرداند (datetime_utc, inclusive)؛ برای تاریخ خالصِ end، «کل آن روز» پوشش داده می‌شود.
    """
    if value is None:
        return None, True
    text = value.strip().replace("T", " ")
    if not text:
        return None, True

    match = _JALALI_DATE_RE.match(text)
    if match:
        year, month, day = (int(part) for part in match.groups())
        try:
            if year < 1700:  # جلالی (هم‌راستا با today_summary.parse_project_date)
                from today_summary import jalali_to_gregorian
                date_value = jalali_to_gregorian(year, month, day)
            else:
                date_value = datetime.date(year, month, day)
        except Exception:
            raise HTTPException(status_code=400, detail=f"تاریخ نامعتبر است: {value}")
        start = datetime.datetime.combine(date_value, datetime.time.min)
        if is_end:
            return _to_utc_naive(start + datetime.timedelta(days=1)), False  # کل روز پایان
        return _to_utc_naive(start), True

    try:
        parsed = datetime.datetime.fromisoformat(text)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="قالب تاریخ نامعتبر است (نمونه‌ی درست: 2026-09-16 یا 1405/06/25)",
        )
    return _to_utc_naive(parsed), True


@router.get("/audit-trail/logs", response_model=AuditTrailResponse)
def list_audit_logs(
    entity_type: Optional[str] = Query(None, description="transaction | installment"),
    entity_id: Optional[int] = Query(None, ge=1, description="شناسه‌ی رکورد مالی"),
    action: Optional[str] = Query(None, description="create | update | delete"),
    user_id: Optional[int] = Query(None, ge=1, description="فیلتر بر اساس کاربر"),
    start_date: Optional[str] = Query(None, description="از تاریخ (ISO یا جلالی)"),
    end_date: Optional[str] = Query(None, description="تا تاریخ (ISO یا جلالی، شامل کل روز)"),
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    _: str = Depends(check_admin_access),
    db: Session = Depends(get_db),
):
    """تاریخچه‌ی تغییرات مالی، صفحه‌بندی‌شده و فیلترپذیر (فقط ادمین)."""
    if entity_type is not None and entity_type not in ENTITY_TYPES:
        raise HTTPException(status_code=400, detail="entity_type باید transaction یا installment باشد")
    if action is not None and action not in ACTIONS:
        raise HTTPException(status_code=400, detail="action باید create یا update یا delete باشد")

    start_dt, start_inclusive = _parse_bound(start_date, is_end=False)
    end_dt, end_inclusive = _parse_bound(end_date, is_end=True)
    if start_dt and end_dt and start_dt > end_dt:
        raise HTTPException(status_code=400, detail="start_date بعد از end_date است")

    query = db.query(FinancialAuditLog)
    if entity_type is not None:
        query = query.filter(FinancialAuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(FinancialAuditLog.entity_id == entity_id)
    if action is not None:
        query = query.filter(FinancialAuditLog.action == action)
    if user_id is not None:
        query = query.filter(FinancialAuditLog.user_id == user_id)
    if start_dt is not None:
        query = query.filter(FinancialAuditLog.timestamp >= start_dt if start_inclusive
                             else FinancialAuditLog.timestamp > start_dt)
    if end_dt is not None:
        query = query.filter(FinancialAuditLog.timestamp <= end_dt if end_inclusive
                             else FinancialAuditLog.timestamp < end_dt)

    total = query.count()
    rows = (
        query.order_by(FinancialAuditLog.timestamp.desc(), FinancialAuditLog.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    logs: List[AuditLogEntry] = []
    for row in rows:
        old_values = _load_json(row.old_values)
        new_values = _load_json(row.new_values)
        logs.append(AuditLogEntry(
            id=row.id,
            timestamp=_to_local_naive(row.timestamp).isoformat(sep=" ") if row.timestamp else "",
            username=row.username,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=row.ip_address,
            changed_fields=_changed_fields(row.action, old_values, new_values),
        ))

    pages = (total + limit - 1) // limit if limit else 0
    return AuditTrailResponse(logs=logs, total=total, page=page, limit=limit, pages=pages)
