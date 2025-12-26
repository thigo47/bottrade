import streamlit as st
import time
import requests
import pandas as pd
from datetime import datetime

# ==========================================================
# 💾 INICIALIZAÇÃO SEGURA DO ESTADO (NÃO QUEBRA NO REBOOT)
# ==========================================================
if "saldo" not in st.session_state: st.session_state.saldo = 1000.0
if "running" not in st.session_state: st.session_state.running = False
if "historico" not in st.session_state: st.session_state.historico = []
if "ciclo" not in st.session_state: st.session_state.ciclo = 1

# ==========================================================
# ⚙️ FUNÇÕES DE MOTOR (SIMPLIFICADAS PARA NÃO TRAVAR)
# ==========================================================
def fetch_price(ca):
    """Tenta buscar o preço de forma robusta"""
    try:
        # Usando a API v2 da Jupiter (mais estável para novos tokens)
        url = f"https://api.jup.ag/price/v2?ids={ca}"
        response = requests.get(url, timeout=1)
        data = response.json()
        return float(data['data'][ca]['price'])
    except:
        try:
            # Backup via DexScreener
            url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
            res = requests.get(url, timeout=1).json()
            return float(res['pairs'][0]['priceUsd'])
        except:
            return None

def get_token_info(ca):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        res = requests.get(url, timeout=2).json()
        return res['pairs'][0]['baseToken']['symbol']
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
# 🖥️ INTERFACE STREAMLIT
# ==========================================================
st.set_page_config(page_title="Sniper Pro v29", layout="wide")

# LOGIN SIMPLES
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🛡️ Acesso Sniper v29")
    senha = st.text_input("Senha de Operação", type="password")
    if st.button("Entrar"):
        if senha == "1234":
            st.session_state.auth = True
            st.rerun()
else:
    # --- BARRA LATERAL (CONTROLE DE BANCA) ---
    with st.sidebar:
        st.header("💰 Gestão Financeira")
        moeda = st.radio("Exibição:", ["USD", "BRL"])
        taxa = 5.05 if moeda == "BRL" else 1.0
        
        st.metric("Saldo", f"{'R$' if moeda == 'BRL' else '$'} {st.session_state.saldo * taxa:,.2f}")
        
        novo_s = st.number_input("Alterar Saldo", value=float(st.session_state.saldo * taxa))
        if st.button("💾 Salvar Novo Saldo"):
            st.session_state.saldo = novo_s / taxa
            st.rerun()
        
        st.divider()
        if st.button("🔴 Logout"):
            st.session_state.auth = False
            st.rerun()

    # --- TELA PRINCIPAL ---
    if not st.session_state.running:
        st.title("🚀 Sniper Pro v29.0")
        st.write("Configuração de Ciclo Inteligente")
        
        ca_input = st.text_input("CA do Token (Solana):")
        invest_input = st.number_input(f"Valor por Ordem ({moeda})", value=10.0 * taxa)
        
        if st.button("⚡ INICIAR MOTOR IA"):
            price_test = fetch_price(ca_input.strip())
            if price_test:
                st.session_state.t_nome = get_token_info(ca_input.strip())
                st.session_state.ca = ca_input.strip()
                st.session_state.invest_usd = invest_input / taxa
                st.session_state.running = True
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

        # LOOP DE CICLO
        while st.session_state.running:
            p_inicio = fetch_price(st.session_state.ca)
            if not p_inicio:
                time.sleep(1)
                continue

            # Inicia as 10 ordens
            trades = [{"ent": p_inicio, "pnl": 0.0, "on": True, "max": 0.0, "res": "", "h": [p_inicio]} for _ in range(10)]

            while any(t['on'] for t in trades) and st.session_state.running:
                p_atual = fetch_price(st.session_state.ca)
                
                if p_atual:
                    # Atualiza Visuais
                    price_area.markdown(f"### Preço Atual: `{p_atual:.10f}`")
                    saldo_area.markdown(f"**Banca:** {'R$' if moeda == 'BRL' else '$'} {st.session_state.saldo * taxa:,.2f}")
                    
                    for i, t in enumerate(trades):
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
                                # Atualiza o saldo real no st.session_state
                                lucro_usd = (st.session_state.invest_usd * (t['pnl']/100))
                                st.session_state.saldo += lucro_usd

                            # Renderiza as ordens
                            cor = "#00FF00" if t['pnl'] >= 0 else "#FF4B4B"
                            status_txt = "🔵" if t['on'] else "🤖"
                            order_slots[i].markdown(f"{status_txt} Ordem {i+1}: <b style='color:{cor}'>{t['pnl']:+.2f}%</b> | {t['res']}", unsafe_allow_html=True)
                
                time.sleep(0.1) # Pequena pausa para o Streamlit processar a interface

            st.session_state.ciclo += 1


