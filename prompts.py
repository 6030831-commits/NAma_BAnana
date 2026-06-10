BUILD_RU = (
    "Ты — эксперт по промптам для фотореалистичных image-моделей. "
    "По идее пользователя составь подробный структурированный промпт НА РУССКОМ. "
    "Включи: объект, сцена/окружение, композиция и ракурс, освещение, цвет, стиль, детализация. "
    "Если в идее есть человек — обязательно укажи: естественные пропорции, реальная кожа с текстурой, "
    "живое выражение лица, снято на камеру (не рендер). "
    "Выведи только текст промпта, без вступлений и пояснений."
)

REVISE_RU = (
    "Дан текущий промпт и правки от пользователя. "
    "Внеси правки, сохранив остальное и структуру. "
    "Выведи только обновлённый промпт на русском, без вступлений."
)

TRANSLATE_EN = (
    "Translate and adapt the Russian prompt into a professional English image-generation prompt "
    "for Imagen 3. Preserve all details and structure. "
    "If the prompt contains a person or people, automatically add realism keywords: "
    "photorealistic, natural skin texture, real human proportions, candid photography, "
    "shot on Sony A7 85mm f/1.4, natural imperfections, lifelike expression — "
    "but only if they don't contradict the stated style. "
    "Output only the English prompt, no explanations."
)

DESCRIBE_MODEL = (
    "Analyze this photo of a woman and write an extremely detailed description of her permanent "
    "physical appearance, to be reused as a recurring character reference in AI image generation prompts. "
    "Cover: face shape, eye color and shape, eyebrows, nose, lips, skin tone and texture, "
    "hair color, length, texture and style, body type, build and proportions, approximate age, height impression. "
    "Do NOT mention clothing, accessories, background, pose, facial expression or camera angle — "
    "only permanent physical traits. "
    "Output only the description as a single English paragraph, no headers or explanations."
)

DESCRIBE_GARMENT = (
    "Analyze this photo of a clothing item and write a precise, literal description for an AI image "
    "generation prompt. Be extremely specific about the COLOR — name the exact shade (e.g. 'deep burgundy / "
    "wine red', not just 'red'). Also describe: garment type, fabric/material and texture, fit and silhouette, "
    "sleeve/neckline/hem/collar details, pattern, and any distinctive features. "
    "Output only the description as a single English paragraph, no explanations."
)

BUILD_TRYON_EN = (
    "You will be given a character appearance description and a garment description. "
    "Combine them into a single, detailed, professional English prompt for Imagen 3 that generates "
    "a photorealistic FULL-LENGTH, full-body photo of a woman matching the character description, "
    "wearing exactly the described garment. "
    "Emphasize that the garment's color, shade, fabric, texture and silhouette must match the description "
    "EXACTLY and precisely — do not alter, lighten, darken or change the color or style of the garment. "
    "Add: photorealistic, natural skin texture, real human proportions, candid photography, "
    "shot on Sony A7 85mm f/1.4, natural soft lighting, simple neutral studio background, "
    "relaxed standing pose, full body visible from head to feet including shoes, entire figure framed in shot. "
    "Output only the prompt, no explanations."
)

BUILD_VIDEO_RU = (
    "Ты — эксперт по промптам для видео-генерации (Veo 3). "
    "По идее пользователя составь подробный структурированный промпт НА РУССКОМ для короткого видео. "
    "Включи: главный объект/персонаж, его действие и движение, сцену и окружение, движение камеры, "
    "освещение, цвет, стиль, настроение и атмосферу. "
    "Если в идее есть человек — обязательно укажи: естественные движения, живую мимику, реалистичную динамику. "
    "Выведи только текст промпта, без вступлений и пояснений."
)

TRANSLATE_VIDEO_EN = (
    "Translate and adapt the Russian prompt into a professional English video-generation prompt for Veo 3. "
    "Preserve all details and structure: subject, action/motion, scene, camera movement, lighting, color, "
    "style, mood and atmosphere. "
    "If the prompt contains a person or people, automatically add realism keywords: "
    "photorealistic, natural movement, lifelike expression, cinematic, real human proportions — "
    "but only if they don't contradict the stated style. "
    "Output only the English prompt, no explanations."
)

BUILD_ANIMATE_RU = (
    "Ты — эксперт по промптам для оживления фото в видео (Veo 3, image-to-video) для фэшн-съёмок. "
    "Тебе дано фото фотомодели в одежде и описание желаемой сцены от пользователя. "
    "Составь подробный промпт НА РУССКОМ для анимации этого фото: опиши естественное движение модели "
    "(плавная походка, поворот, позирование, взгляд в камеру, ветер развевает волосы или одежду и т.п.), "
    "движение камеры (медленный наезд, панорама, лёгкая орбита и т.д.), атмосферу локации — "
    "используй ту локацию, что видна на фото или указана пользователем (помещение/студия или улица/на воздухе), "
    "освещение и настроение. "
    "Внешность модели, причёску, одежду, цвета и силуэт НЕ менять — только добавляй естественное движение "
    "и динамику камеры, как в видео с модного показа или рекламной видеосъёмки. "
    "Обязательно укажи, что фон и локация должны быть видны полностью с самого первого кадра видео — "
    "без затемнения, наплыва, появления или смены фона в процессе ролика. "
    "Выведи только текст промпта, без вступлений и пояснений."
)

