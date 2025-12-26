import streamlit as st
import time
import requests
import pandas as pd
from datetime import datetime

# ==========================================================
# 💾 DATABASE
# ==========================================================
@st.cache_resource
def get_db():
    return {"saldo": 1000.0, "historico": [], "ciclo": 1}

db = get_db()

# ==========================================================
# 🧠 ENGINE DE PREVISÃO (PREDITIVA)
# ==========================================================
def motor_ia_v27(pnl, pnl_max, h_precos):
    if len(h_precos) < 3: return False, ""

    # Cálculo de Tendência Imediata (Derivada Simples)
    # Se a variação entre os últimos milissegundos é negativa e o lucro é alto -> SAI
    tendencia = h_precos[-1] - h_precos[-2]
    
    if pnl > 0.5:
        # Se o preço parou de subir (tendência zero ou negativa), realiza lucro "no estalo"
        if tendencia <= 0: 
            return True, "IA: Saída por Estagnação (Preditivo)"

    if pnl < -1.8: # Stop mais curto para evitar slippage
        return True, "IA: Corte de Risco Rápido"

    # Trailing dinâmico "Shadow"
    if pnl_max > 2.0 and pnl < (pnl_max - 0.3):
        return True, "IA: Shadow Trailing"

    return False, ""

# ==========================================================
# ⚙️ COMUNICAÇÃO ULTRA-RÁPIDA (JUPYTER API)
# ==========================================================
def get_price_v27(ca):
    """
    Usa a API da Jupiter para preços. É muito mais rápida que o DexScreener
    pois a Jupiter é um motor de execução direto.
    """
    try:
        # Consultando a Jupiter (Gratuito e sem delay de agregação)
        url = f"https://price.jup.ag/v4/price?ids={ca}"
        res = requests.get(url, timeout=0.5).json()
        return float(res['data'][ca]['price'])
    except:
        return None

def get_token_info(ca):
    # Usamos o DexScreener apenas UMA VEZ para pegar o nome do token
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        res = requests.get(url, timeout=3).json()
        return res['pairs'][0]['baseToken']['symbol']
    except:
        return "TOKEN"

# ==========================================================
# 🖥️ INTERFACE
# ==========================================================
st.set_page_config(page_title="Sniper Pro v27 - LightSpeed", layout="wide")

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "running" not in st.session_state: st.session_state.running = False

if not st.session_state.logged_in:
    st.title("⚡ Sniper Light-Speed")
    u, p = st.text_input("User"), st.text_input("Pass", type="password")
    if st.button("Ligar Motor"):
        if u == "admin" and p == "1234":
            st.session_state.logged_in = True
            st.rerun()
else:
    with st.sidebar:
        st.header("⚙️ Status do Motor")
        moeda = st.radio("Moeda:", ["USD", "BRL"])
        taxa = 5.05 if moeda == "BRL" else 1.0
        st.metric("Banca Disponível", f"{db['saldo'] * taxa:,.2f}")
        if st.button("Desligar"):
            st.session_state.logged_in = False
            st.rerun()

    if not st.session_state.running:
        st.title("🚀 Sniper Pro v27.0")
        st.info("Utilizando JUPYTER API v4 para latência reduzida.")
        ca_input = st.text_input("CA do Token (Solana):")
        val_input = st.number_input(f"Valor por Ordem ({moeda})", value=10.0 * taxa)
        
        if st.button("⚡ DISPARAR SNIPER"):
            nome = get_token_info(ca_input.strip())
            st.session_state.update({
                "t_nome": nome, "ca": ca_input.strip(), 
                "invest": val_input/taxa, "running": True
            })
            st.rerun()
    else:
        # PAINEL DE OPERAÇÃO EM ALTA VELOCIDADE
        c1, c2 = st.columns([3, 1])
        c1.subheader(f"🟢 EM EXECUÇÃO: {st.session_state.t_nome}")
        if c2.button("🛑 CANCELAR"):
            st.session_state.running = False
            st.rerun()

        price_box = c1.empty()
        slots = [st.empty() for _ in range(10)]

        while st.session_state.running:
            p_start = get_price_v27(st.session_state.ca)
            if not p_start: continue
            
            trades = [{"ent": p_start, "pnl": 0.0, "on": True, "max": 0.0, "res": "", "h": [p_start]} for _ in range(10)]

            while any(t['on'] for t in trades) and st.session_state.running:
                p_now = get_price_v27(st.session_state.ca)
                if p_now:
                    price_box.markdown(f"### Preço Atual: `{p_now:.8f}`")
                    
                    for i, t in enumerate(trades):
                        if t['on']:
                            t['pnl'] = ((p_now / t['ent']) - 1) * 100
                            if t['pnl'] > t['max']: t['max'] = t['pnl']
                            t['h'].append(p_now)
                            if len(t['h']) > 5: t['h'].pop(0)

                            # DECISÃO PREDITIVA
                            fechar, motivo = motor_ia_v27(t['pnl'], t['max'], t['h'])
                            
                            if fechar:
                                t['on'] = False
                                t['res'] = motivo
                                db['saldo'] += (st.session_state.invest * (t['pnl']/100)) - (st.session_state.invest * 0.005) # Taxa Jup é menor

                            cor = "#00FF00" if t['pnl'] >= 0 else "#FF4B4B"
                            slots[i].markdown(f"Ordem {i+1}: <b style='color:{cor}'>{t['pnl']:+.2f}%</b> | {t['res']}", unsafe_allow_html=True)
                
                # Sem sleep longo para manter o processador focado na API
                time.sleep(0.001) 
            
            db['ciclo'] += 1
