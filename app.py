# app.py – Part 1

import streamlit as st
from streamlit_option_menu import option_menu
import firebase_admin
from firebase_admin import credentials, firestore, auth
import pyrebase
from datetime import datetime
import base64
import os
import random
import string
from gtts import gTTS
import tempfile
from io import BytesIO
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ========== 💡 Groq GPT Setup ==========
from utils.groq_api import analyze_resume, rewrite_resume, ats_score  # Placeholder for Groq API helper functions
from utils.file_utils import extract_text_from_pdf, extract_text_from_docx  # Resume parsing utils

# ========== 🎨 Streamlit Page Settings ==========
st.set_page_config(page_title="AI Resume Feedback Bot",
                   page_icon="🧠", layout="wide")

# ========== 🎨 Custom Styled Background ==========
def add_background_color():
    st.markdown("""
        <style>
            body {
                background-color: #f1f6f9;
            }
            .stButton>button {
                color: white;
                background-color: #3b5998;
                font-weight: bold;
            }
            .stTextInput>div>div>input {
                background-color: #ffffff;
                color: #000000;
            }
            .main > div {
                padding: 1rem;
                background-color: #ffffff;
                border-radius: 10px;
                box-shadow: 0px 0px 10px #ccc;
            }
            .css-1v0mbdj {
                font-size: 18px;
                color: #111;
                font-weight: 600;
            }
        </style>
    """, unsafe_allow_html=True)

add_background_color()

# ========== 🔐 Firebase Admin & Config ==========
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")  # Upload your Firebase private key JSON here
    firebase_admin.initialize_app(cred)

firebase_config = {
    "apiKey": "YOUR_API_KEY",
    "authDomain": "your-project.firebaseapp.com",
    "databaseURL": "",
    "projectId": "your-project-id",
    "storageBucket": "your-project.appspot.com",
    "messagingSenderId": "XXXXXXX",
    "appId": "APP_ID",
    "measurementId": "MEASURE_ID"
}

firebase = pyrebase.initialize_app(firebase_config)
auth_fb = firebase.auth()
db = firestore.client()

# ========== 🔄 Session State Setup ==========
if 'page' not in st.session_state:
    st.session_state.page = "login"
if 'user' not in st.session_state:
    st.session_state.user = None
if 'email' not in st.session_state:
    st.session_state.email = ""
if 'role' not in st.session_state:
    st.session_state.role = "user"
if 'feedback_history' not in st.session_state:
    st.session_state.feedback_history = []
if 'selected_resume_id' not in st.session_state:
    st.session_state.selected_resume_id = None
if 'show_dashboard' not in st.session_state:
    st.session_state.show_dashboard = False

# ========== 🔒 Encrypt Password ==========
def encrypt_password(password):
    return base64.b64encode(password.encode()).decode()

def decrypt_password(encoded):
    return base64.b64decode(encoded).decode()

# ========== 🧹 Utility ==========
def reset_login_fields():
    st.session_state["login_email"] = ""
    st.session_state["login_password"] = ""

def reset_signup_fields():
    st.session_state["signup_email"] = ""
    st.session_state["signup_password"] = ""
    st.session_state["signup_name"] = ""
    st.session_state["signup_phone"] = ""



# app.py – Part 2

# ========== 🔐 Login/Signup UI ==========
def login_ui():
    st.markdown("## 🔐 Login to Your Account")
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("📧 Email", key="login_email")
        password = st.text_input("🔑 Password", type="password", key="login_password")
        submitted = st.form_submit_button("Login")

        if submitted:
            try:
                user = auth_fb.sign_in_with_email_and_password(email, password)
                st.success("✅ Logged in successfully!")
                st.session_state.user = user
                st.session_state.email = email
                st.session_state.page = "dashboard"
                st.experimental_rerun()
            except Exception as e:
                st.error("❌ Login failed. Please check your credentials.")

def signup_ui():
    st.markdown("## ✍️ Create New Account")
    with st.form("signup_form", clear_on_submit=False):
        name = st.text_input("🧑 Full Name", key="signup_name")
        email = st.text_input("📧 Email", key="signup_email")
        phone = st.text_input("📱 Phone Number", key="signup_phone")
        password = st.text_input("🔐 Password", type="password", key="signup_password")
        submitted = st.form_submit_button("Sign Up")

        if submitted:
            try:
                user = auth_fb.create_user_with_email_and_password(email, password)
                uid = user['localId']
                db.collection("users").document(uid).set({
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "created_at": datetime.now().isoformat()
                })
                st.success("🎉 Account created! Please log in.")
                reset_signup_fields()
                st.session_state.page = "login"
                st.experimental_rerun()
            except Exception as e:
                st.error("❌ Signup failed. Email might already be in use.")

