import streamlit as st
import pandas as pd
import os
import re
import requests
from datetime import datetime, date
from fpdf import FPDF
from gtts import gTTS

# ====== CONFIG ======
USERS_CSV = "users.csv"
HISTORY_CSV = "history.csv"
FREE_LIMIT = 3
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]  # Replace with your actual Groq API key
client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "llama3-8b-8192"

# ====== INITIAL SETUP ======
if not os.path.exists(USERS_CSV):
    pd.DataFrame(columns=["email", "password", "role", "used_today", "last_used_date"]).to_csv(USERS_CSV, index=False)
else:
    df = pd.read_csv(USERS_CSV)
    if "last_used_date" not in df.columns:
        df["last_used_date"] = str(date.today())
        df.to_csv(USERS_CSV, index=False)

if not os.path.exists(HISTORY_CSV):
    pd.DataFrame(columns=["email", "timestamp", "role_target", "score", "feedback", "rewritten"]).to_csv(HISTORY_CSV, index=False)

# ====== STYLING ======
st.set_page_config(page_title="AI Resume Feedback", layout="centered")
st.markdown("""
    <style>
        .title { color: #2c3e50; font-size: 2.8rem; font-weight: bold; text-align: center; }
        .stApp { background-color: #f4f9fd; padding: 2rem; }
        .stButton > button { background-color: #4CAF50; color: white; border-radius: 8px; }
        .stDownloadButton > button { background-color: #3498db; color: white; }
    </style>
""", unsafe_allow_html=True)
st.markdown("<h1 class='title'>📄 AI Resume Feedback Bot</h1>", unsafe_allow_html=True)

# ====== AUTHENTICATION ======
def login_user(email, password):
    df = pd.read_csv(USERS_CSV)
    user = df[(df.email == email) & (df.password == password)]
    if not user.empty:
        return user.iloc[0].to_dict()
    return None

def signup_user(email, password):
    df = pd.read_csv(USERS_CSV)
    if email in df.email.values:
        return False
    new_user = pd.DataFrame([[email, password, "user", 0, str(date.today())]],
                            columns=["email", "password", "role", "used_today", "last_used_date"])
    new_user.to_csv(USERS_CSV, mode='a', header=False, index=False)
    return True

if "user" not in st.session_state:
    st.session_state.user = None

