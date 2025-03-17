#!/bin/bash

echo "Setting up the test server environment..."

# Create virtual environment
python3 -m venv myenv

# Activate virtual environment
source myenv/bin/activate

# Install required packages with specified versions
pip install -r requirements.txt

echo "Environment setup complete!"
echo "You can now run ./start_server.sh to start the server."
