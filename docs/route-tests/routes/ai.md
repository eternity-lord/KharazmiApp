# ممیزی routeهای `ai`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `POST /ai/chat` | handler `routers.ai.chat_with_ai_assistant`؛ منبع `Kharazmi_Server/routers/ai.py:153` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
