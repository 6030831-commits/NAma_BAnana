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
    "The instruction must tell the model to replace the background and environment of the photo to match "
    "the description, and to fully and realistically integrate the person into the new scene: "
    "relight the person to match the new scene's light direction, color temperature and intensity; "
    "add realistic contact shadows and ambient occlusion under her feet and around her body; "
    "add subtle color grading / color spill from the environment onto her skin, hair and clothes; "
    "match the depth of field, grain and overall photographic quality of the background so the person "
    "looks like she was photographed in that location, not pasted on top. "
    "Strongly emphasize that the person's face, hairstyle, body proportions, pose, outfit, colors and "
    "identity must remain recognizable and unchanged — do not change, move or re-pose the person, only "
    "adjust lighting, shadows and color grading on her so she blends naturally into the new background. "
    "Output only the English instruction, no explanations."
)

BUILD_TRYON_VIDEO_RU = (
    "Ты — эксперт по техническим промптам для видео-генерации (Veo 3, image-to-video) для фэшн-съёмок. "
    "Тебе дано фото девушки в одежде на фоне локации и описание желаемой съёмки от пользователя. "
    "Составь промпт НА РУССКОМ, описывающий ТОЛЬКО технические аспекты съёмки и физику движения, "
    "БЕЗ описания внешности, одежды, позы, причёски или фона (они уже заданы фото и не должны меняться). "
    "Включи: "
    "движение камеры (плавный наезд, отъезд, панорама, лёгкая орбита, проезд и т.п. — в реальном времени, "
    "обычная скорость, без замедленной съёмки и слоу-мо); "
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
    "All movement — camera and the woman's motion — must be at normal, real-time speed. "
    "Never use the words 'slow motion', 'slow-mo' or 'slowed down', and do not imply a slow-motion effect. "
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
