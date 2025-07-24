import streamlit as st
import pandas as pd
import os
import random
import string
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
import smtplib
from email.message import EmailMessage

load_dotenv()

# File paths
USERS_CSV = "users.csv"
HISTORY_CSV = "history.csv"

# Initialize Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Utility: Send OTP email
def send_email_otp(to_email, otp):
    msg = EmailMessage()
    msg.set_content(f"Your OTP to reset your password is: {otp}")
    msg["Subject"] = "Password Reset OTP"
    msg["From"] = os.getenv("EMAIL_ADDRESS")
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_PASSWORD"))
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Email failed: {e}")
        return False

# Utility: Generate OTP
def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

# ========== User Authentication ==========

def load_users():
    if os.path.exists(USERS_CSV):
        try:
            df = pd.read_csv(USERS_CSV)
            if 'email' not in df.columns:
                df = pd.DataFrame(columns=['email', 'password', 'phone'])
        except Exception:
            df = pd.DataFrame(columns=['email', 'password', 'phone'])
    else:
        df = pd.DataFrame(columns=['email', 'password', 'phone'])
    return df


def save_users(df):
    df.to_csv(USERS_CSV, index=False)


def login_user(email, password):
    df = load_users()
    user = df[(df["email"] == email) & (df["password"] == password)]
    return user if not user.empty else None


def signup_user(email, password, phone):
    df = load_users()
    if email in df["email"].values:
        return False
    new_user = pd.DataFrame([{'email': email, 'password': password, 'phone': phone}])
    df = pd.concat([df, new_user], ignore_index=True)
    save_users(df)
    return True


def change_password(email, current_pwd, new_pwd):
    df = load_users()
    user = df[(df["email"] == email) & (df["password"] == current_pwd)]
    if not user.empty:
        df.loc[df["email"] == email, "password"] = new_pwd
        save_users(df)
        return True
    return False


def send_otp(to):
    otp = str(random.randint(100000, 999999))
    # In real apps: integrate with Twilio, SendGrid, etc.
    st.session_state["otp"] = otp
    st.session_state["otp_target"] = to
    st.info(f"Simulated OTP sent to {to}: **{otp}**")
    return otp


def verify_otp(user_input_otp):
    return user_input_otp == st.session_state.get("otp")

# ========== Forgot Password Flow ==========

def forgot_password_flow():
    st.subheader("🔐 Forgot Password")
    verify_method = st.radio("Choose verification method:", ["Verify through Email", "Verify through Phone"])

    if verify_method == "Verify through Email":
        email = st.text_input("Enter your registered Email")
        if st.button("Send OTP to Email"):
            df = load_users()
            if email in df["email"].values:
                send_otp(email)
                st.success("OTP sent to your Email (simulated)")
                st.session_state["reset_email"] = email
                st.session_state["show_email_otp"] = True
            else:
                st.error("Email not found.")

        if st.session_state.get("show_email_otp"):
            otp_input = st.text_input("Enter the OTP sent to your email")
            if st.button("Verify Email OTP"):
                if verify_otp(otp_input):
                    st.session_state["otp_verified"] = True
                    st.success("OTP Verified! You may now reset your password.")
                else:
                    st.error("Invalid OTP")

    elif verify_method == "Verify through Phone":
        phone = st.text_input("Enter your registered Phone Number")
        if st.button("Send OTP to Phone"):
            df = load_users()
            if phone in df["phone"].values:
                send_otp(phone)
                st.success("OTP sent to your Phone (simulated)")
                st.session_state["reset_phone"] = phone
                st.session_state["show_phone_otp"] = True
            else:
                st.error("Phone number not found.")

        if st.session_state.get("show_phone_otp"):
            otp_input = st.text_input("Enter the OTP sent to your phone")
            if st.button("Verify Phone OTP"):
                if verify_otp(otp_input):
                    st.session_state["otp_verified"] = True
                    st.success("OTP Verified! You may now reset your password.")
                else:
                    st.error("Invalid OTP")

    # Password reset after OTP verification
    if st.session_state.get("otp_verified"):
        new_pwd = st.text_input("Enter new password", type="password")
        re_pwd = st.text_input("Re-enter new password", type="password")
        if st.button("Reset Password"):
            if new_pwd != re_pwd:
                st.error("Passwords do not match.")
            else:
                df = load_users()
                if st.session_state.get("reset_email"):
                    df.loc[df["email"] == st.session_state["reset_email"], "password"] = new_pwd
                elif st.session_state.get("reset_phone"):
                    df.loc[df["phone"] == st.session_state["reset_phone"], "password"] = new_pwd
                save_users(df)
                st.success("✅ Password updated successfully.")
                st.session_state["otp_verified"] = False
                st.session_state["show_email_otp"] = False
                st.session_state["show_phone_otp"] = False

# ================= Streamlit UI Layout ===================

st.set_page_config(page_title="AI Resume Feedback Bot", layout="centered")
st.title("🤖 AI Resume Feedback Bot")
st.markdown("Analyze your resume and get smart feedback with AI.")