def login_signup_page():
    with st.container():
        tab1, tab2 = st.tabs(["🔑 Login", "🆕 Sign Up"])
        with tab1:
            login_ui()
        with tab2:
            signup_ui()

# ========== 🧭 Page Router ==========
if st.session_state.page == "login":
    st.markdown("## 🤖 AI Resume Feedback Bot")
    st.info("Please login or create an account to continue.")
    login_signup_page()
elif st.session_state.page == "dashboard":
    if st.session_state.user:
        st.markdown(f"### 👋 Welcome, `{st.session_state.email}`")
    else:
        st.warning("You are not logged in. Redirecting...")
        st.session_state.page = "login"
        st.experimental_rerun()




# app.py – Part 3

# ========== 🧠 Dashboard UI ==========
def dashboard_ui():
    st.markdown("## 🧠 AI Resume Feedback Dashboard")
    st.markdown("Upload your resume and enter the role you're targeting.")

    col1, col2 = st.columns([2, 1])
    with col1:
        target_role = st.text_input("🎯 Target Role", key="target_role")
    with col2:
        analyze_btn = st.button("🔍 Analyze Resume", key="analyze_btn")

    uploaded_file = st.file_uploader("📄 Upload your resume (.pdf or .docx)", type=["pdf", "docx"], key="resume_uploader")

    # Store uploaded file in session
    if uploaded_file:
        st.session_state.resume_file = uploaded_file
        st.success("✅ Resume uploaded successfully!")

    # Feedback Buttons (to be wired in Part 4)
    colA, colB, colC, colD = st.columns(4)
    with colA:
        if st.button("📝 Rewrite Resume", key="rewrite_btn"):
            st.session_state.rewrite_triggered = True
    with colB:
        if st.button("🔈 Audio Tips", key="audio_btn"):
            st.session_state.audio_triggered = True
    with colC:
        if st.button("📧 Send to Email", key="email_btn"):
            st.session_state.email_triggered = True
    with colD:
        if st.button("🧹 Clear Feedback", key="clear_btn"):
            st.session_state.pop("resume_file", None)
            st.session_state.pop("feedback", None)
            st.session_state.pop("score", None)
            st.success("🧼 Cleared feedback and resume.")

    # Feedback Display Area
    if "feedback" in st.session_state:
        st.markdown("### 📊 AI Feedback")
        st.markdown(st.session_state.feedback)
        st.progress(st.session_state.get("score", 50))

    if "rewritten_resume" in st.session_state:
        st.markdown("### ✨ AI Rewritten Resume")
        st.text_area("Rewritten Content", st.session_state.rewritten_resume, height=300)

# ========== 🧭 Dashboard Routing ==========
if st.session_state.page == "dashboard":
    if st.session_state.get("user"):
        dashboard_ui()
    else:
        st.warning("⚠️ Not authenticated. Redirecting to login...")
        st.session_state.page = "login"
        st.experimental_rerun()




# app.py – Part 4

import os
import docx2txt
import PyPDF2
import requests

# ========== 📤 Resume Text Extractor ==========
def extract_resume_text(file):
    text = ""
    if file.name.endswith(".pdf"):
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    elif file.name.endswith(".docx"):
        text = docx2txt.process(file)
    return text.strip()

# ========== 🤖 Get Feedback from Groq ==========
def get_ai_feedback(resume_text, target_role):
    prompt = f"""You're an expert resume reviewer. Analyze the resume below for the role of {target_role}.

Resume:
{resume_text}

Give:
- Summary
- Strengths
- Weaknesses
- Suggestions
- Score out of 100"""

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
    )

    result = response.json()
    feedback = result['choices'][0]['message']['content']

    # Extract score (naive parsing)
    score_line = [line for line in feedback.splitlines() if "score" in line.lower()]
    score = 60
    for line in score_line:
        digits = [int(s) for s in line.split() if s.isdigit()]
        if digits:
            score = digits[0]
            break

    return feedback, min(score, 100)

# ========== 🔍 Handle Resume Analysis ==========
if st.session_state.page == "dashboard" and st.session_state.get("resume_file") and st.session_state.get("target_role") and st.session_state.get("analyze_btn"):

    resume_text = extract_resume_text(st.session_state.resume_file)
    if resume_text:
        with st.spinner("Analyzing with Groq..."):
            feedback, score = get_ai_feedback(resume_text, st.session_state.target_role)
            st.session_state.feedback = feedback
            st.session_state.score = score
            st.success("✅ Feedback generated!")
            st.rerun()
    else:
        st.error("❌ Could not extract text from the resume.")




