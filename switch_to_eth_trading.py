#!/usr/bin/env python3
"""
비트코인을 팔고 이더리움으로 전환하는 스크립트
"""

import ccxt
import os
from dotenv import load_dotenv
import time
from datetime import datetime

# 환경변수 로드
load_dotenv()

def get_exchange():
    """Binance 거래소 설정"""
    return ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_API_SECRET'),
        'sandbox': False,
        'enableRateLimit': True
    })

def get_balance(exchange, symbol):
    """잔액 조회"""
    try:
        balance = exchange.fetch_balance()
        if symbol in balance['total']:
            return balance['total'][symbol]
        return 0
    except Exception as e:
        print(f"❌ 잔액 조회 오류: {e}")
        return 0

def market_sell_all(exchange, symbol):
    """전량 시장가 매도"""
    try:
        balance = get_balance(exchange, symbol)
        if balance <= 0:
            print(f"💰 {symbol} 잔액이 없습니다.")
            return False
        
        print(f"💰 {symbol} 잔액: {balance}")
        
        # 시장가 매도
        order = exchange.create_market_sell_order(
            symbol=f"{symbol}/USDT",
            amount=balance
        )
        
        print(f"✅ {symbol} 전량 매도 완료!")
        print(f"📊 주문 정보: {order}")
        return True
        
    except Exception as e:
        print(f"❌ {symbol} 매도 오류: {e}")
        return False

def market_buy_eth(exchange, usdt_amount):
    """USDT로 이더리움 시장가 매수"""
    try:
        # 이더리움 현재가 조회
        ticker = exchange.fetch_ticker('ETH/USDT')
        current_price = ticker['last']
        
        # 매수 가능한 이더리움 수량 계산
        eth_amount = usdt_amount / current_price
        
        print(f"💰 현재 이더리움 가격: ${current_price:,.2f}")
        print(f"💵 사용할 USDT: ${usdt_amount:,.2f}")
        print(f"🪙 매수할 이더리움: {eth_amount:.6f} ETH")
        
        # 시장가 매수
        order = exchange.create_market_buy_order(
            symbol='ETH/USDT',
            amount=eth_amount
        )
        
        print(f"✅ 이더리움 매수 완료!")
        print(f"📊 주문 정보: {order}")
        return True
        
    except Exception as e:
        print(f"❌ 이더리움 매수 오류: {e}")
        return False

def main():
    """메인 실행 함수"""
    print("🚀 비트코인 → 이더리움 전환 시작!")
    print("=" * 50)
    
    # 거래소 설정
    exchange = get_exchange()
    
    # 1. 비트코인 잔액 확인
    print("📊 잔액 확인 중...")
    btc_balance = get_balance(exchange, 'BTC')
    usdt_balance = get_balance(exchange, 'USDT')
    
    print(f"💰 BTC 잔액: {btc_balance}")
    print(f"💰 USDT 잔액: {usdt_balance}")
    
    if btc_balance <= 0:
        print("❌ 비트코인 잔액이 없습니다.")
        return
    
    # 2. 비트코인 전량 매도
    print("\n🔄 비트코인 매도 중...")
    if market_sell_all(exchange, 'BTC'):
        print("✅ 비트코인 매도 성공!")
        
        # 잠시 대기 (주문 처리 시간)
        print("⏳ 주문 처리 대기 중...")
        time.sleep(5)
        
        # 3. 새로운 USDT 잔액 확인
        new_usdt_balance = get_balance(exchange, 'USDT')
        print(f"💰 새로운 USDT 잔액: {new_usdt_balance}")
        
        # 4. 이더리움 매수
        print("\n🔄 이더리움 매수 중...")
        if market_buy_eth(exchange, new_usdt_balance):
            print("✅ 이더리움 매수 성공!")
            
            # 5. 최종 잔액 확인
            print("\n📊 최종 잔액 확인...")
            final_eth_balance = get_balance(exchange, 'ETH')
            final_usdt_balance = get_balance(exchange, 'USDT')
            
            print(f"💰 최종 ETH 잔액: {final_eth_balance}")
            print(f"💰 최종 USDT 잔액: {final_usdt_balance}")
            
            print("\n🎉 전환 완료!")
        else:
            print("❌ 이더리움 매수 실패!")
    else:
        print("❌ 비트코인 매도 실패!")

if __name__ == "__main__":
    main() 