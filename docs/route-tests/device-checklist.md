# Android device checklist — seed route-audit

این سند برای اجرای دستی روی build و backend متصل به **کپی disposable از seed** است. در این ممیزی Gradle compile، emulator یا گوشی واقعی اجرا نشده؛ موارد پایین، expected values/tests و known defects هستند، نه device-pass ادعایی. **هرگز** build را به `Kharazmi_Server/gaj_db.db` اصلی وصل نکنید.

## آماده‌سازی

- [ ] Backend را با temporary DB ساخته‌شده از `tests/route_audit/seed.py` اجرا کنید؛ امروز باید برابر `2026-09-28 09:00:00` باشد.
- [ ] SMS، push، payment gateway و تمام خروجی شبکه را mock/غیرفعال نگه دارید؛ `FCM_SERVER_KEY` خالی باشد.
- [ ] با build checkout فعلی اجرا کنید و screen/response را کنار JSONهای `tests/route_audit/sweep/` ثبت کنید.
- [ ] تفاوت API تاریخی/current را در `android-route-diff.md` ببینید؛ این audit 162 declaration تاریخی در برابر 169 declaration جاری را بررسی کرده است.
- [ ] بعد از هر flow، فقط DB موقت را بررسی کنید؛ برای مقایسه از pre/post row snapshotهای تست متناظر استفاده کنید.

## مقایسهٔ صفحه و wire values

| صفحه / route | مقدار یا رفتار مورد انتظار از isolated fixture | نتیجهٔ تست/قرارداد | دستگاه |
|---|---|---|---|
| `StudentPortalActivity` — `GET /students/my_profile` | نام `دانش‌آموز تست 1`؛ کد ملی `0020000001`؛ میانگین ریاضی `18.5`؛ بدهی `2,000,000`؛ wallet balance `-5,000` (teacher `-10,000`, institute `5,000`). | مقادیر مصرف‌شده در `test_audit_students.py` و `test_android_contract_regressions.py` assert شده‌اند. `parent_mobile` در پاسخ نیست ولی screen آن را نمی‌خواند (Q-007). | ☐ |
| `ParentPortalActivity` — `GET /parent/child_profile` | کودک `دانش‌آموز تست 1`؛ بدهی `2,000,000`؛ میانگین `18.5`؛ grade `میان‌ترم`; یک SMS واقعی نباید ارسال شود. | `test_parent_child_profile_exact_values_and_no_real_sms`; child scope/role نیز چک می‌شود. | ☐ |
| `ParentPortalActivity` — homework graded display | آیتم `تمرین هفته`; پس از grade=`17`, UI باید `17 / max_score` را نشان دهد. در پاسخ graded فعلی `max_score` غایب است و Kotlin non-null `Float` به 0.0 می‌رسد. | **باگ باز `RA-homework-01` strict-xfail**؛ بررسی دستی فقط روی DB موقت، مقدار نمایش‌داده‌شده را ثبت کند. | ☐ |
| `InvoiceActivity` — `GET /finance/invoice/1` | enrollment 1: شهریه ناخالص/نهایی `1,000,000`؛ پرداخت `300,000`؛ مانده `700,000`؛ دو قسط با مبلغ `350,000`. | response با class-status و independent finance oracle هم‌خوان است. وضعیت `paid_amount` قسط‌ها را از response/DB تطبیق دهید، نه از مبلغ اسمی به‌تنهایی. | ☐ |
| `InvoiceActivity` — `GET /finance/invoice/2` | enrollment 2: شهریه پایه `2,000,000`؛ تخفیف درصدی `10%`؛ شهریه نهایی `1,800,000`؛ پرداخت `500,000`؛ مانده `1,300,000`. | finance oracle فیلدهای discount/payment/due را assert می‌کند؛ قواعد کلی تخفیف مستقل از دادهٔ این seed هنوز business rule قطعی محسوب نمی‌شوند. | ☐ |
| `StudentProfileActivity` — `GET /finance/student/1/dashboard` | دو enrollment فعال با شناسه‌های 1 و 2 و title؛ student screen فعلی `enrollments` را مصرف می‌کند. | screen-consumed fields آزمون شده‌اند. برخی فیلدهای `recent_transactions` با shared `TransactionFullItem` کامل نیستند، اما caller جاری از آنها استفاده نمی‌کند (Q-008). | ☐ |
| `ReportActivity` / `GET /finance/reports/revenue_summary` | seed cash/revenue: total `675,000`; teacher wallet `375,000` (از جمله card=`125,000`)، institute wallet `300,000`. | JSON و receipt/transaction values تست شده‌اند. نام KPI «درآمد» و تفاوت وصول نقدی با تعهد شهریه هنوز Q-001 است؛ label نهایی محصول تأیید نشده. | ☐ |
| `AdminDashboardActivity` — `GET /dashboard/kpis` | today revenue `0`; overdue amount `700,000`; overdue installments `2`; active students `29`; suspicious alerts `0`; dunning pending `2`. Push status باید `{fcm_configured:false, device_token_count:0}` باشد. | exact-value KPI و local-only push status آزمون شده‌اند؛ push واقعی عمداً خاموش است. | ☐ |
| `ExamActivity` / exam list | فهرست فعلی شامل exam id 1 منتشرشده و exam id 2 با `status=pending` است. | رفتار دوم باگ باز O-12/`RA-exams-02` است: student list باید exam منتشرنشده را پنهان کند، ولی اکنون نشان می‌دهد. | ☐ |
| parent exam model — `ParentPortalActivity` | مقدار مرزی `max_score=12.5` باید decimal بماند و به integer parse نشود. | O-14/`RA-parent-01` در این checkout **بسته/سبز** است؛ `ParentExamItem.max_score` اکنون Float است و strict xfail ندارد. Runtime Gson/device هنوز اجرا نشده. | ☐ |
| live lesson screens | `started_at_ts=1790586000.25` (fractional) در fixture عمداً Long parse boundary را می‌آزماید. | `RA-attendance-01/02/03` و `RA-teachers-01` چهار strict xfail بازند؛ simulator آن را برای Kotlin `Long` نامعتبر می‌یابد. | ☐ |
| Parent finance screen — `GET /finance/parent/dashboard` | والد معتبر به financial dashboard کودک باید دسترسی داشته باشد. | Server اکنون 403 می‌دهد (`RA-finance-02`, strict xfail). Screen/caller متناظر در Retrofit جاری پیدا نشده؛ این route را با UI منتشرشده یکی فرض نکنید. | ☐ |
| Device push registration | Android باید FCM token را ثبت کند و Push SDK حاضر باشد. | O-02/`RA-auth-02` باز: Kotlin source scan، FirebaseMessaging یا ثبت `device_token` را پیدا نکرده؛ روی دستگاه ارسال push آزمایش نشده است. | ☐ |

