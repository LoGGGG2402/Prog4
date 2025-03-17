#!/usr/bin/env python3

import socket
import argparse
import ssl
import os
from urllib.parse import urlparse
from contextlib import closing

def decode_chunked_body(chunked_body):
    decoded_body = bytearray()
    index = 0
    
    while index < len(chunked_body):
        # Find the end of the chunk size line
        line_end = chunked_body.find(b'\r\n', index)
        if line_end == -1:
            break
            
        # Get chunk size in hex
        chunk_size_hex = chunked_body[index:line_end].split(b';')[0]  # Remove chunk extensions
        try:
            chunk_size = int(chunk_size_hex, 16)
        except ValueError:
            break
            
        # End of chunked data
        if chunk_size == 0:
            break
            
        # Extract the chunk data
        chunk_start = line_end + 2
        chunk_end = chunk_start + chunk_size
        
        if chunk_end <= len(chunked_body):
            decoded_body.extend(chunked_body[chunk_start:chunk_end])
            index = chunk_end + 2  # Skip the CRLF at the end of the chunk
        else:
            break
            
    return bytes(decoded_body)

def get_file_type(file_path):
    """Determine file type based on extension"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
        return "ảnh"
    elif ext in ['.md', '.txt', '.html', '.css', '.js']:
        return "văn bản"
    elif ext in ['.pdf', '.doc', '.docx']:
        return "tài liệu"
    else:
        return "dữ liệu"

def normalize_path(remote_file):
    """Generate alternative path versions to handle month format differences"""
    if '/uploads/' in remote_file:
        parts = remote_file.split('/')
        if len(parts) >= 5 and parts[3].isdigit():
            if len(parts[3]) == 1:
                # Add leading zero
                parts[3] = parts[3].zfill(2)
                return '/'.join(parts)
            elif len(parts[3]) == 2 and parts[3].startswith('0'):
                # Remove leading zero
                parts[3] = parts[3].lstrip('0')
                return '/'.join(parts)
    return None

def http_download_file(url, remote_file):
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname
    port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
    
    # Ensure the remote file path starts with a slash
    if not remote_file.startswith('/'):
        remote_file = '/' + remote_file
    
    # Try to normalize the path
    alt_remote_file = normalize_path(remote_file)
    
    # Create socket and download
    return download_with_path(parsed_url, hostname, port, remote_file) or \
           (alt_remote_file and download_with_path(parsed_url, hostname, port, alt_remote_file))

def download_with_path(parsed_url, hostname, port, remote_file):
    file_type = get_file_type(remote_file)
    
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as client_socket:
        try:
            # Wrap with SSL if https
            if parsed_url.scheme == 'https':
                context = ssl.create_default_context()
                client_socket = context.wrap_socket(client_socket, server_hostname=hostname)
            
            # Connect to server
            client_socket.connect((hostname, port))
            
            # Prepare and send HTTP request
            headers = {
                "Host": hostname,
                "User-Agent": "Custom-HTTP-Client",
                "Connection": "close"
            }
            
            request = f"GET {remote_file} HTTP/1.1\r\n"
            for key, value in headers.items():
                request += f"{key}: {value}\r\n"
            request += "\r\n"
            
            client_socket.sendall(request.encode())
            
            # Receive response
            chunks = []
            while True:
                data = client_socket.recv(8192)
                if not data:
                    break
                chunks.append(data)
                
            response = b''.join(chunks)
            
            # Check if the response has a valid HTTP status
            if b"HTTP/1." in response:
                # Split headers and body
                header_end = response.find(b'\r\n\r\n')
                if header_end != -1:
                    headers = response[:header_end].decode('utf-8', errors='replace')
                    body = response[header_end + 4:]
                    
                    # Check for chunked encoding
                    if "Transfer-Encoding: chunked" in headers:
                        body = decode_chunked_body(body)
                    
                    # Check if the file was found
                    if "200 OK" in headers:
                        file_size = len(body)
                        print(f"Kích thước file {file_type}: {file_size} bytes")
                        
                        # Save the file
                        local_filename = os.path.basename(remote_file)
                        with open(local_filename, 'wb') as f:
                            f.write(body)
                        print(f"File saved as: {local_filename}")
                        return True
            
            print(f"Không tồn tại file {file_type}")
            return False
                
        except Exception as e:
            print(f"Error: {e}")
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HTTP file download client")
    parser.add_argument('--url', required=True, help='Base WordPress URL')
    parser.add_argument('--remote-file', required=True, help='Path to remote file to download')
    args = parser.parse_args()
    
    http_download_file(args.url, args.remote_file)
