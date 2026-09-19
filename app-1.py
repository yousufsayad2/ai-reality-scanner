import os
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
.block-container {max-width: 1100px; padding-top: 2rem; padding-bottom: 3rem;}
.hero {
    padding: 32px; border-radius: 28px; margin-bottom: 22px;
    background: linear-gradient(135deg, rgba(59,130,246,.18), rgba(168,85,247,.14));
    border: 1px solid rgba(255,255,255,.10);
}
.hero h1 {font-size: 3rem; margin: 0; letter-spacing:-1px;}
.hero p {color:#cbd5e1; font-size:1.08rem;}
.card {
    padding: 22px; border-radius: 22px; background: rgba(15,23,42,.72);
    border:1px solid rgba(255,255,255,.08); margin:10px 0;
}
.badge {display:inline-block; padding:6px 12px; border-radius:999px;
    background:rgba(59,130,246,.16); color:#93c5fd; font-size:.85rem;}
.small {color:#94a3b8; font-size:.9rem;}
.stButton>button {border-radius:14px; min-height:48px; font-weight:700;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <span class="badge">GEMINI VISION • MULTI-PURPOSE</span>
  <h1>📸 AI Reality Scanner</h1>
  <p>صوّر أي حاجة. التطبيق يحاول يفهم الصورة، يحدد نوع المحتوى، ويقدّم لك تحليلًا عمليًا.</p>
</div>
""", unsafe_allow_html=True)


def get_secret(name):
    try:
        return st.secrets.get(name)
    except Exception:
        return None


def local_fallback():
    return """### 🔎 وضع العرض
تم استقبال الصورة بنجاح، لكن محرك Gemini غير متصل حاليًا.

أضف `GEMINI_API_KEY` في Streamlit Secrets ثم أعد تشغيل التطبيق."""


def analyze_with_gemini(image):
    from google import genai
    from google.genai import types

    key = os.getenv("GEMINI_API_KEY") or get_secret("GEMINI_API_KEY")
    if not key:
        return None, "missing"

    prompt = """أنت AI Reality Scanner.
حلل الصورة بالعربية المصرية الواضحة، بدون اختلاق معلومات.
ابدأ بـ:
### 👁️ ماذا أرى؟
ثم:
### 🧠 التحليل
ثم:
### 📌 أهم التفاصيل
ثم:
### 🚀 ماذا أستطيع أن أفعل لك؟
اقترح 3 إجراءات مناسبة حسب نوع الصورة.

إذا كانت فاتورة: استخرج البنود والأسعار والإجمالي الظاهر، ونبّه إذا كان شيء غير واضح.
إذا كانت ورقة/مستند: اقرأ النص الظاهر ولخصه.
إذا كانت مسألة: اشرح الحل خطوة بخطوة.
إذا كان كودًا: حدد الأخطاء الظاهرة واقترح الإصلاح.
إذا كان رسمًا بيانيًا: استخرج الاتجاهات والأرقام الواضحة.
إذا كانت صورة عامة: صف العناصر المهمة.

مهم: لا تدّعي التعرف المؤكد على هوية الأشخاص أو أماكنهم. وإذا كانت المعلومة غير واضحة قل "غير واضح"."""

    try:
        buf = BytesIO()
        image.convert("RGB").save(buf, format="JPEG", quality=90)
        image_part = types.Part.from_bytes(
            data=buf.getvalue(),
            mime_type="image/jpeg",
        )

        client = genai.Client(api_key=key)

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[prompt, image_part],
        )

        text = getattr(response, "text", None)
        if not text:
            return "لم يرجع Gemini نصًا للتحليل.", "error"

        return text, "ok"

    except Exception as e:
        return (
            f"تعذر إكمال التحليل حاليًا.\n\n"
            f"تفاصيل تقنية: `{str(e)[:500]}`",
            "error",
        )


st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("📤 1. اختار صورة")
uploaded = st.file_uploader(
    "ارفع JPG / PNG / WEBP",
    type=["jpg", "jpeg", "png", "webp"],
    label_visibility="collapsed",
)
st.markdown(
    '<p class="small">يفضل صورة واضحة وبإضاءة جيدة للحصول على نتائج أفضل.</p></div>',
    unsafe_allow_html=True,
)

if uploaded:
    image = Image.open(uploaded)
    image = ImageOps.exif_transpose(image)

    left, right = st.columns([1, 1], gap="large")

    with left:
        st.image(image, caption="الصورة", width="stretch")

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("⚡ 2. ابدأ التحليل")
        st.write("سيختار التطبيق أسلوب التحليل المناسب تلقائيًا.")
        analyze = st.button(
            "🔎 حلّل الصورة الآن",
            type="primary",
            width="stretch",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if analyze:
            with st.spinner("🤖 جاري تحليل الصورة باستخدام Gemini..."):
                result, status = analyze_with_gemini(image)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("🧠 النتيجة")

            if status == "missing":
                st.warning(
                    "محرك Gemini غير متصل. أضف GEMINI_API_KEY في Secrets."
                )
                st.markdown(local_fallback())
            else:
                st.markdown(result)

            st.markdown("</div>", unsafe_allow_html=True)

else:
    st.markdown("""
    <div class="card">
    <h3>✨ أمثلة للاستخدام</h3>
    <p>🧾 فاتورة &nbsp; • &nbsp; 📄 مستند &nbsp; • &nbsp; 📊 رسم بياني &nbsp; • &nbsp; 💻 كود &nbsp; • &nbsp; 📝 سؤال &nbsp; • &nbsp; 🖼️ صورة عامة</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;margin-top:40px;color:#64748b;">
AI Reality Scanner • Gemini-powered portfolio prototype
</div>
""", unsafe_allow_html=True)
