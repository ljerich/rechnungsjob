# Web-Service für die Alfahosting-Mail-Verarbeitung mit Dropbox-Upload (monatlich sortiert)
import imaplib
import email
from email.header import decode_header
import os
import datetime
import dropbox
from flask import Flask, jsonify

app = Flask(__name__)

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
DROPBOX_TOKEN = os.getenv("DROPBOX_TOKEN")
IMAP_SERVER = "web8.alfahosting-server.de"  # aktualisierter Alfahosting-Server
SAVE_FOLDER = "/tmp/rechnungen"


def download_rechnungen():
    os.makedirs(SAVE_FOLDER, exist_ok=True)
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, port=993)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")

    result, data = mail.search(None, "ALL")
    ids = data[0].split()

    files = []
    for num in ids:
        result, msg_data = mail.fetch(num, "(RFC822)")
        for response in msg_data:
            if isinstance(response, tuple):
                msg = email.message_from_bytes(response[1])
                subject, encoding = decode_header(msg.get("Subject"))[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")
                if "rechnung" in subject.lower():
                    date_tuple = email.utils.parsedate_tz(msg.get("Date"))
                    if date_tuple:
                        dt = datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                        month_folder = dt.strftime("%Y-%m")
                        for part in msg.walk():
                            if part.get("Content-Disposition") is None:
                                continue
                            filename = part.get_filename()
                            if filename and (filename.endswith(".pdf") or filename.endswith(".docx")):
                                monthly_folder = os.path.join(SAVE_FOLDER, month_folder)
                                os.makedirs(monthly_folder, exist_ok=True)
                                filepath = os.path.join(monthly_folder, filename)
                                with open(filepath, "wb") as f:
                                    f.write(part.get_payload(decode=True))
                                files.append((filepath, month_folder))
    mail.logout()
    return files


def upload_to_dropbox(filepaths):
    dbx = dropbox.Dropbox(DROPBOX_TOKEN)
    uploaded = 0
    for path, folder in filepaths:
        dest = f"/Rechnungen/{folder}/{os.path.basename(path)}"
        with open(path, "rb") as f:
            dbx.files_upload(f.read(), dest, mode=dropbox.files.WriteMode("overwrite"))
            uploaded += 1
    return uploaded


@app.route('/')
def index():
    try:
        files = download_rechnungen()
        uploaded = upload_to_dropbox(files)
        return jsonify({"status": "ok", "rechnungen_gefunden": len(files), "hochgeladen": uploaded})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
