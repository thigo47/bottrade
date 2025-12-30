# botnovo.py
# App Streamlit + loop de paper trading assíncrono (rodando em background thread)
# Fonte de preços: CoinGecko (SOL/USD)
# Estratégia: EMA adaptativa + scalping thresholds ajustados por volatilidade
# Paper trading somente. Persistência em memória.
# Requer: Python 3.10+, streamlit, pandas, numpy, requests

import streamlit as st
import threading
import asyncio
import time
from collections import deque
import requests
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
from typing import Deque, List
import uuid

# ---------- Configurações ----------
PRICE_POLL_INTERVAL = 1.0  # segundos
HISTORY_MAXLEN = 600  # quantos preços manter (1s * 600 = 10 minutos)
EMA_SHORT = 5
EMA_LONG = 20
BASE_BUY_DROP = 0.001  # 0.1%
BASE_SELL_RISE = 0.0015  # 0.15%
VOLATILITY_SCALE = 50.0  # ajuste para normalizar volatilidade -> afeta thresholds
FEE_PCT = 0.001  # 0.1% por trade
SLIPPAGE_PCT = 0.0005  # 0.05% slippage
POSITION_FRACTION = 0.1  # 10% do capital por entrada (proporcional)
INITIAL_CAPITAL = 1000.0  # USD

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"

# ---------- Tipos ----------
@dataclass
class Position:
    id: str
    entry_price: float
    size_sol: float
    entry_time: float
    entry_cash_used: float

@dataclass
class TradeRecord:
    id: str
    entry_time: float
    exit_time: float
    entry_price: float
    exit_price: float
    size_sol: float
    pnl: float
    fees: float
    notes: str

