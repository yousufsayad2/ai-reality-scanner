import os
import base64
import json
import urllib.request
import urllib.error
import urllib.parse
from io import BytesIO
from datetime import datetime

import streamlit as st
from PIL import Image, ImageOps

# -----------------------------
# Page
# -----------------------------
st.set_page_config(
    page_title="AI Reality Scanner PRO",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 10% 5%, #172554 0, #080b16 32%, #05060b 72%);
}
.block-container {max-width:1180px;padding-top:2rem;padding-bottom:4rem;}
.hero {
    padding:34px; border-radius:28px; margin-bottom:20px;
    background:linear-gradient(135deg,rgba(59,130,246,.18),rgba(168,85,247,.14));
    border:1px solid rgba(255,255,255,.10);
}
.hero h1 {font-size:3rem;margin:0 0 8px;}
.hero p {color:#cbd5e1;font-size:1.08rem;margin:0;}
.card {
    padding:22px;border-radius:22px;background:rgba(15,23,42,.74);
    border:1px solid rgba(255,255,255,.08);margin:10px 0;
}
.badge {
    display:inline-block;padding:6px 12px;border-radius:999px;
    background:rgba(59,130,246,.16);color:#93c5fd;font-size:.85rem;
}
.small {color:#94a3b8;font-size:.9rem;}
.stButton>button {border-radius:14px;min-height:46px;font-weight:700;}
div[data-testid="stFileUploader"] {
    background:rgba(15,23,42,.5); border-radius:18px; padding:8px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Header
# -----------------------------
st.markdown("""
<div class="hero">
<span class="badge">GEMINI VISION • PRO</span>
<h1>📸 AI Reality Scanner</h1>
<p>صوّر أي حاجة → الذكاء الاصطناعي يفهمها → يحللها → ويقولك تعمل إيه بعدها.</p>
</div>
""", unsafe_allow_html=True)

# -----------------------------
# API helpers
# -----------------------------
def get_api_key():
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key.strip()
    try:
        key = st.secrets.get("GEMINI_API_KEY")
        return key.strip() if key else None
    except Exception:
        return None


def image_to_base64(image):
    buf = BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=92)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def call_gemini(image, mode, language, extra_instruction):
    api_key = get_api_key()
    if not api_key:
        return None, "مفتاح Gemini غير موجود. أضف GEMINI_API_KEY في Streamlit Secrets."

    prompts = {
        "🧠 تحليل ذكي": """حلل الصورة تحليلًا شاملًا. حدد نوع الصورة، أهم العناصر، النصوص المهمة، وما الذي يمكن فعله بناءً عليها.""",
        "📝 استخراج النص OCR": """استخرج كل النصوص التي تستطيع قراءتها من الصورة. حافظ على ترتيبها قدر الإمكان. إذا كان جزء غير واضح اكتب [غير واضح] ولا تخمّن.""",
        "🧾 فاتورة / إيصال": """حلل الفاتورة أو الإيصال. استخرج اسم المتجر إن كان ظاهرًا، البنود، الكميات، الأسعار، الخصومات، الضرائب، والإجمالي الظاهر. لا تخترع أرقامًا.""",
        "📄 مستند / ورقة": """اقرأ المستند، ثم لخّصه. استخرج العناوين والنقاط المهمة والأسماء والأرقام والتواريخ الظاهرة. إذا كان طويلًا، أعطِ ملخصًا منظمًا.""",
        "💻 كود برمجي": """افهم الكود الظاهر في الصورة. اشرح وظيفته، حدد الأخطاء أو المشاكل الواضحة، ثم اقترح نسخة إصلاح أو تعديلات عملية عندما يكون ذلك ممكنًا.""",
        "📊 رسم بياني": """حلل الرسم البياني. اذكر المحاور، الاتجاهات، القيم الواضحة، المقارنات، وأي استنتاجات مباشرة يمكن قراءتها من الرسم دون اختلاق أرقام.""",
        "🧮 سؤال / مسألة": """حدد السؤال الموجود في الصورة وحلّه خطوة بخطوة. اكتب القوانين أو خطوات التفكير اللازمة، ثم أعطِ الإجابة النهائية بوضوح.""",
        "🔍 فحص تفاصيل": """افحص الصورة بحثًا عن تفاصيل صغيرة مهمة: نصوص، أرقام، رموز، عناصر، أخطاء مرئية، أو تناقضات. فرّق بين المؤكد وغير الواضح.""",
    }

    selected = prompts.get(mode, prompts["🧠 تحليل ذكي"])

    prompt = f"""
أنت AI Reality Scanner PRO.

اللغة المطلوبة: {language}
نوع التحليل المطلوب: {mode}

{selected}

قواعد مهمة:
- لا تخترع أي معلومة غير ظاهرة.
- إذا لم تكن معلومة واضحة، قل "غير واضح".
- لا تدّعِ معرفة هوية الأشخاص في الصورة.
- لا تدّعِ تحديد الموقع الجغرافي الدقيق من مجرد مظهر الصورة.
- اجعل النتيجة عملية ومنظمة.

اكتب النتيجة بهذا الشكل:

### 👁️ ماذا أرى؟
### 🧠 التحليل
### 📌 أهم التفاصيل
### 🚀 ماذا أفعل الآن؟
- اذكر 3 خطوات عملية مناسبة للصورة.

### 💡 ملاحظات
اذكر أي حدود أو أجزاء غير واضحة.

تعليمات إضافية من المستخدم:
{extra_instruction or "لا توجد تعليمات إضافية."}
"""

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_to_base64(image),
                    }
                },
            ]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1800,
        },
    }

    model = "gemini-3.5-flash-lite"
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + model
        + ":generateContent?key="
        + urllib.parse.quote(api_key, safe="")
    )

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))

        candidates = data.get("candidates", [])
        if not candidates:
            return None, "Gemini لم يرجع نتيجة."

        parts = candidates[0].get("content", {}).get("parts", [])
        result = "\n".join(
            part.get("text", "") for part in parts if part.get("text")
        ).strip()

        if not result:
            return None, "Gemini رجع استجابة بدون نص."
        return result, None

    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            error_data = json.loads(raw)
            message = error_data.get("error", {}).get("message", raw)
        except Exception:
            message = raw
        return None, f"Gemini رفض الطلب: {message}"

    except Exception as e:
        return None, f"تعذر الاتصال بـ Gemini: {str(e)[:700]}"


