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

USERS_FILE = 'users.json'
MESSAGES_FILE = 'messages.json'
AVATAR_FOLDER = 'static/avatars'
os.makedirs(AVATAR_FOLDER, exist_ok=True)

# Initialize storage if missing
if not os.path.exists(USERS_FILE):
    json.dump({}, open(USERS_FILE, 'w'))
if not os.path.exists(MESSAGES_FILE):
    json.dump([], open(MESSAGES_FILE, 'w'))

# Helpers
def load_users():
    return json.load(open(USERS_FILE))

def save_users(users):
    json.dump(users, open(USERS_FILE, 'w'), indent=2)

def load_messages():
    return json.load(open(MESSAGES_FILE))

def save_messages(messages):
    json.dump(messages, open(MESSAGES_FILE, 'w'), indent=2)

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

@app.route('/static/avatars/<filename>')
def avatar(filename):
    return send_from_directory(AVATAR_FOLDER, filename)

# SocketIO events
@socketio.on('join')
def handle_join(username):
    session['user'] = username
    users = load_users()
    if username in users:
        users[username]['online'] = True
        save_users(users)
        emit('user-update', users, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    user = session.get('user')
    if user:
        users = load_users()
        if user in users:
            users[user]['online'] = False
            save_users(users)
            emit('user-update', users, broadcast=True)

@socketio.on('message')
def handle_message(data):
    user = session.get('user')
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
    emit('message', msg, broadcast=True)

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
    if user:
        emit('typing', user, broadcast=True)

if __name__ == '__main__':
    # This only runs when testing locally (not on Render)
    import eventlet
    eventlet.monkey_patch()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
