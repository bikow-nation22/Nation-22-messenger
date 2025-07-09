from flask import Flask, render_template, request, session, jsonify, redirect, send_from_directory
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_cors import CORS
import os, json, uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'nation22-secret'
CORS(app, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*", manage_session=True)

# Files
USERS_FILE = 'users.json'
MESSAGES_FILE = 'messages.json'
GROUPS_FILE = 'groups.json'
AVATAR_FOLDER = 'static/avatars'

os.makedirs(AVATAR_FOLDER, exist_ok=True)

# Initialize data files
for file, default in [(USERS_FILE, {}), (MESSAGES_FILE, []), (GROUPS_FILE, {})]:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump(default, f)

# Helpers
def load_users():
    return json.load(open(USERS_FILE))

def save_users(users):
    json.dump(users, open(USERS_FILE, 'w'), indent=2)

def load_messages():
    return json.load(open(MESSAGES_FILE))

def save_messages(messages):
    json.dump(messages, open(MESSAGES_FILE, 'w'), indent=2)

def load_groups():
    return json.load(open(GROUPS_FILE))

def save_groups(groups):
    json.dump(groups, open(GROUPS_FILE, 'w'), indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    users = load_users()
    if username in users and check_password_hash(users[username]['password'], password):
        session['user'] = username
        return '', 200
    return 'Invalid login', 400

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    users = load_users()
    if username in users:
        return 'Username already exists', 400
    users[username] = {
        'password': generate_password_hash(password),
        'nickname': username,
        'avatar': '',
        'online': False
    }
    save_users(users)
    session['user'] = username
    return '', 200

@app.route('/logout')
def logout():
    session.pop('user', None)
    return '', 200

@app.route('/me')
def me():
    user = session.get('user')
    if not user:
        return jsonify({})
    users = load_users()
    return jsonify(users.get(user, {}))

@app.route('/settings', methods=['POST'])
def settings():
    user = session.get('user')
    if not user:
        return 'Unauthorized', 401
    users = load_users()
    if 'nickname' in request.form:
        users[user]['nickname'] = request.form['nickname']
    if 'avatar' in request.files:
        file = request.files['avatar']
        filename = secure_filename(file.filename)
        file.save(os.path.join(AVATAR_FOLDER, filename))
        users[user]['avatar'] = filename
    save_users(users)
    return jsonify({'status': 'updated'})

@app.route('/create_group', methods=['POST'])
def create_group():
    user = session.get('user')
    if not user:
        return 'Unauthorized', 401
    group_name = request.form.get('group')
    groups = load_groups()
    if group_name in groups:
        return 'Group already exists', 400
    groups[group_name] = [user]
    save_groups(groups)
    return jsonify({'status': 'created'})

@app.route('/join_group', methods=['POST'])
def join_group():
    user = session.get('user')
    if not user:
        return 'Unauthorized', 401
    group_name = request.form.get('group')
    groups = load_groups()
    if group_name not in groups:
        return 'Group not found', 404
    if user not in groups[group_name]:
        groups[group_name].append(user)
        save_groups(groups)
    return jsonify({'status': 'joined'})

@app.route('/static/avatars/<filename>')
def avatar(filename):
    return send_from_directory(AVATAR_FOLDER, filename)

# === SocketIO Events ===
@socketio.on('join')
def handle_join(data):
    username = data.get('username')
    group = data.get('group', 'global')
    session['user'] = username
    session['group'] = group

    users = load_users()
    if username in users:
        users[username]['online'] = True
        save_users(users)

    join_room(group)
    emit('user-update', users, room=group)

@socketio.on('disconnect')
def handle_disconnect():
    user = session.get('user')
    group = session.get('group', 'global')
    if user:
        users = load_users()
        if user in users:
            users[user]['online'] = False
            save_users(users)
            emit('user-update', users, room=group)

@socketio.on('message')
def handle_message(data):
    user = session.get('user')
    group = session.get('group', 'global')
    if not user:
        return
    msg = {
        'id': str(uuid.uuid4()),
        'from': user,
        'text': data['text'],
        'to': data.get('to', 'All'),
        'time': datetime.now().strftime('%H:%M'),
        'seen': False
    }
    messages = load_messages()
    messages.append(msg)
    save_messages(messages)
    emit('message', msg, room=group)

@socketio.on('edit')
def handle_edit(data):
    messages = load_messages()
    for m in messages:
        if m['id'] == data['id']:
            m['text'] = data['text'] + ' (edited)'
    save_messages(messages)
    emit('edit', data, broadcast=True)

@socketio.on('delete')
def handle_delete(msg_id):
    messages = load_messages()
    messages = [m for m in messages if m['id'] != msg_id]
    save_messages(messages)
    emit('delete', msg_id, broadcast=True)

@socketio.on('typing')
def handle_typing():
    user = session.get('user')
    group = session.get('group', 'global')
    if user:
        emit('typing', user, room=group)

# Local development only
if __name__ == '__main__':
    import eventlet
    eventlet.monkey_patch()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
