# app.py

import streamlit as st
import os
import sqlite3
import uuid
import hashlib
import random
import smtplib
from email.message import EmailMessage
from docx import Document
import PyPDF2
from groq import Groq
from gtts import gTTS
import base64
from datetime import datetime
import matplotlib.pyplot as plt

# -------------- CONFIG ----------------
st.set_page_config(page_title="AI Resume Feedback Bot", page_icon="📄", layout="wide")
st.markdown("""
    <style>
    .main {background-color: #f8f8f8;}
    .stButton>button {
        color: white;
        background-color: #4CAF50;
        border-radius: 8px;
        height: 3em;
        width: 100%;
        font-size: 16px;
    }
    .stTextInput>div>div>input {
        border: 2px solid #4CAF50;
        border-radius: 6px;
    }
    </style>
""", unsafe_allow_html=True)

# ------------- DATABASE ----------------
conn = sqlite3.connect('users.db', check_same_thread=False)
c = conn.cursor()

def create_tables():
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, email TEXT UNIQUE, phone TEXT,
                password TEXT, role TEXT DEFAULT 'user'
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                user_email TEXT,
                resume_name TEXT,
                target_role TEXT,
                feedback TEXT,
                rewritten_resume TEXT,
                audio_path TEXT,
                created_at TEXT
                )''')
create_tables()

# ------------ UTILITIES --------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def send_otp_email(receiver_email, otp):
    try:
        msg = EmailMessage()
        msg.set_content(f"Your OTP for verification is: {otp}")
        msg["Subject"] = "Your OTP Code"
        msg["From"] = "your_email@gmail.com"
        msg["To"] = receiver_email
        # Placeholder for real email send
        print(f"[DEBUG] OTP sent to email {receiver_email}: {otp}")
    except Exception as e:
        st.error("Failed to send OTP Email.")

def send_otp_sms(phone_number, otp):
    # Placeholder: integrate Twilio or SMS API
    print(f"[DEBUG] OTP sent to phone {phone_number}: {otp}")


#2
# Function to verify OTP (email or phone)
def verify_otp(sent_otp, entered_otp):
    return sent_otp == entered_otp

# ---------------------- MAIN LOGIN/SIGNUP UI ---------------------- #
def login_signup_ui():
    st.markdown("<h2 style='color:#2c3e50;'>🔐 Welcome to the AI Resume Feedback Bot</h2>", unsafe_allow_html=True)
    menu = st.sidebar.selectbox("Login / Signup", ["Login", "Signup"])

    if menu == "Signup":
        st.subheader("📝 Create a New Account")
        name = st.text_input("👤 Full Name")
        email = st.text_input("📧 Email")
        phone = st.text_input("📱 Phone Number")
        password = st.text_input("🔑 Password", type='password')
        confirm_password = st.text_input("✅ Confirm Password", type='password')
        otp = generate_otp()

        if st.button("📨 Send OTP"):
            st.session_state["sent_otp"] = otp
            send_otp_email(email, otp)  # Replace with actual email or phone OTP service

        entered_otp = st.text_input("🔢 Enter OTP")
        if st.button("✅ Verify & Signup"):
            if verify_otp(st.session_state.get("sent_otp", ""), entered_otp):
                if password == confirm_password:
                    if email not in user_db:
                        user_db[email] = {"name": name, "email": email, "phone": phone, "password": password, "role": "user"}
                        st.success("✅ Signup successful! Please login.")
                        st.session_state.page = "login"
                    else:
                        st.warning("⚠️ Email already registered.")
                else:
                    st.error("❌ Passwords do not match.")
            else:
                st.error("❌ Incorrect OTP. Please try again.")

    elif menu == "Login":
        st.subheader("🔑 Login to Your Account")
        email = st.text_input("📧 Email")
        password = st.text_input("🔐 Password", type='password')
        if st.button("🚪 Login"):
            user = user_db.get(email)
            if user and user["password"] == password:
                st.success(f"✅ Welcome back, {user['name']}!")
                st.session_state["authenticated"] = True
                st.session_state["user_email"] = email
                st.session_state["user_role"] = user["role"]
                st.experimental_rerun()
            else:
                st.error("❌ Invalid credentials. Please try again.")

# ---------------------- MAIN APP ENTRY ---------------------- #
def main():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
        st.session_state["user_email"] = None
        st.session_state["user_role"] = None
        st.session_state["page"] = "login"

    if not st.session_state["authenticated"]:
        login_signup_ui()
    else:
        show_dashboard()

if __name__ == "__main__":
    main()


#3
# ---------------------- MAIN DASHBOARD AFTER LOGIN ---------------------- #
def show_dashboard():
    st.sidebar.markdown("---")
    dashboard_menu = st.sidebar.radio("📋 Navigation", [
        "📤 Upload Resume",
        "📊 Feedback & Score",
        "🔄 Rewritten Resume",
        "🔈 Audio Tips",
        "📧 Email Feedback",
        "📂 My History",
        "🔐 Change Password",
        "❓ Forgot Password",
        "🧹 Cleanup",
        "👑 Admin Dashboard",
        "🚪 Logout"
    ])

    st.markdown(f"<h2 style='color:#1abc9c;'>📊 Dashboard - {dashboard_menu}</h2>", unsafe_allow_html=True)

    if dashboard_menu == "📤 Upload Resume":
        st.subheader("📤 Upload Your Resume")
        uploaded_file = st.file_uploader("Upload Resume (.pdf or .docx)", type=["pdf", "docx"])
        target_role = st.text_input("🎯 Enter Your Target Role", placeholder="e.g., Data Scientist")

        if uploaded_file and target_role:
            resume_text = extract_text_from_resume(uploaded_file)
            st.success("✅ Resume uploaded and parsed successfully.")
            st.session_state["resume_text"] = resume_text
            st.session_state["target_role"] = target_role
            st.write("📄 Extracted Text Preview:")
            st.code(resume_text[:1000] + "..." if len(resume_text) > 1000 else resume_text)

            if st.button("🚀 Analyze Resume"):
                with st.spinner("Analyzing resume with GPT..."):
                    feedback = generate_resume_feedback(resume_text, target_role)
                    score = calculate_score(feedback)
                    st.session_state["feedback"] = feedback
                    st.session_state["score"] = score
                    st.success("✅ Feedback generated!")
                    st.experimental_rerun()
        else:
            st.warning("⚠️ Please upload a resume and enter your target role to continue.")

    elif dashboard_menu == "📊 Feedback & Score":
        st.subheader("🤖 Resume Feedback")
        feedback = st.session_state.get("feedback", "")
        score = st.session_state.get("score", 0)

        if feedback:
            st.markdown("### 💬 AI Feedback")
            st.write(feedback)

            st.markdown("### 📊 Resume Score")
            st.progress(score / 100)
            st.markdown(f"<h4 style='color:#3498db;'>Score: {score}/100</h4>", unsafe_allow_html=True)
        else:
            st.warning("⚠️ Please upload and analyze a resume first.")

# -------------- Resume Text Extraction Helper ---------------- #
def extract_text_from_resume(uploaded_file):
    file_extension = uploaded_file.name.split(".")[-1]
    if file_extension == "pdf":
        pdf = PdfReader(uploaded_file)
        return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    elif file_extension == "docx":
        doc = docx.Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])
    else:
        return ""

#4
    elif dashboard_menu == "🔄 Rewritten Resume":
        st.subheader("🔄 AI-Powered Resume Rewriting")
        resume_text = st.session_state.get("resume_text", "")
        target_role = st.session_state.get("target_role", "")
        if resume_text and target_role:
            if st.button("♻️ Rewrite My Resume"):
                with st.spinner("Rewriting resume..."):
                    rewritten = rewrite_resume_with_gpt(resume_text, target_role)
                    st.session_state["rewritten_resume"] = rewritten
                    st.success("✅ Resume rewritten successfully!")
                    st.download_button("📥 Download Rewritten Resume", rewritten, file_name="rewritten_resume.txt")
                    st.code(rewritten[:1500] + "..." if len(rewritten) > 1500 else rewritten)
        else:
            st.warning("⚠️ Please upload and analyze a resume first.")

    elif dashboard_menu == "🔈 Audio Tips":
        st.subheader("🔈 AI Audio Tips (gTTS)")
        feedback = st.session_state.get("feedback", "")
        if feedback:
            audio_file = "audio_feedback.mp3"
            tts = gTTS(text=feedback, lang='en')
            tts.save(audio_file)
            st.audio(audio_file)
            st.success("✅ Audio feedback ready!")
        else:
            st.warning("⚠️ Generate feedback first before playing audio.")

    elif dashboard_menu == "📧 Email Feedback":
        st.subheader("📧 Email Resume Feedback")
        user_email = st.session_state.get("email")
        feedback = st.session_state.get("feedback", "")
        if user_email and feedback:
            if st.button("📤 Send Feedback to Email"):
                try:
                    # Placeholder only — replace with SMTP config
                    send_email_feedback(user_email, feedback)
                    st.success("✅ Feedback sent to your email.")
                except Exception as e:
                    st.error(f"❌ Failed to send email: {e}")
        else:
            st.warning("⚠️ Missing email or feedback.")

#5
# --- GPT Resume Rewriting ---
def rewrite_resume_with_gpt(resume_text, target_role):
    prompt = f"Improve and rewrite this resume for the role of '{target_role}'. Ensure it's professional, concise, and impactful:\n\n{resume_text}"
    try:
        response = groq.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Error rewriting resume: {e}"

# --- Send Email Feedback (Placeholder) ---
def send_email_feedback(to_email, feedback_text):
    # Placeholder SMTP code — configure with real credentials
    sender_email = "youremail@example.com"
    sender_password = "yourpassword"
    msg = EmailMessage()
    msg.set_content(feedback_text)
    msg["Subject"] = "Your AI Resume Feedback"
    msg["From"] = sender_email
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender_email, sender_password)
        smtp.send_message(msg)

# --- Feedback History ---
def load_feedback_history(email):
    history_file = f"history_{email}.json"
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            return json.load(f)
    return []

def save_feedback_history(email, entry):
    history = load_feedback_history(email)
    history.append(entry)
    with open(f"history_{email}.json", "w") as f:
        json.dump(history, f)

elif dashboard_menu == "📂 Feedback History":
    st.subheader("📂 Your Previous Feedback")
    user_email = st.session_state.get("email")
    if user_email:
        history = load_feedback_history(user_email)
        if history:
            for i, item in enumerate(reversed(history)):
                st.markdown(f"### 🗂️ Entry {len(history) - i}")
                st.write(f"**Uploaded:** {item.get('filename', 'N/A')}")
                st.write(f"**Target Role:** {item.get('role', 'N/A')}")
                st.write(f"**Feedback:** {item.get('feedback', '')[:500]}...")
                if st.button(f"🗑️ Delete Entry {len(history) - i}"):
                    history.pop(len(history) - 1 - i)
                    with open(f"history_{user_email}.json", "w") as f:
                        json.dump(history, f)
                    st.experimental_rerun()
        else:
            st.info("ℹ️ No feedback history found.")
    else:
        st.warning("⚠️ Please login to view history.")

elif dashboard_menu == "🧹 Clean Audio/Feedback":
    st.subheader("🧹 Clean Temporary Files")
    if os.path.exists("audio_feedback.mp3"):
        os.remove("audio_feedback.mp3")
    st.session_state.pop("feedback", None)
    st.session_state.pop("rewritten_resume", None)
    st.success("✅ Cleaned audio and feedback cache.")

#6
# ✅ Part 6 — Dashboard Features

elif st.session_state.get("page") == "dashboard":
    st.sidebar.subheader(f"👋 Welcome, {st.session_state.name}")
    dashboard_menu = st.sidebar.radio("📂 Dashboard Menu", [
        "📤 Upload Resume", 
        "🤖 AI Feedback", 
        "🔄 Rewritten Resume", 
        "🔈 Audio Tips", 
        "📧 Email Feedback", 
        "📂 Feedback History", 
        "🧹 Clean Feedback/Audio", 
        "🔐 Change Password", 
        "❓ Forgot Password", 
        "👑 Admin Dashboard"
    ])

    # 📤 Upload Resume
    if dashboard_menu == "📤 Upload Resume":
        uploaded_file = st.file_uploader("Upload your resume (.pdf or .docx)", type=["pdf", "docx"])
        target_role = st.text_input("🎯 Target Role (e.g., Data Scientist)")

        if uploaded_file and target_role:
            resume_bytes = uploaded_file.read()
            resume_text = extract_text_from_resume(uploaded_file)

            st.success("✅ Resume uploaded and parsed successfully.")
            st.write("📄 Extracted Text Preview:")
            st.code(resume_text[:1000] + "...")

            # Store in session for later steps
            st.session_state["resume_text"] = resume_text
            st.session_state["target_role"] = target_role

    # 🤖 GPT Resume Feedback
    elif dashboard_menu == "🤖 AI Feedback":
        if "resume_text" in st.session_state and "target_role" in st.session_state:
            with st.spinner("Analyzing your resume..."):
                feedback = get_resume_feedback(st.session_state["resume_text"], st.session_state["target_role"])
                st.session_state["feedback"] = feedback

            score = get_resume_score(feedback)
            st.subheader("📊 Resume Score")
            st.progress(score / 100)
            st.success(f"Your Resume Score: {score}/100")

            st.subheader("📝 AI Feedback")
            st.write(feedback)

            # Save to DB
            save_feedback(
                st.session_state.email, 
                st.session_state["resume_text"], 
                feedback, 
                st.session_state["target_role"], 
                score
            )
        else:
            st.warning("⚠️ Please upload a resume and set a target role first.")

    # 🔄 Rewritten Resume
    elif dashboard_menu == "🔄 Rewritten Resume":
        if "resume_text" in st.session_state and "target_role" in st.session_state:
            rewritten = rewrite_resume(st.session_state["resume_text"], st.session_state["target_role"])
            st.session_state["rewritten"] = rewritten
            st.subheader("🔁 Rewritten Resume")
            st.code(rewritten[:2000] + "...")

            # Download button
            st.download_button("⬇️ Download Rewritten Resume", rewritten, file_name="rewritten_resume.txt")
        else:
            st.warning("⚠️ Please upload and analyze your resume first.")

    # 🔈 Audio Tips
    elif dashboard_menu == "🔈 Audio Tips":
        if "feedback" in st.session_state:
            audio_file = generate_audio_tips(st.session_state["feedback"])
            st.audio(audio_file)
        else:
            st.warning("⚠️ Please get AI feedback first.")

    # ... (remaining parts continue in Part 7)

#7
        elif dashboard_menu == "🔐 Change Password":
            st.subheader("🔐 Change Password")
            current_password = st.text_input("Current Password", type="password", key="cur_pwd")
            new_password = st.text_input("New Password", type="password", key="new_pwd")
            confirm_password = st.text_input("Confirm New Password", type="password", key="conf_pwd")
            if st.button("🔄 Update Password"):
                if authenticate_user(st.session_state['email'], current_password):
                    if new_password == confirm_password:
                        update_user_password(st.session_state['email'], new_password)
                        st.success("✅ Password updated successfully!")
                    else:
                        st.error("❌ New passwords do not match.")
                else:
                    st.error("❌ Current password is incorrect.")

        elif dashboard_menu == "🔑 Forgot Password":
            st.subheader("🔑 Forgot Password")
            email_reset = st.text_input("📧 Enter your registered email")
            otp_sent = False
            if st.button("📤 Send OTP to Email"):
                if email_reset:
                    otp = generate_otp()
                    st.session_state["reset_otp"] = otp
                    st.session_state["reset_email"] = email_reset
                    send_email_otp(email_reset, otp)
                    st.success("📩 OTP sent to your email.")
                    otp_sent = True
                else:
                    st.warning("⚠️ Enter a valid email.")

            if "reset_otp" in st.session_state:
                user_otp = st.text_input("🔑 Enter OTP sent to your email")
                new_pwd = st.text_input("🆕 New Password", type="password")
                if st.button("✅ Reset Password"):
                    if user_otp == st.session_state["reset_otp"]:
                        update_user_password(st.session_state["reset_email"], new_pwd)
                        st.success("✅ Password reset successful!")
                        del st.session_state["reset_otp"]
                        del st.session_state["reset_email"]
                    else:
                        st.error("❌ Invalid OTP.")

        elif dashboard_menu == "👑 Admin Dashboard":
            st.subheader("👑 Admin Analytics Dashboard")
            user_data = get_all_user_data()
            feedback_count = get_feedback_count()
            upload_count = get_upload_count()

            col1, col2, col3 = st.columns(3)
            col1.metric("🧑 Total Users", len(user_data))
            col2.metric("📥 Total Uploads", upload_count)
            col3.metric("📊 Total Feedbacks", feedback_count)

            st.markdown("### 📈 Feedback Over Time")
            chart_data = get_feedback_chart_data()
            st.line_chart(chart_data)

    else:
        st.warning("🔒 Please log in to view the dashboard.")


#8
# Helper: OTP Generator
def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

# Helper: Placeholder for sending email OTP (use real SMTP in production)
def send_email_otp(email, otp):
    try:
        msg = MIMEText(f"Your OTP code is: {otp}")
        msg['Subject'] = 'Your Resume Feedback Bot OTP'
        msg['From'] = 'noreply@yourbot.com'
        msg['To'] = email

        # Placeholder: Replace with real SMTP credentials
        with smtplib.SMTP('smtp.example.com', 587) as server:
            server.starttls()
            server.login("your_email@example.com", "your_password")
            server.send_message(msg)
        print(f"OTP sent to {email}: {otp}")
    except Exception as e:
        print("Email OTP Error:", e)

# Helper: Update User Password
def update_user_password(email, new_password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET password = ? WHERE email = ?", (new_password, email))
    conn.commit()
    conn.close()

# Admin Stats Helpers
def get_all_user_data():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    data = c.fetchall()
    conn.close()
    return data

def get_upload_count():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM feedbacks")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_feedback_count():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM feedbacks WHERE feedback IS NOT NULL")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_feedback_chart_data():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT created_at FROM feedbacks", conn)
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['date'] = df['created_at'].dt.date
    chart_data = df.groupby('date').size().reset_index(name='feedbacks')
    chart_data.set_index('date', inplace=True)
    return chart_data

# Initialize the app
if __name__ == "__main__":
    st.set_page_config(page_title="AI Resume Feedback Bot", page_icon="🧠", layout="wide")
    init_db()
    login_signup_ui()
