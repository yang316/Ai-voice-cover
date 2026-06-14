#!/bin/bash
# Download required models
set -e

echo "Downloading Demucs model..."
python3 -c "from demucs.pretrained import get_model; get_model('htdemucs')"

echo "Models downloaded successfully!"
