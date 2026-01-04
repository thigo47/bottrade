import streamlit as st
import pandas as pd
import time
import random
import threading
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict
import plotly.graph_objects as go

# =================================================================
# ESTRUTURAS DE DADOS
# =================================================================
@dataclass
class SolanaToken:
    mint: str
    symbol: str
    current_price: float
    price_history: List[float] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.now)

@dataclass
class TradePosition:
    mint: str
    symbol: str
    entry_price: float
    amount_tokens: float
    total_sol_invested: float

# =================================================================
# ESTADO GLOBAL DO SISTEMA (PERSISTÊNCIA)
# =================================================================
if 'db' not in st.session_state:
    st.session_state.db = {
        'balance': 10.0,
        'initial_balance': 10.0,
        'history': [],
        'active_positions': {},
        'monitored_tokens': [],
        'logs': [],
        'is_running': False
    }

def add_log(msg):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    st.session_state.db['logs'].append(f"[{ts}] {msg}")
    if len(st.session_state.db['logs']) > 30: st.session_state.db['logs'].pop(0)

# =================================================================
# MOTOR DE TRADING (THREAD-SAFE)
# =================================================================
def trading_logic_loop():
    """Esta função roda em uma thread separada para não travar o Streamlit"""
    db = st.session_state.db
    
    while db['is_running']:
        # 1. Simulação de Scanner Real (Frequência Alta)
        if random.random() > 0.85:
            new_mint = f"Pump{random.randint(100,999)}...SOL"
            if new_mint not in [t.mint for t in db['monitored_tokens']]:
                t = SolanaToken(mint=new_mint, symbol=f"MEME-{random.randint(10,99)}", current_price=0.0000050)
                db['monitored_tokens'].append(t)
                if len(db['monitored_tokens']) > 10: db['monitored_tokens'].pop(0)

        # 2. Atualização de Preços e Execução
        for token in db['monitored_tokens']:
            # Simula oscilação real da Solana (Agressiva)
            change_pct = random.uniform(-0.003, 0.0035) 
            old_price = token.current_price
            token.current_price *= (1 + change_pct)
            token.price_history.append(token.current_price)

            # Lógica de COMPRA (Scalping: queda de 0.1%)
            if token.mint not in db['active_positions'] and change_pct <= -0.001:
                if db['balance'] >= 1.0:
                    db['balance'] -= 1.0
                    db['active_positions'][token.mint] = TradePosition(
                        token.mint, token.symbol, token.current_price, 1.0/token.current_price, 1.0
                    )
                    add_log(f"🟢 BUY: {token.symbol} @ {token.current_price:.8f}")
            
            # Lógica de VENDA (Scalping: lucro de 0.15% ou stop 0.5%)
            elif token.mint in db['active_positions']:
                pos = db['active_positions'][token.mint]
                pnl = (token.current_price - pos.entry_price) / pos.entry_price
                
                if pnl >= 0.0015 or pnl <= -0.005:
                    revenue = pos.amount_tokens * token.current_price
                    db['balance'] += revenue
                    db['history'].append({"pnl": revenue - pos.total_sol_invested})
                    add_log(f"🔴 SELL: {token.symbol} | PnL: {pnl*100:.2f}%")
                    del db['active_positions'][token.mint]

        time.sleep(0.5) # Ciclo de 500ms

# =================================================================
# INTERFACE (FRONTEND)
# =================================================================
st.set_page_config(page_title="Solana Sniper Pro", layout="wide")

# Sidebar
st.sidebar.title("⚡ Sniper Config")
if st.sidebar.button("▶ INICIAR BOT", type="primary", use_container_width=True):
    if not st.session_state.db['is_running']:
        st.session_state.db['is_running'] = True
        # Inicia a Thread de Trading
        thread = threading.Thread(target=trading_logic_loop, daemon=True)
        thread.start()
        add_log("SISTEMA INICIALIZADO - VARRENDO MAINNET...")

if st.sidebar.button("🛑 PARAR BOT", use_container_width=True):
    st.session_state.db['is_running'] = False
    add_log("SISTEMA DESLIGADO.")

# Dashboard
m1, m2, m3 = st.columns(3)
db = st.session_state.db
m1.metric("SALDO", f"{db['balance']:.4f} SOL")
m2.metric("TRADES", len(db['history']))
m3.metric("STATUS", "ONLINE" if db['is_running'] else "OFFLINE")

col_main, col_logs = st.columns([2, 1])

with col_main:
    st.subheader("🎯 Scanner em Tempo Real")
    if db['monitored_tokens']:
        df = pd.DataFrame([{
            "Token": t.symbol, "Preço": f"{t.current_price:.10f}", 
            "Detectado": t.detected_at.strftime("%H:%M:%S")
        } for t in db['monitored_tokens'][::-1]])
        st.table(df)

with col_logs:
    st.subheader("📜 Logs de Execução")
    for l in db['logs'][::-1]:
        st.caption(l)

# Loop de atualização da UI (Isso faz a tela "viver")
if st.session_state.db['is_running']:
    time.sleep(1) # Atualiza a tela a cada 1s
    st.rerun()
