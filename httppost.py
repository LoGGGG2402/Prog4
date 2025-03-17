#!/usr/bin/env python3

import socket
import argparse
import ssl
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
    request += "\r\n".join(f"{k}: {v}" for k, v in headers.items())
    request += "\r\n\r\n"
    
    if body:
        request += body
    
    sock.sendall(request.encode())
    
    chunks = []
    while True:
        data = sock.recv(8192)
        if not data:
            break
        chunks.append(data)
    
    return b''.join(chunks).decode('utf-8', errors='replace')

def http_post_login(url, username, password):
    parsed_url = urlparse(url)
    login_path = "/wp-login.php"
    
    try:
        # First get the login page
        with closing(create_connection(parsed_url)[0]) as client_socket:
            hostname = create_connection(parsed_url)[1]
            headers = {
                "Host": hostname,
                "User-Agent": "Custom-HTTP-Client",
                "Accept": "text/html",
                "Connection": "close"
            }
            send_request(client_socket, "GET", login_path, headers)
        
        # Send login request
        with closing(create_connection(parsed_url)[0]) as client_socket:
            hostname = create_connection(parsed_url)[1]
            post_data = {
                'log': username,
                'pwd': password,
                'wp-submit': 'Log In',
                'redirect_to': f"{url}/wp-admin/",
                'testcookie': '1'
            }
            
            post_data_encoded = urlencode(post_data)
            headers = {
                "Host": hostname,
                "User-Agent": "Custom-HTTP-Client",
                "Accept": "text/html,application/xhtml+xml",
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(post_data_encoded)),
                "Connection": "close"
            }
            
            response_text = send_request(client_socket, "POST", login_path, headers, post_data_encoded)
            
            # Check login success
            if 'Location:' in response_text and '/wp-admin/' in response_text or 'wordpress_logged_in' in response_text:
                print(f"User {username} đăng nhập thành công")
            else:
                print(f"User {username} đăng nhập thất bại")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HTTP POST client for WordPress login")
    parser.add_argument('--url', required=True, help='WordPress URL')
    parser.add_argument('--user', required=True, help='WordPress username')
    parser.add_argument('--password', required=True, help='WordPress password')
    args = parser.parse_args()
    
    http_post_login(args.url, args.user, args.password)
