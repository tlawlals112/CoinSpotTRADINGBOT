#!/bin/bash

echo "🛑 이더리움 매매봇 중지"
echo "======================="

# PID 확인
if [ -f "eth_bot.pid" ]; then
    PID=$(cat eth_bot.pid)
    echo "🤖 봇 PID: $PID"
    
    # 프로세스 실행 확인
    if ps -p $PID > /dev/null; then
        echo "🔄 봇을 중지하는 중..."
        kill $PID
        
        # 잠시 대기
        sleep 3
        
        # 프로세스 확인
        if ps -p $PID > /dev/null; then
            echo "⚠️ 강제 종료 중..."
            kill -9 $PID
        fi
        
        echo "✅ 봇이 중지되었습니다!"
        
        # PID 파일 삭제
        rm -f eth_bot.pid
    else
        echo "❌ 봇이 이미 실행되지 않고 있습니다."
        rm -f eth_bot.pid
    fi
else
    echo "❌ PID 파일이 없습니다."
fi

echo "📊 최종 거래 로그 확인:"
if [ -f "eth_trading_log.json" ]; then
    echo "📋 거래 내역:"
    cat eth_trading_log.json | python3 -m json.tool
else
    echo "❌ 거래 로그 파일이 없습니다."
fi 