import streamlit as st
import os
from append_mail import get_data
from mail import send_gmail_bulk

# Ensure the required directories exist
os.makedirs("jobs_data", exist_ok=True)
os.makedirs("resume", exist_ok=True)

st.title("Bulk Email Dispatcher")

# --- Inputs ---
my_name = st.text_input("Type your name:", value="Ansh Kapoor")
my_phone = st.text_input("Type your mobile number:")

col1, col2 = st.columns(2)
with col1:
    ctc_start = st.number_input("CTC Start", value=2500000, step=100000)
with col2:
    ctc_end = st.number_input("CTC End", value=5000000, step=100000)

st.markdown("---")
st.subheader("Upload Required Files")

# --- File Uploaders ---
data_file = st.file_uploader("Upload Jobs Data (Excel)", type=["xlsx"])
resume_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

# --- Delete Old & Save New Files ---
if data_file is not None:
    data_path = "jobs_data/data.xlsx"
    if os.path.exists(data_path):
        os.remove(data_path)  
    
    data_file.seek(0) 
    with open(data_path, "wb") as f:
        f.write(data_file.getbuffer())

if resume_file is not None:
    resume_path = "resume/resume.pdf"
    if os.path.exists(resume_path):
        os.remove(resume_path)  
        
    resume_file.seek(0)
    with open(resume_path, "wb") as f:
        f.write(resume_file.getbuffer())

st.markdown("---")

# --- Conditional Execution ---
# The button will ONLY appear if both files are uploaded
if data_file is not None and resume_file is not None:
    
    if st.button("Start Sending Emails", type="primary"):
        
        # Validation for text inputs
        if not my_name or not my_phone:
            st.error("Please enter your name and phone number before starting.")
            st.stop()

        st.write("Processing data...")

        # Fetch Data
        df = get_data(
            ctc_start=int(ctc_start),
            ctc_end=int(ctc_end),
            path="jobs_data/data.xlsx",
            sender_name=my_name,
            phone_number=my_phone
        )

        if len(df) == 0:
            st.warning("No emails matched your criteria. Try adjusting the CTC range or check your Excel file.")
            st.stop()

        st.info(f"Found **{len(df)}** emails to send.")

        success = 0
        failed = 0
        skipped = 0

        # UI Elements for real-time tracking
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, row in df.iterrows():
            recipient = str(row["company_email"]).strip()

            if not recipient or recipient.lower() == "nan":
                skipped += 1
                continue

            current_idx = success + failed + skipped + 1
            
            # Terminal-style output on the UI
            status_text.text(f"[{current_idx}/{len(df)}] {row['company']} -> {recipient}")

            # Send Email
            status = send_gmail_bulk(
                recipient=recipient,
                subject=row["EMAIL_SUBJECT"],
                body_text=row["EMAIL_BODY"],
                pdf_path="resume/resume.pdf"
            )

            if status:
                success += 1
            else:
                failed += 1

            # Update Progress Bar safely
            progress_bar.progress(current_idx / len(df))

        # --- Summary ---
        st.success("Process Complete!")
        
        st.markdown("### ========== SUMMARY ==========")
        st.markdown(f"**Rows:** {len(df)}")
        st.markdown(f"**Success:** {success}")
        st.markdown(f"**Failed:** {failed}")
        st.markdown(f"**Skipped:** {skipped}")

else:
    # This message shows when the app first loads or if a file is cleared
    st.info("Please upload both your Jobs Data (Excel) and Resume (PDF) to unlock the email dispatcher.")