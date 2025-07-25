import streamlit as st
import pandas as pd
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from gtts import gTTS
from PyPDF2 import PdfReader
import base64
import time

# Load .env for API keys
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Groq client setup
client = Groq(api_key=GROQ_API_KEY)

# File paths
USER_DB = "users.csv"
HISTORY_DB = "history.csv"

# Session init
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# Utility: Load or create user database
def load_user_db():
    if not os.path.exists(USER_DB):
        df = pd.DataFrame(columns=["email", "password", "phone"])
        df.to_csv(USER_DB, index=False)
    return pd.read_csv(USER_DB)

# Utility: Signup new user
def signup_user(email, password, phone):
    df = load_user_db()
    if email in df['email'].values:
        return False
    new_user = pd.DataFrame([{'email': email, 'password': password, 'phone': phone}])
    df = pd.concat([df, new_user], ignore_index=True)
    df.to_csv(USER_DB, index=False)
    return True

# Utility: Authenticate login
def login_user(email, password):
    df = load_user_db()
    if ((df['email'] == email) & (df['password'] == password)).any():
        return True
    return False

# Page layout
st.set_page_config(page_title="AI Resume Feedback Bot", layout="wide")
st.markdown("<h1 style='text-align: center;'>📄 AI Resume Feedback Bot</h1>", unsafe_allow_html=True)




# Forgot Password via phone/email
def forgot_password(email_or_phone, new_password):
    df = load_user_db()
    mask = (df['email'] == email_or_phone) | (df['phone'] == email_or_phone)
    if mask.any():
        df.loc[mask, 'password'] = new_password
        df.to_csv(USER_DB, index=False)
        return True
    return False

# Change Password
def change_password(email, current_password, new_password):
    df = load_user_db()
    user_row = df[(df['email'] == email) & (df['password'] == current_password)]
    if not user_row.empty:
        df.loc[user_row.index, 'password'] = new_password
        df.to_csv(USER_DB, index=False)
        return True
    return False

# Sidebar for navigation
if st.session_state.logged_in:
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3178/3178158.png", width=100)
        st.markdown(f"**Logged in as:** `{st.session_state.user_email}`")

        nav = st.radio("🔧 Navigate", [
            "📄 Upload Resume",
            "🧠 Get Feedback",
            "🔄 Rewritten Resume",
            "🔈 Audio Tips",
            "📧 Email Feedback",
            "📂 Resume History",
            "🔐 Change Password",
            "❓ Forgot Password",
            "🧹 Clear Feedback/Audio",
            "👑 Admin Dashboard",
            "🚪 Logout"
        ])

        st.session_state.page = nav

    if st.session_state.page == "🚪 Logout":
        st.success("You’ve been logged out.")
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.experimental_rerun()
else:
    auth_tabs = st.tabs(["🔑 Login", "🆕 Signup"])
    
    with auth_tabs[0]:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if login_user(email, password):
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.session_state.is_admin = (email == "admin@example.com")
                st.success("Login successful.")
                st.experimental_rerun()
            else:
                st.error("Invalid credentials.")

    with auth_tabs[1]:
        email = st.text_input("Email (for signup)")
        password = st.text_input("Password", type="password")
        phone = st.text_input("Phone Number")
        if st.button("Signup"):
            if signup_user(email, password, phone):
                st.success("Signup successful. Please login.")
            else:
                st.error("User already exists.")

    st.stop()  # Don't render further if not logged in




# ================================
# 📄 Upload Resume & Feedback
# ================================

if st.session_state.page == "📄 Upload Resume":
    st.header("📄 Resume Analysis")
    uploaded_file = st.file_uploader("Upload .pdf or .docx", type=["pdf", "docx"])
    st.session_state.uploaded_file = uploaded_file

    if uploaded_file:
        file_path = os.path.join("uploads", uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"Uploaded: `{uploaded_file.name}`")

        # Extract text
        if uploaded_file.name.endswith(".pdf"):
            resume_text = extract_text_from_pdf(file_path)
        else:
            resume_text = extract_text_from_docx(file_path)
        st.session_state.resume_text = resume_text
        st.write("✅ Resume Text Extracted")

