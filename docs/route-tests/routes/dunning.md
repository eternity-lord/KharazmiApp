# ممیزی routeهای `dunning`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `GET /dunning/drafts` | handler `routers.dunning.get_dunning_drafts`؛ منبع `Kharazmi_Server/routers/dunning.py:184` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /dunning/send_batch` | handler `routers.dunning.send_dunning_batch`؛ منبع `Kharazmi_Server/routers/dunning.py:256` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
