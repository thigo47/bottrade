import streamlit as st
import time
import requests
import pandas as pd
from datetime import datetime

# ==========================================================
# 💾 BANCO DE DADOS (PERSISTENTE NO CACHE)
# ==========================================================
if "saldo" not in st.session_state:
    st.session_state.saldo = 1000.0
if "historico" not in st.session_state:
    st.session_state.historico = []
if "ciclo" not in st.session_state:
    st.session_state.ciclo = 1

# ==========================================================
# ⚙️ MOTOR DE PREÇO HÍBRIDO (JUPITER + DEX)
# ==========================================================
def buscar_preco_realtime(ca):
    # Tentativa 1: Jupiter (Mais rápido)
    try:
        url = f"https://api.jup.ag/price/v2?ids={ca}"
        res = requests.get(url, timeout=1).json()
        if res.get('data') and res['data'].get(ca):
            return float(res['data'][ca]['price'])
    except: pass

    # Tentativa 2: DexScreener (Backup estável)
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        res = requests.get(url, timeout=1).json()
        if res.get('pairs'):
            # Pega o preço do par com mais liquidez na Solana
            pair = max([p for p in res['pairs'] if p['chainId'] == 'solana'], 
                       key=lambda x: float(x['liquidity']['usd']))
            return float(pair['priceUsd'])
    except: pass
    return None

def get_token_name(ca):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        res = requests.get(url, timeout=2).json()
        return res['pairs'][0]['baseToken']['symbol']
    except: return "TOKEN"

# ==========================================================
# 🧠 CÉREBRO IA v28
# ==========================================================
def motor_ia_v28(pnl, pnl_max, h_precos):
    if len(h_precos) < 3: return False, ""
    
    # Se o lucro subir e cair 0.2% da máxima, fecha (Trailing Curto)
    if pnl_max > 1.0 and pnl < (pnl_max - 0.25):
        return True, "IA: Proteção de Ganho"
    
    # Stop Loss de Segurança
    if pnl < -2.5:
        return True, "IA: Stop Loss"
        
    # Se o preço estagnar (últimos 3 iguais) com lucro, realiza
    if pnl > 0.5 and h_precos[-1] == h_precos[-2] == h_precos[-3]:
        return True, "IA: Realização por Estagnação"
        
    return False, ""

# ==========================================================
# 🖥️ INTERFACE
# ==========================================================
st.set_page_config(page_title="Sniper Pro v28", layout="wide")

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "running" not in st.session_state: st.session_state.running = False

if not st.session_state.logged_in:
    st.title("🛡️ Sniper Pro v28 - Login")
    u = st.text_input("Usuário")
    p = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if u == "admin" and p == "1234":
            st.session_state.logged_in = True
            st.rerun()
else:
    # --- SIDEBAR (GESTÃO DE SALDO) ---
    with st.sidebar:
        st.header("💰 Gestão de Banca")
        moeda = st.radio("Moeda:", ["USD", "BRL"])
        taxa = 5.05 if moeda == "BRL" else 1.0
        
        st.metric("Saldo Atual", f"{'R$' if moeda == 'BRL' else '$'} {st.session_state.saldo * taxa:,.2f}")
        
        novo_saldo = st.number_input("Ajustar Saldo Manualmente", value=float(st.session_state.saldo * taxa))
        if st.button("💾 Atualizar Saldo"):
            st.session_state.saldo = novo_saldo / taxa
            st.success("Saldo atualizado!")
            st.rerun()

        st.divider()
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.rerun()

    # --- CORPO PRINCIPAL ---
    if not st.session_state.running:
        st.title("🚀 Sniper Pro v28.0")
        ca_input = st.text_input("CA do Token (Solana):", placeholder="Insira o Mint Address...")
        invest_input = st.number_input(f"Investimento por Ordem ({moeda})", value=10.0 * taxa)

        if st.button("⚡ INICIAR OPERAÇÃO INTELIGENTE"):
            with st.spinner("Conectando aos Nodes da Solana..."):
                p_atual = buscar_preco_realtime(ca_input.strip())
                if p_atual:
                    st.session_state.t_nome = get_token_name(ca_input.strip())
                    st.session_state.ca = ca_input.strip()
                    st.session_state.invest_usd = invest_input / taxa
                    st.session_state.running = True
                    st.rerun()
                else:
                    st.error("Erro: Não foi possível ler o preço desse token. Verifique o CA.")
    else:
        # PAINEL OPERACIONAL
        c1, c2 = st.columns([3, 1])
        c1.subheader(f"🟢 Operando: {st.session_state.t_nome}")
        if c2.button("🛑 PARAR BOT", use_container_width=True):
            st.session_state.running = False
            st.rerun()

        price_display = c1.empty()
        saldo_display = c2.empty()
        slots = [st.empty() for _ in range(10)]

        # LOOP PRINCIPAL
        while st.session_state.running:
            p_start = buscar_preco_realtime(st.session_state.ca)
            if not p_start:
                time.sleep(1)
                continue
                
            trades = [{"ent": p_start, "pnl": 0.0, "on": True, "max": 0.0, "res": "", "h": [p_start]} for _ in range(10)]
            
            while any(t['on'] for t in trades) and st.session_state.running:
                p_now = buscar_preco_realtime(st.session_state.ca)
                if p_now:
                    # Atualiza Preço e Saldo na tela
                    price_display.markdown(f"## Preço: `{p_now:.10f}`")
                    saldo_display.metric("Banca em Tempo Real", f"{st.session_state.saldo * taxa:,.2f}")
                    
                    for i, t in enumerate(trades):
                        if t['on']:
                            t['pnl'] = ((p_now / t['ent']) - 1) * 100
                            if t['pnl'] > t['max']: t['max'] = t['pnl']
                            t['h'].append(p_now)
                            if len(t['h']) > 5: t['h'].pop(0)

                            # DECISÃO DA IA
                            fechar, motivo = motor_ia_v28(t['pnl'], t['max'], t['h'])
                            
                            if fechar:
                                t['on'] = False
                                t['res'] = motivo
                                # Atualiza o saldo global
                                lucro_ordem = (st.session_state.invest_usd * (t['pnl']/100))
                                st.session_state.saldo += lucro_ordem
                            
                            cor = "#00FF00" if t['pnl'] >= 0 else "#FF4B4B"
                            status = "🔵" if t['on'] else "🤖"
                            slots[i].markdown(f"{status} Ordem {i+1}: <span style='color:{cor}'>{t['pnl']:+.2f}%</span> | {t['res']}", unsafe_allow_html=True)
                
                time.sleep(0.1) # Intervalo para não travar o Streamlit
            
            st.session_state.ciclo += 1
