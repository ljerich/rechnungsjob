from flask import Flask
import os
import imaplib
import email
from email.header import decode_header
import datetime
import base64
import dropbox

app = Flask(__name__)

EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
DROPBOX_TOKEN = os.environ.get("DROPBOX_TOKEN")

@app.route("/")
def index():
    return "Invoice Processor is live"

@app.route("/run")
def run():
    try:
        process_invoices()
        return "Processing completed successfully"
    except Exception as e:
        return f"Error during processing: {e}", 500

def process_invoices():
    mail = imaplib.IMAP4_SSL("web8.alfahosting-server.de", 993)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")
    result, data = mail.search(None, "ALL")
    mail_ids = data[0].split()

    now = datetime.datetime.now()
    folder_name = now.strftime("%Y-%m")
    os.makedirs(folder_name, exist_ok=True)

    dbx = dropbox.Dropbox(DROPBOX_TOKEN)

    for mail_id in mail_ids:
        result, msg_data = mail.fetch(mail_id, "(RFC822)")
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8")
        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition"))
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        filepath = os.path.join(folder_name, filename)
                        with open(filepath, "wb") as f:
                            f.write(part.get_payload(decode=True))
                        with open(filepath, "rb") as f:
                            dbx.files_upload(f.read(), f"/{folder_name}/{filename}", mode=dropbox.files.WriteMode("overwrite"))

    mail.logout()
