#!/usr/bin/env python3

import socket
import argparse
import re
import ssl
from urllib.parse import urlparse
from contextlib import closing

def http_get(url):
    # Parse the URL
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname
    port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
    path = parsed_url.path or '/'
    
    # Use contextlib.closing to ensure socket is properly closed
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as client_socket:
        try:
            # Wrap with SSL if https
            if parsed_url.scheme == 'https':
                context = ssl.create_default_context()
                client_socket = context.wrap_socket(client_socket, server_hostname=hostname)
            
            # Connect to server
            client_socket.connect((hostname, port))
            
            # Prepare and send HTTP request
            request = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {hostname}\r\n"
                "User-Agent: Custom-HTTP-Client\r\n"
                "Accept: text/html\r\n"
                "Connection: close\r\n\r\n"
            )
            
            client_socket.sendall(request.encode())
            
            # Receive response efficiently
            chunks = []
            while True:
                data = client_socket.recv(8192)  # Increased buffer size
                if not data:
                    break
                chunks.append(data)
                
            # Join all chunks at once
            response = b''.join(chunks)
            response_text = response.decode('utf-8', errors='replace')
            
            # Extract title
            title_match = re.search(r'<title>(.*?)</title>', response_text, re.DOTALL)
            print(f"Title: {title_match.group(1).strip()}" if title_match else "No title found in the page")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HTTP GET client")
    parser.add_argument('--url', required=True, help='URL to fetch')
    args = parser.parse_args()
    
    http_get(args.url)
