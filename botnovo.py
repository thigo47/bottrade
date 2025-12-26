import streamlit as st
import time
import requests
import pandas as pd
from datetime import datetime

# ==========================================================
# 💾 PERSISTÊNCIA DE DADOS
# ==========================================================
@st.cache_resource
def get_db():
    return {"saldo": 1000.0, "historico": [], "ciclo": 1}

db = get_db()

# ==========================================================
# 🧠 CÉREBRO IA v25.0 - LOGIC ENGINE
# ==========================================================
def decisao_ia_v25(pnl, pnl_max, historico_precos):
    """
    Análise de Momentum e Proteção de Capital Ultra-Rápida
    """
    if len(historico_precos) < 10: return False, ""

    # 1. ANÁLISE DE MOMENTUM (ACELERAÇÃO)
    ultimos_precos = historico_precos[-5:]
    subida_media = (ultimos_precos[-1] / ultimos_precos[0]) - 1
    
    # Se o preço estagnou após uma subida, realiza lucro
    if pnl > 1.5 and abs(subida_media) < 0.0001:
        return True, "IA: Exaustão Detectada (Take Profit)"

    # 2. PROTEÇÃO DE LUCRO EXPONENCIAL
    # Se o lucro foi alto, a tolerância para devolução é mínima
    if pnl_max >= 8.0:
        if pnl < 7.0: return True, "IA: Proteção de Topo (8% -> 7%)"
    elif pnl_max >= 3.0:
        if pnl < (pnl_max * 0.8): return True, "IA: Trailing 80% Ativado"

    # 3. STOP LOSS INTELIGENTE (ANTI-DUMP)
    # Se cair mais de 1% em apenas 2 atualizações de preço, é dump
    queda_relampago = (historico_precos[-1] / historico_precos[-3]) - 1
    if queda_relampago < -0.01:
        return True, "IA: Alerta de Dump (Saída Imediata)"

    # Stop Fixo de Segurança IA
    if pnl < -2.8:
        return True, "IA: Corte de Risco"

    return False, ""

# ==========================================================
# ⚙️ ENGINE DE MERCADO
# ==========================================================
def get_market_data(ca):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        res = requests.get(url, timeout=5).json()
        pair = max([p for p in res['pairs'] if p['chainId'] == 'solana'], 
                   key=lambda x: float(x['liquidity']['usd']))
        return {"nome": pair['baseToken']['symbol'], "pair": pair['pairAddress'], "preco": float(pair['priceUsd'])}
    except: return None

def get_price(pair_addr):
    try:
        url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{pair_addr}"
        return float(requests.get(url, timeout=1).json()['pair']['priceUsd'])
    except: return None

# ==========================================================
# 🖥️ INTERFACE
# ==========================================================
st.set_page_config(page_title="Sniper Pro v25 - Ultra AI", layout="wide")

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "running" not in st.session_state: st.session_state.running = False

if not st.session_state.logged_in:
    st.title("🧠 Sniper Ultra AI v25")
    u, p = st.text_input("User"), st.text_input("Pass", type="password")
    if st.button("Acessar"):
        if u == "admin" and p == "1234":
            st.session_state.logged_in = True
            st.rerun()
else:
    with st.sidebar:
        st.header("🎮 Dashboard")
        moeda = st.radio("Moeda:", ["USD", "BRL"])
        t_view = 5.05 if moeda == "BRL" else 1.0
        st.metric("Saldo Real", f"{'R$' if moeda == 'BRL' else '$'} {db['saldo'] * t_view:,.2f}")
        if st.button("Log Out"):
            st.session_state.logged_in = False
            st.rerun()

    if not st.session_state.running:
        st.title("🚀 Sniper Pro v25.0")
        ca_input = st.text_input("Token CA:")
        val_input = st.number_input(f"Valor Ordem ({moeda})", value=10.0 * t_view)
        
        if st.button("🔥 INICIAR IA AUTÓNOMA"):
            data = get_market_data(ca_input.strip())
            if data:
                st.session_state.update({"t_nome": data['nome'], "t_pair": data['pair'], 
                                         "t_preco": data['preco'], "invest": val_input/t_view, "running": True})
                st.rerun()
    else:
        # PAINEL DE EXECUÇÃO IA
        c1, c2 = st.columns([3, 1])
        c1.subheader(f"🤖 IA Operando: {st.session_state.t_nome}")
        if c2.button("🛑 PARAR AGORA"):
            st.session_state.running = False
            st.rerun()

        price_mon = c2.empty()
        bal_mon = c2.empty()
        slots = [st.empty() for _ in range(10)]

        while st.session_state.running:
            p_ref = get_price(st.session_state.t_pair)
            if not p_ref: continue
            
            trades = [{"ent": p_ref, "pnl": 0.0, "on": True, "max": 0.0, "res": "", "h": [p_ref]} for _ in range(10)]
            
            while any(t['on'] for t in trades) and st.session_state.running:
                p_now = get_price(st.session_state.t_pair)
                if p_now:
                    price_mon.markdown(f"<div style='background:#000; padding:10px; border-radius:5px; text-align:center; font-size:24px;'>{p_now:.8f}</div>", unsafe_allow_html=True)
                    bal_mon.info(f"Saldo: {db['saldo']*t_view:,.2f}")
                    
                    for i, t in enumerate(trades):
                        if t['on']:
                            t['pnl'] = ((p_now / t['ent']) - 1) * 100
                            if t['pnl'] > t['max']: t['max'] = t['pnl']
                            t['h'].append(p_now)
                            if len(t['h']) > 20: t['h'].pop(0)

                            # CHAMADA DO CÉREBRO IA
                            finalizar, motivo = decisao_ia_v25(t['pnl'], t['max'], t['h'])
                            
                            if finalizar:
                                t['on'] = False
                                t['res'] = motivo
                                db['saldo'] += (st.session_state.invest * (t['pnl']/100)) - (st.session_state.invest * 0.01)

                            color = "#00FF00" if t['pnl'] >= 0 else "#FF4B4B"
                            slots[i].markdown(f"**Ordem {i+1}:** <span style='color:{color}'>{t['pnl']:+.2f}%</span> | {t['res']}", unsafe_allow_html=True)
                
                time.sleep(0.05)
            
            db['historico'].insert(0, {"DATA": datetime.now().strftime("%H:%M")})
            db['ciclo'] += 1
