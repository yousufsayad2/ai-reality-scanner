import os
import base64
import json
import urllib.request
import urllib.error
from io import BytesIO

import streamlit as st
from PIL import Image, ImageOps

st.set_page_config(
    page_title="AI Reality Scanner",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 15% 10%, #172554 0, #080b16 32%, #05060b 72%);
}
.block-container {max-width:1100px;padding-top:2rem;padding-bottom:3rem;}
.hero{padding:32px;border-radius:28px;margin-bottom:22px;background:linear-gradient(135deg,rgba(59,130,246,.18),rgba(168,85,247,.14));border:1px solid rgba(255,255,255,.10);}
.hero h1{font-size:3rem;margin:0;}
.hero p{color:#cbd5e1;font-size:1.08rem;}
.card{padding:22px;border-radius:22px;background:rgba(15,23,42,.72);border:1px solid rgba(255,255,255,.08);margin:10px 0;}
.badge{display:inline-block;padding:6px 12px;border-radius:999px;background:rgba(59,130,246,.16);color:#93c5fd;font-size:.85rem;}
.small{color:#94a3b8;font-size:.9rem;}
.stButton>button{border-radius:14px;min-height:48px;font-weight:700;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<span class="badge">GEMINI VISION</span>
<h1>📸 AI Reality Scanner</h1>
<p>صوّر أي حاجة — والذكاء الاصطناعي يفهمها ويحللها.</p>
</div>
""", unsafe_allow_html=True)

def get_key():
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key
    try:
        return st.secrets.get("GEMINI_API_KEY")
    except Exception:
        return None

def analyze_with_gemini(image):
    api_key = get_key()
    if not api_key:
        return "مفتاح Gemini غير موجود في Secrets.", "missing"

    prompt = """حلل الصورة بالعربية المصرية الواضحة وبدون اختلاق معلومات.
اكتب:
### 👁️ ماذا أرى؟
### 🧠 التحليل
### 📌 أهم التفاصيل
### 🚀 ماذا أستطيع أن أفعل لك؟
إذا كانت فاتورة استخرج البنود والأسعار والإجمالي الظاهر.
إذا كانت ورقة اقرأ النص الظاهر ولخصه.
إذا كانت مسألة اشرح الحل خطوة بخطوة.
إذا كان كودًا اذكر الأخطاء الظاهرة والإصلاح.
إذا كان رسمًا بيانيًا اشرح الاتجاهات والأرقام الواضحة.
إذا كانت صورة عامة صف أهم العناصر.
إذا كانت معلومة غير واضحة قل إنها غير واضحة."""

    buf = BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=90)
    image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    body = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}}
            ]
        }]
    }

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.5-flash-lite:generateContent?key=" + api_key
    )

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text, "ok"

    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(raw)
            msg = err.get("error", {}).get("message", raw)
        except Exception:
            msg = raw
        return f"Gemini رفض الطلب: {msg}", "error"

    except Exception as e:
        return f"تعذر الاتصال بـ Gemini: {str(e)[:500]}", "error"


st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("📤 1. اختار صورة")
uploaded = st.file_uploader(
    "ارفع JPG / PNG / WEBP",
    type=["jpg", "jpeg", "png", "webp"],
    label_visibility="collapsed",
)
st.markdown('<p class="small">ارفع صورة واضحة للحصول على تحليل أفضل.</p></div>', unsafe_allow_html=True)

if uploaded:
    image = ImageOps.exif_transpose(Image.open(uploaded))

    left, right = st.columns([1, 1], gap="large")
    with left:
        st.image(image, caption="الصورة", width="stretch")

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("⚡ 2. ابدأ التحليل")
        analyze = st.button("🔎 حلّل الصورة الآن", type="primary", width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)

        if analyze:
            with st.spinner("🤖 جاري التحليل باستخدام Gemini..."):
                result, status = analyze_with_gemini(image)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("🧠 النتيجة")
            if status == "missing":
                st.warning(result)
            else:
                st.markdown(result)
            st.markdown("</div>", unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="card">
    <h3>✨ أمثلة</h3>
    <p>🧾 فاتورة • 📄 مستند • 📊 رسم بياني • 💻 كود • 📝 سؤال • 🖼️ صورة عامة</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div style="text-align:center;margin-top:40px;color:#64748b;">AI Reality Scanner • Gemini Vision</div>', unsafe_allow_html=True)
