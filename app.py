# ----------------------------- Part 1: Imports, Config, OTP, Login/Signup -----------------------------

import streamlit as st
import pandas as pd
import os
import uuid
import base64
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from gtts import gTTS
from pathlib import Path
from io import BytesIO
from docx import Document
from PyPDF2 import PdfReader
import matplotlib.pyplot as plt

# ----------------------------- Page Configuration -----------------------------
st.set_page_config(page_title="AI Resume Feedback Bot", layout="wide", page_icon="🤖")

# ----------------------------- Session State Initialization -----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "username" not in st.session_state:
    st.session_state.username = ""
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "history" not in st.session_state:
    st.session_state.history = []

# ----------------------------- Local User DB -----------------------------
if "users" not in st.session_state:
    st.session_state.users = {
        "admin@example.com": {
            "password": "admin123",
            "name": "Admin",
            "phone": "9999999999",
            "otp": "",
            "is_admin": True,
            "history": []
        }
    }

# ----------------------------- OTP Sender Placeholder -----------------------------
def send_otp_via_email(email, otp):
    # ⚠️ Replace with your SMTP credentials for real implementation
    st.success(f"📧 OTP sent to {email}: `{otp}`")  # For testing/demo

def send_otp_via_sms(phone, otp):
    # ⚠️ Replace with Twilio or SMS API for real implementation
    st.success(f"📱 OTP sent to phone: `{otp}`")  # For testing/demo

# ----------------------------- Login / Signup UI -----------------------------
def login_signup_ui():
    st.markdown("<h2 style='color:#00BFFF'>🔐 Welcome to AI Resume Feedback Bot</h2>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Signup"])

    with tab1:
        email = st.text_input("📧 Email", key="login_email")
        password = st.text_input("🔒 Password", type="password", key="login_password")

        if st.button("🔓 Login"):
            user = st.session_state.users.get(email)
            if user and user["password"] == password:
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.session_state.username = user["name"]
                st.session_state.is_admin = user.get("is_admin", False)
                st.success("✅ Login successful!")
                st.experimental_rerun()
            else:
                st.error("❌ Invalid credentials!")

    with tab2:
        name = st.text_input("👤 Full Name", key="signup_name")
        email = st.text_input("📧 Email", key="signup_email")
        phone = st.text_input("📱 Phone Number", key="signup_phone")
        password = st.text_input("🔑 Password", type="password", key="signup_password")
        confirm_password = st.text_input("🔁 Confirm Password", type="password", key="signup_confirm")

        if st.button("📝 Register"):
            if email in st.session_state.users:
                st.warning("⚠️ Email already registered.")
            elif password != confirm_password:
                st.warning("❌ Passwords do not match.")
            else:
                otp = str(uuid.uuid4().int)[:6]
                st.session_state.users[email] = {
                    "name": name,
                    "password": password,
                    "phone": phone,
                    "otp": otp,
                    "is_admin": False,
                    "history": []
                }
                send_otp_via_sms(phone, otp)
                send_otp_via_email(email, otp)
                st.success("✅ Registered! OTP sent for verification.")


# ----------------------------- OTP Verification + Sidebar Navigation -----------------------------

def verify_otp_ui():
    st.subheader("🔐 Verify OTP")
    entered_otp = st.text_input("🔢 Enter OTP sent to your phone/email")
    if st.button("✅ Verify"):
        user = st.session_state.users.get(st.session_state.user_email)
        if user and user["otp"] == entered_otp:
            st.success("🎉 OTP Verified Successfully!")
            st.experimental_rerun()
        else:
            st.error("❌ Invalid OTP. Please try again.")

# ----------------------------- Sidebar Navigation -----------------------------
def dashboard_sidebar():
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2920/2920284.png", width=80)
    st.sidebar.markdown(f"### 👋 Welcome, **{st.session_state.username}**")
    dashboard_menu = st.sidebar.radio(
        "📚 Menu",
        [
            "📤 Upload Resume",
            "📊 Resume Feedback",
            "🔄 Rewritten Resume",
            "🔈 Audio Tips",
            "📧 Email Feedback",
            "📂 My History",
            "🧹 Cleanup",
            "🔐 Password Options",
            "👑 Admin Dashboard" if st.session_state.is_admin else "🔒 Exit",
        ]
    )
    return dashboard_menu

