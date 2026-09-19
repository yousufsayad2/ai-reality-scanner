import io
import os
import tempfile

import streamlit as st
from PIL import Image, ImageFilter
from gradio_client import Client, handle_file

# ============================================================
# YOSEF AI — TRY-ON STUDIO
# Backend: official Hugging Face IDM-VTON
# Gemini / Higgsfield are NOT used.
# ============================================================

st.set_page_config(
    page_title="Yosef AI — Try-On Studio",
    page_icon="👕",
    layout="wide",
)

st.markdown("""
<style>
.stApp {
    background:
        radial-gradient(circle at 10% 10%, #10223d 0%, transparent 32%),
        radial-gradient(circle at 90% 10%, #182b20 0%, transparent 30%),
        #080b12;
    color:#f7f7fb;
}
.block-container{max-width:1150px;padding-top:2rem}
.hero{
    padding:30px;border-radius:24px;
    border:1px solid rgba(255,255,255,.12);
    background:rgba(16,22,34,.86);
    margin-bottom:22px;
}
.hero h1{font-size:42px;margin:0 0 8px}
.hero p{color:#aeb8c8;margin:0}
.card{
    padding:20px;border-radius:20px;
    border:1px solid rgba(255,255,255,.10);
    background:rgba(17,23,35,.78);
    margin-bottom:18px;
}
.badge{
    display:inline-block;padding:6px 12px;border-radius:999px;
    background:#123d2b;color:#8ff0bd;font-size:13px;
    margin-bottom:10px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="badge">● FREE AI VIRTUAL TRY-ON</div>
  <h1>👕 YOSEF AI — TRY-ON STUDIO</h1>
  <p>تغيير اللبس مع الحفاظ على صورة الشخص وملامحه قدر الإمكان.</p>
</div>
""", unsafe_allow_html=True)

SPACE_ID = "yisol/IDM-VTON"
HF_TOKEN = st.secrets.get("HF_TOKEN", "")


def save_upload(uploaded):
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    with open(path, "wb") as f:
        f.write(uploaded.getvalue())
    return path


def normalize_result(result):
    """
    IDM-VTON returns:
      (generated_image, masked_image)
    generated_image is normally a local file path from Gradio.
    """
    if isinstance(result, (list, tuple)):
        if not result:
            raise RuntimeError("الـAI رجّع نتيجة فارغة.")
        result = result[0]

    if isinstance(result, dict):
        result = (
            result.get("path")
            or result.get("url")
            or result.get("image")
            or result.get("value")
        )

    if not result:
        raise RuntimeError("لم يتم العثور على صورة النتيجة.")

    if isinstance(result, Image.Image):
        image = result.convert("RGB")
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return image, buf.getvalue()

    result = str(result)

    if result.startswith(("http://", "https://")):
        import requests
        r = requests.get(result, timeout=90)
        r.raise_for_status()
        data = r.content
    else:
        with open(result, "rb") as f:
            data = f.read()

    image = Image.open(io.BytesIO(data)).convert("RGB")
    return image, data


def preserve_face(original, generated):
    """
    Optional face-preservation pass.
    It copies the detected face pixels from the original image into
    the generated result with a feathered mask. If OpenCV or face
    detection is unavailable, the generated image is returned as-is.
    """
    try:
        import cv2
        import numpy as np

        orig = original.convert("RGB")
        gen = generated.convert("RGB")

        # The model works around 768x1024.
        orig_resized = orig.resize(gen.size, Image.Resampling.LANCZOS)

        gray = cv2.cvtColor(np.array(orig_resized), cv2.COLOR_RGB2GRAY)
        cascade = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        detector = cv2.CascadeClassifier(cascade)

        faces = detector.detectMultiScale(
            gray,
            scaleFactor=1.08,
            minNeighbors=5,
            minSize=(50, 50),
        )

        if len(faces) == 0:
            return gen

        # Use the largest detected face.
        x, y, w, h = max(faces, key=lambda r: r[2] * r[3])

        # Slightly enlarge the protected area around the face.
        pad_x = int(w * 0.16)
        pad_top = int(h * 0.12)
        pad_bottom = int(h * 0.08)

        x0 = max(0, x - pad_x)
        y0 = max(0, y - pad_top)
        x1 = min(gen.width, x + w + pad_x)
        y1 = min(gen.height, y + h + pad_bottom)

        crop = orig_resized.crop((x0, y0, x1, y1))

        mask = Image.new("L", crop.size, 0)
        mask.paste(255, (10, 10, max(10, crop.width - 10), max(10, crop.height - 10)))
        mask = mask.filter(ImageFilter.GaussianBlur(max(8, int(w * 0.08))))

        result = gen.copy()
        result.paste(crop, (x0, y0), mask)
        return result

    except Exception:
        return generated


