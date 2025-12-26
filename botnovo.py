import streamlit as st
import requests
import pandas as pd
import time
import os

# ==========================================================
# INICIALIZAÇÃO DO ESTADO
# ==========================================================
if "saldo" not in st.session_state: st.session_state.saldo = 1000.0
if "running" not in st.session_state: st.session_state.running = False
if "historico" not in st.session_state: st.session_state.historico = []
if "ciclo" not in st.session_state: st.session_state.ciclo = 1
if "auth" not in st.session_state: st.session_state.auth = False

# ==========================================================
# FUNÇÕES DE PREÇO
# ==========================================================
def fetch_price(ca):
    try:
        url = f"https://api.jup.ag/price/v2?ids={ca}"
        data = requests.get(url, timeout=5).json()
        price = data.get('data', {}).get(ca, {}).get('price')
        if price is not None:
            return float(price)
    except:
        pass
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        data = requests.get(url, timeout=5).json()
        price = data.get('pairs', [{}])[0].get('priceUsd')
        if price is not None:
            return float(price)
    except:
        pass
    return None

def get_token_info(ca):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        data = requests.get(url, timeout=5).json()
        return data.get('pairs', [{}])[0].get('baseToken', {}).get('symbol', 'TOKEN')
    except:
        return "TOKEN"

# ==========================================================
# CÉREBRO IA
# ==========================================================
def ia_brain(pnl, pnl_max, h_precos):
    if len(h_precos) < 3: return False, ""
    if pnl_max > 1.0 and pnl < pnl_max - 0.2:
        return True, "IA: Realização de Lucro"
    if pnl < -2.0:
        return True, "IA: Stop Preventivo"
    return False, ""

# ==========================================================
# CÂMBIO
# ==========================================================
@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        data = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5).json()
        return float(data['rates'].get('BRL', 5.05))
    except:
        return 5.05

# ==========================================================
# INTERFACE
# ==========================================================
st.set_page_config(page_title="Sniper Pro v29", layout="wide")

SENHA = os.getenv('SNIPER_SENHA', '1234')

if not st.session_state.auth:
    st.title("🛡️ Acesso Sniper v29")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if senha == SENHA:
            st.session_state.auth = True
            st.rerun()
else:
    with st.sidebar:
        st.header("💰 Banca")
        st.session_state.moeda = st.radio("Moeda", ["USD", "BRL"])
        st.session_state.taxa = 1.0 if st.session_state.moeda == "USD" else get_exchange_rate()
        st.metric("Saldo", f"{'R\( ' if st.session_state.moeda == 'BRL' else ' \)'} {st.session_state.saldo * st.session_state.taxa:,.2f}")
        novo = st.number_input("Alterar saldo", value=st.session_state.saldo * st.session_state.taxa)
        if st.button("Salvar"):
            st.session_state.saldo = novo / st.session_state.taxa
            st.rerun()
        if st.button("Logout"):
            st.session_state.auth = False
            st.rerun()

    if not st.session_state.running:
        st.title("🚀 Sniper Pro v29")
        ca = st.text_input("Contract Address (CA) do token")
        valor = st.number_input(f"Valor por ordem ({st.session_state.moeda})", value=10.0 * st.session_state.taxa)

        if st.button("INICIAR BOT"):
            preco = fetch_price(ca.strip())
            if preco:
                st.session_state.ca = ca.strip()
                st.session_state.t_nome = get_token_info(ca.strip())
                st.session_state.invest_usd = valor / st.session_state.taxa
                entrada = preco
                st.session_state.trades = [
                    {"ent": entrada, "pnl": 0.0, "on": True, "max": 0.0, "res": "", "h": [entrada]}
                    for _ in range(10)
                ]
                st.session_state.running = True
                st.rerun()
            else:
                st.error("Não foi possível obter o preço. Verifique o CA.")
    else:
        col1, col2 = st.columns([3,1])
        col1.subheader(f"🟢 Monitorando: {st.session_state.t_nome}")
        if col2.button("PARAR BOT"):
            st.session_state.running = False
            st.rerun()

        # === FETCH E ATUALIZAÇÃO DO PREÇO ===
        preco_atual = fetch_price(st.session_state.ca)
        if preco_atual is None:
            preco_atual = st.session_state.trades[0]["ent"]  # fallback

        hora = time.strftime("%H:%M:%S")
        st.markdown(f"### Preço atual: `{preco_atual:.10f}` (às {hora})")
        st.markdown(f"**Saldo:** {'R\( ' if st.session_state.moeda == 'BRL' else ' \)'} {st.session_state.saldo * st.session_state.taxa:,.2f}")

        # === PROCESSAMENTO DAS 10 ORDENS ===
        for i, trade in enumerate(st.session_state.trades):
            if trade["on"]:
                trade["pnl"] = ((preco_atual / trade["ent"]) - 1) * 100
                if trade["pnl"] > trade["max"]:
                    trade["max"] = trade["pnl"]
                trade["h"].append(preco_atual)
                if len(trade["h"]) > 5:
                    trade["h"].pop(0)

                fechar, motivo = ia_brain(trade["pnl"], trade["max"], trade["h"])
                if fechar:
                    trade["on"] = False
                    trade["res"] = motivo
                    lucro = st.session_state.invest_usd * (trade["pnl"] / 100)
                    st.session_state.saldo += lucro
                    st.session_state.historico.append({
                        "ciclo": st.session_state.ciclo,
                        "ordem": i+1,
                        "pnl": round(trade["pnl"], 2),
                        "motivo": motivo
                    })

                cor = "#00FF00" if trade["pnl"] >= 0 else "#FF4B4B"
                status = "🔵" if trade["on"] else "🤖"
                st.markdown(f"{status} Ordem {i+1}: <b style='color:{cor}'>{trade['pnl']:+.2f}%</b> | {trade['res']}", unsafe_allow_html=True)
            else:
                st.markdown(f"🤖 Ordem {i+1}: <b style='color:#888'>{trade['pnl']:+.2f}%</b> | {trade['res']}", unsafe_allow_html=True)

        if st.session_state.historico:
            st.subheader("📜 Histórico de Trades Fechados")
            df = pd.DataFrame(st.session_state.historico)
            st.dataframe(df)

        # === AUTO UPDATE A CADA ~3 SEGUNDOS (estável no Streamlit Cloud) ===
        st.rerun()