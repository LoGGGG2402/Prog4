#!/usr/bin/env python3

import socket, ssl, json, re, argparse
from urllib.parse import urlparse, urlencode
from contextlib import closing

def request(host, method, path, headers, body=None, port=80, secure=False):
    """Send HTTP request and return response"""
    with closing(socket.socket()) as s:
        if secure:
            s = ssl.create_default_context().wrap_socket(s, server_hostname=host)
        s.connect((host, port))
        
        req = f"{method} {path} HTTP/1.1\r\n" + "\r\n".join(f"{k}: {v}" for k, v in headers.items()) + "\r\n\r\n"
        s.sendall(req.encode())
        if body:
            s.sendall(body.encode() if isinstance(body, str) else body)
        
        return b''.join(iter(lambda: s.recv(8192), b'')).decode('utf-8', errors='replace')

def extract_cookies(response):
    """Extract cookies from response headers"""
    cookies = {}
    for line in response.split('\r\n'):
        if line.startswith('Set-Cookie:'):
            parts = line[11:].split(';')[0].strip().split('=', 1)
            if len(parts) == 2:
                cookies[parts[0]] = parts[1]
    return cookies

def http_post(url, data=None, content_type=None, headers=None, json_data=None, follow_redirects=True):
    """General purpose HTTP POST function"""
    parsed = urlparse(url)
    host, path = parsed.hostname, parsed.path or '/'
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    secure = parsed.scheme == 'https'
    
    # Setup headers
    req_headers = {
        "Host": host,
        "User-Agent": "Custom-HTTP-Client",
        "Accept": "text/html,application/json",
        "Connection": "close"
    }
    if headers:
        req_headers.update(headers)
    
    # Prepare body
    body = None
    if json_data:
        body = json.dumps(json_data)
        req_headers["Content-Type"] = "application/json"
    elif data:
        if isinstance(data, dict):
            body = urlencode(data)
            req_headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = data
            req_headers.setdefault("Content-Type", "text/plain")
    
    if content_type:
        req_headers["Content-Type"] = content_type
    if body:
        req_headers["Content-Length"] = str(len(body) if isinstance(body, str) else len(body))
    
    try:
        # Send request
        response = request(host, "POST", path, req_headers, body, port, secure)
        
        # Process response
        status = int(response.split('\r\n')[0].split(' ')[1]) if ' ' in response.split('\r\n')[0] else 0
        cookies = extract_cookies(response)
        
        # Handle redirects if needed
        if follow_redirects and 300 <= status < 400:
            location = re.search(r'Location:\s*(.+?)(?:\r\n)', response)
            if location:
                loc = location.group(1).strip()
                loc = f"{parsed.scheme}://{host}{loc}" if loc.startswith('/') else loc
                print(f"Following redirect to: {loc}")
                
                # Perform redirect
                redirect = urlparse(loc)
                redir_headers = {"Host": redirect.hostname, "User-Agent": "Custom-HTTP-Client"}
                if cookies:
                    redir_headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
                
                redir_resp = request(
                    redirect.hostname, "GET", redirect.path or '/', redir_headers,
                    port=redirect.port or (443 if redirect.scheme == 'https' else 80), 
                    secure=redirect.scheme == 'https'
                )
                cookies.update(extract_cookies(redir_resp))
                return redir_resp, 200, cookies
        
        return response, status, cookies
    except Exception as e:
        print(f"Error: {e}")
        return None, 0, {}

def wordpress_login(url, username, password):
    """WordPress login handler"""
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    secure = parsed.scheme == 'https'
    
    # Get initial cookies
    headers = {"Host": host, "User-Agent": "Custom-HTTP-Client", "Connection": "close"}
    resp = request(host, "GET", "/wp-login.php", headers, port=port, secure=secure)
    initial_cookies = extract_cookies(resp)
    
    # Login
    login_data = {
        'log': username, 'pwd': password, 'wp-submit': 'Log In',
        'redirect_to': f"{url.rstrip('/')}/wp-admin/", 'testcookie': '1'
    }
    
    custom_headers = {"Cookie": "; ".join(f"{k}={v}" for k, v in initial_cookies.items())} if initial_cookies else None
    resp, status, cookies = http_post(
        f"{url.rstrip('/')}/wp-login.php", data=login_data, headers=custom_headers
    )
    
    success = ('Location:' in resp and '/wp-admin/' in resp) or 'wordpress_logged_in' in str(cookies)
    print(f"User {username} đăng nhập {'thành công' if success else 'thất bại'}")
    
    return resp, status, cookies

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HTTP POST client")
    parser.add_argument('--url', required=True, help='URL to send POST request to')
    parser.add_argument('--user', help='Username (for WordPress login)')
    parser.add_argument('--password', help='Password (for WordPress login)')
    parser.add_argument('--content-type', help='Content-Type header value')
    parser.add_argument('--form-param', nargs='*', help='Form parameters (key=value)')
    parser.add_argument('--json', help='JSON data to send (as string)')
    parser.add_argument('--header', nargs='*', help='Custom headers (key=value)')
    args = parser.parse_args()
    
    if args.user and args.password:
        # WordPress login
        wordpress_login(args.url, args.user, args.password)
    else:
        # General POST request
        form_data = {}
        if args.form_param:
            for p in args.form_param:
                if '=' in p:
                    k, v = p.split('=', 1)
                    form_data[k] = v
        
        custom_headers = {}
        if args.header:
            for h in args.header:
                if '=' in h:
                    k, v = h.split('=', 1)
                    custom_headers[k] = v
        
        json_data = json.loads(args.json) if args.json else None
        
        resp, status, cookies = http_post(
            args.url, data=form_data or None, content_type=args.content_type,
            headers=custom_headers or None, json_data=json_data
        )
        
        print(f"Status Code: {status}")
        
        if resp:
            # Try to extract useful information
            title = re.search(r'<title>(.*?)</title>', resp, re.DOTALL)
            if title:
                print(f"Response Title: {title.group(1).strip()}")
            
            try:
                body = resp.split('\r\n\r\n', 1)[1] if '\r\n\r\n' in resp else resp
                json_resp = json.loads(body)
                print(f"JSON Response:\n{json.dumps(json_resp, indent=2)}")
            except (json.JSONDecodeError, IndexError):
                body = resp.split('\r\n\r\n', 1)[1] if '\r\n\r\n' in resp else ''
                if body:
                    print(f"Response Body (first 500 chars):\n{body[:500]}{'...' if len(body) > 500 else ''}")
