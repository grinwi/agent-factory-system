#!/bin/bash
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  python3 scripts/bootstrap.py
else
  echo "Python 3.11 or newer is required. Please install python3 and run this again."
fi

echo
read -r -p "Press Enter to close this window..." _
