import streamlit as st
import pandas as pd
import requests
import time
import random
from datetime import datetime

# --- CONFIGURAÇÃO DA UI ---
st.set_page_config(page_title="Trojan Clone | Solana Bot", layout="wide", initial_sidebar_state="expanded")

# --- ESTILO CSS PARA DARK MODE TRADING ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .status-running { color: #00ff00; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DO ESTADO ---
if 'wallet' not in st.session_state:
    st.session_state.wallet = {"SOL": 10.0, "USDC": 1000.0}
    st.session_state.history = []
    st.session_state.running = False
    st.session_state.logs = []

# --- FUNÇÕES CORE ---

def get_dex_price(pair_address):
    """Busca preço real via DexScreener API"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{pair_address}"
        res = requests.get(url, timeout=2)
        data = res.json()
        pair = data['pair']
        return {
            "price": float(pair['priceUsd']),
            "symbol": pair['baseToken']['symbol'],
            "liquidity": pair['liquidity']['usd'],
            "volume_5m": pair['volume']['m5']
        }
    except Exception:
        return None

def calculate_execution(amount_sol, current_price, slippage_pct, priority_fee):
    """Simula a execução com Slippage e Taxas da Solana"""
    # Simulação de impacto no preço (Slippage realístico baseado no tamanho da ordem)
    impact = (amount_sol * 0.001) # 0.1% de impacto a cada 1 SOL
    actual_slippage = random.uniform(0.01, slippage_pct) 
    
    executed_price = current_price * (1 + (actual_slippage / 100) + impact)
    total_cost_sol = amount_sol + priority_fee # Taxa de prioridade (Jito/Compute Budget)
    
    return executed_price, total_cost_sol

# --- SIDEBAR (CONFIGURAÇÕES) ---
with st.sidebar:
    st.title("⚡ Trojan Clone v1.0")
    st.subheader("Wallet Connect (Simulated)")
    st.code("4jZ...x89 (Phantom)", language="text")
    
    st.divider()
    
    target_token = st.text_input("Solana Pair Address", value="8s99S96nS7B69E8Y3D1HpH8L4Dk5C2C4xM4F3L") # Ex: SOL/USDC
    trade_amount = st.number_input("Amount per Trade (SOL)", value=0.1, step=0.1)
    max_slippage = st.slider("Max Slippage (%)", 0.1, 15.0, 1.0)
    priority_fee = st.number_input("Priority Fee (SOL)", value=0.001, format="%.4f")
    
    if st.button("🚀 START BOT", use_container_width=True, type="primary"):
        st.session_state.running = True
    
    if st.button("🛑 STOP BOT", use_container_width=True):
        st.session_state.running = False

# --- DASHBOARD PRINCIPAL ---
col1, col2, col3 = st.columns(3)
price_placeholder = col1.empty()
wallet_placeholder = col2.empty()
status_placeholder = col3.empty()

st.write("### Live Market Execution")
table_placeholder = st.empty()

# --- LOOP DE ALTA FREQUÊNCIA ---
if st.session_state.running:
    while st.session_state.running:
        data = get_dex_price(target_token)
        
        if data:
            # Simulação de Lógica de Scalping
            # Vende se o lucro for > 0.5% ou Compra se cair 0.5%
            current_price = data['price']
            
            # Executa o trade simulado
            exec_price, total_cost = calculate_execution(trade_amount, current_price, max_slippage, priority_fee)
            
            # Atualiza Carteira
            if st.session_state.wallet["SOL"] >= total_cost:
                st.session_state.wallet["SOL"] -= total_cost
                
                new_entry = {
                    "Time": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                    "Token": data['symbol'],
                    "Price": f"${exec_price:.6f}",
                    "Slippage": f"{random.uniform(0.01, max_slippage):.2f}%",
                    "Fee": f"{priority_fee} SOL",
                    "Status": "✅ Success"
                }
                st.session_state.history.insert(0, new_entry)
            
            # Limita histórico visual
            if len(st.session_state.history) > 10: st.session_state.history.pop()

            # Atualiza UI
            price_placeholder.metric(f"Price {data['symbol']}", f"${current_price:.6f}", f"{random.uniform(-0.1, 0.1):.2f}%")
            wallet_placeholder.metric("Phantom Balance", f"{st.session_state.wallet['SOL']:.4f} SOL")
            status_placeholder.markdown(f"Status: <span class='status-running'>ACTIVE (0.5s)</span>", unsafe_allow_html=True)
            
            table_placeholder.table(pd.DataFrame(st.session_state.history))
        
        time.sleep(0.5) # Frequência de meio segundo
else:
    status_placeholder.subheader("Status: 💤 Idle")
    if len(st.session_state.history) > 0:
        table_placeholder.table(pd.DataFrame(st.session_state.history))
