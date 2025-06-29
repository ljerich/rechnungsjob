import os
import imaplib
import email
from email.header import decode_header
import datetime
import dropbox
from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return "Rechnungsverarbeitung läuft..."

def save_attachment(msg, download_folder, date_filter=None):
    for part in msg.walk():
        if part.get_content_maintype() == 'multipart':
            continue
        if part.get('Content-Disposition') is None:
            continue

        filename = part.get_filename()
        if filename:
            filepath = os.path.join(download_folder, filename)
            with open(filepath, 'wb') as f:
                f.write(part.get_payload(decode=True))
            print(f"Gespeichert: {filepath}")
            return filepath
    return None

def process_invoices():
    EMAIL_USER = os.environ.get("EMAIL_USER")
    EMAIL_PASS = os.environ.get("EMAIL_PASS")
    DROPBOX_TOKEN = os.environ.get("DROPBOX_TOKEN")

    mail = imaplib.IMAP4_SSL("web8.alfahosting-server.de", 993)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")

    result, data = mail.search(None, 'ALL')
    ids = data[0].split()
    print(f"{len(ids)} E-Mails gefunden.")

    now = datetime.datetime.now()
    month_folder = now.strftime("%Y-%m")
    os.makedirs(month_folder, exist_ok=True)

    dbx = dropbox.Dropbox(DROPBOX_TOKEN)

    for mail_id in ids:
        result, msg_data = mail.fetch(mail_id, "(RFC822)")
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding if encoding else "utf-8")

        if "rechnung" in subject.lower():
            filepath = save_attachment(msg, month_folder)
            if filepath:
                dropbox_path = f"/{month_folder}/{os.path.basename(filepath)}"
                with open(filepath, "rb") as f:
                    dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
                print(f"Upload erfolgreich: {dropbox_path}")

    mail.logout()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    process_invoices()
    app.run(host="0.0.0.0", port=port)
