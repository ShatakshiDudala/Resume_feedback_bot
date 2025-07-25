import streamlit as st
import pandas as pd
import os
import base64
import hashlib
import random
import string
import time
import smtplib
import uuid
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PyPDF2 import PdfReader
from docx import Document
from gtts import gTTS
from io import BytesIO
from dotenv import load_dotenv
import matplotlib.pyplot as plt

# Optional: Disable warning
st.set_option('deprecation.showfileUploaderEncoding', False)

# Load environment variables (for future SMTP or secrets)
load_dotenv()

# Page config
st.set_page_config(page_title="AI Resume Feedback Bot", layout="wide", page_icon="🧠")

# App-wide constants
USER_DB = "users.csv"
FEEDBACK_HISTORY = "history.csv"
ADMIN_EMAIL = "admin@bot.com"
REVIEWER_MODES = ["General", "Recruiter", "Technical", "Academic", "Startup"]

# Inject CSS styling for colorful UI
st.markdown("""
    <style>
        .main { background-color: #f4f4f9; }
        .stButton>button { background-color: #008CBA; color: white; border-radius: 8px; padding: 10px; }
        .stTextInput>div>div>input { border: 1px solid #aaa; border-radius: 5px; }
        .feedback-box { background: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #00b894; }
        .header-title { font-size:32px; font-weight:bold; color:#6c5ce7 }
    </style>
""", unsafe_allow_html=True)

# Utility functions
def encrypt_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if not os.path.exists(USER_DB):
        return pd.DataFrame(columns=["email", "password", "phone"])
    return pd.read_csv(USER_DB)

def save_users(df):
    df.to_csv(USER_DB, index=False)

def load_history():
    if not os.path.exists(FEEDBACK_HISTORY):
        return pd.DataFrame(columns=["email", "filename", "score", "date", "feedback"])
    return pd.read_csv(FEEDBACK_HISTORY)

def save_history(df):
    df.to_csv(FEEDBACK_HISTORY, index=False)

def send_email_feedback(email, subject, body):
    # Placeholder SMTP (not real)
    print(f"[SMTP Placeholder] Sending feedback to {email} with subject: {subject}")
    return True

def read_resume(file):
    if file.type == "application/pdf":
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    elif file.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        doc = Document(file)
        return "\n".join([para.text for para in doc.paragraphs])
    else:
        return None




# Session state
if "auth" not in st.session_state:
    st.session_state.auth = False
if "email" not in st.session_state:
    st.session_state.email = ""

# Auth container
with st.container():
    st.markdown("<div class='header-title'>🔐 Login / Signup</div>", unsafe_allow_html=True)
    auth_tabs = st.tabs(["🔓 Login", "🆕 Signup", "🔑 Forgot Password", "✏️ Change Password"])

    # --- Login ---
    with auth_tabs[0]:
        login_email = st.text_input("📧 Email", key="login_email")
        login_password = st.text_input("🔒 Password", type="password", key="login_pass")
        if st.button("Login", key="login_btn"):
            users = load_users()
            enc = encrypt_password(login_password)
            match = users[(users["email"] == login_email) & (users["password"] == enc)]
            if not match.empty:
                st.session_state.auth = True
                st.session_state.email = login_email
                st.success("✅ Logged in successfully!")
            else:
                st.error("❌ Invalid email or password.")

    # --- Signup ---
    with auth_tabs[1]:
        signup_email = st.text_input("📧 Email", key="signup_email")
        signup_phone = st.text_input("📱 Phone", key="signup_phone")
        signup_password = st.text_input("🔒 Password", type="password", key="signup_pass")
        signup_confirm = st.text_input("✅ Confirm Password", type="password", key="signup_confirm")
        if st.button("Signup", key="signup_btn"):
            if signup_password != signup_confirm:
                st.warning("❗ Passwords do not match.")
            elif not signup_email or not signup_phone:
                st.warning("❗ Please enter all details.")
            else:
                users = load_users()
                if signup_email in users["email"].values:
                    st.error("⚠️ Email already registered.")
                else:
                    new_user = pd.DataFrame([[signup_email, encrypt_password(signup_password), signup_phone]],
                                            columns=["email", "password", "phone"])
                    users = pd.concat([users, new_user], ignore_index=True)
                    save_users(users)
                    st.success("✅ Registered successfully. You can login now.")

    # --- Forgot Password (OTP Placeholder) ---
    with auth_tabs[2]:
        forgot_email = st.text_input("📧 Enter registered email", key="forgot_email")
        reset_method = st.radio("🔁 Send OTP via:", ["Email", "Phone"], key="otp_method")
        if st.button("Send OTP", key="send_otp_btn"):
            st.info(f"📨 OTP sent to your {reset_method} (placeholder).")
        new_pass = st.text_input("🔒 New Password", type="password", key="forgot_newpass")
        new_pass_confirm = st.text_input("✅ Confirm New Password", type="password", key="forgot_confirmpass")
        if st.button("Reset Password", key="reset_btn"):
            if new_pass != new_pass_confirm:
                st.error("❗ Passwords do not match.")
            else:
                users = load_users()
                if forgot_email not in users["email"].values:
                    st.error("🚫 Email not found.")
                else:
                    users.loc[users["email"] == forgot_email, "password"] = encrypt_password(new_pass)
                    save_users(users)
                    st.success("🔁 Password reset successful.")

    # --- Change Password (Logged In Users) ---
    with auth_tabs[3]:
        change_email = st.text_input("📧 Your Email", key="change_email")
        old_pass = st.text_input("🔑 Current Password", type="password", key="old_pass")
        new_pass2 = st.text_input("🆕 New Password", type="password", key="new_pass2")
        confirm_pass2 = st.text_input("✅ Confirm New Password", type="password", key="confirm_pass2")
        if st.button("Change Password", key="change_btn"):
            users = load_users()
            enc_old = encrypt_password(old_pass)
            if not ((users["email"] == change_email) & (users["password"] == enc_old)).any():
                st.error("❌ Incorrect current password or email.")
            elif new_pass2 != confirm_pass2:
                st.warning("❗ New passwords do not match.")
            else:
                users.loc[users["email"] == change_email, "password"] = encrypt_password(new_pass2)
                save_users(users)
                st.success("🔒 Password changed successfully.")



