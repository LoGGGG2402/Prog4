#!/usr/bin/env python3

import socket, ssl, os, argparse
from urllib.parse import urlparse
from contextlib import closing

def decode_chunked(data):
    """Decode chunked transfer encoding"""
    result = bytearray()
    i = 0
    
    while i < len(data):
        line_end = data.find(b'\r\n', i)
        if line_end == -1:
            break
            
        try:
            chunk_size = int(data[i:line_end].split(b';')[0], 16)
        except ValueError:
            break
        
        if chunk_size == 0:
            break
            
        chunk_start = line_end + 2
        chunk_end = chunk_start + chunk_size
        
        if chunk_end <= len(data):
            result.extend(data[chunk_start:chunk_end])
            i = chunk_end + 2  # Skip CRLF
        else:
            break
            
    return bytes(result)

def get_file_type(path):
    """Determine file type based on extension"""
    ext = os.path.splitext(path)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
        return "ảnh"
    elif ext in ['.md', '.txt', '.html', '.css', '.js']:
        return "văn bản"
    elif ext in ['.pdf', '.doc', '.docx']:
        return "tài liệu"
    return "dữ liệu"

def try_download(url, path):
    """Attempt to download file"""
    parsed = urlparse(url)
    host, port = parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80)
    secure = parsed.scheme == 'https'
    file_type = get_file_type(path)
    
    with closing(socket.socket()) as s:
        try:
            if secure:
                s = ssl.create_default_context().wrap_socket(s, server_hostname=host)
            s.connect((host, port))
            
            s.sendall(f"GET {path} HTTP/1.1\r\nHost: {host}\r\n"
                      f"User-Agent: Custom-HTTP-Client\r\nConnection: close\r\n\r\n".encode())
            
            resp = b''.join(iter(lambda: s.recv(8192), b''))
            
            if b"HTTP/1." in resp:
                header_end = resp.find(b'\r\n\r\n')
                if header_end != -1:
                    headers = resp[:header_end].decode('utf-8', errors='replace')
                    body = resp[header_end + 4:]
                    
                    # Handle chunked encoding
                    if "Transfer-Encoding: chunked" in headers:
                        body = decode_chunked(body)
                    
                    # Check for success
                    if "200 OK" in headers:
                        print(f"Kích thước file {file_type}: {len(body)} bytes")
                        
                        # Save file
                        filename = os.path.basename(path)
                        with open(filename, 'wb') as f:
                            f.write(body)
                        print(f"File saved as: {filename}")
                        return True
            
            return False
                
        except Exception as e:
            print(f"Error: {e}")
            return False

def http_download_file(url, remote_file):
    """Download file with normalized path"""
    # Ensure path starts with slash
    if not remote_file.startswith('/'):
        remote_file = '/' + remote_file
    
    # Try original path
    if try_download(url, remote_file):
        return True
    
    # Try alternate paths (handle month format differences)
    if '/uploads/' in remote_file:
        parts = remote_file.split('/')
        if len(parts) >= 5 and parts[3].isdigit():
            if len(parts[3]) == 1:  # Add leading zero
                parts[3] = parts[3].zfill(2)
                if try_download(url, '/'.join(parts)):
                    return True
            elif parts[3].startswith('0'):  # Remove leading zero
                parts[3] = parts[3].lstrip('0')
                if try_download(url, '/'.join(parts)):
                    return True
    
    print(f"Không tồn tại file {get_file_type(remote_file)}")
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HTTP file download client")
    parser.add_argument('--url', required=True, help='Base URL')
    parser.add_argument('--remote-file', required=True, help='Path to file')
    args = parser.parse_args()
    
    http_download_file(args.url, args.remote_file)