# ---------- Engine ----------
class TradingEngine:
    def __init__(self):
        self.prices: Deque[float] = deque(maxlen=HISTORY_MAXLEN)
        self.timestamps: Deque[float] = deque(maxlen=HISTORY_MAXLEN)
        self.position: Position | None = None
        self.trade_history: List[TradeRecord] = []
        self.capital = INITIAL_CAPITAL
        self.lock = threading.Lock()
        self.running = False
        self.last_price = None

    def fetch_price(self):
        try:
            resp = requests.get(COINGECKO_URL, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            price = float(data["solana"]["usd"])
            return price
        except Exception as e:
            # fallback: add small random walk if API fails
            # but avoid throwing — return last_price +/- small noise
            if self.last_price is not None:
                price = self.last_price * (1 + np.random.normal(0, 0.0005))
                return float(price)
            raise

    def update_price(self, price: float, ts: float):
        with self.lock:
            self.prices.append(price)
            self.timestamps.append(ts)
            self.last_price = price

    def compute_indicators(self):
        with self.lock:
            prices = list(self.prices)
        if len(prices) < 5:
            return None
        s = pd.Series(prices)
        ema_short = s.ewm(span=EMA_SHORT, adjust=False).mean().iloc[-1]
        ema_long = s.ewm(span=EMA_LONG, adjust=False).mean().iloc[-1] if len(s) >= EMA_LONG else s.ewm(span=EMA_LONG, adjust=False).mean().iloc[-1]
        # returns and volatility
        returns = s.pct_change().dropna()
        vol = returns.std() if not returns.empty else 0.0
        return {
            "ema_short": float(ema_short),
            "ema_long": float(ema_long),
            "volatility": float(vol),
            "last_price": float(prices[-1]),
            "recent_return": float((prices[-1] / prices[-2] - 1)) if len(prices) >= 2 else 0.0,
            "n": len(prices)
        }

    def adaptive_thresholds(self, vol: float):
        # normaliza volatilidade e ajusta thresholds
        vol_norm = vol * VOLATILITY_SCALE  # escala para números mais utilizáveis
        buy_thresh = BASE_BUY_DROP * (1 + vol_norm)
        sell_thresh = BASE_SELL_RISE * (1 + vol_norm)
        # regras mínimas/máximas para evitar valores extremos
        buy_thresh = min(max(buy_thresh, 0.0005), 0.01)
        sell_thresh = min(max(sell_thresh, 0.0008), 0.02)
        return buy_thresh, sell_thresh

    def try_open_position(self, price, indicators):
        buy_thresh, _ = self.adaptive_thresholds(indicators["volatility"])
        # Condition: price dropped enough from previous tick OR EMA crossover
        recent_ret = indicators["recent_return"]
        ema_signal = indicators["ema_short"] > indicators["ema_long"]  # short over long => upward bias
        # We'll buy on dip if there's upward bias from EMA or big dip
        should_buy = (recent_ret <= -buy_thresh and ema_signal) or (recent_ret <= -buy_thresh * 1.5 and not ema_signal)
        if not should_buy:
            return False
        # compute position size (proporcional)
        with self.lock:
            available = self.capital
            cash_to_use = available * POSITION_FRACTION
            if cash_to_use <= 1.0:
                return False
            # apply slippage on entry (worse price)
            exec_price = price * (1 + SLIPPAGE_PCT)
            size_sol = cash_to_use / exec_price
            fee = cash_to_use * FEE_PCT
            total_cost = cash_to_use + fee
            if total_cost > self.capital:
                # shouldn't happen, but guard
                cash_to_use = self.capital / (1 + FEE_PCT)
                exec_price = price * (1 + SLIPPAGE_PCT)
                size_sol = cash_to_use / exec_price
                fee = cash_to_use * FEE_PCT
                total_cost = cash_to_use + fee
            # create position
            self.capital -= total_cost
            self.position = Position(
                id=str(uuid.uuid4()),
                entry_price=exec_price,
                size_sol=size_sol,
                entry_time=time.time(),
                entry_cash_used=cash_to_use
            )
        return True

    def try_close_position(self, price, indicators):
        if self.position is None:
            return False
        _, sell_thresh = self.adaptive_thresholds(indicators["volatility"])
        # compute current return vs entry
        entry = self.position.entry_price
        ret = (price - entry) / entry
        # prefer closing when profit target reached or EMA short < long (trend flip)
        ema_flip = indicators["ema_short"] < indicators["ema_long"]
        should_close = (ret >= sell_thresh) or ema_flip or (ret <= -0.03)  # small stop-loss -3%
        if not should_close:
            return False
        # execute close
        with self.lock:
            exec_price = price * (1 - SLIPPAGE_PCT)  # worse price when selling
            proceeds = exec_price * self.position.size_sol
            fee = proceeds * FEE_PCT
            net = proceeds - fee
            pnl = net - self.position.entry_cash_used
            trade = TradeRecord(
                id=self.position.id,
                entry_time=self.position.entry_time,
                exit_time=time.time(),
                entry_price=self.position.entry_price,
                exit_price=exec_price,
                size_sol=self.position.size_sol,
                pnl=pnl,
                fees=fee + (self.position.entry_cash_used * FEE_PCT),
                notes=f"ret={ret:.4f}"
            )
            self.capital += net
            self.trade_history.append(trade)
            self.position = None
        return True

    async def loop(self):
        self.running = True
        while self.running:
            try:
                price = self.fetch_price()
            except Exception:
                # if fetch fails and no last price, sleep and continue
                await asyncio.sleep(PRICE_POLL_INTERVAL)
                continue
            ts = time.time()
            self.update_price(price, ts)
            indicators = self.compute_indicators()
            if indicators:
                # try close first (take profits)
                closed = self.try_close_position(indicators["last_price"], indicators)
                if not closed:
                    # try open
                    self.try_open_position(indicators["last_price"], indicators)
            await asyncio.sleep(PRICE_POLL_INTERVAL)

    def stop(self):
        self.running = False

# ---------- Streamlit UI ----------
st.set_page_config(page_title="BotTrade - Paper Trading (SOL)", layout="wide")
st.title("BotTrade — Paper Trading (SOL)")

if "engine" not in st.session_state:
    st.session_state.engine = TradingEngine()
if "bg_thread" not in st.session_state:
    st.session_state.bg_thread = None

engine: TradingEngine = st.session_state.engine

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Controles")
    if engine.running:
        if st.button("Parar Bot"):
            engine.stop()
    else:
        if st.button("Iniciar Bot"):
            # Start background asyncio loop in a thread
            def start_bg():
                # each thread needs its own event loop
                asyncio.run(engine.loop())
            t = threading.Thread(target=start_bg, daemon=True)
            st.session_state.bg_thread = t
            t.start()
    if st.button("Resetar Estado (limpa histórico)"):
        with engine.lock:
            engine.prices.clear()
            engine.timestamps.clear()
            engine.position = None
            engine.trade_history.clear()
            engine.capital = INITIAL_CAPITAL

    st.write("Intervalo de polling:", f"{PRICE_POLL_INTERVAL}s")
    st.write("Fees simuladas:", f"{FEE_PCT*100:.3f}% por trade")
    st.write("Slippage simulada:", f"{SLIPPAGE_PCT*100:.3f}%")
    st.write("Tamanho de posição por entrada:", f"{POSITION_FRACTION*100:.1f}% do capital disponível")

with col2:
    st.subheader("Status rápido")
    st.metric("Capital USD", f"${engine.capital:,.2f}")
    if engine.position:
        st.write("Posição em aberto:")
        st.write(f"- Entrada: {engine.position.entry_price:.4f} USD")
        st.write(f"- Size (SOL): {engine.position.size_sol:.6f}")
        st.write(f"- Tempo desde entrada: {time.time()-engine.position.entry_time:.1f}s")
    else:
        st.write("Sem posição aberta")

# Price chart and indicators
placeholder_chart = st.empty()
placeholder_table = st.empty()

def render_ui():
    with engine.lock:
        prices = list(engine.prices)
        times = list(engine.timestamps)
        hist = list(engine.trade_history)
        pos = engine.position

    if not prices:
        placeholder_chart.write("Aguardando preços...")
        placeholder_table.write("")
        return

    df = pd.DataFrame({"ts": pd.to_datetime(times, unit="s"), "price": prices})
    df = df.set_index("ts")
    # compute EMAs for display
    df["ema_short"] = df["price"].ewm(span=EMA_SHORT, adjust=False).mean()
    df["ema_long"] = df["price"].ewm(span=EMA_LONG, adjust=False).mean()

    # Plot
    chart = {
        "data": df.tail(300)[["price", "ema_short", "ema_long"]],
    }
    placeholder_chart.line_chart(chart["data"])

    # Trades summary
    trades_summary = {
        "total_trades": len(hist),
        "open_position": bool(pos),
        "capital": f"${engine.capital:,.2f}",
        "unrealized_pnl": (
            ((engine.last_price - pos.entry_price) * pos.size_sol) if pos else 0.0
        ),
    }
    # trade table
    if hist:
        trades_df = pd.DataFrame([asdict(t) for t in hist])
        trades_df["entry_time"] = pd.to_datetime(trades_df["entry_time"], unit="s")
        trades_df["exit_time"] = pd.to_datetime(trades_df["exit_time"], unit="s")
        trades_df = trades_df[["id", "entry_time", "exit_time", "entry_price", "exit_price", "size_sol", "pnl", "fees", "notes"]]
    else:
        trades_df = pd.DataFrame(columns=["id","entry_time","exit_time","entry_price","exit_price","size_sol","pnl","fees","notes"])

    placeholder_table.subheader("Resumo")
    placeholder_table.write(trades_summary)
    placeholder_table.subheader("Histórico de trades (encerrados)")
    placeholder_table.dataframe(trades_df.tail(50))

# Periodically refresh UI
render_ui()

# Auto-refresh every second (client-side)
st.experimental_rerun()