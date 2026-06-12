# Binary Trading Signal Bot

একটি স্বয়ংক্রিয় বাইনারি ট্রেডিং সিগন্যাল জেনারেটর যা Magnus Pro স্টাইলের টেকনিক্যাল বিশ্লেষণ ব্যবহার করে।

## বৈশিষ্ট্য

✅ **প্রতি 5 মিনিটে স্বয়ংক্রিয় বিশ্লেষণ**  
✅ **Magnus Pro স্টাইল ইন্ডিকেটর:**
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands

✅ **টেলিগ্রামে সিগন্যাল পাঠায়**  
✅ **মাল্টিপল কারেন্সি পেয়ার ট্র্যাক করে**  
✅ **Confidence স্কোর প্রদান করে**

## সেটআপ

### 1. Telegram Bot তৈরি করুন

```bash
# BotFather এর সাথে কথা বলুন (@BotFather)
/newbot
# নাম এবং ইউজারনেম দিন
# টোকেন পাবেন
```

### 2. Chat ID পান

```bash
# Bot এ /start পাঠান
# এই URL এ যান: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
# চ্যাটে কোনো মেসেজ পাঠান
# আবার getUpdates করুন - chat.id দেখবেন
```

### 3. GitHub Secrets সেট করুন

আপনার রিপোজিটরিতে যান → Settings → Secrets and variables → Actions

নিম্নলিখিত Secrets যোগ করুন:

```
TELEGRAM_BOT_TOKEN = আপনার বট টোকেন
TELEGRAM_CHAT_ID = আপনার চ্যাট আইডি
TWELVEDATA_API_KEY = আপনার API কী (অপশনাল)
```

### 4. ওয়ার্কফ্লো সক্রিয় করুন

GitHub Actions ট্যাবে যান এবং "Binary Trading Signal Generator" ওয়ার্কফ্লো সক্রিয় করুন।

## ট্রেডিং লজিক

### Signal Generation

**BUY Signal:**
- RSI < 30 (Oversold)
- MACD Histogram থেকে পজিটিভে যাওয়া
- প্রাইস Bollinger Bands এর নিচে

**SELL Signal:**
- RSI > 70 (Overbought)
- MACD Histogram থেকে নেগেটিভে যাওয়া
- প্রাইস Bollinger Bands এর উপরে

**HOLD Signal:**
- কোনো স্পষ্ট সিগন্যাল নেই

### Confidence Score

- প্রতিটি ইন্ডিকেটর সাফল্যের জন্য 25% যোগ করে
- সর্বোচ্চ 100%, সর্বনিম্ন 0%
- শুধুমাত্র 50%+ confidence এর সিগন্যাল পাঠানো হয়

## ট্র্যাক করা সিম্বলস

- EURUSD=X - EUR/USD
- GBPUSD=X - GBP/USD
- USDJPY=X - USD/JPY
- BTC-USD - Bitcoin
- ETH-USD - Ethereum

আপনি `trading/signal_generator.py` এ SYMBOLS তালিকা সম্পাদনা করতে পারেন।

## ওয়ার্কফ্লো রান

### স্বয়ংক্রিয়
প্রতি 5 মিনিটে স্বয়ংক্রিয়ভাবে চলে

### ম্যানুয়াল
GitHub Actions ট্যাবে "Binary Trading Signal Generator" → "Run workflow"

## Telegram বার্তা উদাহরণ

```
🤖 Trading Signals - 2026-06-12 14:30:00
========================================

🟢 BUY SIGNALS:
  • EURUSD=X
    Price: 1.0856
    Confidence: 75%
    RSI: 28.5

🔴 SELL SIGNALS:
  • BTC-USD
    Price: 42500.50
    Confidence: 80%
    RSI: 72.3

⚪ HOLD:
  • GBPUSD=X (Confidence: 40%)
```

## ট্রাবলশুটিং

### কোনো সিগন্যাল পাঠানো হচ্ছে না
1. GitHub Actions Workflow সক্ষম আছে কি চেক করুন
2. Secrets সঠিকভাবে সেট আছে কি যাচাই করুন
3. Workflow Runs লগ চেক করুন

### Telegram সংযোগ ত্রুটি
1. Bot টোকেন সঠিক কি যাচাই করুন
2. Chat ID সঠিক কি যাচাই করুন
3. Bot কে আপনার চ্যাটে যোগ করেছেন কি নিশ্চিত করুন

### No data fetched সতর্কতা
- yfinance অস্থায়ী ডাউনটাইম থাকতে পারে
- বাজার বন্ধ সময়ে ডেটা উপলব্ধ নাও হতে পারে

## কাস্টমাইজেশন

### ইন্ডিকেটর প্যারামিটার পরিবর্তন

`signal_generator.py` এর MAGNUS_CONFIG অনুভাগ সম্পাদনা করুন:

```python
MAGNUS_CONFIG = {
    'rsi_period': 14,        # RSI সময়কাল
    'rsi_overbought': 70,    # Overbought লেভেল
    'rsi_oversold': 30,      # Oversold লেভেল
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'bb_period': 20,         # Bollinger Bands সময়কাল
    'bb_std_dev': 2,
}
```

### Confidence Threshold পরিবর্তন

`main()` ফাংশনে `confidence >= 50` লাইন সম্পাদনা করুন।

## নিরাপত্তা

⚠️ **গুরুত্বপূর্ণ:**
- কখনও আপনার API কী বা টোকেন commit করবেন না
- সর্বদা GitHub Secrets ব্যবহার করুন
- `.env` ফাইল গিটইগনোর করুন

## লাইসেন্স

MIT

## সহায়তা

সমস্যা সম্মুখীন হলে Issues খুলুন বা আমার সাথে যোগাযোগ করুন।