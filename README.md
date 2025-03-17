# WordPress HTTP Client Programs

A collection of Python-based HTTP client implementations using raw sockets to perform various WordPress operations.

## Overview

This project provides several Python programs for interacting with WordPress through HTTP:

- HTTP GET requests
- HTTP POST requests for authentication
- File upload to WordPress
- File download from WordPress

## Setting up the Test Environment

1. Install Flask for the local test server:

   ```bash
   pip install flask
   ```

2. Launch the WordPress test server:

   ```bash
   python local_wordpress_server.py
   ```

3. The mock WordPress server will be available at http://localhost:8000

   - Pre-configured credentials:
     - Username: test
     - Password: test123QWE@AD

4. Create a test image file for upload testing:
   ```bash
   echo "Test image content" > test.png
   ```

## Using the Client Programs

### HTTP GET

Retrieve content from a WordPress site:

```bash
python httpget.py --url http://localhost:8000/
```

### HTTP POST (Authentication)

Authenticate with WordPress credentials:

```bash
python httppost.py --url http://localhost:8000/ --user test --password test123QWE@AD
```

### File Upload

Upload files to WordPress (images, documents, etc.):

```bash
python httpupload.py --url http://localhost:8000/ --user test --password test123QWE@AD --local-file README.md
```

### File Download

Download previously uploaded files:

```bash
python httpdownload.py --url http://localhost:8000/ --remote-file /wp-content/uploads/2025/3/README.md
```

**Note:** The remote file path may vary depending on WordPress's current year/month storage structure. Check the output from the upload command for the correct path.
