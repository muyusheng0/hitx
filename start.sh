#!/bin/bash
cd /home/ubuntu/jlu8
pkill -f "python.*app.py" 2>/dev/null || true
sleep 1
exec python3 app.py >> /tmp/jlu8.log 2>&1
