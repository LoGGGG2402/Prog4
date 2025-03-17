#!/usr/bin/env python3

from flask import Flask, request, render_template_string, redirect, url_for, send_from_directory, jsonify
import os
import time
import hashlib
import shutil

app = Flask(__name__)

# Create directories for uploads
os.makedirs('uploads/wp-content/uploads', exist_ok=True)

# Simple authentication
USERS = {
    'test': 'test123QWE@AD'
}

# Session storage (simple dict instead of cookies)
sessions = {}

# HTML templates
HOME_PAGE = '''<!DOCTYPE html>
<html>
<head>
    <title>Test WordPress</title>
</head>
<body>
    <h1>Test WordPress</h1>
    <p>This is a mock WordPress site for testing HTTP clients</p>
    <p><a href="/wp-login.php">Login</a></p>
</body>
</html>
'''

LOGIN_PAGE = '''<!DOCTYPE html>
<html>
<head>
    <title>Log In ‹ Test WordPress</title>
</head>
<body>
    <h1>Log In</h1>
    <form method="post" action="/wp-login.php">
        <p>
            <label for="user_login">Username</label>
            <input type="text" name="log" id="user_login">
        </p>
        <p>
            <label for="user_pass">Password</label>
            <input type="password" name="pwd" id="user_pass">
        </p>
        <input type="hidden" name="redirect_to" value="/wp-admin/">
        <input type="hidden" name="testcookie" value="1">
        <p>
            <input type="submit" name="wp-submit" value="Log In">
        </p>
    </form>
</body>
</html>
'''

ADMIN_PAGE = '''<!DOCTYPE html>
<html>
<head>
    <title>Dashboard ‹ Test WordPress</title>
</head>
<body>
    <h1>Dashboard</h1>
    <p>Welcome {{ username }}!</p>
    <p><a href="/wp-admin/upload.php">Media</a></p>
    <p><a href="/wp-admin/media-new.php">Add New Media</a></p>
</body>
</html>
'''

MEDIA_NEW_PAGE = '''<!DOCTYPE html>
<html>
<head>
    <title>Add New Media ‹ Test WordPress</title>
</head>
<body>
    <h1>Add New Media</h1>
    <form enctype="multipart/form-data" method="post" action="/wp-admin/async-upload.php">
        <input type="file" name="file">
        <input type="hidden" name="_wpnonce" value="wp_mock_nonce">
        <input type="hidden" name="action" value="upload-attachment">
        <input type="submit" value="Upload">
    </form>
</body>
</html>
'''

@app.route('/')
def home():
    return HOME_PAGE

@app.route('/wp-login.php', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('log')
        password = request.form.get('pwd')
        
        if username in USERS and USERS[username] == password:
            # Create a session token
            session_token = hashlib.md5(f"{username}{time.time()}".encode()).hexdigest()
            sessions[session_token] = username
            
            # Set cookie in headers
            response = redirect('/wp-admin/')
            response.headers['Set-Cookie'] = f"wordpress_logged_in={session_token}; Path=/"
            return response
        else:
            # Failed login
            return render_template_string(LOGIN_PAGE + '<p style="color:red">Error: Invalid username or password</p>')
    
    return LOGIN_PAGE

def check_auth():
    auth_cookie = request.cookies.get('wordpress_logged_in')
    if auth_cookie and auth_cookie in sessions:
        return sessions[auth_cookie]
    
    # Check Authorization header too (for raw socket implementations)
    auth_header = request.headers.get('Cookie')
    if auth_header and 'wordpress_logged_in=' in auth_header:
        token = auth_header.split('wordpress_logged_in=')[1].split(';')[0]
        if token in sessions:
            return sessions[token]
    
    return None

@app.route('/wp-admin/')
def admin():
    username = check_auth()
    if username:
        return render_template_string(ADMIN_PAGE, username=username)
    return redirect('/wp-login.php')

@app.route('/wp-admin/media-new.php')
def media_new():
    username = check_auth()
    if username:
        return MEDIA_NEW_PAGE
    return redirect('/wp-login.php')

@app.route('/wp-admin/async-upload.php', methods=['POST'])
def async_upload():
    username = check_auth()
    if not username:
        return redirect('/wp-login.php')
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'})
    
    # Create year/month directory structure
    year_month = time.strftime('%Y/%m/')
    upload_dir = os.path.join('uploads/wp-content/uploads', year_month)
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save the file
    file_path = os.path.join(upload_dir, file.filename)
    file.save(file_path)
    
    # Return success response
    upload_url = f"/wp-content/uploads/{year_month}{file.filename}"
    return jsonify({
        'success': True,
        'data': {
            'url': upload_url,
            'file': file.filename
        }
    })

@app.route('/wp-content/uploads/<path:filepath>')
def serve_uploads(filepath):
    return send_from_directory('uploads/wp-content/uploads', filepath)

if __name__ == '__main__':
    print("Starting mock WordPress server on http://localhost:8000")
    print("Username: test")
    print("Password: test123QWE@AD")
    app.run(host='0.0.0.0', port=8000, debug=True)
