import streamlit as st
import pandas as pd
import os
import uuid
from PyPDF2 import PdfReader
from fpdf import FPDF
from dotenv import load_dotenv
from groq import Groq

# Load API key securely
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

# Dummy in-memory user DB (you can replace with Firebase or SQLite later)
USER_DB = {"test@example.com": "test123"}

def login_user(email, password):
    return USER_DB.get(email) == password

def extract_text_from_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    return "".join([page.extract_text() or "" for page in reader.pages])

def get_feedback(resume_text):
    prompt = f"Review this resume and give detailed, professional feedback:\n\n{resume_text}"
    chat = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama3-8b-8192"
    )
    return chat.choices[0].message.content.strip()

def create_pdf_feedback(feedback_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in feedback_text.split('\n'):
        pdf.multi_cell(0, 10, line)
    file_path = f"feedback_{uuid.uuid4().hex[:8]}.pdf"
    pdf.output(file_path)
    return file_path

# Streamlit UI
st.set_page_config(page_title="AI Resume Feedback Bot", layout="centered")
st.title("🤖 AI Resume Feedback Bot")

# --- Login Section ---
st.subheader("🔐 Login")
email = st.text_input("Email")
password = st.text_input("Password", type="password")
if st.button("Login"):
    if login_user(email, password):
        st.success("Logged in successfully!")

        # Upload section
        st.subheader("📤 Upload your Resume")
        uploaded_file = st.file_uploader("Choose PDF", type=["pdf"])
        if uploaded_file:
            resume_text = extract_text_from_pdf(uploaded_file)
            st.info("🧠 Generating AI feedback...")
            feedback = get_feedback(resume_text)
            st.success("✅ Feedback Generated")
            st.write(feedback)

            # PDF Feedback
            pdf_path = create_pdf_feedback(feedback)
            with open(pdf_path, "rb") as f:
                st.download_button("📥 Download Feedback as PDF", f, file_name="resume_feedback.pdf")
    else:
        st.error("Invalid email or password.")
