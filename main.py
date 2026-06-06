from append_mail import get_data
from mail import send_gmail_bulk

MY_NAME = input("Type your name: ")
MY_PHONE = input("Type your mobile number: ")

df = get_data(
    ctc_start=2500000,
    ctc_end=5000000,
    path="jobs_data/data.xlsx",
    sender_name=MY_NAME,
    phone_number=MY_PHONE
)

pdf_file_to_send = "resume/resume.pdf"

print(f"\nFound {len(df)} emails to send\n")

success = 0
failed = 0
skipped = 0

for idx, row in df.iterrows():

    recipient = str(
        row["company_email"]
    ).strip()

    if (
        not recipient
        or recipient.lower() == "nan"
    ):
        skipped += 1
        continue

    print(
        f"[{success + failed + skipped + 1}/{len(df)}] "
        f"{row['company']} -> {recipient}"
    )

    status = send_gmail_bulk(
        recipient=recipient,
        subject=row["EMAIL_SUBJECT"],
        body_text=row["EMAIL_BODY"],
        pdf_path=pdf_file_to_send
    )

    if status:
        success += 1
    else:
        failed += 1

print("\n========== SUMMARY ==========")
print(f"Rows     : {len(df)}")
print(f"Success  : {success}")
print(f"Failed   : {failed}")
print(f"Skipped  : {skipped}")