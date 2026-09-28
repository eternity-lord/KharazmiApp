# ممیزی routeهای `messages`

این جدول از `docs/app-map/server-routes.csv` تولید شده است. هر claim تستی باید به نام تست و `file:line` ارجاع دهد.

| route | چه کاری می‌کند | تعداد تست | دسته‌های پوشش | نتیجه | باگ |
|---|---|---:|---|---|---|
| `POST /messages/broadcast` | handler `routers.messages.send_broadcast_message`؛ منبع `Kharazmi_Server/routers/messages.py:242` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /messages/conversations` | handler `routers.messages.get_my_conversations`؛ منبع `Kharazmi_Server/routers/messages.py:53` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /messages/conversations/create` | handler `routers.messages.create_conversation`؛ منبع `Kharazmi_Server/routers/messages.py:93` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `GET /messages/conversations/{id}/history` | handler `routers.messages.get_conversation_history`؛ منبع `Kharazmi_Server/routers/messages.py:145` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /messages/conversations/{id}/pin` | handler `routers.messages.toggle_conversation_pin`؛ منبع `Kharazmi_Server/routers/messages.py:323` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `POST /messages/conversations/{id}/send` | handler `routers.messages.send_message`؛ منبع `Kharazmi_Server/routers/messages.py:176` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
| `DELETE /messages/{id}` | handler `routers.messages.delete_own_message`؛ منبع `Kharazmi_Server/routers/messages.py:221` | 0 | inventory/fixture | مسدود: تست رفتاری این route در نوبت router آن نوشته می‌شود | — |
