# خلاصهٔ ممیزی تست‌محور routeها

**snapshot:** 2026-09-28 — **branch:** `arena/01a0c9b8-kharazmiapp`

## شمارش

| شاخص | مقدار | توضیح |
|---|---:|---|
| کل routeهای inventory | 221 | از `docs/app-map/server-routes.csv` |
| route دارای registry تست | 221 | meta-test اجباری است و missing route را fail می‌کند |
| route با functional assertion مقداری در این نوبت | 21 | finance: 11 route؛ attendance: 10 route با read، live state، نقش و invariant مالی |
| route functional باقی‌مانده | 200 | finance و attendance از inventory عبور کرده‌اند؛ routerهای بعدی هنوز در انتظارند |
| router پردازش‌شده | 2 | finance و attendance، ممیزی اولیه |
| تست‌های pass | 41 | آخرین اجرای routerهای زیرساخت + finance + attendance |
| تست‌های strict xfail | 4 | O-02، O-12، O-14، O-19 |
| باگ‌های ثبت‌شده | 4 | همان چهار مورد شناخته‌شده؛ باگ جدید finance ثبت نشد |

## پوشش این نوبت

- مقدار response و متن فارسی در مسیرهای read finance بررسی شد.
- جزئیات session، history حضور، live start/status/cancel، roster و اثر صفر مالی بررسی شد.
- oracle مستقل برای tuition/discount/payment/due و wallet سهم‌ها استفاده شد.
- atomic update و retry برای پرداخت قسط بررسی شد.
- invalid amount بررسی شد و عدم ایجاد transaction assert شد.
- پاسخ خالی installments به‌صورت `[]` بررسی شد.
- dynamic URL، امنیت token و نفوذ خارج از scope باقی ماندند.

## موارد ناتمام

- ۲۱۰ route functional هنوز باید طبق ترتیب `progress.md` تکمیل شوند.
- exports هنوز به openpyxl/PDF value audit نشده است.
- device checklist عددهای screenهای مهم را دارد، اما اجرای گوشی/compile انجام نشده است.
- تصمیم‌های Q-001 تا Q-005 باید از صاحب محصول گرفته شوند.
- CI remote در این turn اجرا نشده؛ اجرای محلی route-audit ثبت‌شده است.
