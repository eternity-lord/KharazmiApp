# ممیزی routeهای `calendar`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `POST /calendar/check_conflicts` | handler `routers.calendar.check_scheduling_conflicts`؛ منبع `Kharazmi_Server/routers/calendar.py:76` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /calendar/events` | handler `routers.calendar.get_calendar_events`؛ منبع `Kharazmi_Server/routers/calendar.py:153` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /rooms/create` | handler `routers.calendar.create_physical_room`؛ منبع `Kharazmi_Server/routers/calendar.py:46` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /rooms/list` | handler `routers.calendar.get_all_rooms`؛ منبع `Kharazmi_Server/routers/calendar.py:71` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
