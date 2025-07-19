#!/bin/bash

echo "🚀 이더리움 매매봇 실행 스크립트"
echo "=================================="

# 1. 비트코인 → 이더리움 전환
echo "📊 1단계: 비트코인 → 이더리움 전환"
python3 switch_to_eth_trading.py

# 잠시 대기
sleep 10

# 2. 이더리움 매매봇 실행
echo "🤖 2단계: 이더리움 매매봇 실행"
echo "📝 로그 파일: eth_bot.log"
echo "⏳ 백그라운드에서 실행 중..."

# 백그라운드에서 실행
nohup python3 eth_trading_bot.py > eth_bot.log 2>&1 &

# 프로세스 ID 저장
echo $! > eth_bot.pid

echo "✅ 이더리움 매매봇이 백그라운드에서 실행 중입니다!"
echo "📊 PID: $(cat eth_bot.pid)"
echo "📋 로그 확인: tail -f eth_bot.log"
echo "🛑 중지: kill $(cat eth_bot.pid)" 