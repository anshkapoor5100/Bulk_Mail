import smtplib
import time
from email.message import EmailMessage
from dotenv import load_dotenv
import os

load_dotenv()
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

def send_gmail_bulk(recipient, subject, body_text, pdf_path):
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 465

    try:
        # We don't need to print "Connecting" every loop if we run bulk
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)

            email_msg = EmailMessage()
            email_msg["Subject"] = subject
            email_msg["From"] = SENDER_EMAIL
            email_msg["To"] = recipient
            email_msg.set_content(body_text)

            try:
                file_name = os.path.basename(pdf_path)
                with open(pdf_path, "rb") as f:
                    file_data = f.read()
                    
                email_msg.add_attachment(
                    file_data, 
                    maintype="application", 
                    subtype="pdf", 
                    filename=file_name
                )
            except FileNotFoundError:
                print(f"Error: PDF '{pdf_path}' not found. Sending without it.")

            server.send_message(email_msg)
            time.sleep(1.5)
            
            # --- ADD THIS: Tell the main loop it succeeded ---
            return True 
                
    except Exception as e:
        print(f"SMTP Error for {recipient}: {e}")
        
        # --- ADD THIS: Tell the main loop it failed ---
        return False