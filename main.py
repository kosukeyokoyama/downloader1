
import os
import json
from ftplib import FTP
import traceback
from email.mime.text import MIMEText
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# ===== 設定 =====
JSON_DIR = 'json'
UPLOAD_DIR = 'upload'

FTP_HOST = 'ftpupload.net'
FTP_USER = 'if0_39375859'
FTP_PASS = 'tbxgNOfYXIk'
FTP_UPLOAD_DIR = '/upload_contents'

# Gmail設定
SCOPES1 = ['https://www.googleapis.com/auth/gmail.send']

# ===== Gmail関数 =====
def gmail_authenticate():
    creds = None
    token_path = 'token1.json'
    secret_path = 'client_secret.json'
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES1)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(secret_path, SCOPES1)
            creds = flow.run_local_server(port=8080)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    return creds

def create_message(to, subject, body):
    message = MIMEText(body, 'plain', 'utf-8')
    message['to'] = to
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}

def send_message(service, user_id, message):
    sent_message = service.users().messages().send(userId=user_id, body=message).execute()
    print(f"Message sent. ID: {sent_message['id']}")

def send_gmail_notification(to, subject, body):
    try:
        creds = gmail_authenticate()
        service = build('gmail', 'v1', credentials=creds)
        message = create_message(to, subject, body)
        send_message(service, 'me', message)
    except Exception:
        print("Gmail Error:")
        traceback.print_exc()

# ===== FTP関数 =====
def ftp_connect():
    ftp = FTP()
    ftp.connect(FTP_HOST, timeout=10)
    ftp.login(FTP_USER, FTP_PASS)
    return ftp

def ensure_ftp_dir(ftp, path):
    dirs = path.strip("/").split("/")
    for d in dirs:
        try:
            ftp.mkd(d)
        except:
            pass
        ftp.cwd(d)
    ftp.cwd("/")

def upload_ftp_file(local_path, ftp_path):
    try:
        ftp = ftp_connect()
        ensure_ftp_dir(ftp, os.path.dirname(ftp_path))
        with open(local_path, 'rb') as f:
            ftp.storbinary(f"STOR " + os.path.basename(ftp_path), f)
        ftp.quit()
        print(f"Uploaded {local_path} to {ftp_path}")
        return True
    except Exception:
        print("FTP Upload Error:")
        traceback.print_exc()
        return False

# ===== メイン処理 =====
def main():
    for json_file in os.listdir(JSON_DIR):
        if not json_file.endswith('.json'):
            continue
        json_path = os.path.join(JSON_DIR, json_file)
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            user_id = data['user_id']
            file_name = data['file_name']
            notify_method = data.get('notify_method', 'none')
            gmail_address = data.get('gmail_address', '')

            local_file_path = os.path.join(UPLOAD_DIR, file_name)
            if not os.path.exists(local_file_path):
                print(f"File not found: {local_file_path}")
                continue

            ftp_path = f"{FTP_UPLOAD_DIR}/{user_id}/{file_name}"
            if upload_ftp_file(local_file_path, ftp_path):
                # Gmail通知
                if notify_method.lower() == 'gmail' and gmail_address:
                    body = f"{file_name} がアップロードされました。\nFTPパス: {ftp_path}"
                    send_gmail_notification(gmail_address, "✅ ファイルアップロード完了", body)
                # 処理完了したら削除
                os.remove(local_file_path)
                os.remove(json_path)

        except Exception:
            print(f"Error processing {json_file}:")
            traceback.print_exc()

if __name__ == "__main__":
    main()
