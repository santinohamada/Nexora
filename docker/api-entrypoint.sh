#!/bin/sh
set -e
VOICES_DIR=/app/voices
ONNX="$VOICES_DIR/es_AR-daniela-high.onnx"
JSON="$VOICES_DIR/es_AR-daniela-high.onnx.json"
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_AR/daniela/high"
mkdir -p "$VOICES_DIR"
if [ ! -f "$ONNX" ]; then
  curl -fsSL "$BASE/es_AR-daniela-high.onnx" -o "$ONNX"
fi
if [ ! -f "$JSON" ]; then
  curl -fsSL "$BASE/es_AR-daniela-high.onnx.json" -o "$JSON"
fi
exec "$@"
