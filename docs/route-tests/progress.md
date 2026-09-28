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
| 3 | classes | 21 | **ممیزی اولیه انجام شد**؛ 8 route تست مقداری، state و Excel دارند و همهٔ 21 route در inventory حاضرند | این turn |
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
pytest tests/route_audit -q: 61 passed, 9 xfailed, 3 warnings
admin deep audit: 33/41 route assertion؛ 8 blocker؛ RA-admin-01 strict xfail
route sweep: 221 route؛ status 500=0؛ invalid-target=220؛ invalid status 500=0
Retrofit contract: 151 unique؛ dynamic=1؛ unmatched=0؛ RA-sweep=4 entry
retry guards: direct payment=1؛ installment=1؛ session charge=1؛ settlement in-scope=0
```

آخرین commit ممیزی: `00a13c870e992b2add86f94fa4170ebc20a0fcac` — [CI run 36408844870](https://github.com/eternity-lord/KharazmiApp/actions/runs/36408844870) سبز است.

این sweep جای ممیزی عمیق را نمی‌گیرد: registry همهٔ routeها را اجباری کرده، ۳۳ route از finance/attendance/classes در blockers با دلیل صریح بسته شده‌اند، admin هشت blocker دارد و ۱۵۱ route سایر routerها در انتظار نوبت هستند.
