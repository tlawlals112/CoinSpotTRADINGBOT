#!/usr/bin/env python3
"""
이더리움 전용 매매봇
V2 전략 기반으로 이더리움에 최적화
"""

import ccxt
import pandas as pd
import numpy as np
import os
import time
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

# 환경변수 로드
load_dotenv()

class ETHTradingBot:
    def __init__(self):
        """이더리움 매매봇 초기화"""
        self.exchange = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_API_SECRET'),
            'sandbox': False,
            'enableRateLimit': True
        })
        
        # API 키 설정
        self.perplexity_api_key = os.getenv('PERPLEXITY_API_KEY')
        self.claude_api_key = os.getenv('CLAUDE_API_KEY')
        
        # 거래 설정
        self.symbol = 'ETH/USDT'
        self.position = None
        self.entry_price = None
        self.entry_time = None
        
        # 손익절 설정 (V2 전략 기반)
        self.stop_loss_pct = 0.04  # 4%
        self.take_profit_pct = 0.06  # 6%
        
        # 로그 파일
        self.log_file = 'eth_trading_log.json'
        self.load_trading_log()
        
        print("🚀 이더리움 매매봇 초기화 완료!")
        print(f"📉 손절: {self.stop_loss_pct*100}% | 📈 익절: {self.take_profit_pct*100}%")
    
    def load_trading_log(self):
        """거래 로그 로드"""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    self.trading_log = json.load(f)
            else:
                self.trading_log = {'trades': [], 'balance': 10000}
        except:
            self.trading_log = {'trades': [], 'balance': 10000}
    
    def save_trading_log(self):
        """거래 로그 저장"""
        with open(self.log_file, 'w') as f:
            json.dump(self.trading_log, f, indent=2)
    
    def get_market_data(self):
        """시장 데이터 수집 + 15분봉 200MA 계산"""
        try:
            # 1분봉 데이터 수집 (최근 1000개)
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=self.symbol,
                timeframe='1m',
                limit=1000
            )
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            # 15분봉 리샘플링 및 200MA 계산
            df_15m = df.resample('15T').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })
            df_15m['ma_200'] = df_15m['close'].rolling(window=200).mean()
            # 15분봉 200MA를 1분봉에 forward fill
            df['ma_200_15m'] = df_15m['ma_200'].reindex(df.index, method='ffill')
            return df
        except Exception as e:
            print(f"❌ 시장 데이터 수집 오류: {e}")
            return None
    
    def calculate_indicators(self, df):
        """기술적 지표 계산"""
        try:
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            df['macd'] = exp1 - exp2
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            
            # 볼린저 밴드
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['bb_std'] = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['sma_20'] + (df['bb_std'] * 2)
            df['bb_lower'] = df['sma_20'] - (df['bb_std'] * 2)
            
            # VWMA (Volume Weighted Moving Average)
            df['vwma_20'] = (df['close'] * df['volume']).rolling(window=20).sum() / df['volume'].rolling(window=20).sum()
            
            # 거래량 비율
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            # 200MA (하락장 필터용)
            df['ma_200'] = df['close'].rolling(window=200).mean()
            
            return df
        except Exception as e:
            print(f"❌ 지표 계산 오류: {e}")
            return None
    
    def generate_signals(self, df):
        """매매 신호 생성 (V2+200MA 필터)"""
        try:
            df['signal'] = 0
            # 1분봉 200MA, 15분봉 200MA 모두 위에 있을 때만 매수 신호 허용
            ma_filter = (df['close'] >= df['ma_200']) & (df['close'] >= df['ma_200_15m'])
            # 매수 조건 (V2 전략)
            buy_conditions = (
                (df['rsi'] < 30) &
                (df['close'] < df['bb_lower']) &
                (df['macd'] > df['macd_signal']) &
                (df['volume_ratio'] > 1.5) &
                (df['close'] > df['vwma_20'] * 0.98) &
                ma_filter
            )
            # 매도 조건
            sell_conditions = (
                (df['rsi'] > 70) &
                (df['close'] > df['bb_upper']) &
                (df['macd'] < df['macd_signal']) &
                (df['volume_ratio'] > 1.2)
            )
            df.loc[buy_conditions, 'signal'] = 1
            df.loc[sell_conditions, 'signal'] = -1
            return df
        except Exception as e:
            print(f"❌ 신호 생성 오류: {e}")
            return None
    
    def get_ai_analysis(self):
        """AI 시장 분석"""
        try:
            # Perplexity로 최신 뉴스 수집
            news_prompt = "이더리움 ETH 최신 뉴스와 시장 동향을 간단히 알려줘"
            
            headers = {
                'Authorization': f'Bearer {self.perplexity_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'llama-3.1-sonar-small-128k-online',
                'messages': [{'role': 'user', 'content': news_prompt}],
                'max_tokens': 200
            }
            
            response = requests.post(
                'https://api.perplexity.ai/chat/completions',
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                news_analysis = response.json()['choices'][0]['message']['content']
                print(f"📰 AI 뉴스 분석: {news_analysis[:100]}...")
                return news_analysis
            else:
                print("❌ AI 뉴스 분석 실패")
                return None
                
        except Exception as e:
            print(f"❌ AI 분석 오류: {e}")
            return None
    
    def market_buy(self, amount_usdt):
        """시장가 매수"""
        try:
            # 이더리움 현재가 조회
            ticker = self.exchange.fetch_ticker(self.symbol)
            current_price = ticker['last']
            
            # 매수 가능한 이더리움 수량 계산
            eth_amount = amount_usdt / current_price
            
            print(f"🟢 매수 시도: ${amount_usdt:,.2f} → {eth_amount:.6f} ETH @ ${current_price:,.2f}")
            
            # 시장가 매수
            order = self.exchange.create_market_buy_order(
                symbol=self.symbol,
                amount=eth_amount
            )
            
            if order['status'] == 'closed':
                self.position = 'long'
                self.entry_price = current_price
                self.entry_time = datetime.now()
                
                # 로그 저장
                trade_info = {
                    'type': 'buy',
                    'time': self.entry_time.isoformat(),
                    'price': current_price,
                    'amount': eth_amount,
                    'value': amount_usdt
                }
                self.trading_log['trades'].append(trade_info)
                self.save_trading_log()
                
                print(f"✅ 매수 완료: {eth_amount:.6f} ETH @ ${current_price:,.2f}")
                return True
            else:
                print(f"❌ 매수 실패: {order}")
                return False
                
        except Exception as e:
            print(f"❌ 매수 오류: {e}")
            return False
    
    def market_sell(self, reason='signal'):
        """시장가 매도"""
        try:
            # 현재 잔액 조회
            balance = self.exchange.fetch_balance()
            eth_balance = balance['total'].get('ETH', 0)
            
            if eth_balance <= 0:
                print("❌ 매도할 이더리움이 없습니다.")
                return False
            
            # 현재가 조회
            ticker = self.exchange.fetch_ticker(self.symbol)
            current_price = ticker['last']
            
            print(f"🔴 매도 시도: {eth_balance:.6f} ETH @ ${current_price:,.2f}")
            
            # 시장가 매도
            order = self.exchange.create_market_sell_order(
                symbol=self.symbol,
                amount=eth_balance
            )
            
            if order['status'] == 'closed':
                # 수익률 계산
                if self.entry_price:
                    pnl_pct = (current_price - self.entry_price) / self.entry_price
                else:
                    pnl_pct = 0
                
                # 로그 저장
                trade_info = {
                    'type': 'sell',
                    'time': datetime.now().isoformat(),
                    'price': current_price,
                    'amount': eth_balance,
                    'reason': reason,
                    'pnl_pct': pnl_pct
                }
                self.trading_log['trades'].append(trade_info)
                self.save_trading_log()
                
                print(f"✅ 매도 완료: {eth_balance:.6f} ETH @ ${current_price:,.2f}")
                print(f"📊 수익률: {pnl_pct*100:.2f}%")
                
                # 포지션 초기화
                self.position = None
                self.entry_price = None
                self.entry_time = None
                
                return True
            else:
                print(f"❌ 매도 실패: {order}")
                return False
                
        except Exception as e:
            print(f"❌ 매도 오류: {e}")
            return False
    
    def monitor_position(self):
        """포지션 모니터링 (트레일링 스탑 포함)"""
        if not self.position or not self.entry_price:
            return
        try:
            ticker = self.exchange.fetch_ticker(self.symbol)
            current_price = ticker['last']
            pnl_pct = (current_price - self.entry_price) / self.entry_price
            # 트레일링 스탑 파라미터
            TRAILING_TRIGGER = 0.02  # 2% 이상 수익 발생 시 활성화
            TRAILING_STEP = 0.01     # 1% 단위로 손절선 추적
            # 트레일링 스탑 상태 저장
            if not hasattr(self, 'trailing_active'):
                self.trailing_active = False
                self.trailing_stop = None
            # 트레일링 스탑 활성화 조건
            if not self.trailing_active and pnl_pct > TRAILING_TRIGGER:
                self.trailing_active = True
                self.trailing_stop = current_price * (1 - TRAILING_STEP)
                print(f"🚨 트레일링 스탑 활성화! 손절선: {self.trailing_stop:.2f}")
            # 트레일링 스탑 추적
            if self.trailing_active:
                new_trailing_stop = current_price * (1 - TRAILING_STEP)
                if new_trailing_stop > self.trailing_stop:
                    self.trailing_stop = new_trailing_stop
                    print(f"🔄 트레일링 스탑 상향! 손절선: {self.trailing_stop:.2f}")
                # 트레일링 스탑 손절 조건
                if current_price <= self.trailing_stop:
                    print(f"🔴 트레일링 스탑 발동! 수익률: {pnl_pct*100:.2f}%")
                    self.market_sell('trailing_stop')
                    self.trailing_active = False
                    self.trailing_stop = None
                    return
            # 손절/익절
            if pnl_pct <= -self.stop_loss_pct:
                print(f"📉 손절 조건 충족: {pnl_pct*100:.2f}%")
                self.market_sell('stop_loss')
                self.trailing_active = False
                self.trailing_stop = None
            elif pnl_pct >= self.take_profit_pct:
                print(f"📈 익절 조건 충족: {pnl_pct*100:.2f}%")
                self.market_sell('take_profit')
                self.trailing_active = False
                self.trailing_stop = None
        except Exception as e:
            print(f"❌ 포지션 모니터링 오류: {e}")
    
    def run(self):
        """메인 실행 루프"""
        print("🚀 이더리움 매매봇 시작!")
        
        # 기존 보유 이더리움 처리 (매도만)
        balance = self.exchange.fetch_balance()
        eth_balance = balance['total'].get('ETH', 0)
        if eth_balance > 0.001:  # 최소 거래량 0.001 ETH 이상일 때만 매도
            print(f"🪙 기존 보유 ETH 발견: {eth_balance:.6f}")
            print("🔄 보유 ETH를 매도하고 V2 조건 확인 후 재매수...")
            
            # 기존 이더리움 전량 매도
            ticker = self.exchange.fetch_ticker(self.symbol)
            current_price = ticker['last']
            print(f"🔴 기존 ETH 매도: {eth_balance:.6f} ETH @ ${current_price:,.2f}")
            
            # 시장가 매도
            sell_order = self.exchange.create_market_sell_order(self.symbol, eth_balance)
            if sell_order['status'] == 'closed':
                usdt_earned = sell_order['cost']
                print(f"✅ 매도 완료: ${usdt_earned:,.2f} USDT 획득")
                print(f"⏳ V2 조건 확인 후 재매수 대기 중...")
            else:
                print("❌ 기존 ETH 매도 실패")
        elif eth_balance > 0:
            print(f"🪙 보유 ETH: {eth_balance:.6f} (최소 거래량 미만 - 매도 안함)")
        else:
            print("🪙 보유 ETH 없음 - 새로운 거래 시작")
        
        while True:
            try:
                print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 50)
                
                # 1. 시장 데이터 수집
                df = self.get_market_data()
                if df is None:
                    continue
                
                # 2. 기술적 지표 계산
                df = self.calculate_indicators(df)
                if df is None:
                    continue
                
                # 3. 매매 신호 생성
                df = self.generate_signals(df)
                if df is None:
                    continue
                
                # 4. 현재 신호 확인
                current_signal = df['signal'].iloc[-1]
                current_price = df['close'].iloc[-1]
                
                print(f"💰 현재가: ${current_price:,.2f}")
                print(f"📊 RSI: {df['rsi'].iloc[-1]:.1f}")
                print(f"📈 MACD: {df['macd'].iloc[-1]:.2f}")
                print(f"📉 신호: {current_signal}")
                
                # 보유 이더리움 정보 표시
                balance = self.exchange.fetch_balance()
                eth_balance = balance['total'].get('ETH', 0)
                if eth_balance > 0:
                    if self.entry_price:
                        pnl_pct = (current_price - self.entry_price) / self.entry_price
                        print(f"🪙 보유 ETH: {eth_balance:.6f} | 📊 수익률: {pnl_pct*100:.2f}%")
                    else:
                        print(f"🪙 보유 ETH: {eth_balance:.6f} | 📊 진입가: 자동 설정 중...")
                else:
                    print("🪙 보유 ETH: 없음")
                
                # 5. 포지션 모니터링
                self.monitor_position()
                
                # 6. 매매 로직
                # 현재 보유량 확인
                balance = self.exchange.fetch_balance()
                eth_balance = balance['total'].get('ETH', 0)
                
                if eth_balance < 0.001:  # 0.001 ETH 미만이면 매수 가능
                    if current_signal == 1:  # 매수 신호
                        print("🟢 매수 신호 감지!")
                        
                        # AI 분석 (선택적)
                        ai_analysis = self.get_ai_analysis()
                        
                        # 매수 실행 (전체 잔액의 90% 사용)
                        usdt_balance = balance['total'].get('USDT', 0)
                        buy_amount = usdt_balance * 0.9
                        
                        if buy_amount > 10:  # 최소 $10
                            self.market_buy(buy_amount)
                        else:
                            print("❌ 매수 자금 부족")
                
                elif self.position == 'long':  # 롱 포지션
                    if current_signal == -1:  # 매도 신호
                        print("🔴 매도 신호 감지!")
                        self.market_sell('signal')
                
                # 7. 대기
                print("⏳ 1분 대기 중...")
                time.sleep(60)  # 1분
                
            except KeyboardInterrupt:
                print("\n🛑 사용자에 의해 중단됨")
                break
            except Exception as e:
                print(f"❌ 실행 오류: {e}")
                time.sleep(60)  # 1분 대기

if __name__ == "__main__":
    bot = ETHTradingBot()
    bot.run() 