with st.sidebar:
    st.header("🔐 Login / Signup")
    auth_mode = st.radio("Select Mode", ["Login", "Signup"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if auth_mode == "Login":
        if st.button("Login"):
            user = login_user(email, password)
            if user:
                st.session_state.user = user
                st.success(f"Welcome, {email}")
            else:
                st.error("Invalid credentials")
    else:
        if st.button("Signup"):
            if signup_user(email, password):
                st.success("Account created. Please log in.")
            else:
                st.error("Email already exists.")
# ====== UTILITIES ======
import PyPDF2
import docx2txt

def extract_text(file, filename):
    if filename.endswith(".pdf"):
        reader = PyPDF2.PdfReader(file)
        return " ".join([page.extract_text() or "" for page in reader.pages])
    elif filename.endswith(".docx"):
        return docx2txt.process(file)
    return ""

def text_to_audio(text):
    tts = gTTS(text=text, lang='en')
    audio_path = f"audio_{datetime.now().timestamp()}.mp3"
    tts.save(audio_path)
    return audio_path

def export_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in text.split("\n"):
        pdf.multi_cell(0, 10, line)
    filename = f"feedback_{datetime.now().timestamp()}.pdf"
    pdf.output(filename)
    return filename

def ask_groq(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    res = requests.post(url, headers=headers, json=data)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]

def check_usage(email):
    df = pd.read_csv(USERS_CSV)
    row = df[df.email == email].index
    if len(row) == 0:
        return 0
    last = df.loc[row, "last_used_date"].values[0]
    if str(last) != str(date.today()):
        df.loc[row, "used_today"] = 0
        df.loc[row, "last_used_date"] = str(date.today())
        df.to_csv(USERS_CSV, index=False)
    return df.loc[row, "used_today"].values[0]

def increment_usage(email):
    df = pd.read_csv(USERS_CSV)
    row = df[df.email == email].index
    df.loc[row, "used_today"] += 1
    df.to_csv(USERS_CSV, index=False)

# ====== MAIN APP ======
if st.session_state.user:
    role = st.session_state.user["role"]
    email = st.session_state.user["email"]
    usage = check_usage(email)

    st.success(f"Logged in as: {email} ({role}) | Used today: {usage}/{FREE_LIMIT if role == 'user' else '∞'}")

    if role == "user" and usage >= FREE_LIMIT:
        st.warning("🚫 Daily usage limit reached. Please upgrade to premium.")
        st.stop()

    uploaded = st.file_uploader("📎 Upload your Resume", type=["pdf", "docx"])
    target = st.text_input("🎯 Target Role (e.g., Data Analyst, Software Engineer)")
    reviewer_mode = st.selectbox("🧠 Reviewer Mode", ["General", "Recruiter", "Technical", "Startup", "Academic"])
    send_email_toggle = st.checkbox("📧 Email me the feedback (optional)")
    voice_toggle = st.checkbox("🔊 Convert feedback to voice")

    if uploaded and st.button("🧠 Analyze Resume"):
        raw_text = extract_text(uploaded, uploaded.name)
        prompt = f"""
You are a {reviewer_mode} reviewing a resume for the role of {target}. Please provide:
1. Strengths
2. Areas for Improvement
3. Specific Suggestions
4. Score out of 100
5. Summary improvement
6. Section-wise suggestions
Then rewrite the resume in a clean, ATS-friendly format.

Resume:
{raw_text}
"""

        with st.spinner("Analyzing your resume using Groq's LLaMA3..."):
            gpt_response = ask_groq(prompt)

        parts = gpt_response.split("Rewrite:")
        feedback = parts[0].strip()
        rewritten = parts[1].strip() if len(parts) > 1 else "(Could not extract rewritten resume)"
        score_match = re.search(r"score.*?(\d{1,3})", feedback, re.IGNORECASE)
        score = int(score_match.group(1)) if score_match else None

        st.markdown("### 🧠 Feedback")
        st.markdown(feedback)

        if score:
            st.progress(score / 100)
            st.success(f"📊 Score: {score}/100")

        st.markdown("### 📝 Rewritten Resume")
        st.text_area("Rewritten Resume", rewritten, height=300)

        if voice_toggle:
            audio_path = text_to_audio(feedback)
            st.audio(audio_path)
            os.remove(audio_path)

        pdf_path = export_pdf(feedback)
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Download Feedback PDF", f, file_name="feedback.pdf")
        os.remove(pdf_path)

        # Email logic placeholder
        if send_email_toggle:
            st.info("📧 Email sending not yet configured. Add SMTP for real delivery.")

        # Save to history
        pd.DataFrame([[email, datetime.now(), target, score, feedback, rewritten]],
                     columns=["email", "timestamp", "role_target", "score", "feedback", "rewritten"]).to_csv(HISTORY_CSV, mode='a', header=False, index=False)
        increment_usage(email)

    # ====== USER HISTORY ======
    st.markdown("### 📁 Resume Feedback History")
    history = pd.read_csv(HISTORY_CSV)
    user_history = history[history.email == email].sort_values("timestamp", ascending=False)
    st.dataframe(user_history)

    delete_id = st.text_input("🗑️ Enter timestamp to delete record")
    if st.button("❌ Delete Record") and delete_id:
        history = history[~((history.email == email) & (history.timestamp == delete_id))]
        history.to_csv(HISTORY_CSV, index=False)
        st.success("Record deleted successfully.")

    # ====== ADMIN DASHBOARD ======
    if role == "admin":
        st.markdown("### 🛠️ Admin Dashboard")
        all_users = pd.read_csv(USERS_CSV)
        all_hist = pd.read_csv(HISTORY_CSV)
        st.metric("👥 Total Users", len(all_users))
        st.metric("📄 Total Resumes Analyzed", len(all_hist))
        if len(all_hist) > 0:
            st.metric("📈 Avg Score", round(all_hist.score.dropna().astype(float).mean(), 2))
            st.bar_chart(all_hist.role_target.value_counts())

else:
    st.info("🔐 Please log in to continue.")
