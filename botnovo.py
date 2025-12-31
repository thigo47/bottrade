import streamlit as st
import asyncio
import time
import random
from threading import Thread
import pandas as pd

# Initialize session state variables
if 'balance' not in st.session_state:
    st.session_state.balance = 1000.0  # Initial fictional USDC balance

if 'position' not in st.session_state:
    st.session_state.position = 0.0  # SOL position

if 'buy_price' not in st.session_state:
    st.session_state.buy_price = None

if 'history' not in st.session_state:
    st.session_state.history = []  # List of trade dicts

if 'pnl' not in st.session_state:
    st.session_state.pnl = 0.0  # Accumulated Profit and Loss

if 'running' not in st.session_state:
    st.session_state.running = False

if 'current_price' not in st.session_state:
    st.session_state.current_price = 100.0  # Initial SOL price

if 'last_price' not in st.session_state:
    st.session_state.last_price = 100.0

# Asynchronous trading loop
async def trading_loop():
    while st.session_state.running:
        # Simulate rapid price volatility
        change = random.uniform(-0.005, 0.005)  # Random change between -0.5% and +0.5%
        st.session_state.current_price += st.session_state.current_price * change

        # Update last price for next iteration
        current = st.session_state.current_price
        last = st.session_state.last_price

        # Scalping strategy logic
        if st.session_state.position == 0:
            # Buy if price drops 0.1% from last price
            if current < last * 0.999:
                # Use 10% of balance for each trade (adjustable)
                amount_to_buy = st.session_state.balance * 0.1 / current
                if amount_to_buy > 0:
                    st.session_state.position = amount_to_buy
                    st.session_state.buy_price = current
                    st.session_state.balance -= amount_to_buy * current
                    st.session_state.history.append({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "action": "BUY",
                        "price": current,
                        "quantity": amount_to_buy,
                        "value": amount_to_buy * current
                    })
        else:
            # Sell if price rises 0.15% from buy price
            if current > st.session_state.buy_price * 1.0015:
                sell_value = st.session_state.position * current
                profit = st.session_state.position * (current - st.session_state.buy_price)
                st.session_state.balance += sell_value
                st.session_state.pnl += profit
                st.session_state.history.append({
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "action": "SELL",
                    "price": current,
                    "quantity": st.session_state.position,
                    "value": sell_value,
                    "profit": profit
                })
                st.session_state.position = 0.0
                st.session_state.buy_price = None

        # Update last price
        st.session_state.last_price = current

        # Simulate low-latency execution (500ms interval)
        await asyncio.sleep(0.5)

# Function to run the asyncio loop in a separate thread
def run_trading_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(trading_loop())

# Streamlit Dashboard
st.title("Solana Trading Bot Simulator (Paper Trading)")

# Start/Stop buttons
if not st.session_state.running:
    if st.button("Start Trading"):
        st.session_state.running = True
        thread = Thread(target=run_trading_loop, daemon=True)
        thread.start()
else:
    if st.button("Stop Trading"):
        st.session_state.running = False

# Display real-time metrics
st.subheader("Current Status")
col1, col2, col3 = st.columns(3)
col1.metric("USDC Balance", f"${st.session_state.balance:.2f}")
col2.metric("SOL Position", f"{st.session_state.position:.4f}")
col3.metric("Current SOL Price", f"${st.session_state.current_price:.2f}")

st.metric("Total PnL", f"${st.session_state.pnl:.2f}")

# Trade History
st.subheader("Trade History")
if st.session_state.history:
    df = pd.DataFrame(st.session_state.history)
    st.dataframe(df)
else:
    st.write("No trades yet.")

# Auto-refresh the dashboard every 1 second for near real-time updates
# Note: The trading loop runs in background, so interface remains responsive
time.sleep(1)
st.rerun()