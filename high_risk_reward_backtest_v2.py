import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

class HighRiskRewardBacktestV2:
    def __init__(self, data_file, initial_balance=10000):
        self.data_file = data_file
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.position = None
        self.entry_price = None
        self.entry_time = None
        self.trades = []
        self.equity_curve = []
        
        # 손익비 설정 (1:3으로 조정, 익절 낮게)
        self.risk_reward_ratio = 3  # 1:3 손익비
        self.stop_loss_pct = 0.04    # 4% 손절 (넓게)
        self.take_profit_pct = 0.06  # 6% 익절 (낮게)
        
        # 지표 설정
        self.rsi_period = 14
        self.rsi_oversold = 25  # 더 엄격한 과매도
        self.rsi_overbought = 75
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.bb_period = 20
        self.bb_std = 2
        
    def load_data(self):
        """데이터 로드"""
        print(f"📊 {self.data_file} 데이터 로드 중...")
        df = pd.read_csv(self.data_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        return df
    
    def calculate_indicators(self, df):
        """기술적 지표 계산"""
        print("🧮 기술적 지표 계산 중...")
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=self.macd_fast).mean()
        exp2 = df['close'].ewm(span=self.macd_slow).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=self.macd_signal).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=self.bb_period).mean()
        bb_std = df['close'].rolling(window=self.bb_period).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * self.bb_std)
        df['bb_lower'] = df['bb_middle'] - (bb_std * self.bb_std)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # 추가 지표들
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()
        
        # 거래량가중이동평균선 (VWMA)
        def volume_weighted_moving_average(price, volume, window):
            return (price * volume).rolling(window=window).sum() / volume.rolling(window=window).sum()
        
        df['vwma_20'] = volume_weighted_moving_average(df['close'], df['volume'], 20)
        df['vwma_50'] = volume_weighted_moving_average(df['close'], df['volume'], 50)
        
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # 추가 지표: Stochastic RSI
        df['stoch_rsi'] = (df['rsi'] - df['rsi'].rolling(14).min()) / (df['rsi'].rolling(14).max() - df['rsi'].rolling(14).min())
        
        # 추가 지표: ATR (Average True Range)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        return df
    
    def generate_signals(self, df):
        """매매 신호 생성 (더 엄격한 조건)"""
        print("📈 매매 신호 생성 중...")
        
        df['signal'] = 0  # 0: 홀드, 1: 매수, -1: 매도
        
        for i in range(200, len(df)):  # 200개 데이터 후부터 시작 (더 안정적인 지표)
            current = df.iloc[i]
            prev = df.iloc[i-1]
            prev2 = df.iloc[i-2]
            
            # 매수 조건 (거래량가중이동평균선 활용, 완화)
            buy_conditions = (
                current['rsi'] < 40 and  # RSI 중간 이하
                current['close'] < current['bb_lower'] * 1.02 and  # 볼린저 하단 근처
                current['macd'] > current['macd_signal'] and  # MACD 상승
                current['volume_ratio'] > 1.2 and  # 거래량 증가
                current['close'] > current['vwma_20'] * 0.98  # 거래량가중이동평균선 근처
            )
            
            # 매도 조건 (강력한 하락 신호)
            sell_conditions = (
                current['rsi'] > self.rsi_overbought or  # RSI 과매수
                current['close'] > current['bb_upper'] or  # 볼린저 상단 터치
                current['macd'] < current['macd_signal'] or  # MACD 하락
                current['close'] < current['sma_20'] * 0.97  # 단기 이평선 하향 돌파
            )
            
            if buy_conditions:
                df.iloc[i, df.columns.get_loc('signal')] = 1
            elif sell_conditions:
                df.iloc[i, df.columns.get_loc('signal')] = -1
        
        return df
    
    def execute_backtest(self, df):
        """백테스트 실행"""
        print("🚀 백테스트 실행 중...")
        
        for i in range(len(df)):
            current = df.iloc[i]
            
            # 포지션이 없을 때 매수 신호
            if self.position is None and current['signal'] == 1:
                self.entry_price = current['close']
                self.entry_time = current.name
                self.position = 'long'
                self.stop_loss = self.entry_price * (1 - self.stop_loss_pct)
                self.take_profit = self.entry_price * (1 + self.take_profit_pct)
                
                print(f"🟢 매수: {current.name} - 가격: {self.entry_price:.2f}")
                print(f"   손절: {self.stop_loss:.2f} | 익절: {self.take_profit:.2f}")
            
            # 포지션이 있을 때
            elif self.position == 'long':
                current_price = current['close']
                pnl_pct = (current_price - self.entry_price) / self.entry_price
                
                # 손절 조건
                if current_price <= self.stop_loss:
                    self.close_position(current_price, current.name, 'stop_loss', pnl_pct)
                
                # 익절 조건
                elif current_price >= self.take_profit:
                    self.close_position(current_price, current.name, 'take_profit', pnl_pct)
                
                # 매도 신호 (더 엄격하게)
                elif current['signal'] == -1 and pnl_pct > 0.02:  # 2% 이상 수익일 때만 신호 매도
                    self.close_position(current_price, current.name, 'signal', pnl_pct)
            
            # 자산 곡선 업데이트
            self.update_equity_curve(current.name, current['close'])
    
    def close_position(self, exit_price, exit_time, reason, pnl_pct):
        """포지션 종료"""
        trade = {
            'entry_time': self.entry_time,
            'exit_time': exit_time,
            'entry_price': self.entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'pnl_usd': self.balance * pnl_pct,
            'reason': reason
        }
        
        self.trades.append(trade)
        self.balance *= (1 + pnl_pct)
        
        print(f"🔴 매도: {exit_time} - 가격: {exit_price:.2f}")
        print(f"   수익률: {pnl_pct*100:.2f}% | 잔액: {self.balance:.2f}")
        print(f"   종료 사유: {reason}")
        
        self.position = None
        self.entry_price = None
        self.entry_time = None
    
    def update_equity_curve(self, timestamp, price):
        """자산 곡선 업데이트"""
        if self.position == 'long':
            current_value = self.balance * (price / self.entry_price)
        else:
            current_value = self.balance
        
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': current_value
        })
    
    def analyze_results(self):
        """결과 분석"""
        print("\n" + "="*50)
        print("📊 고위험-고수익 백테스트 V2 결과 분석")
        print("="*50)
        
        if not self.trades:
            print("❌ 거래 내역이 없습니다.")
            return
        
        # 기본 통계
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t['pnl_pct'] > 0])
        losing_trades = len([t for t in self.trades if t['pnl_pct'] <= 0])
        
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        
        # 수익률 통계
        total_return = (self.balance - self.initial_balance) / self.initial_balance * 100
        avg_win = np.mean([t['pnl_pct'] for t in self.trades if t['pnl_pct'] > 0]) * 100
        avg_loss = np.mean([t['pnl_pct'] for t in self.trades if t['pnl_pct'] <= 0]) * 100
        
        # 손익비
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        
        # 큰 수익 거래 분석
        big_wins = [t for t in self.trades if t['pnl_pct'] >= 0.05]  # 5% 이상
        big_losses = [t for t in self.trades if t['pnl_pct'] <= -0.02]  # -2% 이하
        
        print(f"💰 초기 자본: ${self.initial_balance:,.2f}")
        print(f"💰 최종 자본: ${self.balance:,.2f}")
        print(f"📈 총 수익률: {total_return:.2f}%")
        print(f"📊 총 거래 수: {total_trades}")
        print(f"✅ 승률: {win_rate:.1f}% ({winning_trades}/{total_trades})")
        print(f"📈 평균 수익: {avg_win:.2f}%")
        print(f"📉 평균 손실: {avg_loss:.2f}%")
        print(f"⚖️ 손익비: 1:{profit_factor:.2f}")
        print(f"🎯 큰 수익 거래: {len(big_wins)}개")
        print(f"💥 큰 손실 거래: {len(big_losses)}개")
        
        # 거래 내역
        print(f"\n📋 거래 내역:")
        for i, trade in enumerate(self.trades, 1):
            pnl_color = "🟢" if trade['pnl_pct'] > 0 else "🔴"
            print(f"  {i}. {pnl_color} {trade['entry_time'].strftime('%Y-%m-%d %H:%M')} → "
                  f"{trade['exit_time'].strftime('%Y-%m-%d %H:%M')} | "
                  f"{trade['pnl_pct']*100:.2f}% | {trade['reason']}")
    
    def plot_results(self):
        """결과 시각화"""
        if not self.equity_curve:
            print("❌ 자산 곡선 데이터가 없습니다.")
            return
        
        df_equity = pd.DataFrame(self.equity_curve)
        df_equity.set_index('timestamp', inplace=True)
        
        plt.figure(figsize=(15, 12))
        
        # 자산 곡선
        plt.subplot(3, 1, 1)
        plt.plot(df_equity.index, df_equity['equity'], label='Portfolio Value', linewidth=2, color='blue')
        plt.axhline(y=self.initial_balance, color='r', linestyle='--', alpha=0.7, label='Initial Balance')
        plt.title('High Risk-Reward Strategy V2 Backtest Results', fontsize=14, fontweight='bold')
        plt.ylabel('Portfolio Value ($)', fontsize=12)
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 수익률 분포
        plt.subplot(3, 1, 2)
        if self.trades:
            pnl_pcts = [t['pnl_pct'] * 100 for t in self.trades]
            plt.hist(pnl_pcts, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
            plt.axvline(x=0, color='red', linestyle='--', alpha=0.7, label='Break-even')
            plt.axvline(x=12, color='green', linestyle='--', alpha=0.7, label='Target (12%)')
            plt.title('Trade P&L Distribution', fontsize=12)
            plt.xlabel('P&L (%)', fontsize=10)
            plt.ylabel('Frequency', fontsize=10)
            plt.legend()
            plt.grid(True, alpha=0.3)
        
        # 거래별 수익률
        plt.subplot(3, 1, 3)
        if self.trades:
            trade_numbers = range(1, len(self.trades) + 1)
            pnl_pcts = [t['pnl_pct'] * 100 for t in self.trades]
            colors = ['green' if p > 0 else 'red' for p in pnl_pcts]
            plt.bar(trade_numbers, pnl_pcts, color=colors, alpha=0.7)
            plt.axhline(y=0, color='black', linestyle='-', alpha=0.5)
            plt.axhline(y=12, color='green', linestyle='--', alpha=0.7, label='Target (12%)')
            plt.title('Individual Trade P&L', fontsize=12)
            plt.xlabel('Trade Number', fontsize=10)
            plt.ylabel('P&L (%)', fontsize=10)
            plt.legend()
            plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('high_risk_reward_backtest_v2_results.png', dpi=300, bbox_inches='tight')
        plt.show()
    
    def run(self):
        """전체 백테스트 실행"""
        print("🚀 고위험-고수익 백테스트 V2 시작!")
        print(f"📁 데이터 파일: {self.data_file}")
        print(f"💰 초기 자본: ${self.initial_balance:,.2f}")
        print(f"⚖️ 손익비 설정: 1:{self.risk_reward_ratio}")
        print(f"📉 손절: {self.stop_loss_pct*100}% | 📈 익절: {self.take_profit_pct*100}%")
        print("-" * 50)
        
        # 데이터 로드 및 처리
        df = self.load_data()
        df = self.calculate_indicators(df)
        df = self.generate_signals(df)
        
        # 백테스트 실행
        self.execute_backtest(df)
        
        # 결과 분석
        self.analyze_results()
        self.plot_results()

if __name__ == "__main__":
    # 1분봉 데이터 사용
    data_file = "data/collected/XRPUSDT_1m.csv"
    
    print("🚀 고위험-고수익 백테스트 V2 시작!")
    print(f"📁 데이터 파일: {data_file}")
    print(f"💰 초기 자본: $10,000.00")
    print(f"⚖️ 손익비 설정: 1:3")
    print(f"📉 손절: 4.0% | 📈 익절: 6.0%")
    print("-" * 50)
    
    backtest = HighRiskRewardBacktestV2(data_file)
    backtest.run() 