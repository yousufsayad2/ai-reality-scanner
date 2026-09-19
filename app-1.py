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

st.set_page_config(
    page_title="AI Reality Scanner ULTIMATE",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# UI
# ============================================================
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 10% 5%, #172554 0, #080b16 32%, #05060b 72%);
}
.block-container {max-width:1200px;padding-top:1.3rem;padding-bottom:4rem;}
.hero {padding:32px;border-radius:30px;margin-bottom:18px;
background:linear-gradient(135deg,rgba(59,130,246,.20),rgba(168,85,247,.15));
border:1px solid rgba(255,255,255,.10);}
.hero h1 {font-size:3rem;margin:0 0 8px;}
.hero p {color:#cbd5e1;font-size:1.05rem;margin:0;}
.card {padding:20px;border-radius:22px;background:rgba(15,23,42,.74);
border:1px solid rgba(255,255,255,.08);margin:10px 0;}
.badge {display:inline-block;padding:6px 12px;border-radius:999px;
background:rgba(59,130,246,.16);color:#93c5fd;font-size:.85rem;}
.small {color:#94a3b8;font-size:.9rem;}
.stButton>button,.stDownloadButton>button {border-radius:14px;min-height:44px;font-weight:700;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<span class="badge">GEMINI VISION • ULTIMATE ALL-IN-ONE</span>
<h1>📸 AI Reality Scanner</h1>
<p>صوّر أو ارفع أي حاجة → حلّلها → اسأل عنها → ترجمها → احفظ تقريرك.</p>
</div>
""", unsafe_allow_html=True)

# ============================================================
# Session state
# ============================================================
for key, default in {
    "history": [],
    "analysis": "",
    "last_source": None,
    "chat": [],
    "logged_in": False,
    "username": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ============================================================
# Authentication (simple demo/session login)
# ============================================================
if not st.session_state.logged_in:
    with st.sidebar:
        st.header("👤 حساب تجريبي")
        st.caption("تسجيل الدخول هنا محلي داخل جلسة Streamlit.")
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        if st.button("دخول", type="primary", width="stretch"):
            if username.strip() and password:
                st.session_state.logged_in = True
                st.session_state.username = username.strip()
                st.rerun()
            else:
                st.error("اكتب اسم المستخدم وكلمة المرور.")
else:
    with st.sidebar:
        st.success(f"مرحبًا {st.session_state.username} 👋")
        if st.button("تسجيل خروج"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

# ============================================================
# API
# ============================================================
def get_key():
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key.strip()
    try:
        key = st.secrets.get("GEMINI_API_KEY")
        return key.strip() if key else None
    except Exception:
        return None

def bytes_b64(data):
    return base64.b64encode(data).decode("utf-8")

def gemini_parts_request(parts, temperature=0.2, max_tokens=2400):
    key = get_key()
    if not key:
        return None, "GEMINI_API_KEY غير موجود في Streamlit Secrets."

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }
    model = "gemini-3.5-flash-lite"
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + model + ":generateContent?key=" + urllib.parse.quote(key, safe="")
    )
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode("utf-8"))
        candidates = data.get("candidates", [])
        if not candidates:
            return None, "Gemini لم يرجع نتيجة."
        parts_out = candidates[0].get("content", {}).get("parts", [])
        text = "\n".join(p.get("text","") for p in parts_out if p.get("text")).strip()
        return text or "لم يرجع Gemini نصًا.", None
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            msg = json.loads(raw).get("error", {}).get("message", raw)
        except Exception:
            msg = raw
        return None, f"Gemini رفض الطلب: {msg}"
    except Exception as e:
        return None, f"تعذر الاتصال بـ Gemini: {str(e)[:700]}"

def image_parts(image):
    buf = BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=92)
    return [{"inline_data": {"mime_type":"image/jpeg", "data":bytes_b64(buf.getvalue())}}]

def file_part(uploaded):
    return [{"inline_data": {"mime_type": uploaded.type, "data":bytes_b64(uploaded.getvalue())}}]

# ============================================================
# Modes
# ============================================================
MODES = {
    "🧠 تحليل ذكي": "حلل المحتوى بالكامل وحدد أهم المعلومات.",
    "📝 OCR استخراج النص": "استخرج كل النص الظاهر بدقة، واكتب [غير واضح] عند عدم القدرة على القراءة.",
    "🧾 فاتورة وإيصال": "استخرج البنود والكميات والأسعار والخصم والضريبة والإجمالي، دون اختلاق أرقام.",
    "📄 مستند وتلخيص": "اقرأ المستند واستخرج البيانات المهمة ثم قدم ملخصًا منظمًا.",
    "💻 تحليل كود": "اشرح الكود، الأخطاء والمشاكل الظاهرة، واقترح إصلاحات عملية.",
    "📊 تحليل رسم بياني": "حلل المحاور والقيم والاتجاهات والمقارنات دون اختلاق أرقام.",
    "🧮 حل مسألة": "اقرأ المسألة وحلها خطوة بخطوة مع القوانين والنتيجة النهائية.",
    "🔍 فحص التفاصيل": "افحص التفاصيل الصغيرة والنصوص والأرقام والرموز والأخطاء المرئية.",
    "🌍 ترجمة النص": "استخرج النص ثم ترجمه للغة المطلوبة مع الحفاظ على المعنى.",
    "📋 تحويل لجدول": "استخرج البيانات المنظمة من الصورة وحولها إلى جدول Markdown واضح."
}

with st.sidebar:
    st.header("⚙️ التحكم")
    language = st.selectbox("لغة النتيجة", ["العربية المصرية","العربية الفصحى","English"])
    mode = st.selectbox("نوع التحليل", list(MODES.keys()))
    extra = st.text_area("تعليمات إضافية", placeholder="مثال: ركز على الأسعار فقط...")
    target_lang = st.selectbox("لغة الترجمة", ["English","العربية","Français","Deutsch","Español"])
    st.caption("🔐 لا تضع مفتاح API داخل الكود أو GitHub.")

# ============================================================
# Input tabs: camera / image / PDF / audio
# ============================================================
tabs = st.tabs(["📸 كاميرا","🖼️ صورة","📄 PDF","🎙️ صوت"])

source_type = None
source_data = None
image = None

with tabs[0]:
    camera = st.camera_input("صوّر الآن")
    if camera:
        source_type = "image"
        source_data = camera
        image = ImageOps.exif_transpose(Image.open(camera))

with tabs[1]:
    img_upload = st.file_uploader(
        "ارفع صورة JPG / PNG / WEBP",
        type=["jpg","jpeg","png","webp"],
        key="image_upload"
    )
    if img_upload:
        source_type = "image"
        source_data = img_upload
        image = ImageOps.exif_transpose(Image.open(img_upload))

with tabs[2]:
    pdf_upload = st.file_uploader(
        "ارفع ملف PDF",
        type=["pdf"],
        key="pdf_upload"
    )
    if pdf_upload:
        source_type = "pdf"
        source_data = pdf_upload
        st.info("سيتم إرسال ملف PDF إلى Gemini لتحليله.")

with tabs[3]:
    audio_upload = st.file_uploader(
        "ارفع تسجيلًا صوتيًا",
        type=["wav","mp3","m4a","aac","ogg"],
        key="audio_upload"
    )
    if audio_upload:
        source_type = "audio"
        source_data = audio_upload
        st.info("سيحاول Gemini فهم الكلام من التسجيل.")

# ============================================================
# Analyze
# ============================================================
if source_type:
    if image:
        st.image(image, caption="المصدر", width="stretch")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🚀 التحليل")
    analyze = st.button("🔎 ابدأ التحليل", type="primary", width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)

    if analyze:
        base_prompt = f"""
أنت AI Reality Scanner ULTIMATE.
النمط: {mode}
اللغة: {language}

المطلوب:
{MODES[mode]}

قواعد:
- لا تخترع معلومات.
- إذا كان شيء غير واضح قل غير واضح.
- لا تدّعي هوية الأشخاص.
- لا تدّعي تحديد موقع دقيق من الصورة وحدها.
- اجعل النتيجة عملية ومنظمة.

اكتب:
### 👁️ ماذا أرى؟
### 🧠 التحليل
### 📌 أهم التفاصيل
### 🚀 ماذا أفعل الآن؟
### 💡 ملاحظات

تعليمات إضافية:
{extra or "لا توجد."}
"""

        if mode == "🌍 ترجمة النص":
            base_prompt += f"\nترجم النص المستخرج إلى: {target_lang}."

        if mode == "📋 تحويل لجدول":
            base_prompt += "\nاستخدم جدول Markdown عند وجود بيانات منظمة."

        if source_type == "image":
            parts = [{"text": base_prompt}] + image_parts(image)
        elif source_type == "pdf":
            parts = [{"text": base_prompt + "\nحلل ملف PDF كاملًا، واذكر الصفحات أو الأقسام عندما يكون ذلك ممكنًا."}] + file_part(source_data)
        else:
            parts = [{
                "text": base_prompt + "\nهذا تسجيل صوتي. استخرج الكلام المهم ثم حلله حسب النمط."
            }, {
                "inline_data": {
                    "mime_type": source_data.type,
                    "data": bytes_b64(source_data.getvalue())
                }
            }]

        with st.spinner("🤖 جاري التحليل..."):
            result, error = gemini_parts_request(parts)

        if error:
            st.error(error)
        else:
            st.session_state.analysis = result
            st.session_state.last_source = source_type
            st.session_state.chat = []
            st.session_state.history.insert(0, {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "mode": mode,
                "type": source_type,
                "result": result
            })
            st.session_state.history = st.session_state.history[:20]

# ============================================================
# Result
# ============================================================
if st.session_state.analysis:
    result = st.session_state.analysis
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🧠 النتيجة")
    st.markdown(result)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "⬇️ حفظ TXT",
            data=result,
            file_name=f"ai_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            width="stretch"
        )
    with col2:
        # Browser print is more reliable than a PDF dependency in Streamlit.
        st.download_button(
            "📥 حفظ تقرير Markdown",
            data=f"# AI Reality Scanner Report\n\n{result}",
            file_name="ai_reality_scanner_report.md",
            mime="text/markdown",
            width="stretch"
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # Translation of the existing result
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🌍 ترجمة النتيجة")
    if st.button("ترجم النتيجة", width="stretch"):
        trans_prompt = f"ترجم النص التالي إلى {target_lang} بدقة، مع الحفاظ على التنسيق والمعنى:\n\n{result}"
        translated, error = gemini_parts_request([{"text": trans_prompt}], temperature=0.1)
        if error:
            st.error(error)
        else:
            st.markdown(translated)
            st.download_button(
                "⬇️ حفظ الترجمة",
                data=translated,
                file_name="translated_result.txt",
                mime="text/plain"
            )
    st.markdown("</div>", unsafe_allow_html=True)

    # Chat
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("💬 Chat مع نفس المحتوى")
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    q = st.chat_input("اسأل عن الصورة أو الـPDF أو النتيجة...")
    if q:
        st.session_state.chat.append({"role":"user","content":q})
        context = "\n".join(
            f'{m["role"]}: {m["content"]}'
            for m in st.session_state.chat[-8:]
        )
        prompt = f"""
أنت مساعد AI Reality Scanner.
المحتوى الذي تم تحليله:
{result}

المحادثة:
{context}

أجب عن سؤال المستخدم اعتمادًا على المحتوى المتاح فقط.
إذا لم توجد المعلومة قل ذلك بوضوح.
سؤال المستخدم: {q}
"""
        # Chat can reuse the original image when available.
        parts = [{"text": prompt}]
        if image is not None:
            parts += image_parts(image)
        with st.spinner("🤖 بجهز الإجابة..."):
            answer, error = gemini_parts_request(parts)
        answer = answer if not error else error
        st.session_state.chat.append({"role":"assistant","content":answer})
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# History / share
# ============================================================
with st.expander("🗂️ سجل التحليلات"):
    if not st.session_state.history:
        st.write("لسه مفيش تحليلات محفوظة في الجلسة.")
    else:
        for i, item in enumerate(st.session_state.history):
            st.markdown(f"**{i+1}. {item['time']} — {item['mode']} — {item['type']}**")
            st.text(item["result"][:500] + ("..." if len(item["result"]) > 500 else ""))
            st.download_button(
                "⬇️ تنزيل",
                data=item["result"],
                file_name=f"scan_history_{i+1}.txt",
                mime="text/plain",
                key=f"hist_{i}"
            )

with st.expander("🔗 مشاركة النتيجة"):
    st.caption("تقدر تستخدم زر المشاركة في المتصفح أو تنسخ النتيجة. سجل التحليلات هنا محفوظ داخل جلسة التطبيق فقط.")
    if st.session_state.analysis:
        st.code(st.session_state.analysis[:3000], language="markdown")

st.markdown("""
<div style="text-align:center;margin-top:45px;color:#64748b;">
AI Reality Scanner ULTIMATE ALL-IN-ONE • Gemini Vision
</div>
""", unsafe_allow_html=True)