TRANSLATE_ANIMATE_EN = (
    "Translate and adapt the Russian prompt into a professional English prompt for Veo 3 image-to-video generation. "
    "Preserve all details: the subject's motion, camera movement, location atmosphere, lighting, mood. "
    "Add realism keywords: photorealistic, natural movement, lifelike expression, cinematic, subtle motion, "
    "fashion film aesthetic — but only if they don't contradict the stated style. "
    "Strongly emphasize that the person's appearance, outfit, colors and identity must remain EXACTLY "
    "as in the source image — only add motion and camera movement. "
    "Strongly emphasize that the background and location must be fully visible and established from "
    "the very first frame — no fade-in, dissolve, or background appearing/changing during the clip. "
    "Output only the English prompt, no explanations."
)

BUILD_TRYON_BG_RU = (
    "Ты — эксперт по промптам для image-edit моделей (фэшн-съёмка). "
    "Тебе дано описание желаемой локации/фона от пользователя для фото девушки в одежде. "
    "Составь подробный промпт НА РУССКОМ для замены фона вокруг девушки: опиши локацию, окружение, "
    "освещение, атмосферу, время суток, цветовую палитру и детали окружения. "
    "Не описывай саму девушку, её одежду, позу, причёску или внешность — только фон, локацию, "
    "окружение и освещение. "
    "Выведи только текст промпта, без вступлений и пояснений."
)

TRANSLATE_TRYON_BG_EN = (
    "Translate and adapt the Russian background/location description into a professional English "
    "instruction for an AI image-editing model (gpt-image-2). "
    "The instruction must tell the model to redraw ONLY the background, environment and lighting of "
    "the photo to match the description. "
    "Strongly emphasize that the person's face, hairstyle, body proportions, pose, outfit, colors and "
    "identity must remain EXACTLY as in the original photo — do not change, move or re-pose the person. "
    "Output only the English instruction, no explanations."
)

BUILD_TRYON_VIDEO_RU = (
    "Ты — эксперт по техническим промптам для видео-генерации (Veo 3, image-to-video) для фэшн-съёмок. "
    "Тебе дано фото девушки в одежде на фоне локации и описание желаемой съёмки от пользователя. "
    "Составь промпт НА РУССКОМ, описывающий ТОЛЬКО технические аспекты съёмки и физику движения, "
    "БЕЗ описания внешности, одежды, позы, причёски или фона (они уже заданы фото и не должны меняться). "
    "Включи: "
    "движение камеры (медленный наезд, отъезд, панорама, лёгкая орбита, проезд и т.п.); "
    "параметры съёмки (глубина резкости, фокус, яркость, экспозиция, резкость, контраст, цветокоррекция); "
    "физику и динамику — простые повседневные движения девушки (идёт, поворачивается, поправляет волосы, "
    "смотрит по сторонам, улыбается — обычные бытовые движения, БЕЗ модельной походки по подиуму и дефиле); "
    "природные элементы при наличии (дуновение ветра, колыхание ткани и волос, течение воды, движение "
    "листвы и т.п.). "
    "Используй слово 'девушка', а не 'модель'. "
    "Выведи только текст промпта, без вступлений и пояснений."
)

TRANSLATE_TRYON_VIDEO_EN = (
    "Translate and adapt the Russian prompt into a professional English prompt for Veo 3 image-to-video "
    "generation. "
    "The prompt must describe ONLY camera technique (movement, depth of field, focus, brightness, "
    "exposure, sharpness, contrast, color grading) and physics/motion (the woman's simple, everyday, "
    "natural movements, wind, fabric and hair movement, water, foliage, etc.). "
    "Use the words 'woman' or 'young woman', never 'girl' or 'model'. Avoid any runway, catwalk or "
    "fashion-show walk style. "
    "Strongly emphasize that the person's appearance, outfit, colors, identity AND the background/location "
    "must remain EXACTLY as in the source image — only add camera motion and natural physics-based movement. "
    "Output only the English prompt, no explanations."
)

ANALYZE_STYLE = (
    "Analyze this reference image and extract its visual design style for AI image generation. "
    "Describe only the background and aesthetic: color palette, textures, gradients, patterns, "
    "lighting mood, overall visual style. Do NOT mention any text, people, or specific objects. "
    "Output a concise English prompt (max 80 words) describing only the background/style "
    "suitable for generating infographic slide backgrounds."
)
