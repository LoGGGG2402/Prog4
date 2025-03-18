# WordPress HTTP Client Programs

A lightweight collection of Python-based HTTP client implementations using raw sockets for WordPress operations.

## Overview

This project provides optimized Python programs for interacting with WordPress via HTTP:

- **httpget.py**: Simple GET requests to retrieve web content
- **httppost.py**: General-purpose POST requests (including WordPress authentication)
- **httpupload.py**: File upload to WordPress media library
- **httpdownload.py**: File download from WordPress uploads directory

## Setting up the Test Environment

1. Install the local test server requirements:

   ```bash
   pip install flask==2.0.1 werkzeug==2.0.1
   ```

2. Launch the WordPress test server:

   ```bash
   cd test_server
   ./setup_environment.sh
   ./start_server.sh
   ```

3. The WordPress test server runs at http://localhost:8000
   - Credentials: `test` / `test123QWE@AD`

## Using the Client Programs

### HTTP GET

Fetch a web page and display its title:

```bash
python3 httpget.py --url http://localhost:8000/
```

### HTTP POST

#### WordPress Login

```bash
python3 httppost.py --url http://localhost:8000/ --user test --password test123QWE@AD
```

#### General POST Requests

Send form data:
```bash
python3 httppost.py --url http://localhost:8000/some-endpoint --form-param key1=value1 key2=value2
```

Send JSON data:
```bash
python3 httppost.py --url http://localhost:8000/api/endpoint --json '{"key":"value"}'
```

With custom headers:
```bash
python3 httppost.py --url http://localhost:8000/endpoint --header Authorization="Bearer token"
```

### File Upload

Upload media to WordPress:

```bash
python3 httpupload.py --url http://localhost:8000/ --user test --password test123QWE@AD --local-file image.jpg
```

### File Download

Download a file from WordPress:

```bash
python3 httpdownload.py --url http://localhost:8000/ --remote-file /wp-content/uploads/2023/05/image.jpg
```

> **Note:** WordPress organizes uploads by year/month. The download script automatically handles both formats (e.g., `/2023/5/` and `/2023/05/`).

## Code Features

- Raw socket communication (no external HTTP libraries)
- SSL/TLS support for HTTPS
- Automatic handling of chunked transfer encoding
- Efficient memory usage for large files
- Path normalization for WordPress date-based directory structure
