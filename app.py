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


# --- Change Password ---
elif dashboard_menu == "🔐 Change Password":
    st.subheader("🔐 Change Your Password")
    email = st.session_state.get("email")
    if not email:
        st.warning("⚠️ You must be logged in to change your password.")
    else:
        with st.form("change_password_form"):
            current = st.text_input("🔑 Current Password", type="password", key="curr_pass")
            new_pass = st.text_input("🆕 New Password", type="password", key="new_pass")
            confirm_pass = st.text_input("✅ Confirm New Password", type="password", key="conf_pass")
            submit_btn = st.form_submit_button("🔄 Update Password")

        if submit_btn:
            with open(USER_DB, "r") as f:
                users = json.load(f)

            if users[email]["password"] != current:
                st.error("❌ Incorrect current password.")
            elif new_pass != confirm_pass:
                st.error("❌ New passwords do not match.")
            else:
                users[email]["password"] = new_pass
                with open(USER_DB, "w") as f:
                    json.dump(users, f)
                st.success("✅ Password updated successfully!")

# --- Forgot Password with OTP (Email or Phone) ---
elif dashboard_menu == "🔐 Forgot Password":
    st.subheader("🔐 Reset Forgotten Password")

    method = st.radio("Choose verification method:", ["📧 Email", "📱 Phone"])

    identifier = st.text_input("Enter your registered Email or Phone:")
    if st.button("📨 Send OTP"):
        otp = str(random.randint(100000, 999999))
        st.session_state["reset_otp"] = otp
        st.session_state["reset_id"] = identifier

        if method == "📧 Email":
            try:
                send_email_feedback(identifier, f"🔐 Your OTP is: {otp}")
                st.success("✅ OTP sent to your email.")
            except:
                st.error("❌ Failed to send email. Check SMTP config.")
        else:
            st.warning("📱 Phone OTP logic placeholder. Integrate with Twilio or SMS gateway.")

    entered_otp = st.text_input("🔢 Enter OTP")
    new_reset_pass = st.text_input("🔑 New Password", type="password")
    confirm_reset_pass = st.text_input("✅ Confirm New Password", type="password")

    if st.button("🔄 Reset Password"):
        with open(USER_DB, "r") as f:
            users = json.load(f)

        id_key = st.session_state.get("reset_id")
        actual_otp = st.session_state.get("reset_otp")

        if entered_otp != actual_otp:
            st.error("❌ Invalid OTP.")
        elif new_reset_pass != confirm_reset_pass:
            st.error("❌ Passwords do not match.")
        elif id_key not in users:
            st.error("❌ Email/Phone not registered.")
        else:
            users[id_key]["password"] = new_reset_pass
            with open(USER_DB, "w") as f:
                json.dump(users, f)
            st.success("✅ Password reset successful.")


# --- Admin Dashboard ---
elif dashboard_menu == "👑 Admin Dashboard":
    st.subheader("📊 Admin Analytics")
    email = st.session_state.get("email")

    if email != "admin@bot.com":
        st.warning("🚫 You are not authorized to access the Admin Dashboard.")
    else:
        with open("history.json", "r") as f:
            full_data = json.load(f)

        st.markdown("### 📈 Upload Count Per User")
        user_upload_counts = {k: len(v) for k, v in full_data.items()}

        if user_upload_counts:
            fig1, ax1 = plt.subplots()
            ax1.bar(user_upload_counts.keys(), user_upload_counts.values(), color="skyblue")
            plt.xticks(rotation=45, ha='right')
            st.pyplot(fig1)
        else:
            st.info("ℹ️ No upload data available.")

        st.markdown("### 🎯 Common Target Roles")
        role_counts = {}
        for user in full_data.values():
            for record in user:
                role = record.get("target_role", "Unknown")
                role_counts[role] = role_counts.get(role, 0) + 1
        if role_counts:
            fig2, ax2 = plt.subplots()
            ax2.pie(role_counts.values(), labels=role_counts.keys(), autopct='%1.1f%%')
            ax2.axis('equal')
            st.pyplot(fig2)
        else:
            st.info("ℹ️ No role data found.")

# --- Logout Button ---
st.markdown("---")
if st.button("🚪 Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.success("✅ You have been logged out.")
    st.experimental_rerun()


# --- Final UI Cleanup and Spacing ---
st.markdown("---")
st.markdown(
    """
    <div style='text-align:center; color:#888; font-size:14px;'>
        💼 Powered by <b>Xcellytics AI Resume Engine</b> | 📬 support@xcellytics.ai
    </div>
    """,
    unsafe_allow_html=True
)
st.markdown("")

# Clean up Streamlit state if page reloads
if "feedback" not in st.session_state:
    st.session_state.feedback = None
if "score" not in st.session_state:
    st.session_state.score = None
if "target_role" not in st.session_state:
    st.session_state.target_role = None
if "audio_path" not in st.session_state:
    st.session_state.audio_path = None

# ------------------------------
# 📁 Suggested Folder Structure
# ------------------------------
# 📦 resume_feedback_bot/
# ┣ 📄 app.py
# ┣ 📁 utils/
# ┃ ┣ 📄 gpt_utils.py       # Handles GPT feedback/rewrite
# ┃ ┣ 📄 otp_utils.py       # Email/Phone OTP (SMTP/Twilio placeholders)
# ┣ 📁 temp/
# ┃ ┗ 📄 (Uploaded files, rewritten resumes, audio files)
# ┣ 📄 users.json           # User login/signup data
# ┣ 📄 history.json         # User feedback history
# ┗ 📄 requirements.txt     # All Python dependencies

# ------------------------------
# 🛠 Deployment Notes
# ------------------------------
# ✅ For Email OTP:
#    - Use smtplib with Gmail SMTP or other providers
#    - Enable 'Less secure apps' or App Passwords
#    - Place credentials in a .env file

# ✅ For Phone OTP:
#    - Use Twilio or similar SMS API
#    - Install: `pip install twilio`
#    - Create Twilio account and verify your number

# ✅ For Groq GPT API:
#    - Add your Groq API key in .env
#    - Use llama3 or mixtral depending on model

# ✅ Final Deployment:
#    - Run: `streamlit run app.py`
#    - Optional: Deploy on Streamlit Cloud, HuggingFace, Render, etc.

# ------------------------------
# 🌟 You're ready to go!
# ------------------------------
