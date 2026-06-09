import asyncio
import logging
import os

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, LabeledPrice, PreCheckoutQuery,
    BufferedInputFile, InputMediaPhoto,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from openai import OpenAI
from google import genai
from google.genai import types as genai_types

from prompts import BUILD_RU, REVISE_RU, TRANSLATE_EN

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OPENAI_API_KEY     = os.environ["OPENAI_API_KEY"]
GEMINI_API_KEY     = os.environ["GEMINI_API_KEY"]
OPENAI_MODEL       = os.getenv("OPENAI_MODEL", "gpt-5.5")
ALLOWED_USERS      = set(map(int, os.environ["ALLOWED_USERS"].split(",")))
FREE_USERS         = (
    set(map(int, os.environ["FREE_USERS"].split(",")))
    if os.getenv("FREE_USERS", "").strip() else set()
)
STARS_PER_IMAGE    = int(os.getenv("STARS_PER_IMAGE", "5"))

oai          = OpenAI(api_key=OPENAI_API_KEY)
genai_client = genai.Client(api_key=GEMINI_API_KEY)
bot          = Bot(token=TELEGRAM_BOT_TOKEN)
dp           = Dispatcher(storage=MemoryStorage())


# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------

class Gen(StatesGroup):
    idea    = State()
    edit_ru = State()


# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------

class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user is None or user.id not in ALLOWED_USERS:
            if hasattr(event, "answer"):
                await event.answer("⛔ Нет доступа.")
            return
        return await handler(event, data)


dp.message.middleware(AuthMiddleware())
dp.callback_query.middleware(AuthMiddleware())


# ---------------------------------------------------------------------------
# API wrappers
# ---------------------------------------------------------------------------

async def openai_chat(system: str, user: str) -> str:
    def _call():
        resp = oai.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.8,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        return resp.choices[0].message.content.strip()
    return await asyncio.to_thread(_call)


async def nano_banana(prompt: str, aspect_ratio: str) -> bytes | None:
    def _call():
        resp = genai_client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt],
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=genai_types.ImageConfig(aspect_ratio=aspect_ratio),
            ),
        )
        for part in resp.candidates[0].content.parts:
            if part.inline_data is not None:
                return part.inline_data.data
        return None
    return await asyncio.to_thread(_call)


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

AR_OPTIONS    = ["1:1", "16:9", "9:16", "4:3", "3:4", "4:5"]
COUNT_OPTIONS = [1, 2, 3, 4]


def params_keyboard(ar: str, count: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for ratio in AR_OPTIONS:
        b.button(
            text=f"✅ {ratio}" if ratio == ar else ratio,
            callback_data=f"ar|{ratio}",
        )
    for n in COUNT_OPTIONS:
        b.button(
            text=f"✅ {n} шт" if n == count else f"{n} шт",
            callback_data=f"cnt|{n}",
        )
    b.button(text="✏️ Изменить промпт",          callback_data="edit_ru")
    b.button(text="🍌 Отправить в Nano Banana",  callback_data="generate")
    b.adjust(3, 3, 4, 1, 1)
    return b.as_markup()


def ru_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Внести правки",    callback_data="edit_ru")
    b.button(text="✅ Готово, English",  callback_data="to_english")
    b.adjust(2)
    return b.as_markup()


def done_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔁 Переделать", callback_data="regen")
    b.button(text="✅ Готово",     callback_data="done")
    b.adjust(2)
    return b.as_markup()


# ---------------------------------------------------------------------------
# Handlers — start / idea
# ---------------------------------------------------------------------------

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Gen.idea)
    await message.answer("Опишите идею для изображения:")


@dp.message(Gen.idea)
async def handle_idea(message: Message, state: FSMContext):
    status = await message.answer("✍️ Собираю промпт…")
    try:
        ru_prompt = await openai_chat(BUILD_RU, message.text)
    except Exception as e:
        await status.edit_text(f"❌ Ошибка OpenAI: {e}")
        return
    await state.update_data(ru_prompt=ru_prompt, ar="1:1", count=1)
    await status.delete()
    await message.answer(ru_prompt, reply_markup=ru_keyboard())


# ---------------------------------------------------------------------------
# Handlers — edit / translate
# ---------------------------------------------------------------------------

@dp.callback_query(F.data == "edit_ru")
async def cb_edit_ru(call: CallbackQuery, state: FSMContext):
    await state.set_state(Gen.edit_ru)
    await call.message.answer("Что поправить?")
    await call.answer()


@dp.message(Gen.edit_ru)
async def handle_edit(message: Message, state: FSMContext):
    data = await state.get_data()
    status = await message.answer("✍️ Вношу правки…")
    try:
        ru_prompt = await openai_chat(
            REVISE_RU,
            f"Текущий промпт: {data['ru_prompt']}\n\nПравки: {message.text}",
        )
    except Exception as e:
        await status.edit_text(f"❌ Ошибка OpenAI: {e}")
        return
    await state.update_data(ru_prompt=ru_prompt)
    await state.set_state(Gen.idea)
    await status.delete()
    await message.answer(ru_prompt, reply_markup=ru_keyboard())


