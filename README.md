# CoinSpot Trading Bot

이더리움 자동매매 봇 - V2 백테스트 전략 기반

## 📊 전략 설명

### V2 전략 조건
- **매수 조건:**
  - RSI < 30 (과매도)
  - 가격이 볼린저 밴드 하단 터치
  - MACD > MACD Signal (상승)
  - 거래량 비율 > 1.5
  - 가격이 VWMA 20의 98% 이상

- **매도 조건:**
  - RSI > 70 (과매수)
  - 가격이 볼린저 밴드 상단 터치
  - MACD < MACD Signal (하락)
  - 거래량 비율 > 1.2

### 리스크 관리
- **손절:** -4%
- **익절:** +6%
- **분석 주기:** 1분
- **데이터:** 1분 캔들스틱

## 🚀 설치 및 실행

### 1. 환경 설정
```bash
# .env 파일 생성
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
PERPLEXITY_API_KEY=your_perplexity_key
```

### 2. 의존성 설치
```bash
pip install ccxt pandas numpy requests
```

### 3. 실행
```bash
# 이더리움 봇 실행
python eth_trading_bot.py

# 백그라운드 실행
./run_eth_bot.sh

# 모니터링
./monitor_eth_bot.sh
```

## 📁 주요 파일

- `eth_trading_bot.py` - 메인 이더리움 봇
- `switch_to_eth_trading.py` - 비트코인 → 이더리움 전환
- `run_eth_bot.sh` - 백그라운드 실행 스크립트
- `monitor_eth_bot.sh` - 모니터링 스크립트
- `high_risk_reward_backtest_v2.py` - V2 백테스트

## ⚠️ 주의사항

- 실제 거래에 사용하기 전에 충분한 테스트 필요
- API 키는 절대 공개하지 마세요
- 거래량이 적은 코인은 주의해서 사용
- 최소 거래량 (0.001 ETH) 고려

## 📈 백테스트 결과

V2 전략은 백테스트에서 안정적인 수익률을 보여줍니다. 