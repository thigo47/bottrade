import streamlit as st
import time
import requests
import pandas as pd
from datetime import datetime
import threading
import os
import functools

# ==========================================================
# 💾 INICIALIZAÇÃO SEGURA DO ESTADO (NÃO QUEBRA NO REBOOT)
# ==========================================================
if "saldo" not in st.session_state: st.session_state.saldo = 1000.0
if "running" not in st.session_state: st.session_state.running = False
if "historico" not in st.session_state: st.session_state.historico = []
if "ciclo" not in st.session_state: st.session_state.ciclo = 1
if "auth" not in st.session_state: st.session_state.auth = False
if "p_atual" not in st.session_state: st.session_state.p_atual = None

# ==========================================================
# ⚙️ FUNÇÕES DE MOTOR (SIMPLIFICADAS PARA NÃO TRAVAR)
# ==========================================================
@functools.lru_cache(maxsize=128)
def fetch_price(ca, _cache_buster=None):
    """Tenta buscar o preço de forma robusta com cache-buster para refresh."""
    try:
        # Jupiter API
        url = f"https://api.jup.ag/price/v2?ids={ca}"
        response = requests.get(url, timeout=5)
        data = response.json()
        price = float(data.get('data', {}).get(ca, {}).get('price', None))
        if price:
            return price
    except Exception as e:
        print(f"Jupiter error: {e}")
    try:
        # Backup DexScreener
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        res = requests.get(url, timeout=5).json()
        return float(res.get('pairs', [{}])[0].get('priceUsd', None))
    except Exception as e:
        print(f"DexScreener error: {e}")
        return None

def get_token_info(ca):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        res = requests.get(url, timeout=5).json()
        return res.get('pairs', [{}])[0].get('baseToken', {}).get('symbol', 'TOKEN')
    except:
        return "TOKEN"

# ==========================================================
# 🧠 CÉREBRO IA v29 (AUTÔNOMO)
# ==========================================================
def ia_brain(pnl, pnl_max, h_precos):
    """Decisões baseadas em micro-movimentos"""
    if len(h_precos) < 3: return False, ""

    # Proteção de Lucro: Se subiu 1% e caiu 0.2% do topo, fecha.
    if pnl_max > 1.0 and (pnl < pnl_max - 0.2):
        return True, "IA: Realização de Lucro"

    # Stop Loss Dinâmico
    if pnl < -2.0:
        return True, "IA: Stop Preventivo"

    return False, ""

# ==========================================================
# 💱 FUNÇÃO PARA CÂMBIO DINÂMICO
# ==========================================================
@st.cache_data(ttl=3600)  # Cache por 1 hora
def get_exchange_rate(base='USD', target='BRL'):
    try:
        url = f"https://open.er-api.com/v6/latest/{base}"
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get('result') == 'success':
            return float(data['rates'].get(target, 5.05))
        else:
            return 5.05  # Fallback
    except:
        return 5.05  # Fallback em caso de erro

# ==========================================================
# 🔄 LOOP DE MONITORAMENTO EM THREAD COM POLLING PARA ESTABILIDADE
# ==========================================================
def monitoring_loop():
    while st.session_state.running:
        # Fetch preço com cache-buster
        cache_buster = time.time()
        p_atual = fetch_price(st.session_state.ca, cache_buster)
        if p_atual:
            st.session_state.p_atual = p_atual
            print(f"Preço atualizado: {p_atual}")  # Log para debug
        else:
            print("Falha ao fetch preço")  # Log erro
        time.sleep(0.5)  # Polling a cada 0.5s para capturar variações (ajuste se necessário)

    # Após parar, incrementa ciclo
    st.session_state.ciclo += 1

def update_ui_from_price():
    p_atual = st.session_state.p_atual
    if p_atual:
        st.session_state.price_text = f"### Preço Atual: `{p_atual:.10f}`"
        st.session_state.saldo_text = f"**Banca:** {'R\( ' if st.session_state.moeda == 'BRL' else ' \)'} {st.session_state.saldo * st.session_state.taxa:,.2f}"

        for i, t in enumerate(st.session_state.trades):
            if t['on']:
                # Cálculo de PNL
                t['pnl'] = ((p_atual / t['ent']) - 1) * 100
                if t['pnl'] > t['max']: t['max'] = t['pnl']
                t['h'].append(p_atual)
                if len(t['h']) > 5: t['h'].pop(0)

                # DECISÃO DA IA
                fechar, motivo = ia_brain(t['pnl'], t['max'], t['h'])

                if fechar:
                    t['on'] = False
                    t['res'] = motivo
                    # Atualiza o saldo real
                    lucro_usd = (st.session_state.invest_usd * (t['pnl']/100))
                    st.session_state.saldo += lucro_usd
                    # Log no histórico
                    st.session_state.historico.append({
                        'ciclo': st.session_state.ciclo,
                        'ordem': i+1,
                        'pnl': t['pnl'],
                        'motivo': motivo
                    })

                # Atualiza texto da ordem
                cor = "#00FF00" if t['pnl'] >= 0 else "#FF4B4B"
                status_txt = "🔵" if t['on'] else "🤖"
                st.session_state.order_texts[i] = f"{status_txt} Ordem {i+1}: <b style='color:{cor}'>{t['pnl']:+.2f}%</b> | {t['res']}"

