# گزارش جاروب خودکار همهٔ routeها

**snapshot:** 2026-09-28 — **branch:** `arena/01a0c9b8-kharazmiapp`

**ابزارها:** `tests/route_audit/sweep/run_sweep.py`، `run_contract.py`، `run_boundary.py` و `run_large.py`

**داده:** همهٔ fixtureها در SQLite موقت `/tmp` ساخته شدند؛ `Kharazmi_Server/gaj_db.db` لمس نشد.

## route sweep پس از فیکس‌ها

| شاخص | مقدار |
|---|---:|
| route اجراشده | 221/221 |
| route با status 500 | 0 |
| payload نامعتبر OpenAPI target | 220 |
| payload نامعتبر با status 500 | 0 |
| empty probe | 11 |
| empty probe با list=`null` | 0 |
| پاسخ non-JSON مورد انتظار | 13 (Excel/PDF/HTML/ResponseBody) |

جزئیات status/shape در `tests/route_audit/sweep/report.json` و `report.csv` ثبت شده است. 4 مورد contract ثبت‌شده بعد از فیکس پاسخ server/client اکنون assertion عادی دارند و هیچ entry دارای issue باقی نمانده است.

## Retrofit/Gson contract sweep پس از فیکس‌ها

| شاخص | مقدار |
|---|---:|
| declaration | 162 |
| method/path یکتای خام | 151 |
| `@Url` dynamic | 1 |
| static call با route معادل | 150 |
| static call بدون route معادل | 0 |
| route response با status غیرموفق | 49 (پیش‌شرط/نقش/بدنهٔ generic؛ باگ 500 نیست) |
| parse/overflow | 0 |
| NPE بالقوه از non-null missing | 0 |
| missing list key | 0 |
| silent zero | 0 |
| entry دارای issue | 0 |
| assertion عادی RA-sweep | 4 (`RA-sweep-01..04`) |

`contract-report.json` آخرین بار پس از `RA-parent-01` تولید شده و `issues=[]` برای همهٔ entryها دارد. `O-02`، `O-12` و `O-19` عمداً تغییر نکرده‌اند.

## seed مرزی مستقل

`tests/route_audit/sweep/boundary_seed.py` روی DB موقت جدا از seed عادی این موارد را اضافه می‌کند:

- `max_score=12.5` در Exam؛
- مبلغ `2^31+1 = 2147483649` در Transaction؛
- فیلدهای اختیاری `null` در description/profile image؛
- رشتهٔ خالی در تاریخ transaction و due_date homework؛
- `students_preview=[]` به‌عنوان empty list.

اجرای `run_boundary.py`: **4 route، status 500 برابر 0، Gson issue برابر 0**. مقادیر واقعی در `boundary-report.json` ثبت شده‌اند و `test_boundary_seed.py` آن‌ها را دقیق assert می‌کند.

## seed حجیم و limit/order/filter

`tests/route_audit/sweep/large_seed.py` از `seed_database(..., large=True)` با **300 دانش‌آموز و 30 کلاس** استفاده کرده و برای transaction/session نیز 300 ردیف مستقل اضافه می‌کند. اجرای `run_large.py` سبز است:

- جستجوی دانش‌آموز: سقف 20، ترتیب دقیق `300..281`؛
- کلاس‌ها: 29 کلاس فعال، حذف‌شده‌ها خارج، ترتیب نزولی، filter برای `تست 300` فقط کلاس 1؛
- تراکنش‌ها: 305 ردیف فعال، نخستین id برابر 399؛
- بدهکاران: فهرست کامل scale با حداقل 290 ردیف؛
- pending session معلم: 301 ردیف، ترتیب معتبر تاریخی سپس session id نزولی، اولین ردیف حجیم id=399.

Artifact این اجرا `large-report.json` و regression آن `test_large_seed.py` است.

## mapping شش NPE و یک missing-list قبل از فیکس

| شناسه | issueهای واقعی قبل از فیکس | علت و اصلاح |
|---|---|---|
| RA-sweep-01 | missing-non-null: `SimpleResponse.message` | bulk approve اکنون `message` صریح دارد. |
| RA-sweep-02 | چهار missing-non-null (`description` و `due_date` برای دو item) | server اکنون هر دو را با رشتهٔ خالی صریح می‌فرستد. |
| RA-sweep-03 | یک missing-non-null: `HomeworkItem.description` | پاسخ parent homework اکنون `description or ""` دارد. |
| RA-sweep-04 | یک missing-list: `TeacherClassItem.students_preview` | کلاس ناقص بدون ثبت‌نام اکنون `students_preview: []` دارد. |

بنابراین 6 NPE بالقوه = 1+4+1 و 1 missing-list = 1؛ چهار موردی که باگ نبودند: parse/overflow، silent-zero، unmatched route و dynamic URL (به‌ترتیب 0، 0، 0 و 1 مورد).

## پاسخ الف: وضعیت seed عادی

seed عادی فعلی **30 دانش‌آموز** دارد؛ `Grade.score=12.5` دارد، اما پیش از seed مرزی `Exam.max_score=12.5` نداشت. مبلغ بزرگ‌تر از `2^31` نداشت. `null` اختیاری دارد (مانند `Grade.description` و برخی فیلدهای legacy)، رشتهٔ خالی دارد (مثل transaction بدون تاریخ)، اما empty-list مرزی صریح برای `students_preview` نداشت. به همین دلیل seed مستقل بالا ساخته و route sweep/Gson simulator روی آن اجرا شد.

## محدودیت تفسیر

statusهای 4xx در contract sweep معمولاً پیش‌شرط/نقش/بدنهٔ generic هستند و تا زمانی که deep audit همان router آن‌ها را oracle نکند، باگ محسوب نمی‌شوند. SMS، push، gateway، printer و network واقعی اجرا نشده‌اند.