def run_idm_vton(person_path, garment_path, description):
    client = Client(
        SPACE_ID,
        token=HF_TOKEN if HF_TOKEN else None,
        verbose=False,
    )

    # IMPORTANT:
    # The official Space uses an ImageEditor dictionary as input:
    # background + layers + composite.
    # We pass the arguments positionally in the exact order of
    # the official /tryon endpoint.
    result = client.predict(
        {
            "background": handle_file(person_path),
            "layers": [],
            "composite": None,
        },
        handle_file(garment_path),
        description,
        True,          # auto mask
        False,        # NO auto-crop: keep original framing
        30,            # denoising steps
        42,            # fixed seed
        api_name="/tryon",
    )

    return result


# ----------------------------
# Uploads
# ----------------------------
c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 👤 1 — صورة الشخص")
    person_file = st.file_uploader(
        "ارفع صورة واضحة للشخص",
        type=["jpg", "jpeg", "png", "webp"],
        key="person",
    )
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 👕 2 — صورة اللبس")
    outfit_file = st.file_uploader(
        "ارفع صورة اللبس التي تريد ارتداءها",
        type=["jpg", "jpeg", "png", "webp"],
        key="outfit",
    )
    st.markdown("</div>", unsafe_allow_html=True)

if person_file or outfit_file:
    p1, p2 = st.columns(2)
    if person_file:
        with p1:
            st.markdown("**👤 الشخص**")
            st.image(person_file, use_container_width=True)
    if outfit_file:
        with p2:
            st.markdown("**👕 اللبس المطلوب**")
            st.image(outfit_file, use_container_width=True)

st.markdown('<div class="card">', unsafe_allow_html=True)

garment_type = st.selectbox(
    "👔 نوع اللبس",
    [
        "Upper body / قميص أو تيشيرت أو جاكيت",
        "Lower body / بنطلون أو شورت",
        "Dress / فستان",
    ],
)

if garment_type.startswith("Upper"):
    garment_description = "Short sleeve shirt or t-shirt, realistic fabric, same garment shown in the reference image"
elif garment_type.startswith("Lower"):
    garment_description = "Pants or shorts, realistic fabric, same garment shown in the reference image"
else:
    garment_description = "Dress, realistic fabric, same garment shown in the reference image"

st.info("🔒 وضع الحفاظ على الملامح مفعّل. الصورة الأصلية لا يتم قصّها تلقائيًا.")

st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------
# Generate
# ----------------------------
if st.button("✨ جرّب اللبس بالـAI", use_container_width=True, type="primary"):

    if not person_file:
        st.error("ارفع صورة الشخص أولًا.")
        st.stop()

    if not outfit_file:
        st.error("ارفع صورة اللبس أولًا.")
        st.stop()

    person_path = save_upload(person_file)
    garment_path = save_upload(outfit_file)

    progress = st.progress(0)
    status = st.empty()

    try:
        status.info("🔗 الاتصال بمحرك Virtual Try-On...")
        progress.progress(10)

        original = Image.open(person_path).convert("RGB")

        status.info("📤 رفع صورة الشخص واللبس...")
        progress.progress(25)

        status.info("🧠 الـAI بيغيّر اللبس فقط...")
        progress.progress(45)

        raw_result = run_idm_vton(
            person_path,
            garment_path,
            garment_description,
        )

        progress.progress(88)

        generated, _ = normalize_result(raw_result)

        status.info("🔒 تثبيت ملامح الوجه من الصورة الأصلية...")
        final_image = preserve_face(original, generated)

        buf = io.BytesIO()
        final_image.save(buf, format="PNG")
        final_bytes = buf.getvalue()

        progress.progress(100)
        status.success("✅ خلصت! اللبس الجديد جاهز.")

        st.markdown("## ✨ النتيجة")
        st.image(final_image, use_container_width=True)

        st.download_button(
            "⬇️ حفظ الصورة",
            data=final_bytes,
            file_name="yosef_ai_tryon.png",
            mime="image/png",
            use_container_width=True,
        )

    except Exception as e:
        progress.empty()
        status.empty()
        st.error("❌ حصل خطأ أثناء تنفيذ الـAI")
        st.code(str(e))

    finally:
        for path in (person_path, garment_path):
            try:
                os.remove(path)
            except Exception:
                pass

st.caption("YOSEF AI • IDM-VTON • Hugging Face ZeroGPU")
