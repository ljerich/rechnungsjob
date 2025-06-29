
import os
import imaplib
import email
from email.header import decode_header
import time
from flask import Flask
import dropbox

app = Flask(__name__)

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
DROPBOX_TOKEN = os.getenv("DROPBOX_TOKEN")

def process_invoices():
    mail = imaplib.IMAP4("imap.dietrichdigital.de", 143)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")
    status, messages = mail.search(None, 'UNSEEN')
    mail_ids = messages[0].split()
    dbx = dropbox.Dropbox(DROPBOX_TOKEN)
    folder_name = "Rechnungen"
    dbx.files_create_folder_v2(f"/{folder_name}", autorename=True)

    for mail_id in mail_ids:
        result, msg_data = mail.fetch(mail_id, "(RFC822)")
        raw_email = msg_data[0][1]
        email_message = email.message_from_bytes(raw_email)

        for part in email_message.walk():
            content_disposition = part.get("Content-Disposition")
            if content_disposition and "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    data = part.get_payload(decode=True)
                    with open(filename, "wb") as f:
                        f.write(data)
                    with open(filename, "rb") as f:
                        dbx.files_upload(f.read(), f"/{folder_name}/{filename}",
                                         mode=dropbox.files.WriteMode("overwrite"))
                    os.remove(filename)
    mail.logout()

@app.route("/")
def index():
    return "Rechnungsservice aktiv"

@app.route("/run")
def run():
    process_invoices()
    return "Rechnungen verarbeitet"
