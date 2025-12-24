import streamlit as st
import time
import requests
import pandas as pd
import json
import os

# ==========================================================
# 💾 SISTEMA DE PERSISTÊNCIA (DATABASE JSON)
# ==========================================================
DB_FILE = "user_data.json"

def carregar_dados():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {
        "saldo_usd": 1000.0,
        "resultados_ciclos": [],
        "ciclo_atual": 1
    }

def salvar_dados():
    dados = {
        "saldo_usd": st.session_state.saldo_usd,
        "resultados_ciclos": st.session_state.resultados_ciclos,
        "ciclo_atual": st.session_state.ciclo_atual
    }
    with open(DB_FILE, "w") as f:
        json.dump(dados, f)

# ==========================================================
# 🔐 SISTEMA DE LOGIN
# ==========================================================
def tela_login():
    st.title("🔐 Acesso Sniper Pro")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if usuario == "admin" and senha == "1234": # Altere aqui
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Credenciais incorretas")

# ==========================================================
# 🔑 INICIALIZAÇÃO DO ESTADO
# ==========================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    db = carregar_dados()
    if "saldo_usd" not in st.session_state:
        st.session_state.saldo_usd = db["saldo_usd"]
        st.session_state.resultados_ciclos = db["resultados_ciclos"]
        st.session_state.ciclo_atual = db["ciclo_atual"]
        st.session_state.running = False
        st.session_state.ultimo_preco_track = 0.0

# ==========================================================
# ⚙️ FUNÇÕES DO BOT (Mantidas as correções anteriores)
# ==========================================================
def formatar_moeda(valor_usd, moeda_ref):
    taxa = 5.05 if moeda_ref == "BRL" else 1.0
    simbolo = "R$" if moeda_ref == "BRL" else "$"
    return f"{simbolo} {valor_usd * taxa:,.2f}"

def check_preco(pair_addr):
    try:
        url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{pair_addr}"
        res = requests.get(url, timeout=1).json()
        return float(res['pair']['priceUsd'])
    except: return None

# ==========================================================
# 🖥️ INTERFACE PRINCIPAL
# ==========================================================
if not st.session_state.logged_in:
    tela_login()
else:
    st.set_page_config(page_title="Sniper Pro v16", layout="wide")

    with st.sidebar:
        st.header("👤 Perfil: Admin")
        if st.button("Sair / Logout"):
            st.session_state.logged_in = False
            st.rerun()
            
        st.divider()
        modo_operacao = st.toggle("🚀 MODO REAL", value=False)
        moeda_ref = st.radio("Moeda:", ["USD", "BRL"])
        taxa_view = 5.05 if moeda_ref == "BRL" else 1.0
        
        st.metric("Saldo", formatar_moeda(st.session_state.saldo_usd, moeda_ref))
        
        val_banca = st.number_input(f"Ajustar Banca ({moeda_ref})", value=st.session_state.saldo_usd * taxa_view)
        if st.button("Salvar Novo Saldo"):
            st.session_state.saldo_usd = val_banca / taxa_view
            salvar_dados()
            st.rerun()

        st.divider()
        alvo_gain = st.slider("Alvo %", 0.5, 20.0, 2.5)
        stop_cfg = st.slider("Stop %", 0.5, 15.0, 3.0)

    # --- LÓGICA DE OPERAÇÃO ---
    if not st.session_state.running:
        st.title("🛡️ Sniper Pro v16.0")
        ca = st.text_input("Token CA:")
        invest_input = st.number_input(f"Valor Ordem ({moeda_ref}):", value=10.0 * taxa_view)
        
        if st.button("⚡ INICIAR ESTRATÉGIA", use_container_width=True, type="primary"):
            # Lógica de início omitida aqui para brevidade, mas segue a v15.1
            st.session_state.running = True
            st.rerun()
    else:
        # Interface de Trading (Recuperada da v15.1)
        st.markdown(f"**Saldo: {formatar_moeda(st.session_state.saldo_usd, moeda_ref)}**")
        
        # ... (Resto do código de trading da v15.1 aqui) ...
        # IMPORTANTE: Dentro do loop de fechamento de trade, chame salvar_dados()
        # st.session_state.saldo_usd += liq
        # salvar_dados() 
