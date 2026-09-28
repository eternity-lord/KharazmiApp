# پیشرفت ممیزی routeها

**تاریخ شروع:** 2026-09-28 — **branch:** `arena/01a0c9b8-kharazmiapp`

## وضعیت زیرساخت

- seed قطعی در `tests/route_audit/seed.py` و wrapper در `scripts/seed_demo.py` ساخته شد.
- seed عادی: ۳۰ دانش‌آموز؛ seed حجیم: ۳۰۰ دانش‌آموز و ۳۰ کلاس.
- oracle مستقل و شبیه‌ساز قرارداد Kotlin ساخته شد.
- پلاگین/registry ممیزی همهٔ ۲۲۱ route را به فایل `test_audit_<router>.py` وصل می‌کند.
- seed فقط روی مسیر ورودی صریح و غیر از `Kharazmi_Server/gaj_db.db` کار می‌کند.

## routerها

| اولویت | router | route | وضعیت | commit گزارش |
|---:|---|---:|---|---|
| 1 | finance | 26 | **ممیزی اولیه انجام شد**؛ 11 route تست مقداری/DB دارند و همهٔ 26 route در inventory حاضرند | این turn |
| 2 | attendance | 15 | **ممیزی اولیه انجام شد**؛ 10 route تست مقداری/ماشین‌حالت دارند و همهٔ 15 route در inventory حاضرند | این turn |
| 3 | classes | 21 | scaffold صریح؛ functional audit هنوز انجام نشده | — |
| 4 | admin | 41 | scaffold صریح؛ functional audit هنوز انجام نشده | — |
| 5 | teachers | 18 | scaffold صریح؛ functional audit هنوز انجام نشده | — |
| 6 | students | 13 | scaffold صریح؛ functional audit هنوز انجام نشده | — |
| 7 | dashboard | 2 | scaffold صریح؛ functional audit هنوز انجام نشده | — |
| 8 | reports | 9 | scaffold صریح؛ functional audit هنوز انجام نشده | — |
| 9 | analytics | 6 | scaffold صریح؛ functional audit هنوز انجام نشده | — |
| 10 | exports | 3 | scaffold صریح؛ functional audit هنوز انجام نشده | — |
| 11 | exams | 7 | scaffold صریح؛ reproduction برای O-12 در `test_known_bugs.py` ثبت شد | — |
| 12 | homework | 6 | scaffold صریح؛ functional audit هنوز انجام نشده | — |
| 13 | parent | 5 | scaffold صریح؛ contract risk در infrastructure ثبت شده | — |
| 14 | crm / dunning / messages / automation | 19 | scaffold صریح؛ functional audit هنوز انجام نشده | — |
| 15 | calendar / branches / timeline / audit | 15 | scaffold صریح؛ functional audit هنوز انجام نشده | — |
| 16 | auth / ai / serve_upload | 14 | scaffold صریح؛ functional audit هنوز انجام نشده | — |

## آخرین اجرای ثبت‌شده

```text
command: /tmp/route-audit-venv/bin/python -m pytest tests/route_audit -q
result: 36 passed, 4 xfailed
```

این عدد به معنی ممیزی کامل رفتاری ۲۲۱ route نیست: registry همهٔ routeها را اجباری کرده، اما routeهای غیر finance/attendance در docs به‌صورت «مسدود/در انتظار نوبت router» ثبت شده‌اند.
