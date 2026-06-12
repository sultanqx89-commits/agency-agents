import os
import sys
import json
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple

import yfinance as yf
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TWELVEDATA_API_KEY = os.getenv('TWELVEDATA_API_KEY')

# Trading symbols to monitor
SYMBOLS = [
    'EURUSD=X',  # EUR/USD
    'GBPUSD=X',  # GBP/USD
    'USDJPY=X',  # USD/JPY
    'BTC-USD',   # Bitcoin
    'ETH-USD',   # Ethereum
]

# Binary Options Configuration (5 minutes)
BINARY_OPTIONS_CONFIG = {
    'expiration_time_minutes': 5,  # 5 minute binary options
    'buffer_seconds': 10,          # Buffer for order placement
}

# Magnus Pro style configuration
MAGNUS_CONFIG = {
    'rsi_period': 14,
    'rsi_overbought': 70,
    'rsi_oversold': 30,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'bb_period': 20,
    'bb_std_dev': 2,
}


class BinaryOptionsTimer:
    """Calculate Entry and Expiration times for binary options"""
    
    @staticmethod
    def get_current_candle_time() -> Tuple[datetime, datetime]:
        """Get current 5-minute candle start and end time"""
        now = datetime.now()
        
        # Get the start of current 5-minute candle
        minute = now.minute
        candle_minute = (minute // 5) * 5
        candle_start = now.replace(minute=candle_minute, second=0, microsecond=0)
        
        # Calculate candle end
        candle_end = candle_start + timedelta(minutes=5)
        
        return candle_start, candle_end
    
    @staticmethod
    def calculate_entry_expire_times() -> Dict:
        """Calculate Entry and Expiration times"""
        now = datetime.now()
        candle_start, candle_end = BinaryOptionsTimer.get_current_candle_time()
        
        # Entry time is the signal generation time
        entry_time = now
        
        # For 5-minute binary options
        expiration_time = candle_end + timedelta(
            seconds=BINARY_OPTIONS_CONFIG['buffer_seconds']
        )
        
        # Calculate duration
        duration = (expiration_time - entry_time).total_seconds()
        
        return {
            'entry_time': entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            'entry_time_unix': int(entry_time.timestamp()),
            'expiration_time': expiration_time.strftime('%Y-%m-%d %H:%M:%S'),
            'expiration_time_unix': int(expiration_time.timestamp()),
            'duration_seconds': int(duration),
            'duration_minutes': round(duration / 60, 1),
            'candle_start': candle_start.strftime('%Y-%m-%d %H:%M:%S'),
            'candle_end': candle_end.strftime('%Y-%m-%d %H:%M:%S'),
        }


class MagnusProAnalyzer:
    """Magnus Pro style technical analysis"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.data = None
        
    def fetch_data(self, period: str = '1d', interval: str = '5m') -> bool:
        """Fetch market data using yfinance"""
        try:
            self.data = yf.download(
                self.symbol,
                period=period,
                interval=interval,
                progress=False
            )
            
            if self.data.empty:
                logger.warning(f"No data fetched for {self.symbol}")
                return False
                
            logger.info(f"Fetched {len(self.data)} candles for {self.symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error fetching data for {self.symbol}: {str(e)}")
            return False
    
    def calculate_rsi(self, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        if self.data is None or len(self.data) < period + 1:
            return None
            
        delta = self.data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if self.data is None or len(self.data) < slow + signal:
            return None, None, None
            
        ema_fast = self.data['Close'].ewm(span=fast).mean()
        ema_slow = self.data['Close'].ewm(span=slow).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def calculate_bollinger_bands(self, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        if self.data is None or len(self.data) < period:
            return None, None, None
            
        sma = self.data['Close'].rolling(window=period).mean()
        std = self.data['Close'].rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return upper_band, sma, lower_band
    
    def generate_signal(self) -> Dict:
        """Generate trading signal using Magnus Pro logic"""
        if not self.fetch_data():
            return {'symbol': self.symbol, 'signal': 'NO_DATA', 'confidence': 0}
        
        # Get current price
        current_price = self.data['Close'].iloc[-1]
        
        # Calculate indicators
        rsi = self.calculate_rsi(MAGNUS_CONFIG['rsi_period'])
        macd_line, signal_line, histogram = self.calculate_macd(
            MAGNUS_CONFIG['macd_fast'],
            MAGNUS_CONFIG['macd_slow'],
            MAGNUS_CONFIG['macd_signal']
        )
        upper_band, middle_band, lower_band = self.calculate_bollinger_bands(
            MAGNUS_CONFIG['bb_period'],
            MAGNUS_CONFIG['bb_std_dev']
        )
        
        # Get current values
        current_rsi = rsi.iloc[-1] if rsi is not None else None
        current_macd = macd_line.iloc[-1] if macd_line is not None else None
        current_signal = signal_line.iloc[-1] if signal_line is not None else None
        current_histogram = histogram.iloc[-1] if histogram is not None else None
        current_upper = upper_band.iloc[-1] if upper_band is not None else None
        current_lower = lower_band.iloc[-1] if lower_band is not None else None
        
        # Magnus Pro Signal Logic
        signals = []
        confidence = 0
        
        # RSI signals
        if current_rsi is not None:
            if current_rsi < MAGNUS_CONFIG['rsi_oversold']:
                signals.append('BUY_RSI')
                confidence += 25
            elif current_rsi > MAGNUS_CONFIG['rsi_overbought']:
                signals.append('SELL_RSI')
                confidence += 25
        
        # MACD signals
        if current_histogram is not None and len(histogram) > 1:
            prev_histogram = histogram.iloc[-2]
            if prev_histogram < 0 and current_histogram > 0:
                signals.append('BUY_MACD')
                confidence += 25
            elif prev_histogram > 0 and current_histogram < 0:
                signals.append('SELL_MACD')
                confidence += 25
        
        # Bollinger Bands signals
        if current_lower is not None and current_upper is not None:
            if current_price < current_lower:
                signals.append('BUY_BB')
                confidence += 25
            elif current_price > current_upper:
                signals.append('SELL_BB')
                confidence += 25
        
        # Determine final signal
        buy_signals = len([s for s in signals if 'BUY' in s])
        sell_signals = len([s for s in signals if 'SELL' in s])
        
        if buy_signals > sell_signals:
            final_signal = 'BUY'
        elif sell_signals > buy_signals:
            final_signal = 'SELL'
        else:
            final_signal = 'HOLD'
        
        # Get binary options timing
        timing = BinaryOptionsTimer.calculate_entry_expire_times()
        
        return {
            'symbol': self.symbol,
            'price': round(current_price, 4),
            'signal': final_signal,
            'confidence': min(confidence, 100),
            'rsi': round(current_rsi, 2) if current_rsi is not None else None,
            'macd': round(current_macd, 4) if current_macd is not None else None,
            'signals': signals,
            'timestamp': datetime.now().isoformat(),
            'entry_time': timing['entry_time'],
            'entry_time_unix': timing['entry_time_unix'],
            'expiration_time': timing['expiration_time'],
            'expiration_time_unix': timing['expiration_time_unix'],
            'duration_seconds': timing['duration_seconds'],
            'duration_minutes': timing['duration_minutes'],
            'candle_start': timing['candle_start'],
            'candle_end': timing['candle_end'],
        }


async def send_telegram_message(message: str) -> bool:
    """Send message to Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram credentials not configured")
        return False
    
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode='HTML'
        )
        logger.info("Message sent to Telegram successfully")
        return True
    except TelegramError as e:
        logger.error(f"Telegram error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error sending Telegram message: {str(e)}")
        return False