# -----------------------------
# Sidebar settings
# -----------------------------
with st.sidebar:
    st.header("⚙️ إعدادات")
    language = st.selectbox(
        "لغة النتيجة",
        ["العربية المصرية", "العربية الفصحى", "English"],
        index=0,
    )
    mode = st.selectbox(
        "نوع التحليل",
        [
            "🧠 تحليل ذكي",
            "📝 استخراج النص OCR",
            "🧾 فاتورة / إيصال",
            "📄 مستند / ورقة",
            "💻 كود برمجي",
            "📊 رسم بياني",
            "🧮 سؤال / مسألة",
            "🔍 فحص تفاصيل",
        ],
    )
    extra = st.text_area(
        "تعليمات إضافية (اختياري)",
        placeholder="مثال: ركز على الأسعار فقط...",
        height=100,
    )
    st.caption("🔐 المفتاح يُقرأ من GEMINI_API_KEY في Secrets.")

# -----------------------------
# Upload
# -----------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("📤 1. ارفع صورة")

uploaded = st.file_uploader(
    "JPG / JPEG / PNG / WEBP",
    type=["jpg", "jpeg", "png", "webp"],
    label_visibility="collapsed",
)
st.markdown(
    '<p class="small">كلما كانت الصورة أوضح، كانت قراءة النصوص والتفاصيل أفضل.</p></div>',
    unsafe_allow_html=True,
)

if not uploaded:
    st.markdown("""
    <div class="card">
    <h3>✨ التطبيق يقدر يعمل إيه؟</h3>
    <p>
    📝 OCR للنصوص • 🧾 قراءة الفواتير • 📄 تلخيص المستندات •
    💻 تحليل الأكواد • 📊 فهم الرسوم البيانية • 🧮 حل المسائل •
    🔍 فحص التفاصيل • 🧠 تحليل عام
    </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# -----------------------------
# Image preview
# -----------------------------
try:
    image = ImageOps.exif_transpose(Image.open(uploaded))
except Exception:
    st.error("الصورة غير صالحة أو لا يمكن قراءتها.")
    st.stop()

left, right = st.columns([1, 1], gap="large")

with left:
    st.image(image, caption="الصورة", width="stretch")

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("⚡ 2. التحليل")
    st.write(f"**النمط:** {mode}")
    if extra:
        st.write(f"**تعليماتك:** {extra}")

    analyze = st.button(
        "🔎 حلّل الصورة الآن",
        type="primary",
        width="stretch",
    )
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Analysis result
# -----------------------------
if analyze:
    with st.spinner("🤖 Gemini بيحلل الصورة..."):
        result, error = call_gemini(image, mode, language, extra)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🧠 النتيجة")

    if error:
        st.error(error)
    else:
        st.markdown(result)

        st.download_button(
            "⬇️ حفظ النتيجة كملف TXT",
            data=result,
            file_name=f"ai_reality_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            width="stretch",
        )

        st.info("💡 تقدر تنسخ النتيجة من الصفحة أو تحفظها كملف TXT.")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;margin-top:42px;color:#64748b;">
AI Reality Scanner PRO • Gemini Vision
</div>
""", unsafe_allow_html=True)
