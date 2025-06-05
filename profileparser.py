import streamlit as st
import pandas as pd
from docx import Document
from sqlalchemy import create_engine
import re
from datetime import datetime
import dateutil.parser

st.set_page_config(page_title="Candidate Parser", layout="centered")
st.title("Candidate Profile Extractor & Exporter - Powered by Coursemon")

uploaded_files = st.file_uploader("Upload Candidate DOCX Files", type=["docx"], accept_multiple_files=True)

def extract_section(text, start_pattern, end_pattern=None):
    try:
        start_match = re.search(start_pattern, text, re.IGNORECASE)
        if not start_match:
            return ""
        start = start_match.end()
        if end_pattern:
            end_match = re.search(end_pattern, text[start:], re.IGNORECASE)
            if end_match:
                end = start + end_match.start()
                return text[start:end].strip()
        return text[start:].strip()
    except Exception as e:
        return f"Error extracting section: {e}"

def extract_name(text):
    try:
        return text.split("Candidate assessment of")[1].split("For the position")[0].strip()
    except:
        return "Unknown"

def parse_docx(file):
    doc = Document(file)
    full_text = "\n".join([para.text.strip() for para in doc.paragraphs if para.text.strip()])
    data = {
        "Name": extract_name(full_text),
        "DOB": extract_section(full_text, r"DOB[:]*", r"Nationality[:]*"),
        "Nationality": extract_section(full_text, r"Nationality[:]*", r"Languages[:]*"),
        "Languages": extract_section(full_text, r"Languages[:]*", r"Current Location[:]*"),
        "Education": extract_section(full_text, r"Qualification", r"Professional Training|Trainings|Detailed Work Experience"),
        "Experience Summary": extract_section(full_text, r"Summary of Experience", r"Qualification|Professional Training"),
        "Work History": extract_section(full_text, r"Detailed Work Experience", r"Qualification|Trainings|Availability|Current Package|Prepared for")
    }
    return data

parsed_profiles = []
if uploaded_files:
    for file in uploaded_files:
        profile = parse_docx(file)
        parsed_profiles.append(profile)

    df = pd.DataFrame(parsed_profiles)

    tab1, tab2 = st.tabs(["📄 View & Download", "🔗 Upload to MySQL"])

    with tab1:
        st.success("✅ Extraction Completed")

        st.subheader("🔍 Filter Candidates")

        # Search by name
        name_query = st.text_input("Search by Candidate Name (Job Title Equivalent)", "")

        # Dropdown filters
        nationality_filter = st.selectbox("Filter by Nationality", ["All"] + sorted(df["Nationality"].dropna().unique().tolist()))
        language_filter = st.selectbox("Filter by Language", ["All"] + sorted(df["Languages"].dropna().unique().tolist()))
        location_filter = st.selectbox("Filter by Current Location", ["All"] + sorted(df["Languages"].dropna().unique().tolist()))  # Replace if location column exists

        # Apply filters
        filtered_df = df.copy()
        if name_query:
            filtered_df = filtered_df[filtered_df["Name"].str.contains(name_query, case=False, na=False)]
        if nationality_filter != "All":
            filtered_df = filtered_df[filtered_df["Nationality"].str.contains(nationality_filter, case=False, na=False)]
        if language_filter != "All":
            filtered_df = filtered_df[filtered_df["Languages"].str.contains(language_filter, case=False, na=False)]
        if location_filter != "All":
            filtered_df = filtered_df[filtered_df["Languages"].str.contains(location_filter, case=False, na=False)]  # Replace with actual location field if available

        st.dataframe(filtered_df)

        csv = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", csv, "candidate_profiles.csv", "text/csv")

    with tab2:
        with st.expander("Connect to MySQL"):
            host = st.text_input("Host", "localhost")
            user = st.text_input("User")
            password = st.text_input("Password", type="password")
            db = st.text_input("Database")
            table = st.text_input("Table", "candidate_profiles")

            if st.button("Upload"):
                try:
                    engine = create_engine(f'mysql+pymysql://{user}:{password}@{host}/{db}')
                    df.to_sql(table, con=engine, if_exists='append', index=False)
                    st.success("✅ Uploaded to MySQL!")
                except Exception as e:
                    st.error(f"❌ Upload failed: {e}")

else:
    st.info("📂 Please upload at least one DOCX file to begin.")
