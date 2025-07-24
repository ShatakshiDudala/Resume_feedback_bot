# app.py — Part 1: Setup & Utilities
import streamlit as st
from groq import Groq
from PyPDF2 import PdfReader
import docx
import pandas as pd
import os
import time
import random
import string
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import matplotlib.pyplot as plt
from gtts import gTTS
from datetime import datetime
import hashlib

# === Environment Variables ===
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_USER")        # For SMTP
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")   # For SMTP

# === Groq Client ===
client = Groq(api_key=GROQ_API_KEY)

# === Load user and history CSVs ===
USER_FILE = "users.csv"
HISTORY_FILE = "history.csv"
if not os.path.exists(USER_FILE):
    pd.DataFrame(columns=["email", "password", "phone"]).to_csv(USER_FILE, index=False)
if not os.path.exists(HISTORY_FILE):
    pd.DataFrame(columns=["email", "role", "score", "timestamp", "feedback"]).to_csv(HISTORY_FILE, index=False)

# === Utility Functions ===
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password, hashed):
    return hash_password(password) == hashed

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def extract_text(file):
    text = ""
    if file.name.endswith(".pdf"):
        reader = PdfReader(file)
        text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    elif file.name.endswith(".docx"):
        doc = docx.Document(file)
        text = "\n".join([p.text for p in doc.paragraphs])
    return text.strip()

def send_email_otp(to_email, otp):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg['Subject'] = "OTP for Resume Feedback Password Reset"
    body = f"Your OTP for password reset is: {otp}"
    msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Email failed: {e}")
        return False

# app.py — Part 2: Auth System

# === Load user database ===
def load_users():
    return pd.read_csv(USER_FILE)

def save_users(df):
    df.to_csv(USER_FILE, index=False)

def login_user(email, password):
    df = load_users()
    user = df[df['email'] == email]
    if not user.empty and check_password(password, user.iloc[0]['password']):
        return True
    return False

def signup_user(email, password, phone):
    df = load_users()
    if email in df['email'].values:
        return False
    hashed = hash_password(password)
    new_user = pd.DataFrame([{'email': email, 'password': hashed, 'phone': phone}])
    df = pd.concat([df, new_user], ignore_index=True)
    save_users(df)
    return True

def change_user_password(email, current_pw, new_pw):
    df = load_users()
    if email in df['email'].values:
        user_idx = df[df['email'] == email].index[0]
        if check_password(current_pw, df.loc[user_idx, 'password']):
            df.loc[user_idx, 'password'] = hash_password(new_pw)
            save_users(df)
            return True
    return False

def reset_password(email_or_phone, new_password):
    df = load_users()
    if "@" in email_or_phone:
        user_row = df[df['email'] == email_or_phone]
    else:
        user_row = df[df['phone'] == email_or_phone]
    if not user_row.empty:
        idx = user_row.index[0]
        df.loc[idx, 'password'] = hash_password(new_password)
        save_users(df)
        return True
    return False

def otp_verification_flow(identifier):
    otp = generate_otp()
    if "@" in identifier:
        success = send_email_otp(identifier, otp)
    else:
        st.info(f"Simulated OTP sent to phone: {otp}")
        success = True
    if success:
        entered = st.text_input("Enter the OTP sent", type="password")
        if entered == otp:
            new_pw = st.text_input("New password", type="password")
            confirm_pw = st.text_input("Confirm password", type="password")
            if new_pw and confirm_pw and new_pw == confirm_pw:
                if reset_password(identifier, new_pw):
                    st.success("Password reset successful. You can now log in.")
                    return True
    return False

# app.py — Part 3: Streamlit UI for login/signup and password tools