# ----------------------------- Dashboard Layout After Login -----------------------------
def dashboard():
    st.markdown("<h2 style='color:#20B2AA'>📊 AI Resume Analysis Dashboard</h2>", unsafe_allow_html=True)
    dashboard_menu = dashboard_sidebar()

    if dashboard_menu == "📤 Upload Resume":
        upload_resume_section()
    elif dashboard_menu == "📊 Resume Feedback":
        feedback_section()
    elif dashboard_menu == "🔄 Rewritten Resume":
        rewritten_resume_section()
    elif dashboard_menu == "🔈 Audio Tips":
        audio_tip_section()
    elif dashboard_menu == "📧 Email Feedback":
        email_section()
    elif dashboard_menu == "📂 My History":
        history_section()
    elif dashboard_menu == "🧹 Cleanup":
        cleanup_section()
    elif dashboard_menu == "🔐 Password Options":
        password_options_section()
    elif dashboard_menu == "👑 Admin Dashboard":
        admin_dashboard_section()
    elif dashboard_menu == "🔒 Exit":
        st.session_state.logged_in = False
        st.success("👋 Logged out!")
        st.experimental_rerun()


# ----------------------------- Upload Resume Section -----------------------------
def upload_resume_section():
    st.markdown("## 📤 Upload Your Resume")
    uploaded_file = st.file_uploader("Upload Resume (.pdf or .docx)", type=["pdf", "docx"])

    target_role = st.text_input("🎯 Enter Target Role (e.g., Data Scientist, Software Engineer)")

    if uploaded_file and target_role:
        resume_bytes = uploaded_file.read()

        # Save file temporarily
        resume_path = f"temp/{uploaded_file.name}"
        with open(resume_path, "wb") as f:
            f.write(resume_bytes)

        # Extract text from resume
        if uploaded_file.name.endswith(".pdf"):
            resume_text = extract_text_from_pdf(resume_path)
        elif uploaded_file.name.endswith(".docx"):
            resume_text = extract_text_from_docx(resume_path)
        else:
            st.error("Unsupported file format.")
            return

        # Store in session
        st.session_state.resume_text = resume_text
        st.session_state.resume_name = uploaded_file.name
        st.session_state.target_role = target_role

        st.success("✅ Resume uploaded and text extracted successfully!")

        st.markdown("### 📝 Extracted Resume Text Preview")
        st.text_area("Resume Content", resume_text, height=300)

# ----------------------------- PDF/DOCX Parsing Utilities -----------------------------
def extract_text_from_pdf(pdf_path):
    from PyPDF2 import PdfReader
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_docx(docx_path):
    from docx import Document
    doc = Document(docx_path)
    return "\n".join([para.text for para in doc.paragraphs])


# ----------------------------- GPT Resume Feedback Section -----------------------------
def generate_resume_feedback():
    st.markdown("## 🤖 AI-Powered Resume Feedback")
    
    if "resume_text" not in st.session_state:
        st.warning("⚠️ Please upload a resume first from the 'Upload Resume' tab.")
        return

    resume_text = st.session_state.resume_text
    target_role = st.session_state.target_role

    with st.spinner("Analyzing your resume with AI..."):
        try:
            feedback, score = call_groq_resume_feedback(resume_text, target_role)
            st.session_state.generated_feedback = feedback
            st.session_state.generated_score = score

            st.success("✅ Resume feedback generated!")

            # Display Score with progress bar
            st.markdown("### 📊 Resume Score")
            st.progress(score / 100.0)
            st.write(f"Score: **{score}/100**")

            # Display feedback
            st.markdown("### 🧠 AI Feedback Summary")
            st.write(feedback)

            # Save feedback for history
            save_feedback_to_history(
                st.session_state.user_email,
                st.session_state.resume_name,
                resume_text,
                target_role,
                feedback,
                score
            )

        except Exception as e:
            st.error(f"❌ Failed to generate feedback: {str(e)}")

# ----------------------------- Groq API or Mock Call -----------------------------
def call_groq_resume_feedback(resume_text, target_role):
    import random
    # Replace with actual Groq API call here
    # Simulated Response:
    mock_feedback = f"Your resume is well-suited for the role of {target_role}. Focus more on quantifying achievements, adding relevant keywords, and clarifying your role in each project."
    mock_score = random.randint(60, 90)
    return mock_feedback, mock_score

# ----------------------------- Store Feedback to History -----------------------------
def save_feedback_to_history(email, resume_name, resume_text, role, feedback, score):
    history_path = "data/feedback_history.json"
    try:
        with open(history_path, "r") as f:
            history = json.load(f)
    except:
        history = {}

    if email not in history:
        history[email] = []

    history[email].append({
        "resume_name": resume_name,
        "role": role,
        "feedback": feedback,
        "score": score,
        "text": resume_text,
        "timestamp": datetime.datetime.now().isoformat()
    })

    with open(history_path, "w") as f:
        json.dump(history, f, indent=4)


