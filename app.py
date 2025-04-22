### Fully refactored and fixed app.py ###

from flask import Flask, render_template, request, redirect, jsonify, url_for
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from PIL import Image
import json
import os
import uuid

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

app.config['DEBUG'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True

PROFILE_FILE = 'profiles.json'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Profile Class ---
class Profile:
    def __init__(self, data):
        self.name = data.get('name', '')
        self.appearance = data.get('appearance', '')
        self.background = data.get('background', '')
        self.personality = data.get('personality', '')
        self.goal = data.get('goal', '')
        self.attitude = data.get('attitude', '')
        self.benefit = data.get('benefit', '')
        self.special = data.get('special', '')
        self.successesNeeded = data.get('successesNeeded', 1)
        self.influence_successes = data.get('influence_successes', 0)
        self.biases = data.get('biases', [])
        self.strengths = data.get('strengths', [])
        self.weaknesses = data.get('weaknesses', [])
        self.influence_skills = data.get('influence_skills', [])
        self.revealed = data.get('revealed', self._initialize_revealed())
        self.photo_filename = data.get('photo_filename', None)

    def _initialize_revealed(self):
        return {k: [False] * len(getattr(self, k)) for k in ['biases', 'strengths', 'weaknesses', 'influence_skills']}

    def to_dict(self):
        return self.__dict__

# --- Profile Management ---
def load_profiles():
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, 'r') as f:
            raw_profiles = json.load(f)
            return [Profile(p) for p in raw_profiles]
    else:
        return []

def save_profiles():
    with open(PROFILE_FILE, 'w') as f:
        json.dump([p.to_dict() for p in profiles], f, indent=4)

profiles = load_profiles()

# --- Utility ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Routes ---
@app.route('/')
def home():
    return redirect('/players')

@app.route('/gm')
def gm_page():
    return render_template('gm.html', profiles=[p.to_dict() for p in profiles])

@app.route('/players')
def player_page():
    return render_template('players.html', profiles=[p.to_dict() for p in profiles])

@app.route('/api/get_profiles', methods=['GET'])
def get_profiles():
    return jsonify([p.to_dict() for p in profiles])

@app.route('/api/toggle_reveal', methods=['POST'])
def toggle_reveal():
    data = request.get_json()
    profile = profiles[int(data['profile_index'])]
    category = data['category']
    item_index = int(data['item_index'])
    profile.revealed[category][item_index] = not profile.revealed[category][item_index]
    save_profiles()
    socketio.emit('refresh_profiles')
    return jsonify(success=True)

@app.route('/api/increment_success', methods=['POST'])
def increment_success():
    data = request.get_json()
    profile = profiles[int(data['profile_index'])]
    profile.influence_successes += 1
    save_profiles()
    socketio.emit('refresh_profiles')
    return jsonify(success=True)

@app.route('/api/reset_success', methods=['POST'])
def reset_success():
    data = request.get_json()
    profile = profiles[int(data['profile_index'])]
    profile.influence_successes = 0
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

    data = request.form.to_dict()

    new_profile = Profile({
        'name': data.get('name', ''),
        'appearance': data.get('appearance', ''),
        'background': data.get('background', ''),
        'personality': data.get('personality', ''),
        'goal': data.get('goal', ''),
        'attitude': data.get('attitude', ''),
        'benefit': data.get('benefit', ''),
        'special': data.get('special', ''),
        'successesNeeded': int(data.get('successesNeeded', 1)),
        'biases': [x.strip() for x in data.get('biases', '').split(';') if x.strip()],
        'strengths': [x.strip() for x in data.get('strengths', '').split(';') if x.strip()],
        'weaknesses': [x.strip() for x in data.get('weaknesses', '').split(';') if x.strip()],
        'influence_skills': [x.strip() for x in data.get('influence_skills', '').split(';') if x.strip()],
        'photo_filename': photo_filename,
    })

    profiles.append(new_profile)
    save_profiles()
    socketio.emit('refresh_profiles')
    return jsonify(success=True)

@app.route('/api/edit_profile', methods=['POST'])
def edit_profile():
    try:
        data = request.get_json()
        profile_index = int(data['profile_index'])
        profile = profiles[profile_index]

        # Update simple fields
        for field in ['name', 'appearance', 'background', 'personality', 'goal', 'attitude', 'benefit', 'special']:
            if field in data:
                profile[field] = data[field]

        if 'successesNeeded' in data:
            profile['successesNeeded'] = int(data['successesNeeded'])

        if 'influence_successes' in data:
            profile['influence_successes'] = int(data['influence_successes'])

        # Update lists cleanly
        for field in ['biases', 'strengths', 'weaknesses', 'influence_skills']:
            new_items = data.get(field, [])
            revealed_data = data.get('revealed', {}).get(field, [])
            profile[field] = new_items
            profile['revealed'][field] = [
                revealed_data[idx] if idx < len(revealed_data) else False
                for idx in range(len(new_items))
            ]

        save_profiles()
        socketio.emit('refresh_profiles')
        return jsonify(success=True)
    except Exception as e:
        print(f"Error editing profile: {e}")
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