menu = ["Login", "Register", "Forgot Password", "Change Password"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Login":
    st.subheader("🔑 Login to Continue")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login_user(email, password)
        if user is not None:
            st.session_state["logged_in"] = True
            st.session_state["email"] = email
            st.success(f"Welcome back, {email}!")
        else:
            st.error("Invalid credentials.")

elif choice == "Register":
    st.subheader("📝 Create New Account")
    email = st.text_input("Email", key="reg_email")
    phone = st.text_input("Phone Number", key="reg_phone")
    password = st.text_input("Password", type="password", key="reg_pass")
    confirm_password = st.text_input("Confirm Password", type="password", key="reg_pass2")
    if st.button("Sign Up"):
        if password != confirm_password:
            st.error("Passwords do not match.")
        elif signup_user(email, password, phone):
            st.success("Account created! Please login.")
        else:
            st.warning("User already exists.")

elif choice == "Forgot Password":
    forgot_password_flow()

elif choice == "Change Password":
    st.subheader("🔁 Change Password")
    email = st.text_input("Enter Email")
    current_pwd = st.text_input("Current Password", type="password")
    new_pwd = st.text_input("New Password", type="password")
    confirm_new_pwd = st.text_input("Confirm New Password", type="password")
    if st.button("Update Password"):
        if not login_user(email, current_pwd):
            st.error("Incorrect current password.")
        elif new_pwd != confirm_new_pwd:
            st.error("New passwords do not match.")
        else:
            df = load_users()
            df.loc[df["email"] == email, "password"] = new_pwd
            save_users(df)
            st.success("Password changed successfully!")

# ========== Logged-in user resume feedback ==========
if st.session_state.get("logged_in"):
    st.markdown("---")
    st.header("📄 Upload Your Resume")
    uploaded_file = st.file_uploader("Choose your resume (.pdf or .docx)", type=["pdf", "docx"])

    if uploaded_file:
        file_path = save_resume(uploaded_file, st.session_state["email"])
        st.success("Resume uploaded successfully!")

        if st.button("Analyze Resume"):
            with st.spinner("Analyzing with AI..."):
                feedback, strengths, weaknesses, score, keywords, audio_path = analyze_resume(file_path)

                st.markdown("### ✅ Feedback Summary")
                st.write(feedback)
                st.markdown(f"**⭐ Score:** `{score}/10`")
                st.markdown(f"**✅ Strengths:** {', '.join(strengths)}")
                st.markdown(f"**⚠️ Weaknesses:** {', '.join(weaknesses)}")
                st.markdown(f"**📌 ATS Keywords:** `{', '.join(keywords)}`")

                if audio_path:
                    st.audio(audio_path)

                save_feedback(st.session_state["email"], uploaded_file.name, feedback, strengths, weaknesses, score, keywords, audio_path)

    if st.button("Logout"):
        st.session_state.clear()
        st.success("You have been logged out.")


# ========== Global Constants ==========
USERS_CSV = "users.csv"
HISTORY_CSV = "feedback_history.csv"
OTP_DB = {}

# Ensure CSV files exist
for file, headers in [
    (USERS_CSV, ["email", "password", "phone"]),
    (HISTORY_CSV, ["email", "filename", "feedback", "strengths", "weaknesses", "score", "keywords", "timestamp", "audio_path"]),
]:
    if not os.path.exists(file):
        pd.DataFrame(columns=headers).to_csv(file, index=False)

# ========== Save Uploaded Resume ==========
def save_resume(uploaded_file, user_email):
    folder = "uploaded_resumes"
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, f"{user_email}_{uploaded_file.name}")
    with open(filepath, "wb") as f:
        f.write(uploaded_file.read())
    return filepath

# ========== Analyze Resume Using AI ==========
def analyze_resume(file_path):
    import docx
    import PyPDF2

    def extract_text(path):
        text = ""
        if path.endswith(".pdf"):
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text()
        elif path.endswith(".docx"):
            doc = docx.Document(path)
            text = "\n".join([para.text for para in doc.paragraphs])
        return text

    resume_text = extract_text(file_path)

    prompt = f"Analyze this resume:\n\n{resume_text}\n\nGive feedback, strengths, weaknesses, a score out of 10, and 10 keywords."
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    result = response["choices"][0]["message"]["content"]

    feedback = result
    strengths = re.findall(r"(?i)strengths?:\s*(.*)", result)
    weaknesses = re.findall(r"(?i)weaknesses?:\s*(.*)", result)
    score = re.findall(r"(?i)score\s*[:\-]?\s*(\d+)", result)
    keywords = re.findall(r"(?i)keywords?:\s*(.*)", result)

    strengths = strengths[0].split(",") if strengths else []
    weaknesses = weaknesses[0].split(",") if weaknesses else []
    score = int(score[0]) if score else 0
    keywords = keywords[0].split(",") if keywords else []

    audio_path = None
    try:
        from gtts import gTTS
        audio = gTTS(text=feedback)
        audio_path = f"audio_feedback/{uuid.uuid4()}.mp3"
        os.makedirs("audio_feedback", exist_ok=True)
        audio.save(audio_path)
    except:
        pass

    return feedback, strengths, weaknesses, score, keywords, audio_path

# ========== Save Feedback ==========
def save_feedback(email, filename, feedback, strengths, weaknesses, score, keywords, audio_path):
    df = pd.read_csv(HISTORY_CSV)
    new_entry = {
        "email": email,
        "filename": filename,
        "feedback": feedback,
        "strengths": ",".join(strengths),
        "weaknesses": ",".join(weaknesses),
        "score": score,
        "keywords": ",".join(keywords),
        "timestamp": datetime.datetime.now(),
        "audio_path": audio_path or "",
    }
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    df.to_csv(HISTORY_CSV, index=False)

# ========== OTP Verification ==========
def send_otp(contact):
    otp = str(random.randint(100000, 999999))
    OTP_DB[contact] = otp

    if re.match(r"[^@]+@[^@]+\.[^@]+", contact):
        yag = yagmail.SMTP(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
        yag.send(to=contact, subject="Your OTP Code", contents=f"Your OTP is: {otp}")
    else:
        # Simulated SMS for deployment. Replace with Twilio if needed.
        print(f"SMS OTP to {contact}: {otp}")

def verify_otp(contact, otp):
    return OTP_DB.get(contact) == otp



