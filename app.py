import streamlit as st
import os
import sqlite3
import base64
import random
import string
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from PyPDF2 import PdfReader
import docx
from groq import Groq
from gtts import gTTS
import time
import matplotlib.pyplot as plt

# Set page config and hide warnings
st.set_page_config(page_title="AI Resume Feedback Bot", layout="wide")
st.markdown("<style>footer {visibility: hidden;}</style>", unsafe_allow_html=True)

# Groq API key
groq_api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=groq_api_key)

# SQLite database setup
conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT UNIQUE,
    phone TEXT,
    password TEXT,
    is_admin INTEGER DEFAULT 0
)''')
c.execute('''CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT,
    role TEXT,
    original_resume TEXT,
    ai_feedback TEXT,
    rewritten_resume TEXT,
    audio_file TEXT,
    timestamp TEXT
)''')
conn.commit()

# Helper Functions
def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email, otp):
    try:
        smtp_host = "smtp.example.com"  # Placeholder SMTP
        smtp_port = 587
        smtp_user = "your@email.com"
        smtp_pass = "password"

        msg = MIMEText(f"Your OTP is: {otp}")
        msg["Subject"] = "Your OTP for Resume Bot"
        msg["From"] = smtp_user
        msg["To"] = email

        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [email], msg.as_string())
        server.quit()
    except Exception as e:
        st.error(f"Email sending failed: {e}")

def read_pdf(file):
    pdf_reader = PdfReader(file)
    return "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])

def read_docx(file):
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

# App State
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

# Title UI
st.markdown("<h1 style='text-align: center; color: #00BFFF;'>🚀 AI Resume Feedback Bot</h1>", unsafe_allow_html=True)


def login_signup_ui():
    tabs = st.tabs(["🔐 Login", "📝 Signup", "🔁 Forgot Password", "🔒 Change Password"])

    with tabs[0]:
        st.subheader("🔐 Login to your account")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            c.execute("SELECT * FROM users WHERE email=? AND password=?", (login_email, login_password))
            user = c.fetchone()
            if user:
                st.success(f"Welcome back, {user[1]}! 🎉")
                st.session_state.logged_in = True
                st.session_state.user_email = login_email
                st.experimental_rerun()
            else:
                st.error("Invalid email or password.")

    with tabs[1]:
        st.subheader("📝 Create a new account")
        signup_name = st.text_input("Name", key="signup_name")
        signup_email = st.text_input("Email", key="signup_email")
        signup_phone = st.text_input("Phone", key="signup_phone")
        signup_password = st.text_input("Password", type="password", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm")
        if st.button("Signup"):
            if signup_password != confirm_password:
                st.warning("Passwords do not match.")
            else:
                try:
                    c.execute("INSERT INTO users (name, email, phone, password) VALUES (?, ?, ?, ?)",
                              (signup_name, signup_email, signup_phone, signup_password))
                    conn.commit()
                    st.success("Signup successful. Please login.")
                    st.experimental_rerun()
                except sqlite3.IntegrityError:
                    st.error("Email already exists. Please login.")

    with tabs[2]:
        st.subheader("🔁 Forgot Password")
        forgot_email = st.text_input("Enter your registered email", key="forgot_email")
        if st.button("Send OTP"):
            otp = generate_otp()
            st.session_state.generated_otp = otp
            st.session_state.otp_email = forgot_email
            send_otp_email(forgot_email, otp)
            st.info("OTP sent to your email.")
        if "generated_otp" in st.session_state:
            entered_otp = st.text_input("Enter OTP")
            new_pass = st.text_input("New Password", type="password")
            confirm_pass = st.text_input("Confirm New Password", type="password")
            if st.button("Reset Password"):
                if entered_otp == st.session_state.generated_otp and new_pass == confirm_pass:
                    c.execute("UPDATE users SET password=? WHERE email=?", (new_pass, st.session_state.otp_email))
                    conn.commit()
                    st.success("Password updated successfully. Please login.")
                    del st.session_state.generated_otp
                    del st.session_state.otp_email
                else:
                    st.error("OTP mismatch or passwords do not match.")

    with tabs[3]:
        st.subheader("🔒 Change Password")
        change_email = st.text_input("Email", key="change_email")
        current_pass = st.text_input("Current Password", type="password")
        new_pass = st.text_input("New Password", type="password")
        confirm_new_pass = st.text_input("Confirm New Password", type="password")
        if st.button("Change Password"):
            c.execute("SELECT * FROM users WHERE email=? AND password=?", (change_email, current_pass))
            if c.fetchone():
                if new_pass == confirm_new_pass:
                    c.execute("UPDATE users SET password=? WHERE email=?", (new_pass, change_email))
                    conn.commit()
                    st.success("Password changed successfully.")
                else:
                    st.warning("New passwords do not match.")
            else:
                st.error("Current email/password is incorrect.")

# If not logged in, show login/signup page
if not st.session_state.logged_in:
    login_signup_ui()


# 🌈 Custom dashboard after login
if st.session_state.logged_in:
    st.markdown("## 🧠 AI Resume Feedback Dashboard")
    st.sidebar.markdown("### 🌟 Navigation")
    dashboard_menu = st.sidebar.radio(
        "Go to",
        ["📤 Upload Resume", "📂 Feedback History", "🧠 AI Rewriter", "🔊 Voice Tips", "📧 Email Feedback", "📈 Admin Dashboard", "🔓 Logout"],
        key="menu",
    )

    st.markdown("---")

    if dashboard_menu == "📤 Upload Resume":
        st.subheader("📤 Upload your Resume (PDF/DOCX)")
        uploaded_file = st.file_uploader("Choose your resume file", type=["pdf", "docx"], key="resume_upload")

        target_role = st.text_input("🎯 Target Role (e.g., Software Engineer)", key="target_role")

        if st.button("🔍 Analyze Resume"):
            if uploaded_file and target_role:
                file_ext = uploaded_file.name.split(".")[-1]
                file_path = f"temp_resume.{file_ext}"
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.read())
                resume_text = extract_text_from_file(file_path)

                # Store in session
                st.session_state.resume_text = resume_text
                st.session_state.target_role = target_role

                st.success("Resume uploaded and extracted successfully ✅")
                st.markdown("Click other tabs for feedback, rewrite, audio tips, or email delivery.")
            else:
                st.warning("Please upload your resume and enter target role.")


    elif dashboard_menu == "📂 Feedback History":
        st.subheader("📂 Your Feedback History")
        user_folder = f"user_uploads/{st.session_state.current_user}"
        if os.path.exists(user_folder):
            files = os.listdir(user_folder)
            if files:
                for file in files:
                    with open(os.path.join(user_folder, file), "r", encoding="utf-8") as f:
                        content = f.read()
                        st.markdown(f"**📝 {file}**")
                        st.code(content, language="markdown")
                        if st.button(f"🗑 Delete {file}", key=f"delete_{file}"):
                            os.remove(os.path.join(user_folder, file))
                            st.success(f"{file} deleted!")
                            st.experimental_rerun()
            else:
                st.info("No feedback files found.")
        else:
            st.info("No upload history available.")

    elif dashboard_menu == "🧠 AI Rewriter":
        st.subheader("🧠 Rewritten Resume (AI Generated)")
        if "resume_text" in st.session_state and "target_role" in st.session_state:
            rewritten_resume = generate_rewritten_resume(st.session_state.resume_text, st.session_state.target_role)
            st.text_area("✍️ Rewritten Resume", value=rewritten_resume, height=400)
            if st.download_button("📥 Download Rewritten Resume", data=rewritten_resume, file_name="Rewritten_Resume.txt"):
                st.success("Rewritten resume downloaded.")
        else:
            st.warning("Please upload your resume and target role first.")

    elif dashboard_menu == "🔊 Voice Tips":
        st.subheader("🔊 Audio Resume Feedback")
        if "resume_text" in st.session_state and "target_role" in st.session_state:
            voice_feedback = generate_feedback(st.session_state.resume_text, st.session_state.target_role)
            tts = gTTS(text=voice_feedback, lang="en")
            audio_path = f"feedback_{st.session_state.current_user}.mp3"
            tts.save(audio_path)
            st.audio(audio_path)
            if st.button("🗑 Delete Audio"):
                os.remove(audio_path)
                st.success("Audio deleted.")
        else:
            st.warning("Upload resume and enter target role to get audio feedback.")

    elif dashboard_menu == "📧 Email Feedback":
        st.subheader("📧 Send Feedback to Email")
        if "resume_text" in st.session_state and "target_role" in st.session_state:
            feedback_email = st.text_input("Enter your email address")
            if st.button("📨 Send via Email"):
                if feedback_email:
                    st.info("📧 Sending email... (Placeholder)")
                    st.success(f"Feedback sent to {feedback_email} (SMTP logic can be added here)")
                else:
                    st.warning("Please enter an email address.")
        else:
            st.warning("Upload resume and enter target role to send feedback.")


    elif dashboard_menu == "📊 Admin Dashboard":
        st.subheader("📊 Admin Dashboard")
        if st.session_state.current_user == "admin":
            all_users = list_user_history()
            user_counts = len(all_users)
            st.markdown(f"### 👥 Total Users: `{user_counts}`")
            st.bar_chart({"Uploads": [len(get_user_files(u)) for u in all_users]})
            for user in all_users:
                st.markdown(f"**🧑 User: `{user}`**")
                user_files = get_user_files(user)
                if user_files:
                    for f in user_files:
                        st.markdown(f"- 📄 `{f}`")
                else:
                    st.info("No uploads yet.")
        else:
            st.warning("You must be admin to view this section.")

    elif dashboard_menu == "🔒 Change Password":
        st.subheader("🔒 Change Your Password")
        current_pass = st.text_input("Current Password", type="password", key="change_current")
        new_pass = st.text_input("New Password", type="password", key="change_new")
        confirm_pass = st.text_input("Confirm New Password", type="password", key="change_confirm")
        if st.button("✅ Update Password"):
            if current_pass == users_db[st.session_state.current_user]["password"]:
                if new_pass == confirm_pass:
                    users_db[st.session_state.current_user]["password"] = new_pass
                    st.success("✅ Password updated successfully.")
                else:
                    st.error("❌ New passwords do not match.")
            else:
                st.error("❌ Current password is incorrect.")

    elif dashboard_menu == "❓ Forgot Password":
        st.subheader("❓ Forgot Password")
        recovery_method = st.radio("Choose recovery method", ["📧 Email", "📱 Phone OTP"])
        if recovery_method == "📧 Email":
            email = st.text_input("Enter your registered email")
            if st.button("Send Reset Link"):
                st.info(f"📨 Reset link sent to {email} (Placeholder)")
        else:
            phone = st.text_input("Enter your registered phone number")
            if st.button("Send OTP"):
                st.info(f"📱 OTP sent to {phone} (Placeholder)")
            otp = st.text_input("Enter OTP")
            new_pass = st.text_input("Enter New Password", type="password")
            confirm_pass = st.text_input("Confirm New Password", type="password")
            if st.button("Reset Password"):
                if new_pass == confirm_pass:
                    st.success("✅ Password reset (simulated).")
                else:
                    st.error("❌ Passwords do not match.")

    elif dashboard_menu == "🚪 Logout":
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.success("✅ Logged out successfully.")
        st.experimental_rerun()


# ========== UTILITY FUNCTIONS ==========

def save_user_file(username, filename, feedback, rewritten_text):
    user_dir = os.path.join("user_uploads", username)
    os.makedirs(user_dir, exist_ok=True)

    base_name = os.path.splitext(filename)[0]
    with open(os.path.join(user_dir, f"{base_name}_feedback.txt"), "w", encoding="utf-8") as f:
        f.write(feedback)

    with open(os.path.join(user_dir, f"{base_name}_rewritten.txt"), "w", encoding="utf-8") as f:
        f.write(rewritten_text)


def get_user_files(username):
    user_dir = os.path.join("user_uploads", username)
    if not os.path.exists(user_dir):
        return []
    return [f for f in os.listdir(user_dir) if f.endswith("_feedback.txt")]


def delete_user_file(username, filename):
    user_dir = os.path.join("user_uploads", username)
    feedback_path = os.path.join(user_dir, filename)
    rewritten_path = feedback_path.replace("_feedback.txt", "_rewritten.txt")
    audio_path = feedback_path.replace("_feedback.txt", "_tips.mp3")

    for file in [feedback_path, rewritten_path, audio_path]:
        if os.path.exists(file):
            os.remove(file)


def list_user_history():
    if not os.path.exists("user_uploads"):
        return []
    return [u for u in os.listdir("user_uploads") if os.path.isdir(os.path.join("user_uploads", u))]


# ========== GPT & Groq API ==========
import openai
openai.api_key = os.getenv("GROQ_API_KEY", "sk-...")  # Replace with real or use .env

def generate_feedback(resume_text, target_role):
    prompt = f"""
You're a professional ATS recruiter. Review this resume for a role as '{target_role}' and give:
1. Resume Score out of 100
2. Strengths
3. Weaknesses
4. ATS Keyword Suggestions

Resume:
\"\"\"
{resume_text}
\"\"\"
"""
    response = openai.ChatCompletion.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message["content"]


def generate_rewritten_resume(resume_text, target_role):
    prompt = f"Rewrite this resume to better match the job role '{target_role}':\n\n{resume_text}"
    response = openai.ChatCompletion.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message["content"]


# ========== gTTS AUDIO TIPS ==========
from gtts import gTTS
import base64

def generate_audio_tips(feedback_text, username, filename):
    tts = gTTS(text=feedback_text, lang='en')
    audio_path = os.path.join("user_uploads", username, f"{filename}_tips.mp3")
    tts.save(audio_path)
    return audio_path


def play_audio(audio_path):
    with open(audio_path, "rb") as audio_file:
        audio_bytes = audio_file.read()
        b64_audio = base64.b64encode(audio_bytes).decode()
        audio_html = f"""
        <audio controls autoplay>
            <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
        </audio>
        """
        st.markdown(audio_html, unsafe_allow_html=True)
