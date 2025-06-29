import os
import imaplib
import email
from email.header import decode_header
import datetime
import dropbox
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({"status": "online"})

@app.route('/run')
def run():
    try:
        process_invoices()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

def process_invoices():
    EMAIL_USER = os.environ["EMAIL_USER"]
    EMAIL_PASS = os.environ["EMAIL_PASS"]
    DROPBOX_TOKEN = os.environ["DROPBOX_TOKEN"]

    mail = imaplib.IMAP4_SSL("web8.alfahosting-server.de", 993)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")

    result, data = mail.search(None, 'ALL')
    ids = data[0].split()

    now = datetime.datetime.now()
    month_folder = now.strftime("%Y-%m")
    os.makedirs(month_folder, exist_ok=True)

    dbx = dropbox.Dropbox(DROPBOX_TOKEN)

    for mail_id in ids:
        _, msg_data = mail.fetch(mail_id, "(RFC822)")
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
        subject, encoding = decode_header(msg.get("Subject", ""))[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8")

        if "rechnung" in subject.lower():
            for part in msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
                filename = part.get_filename()
                if filename and filename.lower().endswith(('.pdf', '.docx')):
                    filepath = os.path.join(month_folder, filename)
                    with open(filepath, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                    dropbox_path = f"/{month_folder}/{filename}"
                    with open(filepath, 'rb') as f:
                        dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)

    mail.logout()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    # Server startet direkt, Rechnungen nur über /run
    app.run(host="0.0.0.0", port=port)
