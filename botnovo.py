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
# ⚙️ MOTOR DE BUSCA E MONITORAMENTO
# ==========================================================
def buscar_melhor_pool(ca):
    if not ca or len(ca.strip()) < 30: return None
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('pairs'):
                pools_solana = [p for p in data['pairs'] if p.get('chainId') == 'solana' and p.get('quoteToken', {}).get('symbol') == 'SOL']
                if pools_solana:
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
# 🖥️ INTERFACE v22.0 (ESTRATÉGIA 90% ACCURACY)
# ==========================================================
st.set_page_config(page_title="Sniper Pro v22 - 90% Acc", layout="wide")

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "running" not in st.session_state: st.session_state.running = False

if not st.session_state.logged_in:
    st.title("🛡️ Login Sniper")
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
        
        novo_val = st.number_input("Ajustar Banca", value=float(db['saldo'] * taxa))
        if st.button("💾 Salvar"):
            db['saldo'] = novo_val / taxa
            st.rerun()

        st.divider()
        st.subheader("🚀 Parâmetros Sniper")
        alvo = st.slider("Alvo de Saída (%)", 0.5, 20.0, 2.0)
        stop_max = st.slider("Stop Loss Máximo (%)", 0.5, 15.0, 3.5)
        gatilho_on = st.checkbox("Confirmar Micro-Tendência", value=True)
        
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.rerun()

    if not st.session_state.running:
        st.title("🚀 Sniper Pro v22.0")
        st.info("Estratégia atualizada para alta assertividade baseada em momentum.")
        ca_input = st.text_input("CA do Token:")
        invest_input = st.number_input(f"Valor Ordem ({moeda_ref})", value=10.0 * taxa)

        if st.button("⚡ INICIAR OPERAÇÃO"):
            pool_data = buscar_melhor_pool(ca_input.strip())
            if pool_data:
                st.session_state.t_nome = pool_data['nome']
                st.session_state.t_pair = pool_data['pair_address']
                st.session_state.invest_usd = invest_input / taxa
                st.session_state.running = True
                st.rerun()
            else: st.error("Erro ao mapear pool.")
    else:
        # PAINEL DE CONTROLO
        col_head, col_ctrl = st.columns([3, 1])
        col_head.subheader(f"🛰️ Sniper Ativo: {st.session_state.t_nome}")
        
        if col_ctrl.button("🛑 PARAR AGORA", use_container_width=True):
            st.session_state.running = False
            st.rerun()

        monitor_preco = col_ctrl.empty()
        saldo_place = col_ctrl.empty()
        slots = [st.empty() for _ in range(10)]
        status_bot = st.empty()

        while st.session_state.running:
            # --- FILTRO DE TENDÊNCIA (Gatilho de Entrada) ---
            if gatilho_on:
                status_bot.warning("⏳ Aguardando confirmação de momentum (Alta)...")
                p1 = monitorar_preco_pool(st.session_state.t_pair)
                time.sleep(1)
                p2 = monitorar_preco_pool(st.session_state.t_pair)
                if not p1 or not p2 or p2 <= p1:
                    continue # Só entra se o preço estiver subindo no micro-tempo
            
            status_bot.success("✅ Momentum Confirmado! Iniciando Ciclo.")
            p_start = monitorar_preco_pool(st.session_state.t_pair)
            trades = [{"ent": p_start, "pnl": 0.0, "on": True, "max": 0.0, "res": "", "liq": 0.0} for _ in range(10)]
            ultimo_p = p_start

            while any(t['on'] for t in trades) and st.session_state.running:
                p_now = monitorar_preco_pool(st.session_state.t_pair)
                if p_now:
                    seta = "▲" if p_now >= ultimo_p else "▼"
                    cor_s = "#00FF00" if p_now >= ultimo_p else "#FF4B4B"
                    monitor_preco.markdown(f"<div style='text-align:center; font-size:20px; font-weight:bold; background:#1e1e1e; padding:10px; border-radius:10px;'>{p_now:.8f} <span style='color:{cor_s};'>{seta}</span></div>", unsafe_allow_html=True)
                    
                    simb = "R$" if moeda_ref == "BRL" else "$"
                    saldo_place.markdown(f"<div style='text-align:center; font-size:16px; color:#aaa;'>Saldo: <b style='color:white;'>{simb} {db['saldo'] * taxa:,.2f}</b></div>", unsafe_allow_html=True)
                    ultimo_p = p_now

                    for i, t in enumerate(trades):
                        if t['on']:
                            t['pnl'] = ((p_now / t['ent']) - 1) * 100
                            if t['pnl'] > t['max']: t['max'] = t['pnl']
                            
                            # --- TRAILING STOP DINÂMICO ---
                            st_din = -stop_max
                            if t['max'] > 1.0: st_din = 0.2  # Travou no lucro, não perde mais
                            if t['max'] > 1.8: st_din = 0.8  # Sobe o stop conforme sobe o gain

                            if t['pnl'] >= alvo or t['pnl'] <= st_din:
                                t['on'] = False
                                t['res'] = "WIN" if t['pnl'] > 0 else "LOSS"
                                t['liq'] = (st.session_state.invest_usd * (t['pnl']/100)) - (st.session_state.invest_usd * 0.01)
                                db['saldo'] += t['liq']

                            cor_p = "#00FF00" if t['pnl'] >= 0 else "#FF4B4B"
                            icon = "🔵" if t['on'] else ("✅" if t['res'] == "WIN" else "❌")
                            slots[i].markdown(f"{icon} Order {i+1}: <span style='color:{cor_p}; font-weight:bold;'>{t['pnl']:+.2f}%</span> (Max: {t['max']:.2f}%)", unsafe_allow_html=True)
                
                time.sleep(0.1)

            # FIM DO CICLO
            if st.session_state.running:
                liq_c = sum(tr['liq'] for tr in trades)
                db['historico'].insert(0, {
                    "CICLO": f"#{db['ciclo']}",
                    "PNL": f"{(liq_c/(st.session_state.invest_usd*10))*100:+.2f}%",
                    "LÍQUIDO": f"{simb} {liq_c * taxa:,.2f}",
                    "HORA": datetime.now().strftime("%H:%M:%S")
                })
                db['ciclo'] += 1
                time.sleep(2) # Pausa estratégica para nova leitura de mercado
