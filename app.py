from flask import Flask, render_template, request, redirect, jsonify, url_for
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from PIL import Image
import json
import os
import uuid

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Paths and settings
PROFILE_FILE = 'profiles.json'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure uploads folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def initialize_revealed(profile):
    """Ensure the 'revealed' field exists and is valid."""
    if 'revealed' not in profile:
        profile['revealed'] = {
            'biases': [False] * len(profile.get('biases', [])),
            'strengths': [False] * len(profile.get('strengths', [])),
            'weaknesses': [False] * len(profile.get('weaknesses', [])),
            'influence_skills': [False] * len(profile.get('influence_skills', [])),
        }
    else:
        for key in ['biases', 'strengths', 'weaknesses', 'influence_skills']:
            if key not in profile['revealed']:
                profile['revealed'][key] = [False] * len(profile.get(key, []))

# Load profiles
if os.path.exists(PROFILE_FILE):
    with open(PROFILE_FILE, 'r') as f:
        profiles = json.load(f)
    for profile in profiles:
        initialize_revealed(profile)
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
    if 'photo' in request.files:
        photo = request.files['photo']
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join(UPLOAD_FOLDER, unique_filename)

            # Save then resize the image
            photo.save(filepath)
            try:
                img = Image.open(filepath)
                img.thumbnail((300, 300))  # Max size 300x300, maintain aspect ratio
                img.save(filepath)
            except Exception as e:
                print(f"Error processing image: {e}")

            photo_filename = unique_filename
        else:
            photo_filename = None
    else:
        photo_filename = None

    data = request.form

    new_profile = {
        "name": data['name'],
        "appearance": data['appearance'],
        "background": data['background'],
        "personality": data['personality'],
        "biases": [bias.strip() for bias in data['biases'].split(',') if bias.strip()],
        "strengths": [strength.strip() for strength in data['strengths'].split(',') if strength.strip()],
        "weaknesses": [weakness.strip() for weakness in data['weaknesses'].split(',') if weakness.strip()],
        "influence_skills": [skill.strip() for skill in data['influence_skills'].split(',') if skill.strip()],
        "influence_successes": 0,
        "photo_filename": photo_filename,
        "revealed": {
            "biases": [],
            "strengths": [],
            "weaknesses": [],
            "influence_skills": []
        }
    }

    for key in ['biases', 'strengths', 'weaknesses', 'influence_skills']:
        new_profile['revealed'][key] = [False] * len(new_profile[key])

    profiles.append(new_profile)
    save_profiles()
    socketio.emit('refresh_profiles')
    return jsonify(success=True)

@app.route('/api/get_profiles', methods=['GET'])
def get_profiles():
    return jsonify(profiles)

@app.route('/api/edit_profile', methods=['POST'])
def edit_profile():
    data = request.get_json()
    profile_index = int(data['profile_index'])

    profiles[profile_index]['name'] = data['name']
    profiles[profile_index]['appearance'] = data['appearance']
    profiles[profile_index]['background'] = data['background']
    profiles[profile_index]['personality'] = data['personality']
    profiles[profile_index]['biases'] = [bias.strip() for bias in data['biases'].split(',') if bias.strip()]
    profiles[profile_index]['strengths'] = [strength.strip() for strength in data['strengths'].split(',') if strength.strip()]
    profiles[profile_index]['weaknesses'] = [weakness.strip() for weakness in data['weaknesses'].split(',') if weakness.strip()]
    profiles[profile_index]['influence_skills'] = [skill.strip() for skill in data['influence_skills'].split(',') if skill.strip()]

    save_profiles()
    socketio.emit('refresh_profiles')
    return jsonify(success=True)

@app.route('/api/delete_profile', methods=['POST'])
def delete_profile():
    data = request.get_json()
    profile_index = int(data['profile_index'])

    if 0 <= profile_index < len(profiles):
        del profiles[profile_index]
        save_profiles()
        socketio.emit('refresh_profiles')
        return jsonify(success=True)
    else:
        return jsonify(success=False, error="Invalid profile index")



def save_profiles():
    with open(PROFILE_FILE, 'w') as f:
        json.dump(profiles, f, indent=4)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
