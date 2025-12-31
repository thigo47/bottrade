import streamlit as st
import asyncio
import time
import random  # For fallback simulation if API fails
import aiohttp
from threading import Thread
import pandas as pd
import logging

# Configure logging for robustness
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
USDC_DECIMALS = 6
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/solana"
JUPITER_QUOTE_API = "https://quote-api.jup.ag/v6/quote"

# Initialize session state variables
if 'balance' not in st.session_state:
    st.session_state.balance = 1000.0  # Initial fictional USDC balance

if 'tokens' not in st.session_state:
    st.session_state.tokens = {}  # Dict of tokens: {'token_address': {'position': 0.0, 'buy_price': None, 'last_price': 0.0, 'symbol': 'UNKNOWN', 'decimals': 9}}

if 'history' not in st.session_state:
    st.session_state.history = []  # List of trade dicts

if 'pnl' not in st.session_state:
    st.session_state.pnl = 0.0  # Accumulated Profit and Loss

if 'running' not in st.session_state:
    st.session_state.running = False

# Asynchronous function to fetch prices from DexScreener
async def fetch_token_prices(token_addresses):
    if not token_addresses:
        return {}
    
    url = f"{DEXSCREENER_API}/{','.join(token_addresses)}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    prices = {}
                    for pair in data.get('pairs', []):
                        token_addr = pair['baseToken']['address']
                        symbol = pair['baseToken']['symbol']
                        price = float(pair.get('priceUsd', 0))
                        decimals = int(pair['baseToken'].get('decimals', 9))
                        if price > 0:
                            prices[token_addr] = {'price': price, 'symbol': symbol, 'decimals': decimals}
                    return prices
                else:
                    logger.error(f"DexScreener API error: {response.status}")
                    return {}
    except Exception as e:
        logger.error(f"Error fetching prices from DexScreener: {e}")
        return {}

# Asynchronous function to get Jupiter quote
async def get_jupiter_quote(input_mint, output_mint, amount, slippage_bps=50):
    url = f"{JUPITER_QUOTE_API}?inputMint={input_mint}&outputMint={output_mint}&amount={amount}&slippageBps={slippage_bps}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Jupiter quote API error: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error fetching Jupiter quote: {e}")
        return None

# Asynchronous trading loop
async def trading_loop():
    while st.session_state.running:
        token_addresses = list(st.session_state.tokens.keys())
        if token_addresses:
            prices_data = await fetch_token_prices(token_addresses)
            
            for token_addr, data in st.session_state.tokens.items():
                price_info = prices_data.get(token_addr)
                if price_info:
                    current_price = price_info['price']
                    symbol = price_info['symbol']
                    decimals = price_info['decimals']
                    st.session_state.tokens[token_addr]['symbol'] = symbol
                    st.session_state.tokens[token_addr]['decimals'] = decimals
                else:
                    # Fallback to simulation if API fails
                    current_price = data['last_price'] + data['last_price'] * random.uniform(-0.005, 0.005)
                    logger.warning(f"Using simulated price for {token_addr}")
                
                last_price = data['last_price']
                
                # Update last price immediately for accuracy
                st.session_state.tokens[token_addr]['last_price'] = current_price
                
                # Scalping strategy logic per token
                position = data['position']
                buy_price = data['buy_price']
                
                if position == 0:
                    # Buy if price drops 0.1% from last price
                    if current_price < last_price * 0.999:
                        # Use 10% of balance for each trade, but check if sufficient balance
                        trade_value = st.session_state.balance * 0.1
                        if trade_value > 0:
                            amount_in = int(trade_value * 10**USDC_DECIMALS)
                            quote = await get_jupiter_quote(USDC_MINT, token_addr, amount_in)
                            if quote:
                                quantity = int(quote['outAmount']) / 10**data['decimals']
                                if quantity > 0:
                                    effective_buy_price = trade_value / quantity
                                    st.session_state.tokens[token_addr]['position'] = quantity
                                    st.session_state.tokens[token_addr]['buy_price'] = effective_buy_price
                                    st.session_state.balance -= trade_value
                                    st.session_state.history.append({
                                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                        "action": "BUY",
                                        "token": symbol or token_addr,
                                        "price": effective_buy_price,
                                        "quantity": quantity,
                                        "value": trade_value
                                    })
                                    logger.info(f"Simulated BUY {quantity} of {symbol} at effective price {effective_buy_price}")
                            else:
                                # Fallback if no quote
                                quantity = trade_value / current_price
                                if quantity > 0:
                                    st.session_state.tokens[token_addr]['position'] = quantity
                                    st.session_state.tokens[token_addr]['buy_price'] = current_price
                                    st.session_state.balance -= trade_value
                                    st.session_state.history.append({
                                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                        "action": "BUY",
                                        "token": symbol or token_addr,
                                        "price": current_price,
                                        "quantity": quantity,
                                        "value": trade_value
                                    })
                                    logger.info(f"Fallback BUY {quantity} of {symbol} at {current_price}")
                else:
                    # Sell if price rises 0.15% from buy price
                    if current_price > buy_price * 1.0015:
                        amount_in = int(position * 10**data['decimals'])
                        quote = await get_jupiter_quote(token_addr, USDC_MINT, amount_in)
                        if quote:
                            out_amount = int(quote['outAmount']) / 10**USDC_DECIMALS
                            profit = out_amount - (position * buy_price)
                            st.session_state.balance += out_amount
                            st.session_state.pnl += profit
                            effective_sell_price = out_amount / position
                            st.session_state.history.append({
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "action": "SELL",
                                "token": symbol or token_addr,
                                "price": effective_sell_price,
                                "quantity": position,
                                "value": out_amount,
                                "profit": profit
                            })
                            logger.info(f"Simulated SELL {position} of {symbol} at effective price {effective_sell_price}, Profit: {profit}")
                            st.session_state.tokens[token_addr]['position'] = 0.0
                            st.session_state.tokens[token_addr]['buy_price'] = None
                        else:
                            # Fallback if no quote
                            sell_value = position * current_price
                            profit = position * (current_price - buy_price)
                            st.session_state.balance += sell_value
                            st.session_state.pnl += profit
                            st.session_state.history.append({
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "action": "SELL",
                                "token": symbol or token_addr,
                                "price": current_price,
                                "quantity": position,
                                "value": sell_value,
                                "profit": profit
                            })
                            logger.info(f"Fallback SELL {position} of {symbol} at {current_price}, Profit: {profit}")
                            st.session_state.tokens[token_addr]['position'] = 0.0
                            st.session_state.tokens[token_addr]['buy_price'] = None

        # Simulate low-latency execution (500ms interval)
        await asyncio.sleep(0.5)