# ==========================================================
# 🖥️ INTERFACE STREAMLIT
# ==========================================================
st.set_page_config(page_title="Sniper Pro v29", layout="wide")

# Senha de ambiente (para GitHub, use st.secrets ou os.getenv)
SENHA = os.getenv('SNIPER_SENHA', '1234')  # Defina no .env ou GitHub Secrets

if not st.session_state.auth:
    st.title("🛡️ Acesso Sniper v29")
    senha = st.text_input("Senha de Operação", type="password")
    if st.button("Entrar"):
        if senha == SENHA:
            st.session_state.auth = True
            st.rerun()
else:
    # --- BARRA LATERAL (CONTROLE DE BANCA) ---
    with st.sidebar:
        st.header("💰 Gestão Financeira")
        st.session_state.moeda = st.radio("Exibição:", ["USD", "BRL"])
        st.session_state.taxa = 1.0 if st.session_state.moeda == "USD" else get_exchange_rate()

        st.metric("Saldo", f"{'R\( ' if st.session_state.moeda == 'BRL' else ' \)'} {st.session_state.saldo * st.session_state.taxa:,.2f}")

        novo_s = st.number_input("Alterar Saldo", value=float(st.session_state.saldo * st.session_state.taxa))
        if st.button("💾 Salvar Novo Saldo"):
            st.session_state.saldo = novo_s / st.session_state.taxa
            st.rerun()

        st.divider()
        if st.button("🔴 Logout"):
            st.session_state.auth = False
            st.rerun()

        st.markdown('Rates by <a href="https://www.exchangerate-api.com">Exchange Rate API</a>', unsafe_allow_html=True)

    # --- TELA PRINCIPAL ---
    if not st.session_state.running:
        st.title("🚀 Sniper Pro v29.0")
        st.write("Configuração de Ciclo Inteligente")

        ca_input = st.text_input("CA do Token (Solana):")
        invest_input = st.number_input(f"Valor por Ordem ({st.session_state.moeda})", value=10.0 * st.session_state.taxa)

        if st.button("⚡ INICIAR MOTOR IA"):
            price_test = fetch_price(ca_input.strip())
            if price_test:
                st.session_state.t_nome = get_token_info(ca_input.strip())
                st.session_state.ca = ca_input.strip()
                st.session_state.invest_usd = invest_input / st.session_state.taxa
                st.session_state.p_atual = price_test

                # Inicia trades
                p_inicio = price_test
                st.session_state.trades = [{"ent": p_inicio, "pnl": 0.0, "on": True, "max": 0.0, "res": "", "h": [p_inicio]} for _ in range(10)]

                # Prepara placeholders texts
                st.session_state.price_text = ""
                st.session_state.saldo_text = ""
                st.session_state.order_texts = [""] * 10

                st.session_state.running = True
                # Inicia thread
                thread = threading.Thread(target=monitoring_loop, daemon=True)
                thread.start()
                st.rerun()
            else:
                st.error("Erro: Não foi possível detectar o preço. Verifique o CA.")

    else:
        # --- MODO OPERAÇÃO ATIVA ---
        col_title, col_btn = st.columns([3, 1])
        col_title.subheader(f"🟢 Monitorando: {st.session_state.t_nome}")
        if col_btn.button("🛑 DESATIVAR BOT", use_container_width=True):
            st.session_state.running = False
            st.rerun()

        # Áreas de atualização dinâmica
        price_area = st.empty()
        saldo_area = st.empty()
        order_slots = [st.empty() for _ in range(10)]

        # Atualiza UI com session_state (rerun chamará isso novamente)
        update_ui_from_price()

        price_area.markdown(st.session_state.price_text)
        saldo_area.markdown(st.session_state.saldo_text)
        for i, slot in enumerate(order_slots):
            slot.markdown(st.session_state.order_texts[i], unsafe_allow_html=True)

        # Histórico como tabela
        if st.session_state.historico:
            st.subheader("📜 Histórico de Trades")
            df_hist = pd.DataFrame(st.session_state.historico)
            st.dataframe(df_hist)

        # Força rerun para updates
        time.sleep(0.05)  # Pequena pausa para responsividade
        st.rerun()