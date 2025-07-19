#!/bin/bash

echo "📊 이더리움 매매봇 모니터링"
echo "============================"

# PID 확인
if [ -f "eth_bot.pid" ]; then
    PID=$(cat eth_bot.pid)
    echo "🤖 봇 PID: $PID"
    
    # 프로세스 실행 확인
    if ps -p $PID > /dev/null; then
        echo "✅ 봇이 실행 중입니다!"
        
        # 로그 실시간 확인
        echo "📋 실시간 로그 (Ctrl+C로 종료):"
        echo "----------------------------------------"
        tail -f eth_bot.log
    else
        echo "❌ 봇이 실행되지 않고 있습니다."
        echo "🔄 봇을 다시 시작하려면: ./run_eth_bot.sh"
    fi
else
    echo "❌ PID 파일이 없습니다."
    echo "🔄 봇을 시작하려면: ./run_eth_bot.sh"
fi 