if st.session_state.page == "🧠 Get Feedback":
    st.header("🧠 AI Resume Feedback")
    resume_text = st.session_state.get("resume_text", None)

    if not resume_text:
        st.warning("Please upload your resume first.")
    else:
        role = st.text_input("🎯 Enter Target Role (e.g., Data Scientist)")
        reviewer_mode = st.selectbox("🧠 Choose Reviewer Mode", [
            "General", "Recruiter", "Technical", "Academic", "Startup"
        ])

        prompt = f"""You're an expert {reviewer_mode} resume reviewer.
Role applied: {role}
Resume:
{resume_text}
Give detailed feedback with strengths, weaknesses, and suggestions. Provide a rating out of 100."""

        if st.button("🔍 Generate Feedback"):
            with st.spinner("Analyzing resume..."):
                response = client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=[{"role": "user", "content": prompt}]
                )
                feedback = response.choices[0].message.content
                st.session_state.feedback = feedback

            # Extract Score
            score_match = re.search(r'(\d{1,3})/100', feedback)
            score = int(score_match.group(1)) if score_match else 70
            st.progress(score)
            st.write("### 📋 Feedback Summary")
            st.markdown(feedback)

            # Save to history
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_entry = {
                'email': st.session_state.user_email,
                'timestamp': timestamp,
                'role': role,
                'score': score,
                'feedback': feedback.replace('\n', ' ')
            }
            if os.path.exists(HISTORY_CSV):
                history_df = pd.read_csv(HISTORY_CSV)
                history_df = pd.concat([history_df, pd.DataFrame([new_entry])], ignore_index=True)
            else:
                history_df = pd.DataFrame([new_entry])
            history_df.to_csv(HISTORY_CSV, index=False)




# ================================
# ✍️ Rewritten Resume (AI)
# ================================

if st.session_state.page == "✍️ Rewritten Resume":
    st.header("✍️ Resume Rewrite (ATS Optimized)")
    feedback = st.session_state.get("feedback", "")
    resume_text = st.session_state.get("resume_text", "")

    if resume_text and feedback:
        prompt = f"""You are an AI resume writer. Rewrite this resume to be more ATS-friendly and aligned with feedback.
Resume:
{resume_text}

Feedback:
{feedback}

Return the improved resume:"""

        if st.button("🔁 Rewrite Resume"):
            with st.spinner("Rewriting resume..."):
                response = client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=[{"role": "user", "content": prompt}]
                )
                rewritten = response.choices[0].message.content
                st.session_state.rewritten = rewritten
                st.success("✅ Resume Rewritten")

    if "rewritten" in st.session_state:
        st.subheader("📄 Improved Resume")
        st.code(st.session_state.rewritten, language="markdown")


# ================================
# 🔈 Audio Tips with gTTS
# ================================

if st.session_state.page == "🔈 Audio Tips":
    st.header("🔈 Voice-Based Resume Tips")

    feedback = st.session_state.get("feedback", "")
    if not feedback:
        st.warning("⚠️ Generate feedback first!")
    else:
        audio_path = os.path.join("audio", f"{st.session_state.user_email}.mp3")
        if not os.path.exists(audio_path):
            tts = gTTS(feedback)
            tts.save(audio_path)

        st.audio(audio_path)
        st.info("💡 Click play to hear your feedback!")


# ================================
# 📥 Download Feedback PDF
# ================================

if st.session_state.page == "📥 Download Feedback":
    st.header("📥 Export Feedback")

    feedback = st.session_state.get("feedback", "")
    score = st.session_state.get("score", 0)

    if feedback:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, f"Resume Feedback\n\nScore: {score}/100\n\n{feedback}")
        pdf_path = f"downloads/{st.session_state.user_email}_feedback.pdf"
        pdf.output(pdf_path)

        with open(pdf_path, "rb") as f:
            st.download_button("📥 Download PDF", f, file_name="resume_feedback.pdf")
    else:
        st.warning("Generate feedback first.")




# ================================
# 🧾 Resume Feedback History
# ================================

if st.session_state.page == "📂 Resume History":
    st.header("📂 Your Resume Feedback History")
    df = pd.read_csv("history.csv")

    user_df = df[df['email'] == st.session_state.user_email]

    if not user_df.empty:
        st.dataframe(user_df[['timestamp', 'target_role', 'score']].sort_values(by='timestamp', ascending=False))

        if st.button("🗑️ Delete All My Feedback"):
            df = df[df['email'] != st.session_state.user_email]
            df.to_csv("history.csv", index=False)
            st.success("🧹 Your feedback history has been deleted.")
    else:
        st.info("No feedback history found.")


