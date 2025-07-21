# CoinSpot Trading Bot

이더리움 자동매매 봇 - V2 백테스트 전략 기반

## 📊 전략 설명

### 실전 자동매매 전략 (2024 최신)

- **매수 조건:**
  - 1분봉 200MA 위 + 15분봉 200MA 위 (상승장 필터)
  - RSI < 30 (과매도)
  - 가격이 볼린저밴드 하단 터치
  - MACD > MACD Signal (상승)
  - 거래량 비율 > 1.5
  - 가격이 VWMA 20의 98% 이상

- **매도 조건:**
  - RSI > 70 (과매수)
  - 가격이 볼린저밴드 상단 터치
  - MACD < MACD Signal (하락)
  - 거래량 비율 > 1.2

- **리스크 관리:**
  - 손절: -4%
  - 익절: +6%
  - **트레일링 스탑:**
    - 매수 후 2% 이상 수익 발생 시 활성화
    - 1% 단위로 손절선 추적, 가격 반전 시 자동 매도(이익 실현)

- **분석 주기:** 1분
- **데이터:** 1분 캔들스틱(실시간)

## 🚀 설치 및 실행

### 1. 환경 설정
```bash
# .env 파일 생성
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
PERPLEXITY_API_KEY=your_perplexity_key
```

### 2. 파이썬 모듈 설치 (필수)
아래 명령어로 필요한 파이썬 패키지를 한 번에 설치할 수 있습니다.

```bash
pip install -r requirements.txt
```

또는 개별 설치:
```bash
pip install ccxt pandas numpy requests python-dotenv
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
- `requirements.txt` - 파이썬 의존성 목록

## ⚡️ 실전 적용 방법
- `python3 eth_trading_bot.py` 실행 시 위 전략이 자동 적용됨
- 계좌에 USDT를 입금하면 자동으로 조건에 맞춰 매매
- 24시간 켜두면 시장 상황에 따라 자동매매

## ⚠️ 주의사항
- 실제 거래 전 반드시 소액/테스트로 충분히 검증
- API 키/시크릿은 절대 외부에 노출 금지
- 최소 거래량(0.001 ETH) 및 바이낸스 수수료 고려
- 노트북/PC가 꺼지면 자동매매도 중단됨
- 실전에서는 슬리피지, 체결 지연 등 실환경 변수를 항상 고려

## 📈 백테스트 결과

V2 전략은 백테스트에서 안정적인 수익률을 보여줍니다. 