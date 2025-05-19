import streamlit as st
import os
import pandas as pd
from docx import Document
from sqlalchemy import create_engine
import re

# --- Streamlit UI ---
st.set_page_config(page_title="Candidate Parser", layout="centered")
st.title("Candidate Profile Extractor & Exporter - Powered by Coursemon")

uploaded_files = st.file_uploader("Upload Candidate DOCX Files", type=["docx"], accept_multiple_files=True)

# --- Section Extraction Functions ---
def extract_section(text, start_keyword, end_keyword=None):
    try:
        start_match = re.search(re.escape(start_keyword), text, re.IGNORECASE)
        if not start_match:
            return ""
        start = start_match.end()

        if end_keyword:
            end_match = re.search(re.escape(end_keyword), text[start:], re.IGNORECASE)
            if end_match:
                end = start + end_match.start()
                return text[start:end].strip()

        return text[start:].strip()
    except Exception as e:
        return f"Extraction error: {e}"

def extract_name(text):
    try:
        return text.split("Candidate assessment of")[1].split("For the position")[0].strip()
    except:
        return "Unknown"

# --- Main Parsing Logic ---
def parse_docx(file):
    doc = Document(file)
    full_text = "\n".join([para.text.strip() for para in doc.paragraphs if para.text.strip()])

    # Debug: Show raw extracted text
    st.text_area("🧾 Raw Document Text", full_text, height=300)

    candidate_data = {
        "Name": extract_name(full_text),
        "DOB": extract_section(full_text, "DOB:", "Nationality:"),
        "Nationality": extract_section(full_text, "Nationality:", "Languages:"),
        "Languages": extract_section(full_text, "Languages:", "Current Location:"),
        "Education": extract_section(full_text, "Qualification", "Professional Training"),
        "Experience Summary": extract_section(full_text, "Summary of Experience", "Qualification"),
        "Work History": extract_section(full_text, "Detailed Work Experience", "Qualification" if "Qualification" in full_text else "Trainings")
    }
    return candidate_data

# --- Process Uploaded Files ---
all_data = []

if uploaded_files:
    for file in uploaded_files:
        candidate_data = parse_docx(file)
        all_data.append(candidate_data)

    df = pd.DataFrame(all_data)

    st.success("✅ Extraction Completed!")
    st.dataframe(df)

    # --- CSV Download ---
    csv_file = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download as CSV", csv_file, "candidate_profiles.csv", "text/csv")

    # --- Optional: Upload to MySQL ---
    with st.expander("🔗 Connect to MySQL and Upload"):
        host = st.text_input("MySQL Host", "localhost")
        user = st.text_input("MySQL Username")
        password = st.text_input("MySQL Password", type="password")
        db_name = st.text_input("Database Name")
        table_name = st.text_input("Table Name", "candidate_profiles")

        if st.button("Upload to MySQL"):
            try:
                engine = create_engine(f'mysql+pymysql://{user}:{password}@{host}/{db_name}')
                df.to_sql(table_name, con=engine, if_exists='append', index=False)
                st.success("✅ Data uploaded to MySQL successfully!")
            except Exception as e:
                st.error(f"❌ Error uploading to MySQL: {e}")