# ================================
# 👑 Admin Dashboard
# ================================

if st.session_state.page == "👑 Admin Dashboard":
    st.header("👑 Admin Metrics")
    df = pd.read_csv("history.csv")
    users = df['email'].nunique()
    resumes = len(df)
    avg_score = round(df['score'].mean(), 2)

    col1, col2, col3 = st.columns(3)
    col1.metric("👥 Total Users", users)
    col2.metric("📄 Resumes Analyzed", resumes)
    col3.metric("📊 Average Score", avg_score)

    # Chart: Score distribution
    st.subheader("📈 Score Distribution")
    st.bar_chart(df['score'].value_counts().sort_index())

    # Chart: Target roles popularity
    st.subheader("💼 Target Role Popularity")
    role_counts = df['target_role'].value_counts()
    st.bar_chart(role_counts)


# ================================
# 🧹 Audio Cleanup Utility
# ================================

if st.session_state.page == "🧹 Cleanup Audio":
    st.header("🧹 Cleanup Audio Files")

    audio_dir = "audio"
    if os.path.exists(audio_dir):
        for f in os.listdir(audio_dir):
            os.remove(os.path.join(audio_dir, f))
        st.success("✅ All audio files cleaned.")
    else:
        st.info("No audio files found.")




# ================================
# 🔐 Change Password
# ================================

if st.session_state.page == "🔐 Change Password":
    st.header("🔐 Change Your Password")
    email = st.session_state.user_email
    df = pd.read_csv("users.csv")

    current_pass = st.text_input("🔑 Current Password", type="password")
    new_pass = st.text_input("🆕 New Password", type="password")
    confirm_pass = st.text_input("✅ Confirm New Password", type="password")

    if st.button("🔁 Update Password"):
        user_row = df[df['email'] == email]
        if not user_row.empty and user_row.iloc[0]['password'] == current_pass:
            if new_pass == confirm_pass:
                df.loc[df['email'] == email, 'password'] = new_pass
                df.to_csv("users.csv", index=False)
                st.success("✅ Password updated successfully!")
            else:
                st.error("❌ New passwords do not match.")
        else:
            st.error("❌ Incorrect current password.")


# ================================
# ❓ Forgot Password (Placeholder)
# ================================

if st.session_state.page == "❓ Forgot Password":
    st.header("❓ Forgot Password")
    st.markdown("Please choose a method to reset your password:")

    reset_method = st.radio("Select Method", ["📧 Email Verification", "📱 Phone OTP"])
    if reset_method == "📧 Email Verification":
        email = st.text_input("📧 Enter your email")
        st.button("📨 Send Reset Link (Mock)")
    else:
        phone = st.text_input("📱 Enter your phone number")
        st.button("📩 Send OTP (Mock)")

    st.info("⚠️ OTP and email sending not implemented. This is a UI placeholder.")


# ================================
# 🎨 UI Styling & Sidebar
# ================================

st.markdown("""
<style>
.sidebar .sidebar-content {
    background-color: #f0f2f6;
    color: #333;
}
.reportview-container .markdown-text-container {
    font-family: 'Segoe UI', sans-serif;
}
h1, h2, h3 {
    color: #256D85;
}
.stButton>button {
    background-color: #256D85;
    color: white;
}
.stButton>button:hover {
    background-color: #1b4f66;
}
.stTextInput>div>input {
    background-color: #ffffff;
}
</style>
""", unsafe_allow_html=True)

# Default home/dashboard display if no page selected
if st.session_state.page == "🏠 Home":
    st.title("🎓 Welcome to AI Resume Feedback Bot")
    st.markdown("Upload your resume, receive feedback, and improve with AI-powered suggestions!")

    st.markdown("""
    ### 🔧 Features
    - 📄 Upload resume (.pdf or .docx)
    - 🤖 Get AI feedback with score
    - 🔊 Hear voice tips
    - 📥 Export improved resume
    - 👑 Admin dashboard & user history
    """)
