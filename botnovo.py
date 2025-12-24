import streamlit as st
import time
import requests
import pandas as pd
from datetime import datetime

# ==========================================================
# 💾 BANCO DE DADOS EM CACHE
# ==========================================================
@st.cache_resource
def get_db():
    return {"saldo": 1000.0, "historico": [], "ciclo": 1}

db = get_db()

# ==========================================================
# ⚙️ MOTOR DE POOL (VELOCIDADE MÁXIMA)
# ==========================================================
def buscar_melhor_pool(ca):
    if not ca or len(ca.strip()) < 30: return None
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('pairs'):
                pools_solana = [
                    p for p in data['pairs'] 
                    if p.get('chainId') == 'solana' and p.get('quoteToken', {}).get('symbol') == 'SOL'
                ]
                if pools_solana:
                    # Pega a pool com mais liquidez
                    melhor = max(pools_solana, key=lambda x: float(x.get('liquidity', {}).get('usd', 0)))
                    return {
                        "nome": melhor['baseToken']['symbol'].upper(),
                        "pair_address": melhor['pairAddress'],
                        "preco_inicial": float(melhor['priceUsd']),
                        "dex": melhor['dexId'].capitalize()
                    }
    except: pass
    return None

def monitorar_preco_pool(pair_address):
    try:
        url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{pair_address}"
        res = requests.get(url, timeout=1)
        if res.status_code == 200:
            return float(res.json()['pair']['priceUsd'])
    except: pass
    return None

# ==========================================================
# 🖥️ INTERFACE
# ==========================================================
st.set_page_config(page_title="Sniper Pro v21", layout="wide")

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "running" not in st.session_state: st.session_state.running = False

if not st.session_state.logged_in:
    st.title("🛡️ Login")
    u = st.text_input("Usuário")
    p = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if u == "admin" and p == "1234":
            st.session_state.logged_in = True
            st.rerun()
else:
    with st.sidebar:
        st.header(f"💰 Banca")
        moeda_ref = st.radio("Moeda:", ["USD", "BRL"])
        taxa = 5.05 if moeda_ref == "BRL" else 1.0
        st.metric("Saldo", f"{'R$' if moeda_ref == 'BRL' else '$'} {db['saldo'] * taxa:,.2f}")
        
        novo_val = st.number_input("Ajustar Saldo", value=float(db['saldo'] * taxa))
        if st.button("💾 Salvar Saldo"):
            db['saldo'] = novo_val / taxa
            st.rerun()

        st.divider()
        alvo = st.slider("Alvo (%)", 0.5, 20.0, 2.5)
        stop = st.slider("Stop (%)", 0.5, 15.0, 3.0)
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.rerun()

    # --- LÓGICA DE OPERAÇÃO ---
    if not st.session_state.running:
        st.title("🚀 Sniper Pro v21")
        ca_input = st.text_input("CA do Token:")
        invest_input = st.number_input(f"Valor Ordem ({moeda_ref})", value=10.0 * taxa)

        if st.button("⚡ INICIAR ESTRATÉGIA"):
            pool_data = buscar_melhor_pool(ca_input.strip())
            if pool_data:
                st.session_state.t_nome = pool_data['nome']
                st.session_state.t_pair = pool_data['pair_address']
                st.session_state.t_preco = pool_data['preco_inicial']
                st.session_state.invest_usd = invest_input / taxa
                st.session_state.running = True
                st.rerun()
            else: st.error("Erro ao mapear pool.")
    else:
        # PAINEL ATIVO
        col_head, col_ctrl = st.columns([3, 1])
        col_head.subheader(f"🛰️ Monitorando: {st.session_state.t_nome}")
        
        if col_ctrl.button("🛑 PARAR BOT", use_container_width=True):
            st.session_state.running = False
            st.rerun()

        monitor_preco = col_ctrl.empty()
        slots = [st.empty() for _ in range(10)]
        area_hist = st.empty()

        # --- LOOP INFINITO DE CICLOS ---
        while st.session_state.running:
            # Pega preço atual para as novas ordens do ciclo
            p_start = monitorar_preco_pool(st.session_state.t_pair)
            if not p_start: 
                time.sleep(1)
                continue
                
            # Inicializa as 10 ordens do ciclo atual
            trades = [{"ent": p_start, "pnl": 0.0, "on": True, "max": 0.0, "res": "", "liq": 0.0} for _ in range(10)]
            ultimo_p = p_start

            # Loop das 10 ordens (Só sai quando todas fecharem)
            while any(t['on'] for t in trades) and st.session_state.running:
                p_now = monitorar_preco_pool(st.session_state.t_pair)
                if p_now:
                    seta = "▲" if p_now >= ultimo_p else "▼"
                    cor_s = "#00FF00" if p_now >= ultimo_p else "#FF4B4B"
                    monitor_preco.markdown(f"<div style='text-align:center; font-size:20px; font-weight:bold; background:#1e1e1e; padding:10px; border-radius:10px;'>{p_now:.8f} <span style='color:{cor_s};'>{seta}</span></div>", unsafe_allow_html=True)
                    ultimo_p = p_now

                    for i, t in enumerate(trades):
                        if t['on']:
                            if db['saldo'] < st.session_state.invest_usd:
                                t['on'] = False; t['res'] = "STOP"; continue

                            t['pnl'] = ((p_now / t['ent']) - 1) * 100
                            if t['pnl'] > t['max']: t['max'] = t['pnl']
                            
                            st_din = -stop
                            if t['max'] > 1.2: st_din = 0.1

                            if t['pnl'] >= alvo or t['pnl'] <= st_din:
                                t['on'] = False
                                t['res'] = "WIN" if t['pnl'] > 0 else "LOSS"
                                t['liq'] = (st.session_state.invest_usd * (t['pnl']/100)) - (st.session_state.invest_usd * 0.01)
                                db['saldo'] += t['liq']

                            cor_p = "#00FF00" if t['pnl'] >= 0 else "#FF4B4B"
                            icon = "🔵" if t['on'] else ("✅" if t['res'] == "WIN" else "❌")
                            slots[i].markdown(f"{icon} Ordem {i+1}: <span style='color:{cor_p}; font-weight:bold;'>{t['pnl']:+.2f}%</span>", unsafe_allow_html=True)
                
                time.sleep(0.05)

            # FIM DE UM CICLO -> SALVAR E REINICIAR AUTOMATICAMENTE
            if st.session_state.running:
                liq_ciclo = sum(tr['liq'] for tr in trades)
                db['historico'].insert(0, {
                    "CICLO": f"#{db['ciclo']}",
                    "LÍQUIDO": f"{'R$' if moeda_ref == 'BRL' else '$'} {liq_ciclo * taxa:,.2f}",
                    "HORA": datetime.now().strftime("%H:%M:%S")
                })
                db['ciclo'] += 1
                area_hist.table(pd.DataFrame(db['historico']).head(5))
                # O loop 'while st.session_state.running' vai recomeçar aqui automaticamente!