def show_login_ui():
    st.title("🔐 Login to Resume Feedback Bot")
    menu = st.sidebar.selectbox("Choose Option", ["Login", "Sign Up", "Forgot Password"])

    if menu == "Login":
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if login_user(email, password):
                st.success("Logged in successfully!")
                st.session_state.authenticated = True
                st.session_state.user_email = email
            else:
                st.error("Invalid credentials")

    elif menu == "Sign Up":
        email = st.text_input("Email")
        phone = st.text_input("Phone Number")
        password = st.text_input("Password", type="password")
        confirm_pw = st.text_input("Confirm Password", type="password")
        if st.button("Sign Up"):
            if password == confirm_pw and email and phone:
                if signup_user(email, password, phone):
                    st.success("Account created! You can log in now.")
                else:
                    st.warning("User already exists.")
            else:
                st.error("Check fields and password match.")

    elif menu == "Forgot Password":
        method = st.radio("Verify via", ["Email", "Phone"])
        identifier = st.text_input("Enter your email or phone")
        if st.button("Send OTP"):
            if otp_verification_flow(identifier):
                st.balloons()
                st.success("Password updated successfully")

def show_change_password_ui():
    st.subheader("🔑 Change Password")
    current = st.text_input("Current Password", type="password")
    new = st.text_input("New Password", type="password")
    confirm = st.text_input("Confirm New Password", type="password")
    if st.button("Update Password"):
        if new == confirm:
            if change_user_password(st.session_state.user_email, current, new):
                st.success("Password changed successfully")
            else:
                st.error("Current password is incorrect")
        else:
            st.error("New passwords do not match")

# app.py — Part 4: Main Dashboard after login

def main_dashboard():
    st.title("📄 AI Resume Feedback Bot Dashboard")

    menu = [
        "📄 Resume Analysis",
        "🧠 Feedback Delivery",
        "🧼 User Tools",
        "🔑 Change Password",
        "🚪 Logout"
    ]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "📄 Resume Analysis":
        st.header("📄 Upload Resume")
        uploaded_file = st.file_uploader("Upload your resume (.pdf or .docx)", type=["pdf", "docx"])

        target_role = st.text_input("🎯 Target Job Role", placeholder="e.g. Data Analyst")

        reviewer_mode = st.radio("🧑‍💼 Choose Reviewer Mode", ["General", "Recruiter", "Technical", "Academic", "Startup"])

        if st.button("Generate Feedback"):
            if uploaded_file and target_role:
                feedback, score, rewritten_resume, keywords = analyze_resume(uploaded_file, target_role, reviewer_mode)
                st.success("Feedback generated!")
                st.markdown(f"**Feedback Score:** {score}/100")
                st.progress(score)

                st.subheader("✅ Resume Feedback")
                st.write(feedback)

                st.subheader("✍️ Rewritten Resume (ATS Optimized)")
                st.code(rewritten_resume)

                save_feedback(st.session_state.user_email, uploaded_file.name, feedback, score)

                st.download_button("⬇️ Download Rewritten Resume", rewritten_resume, file_name="Rewritten_Resume.txt")

    elif choice == "🧠 Feedback Delivery":
        st.header("🧠 Voice-based Resume Feedback")

        feedback_audio_path = generate_audio_feedback(st.session_state.user_email)
        if feedback_audio_path:
            st.audio(feedback_audio_path)
            if st.button("🧹 Delete Audio Cache"):
                delete_audio_cache()
                st.success("Audio cache cleared.")
        else:
            st.warning("No feedback audio available. Generate feedback first.")

    elif choice == "🧼 User Tools":
        st.subheader("🗂 Resume Feedback History")
        df = load_history()
        user_df = df[df["email"] == st.session_state.user_email]
        st.dataframe(user_df)

        if st.button("🗑 Delete My History"):
            delete_user_history(st.session_state.user_email)
            st.success("Your resume feedback history has been deleted.")

        if st.session_state.user_email == "admin@example.com":
            st.subheader("📊 Admin Metrics")
            total_users, total_resumes, avg_score = admin_metrics()
            st.markdown(f"- 👥 **Total Users:** {total_users}")
            st.markdown(f"- 📄 **Total Resumes:** {total_resumes}")
            st.markdown(f"- 📈 **Average Score:** {avg_score:.2f}")
            show_metrics_charts()

    elif choice == "🔑 Change Password":
        show_change_password_ui()

    elif choice == "🚪 Logout":
        st.session_state.authenticated = False
        st.session_state.user_email = ""
        st.success("Logged out successfully")

# app.py — Part 5: Utility Functions (Groq API, feedback, audio, admin, etc.)

