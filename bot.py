import asyncio
import base64
import io
import logging
import os
import textwrap
import time

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
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
from PIL import Image, ImageDraw, ImageFont

from prompts import (
    BUILD_RU, REVISE_RU, TRANSLATE_EN, ANALYZE_STYLE,
    BUILD_TRYON_BG_RU, TRANSLATE_TRYON_BG_EN,
    BUILD_TRYON_VIDEO_RU, TRANSLATE_TRYON_VIDEO_EN,
)

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN    = os.environ["TELEGRAM_BOT_TOKEN"]
OPENAI_API_KEY        = os.environ["OPENAI_API_KEY"]
GOOGLE_CLOUD_PROJECT  = os.environ["GOOGLE_CLOUD_PROJECT"]
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GEMINI_IMAGE_MODEL    = os.getenv("GEMINI_IMAGE_MODEL", "imagen-3.0-generate-002")
VEO_MODEL             = os.getenv("VEO_MODEL", "veo-3.0-fast-generate-001")
OPENAI_MODEL          = os.getenv("OPENAI_MODEL", "gpt-4o")
ALLOWED_USERS         = set(map(int, os.environ["ALLOWED_USERS"].split(",")))
FREE_USERS            = (
    set(map(int, os.environ["FREE_USERS"].split(",")))
    if os.getenv("FREE_USERS", "").strip() else set()
)
STARS_PER_IMAGE       = int(os.getenv("STARS_PER_IMAGE", "5"))
STARS_PER_VIDEO       = int(os.getenv("STARS_PER_VIDEO", "50"))
MODELS_DIR            = os.path.join(os.path.dirname(__file__), "models")

oai          = OpenAI(api_key=OPENAI_API_KEY)
genai_client = genai.Client(vertexai=True, project=GOOGLE_CLOUD_PROJECT, location=GOOGLE_CLOUD_LOCATION)
bot          = Bot(token=TELEGRAM_BOT_TOKEN)
dp           = Dispatcher(storage=MemoryStorage())


# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------

class Gen(StatesGroup):
    idea    = State()
    edit_ru = State()

class VideoGen(StatesGroup):
    photo  = State()
    prompt = State()

class Infographic(StatesGroup):
    sample = State()
    count  = State()
    text   = State()

class TryOn(StatesGroup):
    garment      = State()
    bg_idea      = State()
    bg_edit      = State()
    video_idea   = State()
    video_review = State()
    video_edit   = State()


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
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        return resp.choices[0].message.content.strip()
    return await asyncio.to_thread(_call)


async def openai_vision(prompt: str, image_bytes: bytes) -> str:
    def _call():
        b64 = base64.b64encode(image_bytes).decode()
        resp = oai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            }],
        )
        return resp.choices[0].message.content.strip()
    return await asyncio.to_thread(_call)


async def nano_banana(prompt: str, aspect_ratio: str) -> bytes | None:
    def _call():
        resp = genai_client.models.generate_images(
            model=GEMINI_IMAGE_MODEL,
            prompt=prompt,
            config=genai_types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect_ratio,
            ),
        )
        if resp.generated_images:
            return resp.generated_images[0].image.image_bytes
        return None
    return await asyncio.to_thread(_call)


async def veo_generate(prompt: str, aspect_ratio: str, image_bytes: bytes | None = None) -> bytes | None:
    log.info("veo prompt: %s", prompt)

    def _call():
        kwargs = {}
        if image_bytes is not None:
            kwargs["image"] = genai_types.Image(image_bytes=image_bytes, mime_type="image/jpeg")
        operation = genai_client.models.generate_videos(
            model=VEO_MODEL,
            prompt=prompt,
            config=genai_types.GenerateVideosConfig(
                aspect_ratio=aspect_ratio,
                number_of_videos=1,
            ),
            **kwargs,
        )
        while not operation.done:
            time.sleep(10)
            operation = genai_client.operations.get(operation)
        if operation.error:
            log.error("veo operation error: %s", operation.error)
            return None
        if operation.response and operation.result.generated_videos:
            return operation.result.generated_videos[0].video.video_bytes
        log.error(
            "veo no video generated; result=%s rai_filtered_reasons=%s",
            operation.result,
            getattr(operation.result, "rai_media_filtered_reasons", None),
        )
        return None
    return await asyncio.to_thread(_call)


