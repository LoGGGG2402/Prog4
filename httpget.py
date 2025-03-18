#!/usr/bin/env python3

import socket, ssl, re, argparse
from urllib.parse import urlparse
from contextlib import closing

def http_get(url):
    parsed = urlparse(url)
    host, path = parsed.hostname, parsed.path or '/'
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    
    with closing(socket.socket()) as s:
        try:
            # Setup connection
            if parsed.scheme == 'https':
                s = ssl.create_default_context().wrap_socket(s, server_hostname=host)
            s.connect((host, port))
            
            # Send request and get response
            s.sendall(f"GET {path} HTTP/1.1\r\nHost: {host}\r\n"
                      f"User-Agent: Custom-HTTP-Client\r\nConnection: close\r\n\r\n".encode())
            resp = b''.join(iter(lambda: s.recv(8192), b'')).decode('utf-8', errors='replace')
            
            # Extract title
            title = re.search(r'<title>(.*?)</title>', resp, re.DOTALL)
            print(f"Title: {title.group(1).strip()}" if title else "No title found")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HTTP GET client")
    parser.add_argument('--url', required=True, help='URL to fetch')
    http_get(parser.parse_args().url)