@dp.callback_query(F.data == "to_english")
async def cb_to_english(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await call.message.edit_reply_markup(reply_markup=None)
    status = await call.message.answer("🌐 Перевожу на английский…")
    try:
        en_prompt = await openai_chat(TRANSLATE_EN, data["ru_prompt"])
    except Exception as e:
        await status.edit_text(f"❌ Ошибка OpenAI: {e}")
        await call.answer()
        return
    await state.update_data(en_prompt=en_prompt)
    await status.delete()
    await call.message.answer(en_prompt, reply_markup=params_keyboard(data["ar"], data["count"]))
    await call.answer()


# ---------------------------------------------------------------------------
# Handlers — params
# ---------------------------------------------------------------------------

@dp.callback_query(F.data.startswith("ar|"))
async def cb_ar(call: CallbackQuery, state: FSMContext):
    ar = call.data.split("|")[1]
    data = await state.get_data()
    await state.update_data(ar=ar)
    await call.message.edit_reply_markup(reply_markup=params_keyboard(ar, data["count"]))
    await call.answer(f"Соотношение: {ar}")


@dp.callback_query(F.data.startswith("cnt|"))
async def cb_cnt(call: CallbackQuery, state: FSMContext):
    count = int(call.data.split("|")[1])
    data = await state.get_data()
    await state.update_data(count=count)
    await call.message.edit_reply_markup(reply_markup=params_keyboard(data["ar"], count))
    await call.answer(f"Количество: {count} шт")


# ---------------------------------------------------------------------------
# Handlers — generate / payment
# ---------------------------------------------------------------------------

@dp.callback_query(F.data.in_({"generate", "regen"}))
async def cb_generate(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id  = call.from_user.id
    ar       = data.get("ar", "1:1")
    count    = data.get("count", 1)
    en_prompt = data.get("en_prompt", "")

    if not en_prompt:
        await call.answer("Сначала переведите промпт на английский.", show_alert=True)
        return

    if user_id in FREE_USERS:
        await call.answer()
        await do_generate(call.message, en_prompt, ar, count)
        return

    await call.message.answer_invoice(
        title="Генерация изображений",
        description=f"{count} изобр. ({ar})",
        payload=f"gen:{user_id}:{ar}:{count}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Генерация", amount=count * STARS_PER_IMAGE)],
    )
    await call.answer()


@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@dp.message(F.successful_payment)
async def paid(message: Message, state: FSMContext):
    payload = message.successful_payment.invoice_payload
    parts = payload.split(":")
    if len(parts) != 4 or parts[0] != "gen":
        return
    _, uid, ar, count_str = parts
    if int(uid) != message.from_user.id:
        return
    data = await state.get_data()
    en_prompt = data.get("en_prompt", "")
    if not en_prompt:
        await message.answer("❌ Промпт не найден. Начните заново через /start")
        return
    await state.update_data(ar=ar, count=int(count_str))
    await do_generate(message, en_prompt, ar, int(count_str))


async def do_generate(message: Message, en_prompt: str, ar: str, count: int):
    status = await message.answer(f"🍌 Генерирую {count} изобр. ({ar})…")

    results = await asyncio.gather(
        *[nano_banana(en_prompt, ar) for _ in range(count)],
        return_exceptions=True,
    )

    try:
        await status.delete()
    except Exception:
        pass

    images = []
    errors = []
    for i, r in enumerate(results):
        if isinstance(r, Exception) or r is None:
            errors.append(i + 1)
            log.error("Ошибка генерации %d: %s", i + 1, r)
        else:
            images.append(r)

    if images:
        if len(images) == 1:
            await message.answer_photo(BufferedInputFile(images[0], filename="image.png"))
        else:
            media = [
                InputMediaPhoto(media=BufferedInputFile(img, filename=f"image_{i}.png"))
                for i, img in enumerate(images)
            ]
            await message.answer_media_group(media)

    result_text = f"Готово: {len(images)} из {count}"
    if errors:
        result_text += f"\nНе удалось: {', '.join(map(str, errors))}"

    await message.answer(result_text, reply_markup=done_keyboard())


# ---------------------------------------------------------------------------
# Handlers — done / fallback
# ---------------------------------------------------------------------------

@dp.callback_query(F.data == "done")
async def cb_done(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(Gen.idea)
    await call.message.answer("Пришлите следующую идею:")
    await call.answer()


@dp.message()
async def fallback(message: Message, state: FSMContext):
    await state.set_state(Gen.idea)
    await handle_idea(message, state)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