def list_models() -> list[str]:
    if not os.path.isdir(MODELS_DIR):
        return []
    return sorted(
        f for f in os.listdir(MODELS_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    )


async def openai_image_edit(prompt: str, images: list[bytes]) -> bytes:
    def _call():
        files = []
        for data in images:
            buf = io.BytesIO(data)
            buf.name = "image.jpg"
            files.append(buf)
        resp = oai.images.edit(
            model="gpt-image-2",
            image=files,
            prompt=prompt,
            size="1024x1536",
            quality="medium",
        )
        return base64.b64decode(resp.data[0].b64_json)
    return await asyncio.to_thread(_call)


def overlay_text(bg_bytes: bytes, text: str) -> bytes:
    img = Image.open(io.BytesIO(bg_bytes)).convert("RGB")
    w, h = img.size

    font_size = max(28, h // 10)
    font = None
    for path in [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]:
        try:
            font = ImageFont.truetype(path, font_size)
            break
        except OSError:
            pass
    if font is None:
        font = ImageFont.load_default()

    max_width_px = int(w * 0.8)
    avg_char_w = font_size * 0.55
    chars_per_line = max(10, int(max_width_px / avg_char_w))
    wrapped = textwrap.fill(text, width=chars_per_line)

    draw_tmp = ImageDraw.Draw(img)
    bbox = draw_tmp.multiline_textbbox((0, 0), wrapped, font=font, align="center")
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (w - tw) / 2
    y = (h - th) / 2

    pad = int(h * 0.03)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle(
        [x - pad, y - pad, x + tw + pad, y + th + pad],
        fill=(0, 0, 0, 150),
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    draw.multiline_text((x + 2, y + 2), wrapped, font=font, fill=(0, 0, 0), align="center")
    draw.multiline_text((x, y), wrapped, font=font, fill=(255, 255, 255), align="center")

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

AR_OPTIONS               = ["1:1", "16:9", "9:16", "4:3", "3:4", "4:5"]
COUNT_OPTIONS            = [1, 2, 3, 4]
INFOGRAPHIC_COUNT_OPTIONS = [3, 5, 7, 10]
VIDEO_AR_OPTIONS         = ["16:9", "9:16"]


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
    b.button(text="✏️ Изменить промпт",         callback_data="edit_ru")
    b.button(text="🍌 Отправить в Nano Banana", callback_data="generate")
    b.adjust(3, 3, 4, 1, 1)
    return b.as_markup()


def ru_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Внести правки",   callback_data="edit_ru")
    b.button(text="✅ Готово, English", callback_data="to_english")
    b.adjust(2)
    return b.as_markup()


def done_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔁 Переделать", callback_data="regen")
    b.button(text="✅ Готово",     callback_data="done")
    b.adjust(2)
    return b.as_markup()


def video_params_keyboard(ar: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for ratio in VIDEO_AR_OPTIONS:
        b.button(
            text=f"✅ {ratio}" if ratio == ar else ratio,
            callback_data=f"var|{ratio}",
        )
    b.button(text="✏️ Вставить другой промпт", callback_data="video_edit_prompt")
    b.button(text="🎬 Сгенерировать видео",     callback_data="video_generate")
    b.adjust(2, 1, 1)
    return b.as_markup()


def video_done_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔁 Переделать", callback_data="video_regen")
    b.button(text="✅ Готово",     callback_data="done")
    b.adjust(2)
    return b.as_markup()


def tryon_bg_ru_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Внести правки",        callback_data="tryon_bg_edit_ru")
    b.button(text="✅ Готово, сгенерировать", callback_data="tryon_bg_generate")
    b.adjust(2)
    return b.as_markup()


def tryon_bg_done_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔁 Переделать фон",  callback_data="tryon_bg_regen")
    b.button(text="✅ Подходит, дальше", callback_data="tryon_bg_confirm")
    b.adjust(2)
    return b.as_markup()


def tryon_video_ru_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Внести правки",   callback_data="tryon_video_edit_ru")
    b.button(text="✅ Готово, English", callback_data="tryon_video_to_english")
    b.adjust(2)
    return b.as_markup()


def tryon_video_done_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Готово", callback_data="done")
    b.adjust(1)
    return b.as_markup()


def start_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🖼 Генерация изображения", callback_data="mode_image")
    b.button(text="🎬 Оживить фото",          callback_data="mode_video")
    b.button(text="📊 Инфографика",           callback_data="mode_infographic")
    b.button(text="👗 Примерка одежды",       callback_data="mode_tryon")
    b.adjust(1)
    return b.as_markup()


def infographic_count_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for n in INFOGRAPHIC_COUNT_OPTIONS:
        b.button(text=f"{n} слайдов", callback_data=f"inf_cnt|{n}")
    b.adjust(4)
    return b.as_markup()


# ---------------------------------------------------------------------------
# Handlers — start / mode
# ---------------------------------------------------------------------------

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите режим:", reply_markup=start_keyboard())


@dp.callback_query(F.data == "mode_image")
async def cb_mode_image(call: CallbackQuery, state: FSMContext):
    await state.set_state(Gen.idea)
    await call.message.answer("Опишите идею для изображения:")
    await call.answer()


@dp.callback_query(F.data == "mode_video")
async def cb_mode_video(call: CallbackQuery, state: FSMContext):
    await state.set_state(VideoGen.photo)
    await call.message.answer(
        "Пришлите фото для анимации (например, готовое изображение из «Примерка одежды»):"
    )
    await call.answer()


@dp.callback_query(F.data == "mode_infographic")
async def cb_mode_infographic(call: CallbackQuery, state: FSMContext):
    await state.set_state(Infographic.sample)
    await call.message.answer("Пришлите фото-образец стиля для инфографики:")
    await call.answer()


@dp.message(Command("infographic"))
async def cmd_infographic(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Infographic.sample)
    await message.answer("Пришлите фото-образец стиля для инфографики:")


# ---------------------------------------------------------------------------
# Handlers — image generation
# ---------------------------------------------------------------------------

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


@dp.callback_query(F.data.in_({"generate", "regen"}))
async def cb_generate(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id   = call.from_user.id
    ar        = data.get("ar", "1:1")
    count     = data.get("count", 1)
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

    if parts[0] == "gen" and len(parts) == 4:
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
        return

    if parts[0] == "vid" and len(parts) == 3:
        _, uid, ar = parts
        if int(uid) != message.from_user.id:
            return
        data = await state.get_data()
        en_prompt = data.get("video_en_prompt", "")
        image_bytes = data.get("video_image")
        if not en_prompt:
            await message.answer("❌ Промпт не найден. Начните заново через /start")
            return
        await state.update_data(var=ar)
        await do_generate_video(message, en_prompt, ar, image_bytes)
        return


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
# Handlers — video generation
# ---------------------------------------------------------------------------

@dp.message(VideoGen.photo, F.photo)
async def handle_video_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    buf = await bot.download_file(file.file_path)
    buf.seek(0)
    image_bytes = buf.read()

    await state.update_data(video_image=image_bytes, var="9:16")
    await state.set_state(VideoGen.prompt)
    await message.answer("Вставьте готовый английский промпт для видео (из «Примерка одежды»):")


@dp.message(VideoGen.prompt)
async def handle_video_prompt(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("video_image") is None:
        await state.set_state(VideoGen.photo)
        await message.answer("Сначала пришлите фото для анимации.")
        return

    await state.update_data(video_en_prompt=message.text)
    await message.answer(message.text, reply_markup=video_params_keyboard(data.get("var", "9:16")))


@dp.callback_query(F.data == "video_edit_prompt")
async def cb_video_edit_prompt(call: CallbackQuery, state: FSMContext):
    await state.set_state(VideoGen.prompt)
    await call.message.answer("Вставьте новый промпт для видео:")
    await call.answer()


@dp.callback_query(F.data.startswith("var|"))
async def cb_video_ar(call: CallbackQuery, state: FSMContext):
    ar = call.data.split("|")[1]
    await state.update_data(var=ar)
    await call.message.edit_reply_markup(reply_markup=video_params_keyboard(ar))
    await call.answer(f"Соотношение: {ar}")


@dp.callback_query(F.data.in_({"video_generate", "video_regen"}))
async def cb_video_generate(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id     = call.from_user.id
    ar          = data.get("var", "9:16")
    en_prompt   = data.get("video_en_prompt", "")
    image_bytes = data.get("video_image")

    if not en_prompt:
        await call.answer("Сначала переведите промпт на английский.", show_alert=True)
        return

    if user_id in FREE_USERS:
        await call.answer()
        await do_generate_video(call.message, en_prompt, ar, image_bytes)
        return

    await call.message.answer_invoice(
        title="Генерация видео",
        description=f"Видео ({ar})",
        payload=f"vid:{user_id}:{ar}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Генерация видео", amount=STARS_PER_VIDEO)],
    )
    await call.answer()


async def do_generate_video(message: Message, en_prompt: str, ar: str, image_bytes: bytes | None = None):
    status = await message.answer(f"🎬 Генерирую видео ({ar})… это может занять несколько минут")

    try:
        video_bytes = await veo_generate(en_prompt, ar, image_bytes)
    except Exception as e:
        await status.edit_text(f"❌ Ошибка генерации видео: {e}")
        log.error("video generation error: %s", e)
        return

    try:
        await status.delete()
    except Exception:
        pass

    if video_bytes:
        await message.answer_video(BufferedInputFile(video_bytes, filename="video.mp4"))
        await message.answer("Готово!", reply_markup=video_done_keyboard())
    else:
        await message.answer("❌ Не удалось сгенерировать видео.", reply_markup=video_done_keyboard())


# ---------------------------------------------------------------------------
# Handlers — infographic
# ---------------------------------------------------------------------------

@dp.message(Infographic.sample, F.photo)
async def handle_infographic_sample(message: Message, state: FSMContext):
    status = await message.answer("🔍 Анализирую стиль…")
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    buf = await bot.download_file(file.file_path)
    buf.seek(0)
    image_bytes = buf.read()

    try:
        style_prompt = await openai_vision(ANALYZE_STYLE, image_bytes)
    except Exception as e:
        await status.edit_text(f"❌ Ошибка анализа: {e}")
        return

    await state.update_data(style_prompt=style_prompt)
    await status.delete()
    await message.answer(
        f"✅ Стиль определён:\n\n<i>{style_prompt}</i>\n\nСколько слайдов?",
        parse_mode="HTML",
        reply_markup=infographic_count_keyboard(),
    )
    await state.set_state(Infographic.count)


@dp.callback_query(Infographic.count, F.data.startswith("inf_cnt|"))
async def cb_infographic_count(call: CallbackQuery, state: FSMContext):
    count = int(call.data.split("|")[1])
    await state.update_data(slide_count=count, texts=[])
    await state.set_state(Infographic.text)
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(f"Введите текст для слайда 1 из {count}:")
    await call.answer()


@dp.message(Infographic.text)
async def handle_infographic_text(message: Message, state: FSMContext):
    data = await state.get_data()
    texts: list = data.get("texts", [])
    texts.append(message.text)
    slide_count: int = data["slide_count"]
    await state.update_data(texts=texts)

    if len(texts) < slide_count:
        await message.answer(f"Введите текст для слайда {len(texts) + 1} из {slide_count}:")
        return

    style_prompt = data["style_prompt"]
    status = await message.answer(f"🎨 Генерирую {slide_count} слайдов…")

    bg_results = await asyncio.gather(
        *[nano_banana(style_prompt, "1:1") for _ in range(slide_count)],
        return_exceptions=True,
    )

    slides = []
    errors = []
    for i, (bg, text) in enumerate(zip(bg_results, texts)):
        if isinstance(bg, Exception) or bg is None:
            errors.append(i + 1)
            log.error("Ошибка фона слайда %d: %s", i + 1, bg)
            continue
        try:
            slide = await asyncio.to_thread(overlay_text, bg, text)
            slides.append(slide)
        except Exception as e:
            errors.append(i + 1)
            log.error("Ошибка текста слайда %d: %s", i + 1, e)

    try:
        await status.delete()
    except Exception:
        pass

    if slides:
        if len(slides) == 1:
            await message.answer_photo(BufferedInputFile(slides[0], filename="slide_1.png"))
        else:
            media = [
                InputMediaPhoto(media=BufferedInputFile(s, filename=f"slide_{i + 1}.png"))
                for i, s in enumerate(slides)
            ]
            await message.answer_media_group(media)

    result_text = f"Готово: {len(slides)} из {slide_count}"
    if errors:
        result_text += f"\nНе удалось: {', '.join(map(str, errors))}"

    await state.clear()
    await message.answer(result_text + "\n\n/start — начать заново")


# ---------------------------------------------------------------------------
# Handlers — try-on
# ---------------------------------------------------------------------------

@dp.callback_query(F.data == "mode_tryon")
async def cb_mode_tryon(call: CallbackQuery, state: FSMContext):
    if not list_models():
        await call.message.answer("⚠️ Нет фото модели. Добавьте изображения в папку /models/")
        await call.answer()
        return
    await state.set_state(TryOn.garment)
    await call.message.answer("Пришлите фото одежды (свитер, кардиган и т.д.):")
    await call.answer()


@dp.message(TryOn.garment, F.photo)
async def handle_tryon_garment(message: Message, state: FSMContext):
    status = await message.answer("👗 Генерирую изображение…")

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    buf = await bot.download_file(file.file_path)
    buf.seek(0)
    garment_bytes = buf.read()

    models = list_models()
    source = "front.jpg" if "front.jpg" in models else models[0]
    with open(os.path.join(MODELS_DIR, source), "rb") as f:
        model_bytes = f.read()

    base_prompt = (
        "Generate a photorealistic, full-length, full-body photo of the woman from the first image, "
        "wearing exactly the garment shown in the second image. Preserve her face, hairstyle, body "
        "proportions and skin tone exactly as in the first image. Match the garment's color, shade, "
        "fabric, texture, pattern and silhouette exactly as shown in the second image — do not alter, "
        "reinterpret or recolor it. Replace her pants with blue denim jeans and her shoes with white "
        "sneakers. Place her standing in a simple neutral studio background, relaxed "
        "pose, entire body visible from head to feet including shoes. {angle}"
    )

    angles = [
        "Camera angle: shot from a 45-degree angle relative to the woman.",
        "Camera angle: side profile view, shot from the side of the woman.",
    ]

    try:
        results = await asyncio.gather(
            *(
                openai_image_edit(base_prompt.format(angle=angle), [model_bytes, garment_bytes])
                for angle in angles
            )
        )
    except Exception as e:
        await status.edit_text(f"❌ Ошибка генерации: {e}")
        log.error("tryon generation error: %s", e)
        await state.clear()
        return

    await status.delete()
    media = [
        InputMediaPhoto(
            media=BufferedInputFile(image_bytes, filename=f"tryon_{i}.png"),
            caption="✅ Готово!" if i == 0 else None,
        )
        for i, image_bytes in enumerate(results)
    ]
    await message.answer_media_group(media)

    await state.update_data(tryon_base_image=results[0])
    await state.set_state(TryOn.bg_idea)
    await message.answer(
        "Опишите желаемый фон/локацию вокруг девушки (например: на улице вечером в неоновом городе, "
        "в кафе у окна, на пляже на закате):"
    )


@dp.message(TryOn.bg_idea)
async def handle_tryon_bg_idea(message: Message, state: FSMContext):
    status = await message.answer("✍️ Собираю промпт фона…")
    try:
        ru_prompt = await openai_chat(BUILD_TRYON_BG_RU, message.text)
    except Exception as e:
        await status.edit_text(f"❌ Ошибка OpenAI: {e}")
        return
    await state.update_data(tryon_bg_ru_prompt=ru_prompt)
    await status.delete()
    await message.answer(ru_prompt, reply_markup=tryon_bg_ru_keyboard())


@dp.callback_query(F.data == "tryon_bg_edit_ru")
async def cb_tryon_bg_edit_ru(call: CallbackQuery, state: FSMContext):
    await state.set_state(TryOn.bg_edit)
    await call.message.answer("Что поправить?")
    await call.answer()


@dp.message(TryOn.bg_edit)
async def handle_tryon_bg_edit(message: Message, state: FSMContext):
    data = await state.get_data()
    status = await message.answer("✍️ Вношу правки…")
    try:
        ru_prompt = await openai_chat(
            REVISE_RU,
            f"Текущий промпт: {data['tryon_bg_ru_prompt']}\n\nПравки: {message.text}",
        )
    except Exception as e:
        await status.edit_text(f"❌ Ошибка OpenAI: {e}")
        return
    await state.update_data(tryon_bg_ru_prompt=ru_prompt)
    await state.set_state(TryOn.bg_idea)
    await status.delete()
    await message.answer(ru_prompt, reply_markup=tryon_bg_ru_keyboard())


@dp.callback_query(F.data.in_({"tryon_bg_generate", "tryon_bg_regen"}))
async def cb_tryon_bg_generate(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await call.answer()
    status = await call.message.answer("🎨 Генерирую фон…")
    try:
        en_prompt = await openai_chat(TRANSLATE_TRYON_BG_EN, data["tryon_bg_ru_prompt"])
        composite = await openai_image_edit(en_prompt, [data["tryon_base_image"]])
    except Exception as e:
        await status.edit_text(f"❌ Ошибка генерации: {e}")
        log.error("tryon bg generation error: %s", e)
        return

    await state.update_data(tryon_composite=composite)
    await status.delete()
    await call.message.answer_photo(
        BufferedInputFile(composite, filename="tryon_bg.png"),
        reply_markup=tryon_bg_done_keyboard(),
    )


@dp.callback_query(F.data == "tryon_bg_confirm")
async def cb_tryon_bg_confirm(call: CallbackQuery, state: FSMContext):
    await state.set_state(TryOn.video_idea)
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(
        "Опишите движения камеры (наезд, отъезд, панорама, глубина резкости, яркость, резкость и т.д.) "
        "и физику движений девушки (обычная походка, поворот, ветер, вода и т.п.):"
    )
    await call.answer()


@dp.message(TryOn.video_idea)
async def handle_tryon_video_idea(message: Message, state: FSMContext):
    data = await state.get_data()
    composite = data.get("tryon_composite")
    if composite is None:
        await state.clear()
        await message.answer("Сессия сброшена. Начните заново через /start")
        return

    status = await message.answer("✍️ Собираю промпт…")
    vision_prompt = BUILD_TRYON_VIDEO_RU + f"\n\nОписание желаемой съёмки от пользователя: {message.text}"
    try:
        ru_prompt = await openai_vision(vision_prompt, composite)
    except Exception as e:
        await status.edit_text(f"❌ Ошибка OpenAI: {e}")
        return

    await state.update_data(tryon_video_ru_prompt=ru_prompt)
    await state.set_state(TryOn.video_review)
    await status.delete()
    await message.answer(ru_prompt, reply_markup=tryon_video_ru_keyboard())


@dp.callback_query(F.data == "tryon_video_edit_ru")
async def cb_tryon_video_edit_ru(call: CallbackQuery, state: FSMContext):
    await state.set_state(TryOn.video_edit)
    await call.message.answer("Что поправить?")
    await call.answer()


@dp.message(TryOn.video_edit)
async def handle_tryon_video_edit(message: Message, state: FSMContext):
    data = await state.get_data()
    status = await message.answer("✍️ Вношу правки…")
    try:
        ru_prompt = await openai_chat(
            REVISE_RU,
            f"Текущий промпт: {data['tryon_video_ru_prompt']}\n\nПравки: {message.text}",
        )
    except Exception as e:
        await status.edit_text(f"❌ Ошибка OpenAI: {e}")
        return
    await state.update_data(tryon_video_ru_prompt=ru_prompt)
    await state.set_state(TryOn.video_review)
    await status.delete()
    await message.answer(ru_prompt, reply_markup=tryon_video_ru_keyboard())


@dp.callback_query(F.data == "tryon_video_to_english")
async def cb_tryon_video_to_english(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await call.message.edit_reply_markup(reply_markup=None)
    status = await call.message.answer("🌐 Перевожу на английский…")
    try:
        en_prompt = await openai_chat(TRANSLATE_TRYON_VIDEO_EN, data["tryon_video_ru_prompt"])
    except Exception as e:
        await status.edit_text(f"❌ Ошибка OpenAI: {e}")
        await call.answer()
        return
    await status.delete()
    await call.message.answer_photo(
        BufferedInputFile(data["tryon_composite"], filename="tryon_scene.png"),
    )
    await call.message.answer(
        f"<code>{en_prompt}</code>\n\n"
        "Скопируйте промпт и фото выше и вставьте их в «🎬 Оживить фото».",
        parse_mode="HTML",
        reply_markup=tryon_video_done_keyboard(),
    )
    await state.clear()
    await call.answer()


# ---------------------------------------------------------------------------
# Handlers — done / fallback
# ---------------------------------------------------------------------------

@dp.callback_query(F.data == "done")
async def cb_done(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("Выберите режим:", reply_markup=start_keyboard())
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
