#!/usr/bin/env bash
# Installs everything a fresh cloud session needs to build quiz videos.
# Usage: bash pipeline/setup.sh    (takes ~2-4 minutes)
set -e
pip install --break-system-packages -q kokoro-onnx soundfile scipy pillow numpy 2>&1 | grep -v WARNING || true
python3 -c "import bpy" 2>/dev/null || pip install --break-system-packages -q bpy 2>&1 | grep -v WARNING || true
mkdir -p /home/claude/tts
cd /home/claude/tts
[ -f kokoro-v1.0.int8.onnx ] || curl -sSL -O https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx
[ -f voices-v1.0.bin ] || curl -sSL -O https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
python3 -c "import bpy, kokoro_onnx, scipy; print('setup ok, blender', bpy.app.version_string)"