# --- Resume Rewriting with GPT ---
def rewrite_resume(resume_text, target_role):
    prompt = f"""You're an expert resume writer. Rewrite the following resume to better fit the target role of '{target_role}'.
Make it more impressive, concise, and tailored for the industry.

Resume:
{resume_text}

Rewritten Resume:"""
    rewritten = call_gpt_api(prompt)
    return rewritten

# --- Generate and Play Audio Tips using gTTS ---
def generate_audio_tips(text):
    try:
        tts = gTTS(text=text, lang='en')
        audio_path = f"audio_tips_{uuid.uuid4().hex}.mp3"
        tts.save(audio_path)
        return audio_path
    except Exception as e:
        st.error("❌ Failed to generate audio tips.")
        return None

# --- Email Feedback via SMTP Placeholder ---
def send_email_feedback(receiver_email, feedback_text):
    try:
        # For real deployment: use environment variables securely!
        smtp_server = "smtp.gmail.com"
        port = 587
        sender_email = os.getenv("SMTP_EMAIL")
        password = os.getenv("SMTP_PASSWORD")  # app password or OAuth token

        msg = EmailMessage()
        msg.set_content(feedback_text)
        msg["Subject"] = "🧠 Your AI Resume Feedback"
        msg["From"] = sender_email
        msg["To"] = receiver_email

        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)
        return True
    except Exception as e:
        st.warning("📬 Email placeholder active. Configure SMTP to enable this.")
        return False




        # ===============================
        # 📂 Resume Feedback History Tab
        # ===============================
        elif dashboard_menu == "📂 Feedback History":
            st.subheader("📂 Your Resume Feedback History")
            user_feedbacks = feedback_collection.find({"user_id": st.session_state.logged_user["_id"]})
            for feedback in user_feedbacks:
                with st.expander(f"📄 {feedback['timestamp']} — {feedback['target_role']}"):
                    st.markdown("**Feedback:**")
                    st.write(feedback["feedback"])
                    if "audio_path" in feedback and os.path.exists(feedback["audio_path"]):
                        st.audio(feedback["audio_path"], format="audio/mp3")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"🗑️ Delete Feedback {feedback['_id']}", key=f"delete_f{feedback['_id']}"):
                            feedback_collection.delete_one({"_id": feedback["_id"]})
                            st.success("Feedback deleted.")
                            st.experimental_rerun()
                    with col2:
                        if st.button(f"🗑️ Delete Audio {feedback['_id']}", key=f"delete_a{feedback['_id']}"):
                            if os.path.exists(feedback["audio_path"]):
                                os.remove(feedback["audio_path"])
                                st.success("Audio deleted.")
                                st.experimental_rerun()

        # ========================
        # 👑 Admin Dashboard
        # ========================
        elif dashboard_menu == "👑 Admin Dashboard":
            st.subheader("👑 Admin Dashboard")

            total_users = user_collection.count_documents({})
            total_feedbacks = feedback_collection.count_documents({})
            recent_feedbacks = list(feedback_collection.find().sort("timestamp", -1).limit(5))

            col1, col2 = st.columns(2)
            with col1:
                st.metric("👥 Total Users", total_users)
            with col2:
                st.metric("📄 Total Feedbacks", total_feedbacks)

            st.markdown("### 🔍 Recent Feedback Activity")
            for fb in recent_feedbacks:
                st.write(f"• {fb['timestamp']} | {fb.get('target_role', 'N/A')}")

            st.markdown("### 📊 Feedback Per Role")
            pipeline = [
                {"$group": {"_id": "$target_role", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            role_stats = list(feedback_collection.aggregate(pipeline))
            if role_stats:
                import matplotlib.pyplot as plt
                roles = [r["_id"] for r in role_stats]
                counts = [r["count"] for r in role_stats]
                fig, ax = plt.subplots()
                ax.barh(roles, counts, color='skyblue')
                ax.set_xlabel("Feedback Count")
                ax.set_title("📊 Feedbacks by Target Role")
                st.pyplot(fig)

        # ================
        # 🚪 Logout Option
        # ================
        if st.button("🔚 Logout"):
            st.session_state.logged_in = False
            st.session_state.logged_user = None
            st.success("Logged out successfully!")
            st.rerun()