import datetime
from gtts import gTTS
import base64

def analyze_resume(uploaded_file, target_role, reviewer_mode):
    file_bytes = uploaded_file.read()
    resume_text = extract_text_from_file(file_bytes, uploaded_file.name)

    prompt = f"""
You are an expert resume reviewer. Analyze this resume for the role of {target_role}.
Review it from the perspective of a {reviewer_mode}. Highlight strengths, weaknesses,
and give a detailed feedback. Then rewrite the resume to make it ATS-friendly.
Finally, give a feedback score out of 100.

Resume:
{resume_text}
"""

    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": prompt}]
    )

    reply = response.choices[0].message.content

    score = extract_score_from_reply(reply)
    rewritten = extract_rewritten_resume(reply)
    feedback = reply.split("Rewritten Resume")[0]

    return feedback.strip(), score, rewritten.strip(), extract_keywords(resume_text, target_role)

def extract_score_from_reply(reply):
    import re
    match = re.search(r"score\s*[:\-]?\s*(\d{1,3})", reply, re.IGNORECASE)
    return int(match.group(1)) if match else 70

def extract_rewritten_resume(reply):
    parts = reply.split("Rewritten Resume")
    return parts[1] if len(parts) > 1 else reply

def extract_keywords(resume_text, role):
    prompt = f"""
Extract the top 10 keywords that should be present in a resume for the role of {role}.
Only return comma-separated keywords.
Resume:
{resume_text}
"""
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def extract_text_from_file(file_bytes, filename):
    if filename.endswith(".pdf"):
        with open("temp.pdf", "wb") as f:
            f.write(file_bytes)
        with open("temp.pdf", "rb") as f:
            return extract_text(f)
    elif filename.endswith(".docx"):
        with open("temp.docx", "wb") as f:
            f.write(file_bytes)
        return docx2txt.process("temp.docx")
    return ""

def save_feedback(email, filename, feedback, score):
    df = load_history()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_entry = pd.DataFrame([{
        "email": email,
        "filename": filename,
        "feedback": feedback,
        "score": score,
        "timestamp": timestamp
    }])
    df = pd.concat([df, new_entry], ignore_index=True)
    df.to_csv(HISTORY_FILE, index=False)

def load_history():
    if os.path.exists(HISTORY_FILE):
        return pd.read_csv(HISTORY_FILE)
    else:
        return pd.DataFrame(columns=["email", "filename", "feedback", "score", "timestamp"])

def delete_user_history(email):
    df = load_history()
    df = df[df["email"] != email]
    df.to_csv(HISTORY_FILE, index=False)

def generate_audio_feedback(email):
    df = load_history()
    user_df = df[df["email"] == email]
    if user_df.empty:
        return None
    text = user_df.iloc[-1]["feedback"]
    tts = gTTS(text)
    audio_path = f"audio_{email.replace('@', '_')}.mp3"
    tts.save(audio_path)
    return audio_path

def delete_audio_cache():
    for f in os.listdir():
        if f.startswith("audio_") and f.endswith(".mp3"):
            os.remove(f)

def admin_metrics():
    df = load_history()
    total_users = df["email"].nunique()
    total_resumes = len(df)
    avg_score = df["score"].astype(float).mean() if not df.empty else 0
    return total_users, total_resumes, avg_score

