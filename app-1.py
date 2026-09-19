import os
import base64
import json
import urllib.request
import urllib.error

import streamlit as st
from PIL import Image

# ============================================================
# YOSEF AI TRY-ON STUDIO — Gemini Image Edition
# ============================================================

st.set_page_config(
    page_title="Yosef AI — Try-On Studio",
    page_icon="👕",
    layout="wide",
)

# -----------------------------
# Styling
# -----------------------------
st.markdown("""
<style>
    .stApp {
        background:
            radial-gradient(circle at 15% 0%, rgba(125, 72, 255, .18), transparent 28%),
            radial-gradient(circle at 90% 10%, rgba(0, 220, 170, .12), transparent 25%),
            #090b12;
        color: #f7f7fb;
    }
    section[data-testid="stSidebar"] { background: #10131c; }
    .hero { padding: 28px 10px 18px; text-align: center; }
    .hero h1 { font-size: 42px; margin-bottom: 5px; font-weight: 800; }
    .hero p { color: #a7a9b6; font-size: 16px; }
    .card {
        background: rgba(25, 28, 39, .78);
        border: 1px solid rgba(255,255,255,.08);
        border-radius: 22px;
        padding: 22px;
        margin-bottom: 18px;
        box-shadow: 0 15px 45px rgba(0,0,0,.20);
    }
    .badge {
        display: inline-block;
        padding: 7px 12px;
        border-radius: 999px;
        background: rgba(142, 92, 255, .16);
        color: #cbb7ff;
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 8px;
    }
    .small { color: #9fa3b5; font-size: 13px; }
    div.stButton > button {
        width: 100%;
        border-radius: 14px;
        min-height: 50px;
        font-weight: 800;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------
# Gemini
# -----------------------------
def get_gemini_key():
    try:
        key = st.secrets.get("GEMINI_API_KEY")
        if key:
            return str(key).strip()
    except Exception:
        pass

    key = os.getenv("GEMINI_API_KEY")
    return key.strip() if key else None


def image_block(uploaded_file):
    data = uploaded_file.getvalue()
    encoded = base64.b64encode(data).decode("utf-8")
    mime = uploaded_file.type or "image/jpeg"
    return {
        "type": "image",
        "mime_type": mime,
        "data": encoded,
    }


def try_on_with_gemini(person_file, outfit_file, style, aspect):
    api_key = get_gemini_key()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY غير موجود في Streamlit Secrets."
        )

    prompt = f"""
Create a photorealistic fashion virtual try-on image.

REFERENCE ORDER:
1. The first image is the person/model.
2. The second image is the clothing/outfit.

TASK:
Put the exact clothing from the second image onto the person in the first image.

IMPORTANT:
- Preserve the person's face, identity, skin tone, body proportions and natural appearance.
- Preserve the garment's color, design, pattern, material, logos and important details.
- Make the garment fit naturally with realistic folds, shadows and lighting.
- Do not change the person's face or hairstyle.
- Do not add extra people.
- Keep the result realistic, like professional fashion photography.
- Prefer a full-body composition when possible.
- Style: {style}.
- Output aspect ratio: {aspect}.
""".strip()

    payload = {
        "model": "gemini-3.1-flash-image",
        "input": [
            image_block(person_file),
            image_block(outfit_file),
            {"type": "text", "text": prompt},
        ],
        "response_format": {
            "type": "image",
            "aspect_ratio": aspect,
            "image_size": "1K",
        },
    }

    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/interactions",
        data=body,
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            raw = response.read().decode("utf-8")
            result = json.loads(raw)
    except urllib.error.HTTPError as e:
        details = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API HTTP {e.code}: {details}") from e
    except Exception as e:
        raise RuntimeError(f"تعذر الاتصال بـ Gemini: {e}") from e

    # Current Interactions API normally exposes output_image directly.
    output_image = result.get("output_image")
    if isinstance(output_image, dict):
        data = output_image.get("data")
        if data:
            return base64.b64decode(data)

    # Fallback: inspect model output steps.
    for step in result.get("steps", []):
        for block in step.get("content", []) or step.get("summary", []):
            if isinstance(block, dict) and block.get("type") == "image":
                data = block.get("data")
                if data:
                    return base64.b64decode(data)

    raise RuntimeError(
        "Gemini رجّع استجابة بدون صورة. جرّب مرة أخرى، ولو ظهر نفس الخطأ ابعتلي نص الخطأ."
    )


# -----------------------------
# Header
# -----------------------------
st.markdown("""
<div class="hero">
    <div class="badge">🍌 GEMINI AI FASHION TRY-ON</div>
    <h1>YOSEF AI — TRY-ON STUDIO</h1>
    <p>ارفع صورة الشخص + صورة اللبس، وخلي Gemini يعمل تجربة اللبس بالـAI.</p>
</div>
""", unsafe_allow_html=True)


# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown("## ⚙️ إعدادات التجربة")

    mode = st.radio(
        "نوع التجربة",
        ["📸 صورة", "🎬 فيديو"],
        index=0,
    )

    style = st.selectbox(
        "ستايل النتيجة",
        [
            "Natural / Realistic",
            "Studio Fashion",
            "Streetwear",
            "Luxury Fashion",
            "E-commerce",
        ],
    )

    ratio = st.selectbox(
        "نسبة العرض",
        [
            "9:16 — Reels",
            "1:1 — Square",
            "4:5 — Instagram",
            "16:9 — Landscape",
        ],
    )

    st.markdown("---")
    st.markdown("### 🔐 AI")

    if get_gemini_key():
        st.success("Gemini API متصل")
    else:
        st.warning("أضف GEMINI_API_KEY في Streamlit Secrets.")

    st.markdown(
        '<div class="small">المفتاح لا يتم وضعه داخل app.py.</div>',
        unsafe_allow_html=True,
    )

    if mode == "🎬 فيديو":
        st.info(
            "نسخة Gemini الحالية تعمل على تجربة الملابس بالصور. "
            "الفيديو سنضيفه لاحقًا بمحرك فيديو مناسب."
        )


# -----------------------------
# Inputs
# -----------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### 👤 1 — صورة الشخص")
person_file = st.file_uploader(
    "ارفع صورة واضحة للشخص",
    type=["jpg", "jpeg", "png", "webp"],
    key="person",
)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### 👕 2 — صورة اللبس")
outfit_file = st.file_uploader(
    "ارفع صورة واضحة للملابس / اللوك",
    type=["jpg", "jpeg", "png", "webp"],
    key="outfit",
)
st.markdown("</div>", unsafe_allow_html=True)


# Preview
if person_file or outfit_file:
    cols = st.columns(2)

    if person_file:
        with cols[0]:
            st.markdown("**👤 الشخص**")
            st.image(person_file, use_container_width=True)

    if outfit_file:
        with cols[1]:
            st.markdown("**👕 اللبس**")
            st.image(outfit_file, use_container_width=True)


# -----------------------------
# Generate
# -----------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)

if mode == "📸 صورة":
    if st.button("✨ جرّب اللبس بالـAI", type="primary", use_container_width=True):

        if not get_gemini_key():
            st.error("مفتاح Gemini غير موجود في Streamlit Secrets.")
            st.stop()

        if not person_file:
            st.error("ارفع صورة الشخص أولًا.")
            st.stop()

        if not outfit_file:
            st.error("ارفع صورة اللبس أولًا.")
            st.stop()

        ratio_map = {
            "9:16 — Reels": "9:16",
            "1:1 — Square": "1:1",
            "4:5 — Instagram": "4:5",
            "16:9 — Landscape": "16:9",
        }
        aspect = ratio_map.get(ratio, "9:16")

        progress = st.progress(0)
        status = st.empty()

        try:
            status.info("📤 جاري تجهيز الصور...")
            progress.progress(15)

            status.info("🧠 Gemini بيعمل الـAI Try-On...")
            progress.progress(35)

            result_bytes = try_on_with_gemini(
                person_file,
                outfit_file,
                style,
                aspect,
            )

            progress.progress(90)
            status.success("✅ النتيجة جاهزة!")
            progress.progress(100)

            st.markdown("## ✨ النتيجة")

            result_image = Image.open(__import__("io").BytesIO(result_bytes))
            st.image(result_image, use_container_width=True)

            st.download_button(
                "⬇️ حفظ الصورة",
                data=result_bytes,
                file_name="yosef_ai_tryon.png",
                mime="image/png",
                use_container_width=True,
            )

        except Exception as e:
            st.error("حصل خطأ أثناء تنفيذ Gemini AI.")
            st.code(str(e))

else:
    st.info("اختار 📸 صورة للتجربة الحالية.")

st.markdown("</div>", unsafe_allow_html=True)

st.caption(
    "Powered by Google Gemini API • لا تضع مفاتيح API داخل GitHub أو داخل الكود."
)
