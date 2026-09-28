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
| 1 | finance | 26 | **ممیزی اولیه + mutation validation انجام شد**؛ 11 route دارای assertion مقداری، و 4 oracle مالی جدید | این turn |
| 2 | attendance | 15 | **ممیزی اولیه + mutation validation انجام شد**؛ 12 route دارای assertion مقداری/ماشین‌حالت و 2 oracle جبرانی | این turn |
| 3 | classes | 21 | **ممیزی اولیه انجام شد**؛ 8 route تست مقداری، state و Excel دارند و همهٔ 21 route در inventory حاضرند | این turn |
| 4 | admin | 41 | **deep audit کامل قبلی + RA-admin-01 fix**؛ 41/41 route assertion/guard | `1ac90d0`؛ CI `36411439389` |
| 5 | teachers | 18 | **deep slice انجام شد**؛ settlement/retry/reversal/payout/wallet و responseهای لیست assert شدند | `cdb72b5`؛ CI `36411439389` |
| 6 | students | 13 | **deep slice انجام شد**؛ profile/grades/access/empty search/version conflict | `cdb72b5`؛ CI `36411439389` |
| 7 | dashboard | 2 | **deep slice انجام شد**؛ KPI exact values و push redaction | `cdb72b5`؛ CI `36411439389` |
| 8 | reports | 9 | **deep slice انجام شد**؛ debtor/statement/chart/order/access | `cdb72b5`؛ CI `36411439389` |
| 9 | analytics | 6 | **deep slice انجام شد**؛ custom date/filter/limit/funnel invalid range | `cdb72b5`؛ CI `36411439389` |
| 10 | exports | 3 | **deep slice انجام شد**؛ CSV headers/rows/BOM/role guard | `cdb72b5`؛ CI `36411439389` |
| 11 | exams | 7 | **deep slice انجام شد**؛ list shape، attempt retry و O-12 untouched | `cdb72b5`؛ CI `36411439389` |
| 12 | homework | 6 | **deep slice انجام شد**؛ parent/student scope و optional defaults | `cdb72b5`؛ CI `36411439389` |
| 13 | parent | 5 | **deep slice انجام شد**؛ child profile values، portal HTML و no-SMS | `cdb72b5`؛ CI `36411439389` |
| 14 | crm / dunning / messages / automation | 19 | scaffold صریح؛ functional audit هنوز انجام نشده | — |
| 15 | calendar / branches / timeline / audit | 15 | scaffold صریح؛ functional audit هنوز انجام نشده | — |
| 16 | auth / ai / serve_upload | 14 | scaffold صریح؛ functional audit هنوز انجام نشده | — |

## آخرین اجرای ثبت‌شده

```text
pytest tests/route_audit -q: 86 passed, 3 xfailed, 4 warnings
admin deep audit: 41/41 route assertion/guard؛ RA-admin-01 fixed؛ direct student fallback سبز
route sweep: 221 route؛ status 500=0؛ invalid-target=220؛ invalid status 500=0
Retrofit contract: 151 unique؛ dynamic=1؛ unmatched=0؛ issue=0؛ RA-sweep=4 normal assertions
retry guards: direct payment=1؛ installment=1؛ session charge=1؛ teacher settlement/reversal=1
mutation validation: 10/10 caught؛ 0 escaped؛ route assertions=72/221
```

آخرین mutation-validation push سبز است: [CI run 36413712720](https://github.com/eternity-lord/KharazmiApp/actions/runs/36413712720)؛ mutation validation در `mutation-validation.md` ثبت شد؛ checksum DB اصلی `f048f8d11833c4eaa944490594121d7` باقی مانده است.

این sweep جای ممیزی عمیق را نمی‌گیرد: registry همهٔ routeها را اجباری کرده، ۳۳ route از finance/attendance/classes در blockers با دلیل واقعی یک‌خطی بسته شده‌اند. calendar، branches، timeline و audit در این مرحله فقط sweep باقی مانده‌اند.
