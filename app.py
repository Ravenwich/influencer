### Updated app.py ###

from flask import Flask, render_template, request, redirect, jsonify, url_for
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from PIL import Image
import json
import os
import uuid

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

PROFILE_FILE = 'profiles.json'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def initialize_revealed(profile):
    if 'revealed' not in profile:
        profile['revealed'] = {k: [False] * len(profile.get(k, [])) for k in ['biases', 'strengths', 'weaknesses', 'influence_skills']}

if os.path.exists(PROFILE_FILE):
    with open(PROFILE_FILE, 'r') as f:
        profiles = json.load(f)
    for p in profiles:
        initialize_revealed(p)
else:
    profiles = []
    with open(PROFILE_FILE, 'w') as f:
        json.dump(profiles, f, indent=4)

@app.route('/')
def home():
    return redirect('/players')

@app.route('/gm')
def gm_page():
    return render_template('gm.html', profiles=profiles)

@app.route('/players')
def player_page():
    return render_template('players.html', profiles=profiles)

@app.route('/api/get_profiles', methods=['GET'])
def get_profiles():
    return jsonify(profiles)

def save_profiles():
    with open(PROFILE_FILE, 'w') as f:
        json.dump(profiles, f, indent=4)

@app.route('/api/toggle_reveal', methods=['POST'])
def toggle_reveal():
    data = request.get_json()
    profile_index = int(data['profile_index'])
    category = data['category']
    item_index = int(data['item_index'])

    profiles[profile_index]['revealed'][category][item_index] = not profiles[profile_index]['revealed'][category][item_index]
    save_profiles()
    socketio.emit('refresh_profiles')
    return jsonify(success=True)

@app.route('/api/increment_success', methods=['POST'])
def increment_success():
    data = request.get_json()
    profile_index = int(data['profile_index'])
    profiles[profile_index]['influence_successes'] += 1
    save_profiles()
    socketio.emit('refresh_profiles')
    return jsonify(success=True)

@app.route('/api/reset_success', methods=['POST'])
def reset_success():
    data = request.get_json()
    profile_index = int(data['profile_index'])
    profiles[profile_index]['influence_successes'] = 0
    save_profiles()
    socketio.emit('refresh_profiles')
    return jsonify(success=True)

@app.route('/api/create_profile', methods=['POST'])
def create_profile():
    photo_filename = None
    if 'photo' in request.files:
        photo = request.files['photo']
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
            photo.save(filepath)
            try:
                img = Image.open(filepath)
                img.thumbnail((300, 300))
                img.save(filepath)
            except Exception as e:
                print(f"Image processing error: {e}")
            photo_filename = unique_filename

    data = request.form

    new_profile = {
        "name": data['name'],
        "appearance": data['appearance'],
        "background": data['background'],
        "personality": data['personality'],
        "biases": [x.strip() for x in data.get('biases', '').split(';') if x.strip()],
        "strengths": [x.strip() for x in data.get('strengths', '').split(';') if x.strip()],
        "weaknesses": [x.strip() for x in data.get('weaknesses', '').split(';') if x.strip()],
        "influence_skills": [x.strip() for x in data.get('influence_skills', '').split(';') if x.strip()],
        "influence_successes": 0,
        "photo_filename": photo_filename,
        "goal": data.get('goal', ''),
        "attitude": data.get('attitude', ''),
        "benefit": data.get('benefit', ''),
        "special": data.get('special', ''),
        "successesNeeded": int(data.get('successesNeeded', 1)),
        "revealed": {k: [] for k in ['biases', 'strengths', 'weaknesses', 'influence_skills']}
    }

    for k in ['biases', 'strengths', 'weaknesses', 'influence_skills']:
        new_profile['revealed'][k] = [False] * len(new_profile[k])

    profiles.append(new_profile)
    save_profiles()
    socketio.emit('refresh_profiles')
    return jsonify(success=True)

def parse_list_field(value):
    if isinstance(value, list):
        return [item.strip() for item in value if item.strip()]
    elif isinstance(value, str):
        return [item.strip() for item in value.split(';') if item.strip()]
    else:
        return []

@app.route('/api/edit_profile', methods=['POST'])
def edit_profile():
    try:
        data = request.get_json()
        profile_index = int(data['profile_index'])
        profile = profiles[profile_index]

        profile['name'] = data.get('name', profile.get('name', ''))
        profile['appearance'] = data.get('appearance', profile.get('appearance', ''))
        profile['background'] = data.get('background', profile.get('background', ''))
        profile['personality'] = data.get('personality', profile.get('personality', ''))
        profile['goal'] = data.get('goal', profile.get('goal', ''))
        profile['attitude'] = data.get('attitude', profile.get('attitude', ''))
        profile['benefit'] = data.get('benefit', profile.get('benefit', ''))
        profile['special'] = data.get('special', profile.get('special', ''))
        profile['successesNeeded'] = int(data.get('successesNeeded', profile.get('successesNeeded', 1)))
        profile['influence_successes'] = int(data.get('influence_successes', profile.get('influence_successes', 0)))


        profile['biases'] = parse_list_field(data.get('biases', ''))
        profile['strengths'] = parse_list_field(data.get('strengths', ''))
        profile['weaknesses'] = parse_list_field(data.get('weaknesses', ''))
        profile['influence_skills'] = parse_list_field(data.get('influence_skills', ''))

        if 'revealed' in data:
            profile['revealed'] = {}
            for key in ['biases', 'strengths', 'weaknesses', 'influence_skills']:
                revealed_list = data['revealed'].get(key, [])
                rebuilt_revealed = []
                for idx in range(len(profile.get(key, []))):
                    if idx < len(revealed_list):
                        rebuilt_revealed.append(revealed_list[idx])
                    else:
                        rebuilt_revealed.append(False)
                profile['revealed'][key] = rebuilt_revealed

        save_profiles()
        socketio.emit('refresh_profiles')
        return jsonify(success=True)
    except Exception as e:
        print("Error editing profile:", e)
        return jsonify(success=False), 500





@app.route('/api/delete_profile', methods=['POST'])
def delete_profile():
    data = request.get_json()
    idx = int(data['profile_index'])
    if 0 <= idx < len(profiles):
        del profiles[idx]
        save_profiles()
        socketio.emit('refresh_profiles')
        return jsonify(success=True)
    return jsonify(success=False)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)