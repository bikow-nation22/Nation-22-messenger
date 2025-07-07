const socket = io(window.location.origin);
let isRegistering = false;
let currentUser = "";
let currentTarget = "All";

function toggleAuth() {
  isRegistering = !isRegistering;
  document.getElementById('auth-title').textContent = isRegistering ? 'Register' : 'Login';
  document.querySelector('#auth-forms button').textContent = isRegistering ? 'Register' : 'Login';
  document.getElementById('toggle-auth').textContent = isRegistering ? 'Already have an account? Login' : "Don't have an account? Register";
}

async function submitAuth() {
  const username = document.getElementById('auth-username').value.trim();
  const password = document.getElementById('auth-password').value.trim();
  if (!username || !password) return alert("Fill all fields");

const res = await fetch(isRegistering ? '/register' : '/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
  credentials: 'include'
});

  if (res.ok) {
    currentUser = username;
    socket.emit('join', username);
    location.reload();
  } else alert(await res.text());
}

function openSettings() {
  document.getElementById('settings-modal').style.display = 'block';
}

function closeSettings() {
  document.getElementById('settings-modal').style.display = 'none';
}

function saveSettings() {
  const nickname = document.getElementById('nickname').value;
  const formData = new FormData();
  formData.append('nickname', nickname);
  const file = document.getElementById('avatarUpload').files[0];
  if (file) formData.append('avatar', file);
  fetch('/settings', { method: 'POST', body: formData });
  alert("Saved!");
  closeSettings();
}

function createGroup() {
  const name = prompt("Enter group name:");
  if (name) alert("Group '" + name + "' created!");
}

function joinGroup() {
  const name = prompt("Enter group name to join:");
  if (name) alert("Joined group '" + name + "'!");
}

function renderUsers(users) {
  const list = document.getElementById('user-list');
  list.innerHTML = '';
  Object.entries(users).forEach(([username, info]) => {
    if (username === currentUser) return;
    const div = document.createElement('div');
    div.className = 'user';
    div.innerHTML = `<span>${username}</span><span class="status ${info.online ? 'online' : 'offline'}">${info.online ? 'Online' : 'Offline'}</span>`;
    div.onclick = () => { currentTarget = username; alert(`Now chatting with ${username}`); };
    list.appendChild(div);
  });
}

function renderMessage(msg) {
  const div = document.createElement('div');
  const className = msg.from === currentUser ? 'from-me seen' : 'from-other';
  if (msg.to !== 'All' && msg.to !== currentUser && msg.from !== currentUser) return;
  div.className = `message ${className}`;
  div.innerHTML = `<strong>${msg.from}</strong>: ${msg.text}`;
  document.getElementById('messages').appendChild(div);
  document.getElementById('messages').scrollTop = 99999;
}

document.getElementById('send-btn').onclick = () => {
  const text = document.getElementById('message-input').value.trim();
  if (text) {
    socket.emit('message', { text, to: currentTarget });
    document.getElementById('message-input').value = '';
  }
};

document.getElementById('message-input').addEventListener('input', () => {
  socket.emit('typing');
});

socket.on('connect', async () => {
  const res = await fetch('/me', { credentials: 'include' });
  const me = await res.json();
  if (me.nickname) {
    currentUser = me.nickname;
    document.getElementById('auth-forms').style.display = 'none';
    document.getElementById('chat-area').style.display = 'flex';
    document.getElementById('input-area').style.display = 'flex';
    socket.emit('join', me.nickname);
  }
});

socket.on('user-update', data => renderUsers(data));
socket.on('message', msg => renderMessage(msg));
socket.on('typing', user => {
  document.getElementById('typing-status').innerText = `${user} is typing...`;
  setTimeout(() => document.getElementById('typing-status').innerText = '', 1500);
});
