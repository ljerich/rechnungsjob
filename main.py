import os
import imaplib
import email
from email.header import decode_header
import base64
import tempfile
import dropbox
from flask import Flask

app = Flask(__name__)

EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
DROPBOX_TOKEN = os.environ.get("DROPBOX_TOKEN")

@app.route("/")
def index():
    return "Server is running!"

@app.route("/run", methods=["GET"])
def run():
    process_invoices()
    return "Processing completed!"

def clean(text):
    return "".join(c if c.isalnum() else "_" for c in text)

def process_invoices():
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")
    status, messages = mail.search(None, 'UNSEEN')
    mail_ids = messages[0].split()

    for mail_id in mail_ids:
        result, msg_data = mail.fetch(mail_id, "(RFC822)")
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = decode_header(msg["Subject"])[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode()
        From = msg.get("From")

        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = part.get("Content-Disposition")
                if content_disposition and "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        filename = decode_header(filename)[0][0]
                        if isinstance(filename, bytes):
                            filename = filename.decode()
                        filename = clean(filename)
                        content = part.get_payload(decode=True)

                        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                            tmp_file.write(content)
                            upload_to_dropbox(tmp_file.name, filename)

    mail.logout()

def upload_to_dropbox(filepath, filename):
    dbx = dropbox.Dropbox(DROPBOX_TOKEN)
    dropbox_path = f"/{filename}"
    with open(filepath, "rb") as f:
        dbx.files_upload(f.read(), dropbox_path)
