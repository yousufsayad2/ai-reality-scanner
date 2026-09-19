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

# ============================================================
# AI REALITY SCANNER ULTIMATE
# ============================================================

st.set_page_config(
    page_title="AI Reality Scanner ULTIMATE",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -------------------- UI --------------------
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 10% 5%, #172554 0, #080b16 32%, #05060b 72%);
}
.block-container {max-width:1180px;padding-top:1.5rem;padding-bottom:4rem;}
.hero {
    padding:34px;border-radius:30px;margin-bottom:20px;
    background:linear-gradient(135deg,rgba(59,130,246,.20),rgba(168,85,247,.15));
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
.stButton>button,.stDownloadButton>button {border-radius:14px;min-height:46px;font-weight:700;}
div[data-testid="stFileUploader"] {background:rgba(15,23,42,.5);border-radius:18px;padding:8px;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<span class="badge">GEMINI VISION • ULTIMATE</span>
<h1>📸 AI Reality Scanner</h1>
<p>صوّر أي حاجة → افهمها → حلّلها → اسأل عنها → احفظ النتيجة.</p>
</div>
""", unsafe_allow_html=True)

# -------------------- Gemini --------------------
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


def gemini_request(image, prompt):
    api_key = get_api_key()
    if not api_key:
        return None, "مفتاح Gemini غير موجود في Streamlit Secrets."

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_to_base64(image)
                    }
                }
            ]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2200
        }
    }

    model = "gemini-3.5-flash-lite"
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + model + ":generateContent?key=" + urllib.parse.quote(api_key, safe="")
    )

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))

        candidates = data.get("candidates", [])
        if not candidates:
            return None, "Gemini لم يرجع نتيجة."

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "\n".join(
            p.get("text", "") for p in parts if p.get("text")
        ).strip()

        return (text or "لم يرجع Gemini نصًا."), None

    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            obj = json.loads(raw)
            msg = obj.get("error", {}).get("message", raw)
        except Exception:
            msg = raw
        return None, f"Gemini رفض الطلب: {msg}"
    except Exception as e:
        return None, f"تعذر الاتصال بـ Gemini: {str(e)[:700]}"


# -------------------- Analysis modes --------------------
MODE_PROMPTS = {
    "🧠 تحليل ذكي":
        "حلل الصورة تحليلًا شاملًا وحدد نوع المحتوى وأهم المعلومات والاستخدامات.",
    "📝 استخراج النص OCR":
        "استخرج كل النص الظاهر في الصورة بدقة وحافظ على ترتيب الأسطر قدر الإمكان. اكتب [غير واضح] بدل التخمين.",
    "🧾 فاتورة / إيصال":
        "استخرج المتجر، البنود، الكميات، الأسعار، الخصومات، الضرائب والإجمالي الظاهر. لا تخترع أرقامًا.",
    "📄 مستند / ورقة":
        "اقرأ المستند، استخرج أهم البيانات والعناوين والتواريخ والأرقام، ثم لخّصه.",
    "💻 كود برمجي":
        "اشرح الكود، وظيفته، الأخطاء الظاهرة، ثم اقترح إصلاحات عملية أو نسخة محسنة.",
    "📊 رسم بياني":
        "حلل المحاور والقيم والاتجاهات والمقارنات والاستنتاجات المباشرة من الرسم.",
    "🧮 سؤال / مسألة":
        "اقرأ السؤال وحله خطوة بخطوة مع القوانين والنتيجة النهائية.",
    "🔍 فحص تفاصيل":
        "افحص الصورة بحثًا عن النصوص والأرقام والرموز والعناصر والأخطاء المرئية والتفاصيل المهمة."
}

def build_analysis_prompt(mode, language, extra):
    return f"""
أنت AI Reality Scanner ULTIMATE.
اللغة: {language}
النمط: {mode}

المطلوب:
{MODE_PROMPTS[mode]}

اكتب:
### 👁️ ماذا أرى؟
### 🧠 التحليل
### 📌 أهم التفاصيل
### 🚀 ماذا أفعل الآن؟
اذكر 3 خطوات عملية مناسبة.
### 💡 ملاحظات
اذكر ما هو غير واضح بدل التخمين.

قواعد:
- لا تخترع معلومات غير ظاهرة.
- لا تدّعي معرفة هوية الأشخاص.
- لا تدّعي تحديد الموقع الدقيق من الصورة وحدها.
- فرّق بين المعلومة المؤكدة والاحتمال.

تعليمات إضافية:
{extra or "لا توجد."}
"""


# -------------------- Sidebar --------------------
with st.sidebar:
    st.header("⚙️ إعدادات")
    language = st.selectbox(
        "لغة النتيجة",
        ["العربية المصرية", "العربية الفصحى", "English"]
    )
    mode = st.selectbox("نوع التحليل", list(MODE_PROMPTS.keys()))
    extra = st.text_area(
        "تعليمات إضافية",
        placeholder="مثال: ركز على الأسعار فقط...",
        height=100
    )
    st.caption("🔐 Gemini API Key محفوظ في Secrets.")

# -------------------- Upload --------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("📤 ارفع صورة")

uploaded = st.file_uploader(
    "JPG / JPEG / PNG / WEBP",
    type=["jpg", "jpeg", "png", "webp"],
    label_visibility="collapsed"
)
st.markdown(
    '<p class="small">ارفع صورة واضحة للحصول على أفضل قراءة.</p></div>',
    unsafe_allow_html=True
)

if not uploaded:
    st.markdown("""
    <div class="card">
    <h3>✨ المميزات</h3>
    <p>
    📝 OCR • 🧾 فواتير • 📄 مستندات • 💻 كود • 📊 رسوم بيانية •
    🧮 مسائل • 🔍 تفاصيل • 💬 Chat مع الصورة • 📥 حفظ النتيجة
    </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

try:
    image = ImageOps.exif_transpose(Image.open(uploaded))
except Exception:
    st.error("الصورة غير صالحة.")
    st.stop()

# Store image in session for chat
st.session_state["scanner_image"] = image

left, right = st.columns([1, 1], gap="large")

with left:
    st.image(image, caption="الصورة", width="stretch")

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("⚡ التحليل")
    st.write(f"**النمط:** {mode}")
    analyze = st.button("🔎 حلّل الصورة الآن", type="primary", width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)

# -------------------- Analysis --------------------
if analyze:
    with st.spinner("🤖 Gemini بيحلل الصورة..."):
        result, error = gemini_request(
            image,
            build_analysis_prompt(mode, language, extra)
        )

    if error:
        st.error(error)
    else:
        st.session_state["analysis_result"] = result
        st.session_state["chat_history"] = []

# -------------------- Result --------------------
if st.session_state.get("analysis_result"):
    result = st.session_state["analysis_result"]

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🧠 النتيجة")
    st.markdown(result)

    st.download_button(
        "⬇️ حفظ التحليل TXT",
        data=result,
        file_name=f"ai_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
        width="stretch"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # -------------------- Chat --------------------
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("💬 Chat مع الصورة")
    st.caption("اسأل Gemini أي سؤال عن الصورة أو عن نتيجة التحليل.")

    for msg in st.session_state.get("chat_history", []):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    question = st.chat_input("مثال: إيه أهم حاجة في الصورة؟")

    if question:
        st.session_state.setdefault("chat_history", []).append(
            {"role": "user", "content": question}
        )

        history_text = "\n".join(
            f'{m["role"]}: {m["content"]}'
            for m in st.session_state["chat_history"][-8:]
        )

        chat_prompt = f"""
أنت مساعد AI Reality Scanner.
أجب عن سؤال المستخدم اعتمادًا على الصورة الموجودة وسياق التحليل.

التحليل السابق:
{result}

سجل المحادثة:
{history_text}

سؤال المستخدم:
{question}

أجب بالعربية المصرية بوضوح، ولا تخترع شيئًا غير ظاهر في الصورة.
إذا كان السؤال يحتاج معلومة غير موجودة في الصورة، قل ذلك بوضوح.
"""

        with st.spinner("🤖 بفكر في سؤالك..."):
            answer, error = gemini_request(image, chat_prompt)

        if error:
            answer = error

        st.session_state["chat_history"].append(
            {"role": "assistant", "content": answer}
        )
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# -------------------- Footer --------------------
st.markdown("""
<div style="text-align:center;margin-top:45px;color:#64748b;">
AI Reality Scanner ULTIMATE • Gemini Vision
</div>
""", unsafe_allow_html=True)