## بررسی‌های عمومی

- [ ] مقدار، format و ترتیب هر لیست را با JSON خام تطبیق دهید؛ در response خالی، `[]` و `null` را از هم جدا کنید.
- [ ] filter/limit و pagination را در صفحه با درخواست/JSON واقعی تطبیق دهید؛ scale runner برای 300 student، 30 class و 300 transaction/session موفق شده است.
- [ ] بعد از submit/retry/cancel، دوباره صفحه را باز کنید و duplicate row/receipt یا rollback را در temporary DB بررسی کنید؛ رفتار Android UI جای DB assertion را نمی‌گیرد.
- [ ] Persian/number formatting را با unit definition مصوب محصول مقایسه کنید؛ تبدیل تومان/ریال را حدس نزنید (Q-003).
- [ ] `target_wallet=both`، پرداخت بی‌تاریخ و restore کلاس را تا پاسخ Q-002/Q-004/Q-005 با expected قطعی mark نکنید.
- [ ] PDF/XLSX bytes، export content و native print را جداگانه باز کنید؛ 200 یا فایلِ قابل دانلود به‌تنهایی صحت محتوا را ثابت نمی‌کند.
- [ ] نتیجهٔ دستی را با نام دستگاه/نسخهٔ build و `PASS`, `FAIL` یا `NOT RUN` به این checklist اضافه کنید؛ در حال حاضر تمام خانه‌ها `NOT RUN` هستند.