def format_signal_message(analysis_results: List[Dict]) -> str:
    """Format analysis results for Telegram with Entry and Expiration times"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    message = f"<b>🤖 Binary Trading Signals - {timestamp}</b>\n"
    message += "=" * 50 + "\n\n"
    
    buy_signals = [r for r in analysis_results if r['signal'] == 'BUY']
    sell_signals = [r for r in analysis_results if r['signal'] == 'SELL']
    hold_signals = [r for r in analysis_results if r['signal'] == 'HOLD']
    
    if buy_signals:
        message += "<b>🟢 BUY SIGNALS (CALL):</b>\n"
        message += "-" * 50 + "\n"
        for signal in buy_signals:
            message += f"<b>📊 {signal['symbol']}</b>\n"
            message += f"  💰 Price: {signal['price']}\n"
            message += f"  📈 RSI: {signal['rsi']}\n"
            message += f"  🎯 Confidence: {signal['confidence']}%\n"
            message += f"  ⏰ Entry Time: <code>{signal['entry_time']}</code>\n"
            message += f"  ⏱️  Expire Time: <code>{signal['expiration_time']}</code>\n"
            message += f"  ⌛ Duration: <b>{signal['duration_minutes']} min</b>\n"
            message += f"  📍 Candle: {signal['candle_start']} → {signal['candle_end']}\n\n"
    
    if sell_signals:
        message += "<b>🔴 SELL SIGNALS (PUT):</b>\n"
        message += "-" * 50 + "\n"
        for signal in sell_signals:
            message += f"<b>📊 {signal['symbol']}</b>\n"
            message += f"  💰 Price: {signal['price']}\n"
            message += f"  📉 RSI: {signal['rsi']}\n"
            message += f"  🎯 Confidence: {signal['confidence']}%\n"
            message += f"  ⏰ Entry Time: <code>{signal['entry_time']}</code>\n"
            message += f"  ⏱️  Expire Time: <code>{signal['expiration_time']}</code>\n"
            message += f"  ⌛ Duration: <b>{signal['duration_minutes']} min</b>\n"
            message += f"  📍 Candle: {signal['candle_start']} → {signal['candle_end']}\n\n"
    
    if hold_signals:
        message += "<b>⚪ HOLD:</b>\n"
        message += "-" * 50 + "\n"
        for signal in hold_signals:
            message += f"  • {signal['symbol']} (Confidence: {signal['confidence']}%)\n"
    
    message += "\n<i>⚠️ This is for educational purposes only. Trade at your own risk.</i>\n"
    
    return message


async def main():
    """Main execution"""
    logger.info("Starting trading signal generation with binary options timing...")
    
    try:
        results = []
        
        for symbol in SYMBOLS:
            logger.info(f"Analyzing {symbol}...")
            analyzer = MagnusProAnalyzer(symbol)
            signal = analyzer.generate_signal()
            results.append(signal)
            logger.info(f"{symbol}: {signal['signal']} (Confidence: {signal['confidence']}%)")
            logger.info(f"Entry: {signal['entry_time']} → Expire: {signal['expiration_time']}")
        
        # Filter strong signals only
        strong_signals = [r for r in results if r['confidence'] >= 50 and r['signal'] != 'HOLD']
        
        if strong_signals:
            message = format_signal_message(strong_signals)
            await send_telegram_message(message)
            logger.info(f"Sent {len(strong_signals)} strong signals to Telegram")
        else:
            logger.info("No strong signals generated")
        
        # Save results to file
        with open('trading/results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info("Trading signal generation completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        error_message = f"<b>⚠️ Trading Bot Error</b>\n<code>{str(e)}</code>"
        await send_telegram_message(error_message)
        return False


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
