# Webinterface zur Alfahosting-Mail-Verarbeitung mit monatlicher Sortierung und Dropbox-Upload
from flask import Flask, request, render_template_string
import imaplib
import email
from email.header import decode_header
import os
import datetime
import tempfile
import dropbox

app = Flask(__name__)

HTML_FORM = """
<!doctype html>
<title>Rechnungen in Dropbox archivieren</title>
<h2>Alfahosting & Dropbox Integration</h2>
<form method=post>
  Alfahosting E-Mail: <input type=text name=email required><br><br>
  Passwort: <input type=password name=password required><br><br>
  Dropbox Access Token: <input type=text name=token required><br><br>
  <input type=submit value='Rechnungen archivieren'>
</form>
{% if result %}<pre>{{ result }}</pre>{% endif %}
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    result = ""
    if request.method == 'POST':
        email_user = request.form['email']
        email_pass = request.form['password']
        dropbox_token = request.form['token']

        result += "Suche nach Rechnungen...\n"
        try:
            files = download_rechnungen(email_user, email_pass)
            result += f"{len(files)} Rechnungen gefunden.\n"
            uploaded = upload_to_dropbox(files, dropbox_token)
            result += f"{uploaded} Dateien nach Dropbox hochgeladen.\n"
        except Exception as e:
            result += f"Fehler: {e}"

    return render_template_string(HTML_FORM, result=result)

def download_rechnungen(user, password):
    SAVE_FOLDER = tempfile.mkdtemp()
    mail = imaplib.IMAP4_SSL("imap.alfahosting.de")
    mail.login(user, password)
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

def upload_to_dropbox(filepaths, token):
    dbx = dropbox.Dropbox(token)
    uploaded = 0
    for path, folder in filepaths:
        dest = f"/Rechnungen/{folder}/{os.path.basename(path)}"
        with open(path, "rb") as f:
            dbx.files_upload(f.read(), dest, mode=dropbox.files.WriteMode("overwrite"))
            uploaded += 1
    return uploaded

if __name__ == '__main__':
    app.run(debug=True)