def show_metrics_charts():
    df = load_history()
    if df.empty:
        st.info("No data available for metrics.")
        return
    st.bar_chart(df["score"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)
    st.line_chart(df["score"].resample("D").mean())
# app.py — Part 6: Final UI & Execution

def show_change_password_ui():
    st.subheader("🔐 Change Password")
    email = st.text_input("Your registered email")
    current_password = st.text_input("Current Password", type="password")
    new_password = st.text_input("New Password", type="password")
    confirm_new_password = st.text_input("Confirm New Password", type="password")

    if st.button("Update Password"):
        df = load_users()
        user = df[(df['email'] == email) & (df['password'] == current_password)]
        if not user.empty:
            if new_password == confirm_new_password:
                df.loc[df['email'] == email, 'password'] = new_password
                df.to_csv(USER_DATA_FILE, index=False)
                st.success("Password updated successfully.")
            else:
                st.warning("New passwords do not match.")
        else:
            st.error("Incorrect email or current password.")

def main_app(email, phone):
    st.sidebar.subheader("🛠 User Tools")
    menu = st.sidebar.radio("Navigate", ["📄 Resume Analysis", "🧠 Feedback Delivery", "🗃 History", "📊 Admin Dashboard", "🧼 Cleanup", "🔐 Change Password"])

    if menu == "📄 Resume Analysis":
        st.subheader("📄 Resume Analysis")
        uploaded_file = st.file_uploader("Upload your resume (.pdf or .docx)", type=["pdf", "docx"])
        target_role = st.text_input("🎯 Target Role (e.g., Data Analyst)")
        reviewer_mode = st.selectbox("🧠 Reviewer Mode", ["General", "Recruiter", "Technical", "Academic", "Startup"])
        if st.button("Analyze Resume") and uploaded_file and target_role:
            with st.spinner("Analyzing via Groq..."):
                feedback, score, rewritten, keywords = analyze_resume(uploaded_file, target_role, reviewer_mode)
                st.markdown("#### ✅ Feedback")
                st.write(feedback)
                st.markdown(f"#### ⭐ Score: {score}/100")
                st.progress(score)
                st.markdown("#### 📄 Rewritten Resume (ATS-Friendly)")
                st.code(rewritten, language="markdown")
                st.markdown("#### 🔍 Suggested Keywords")
                st.info(keywords)

                save_feedback(email, uploaded_file.name, feedback, score)

    elif menu == "🧠 Feedback Delivery":
        st.subheader("🧠 Voice Feedback")
        audio_path = generate_audio_feedback(email)
        if audio_path and os.path.exists(audio_path):
            audio_file = open(audio_path, "rb")
            audio_bytes = audio_file.read()
            st.audio(audio_bytes, format="audio/mp3")
        else:
            st.info("No feedback available yet. Analyze a resume first.")

        if st.button("🗑 Delete Audio Cache"):
            delete_audio_cache()
            st.success("Audio files deleted.")

    elif menu == "🗃 History":
        st.subheader("📜 Resume History")
        df = load_history()
        df_user = df[df["email"] == email]
        if df_user.empty:
            st.info("No resume feedback yet.")
        else:
            st.dataframe(df_user[["filename", "score", "timestamp"]])
            if st.button("❌ Delete My History"):
                delete_user_history(email)
                st.success("Your history has been deleted.")

    elif menu == "📊 Admin Dashboard":
        st.subheader("📊 Admin Metrics")
        users, resumes, avg_score = admin_metrics()
        st.markdown(f"- 👥 Total Users: **{users}**")
        st.markdown(f"- 📄 Total Resumes: **{resumes}**")
        st.markdown(f"- 📊 Average Score: **{avg_score:.2f}/100**")
        show_metrics_charts()

    elif menu == "🧼 Cleanup":
        st.subheader("🧼 Delete All Audio Cache")
        if st.button("Clean Now"):
            delete_audio_cache()
            st.success("Deleted all cached .mp3 audio files.")

    elif menu == "🔐 Change Password":
        show_change_password_ui()

def main():
    st.set_page_config(page_title="AI Resume Feedback Bot", page_icon="📄", layout="wide")

    show_logo()
    st.title("📄 AI Resume Feedback Bot")

    menu = st.sidebar.selectbox("👤 Menu", ["Login", "Signup", "Forgot Password"])
    if menu == "Login":
        st.subheader("🔐 Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user = login_user(email, password)
            if user:
                st.success(f"Welcome, {email}")
                main_app(email, user['phone'])
            else:
                st.error("Invalid email or password.")

    elif menu == "Signup":
        st.subheader("📝 Signup")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pwd")
        phone = st.text_input("Phone", key="signup_phone")
        if st.button("Signup"):
            if signup_user(email, password, phone):
                st.success("Account created. Please login.")
            else:
                st.warning("Email already exists.")

    elif menu == "Forgot Password":
        show_forgot_password_ui()

if __name__ == "__main__":
    main()
