#!/usr/bin/env python3

import socket, ssl, re, os, time, mimetypes, argparse
from urllib.parse import urlparse, urlencode
from contextlib import closing

def send_request(host, method, path, headers, body=None, port=80, secure=False):
    """Send HTTP request and return response"""
    with closing(socket.socket()) as s:
        if secure:
            s = ssl.create_default_context().wrap_socket(s, server_hostname=host)
        s.connect((host, port))
        
        # Send headers
        req = f"{method} {path} HTTP/1.1\r\n"
        for k, v in headers.items():
            req += f"{k}: {v}\r\n"
        req += "\r\n"
        s.sendall(req.encode())
        
        # Send body if present
        if body:
            s.sendall(body if isinstance(body, bytes) else body.encode())
        
        # Get response
        return b''.join(iter(lambda: s.recv(8192), b''))

def extract_cookies(response):
    """Extract cookies from HTTP response"""
    cookies = {}
    text = response.decode('utf-8', errors='replace')
    for line in text.split('\r\n'):
        if line.startswith('Set-Cookie:'):
            parts = line[11:].strip().split(';')[0].strip().split('=', 1)
            if len(parts) == 2:
                cookies[parts[0]] = parts[1]
    return cookies

def login(url, username, password):
    """Login to WordPress and get session cookies"""
    parsed = urlparse(url)
    host, port = parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80)
    secure = parsed.scheme == 'https'
    
    # Get login page cookies
    headers = {"Host": host, "User-Agent": "Custom-HTTP-Client", "Connection": "close"}
    resp = send_request(host, "GET", "/wp-login.php", headers, port=port, secure=secure)
    cookies = extract_cookies(resp)
    
    # Send login request
    login_data = urlencode({
        'log': username, 'pwd': password, 'wp-submit': 'Log In',
        'redirect_to': f"{parsed.scheme}://{host}/wp-admin/", 'testcookie': '1'
    })
    
    headers = {
        "Host": host, "User-Agent": "Custom-HTTP-Client",
        "Content-Type": "application/x-www-form-urlencoded",
        "Content-Length": str(len(login_data)),
        "Connection": "close"
    }
    if cookies:
        headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    
    resp = send_request(host, "POST", "/wp-login.php", headers, login_data, port, secure)
    login_cookies = extract_cookies(resp)
    cookies.update(login_cookies)
    
    # Check login success
    text = resp.decode('utf-8', errors='replace')
    if 'wordpress_logged_in' in str(cookies) or ('Location:' in text and '/wp-admin/' in text):
        return cookies
    return None

def http_upload_file(url, username, password, local_file):
    """Upload a file to WordPress"""
    if not os.path.exists(local_file):
        print(f"File {local_file} does not exist")
        return
    
    # Login
    cookies = login(url, username, password)
    if not cookies:
        print("Login failed")
        return
    
    # Prepare upload
    parsed = urlparse(url)
    host, port = parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80)
    secure = parsed.scheme == 'https'
    
    try:
        # Create multipart form data
        boundary = f"---------------------------{int(time.time())}"
        filename = os.path.basename(local_file)
        content_type = mimetypes.guess_type(local_file)[0] or 'application/octet-stream'
        
        with open(local_file, 'rb') as f:
            file_content = f.read()
        
        # Build the form data
        body = []
        body.append(f"--{boundary}\r\n".encode())
        body.append(f'Content-Disposition: form-data; name="_wpnonce"\r\n\r\n'.encode())
        body.append(f"wp_mock_nonce\r\n".encode())
        body.append(f"--{boundary}\r\n".encode())
        body.append(f'Content-Disposition: form-data; name="action"\r\n\r\n'.encode())
        body.append(f"upload-attachment\r\n".encode())
        body.append(f"--{boundary}\r\n".encode())
        body.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
        body.append(f'Content-Type: {content_type}\r\n\r\n'.encode())
        body.append(file_content)
        body.append(f"\r\n--{boundary}--\r\n".encode())
        
        data = b''.join(body)
        
        # Send upload request
        headers = {
            "Host": host,
            "User-Agent": "Custom-HTTP-Client",
            "Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(data)),
            "Connection": "close"
        }
        
        resp = send_request(host, "POST", "/wp-admin/async-upload.php", headers, data, port, secure)
        text = resp.decode('utf-8', errors='replace')
        
        # Process response
        if '200 OK' in text and ('success' in text.lower() or 'file' in text.lower()):
            url_match = re.search(r'"url"\s*:\s*"([^"]+)"', text)
            if url_match:
                print(f"Upload success. URL: {url_match.group(1)}")
            else:
                upload_path = f"/wp-content/uploads/{time.strftime('%Y/%m/')}{filename}"
                print(f"Upload success. URL: {parsed.scheme}://{host}{upload_path}")
        else:
            print("Upload failed.")
            if 'error' in text.lower():
                error = re.search(r'"error"\s*:\s*"([^"]+)"', text)
                if error:
                    print(f"Error: {error.group(1)}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HTTP file upload client")
    parser.add_argument('--url', required=True, help='WordPress URL')
    parser.add_argument('--user', required=True, help='WordPress username')
    parser.add_argument('--password', required=True, help='WordPress password')
    parser.add_argument('--local-file', required=True, help='Path to local file to upload')
    args = parser.parse_args()
    
    http_upload_file(args.url, args.user, args.password, args.local_file)
