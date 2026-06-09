# ТЗ: Telegram-бот для генерации изображений (OpenAI + Nano Banana)

## Цель
Собрать Telegram-бота, который превращает идею пользователя в картинку через двухступенчатый
конвейер: сначала OpenAI составляет и дорабатывает текстовый промпт (на русском, с циклом правок),
затем переводит его на английский, и финальный промпт уходит в Nano Banana (Gemini 2.5 Flash Image)
для генерации. Перед генерацией пользователь выбирает параметры (соотношение сторон, количество).

Окружение разработки: VS Code на собственном VPS. Python 3.11+.

---

## Стек
- **aiogram 3.x** — Telegram-бот, асинхронный, с FSM и inline-клавиатурами.
- **openai** (официальный SDK) — генерация и доработка промптов.
- **google-genai** (`from google import genai`) — генерация изображений через Nano Banana.

```
pip install aiogram openai google-genai python-dotenv
```

Синхронные вызовы OpenAI и google-genai оборачивать в `asyncio.to_thread`, чтобы не блокировать
event loop aiogram.

---

## Структура проекта
```
imagebot/
├── bot.py            # точка входа + хендлеры + AuthMiddleware
├── prompts.py        # системные промпты для OpenAI (вынести константами)
├── .env              # ключи, ALLOWED_USERS, FREE_USERS, STARS_PER_IMAGE (в .gitignore!)
├── .env.example      # шаблон без значений
├── requirements.txt
└── README.md
```
Можно начать с одного `bot.py`, но разнести промпты в `prompts.py` — желательно.

`.env.example`:
```
TELEGRAM_BOT_TOKEN=
OPENAI_API_KEY=
GEMINI_API_KEY=
OPENAI_MODEL=gpt-4o
ALLOWED_USERS=
FREE_USERS=
STARS_PER_IMAGE=5
```

---

## Переменные окружения (.env)
```
TELEGRAM_BOT_TOKEN=
OPENAI_API_KEY=
GEMINI_API_KEY=
OPENAI_MODEL=gpt-4o
ALLOWED_USERS=123456789,987654321
STARS_PER_IMAGE=5
FREE_USERS=123456789
```
Читать через `os.environ` (обязательные) и `os.getenv` (с дефолтом для `OPENAI_MODEL`).
Ключи нигде не хардкодить. `.env` загружать через `python-dotenv` или экспортом в systemd.

`ALLOWED_USERS` — список Telegram user_id через запятую без пробелов. Только эти пользователи
могут работать с ботом. Как узнать свой ID: написать боту `@userinfobot` в Telegram.

`FREE_USERS` — подмножество `ALLOWED_USERS`, которые платить не должны (владелец бота и др.).

`STARS_PER_IMAGE` — цена одной генерации в Telegram Stars (по умолчанию 5).

---

## Оплата (Tribute / Telegram Stars)