# Function to run the asyncio loop in a separate thread
def run_trading_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(trading_loop())
    except Exception as e:
        logger.error(f"Trading loop error: {e}")

# Streamlit Dashboard
st.title("Solana Trading Bot Simulator (Paper Trading with DexScreener and Jupiter Integration)")

# Add token input with validation
st.subheader("Add Token to Monitor")
token_address = st.text_input("Solana Token Address (e.g., So11111111111111111111111111111111111111112 for SOL)")
if st.button("Add Token"):
    if token_address:
        if token_address in st.session_state.tokens:
            st.warning(f"Token {token_address} is already being monitored.")
        else:
            # Validate token by fetching price
            prices_data = asyncio.run(fetch_token_prices([token_address]))
            if token_address in prices_data:
                price_info = prices_data[token_address]
                st.session_state.tokens[token_address] = {
                    'position': 0.0,
                    'buy_price': None,
                    'last_price': price_info['price'],
                    'symbol': price_info['symbol'],
                    'decimals': price_info['decimals']
                }
                st.success(f"Added valid token {price_info['symbol']} ({token_address}) with initial price ${price_info['price']:.4f}")
            else:
                st.error("Invalid token address or no data available on DexScreener.")
    else:
        st.error("Please enter a token address.")

# Display monitored tokens
if st.session_state.tokens:
    st.subheader("Monitored Tokens")
    for addr, data in st.session_state.tokens.items():
        st.write(f"{data['symbol']} ({addr}): Position {data['position']:.4f}, Last Price ${data['last_price']:.4f}")

# Start/Stop buttons
if not st.session_state.running:
    if st.button("Start Trading"):
        if st.session_state.tokens:
            st.session_state.running = True
            thread = Thread(target=run_trading_loop, daemon=True)
            thread.start()
        else:
            st.warning("Add at least one token to start trading.")
else:
    if st.button("Stop Trading"):
        st.session_state.running = False

# Display real-time metrics
st.subheader("Current Status")
col1, col2 = st.columns(2)
col1.metric("USDC Balance", f"${st.session_state.balance:.2f}")
col2.metric("Total PnL", f"${st.session_state.pnl:.2f}")

# Trade History
st.subheader("Trade History")
if st.session_state.history:
    df = pd.DataFrame(st.session_state.history)
    st.dataframe(df)
else:
    st.write("No trades yet.")

# Auto-refresh the dashboard every 1 second for near real-time updates
time.sleep(1)
st.rerun()