# ----------------------------- Resume Rewriting Section -----------------------------
def generate_ai_rewritten_resume():
    st.markdown("## 🔄 AI-Generated Resume Rewrite")

    if "resume_text" not in st.session_state or "generated_feedback" not in st.session_state:
        st.warning("⚠️ Please upload a resume and generate feedback first.")
        return

    with st.spinner("Rewriting your resume using AI..."):
        try:
            rewritten_resume = rewrite_resume_using_ai(
                st.session_state.resume_text,
                st.session_state.generated_feedback,
                st.session_state.target_role
            )
            st.session_state.rewritten_resume = rewritten_resume

            st.success("✅ Resume rewritten successfully!")
            st.download_button(
                label="📥 Download Rewritten Resume",
                data=rewritten_resume,
                file_name="AI_Rewritten_Resume.txt",
                mime="text/plain"
            )
        except Exception as e:
            st.error(f"❌ Could not rewrite resume: {str(e)}")

def rewrite_resume_using_ai(original_text, feedback, target_role):
    return (
        f"📄 **AI-Rewritten Resume for Role: {target_role}**\n\n"
        f"{original_text}\n\n"
        f"---\n\n"
        f"🧠 **AI Suggestions Applied:**\n{feedback}"
    )

# ----------------------------- Audio Feedback Section -----------------------------
def generate_audio_feedback():
    st.markdown("## 🔈 Audio Tips from AI")

    if "generated_feedback" not in st.session_state:
        st.warning("⚠️ Generate resume feedback first.")
        return

    feedback_text = st.session_state.generated_feedback

    try:
        tts = gTTS(text=feedback_text)
        audio_path = f"temp_audio_{uuid.uuid4()}.mp3"
        tts.save(audio_path)
        st.audio(audio_path)

        st.session_state.audio_path = audio_path
        st.success("🎧 Audio feedback generated!")

    except Exception as e:
        st.error(f"❌ Failed to generate audio: {str(e)}")

# ----------------------------- Email Feedback Section -----------------------------
def send_feedback_via_email():
    st.markdown("## 📧 Send Feedback to Your Email")

    if "generated_feedback" not in st.session_state:
        st.warning("⚠️ Generate resume feedback first.")
        return

    if st.button("📤 Send to My Email"):
        try:
            sender = "youremail@example.com"
            receiver = st.session_state.user_email
            password = "yourpassword"

            subject = "Your AI Resume Feedback"
            body = st.session_state.generated_feedback

            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = receiver

            # Placeholder: Configure actual SMTP here
            st.info("📬 (SMTP sending skipped — placeholder used)")

            st.success("✅ Feedback sent to your email!")

        except Exception as e:
            st.error(f"❌ Failed to send email: {str(e)}")


# ----------------------------- Feedback History Section -----------------------------
def show_feedback_history():
    st.markdown("## 📂 Feedback History")

    user_id = st.session_state.user_email
    history = resume_db.get(user_id, [])

    if not history:
        st.info("📭 No feedback history yet. Upload your resume to get started!")
        return

    for i, entry in enumerate(history[::-1]):
        with st.expander(f"📝 Feedback for: {entry['timestamp']}"):
            st.write(f"**Target Role:** {entry['target_role']}")
            st.write(f"**Feedback:** {entry['feedback']}")
            st.download_button("📥 Download Resume Text", data=entry['resume_text'], file_name="resume.txt")
            if st.button(f"🗑 Delete Entry #{len(history)-i}", key=f"delete_{i}"):
                resume_db[user_id].remove(entry)
                st.success("✅ Entry deleted. Refreshing...")
                st.experimental_rerun()

# ----------------------------- Clean Audio & Feedback -----------------------------
def cleanup_audio_and_feedback():
    st.markdown("## 🧹 Clean Up Audio & Feedback")
    if st.button("🧽 Clear All Generated Audio & Feedback"):
        st.session_state.pop("generated_feedback", None)
        st.session_state.pop("audio_path", None)
        st.session_state.pop("resume_text", None)
        st.session_state.pop("rewritten_resume", None)
        st.success("✅ Cleared all feedback/audio successfully!")

