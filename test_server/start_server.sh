#!/bin/bash

# Activate virtual environment
source myenv/bin/activate

echo "Starting local WordPress test server..."
python3 local_wordpress_server.py
