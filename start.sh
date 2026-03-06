#!/bin/bash
set -e

# Chạy Discord bot ở background
python main.py &
BOT_PID=$!

# Chạy FastAPI server ở background
uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} &
API_PID=$!

echo "✅ Bot PID: $BOT_PID | API PID: $API_PID"

# Chờ cả 2 process — nếu 1 cái chết thì kill cái kia và thoát
wait_for_any() {
    while true; do
        if ! kill -0 $BOT_PID 2>/dev/null; then
            echo "❌ Bot process đã dừng (PID $BOT_PID), dừng toàn bộ..."
            kill $API_PID 2>/dev/null || true
            exit 1
        fi
        if ! kill -0 $API_PID 2>/dev/null; then
            echo "❌ API process đã dừng (PID $API_PID), dừng toàn bộ..."
            kill $BOT_PID 2>/dev/null || true
            exit 1
        fi
        sleep 5
    done
}

wait_for_any
