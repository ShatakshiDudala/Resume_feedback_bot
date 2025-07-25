# app.py (Part 1/6) - App Setup, Login/Signup with Session Management

import streamlit as st
from pathlib import Path
import json
import os
import random
import string
from datetime import datetime
from gtts import gTTS
from io import BytesIO
import base64

# Page config
st.set_page_config(page_title="AI Resume Feedback Bot", page_icon="🧠", layout="wide")

# User data path
USER_DB = "users.json"
os.makedirs("feedback_data", exist_ok=True)

# Load users
def load_users():
    if Path(USER_DB).exists():
        with open(USER_DB, "r") as f:
            return json.load(f)
    return {}

# Save users
def save_users(users):
    with open(USER_DB, "w") as f:
        json.dump(users, f, indent=2)

# Colorful background styling
def set_background():
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(135deg, #e0f7fa, #fce4ec);
            font-family: 'Segoe UI', sans-serif;
        }
        .login-box, .signup-box {
            background-color: #ffffffcc;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 2px 2px 12px #aaa;
            max-width: 400px;
            margin: auto;
        }
        .title {
            text-align: center;
            color: #6a1b9a;
            font-size: 2rem;
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# Session state defaults
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "dashboard_page" not in st.session_state:
    st.session_state.dashboard_page = "home"

# Background
set_background()

# Login & Signup
def login_signup_page():
    st.markdown("<div class='title'>🚀 AI Resume Feedback Bot</div>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🔐 Login", "🆕 Signup"])

    with tab1:
        with st.container():
            st.markdown("<div class='login-box'>", unsafe_allow_html=True)
            email_login = st.text_input("📧 Email", key="login_email")
            password_login = st.text_input("🔑 Password", type="password", key="login_password")
            if st.button("Login", key="login_btn"):
                users = load_users()
                if email_login in users and users[email_login]["password"] == password_login:
                    st.session_state.logged_in = True
                    st.session_state.current_user = email_login
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
            st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        with st.container():
            st.markdown("<div class='signup-box'>", unsafe_allow_html=True)
            email_signup = st.text_input("📧 Email", key="signup_email")
            password_signup = st.text_input("🔑 Password", type="password", key="signup_pass1")
            confirm_signup = st.text_input("🔁 Confirm Password", type="password", key="signup_pass2")
            if st.button("Create Account", key="signup_btn"):
                users = load_users()
                if email_signup in users:
                    st.warning("Account already exists.")
                elif password_signup != confirm_signup:
                    st.warning("Passwords do not match.")
                else:
                    users[email_signup] = {"password": password_signup, "is_admin": False}
                    save_users(users)
                    st.success("Account created! You can now login.")
                    st.experimental_rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# Entry point
if not st.session_state.logged_in:
    login_signup_page()
else:
    # Dashboard comes next
    st.experimental_set_query_params(logged_in="true")




# app.py (Part 2/6) – Dashboard Navigation + Resume Upload UI (Post-login)

import uuid
import docx2txt
import PyPDF2