Бот принимает оплату через **Telegram Stars** — встроенную валюту Telegram.
Платёжный провайдер: **[Tribute](https://tribute.tg)** — поддерживает Stars и банковские карты (РФ),
не требует регистрации юрлица.

### Как подключить Tribute
1. Зайти на tribute.tg, создать аккаунт.
2. Добавить бота в Tribute, выбрать «Разовые платежи» (не подписка).
3. Tribute выдаст параметры, которые настраиваются через BotFather:
   `/mybots → Payments → Connect Tribute`.
4. После подключения бот получает `provider_token` от BotFather — внести в `.env`.

> **Важно:** Tribute сам выдаёт `provider_token`. Нативные Stars-инвойсы (`currency="XTR"`)
> не требуют `provider_token` — они работают напрямую через aiogram без Tribute.
> Tribute нужен только если хочется принимать карты/СБП помимо Stars.

### Модель: оплата за каждую картинку

Пользователи из `FREE_USERS` генерируют бесплатно (владелец и доверенные лица).
Остальные платят **`STARS_PER_IMAGE` Stars × количество картинок** перед генерацией.

### Флоу оплаты

**callback `generate` / `regen`** (изменить шаг 7):
1. Если `user_id` в `FREE_USERS` → сразу генерировать.
2. Иначе отправить инвойс Stars:
```python
from aiogram.types import LabeledPrice

await bot.send_invoice(
    chat_id=user_id,
    title="Генерация изображений",
    description=f"{count} изобр. ({ar}), промпт: {en_prompt[:80]}…",
    payload=f"gen:{user_id}:{ar}:{count}",   # проверяем в successful_payment
    currency="XTR",                           # XTR = Telegram Stars
    prices=[LabeledPrice(label="Генерация", amount=count * STARS_PER_IMAGE)],
)
```
3. Хендлер `pre_checkout_query` — всегда подтверждать (`await query.answer(ok=True)`).
4. Хендлер `successful_payment` — разобрать `payload`, запустить генерацию.

```python
@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def paid(message: Message, state: FSMContext):
    payload = message.successful_payment.invoice_payload
    # payload = "gen:{user_id}:{ar}:{count}"
    _, uid, ar, count = payload.split(":")
    if int(uid) != message.from_user.id:
        return  # чужой payload — игнорировать
    # обновить state и запустить генерацию
    await state.update_data(ar=ar, count=int(count))
    await do_generate(message, state)
```

`do_generate` — вынести логику генерации в отдельную async-функцию, вызываемую
как из `successful_payment`, так и из `generate` (для `FREE_USERS`).

### Stars vs карты
| | Stars | Карты через Tribute |
|---|---|---|
| Настройка | Нулевая | Регистрация в Tribute |
| Комиссия | 30% Telegram | ~5% Tribute + эквайринг |
| Вывод | Через монетизацию | На банковский счёт |
| Пользователь | Покупает Stars в Telegram | Платит картой в чате |

Для первой версии достаточно чистых Stars (`currency="XTR"`, без `provider_token`).
Tribute подключать позже, когда нужна карточная оплата.

---

## Авторизация

Бот принимает команды и сообщения **только** от пользователей из `ALLOWED_USERS`.

Реализация — `BaseMiddleware` aiogram, проверяет `event.from_user.id`:

```python
ALLOWED = set(map(int, os.environ["ALLOWED_USERS"].split(",")))

class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user is None or user.id not in ALLOWED:
            # для Message — ответить; для CallbackQuery — тихо игнорировать
            if hasattr(event, "answer"):
                await event.answer("⛔ Нет доступа.")
            return
        return await handler(event, data)
```

Регистрировать на `dp.message.middleware(AuthMiddleware())` и
`dp.callback_query.middleware(AuthMiddleware())`.

---

## Пользовательский поток (FSM)

### Состояния
- `idea` — ждём текстовое описание идеи.
- `edit_ru` — ждём текст правок к русскому промпту.

(Остальные шаги управляются inline-кнопками через callback, отдельные состояния не нужны.)

### Переходы

**1. `/start`**
→ очистить state, установить `idea`, попросить описать идею.

**2. Пользователь прислал идею (state `idea`)**
→ показать «✍️ Собираю промпт…»
→ OpenAI: системный промпт `BUILD_RU`, user = текст идеи → получить RU-промпт
→ сохранить `ru_prompt`, дефолты `ar="1:1"`, `count=1`
→ вывести RU-промпт + клавиатура:
   - `✏️ Внести правки` → callback `edit_ru`
   - `✅ Готово, English` → callback `to_english`

**3. callback `edit_ru`**
→ перевести в state `edit_ru`, спросить «Что поправить?»

**4. Пользователь прислал правки (state `edit_ru`)**
→ OpenAI: системный промпт `REVISE_RU`, user = «Текущий промпт: …\n\nПравки: …» → новый RU-промпт
→ обновить `ru_prompt`, выйти из состояния
→ снова вывести RU-промпт с той же клавиатурой (шаг 2). Это цикл — правок может быть много.

**5. callback `to_english`**
→ «🌐 Перевожу на английский…»
→ OpenAI: системный промпт `TRANSLATE_EN`, user = `ru_prompt` → EN-промпт
→ сохранить `en_prompt`
→ вывести EN-промпт + клавиатура параметров (см. ниже).

**6. Экран параметров**
Клавиатура:
- Ряды кнопок соотношения сторон: `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `4:5` (по 3 в ряд).
  Выбранное помечается `✅`.
- Ряд количества: `1 шт`, `2 шт`, `3 шт`, `4 шт`. Выбранное помечается `✅`.
- `✏️ Изменить промпт` → callback `edit_ru` (вернуться к правкам).
- `🍌 Отправить в Nano Banana` → callback `generate`.

callback `ar|<value>` и `cnt|<n>`: обновляют `ar`/`count` в state и перерисовывают клавиатуру
**на месте** через `edit_reply_markup` (не плодить новые сообщения), плюс короткий `call.answer(...)`.

**7. callback `generate` / `regen`**
→ «🍌 Генерирую N изобр. (AR)…»
→ N параллельных вызовов Nano Banana (см. раздел «Nano Banana»), `asyncio.gather(..., return_exceptions=True)`
→ удалить статус-сообщение
→ если 1 картинка — отправить фото; если >1 — медиагруппой
→ отдельным сообщением вывести «Готово: K из N» + клавиатура:
   - `🔁 Переделать` → callback `regen` (та же логика, что `generate`)
   - `✅ Готово` → callback `done`
→ при частичных ошибках — дописать список неудавшихся вызовов.

**8. callback `done`**
→ очистить state, установить `idea`, предложить прислать следующую идею.

**Фолбэк:** любое текстовое сообщение вне состояния (не команда) трактовать как новую идею.

---

## Данные в FSM-контексте
`ru_prompt`, `en_prompt`, `ar` (строка соотношения), `count` (int).

---

## Интеграция: OpenAI

Обёртка:
```python
async def openai_chat(system: str, user: str) -> str:
    def _call():
        resp = oai.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.8,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content.strip()
    return await asyncio.to_thread(_call)
```

Три системных промпта (в `prompts.py`):

- **BUILD_RU** — «эксперт по промптам для image-моделей; по идее пользователя составь подробный
  структурированный промпт НА РУССКОМ: объект, сцена/окружение, композиция и ракурс, освещение,
  цвет, стиль, детализация; только текст промпта, без вступлений».
- **REVISE_RU** — «дан текущий промпт и правки; внеси правки, сохранив остальное и структуру;
  выведи только обновлённый промпт на русском».
- **TRANSLATE_EN** — «translate and adapt the Russian prompt into a professional English
  image-generation prompt for Nano Banana/Gemini; preserve all details; output only the English prompt».

---

## Интеграция: Nano Banana (Gemini 2.5 Flash Image)

**Критично:** модель `gemini-2.5-flash-image` возвращает **одно изображение за вызов**.
Параметра «количество» у неё **нет** — управляется только `aspect_ratio`.
Поэтому «N изображений» = N независимых вызовов (через `asyncio.gather`).

Поддерживаемые соотношения сторон: `1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9`.
Кнопками показываем подмножество (см. шаг 6), но в коде допускать все из списка.

Обёртка (один вызов → байты изображения):
```python
from google import genai
from google.genai import types

genai_client = genai.Client(api_key=GEMINI_API_KEY)

async def nano_banana(prompt: str, aspect_ratio: str) -> bytes | None:
    def _call():
        resp = genai_client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
            ),
        )
        for part in resp.candidates[0].content.parts:
            if part.inline_data is not None:
                return part.inline_data.data
        return None
    return await asyncio.to_thread(_call)