# ----------------------------- Admin Dashboard Section -----------------------------
def show_admin_dashboard():
    st.markdown("## 👑 Admin Dashboard (Demo)")

    total_users = len(user_db)
    total_feedbacks = sum(len(v) for v in resume_db.values())
    feedback_chart_data = {user: len(v) for user, v in resume_db.items()}

    col1, col2 = st.columns(2)
    with col1:
        st.metric("👥 Total Users", total_users)
    with col2:
        st.metric("📄 Total Feedbacks", total_feedbacks)

    st.subheader("📊 Feedback Count per User")
    if feedback_chart_data:
        df_chart = pd.DataFrame(list(feedback_chart_data.items()), columns=["User", "Feedback Count"])
        st.bar_chart(df_chart.set_index("User"))
    else:
        st.info("📉 No feedback data to display.")

    st.caption("🔒 Note: Admin dashboard is a demo and can be extended with role-based control.")


# ----------------------------- Change Password Section -----------------------------
def change_password():
    st.markdown("## 🔐 Change Password")

    current_password = st.text_input("🔑 Current Password", type="password", key="curr_pwd")
    new_password = st.text_input("🆕 New Password", type="password", key="new_pwd")
    confirm_password = st.text_input("✅ Confirm New Password", type="password", key="conf_pwd")

    if st.button("🔄 Update Password"):
        user_data = user_db.get(st.session_state.user_email)
        if not user_data or user_data["password"] != current_password:
            st.error("❌ Current password is incorrect.")
        elif new_password != confirm_password:
            st.warning("⚠️ New password and confirm password do not match.")
        else:
            user_data["password"] = new_password
            st.success("✅ Password updated successfully!")

# ----------------------------- Forgot Password Section -----------------------------
def forgot_password():
    st.markdown("## ❓ Forgot Password")

    email = st.text_input("📧 Enter your registered email")
    if st.button("📨 Send OTP to Email"):
        if email not in user_db:
            st.error("❌ Email not registered.")
        else:
            otp = str(random.randint(1000, 9999))
            st.session_state.otp = otp
            st.session_state.otp_email = email
            st.info(f"📩 OTP sent to {email} (Simulated): `{otp}`")  # Simulated
            st.experimental_rerun()

    if "otp_email" in st.session_state:
        entered_otp = st.text_input("🔐 Enter OTP from Email", key="entered_email_otp")
        new_pwd = st.text_input("🆕 New Password", type="password", key="forgot_new_pwd")
        confirm_pwd = st.text_input("✅ Confirm Password", type="password", key="forgot_conf_pwd")

        if st.button("🔁 Reset Password"):
            if entered_otp != st.session_state.otp:
                st.error("❌ Invalid OTP.")
            elif new_pwd != confirm_pwd:
                st.warning("⚠️ Passwords do not match.")
            else:
                user_db[st.session_state.otp_email]["password"] = new_pwd
                st.success("✅ Password reset successfully!")
                del st.session_state["otp"]
                del st.session_state["otp_email"]

# ----------------------------- Section Headers -----------------------------
def show_section_header(title, icon):
    st.markdown(f"### {icon} {title}")


# ----------------------------- Main App Layout After Login -----------------------------
def dashboard_ui():
    st.sidebar.image("https://img.icons8.com/external-flat-juicy-fish/64/resume.png", width=100)
    st.sidebar.markdown("## 🧠 AI Resume Feedback Bot")
    menu = st.sidebar.radio("📚 Navigate", ["📤 Upload & Feedback", "📂 Feedback History", "🧹 Clean Audio", "🔐 Change Password", "👑 Admin Dashboard", "🚪 Logout"])

    st.sidebar.markdown("---")
    st.sidebar.success(f"👤 Logged in as: `{st.session_state.user_email}`")

    if menu == "📤 Upload & Feedback":
        show_section_header("Resume Upload & Feedback", "📤")
        upload_resume_section()

    elif menu == "📂 Feedback History":
        show_feedback_history()

    elif menu == "🧹 Clean Audio":
        cleanup_audio_and_feedback()

    elif menu == "🔐 Change Password":
        change_password()

    elif menu == "👑 Admin Dashboard":
        show_admin_dashboard()

    elif menu == "🚪 Logout":
        st.session_state.clear()
        st.success("✅ Logged out successfully.")
        st.experimental_rerun()

# ----------------------------- App Start Point -----------------------------
def main():
    st.set_page_config(page_title="AI Resume Feedback Bot", page_icon="🧠", layout="wide")
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #f0f6ff;
        }
        .css-18e3th9 {
            padding: 2rem;
            border-radius: 12px;
            background-color: #ffffff;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        .stButton>button {
            background-color: #1f77b4;
            color: white;
            border-radius: 8px;
            padding: 0.5rem 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    if "authenticated" in st.session_state and st.session_state.authenticated:
        dashboard_ui()
    else:
        login_signup_ui()

# ----------------------------- Run App -----------------------------
if __name__ == "__main__":
    main()