# Sidebar Navigation Menu
def dashboard():
    st.sidebar.markdown(
        """
        <style>
        section[data-testid="stSidebar"] {
            background-color: #ede7f6;
        }
        .sidebar-title {
            color: #4a148c;
            font-size: 1.5rem;
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("<div class='sidebar-title'>🎯 Dashboard Menu</div>", unsafe_allow_html=True)
    dashboard_menu = st.sidebar.radio(
        "Select an option",
        ["📤 Upload Resume", "🤖 GPT Feedback", "🗣️ Audio Tips", "✍️ Rewrite Resume", 
         "📨 Send to Mail", "📂 Feedback History", "📊 Admin Panel", "🔑 Change Password", 
         "🔁 Forgot Password", "🚪 Logout"]
    )

    st.title("✨ Welcome to Your AI Resume Assistant Dashboard")

    # Resume Upload Section
    if dashboard_menu == "📤 Upload Resume":
        st.header("📄 Upload Your Resume (PDF or DOCX)")
        uploaded_file = st.file_uploader("Choose your resume file:", type=["pdf", "docx"], key="resume_upload")

        if uploaded_file:
            # Save file
            user_folder = f"feedback_data/{st.session_state.current_user}"
            os.makedirs(user_folder, exist_ok=True)
            unique_id = str(uuid.uuid4())
            file_path = os.path.join(user_folder, f"{unique_id}_{uploaded_file.name}")
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Extract text
            resume_text = extract_text_from_resume(uploaded_file)
            st.success("✅ Resume uploaded and parsed successfully!")

            # Store in session
            st.session_state.resume_text = resume_text
            st.session_state.uploaded_file_path = file_path

            # Target Role
            st.session_state.target_role = st.text_input("🎯 Enter your target role:", key="target_role_input")

            st.info("✅ Now switch to '🤖 GPT Feedback' tab to get AI-powered review.")

    return dashboard_menu

# Resume Text Extraction
def extract_text_from_resume(uploaded_file):
    file_type = uploaded_file.name.split(".")[-1].lower()
    if file_type == "pdf":
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    elif file_type == "docx":
        return docx2txt.process(uploaded_file)
    else:
        return "Unsupported file type"

# Call the dashboard if logged in
if st.session_state.logged_in:
    current_tab = dashboard()




        if dashboard_menu == "📤 Upload Resume":
            st.subheader("📤 Upload Your Resume")
            uploaded_file = st.file_uploader("Upload Resume (PDF or DOCX)", type=["pdf", "docx"], key="resume_uploader")
            target_role = st.text_input("🎯 Enter your Target Role", placeholder="e.g., Data Scientist", key="target_role")

            if st.button("📊 Analyze Resume"):
                if uploaded_file and target_role:
                    with st.spinner("Reading and analyzing resume..."):
                        file_extension = os.path.splitext(uploaded_file.name)[1]
                        resume_text = extract_text_from_file(uploaded_file, file_extension)

                        # --- GPT Feedback ---
                        feedback_prompt = f"Give a detailed professional resume review for someone applying to the role of {target_role}. Here's the resume:\n\n{resume_text}"
                        resume_feedback = generate_feedback(feedback_prompt)

                        # --- Resume Score ---
                        score_prompt = f"Give a resume score out of 10 for this resume based on its effectiveness for the role of {target_role} and justify it briefly:\n\n{resume_text}"
                        score_response = generate_feedback(score_prompt)

                        # --- Resume Rewriting ---
                        rewrite_prompt = f"Rewrite and improve the resume below for the role of {target_role}. Make it ATS-friendly and impactful:\n\n{resume_text}"
                        rewritten_resume = generate_feedback(rewrite_prompt)

                        # --- Audio Feedback ---
                        audio_tip = f"Here's a tip for improving your resume for a {target_role} role: {resume_feedback.split('.')[0]}"
                        audio_file = "audio_tip.mp3"
                        tts = gTTS(audio_tip)
                        tts.save(audio_file)

                        # Save history
                        feedback_data = {
                            "feedback": resume_feedback,
                            "score": score_response,
                            "rewritten": rewritten_resume,
                            "audio_file": audio_file,
                            "role": target_role,
                            "uploaded_on": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        user_feedbacks.setdefault(st.session_state.user_email, []).append(feedback_data)

                        # Display Results
                        st.success("✅ Resume analysis complete!")
                        st.markdown("### 💡 AI Feedback")
                        st.write(resume_feedback)

                        st.markdown("### 🏅 Resume Score")
                        st.info(score_response)

                        st.markdown("### 📝 Rewritten Resume (AI-generated)")
                        st.code(rewritten_resume, language='markdown')

                        st.markdown("### 🔊 Audio Tip")
                        st.audio(audio_file, format='audio/mp3')

                        st.markdown("### 📧 Send Feedback via Email")
                        if st.button("📨 Send to Email"):
                            email_subject = f"Your Resume Feedback for {target_role}"
                            email_body = f"Hello,\n\nHere is the feedback for your resume:\n\n{resume_feedback}\n\nScore: {score_response}\n\nRewritten Resume:\n{rewritten_resume}"
                            try:
                                send_email(st.session_state.user_email, email_subject, email_body)
                                st.success("✅ Email sent successfully!")
                            except Exception as e:
                                st.error(f"❌ Failed to send email: {str(e)}")

                else:
                    st.warning("⚠️ Please upload a resume and enter your target role.")




# --------------------------- Feedback History Section --------------------------- #

elif dashboard_menu == "📂 Feedback History":
    st.subheader("📂 Your Feedback History")
    st.markdown("---")
    user_history = feedback_history.get(current_user, [])

    if user_history:
        for i, entry in enumerate(user_history[::-1]):
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(f"""
                <div style='background-color:#f3f0ff;padding:15px;border-radius:10px;margin-bottom:10px'>
                <b>🧾 Target Role:</b> {entry['target_role']}<br>
                <b>📈 Score:</b> {entry['score']}<br>
                <b>🗒️ Feedback:</b> {entry['feedback']}<br>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                if st.button("🗑️", key=f"delete_{i}"):
                    user_history.remove(entry)
                    st.success("Deleted entry!")
                    break
    else:
        st.info("No feedback history yet.")

# --------------------------- Admin Dashboard Section --------------------------- #

elif dashboard_menu == "👑 Admin Dashboard":
    st.subheader("👑 Admin Panel: Usage Overview")
    st.markdown("---")

    # Show number of users
    num_users = len(users)
    num_feedback = sum(len(v) for v in feedback_history.values())

    col1, col2 = st.columns(2)
    col1.metric("👥 Total Users", num_users)
    col2.metric("📄 Total Feedbacks", num_feedback)

    # Users list
    with st.expander("📜 Registered Users"):
        for user, data in users.items():
            st.markdown(f"""
            <div style='background-color:#e1f5fe;padding:10px;border-radius:8px;margin-bottom:5px'>
            <b>Email:</b> {user} <br>
            <b>Phone:</b> {data['phone']}
            </div>
            """, unsafe_allow_html=True)

    # Feedback trends by score range (simple)
    import matplotlib.pyplot as plt
    from collections import Counter

    score_ranges = []
    for history in feedback_history.values():
        for item in history:
            score = int(item.get('score', 0))
            if score < 40:
                score_ranges.append("0-39")
            elif score < 70:
                score_ranges.append("40-69")
            else:
                score_ranges.append("70-100")

    if score_ranges:
        st.markdown("### 📊 Feedback Score Distribution")
        count = Counter(score_ranges)
        plt.bar(count.keys(), count.values(), color=['#FF6666', '#FFCC66', '#66FF66'])
        plt.xlabel("Score Range")
        plt.ylabel("Count")
        st.pyplot(plt)
    else:
        st.info("No feedback data yet to show trends.")




# ------------------ AI Resume Rewriting ------------------
def ai_rewrite_resume(api_key, resume_text, role):
    try:
        prompt = f"Rewrite the following resume to better suit the target role of '{role}'. Improve clarity, professionalism, and relevance:\n\n{resume_text}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama3-8b-8192",
            "messages": [
                {"role": "system", "content": "You are a professional resume writing assistant."},
                {"role": "user", "content": prompt}
            ]
        }
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
        rewritten = response.json()['choices'][0]['message']['content']
        return rewritten
    except Exception as e:
        return f"❌ Failed to rewrite resume: {e}"