```

Байты отправлять в Telegram через `BufferedInputFile(data, filename="image.png")`,
медиагруппу — через `InputMediaPhoto`.

---

## Обработка ошибок
- Каждый внешний вызов (OpenAI, Nano Banana) — в `try/except`; при ошибке заменить статус-сообщение
  текстом ошибки, не роняя бота.
- В `generate` использовать `return_exceptions=True` и показать, сколько из N удалось.
- Логирование через `logging` (INFO).

---

## Запуск и деплой на VPS

**Локально/в venv:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

**systemd unit** (`/etc/systemd/system/imagebot.service`):
```ini
[Unit]
Description=Image generation Telegram bot
After=network.target

[Service]
WorkingDirectory=/path/to/imagebot
EnvironmentFile=/path/to/imagebot/.env
ExecStart=/path/to/imagebot/.venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now imagebot
journalctl -u imagebot -f
```

Бот работает на long polling — открытый порт/домен не нужен.

---

## Критерии готовности (чек-лист)
- [ ] Пользователь не из `ALLOWED_USERS` получает «⛔ Нет доступа» и дальше не проходит.
- [ ] Пользователь из `FREE_USERS` генерирует без оплаты.
- [ ] Остальные `ALLOWED_USERS` получают Stars-инвойс перед генерацией (сумма = кол-во × `STARS_PER_IMAGE`).
- [ ] После оплаты генерация запускается автоматически.
- [ ] `/start` запускает поток, бот просит идею.
- [ ] По идее приходит RU-промпт с кнопками «Внести правки» / «Готово, English».
- [ ] Правки работают циклично, промпт обновляется.
- [ ] «Готово, English» выдаёт EN-промпт.
- [ ] Кнопки соотношения сторон и количества переключаются с пометкой `✅`, без новых сообщений.
- [ ] «Отправить в Nano Banana» генерирует выбранное количество с выбранным AR.
- [ ] Несколько картинок приходят медиагруппой; одна — отдельным фото.
- [ ] После генерации есть «Переделать» / «Готово».
- [ ] Ошибки внешних API не роняют бота, показываются пользователю.
- [ ] Ключи только в `.env`, `.env` в `.gitignore`.

---

## Вне первой версии (опциональные расширения, не делать сейчас)
- Image-to-image (передавать в `contents=[prompt, image]` загруженное пользователем фото для редактирования).
- История промптов / сохранение в БД.
- Полный список из 10 соотношений (включая 21:9, 5:4) отдельным меню.
- Очередь/ограничение конкурентных генераций на пользователя.
