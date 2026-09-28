# گزارش جاروب خودکار همهٔ routeها

**ابزارها:** `tests/route_audit/sweep/run_sweep.py` و `run_contract.py`  
**داده:** seed موقت در `/tmp`؛ دیتابیس اصلی لمس نشد.

## route sweep

| شاخص | مقدار |
|---|---:|
| route اجراشده | 221/221 |
| route با status 500 | 0 |
| payload نامعتبر OpenAPI target | 220 |
| payload نامعتبر با status 500 | 0 |
| empty probe | 11 |
| empty probe با list=`null` | 0 |
| پاسخ non-JSON مورد انتظار | 13 (Excel/PDF/HTML/ResponseBody) |

statusها و شکل پاسخ هر route در `tests/route_audit/sweep/report.json` و جدول قابل جست‌وجو در `report.csv` ثبت شده‌اند. statusهای 4xx در این sweep با payload/role/پیش‌شرط seed ثبت شده‌اند و تا زمانی که assertion رفتاری router نوشته نشود به‌عنوان باگ 500 شمرده نشده‌اند.

## Retrofit/Gson contract sweep

| شاخص | مقدار |
|---|---:|
| declaration | 162 |
| method/path یکتای خام | 151 |
| `@Url` dynamic | 1 |
| static call با route معادل | 150 |
| static call بدون route معادل | 0 |
| route response با status غیرموفق | 49 (پیش‌شرط/نقش/بدنهٔ generic؛ باگ 500 نیست) |
| parse/overflow | 0 |
| NPE بالقوه از non-null missing | 6 issue instance در 3 entry |
| missing list key | 1 |
| silent zero | 0 |
| RA-sweep با strict xfail | 4 entry |

چهار entry دارای issue و شناسهٔ xfail در `bugs.md` آمده‌اند. برای آزمون‌های status غیرموفق، علت دقیق response باید در ممیزی عمیق همان router تعیین شود؛ status غیرموفق generic به‌تنهایی ادعای باگ نیست.
