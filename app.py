import streamlit as st
import os
import hashlib
import sqlite3
from datetime import datetime
import random
import string

# ---------- Database Setup ----------
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        phone TEXT,
        password TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT,
        resume_filename TEXT,
        feedback TEXT,
        rewritten_resume TEXT,
        timestamp TEXT
    )
''')
conn.commit()

# ---------- Utility Functions ----------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password, hashed):
    return hash_password(password) == hashed

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

# ---------- Page Config ----------
st.set_page_config(page_title="AI Resume Feedback Bot", layout="wide")

# ---------- Session State ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "auth"

# ---------- Styling ----------
st.markdown("""
    <style>
        .main {
            background: linear-gradient(to right, #f9f9f9, #d1e8ff);
            padding: 30px;
            border-radius: 15px;
        }
        .stButton > button {
            background-color: #4CAF50;
            color: white;
            padding: 10px;
            width: 100%;
            border-radius: 10px;
            font-weight: bold;
        }
        .stTextInput > div > input {
            border: 2px solid #4CAF50;
            border-radius: 8px;
        }
    </style>
""", unsafe_allow_html=True)

# ---------- Auth Page ----------
def show_auth():
    st.title("🔐 Welcome to Resume Feedback Bot")
    tabs = st.tabs(["Login", "Signup", "Forgot Password", "Change Password"])

    # ---------- LOGIN ----------
    with tabs[0]:
        st.subheader("🔑 Login")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            cursor.execute("SELECT password FROM users WHERE email=?", (login_email,))
            result = cursor.fetchone()
            if result and check_password(login_password, result[0]):
                st.success("✅ Logged in successfully!")
                st.session_state.logged_in = True
                st.session_state.user_email = login_email
                st.session_state.current_page = "dashboard"
            else:
                st.error("❌ Invalid email or password.")

    # ---------- SIGNUP ----------
    with tabs[1]:
        st.subheader("📝 Create Account")
        name = st.text_input("Full Name", key="signup_name")
        email = st.text_input("Email", key="signup_email")
        phone = st.text_input("Phone Number", key="signup_phone")
        password = st.text_input("Password", type="password", key="signup_pass")
        confirm_password = st.text_input("Confirm Password", type="password", key="signup_cpass")

        if st.button("Signup"):
            if password != confirm_password:
                st.warning("⚠️ Passwords do not match.")
            else:
                try:
                    hashed_pw = hash_password(password)
                    cursor.execute("INSERT INTO users (name, email, phone, password) VALUES (?, ?, ?, ?)",
                                   (name, email, phone, hashed_pw))
                    conn.commit()
                    st.success("🎉 Account created. Please login.")
                    # Clear form after signup
                    for key in ["signup_name", "signup_email", "signup_phone", "signup_pass", "signup_cpass"]:
                        st.session_state[key] = ""
                except sqlite3.IntegrityError:
                    st.error("⚠️ Email already exists.")

    # ---------- FORGOT PASSWORD ----------
    with tabs[2]:
        st.subheader("🔁 Forgot Password (OTP Placeholder)")
        f_email = st.text_input("Enter your registered email", key="fp_email")
        f_otp = st.text_input("Enter OTP (sent to email)", key="fp_otp")
        f_newpass = st.text_input("New Password", type="password", key="fp_new")
        if st.button("Reset Password"):
            # Placeholder: Assume OTP is always valid
            hashed = hash_password(f_newpass)
            cursor.execute("UPDATE users SET password=? WHERE email=?", (hashed, f_email))
            conn.commit()
            st.success("✅ Password reset successfully.")

    # ---------- CHANGE PASSWORD ----------
    with tabs[3]:
        st.subheader("🔒 Change Password")
        ch_email = st.text_input("Email", key="cp_email")
        old_pass = st.text_input("Current Password", type="password", key="cp_old")
        new_pass = st.text_input("New Password", type="password", key="cp_new")

        if st.button("Change Password"):
            cursor.execute("SELECT password FROM users WHERE email=?", (ch_email,))
            data = cursor.fetchone()
            if data and check_password(old_pass, data[0]):
                hashed = hash_password(new_pass)
                cursor.execute("UPDATE users SET password=? WHERE email=?", (hashed, ch_email))
                conn.commit()
                st.success("✅ Password changed.")
            else:
                st.error("❌ Incorrect current password.")




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
