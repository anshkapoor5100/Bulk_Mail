import logging
import time
import pandas as pd
import httpx

from dotenv import load_dotenv

from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import PyPDFLoader

# --------------------------------------------------
# Logging
# --------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

# --------------------------------------------------
# Setup
# --------------------------------------------------
load_dotenv()

logger.info("Initializing Mistral model...")

llm = ChatMistralAI(
    model="mistral-small-latest",
    temperature=0.3,
)

# --------------------------------------------------
# Email Prompt Template
# --------------------------------------------------
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are helping me write a cold outreach email.
Assume you to be {sender_name}

Candidate Profile:
--------------------
{profile}
--------------------

Sender Details:
Name: {sender_name}
Phone: {phone_number}

Return output EXACTLY in this format:

SUBJECT: <subject>

BODY:
<body>

Rules:
- Professional tone.
- Mention only information present in the profile.
- Explain why the candidate is a good fit.
- Sign off the email with the provided Sender Details (Name and Phone).
- DO NOT use any placeholders, variables, or brackets like {{recipient_name}}, [Hiring Manager], or [Company Name]. 
- Do not include a recipient name. Start the email with a professional, generic greeting like "Hi Team," or "Dear Hiring Team,".
- This is the final email ready to be sent—make it complete.
- Keep under 200 words.
- No markdown.
- No code blocks.
- No extra text.
            """
        ),
        (
            "human",
            """
Job Description:

{job_description}
            """
        ),
    ]
)

chain = prompt | llm


# --------------------------------------------------
# Parse LLM output
# --------------------------------------------------
def parse_response(text):
    subject = ""
    body = text.strip()

    try:
        if "BODY:" in text:
            subject_part, body_part = text.split("BODY:", 1)
            subject = subject_part.replace("SUBJECT:", "").strip()
            body = body_part.strip()
    except Exception:
        pass

    return subject, body


# --------------------------------------------------
# Retry wrapper
# --------------------------------------------------
def generate_email(job_description, sender_name, phone_number, profile_text, max_retries=6):
    for attempt in range(max_retries):
        try:
            response = chain.invoke(
                {
                    "profile": profile_text,  # Uses the dynamically generated profile
                    "job_description": job_description,
                    "sender_name": sender_name,
                    "phone_number": phone_number,
                }
            )
            return response.content

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait_time = min(2 ** attempt, 60)
                logger.warning("Rate limit hit. Waiting %d sec...", wait_time)
                time.sleep(wait_time)
            else:
                raise

        except Exception as e:
            logger.error("Generation failed: %s", str(e))
            if attempt == max_retries - 1:
                return ""
            time.sleep(3)

    return ""


# --------------------------------------------------
# Main processing
# --------------------------------------------------
def get_data(ctc_start, ctc_end, path, sender_name, phone_number):
    
    # 1. LOAD RESUME (Moved inside the function so it only runs when called)
    logger.info("Loading resume PDF...")
    try:
        loader = PyPDFLoader("resume/resume.pdf")
        docs = loader.load()
        RESUME_CONTENT = "\n".join(doc.page_content for doc in docs)
        logger.info("Resume loaded successfully (%d pages, %d chars)", len(docs), len(RESUME_CONTENT))
    except Exception as e:
        logger.error("Failed to load resume PDF: %s", str(e))
        raise


    # 3. LOAD EXCEL & PROCESS EMAILS
    logger.info("Loading Excel file: %s", path)
    df = pd.read_excel(path)
    logger.info("Loaded %d rows", len(df))

    # Sort
    df = df.sort_values(by="ctc", ascending=False)

    # Filter
    before_filter = len(df)
    df = df[(df["ctc"] >= ctc_start) & (df["ctc"] <= ctc_end)]
    logger.info("CTC filter %d -> %d rows", before_filter, len(df))

    # Remove missing emails
    before_dedup = len(df)
    df = df.dropna(subset=["company_email"])
    df = df.drop_duplicates(subset=["company_email"], keep="first")
    logger.info("Dedup %d -> %d rows", before_dedup, len(df))

    total = len(df)
    subjects = []
    bodies = []

    logger.info("Generating %d emails...", total)

    for idx, row in enumerate(df.itertuples(), start=1):
        company = getattr(row, "company", "Unknown")
        role = getattr(row, "role", "Unknown")

        logger.info("[%d/%d] %s | %s", idx, total, company, role)

        jd = row.jobDescription if pd.notna(row.jobDescription) else ""

        # Generate the email, passing the profile generated earlier
        response_text = generate_email(
            job_description=jd,
            sender_name=sender_name,
            phone_number=phone_number,
            profile_text=RESUME_CONTENT 
        )

        subject, body = parse_response(response_text)
        subjects.append(subject)
        bodies.append(body)

        # small delay
        time.sleep(0.5)

    df["EMAIL_SUBJECT"] = subjects
    df["EMAIL_BODY"] = bodies

    return df[["company", "role", "company_email", "EMAIL_SUBJECT", "EMAIL_BODY"]]


# --------------------------------------------------
# Run (Used for testing without Streamlit)
# --------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting pipeline")

    # Replace these strings with your actual details
    MY_NAME = "Prashans" 
    MY_PHONE = "+91-8319293560" 

    result = get_data(
        ctc_start=00000,
        ctc_end=5000000,
        path="jobs_data/data.xlsx",
        sender_name=MY_NAME,
        phone_number=MY_PHONE
    )

    import os
    os.makedirs("finalData", exist_ok=True)
    output_path = "finalData/jobs_with_emails.xlsx"

    result.to_excel(output_path, index=False)
    logger.info("Saved output file: %s (%d rows)", output_path, len(result))
    logger.info("Pipeline completed successfully")
    print(result.head())