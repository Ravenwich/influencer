from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import json
import os
from models.profile import Profile
from werkzeug.utils import secure_filename

app = Flask(__name__)
socketio = SocketIO(app)

PROFILE_FILE = 'profiles.json'

# Load profiles
def load_profiles():
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, 'r') as f:
            return [Profile.from_dict(p) for p in json.load(f)]
    return []

# Save profiles
def save_profiles(profiles):
    with open(PROFILE_FILE, 'w') as f:
        json.dump([p.to_dict() for p in profiles], f, indent=2)

profiles = load_profiles()

@app.route('/players')
def players():
    return render_template('players.html', profiles=[p.to_player_dict() for p in profiles])

@app.route('/gm')
def gm_login():
    return render_template('gm.html')

@app.route('/gretchen')
def gretchen():
    return render_template('gretchen.html', profiles=[p.to_dict() for p in profiles])

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    file = request.files.get('photo')
    if not file:
        return jsonify({"error": "No file"}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(app.static_folder, 'images', filename)
    file.save(save_path)
    return jsonify({"filename": filename})


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
    # For players, we want to send the player‐view version;
    # but since both pages share the same socket endpoint, 
    # just send the full dicts—either client will render what it needs.
    emit('profiles_updated', [p.to_dict() for p in profiles])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # debug=False for prod
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