# ------------------ Audio Tips via gTTS ------------------
def generate_audio(text, filename="audio_feedback.mp3"):
    try:
        speech = gTTS(text)
        path = os.path.join("temp", filename)
        os.makedirs("temp", exist_ok=True)
        speech.save(path)
        return path
    except Exception as e:
        return None

# ------------------ Email Feedback (Placeholder) ------------------
def send_feedback_email(to_email, subject, body, resume_file=None):
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = 'noreply@example.com'
        msg['To'] = to_email
        msg.set_content(body)

        if resume_file:
            with open(resume_file, 'rb') as f:
                file_data = f.read()
                file_name = os.path.basename(resume_file)
            msg.add_attachment(file_data, maintype='application', subtype='octet-stream', filename=file_name)

        # Placeholder - not configured with real SMTP
        # smtp = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        # smtp.login("your_email", "your_password")
        # smtp.send_message(msg)
        # smtp.quit()

        return True
    except Exception as e:
        return False

# ------------------ UI - AI Feedback Buttons ------------------
if dashboard_menu == "📄 Resume Upload":
    st.markdown("### 🔍 Analyze Your Resume")
    if st.button("🧠 Analyze Resume", use_container_width=True, type="primary"):
        if resume_text and target_role:
            with st.spinner("Analyzing your resume..."):
                feedback = analyze_resume_groq(api_key, resume_text, target_role)
                score = min(100, max(30, 60 + feedback.lower().count("good") * 10 - feedback.lower().count("needs improvement") * 5))
                st.success("✅ Resume analysis completed.")
                st.markdown("### ✨ Feedback")
                st.info(feedback)

                st.progress(score / 100.0, text=f"Score: {score}/100")

                st.session_state['feedback'] = feedback
                st.session_state['score'] = score

                # Save feedback
                save_feedback(user_id, resume_text, target_role, feedback, score)

    if st.button("🔄 Rewrite Resume (AI)", use_container_width=True):
        if resume_text and target_role:
            with st.spinner("Rewriting resume..."):
                rewritten = ai_rewrite_resume(api_key, resume_text, target_role)
                st.markdown("### ✍️ AI-Rewritten Resume")
                st.code(rewritten)
                st.download_button("⬇️ Download Rewritten Resume", rewritten, file_name="rewritten_resume.txt")

    if st.button("🔈 Voice Tips", use_container_width=True):
        if 'feedback' in st.session_state:
            with st.spinner("Generating audio..."):
                audio_path = generate_audio(st.session_state['feedback'])
                if audio_path:
                    st.audio(audio_path)
                else:
                    st.warning("Could not generate audio.")
        else:
            st.warning("Please analyze your resume first.")

    if st.button("📧 Send Feedback to Email", use_container_width=True):
        if 'feedback' in st.session_state:
            success = send_feedback_email(user_id, "Your Resume Feedback", st.session_state['feedback'])
            if success:
                st.success("📨 Email sent (simulated).")
            else:
                st.error("❌ Failed to send email.")




        elif dashboard_menu == "📂 Feedback History":
            st.subheader("📂 Your Resume Feedback History")
            history = user_data.get(email, {}).get("history", [])
            if history:
                for idx, item in enumerate(history[::-1]):
                    st.markdown(f"**🗂️ Resume #{len(history)-idx}** - {item['timestamp']}")
                    st.markdown(f"🎯 **Target Role:** `{item['target_role']}`")
                    st.markdown(f"📄 **Feedback:**")
                    st.code(item["feedback"], language='markdown')
                    st.markdown(f"📊 **Score:** `{item['score']}/100`")
                    if st.button(f"🗑️ Delete Resume #{len(history)-idx}", key=f"delete_{idx}"):
                        user_data[email]["history"].remove(item)
                        save_user_data(user_data)
                        st.success("Deleted successfully.")
                        st.experimental_rerun()
            else:
                st.info("No history found yet.")

        elif dashboard_menu == "👑 Admin Dashboard":
            st.subheader("👑 Admin Dashboard")
            total_users = len(user_data)
            total_uploads = sum(len(data.get("history", [])) for data in user_data.values())
            st.metric("👤 Total Users", total_users)
            st.metric("📂 Total Resume Uploads", total_uploads)

            chart_data = {
                "User": [],
                "Uploads": []
            }
            for email, data in user_data.items():
                chart_data["User"].append(email)
                chart_data["Uploads"].append(len(data.get("history", [])))
            chart_df = pd.DataFrame(chart_data)
            if not chart_df.empty:
                st.bar_chart(chart_df.set_index("User"))
            else:
                st.info("No user data yet to show.")

# Final cleanup
hide_footer = """
    <style>
    footer {visibility: hidden;}
    .block-container {padding-top: 2rem;}
    </style>
"""
st.markdown(hide_footer, unsafe_allow_html=True)
