#!/usr/bin/env python3

import socket
import argparse
import re
import ssl
import os
import time
import mimetypes
from urllib.parse import urlparse, urlencode
from contextlib import closing

def create_connection(parsed_url):
    """Create and return a socket connection to the server"""
    hostname = parsed_url.hostname
    port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    if parsed_url.scheme == 'https':
        context = ssl.create_default_context()
        sock = context.wrap_socket(sock, server_hostname=hostname)
    
    sock.connect((hostname, port))
    return sock, hostname

def send_request(sock, method, path, headers, body=None):
    """Send HTTP request and return response"""
    request = f"{method} {path} HTTP/1.1\r\n"
    for key, value in headers.items():
        request += f"{key}: {value}\r\n"
    request += "\r\n"
    
    sock.sendall(request.encode())
    
    if body:
        if isinstance(body, str):
            sock.sendall(body.encode())
        else:
            sock.sendall(body)
    
    chunks = []
    while True:
        data = sock.recv(8192)
        if not data:
            break
        chunks.append(data)
    
    return b''.join(chunks)

def get_cookies_from_response(response_text):
    cookies = {}
    for line in response_text.split('\r\n'):
        if line.startswith('Set-Cookie:'):
            cookie_part = line[11:].strip()
            if ';' in cookie_part:
                cookie_name_val = cookie_part.split(';')[0].strip()
                if '=' in cookie_name_val:
                    name, val = cookie_name_val.split('=', 1)
                    cookies[name] = val
    return cookies

def login_and_get_cookies(parsed_url, hostname, port, username, password):
    cookies = {}
    
    try:
        # Get login page
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as client_socket:
            if parsed_url.scheme == 'https':
                context = ssl.create_default_context()
                client_socket = context.wrap_socket(client_socket, server_hostname=hostname)
            
            client_socket.connect((hostname, port))
            
            headers = {
                "Host": hostname,
                "User-Agent": "Custom-HTTP-Client",
                "Accept": "text/html",
                "Connection": "close"
            }
            
            response = send_request(client_socket, "GET", "/wp-login.php", headers)
            response_text = response.decode('utf-8', errors='replace')
            
            # Get cookies
            initial_cookies = get_cookies_from_response(response_text)
        
        # Login
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as client_socket:
            if parsed_url.scheme == 'https':
                context = ssl.create_default_context()
                client_socket = context.wrap_socket(client_socket, server_hostname=hostname)
            
            client_socket.connect((hostname, port))
            
            post_data = {
                'log': username,
                'pwd': password,
                'wp-submit': 'Log In',
                'redirect_to': f"{parsed_url.scheme}://{hostname}/wp-admin/",
                'testcookie': '1'
            }
            
            post_data_encoded = urlencode(post_data)
            
            headers = {
                "Host": hostname,
                "User-Agent": "Custom-HTTP-Client",
                "Accept": "text/html,application/xhtml+xml",
                "Cookie": "; ".join([f"{k}={v}" for k, v in initial_cookies.items()]),
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(post_data_encoded)),
                "Connection": "close"
            }
            
            response = send_request(client_socket, "POST", "/wp-login.php", headers, post_data_encoded)
            response_text = response.decode('utf-8', errors='replace')
            
            # Update cookies
            cookies.update(get_cookies_from_response(response_text))
            
            # Check login success
            if 'wordpress_logged_in' in str(cookies) or ('Location:' in response_text and '/wp-admin/' in response_text):
                return cookies
            
        return None
            
    except Exception as e:
        print(f"Login Error: {e}")
        return None

def http_upload_file(url, username, password, local_file):
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname
    port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
    
    # Check if file exists
    if not os.path.exists(local_file):
        print(f"File {local_file} does not exist")
        return
    
    try:
        # Login first to get cookies
        cookies = login_and_get_cookies(parsed_url, hostname, port, username, password)
        if not cookies:
            print("Login failed")
            return
        
        # Upload file
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as client_socket:
            if parsed_url.scheme == 'https':
                context = ssl.create_default_context()
                client_socket = context.wrap_socket(client_socket, server_hostname=hostname)
            
            client_socket.connect((hostname, port))
            
            # Generate boundary and prepare file
            boundary = f"---------------------------{int(time.time())}"
            filename = os.path.basename(local_file)
            content_type = mimetypes.guess_type(local_file)[0] or 'application/octet-stream'
            
            with open(local_file, 'rb') as f:
                file_content = f.read()
            
            # Build multipart form data
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
            
            body_bytes = b''.join(body)
            
            headers = {
                "Host": hostname,
                "User-Agent": "Custom-HTTP-Client",
                "Cookie": "; ".join([f"{k}={v}" for k, v in cookies.items()]),
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body_bytes)),
                "Connection": "close"
            }
            
            response = send_request(client_socket, "POST", "/wp-admin/async-upload.php", headers, body_bytes)
            response_text = response.decode('utf-8', errors='replace')
            
            # Check upload success
            if '200 OK' in response_text and ('success' in response_text.lower() or 'file' in response_text.lower()):
                url_match = re.search(r'"url"\s*:\s*"([^"]+)"', response_text)
                if url_match:
                    upload_url = url_match.group(1)
                    print(f"Upload success. File upload url: {upload_url}")
                else:
                    upload_path = f"/wp-content/uploads/{time.strftime('%Y/%m/')}{filename}"
                    upload_url = f"{parsed_url.scheme}://{hostname}{upload_path}"
                    print(f"Upload success. File upload url: {upload_url}")
            else:
                print("Upload failed.")
                if 'error' in response_text.lower():
                    error_match = re.search(r'"error"\s*:\s*"([^"]+)"', response_text)
                    if error_match:
                        print(f"Error message: {error_match.group(1)}")
            
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