if st.session_state.auth:

    st.markdown("<div class='section-title'>📄 Upload Your Resume</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader("📎 Upload Resume (.pdf or .docx)", type=["pdf", "docx"], key="resume_upload")

    with col2:
        target_role = st.text_input("🎯 Target Job Role (e.g., Data Scientist)", key="target_role")

    reviewer = st.selectbox("🧠 AI Reviewer Type", ["Recruiter", "Technical Interviewer", "Startup Founder"], key="reviewer_mode")

    if uploaded_file and target_role:
        file_path = save_uploaded_resume(st.session_state.email, uploaded_file)
        st.success(f"✅ Uploaded `{uploaded_file.name}` successfully.")
        st.markdown(f"📥 File saved as: `{file_path}`")

        # Extract resume text
        resume_text = extract_text_from_file(uploaded_file)

        # AI Feedback via Groq
        with st.spinner("🧠 Generating AI feedback..."):
            prompt = f"""
            You are an AI {reviewer}. Give feedback on this resume for the role of {target_role}.
            Resume:
            {resume_text}
            """
            feedback = generate_ai_feedback(prompt)
            score = calculate_resume_score(feedback)

        # Show score with progress bar
        st.markdown("<div class='section-title'>📊 Resume Score</div>", unsafe_allow_html=True)
        st.progress(score / 100)
        st.success(f"💯 Resume Score: {score}/100")

        # Show feedback
        st.markdown("<div class='section-title'>🧾 AI Feedback Summary</div>", unsafe_allow_html=True)
        st.markdown(feedback)

        # Save feedback
        store_feedback(st.session_state.email, uploaded_file.name, feedback, score, target_role, reviewer)

        # Next: Options for rewriting, audio tips, email
    else:
        st.warning("📌 Upload your resume and enter your target role to continue.")




        # -----------------------------
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>🔄 AI Resume Rewriting</div>", unsafe_allow_html=True)

        if st.button("✍️ Rewrite Resume using AI", key="rewrite_resume"):
            with st.spinner("Rewriting your resume with AI..."):
                rewrite_prompt = f"""
                Rewrite this resume professionally for the role of {target_role} from the perspective of a {reviewer}.
                Resume Text:
                {resume_text}
                """
                rewritten_resume = generate_ai_feedback(rewrite_prompt)
                save_rewritten_resume(st.session_state.email, uploaded_file.name, rewritten_resume)

            st.text_area("📝 Rewritten Resume", rewritten_resume, height=300)

            with open(f"rewritten_{uploaded_file.name}.txt", "w", encoding="utf-8") as f:
                f.write(rewritten_resume)
            st.download_button("📄 Download Rewritten Resume", data=rewritten_resume, file_name="rewritten_resume.txt")

        # -----------------------------
        st.markdown("<div class='section-title'>🔈 Audio Tips</div>", unsafe_allow_html=True)

        if st.button("🎧 Generate Voice Tips", key="generate_audio"):
            with st.spinner("Generating voice feedback..."):
                audio_path = generate_audio_feedback(feedback)
            st.audio(audio_path)
            st.success("🔉 Voice tip generated successfully.")

        # -----------------------------
        st.markdown("<div class='section-title'>📧 Email Feedback</div>", unsafe_allow_html=True)

        if st.button("📤 Send Feedback to My Email", key="email_feedback"):
            with st.spinner("Sending email..."):
                smtp_status = send_email_feedback(
                    to_email=st.session_state.email,
                    subject="Your AI Resume Feedback",
                    body=feedback
                )
            if smtp_status:
                st.success("✅ Feedback sent to your email!")
            else:
                st.error("❌ Failed to send email (SMTP placeholder active).")




        # -----------------------------
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>📂 My Resume History</div>", unsafe_allow_html=True)

        history = load_user_history(st.session_state.email)
        if history:
            for entry in history:
                with st.expander(f"📝 {entry['filename']} - {entry['timestamp']}"):
                    st.markdown(f"**🔍 Feedback:** {entry['feedback']}")
                    st.markdown(f"**📈 Score:** {entry['score']}%")
                    if st.button("🗑️ Delete Entry", key=f"delete_{entry['timestamp']}"):
                        delete_history_entry(st.session_state.email, entry['timestamp'])
                        st.success("🧹 Entry deleted. Please refresh to update.")
        else:
            st.info("📁 No resume history found.")

        # -----------------------------
        st.markdown("<div class='section-title'>🧹 Cleanup Tools</div>", unsafe_allow_html=True)

        if st.button("🧼 Clear Audio & Feedback", key="cleanup_audio_feedback"):
            st.session_state.pop("audio_feedback", None)
            st.session_state.pop("ai_feedback", None)
            st.success("✅ Audio and feedback cleared.")

        # -----------------------------
        st.markdown("<div class='section-title'>👑 Admin Dashboard</div>", unsafe_allow_html=True)

        if st.session_state.email == "admin@example.com":
            user_df = load_all_user_data()
            resume_stats = get_resume_stats()

            st.subheader("📊 User & Resume Stats")
            st.write(f"👤 Total Users: {len(user_df)}")
            st.write(f"📄 Total Resumes: {resume_stats['total_resumes']}")
            st.write(f"🎯 Top Roles: {', '.join(resume_stats['top_roles'])}")

            st.subheader("📈 User Signup Trends")
            chart_data = prepare_signup_chart(user_df)
            st.line_chart(chart_data)
        else:
            st.info("🔒 Admin dashboard is only visible to admin@example.com.")



        # -----------------------------
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align: center; padding: 10px; color: gray; font-size: 14px;'>
            🚀 <b>AI Resume Feedback Bot</b> by Shatu | Made with ❤️ using Streamlit & Groq API
        </div>
        """, unsafe_allow_html=True)

# ======================= #
#   Utility Functions     #
# ======================= #

def save_user(email, password, phone):
    df = load_user_data()
    new_user = pd.DataFrame([{'email': email, 'password': password, 'phone': phone}])
    df = pd.concat([df, new_user], ignore_index=True)
    df.to_csv(USER_DB, index=False)

def save_history(email, filename, feedback, score, rewritten, role):
    df = load_resume_history()
    new_entry = pd.DataFrame([{
        'email': email, 'filename': filename,
        'feedback': feedback, 'score': score,
        'rewritten': rewritten, 'timestamp': str(datetime.datetime.now()),
        'role': role
    }])
    df = pd.concat([df, new_entry], ignore_index=True)
    df.to_csv(HISTORY_DB, index=False)

def load_user_data():
    if os.path.exists(USER_DB):
        return pd.read_csv(USER_DB)
    else:
        return pd.DataFrame(columns=['email', 'password', 'phone'])

def load_resume_history():
    if os.path.exists(HISTORY_DB):
        return pd.read_csv(HISTORY_DB)
    else:
        return pd.DataFrame(columns=['email', 'filename', 'feedback', 'score', 'rewritten', 'timestamp', 'role'])

def load_user_history(email):
    df = load_resume_history()
    return df[df['email'] == email].to_dict(orient='records')

def delete_history_entry(email, timestamp):
    df = load_resume_history()
    df = df[~((df['email'] == email) & (df['timestamp'] == timestamp))]
    df.to_csv(HISTORY_DB, index=False)

def load_all_user_data():
    return load_user_data()

def get_resume_stats():
    df = load_resume_history()
    top_roles = df['role'].value_counts().head(3).index.tolist()
    return {
        "total_resumes": len(df),
        "top_roles": top_roles
    }

def prepare_signup_chart(user_df):
    user_df['signup_date'] = pd.to_datetime(user_df.get('timestamp', pd.Timestamp.now()))
    chart_data = user_df.groupby(user_df['signup_date'].dt.date).size()
    return chart_data

# ======================= #
#       Custom CSS        #
# ======================= #
st.markdown("""
    <style>
        .section-title {
            font-size: 20px;
            font-weight: bold;
            color: #3B82F6;
            margin-top: 25px;
        }
        .stButton>button {
            background-color: #6366F1;
            color: white;
            border-radius: 8px;
            padding: 0.5em 1.5em;
        }
        .stTextInput>div>div>input {
            border-radius: 8px;
        }
        .css-1cpxqw2 {
            background-color: #f0f4ff;
        }
    </style>
""", unsafe_allow_html=True)
