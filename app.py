import os, json, io, mimetypes
from flask import Flask, render_template, request, jsonify, send_file, make_response
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from collections import namedtuple

from models.profile import Profile

app = Flask(__name__)
socketio = SocketIO(app)

# ─────────────── Constants & Cache ───────────────
SCOPES = ['https://www.googleapis.com/auth/drive']
PROFILES_FILE_ID = os.environ['PROFILES_FILE_ID']
IMAGES_FOLDER_ID = os.environ['IMAGES_FOLDER_ID']

ImageCacheEntry = namedtuple('ImageCacheEntry', ['mime','data'])
_image_cache: dict[str,ImageCacheEntry] = {}

# ─────────── Drive Service Helper ───────────
def get_drive_service():
    key_path = os.environ.get('SERVICE_ACCOUNT_FILE', 'service-account.json')
    creds = service_account.Credentials.from_service_account_file(
        key_path, scopes=SCOPES
    )
    return build('drive', 'v3', credentials=creds)

# ─────────── Profile Load / Save ───────────
def load_profiles():
    drive = get_drive_service()
    req = drive.files().get_media(
        fileId=PROFILES_FILE_ID,
        supportsAllDrives=True
    )
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, req)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    data = json.load(io.TextIOWrapper(fh, encoding='utf-8'))
    return [Profile.from_dict(p) for p in data]

def save_profiles(profiles):
    drive = get_drive_service()
    payload = json.dumps([p.to_dict() for p in profiles], indent=2).encode('utf-8')
    buf = io.BytesIO(payload)
    media = MediaIoBaseUpload(buf, mimetype='application/json', resumable=True)
    result = drive.files().update(
        fileId=PROFILES_FILE_ID,
        media_body=media,
        supportsAllDrives=True
    ).execute()
    app.logger.info(f"✅ Updated Drive file {PROFILES_FILE_ID}: {result}")

# load once at startup
profiles = load_profiles()

# ─────────── Image Proxy & Upload ───────────
@app.route('/images/<drive_id>')
def serve_image(drive_id):
    entry = _image_cache.get(drive_id)
    if entry:
        mime, data = entry.mime, entry.data
    else:
        drive = get_drive_service()
        meta = drive.files().get(
            fileId=drive_id,
            fields='name,mimeType',
            supportsAllDrives=True
        ).execute()
        mime = meta.get('mimeType')
        if not mime or mime == 'application/octet-stream':
            mime, _ = mimetypes.guess_type(meta.get('name',''))
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(
            buf,
            drive.files().get_media(fileId=drive_id)
        )
        done = False
        while not done:
            _, done = downloader.next_chunk()
        data = buf.getvalue()
        _image_cache[drive_id] = ImageCacheEntry(mime, data)

    resp = make_response(data)
    resp.headers.set('Content-Type', mime or 'application/octet-stream')
    resp.headers.set('Cache-Control', 'public, max-age=86400')
    return resp

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    file = request.files.get('photo')
    if not file:
        return jsonify(error="No file"), 400

    drive = get_drive_service()
    bio = io.BytesIO()
    file.save(bio); bio.seek(0)
    media = MediaIoBaseUpload(bio, mimetype=file.mimetype, resumable=True)
    gfile = drive.files().create(
        body={
            'name': secure_filename(file.filename),
            'parents': [IMAGES_FOLDER_ID]
        },
        media_body=media,
        fields='id'
    ).execute()
    drive.permissions().create(
        fileId=gfile['id'],
        body={'role':'reader','type':'anyone'}
    ).execute()

    return jsonify({ "driveId": gfile['id'] })

# ─────────── Download Profiles ───────────
@app.route('/download_profiles')
def download_profiles():
    drive = get_drive_service()
    req = drive.files().get_media(
        fileId=PROFILES_FILE_ID,
        supportsAllDrives=True
    )
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name='profiles.json',
        mimetype='application/json'
    )

# ─────────── Socket Handlers ───────────
@app.route('/players')
def players():
    return render_template('players.html',
        profiles=[p.to_player_dict() for p in profiles])

@app.route('/gm')
def gm_login():
    return render_template('gm.html')

@app.route('/gretchen')
def gretchen():
    return render_template('gretchen.html',
        profiles=[p.to_dict() for p in profiles])

@socketio.on('create_profile')
def create_profile(data):
    new_profile = Profile.from_dict(data)
    profiles.append(new_profile)
    save_profiles(profiles)
    emit('profiles_updated', [p.to_dict() for p in profiles], broadcast=True)

@socketio.on('update_profile')
def update_profile(data):
    idx = data.get('index')
    if 0 <= idx < len(profiles):
        profiles[idx] = Profile.from_dict(data['profile'])
        save_profiles(profiles)
        emit('profiles_updated', [p.to_dict() for p in profiles], broadcast=True)

@socketio.on('delete_profile')
def delete_profile(data):
    idx = data.get('index')
    if 0 <= idx < len(profiles):
        profiles.pop(idx)
        save_profiles(profiles)
        emit('profiles_updated', [p.to_dict() for p in profiles], broadcast=True)

@socketio.on('connect')
def on_connect():
    emit('profiles_updated', [p.to_dict() for p in profiles])

# ─────────── App Entry Point ───────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
