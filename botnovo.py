import streamlit as st
import time
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# ==========================================================
# 🔑 CONFIGURAÇÕES DE ALTA FIDELIDADE
# ==========================================================
if "resultados_trades" not in st.session_state:
    st.session_state.resultados_trades = []
if "running" not in st.session_state:
    st.session_state.running = False
if "saldo_demo" not in st.session_state:
    st.session_state.saldo_demo = 1000.0

TAXA_EXECUCAO_SIMULADA = 0.01 

# ==========================================================
# ⚙️ MOTORES DE ANALISE
# ==========================================================
def obter_dados(address):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
        res = requests.get(url, timeout=5).json()
        pair = res['pairs'][0]
        return {
            "nome": pair['baseToken']['symbol'].upper(),
            "preco": float(pair['priceUsd']),
            "liquidez": pair.get('liquidity', {}).get('usd', 0)
        }
    except: return None

def checar_tendencia(precos):
    """Retorna True se a tendência for de alta (Média Curta > Média Longa)"""
    if len(precos) < 10: return True # Sem dados suficientes, assume neutro
    ma_curta = sum(precos[-5:]) / 5
    ma_longa = sum(precos[-10:]) / 10
    return ma_curta > ma_longa

# ==========================================================
# 🖥️ INTERFACE
# ==========================================================
st.set_page_config(page_title="Sniper Pro Terminal", layout="wide")

with st.sidebar:
    st.header("⚡ Configurações")
    moeda_ref = st.radio("Moeda:", ["USD", "BRL"])
    taxa_c = 5.05 if moeda_ref == "BRL" else 1.0
    
    st.divider()
    st.subheader("🤖 Estratégia")
    alvo_gain = st.slider("Alvo de Gain (%)", 1.0, 10.0, 2.5)
    stop_inicial = st.slider("Stop Loss Inicial (%)", 1.0, 10.0, 3.0)
    ativar_trailing = st.checkbox("Ativar Trailing Stop", value=True)
    
    if st.button("Resetar Saldo"):
        st.session_state.saldo_demo = 1000.0
        st.session_state.resultados_trades = []
        st.rerun()

# --- TELA INICIAL ---
if not st.session_state.running:
    st.title("🛡️ Sniper Pro - Trend Filter")
    st.metric("Saldo", f"${st.session_state.saldo_demo:,.2f}")
    
    ca = st.text_input("Insira o CA do Token:")
    valor_invest = st.number_input(f"Investimento ({moeda_ref}):", value=10.0)
    
    if st.button("🚀 INICIAR OPERAÇÕES", use_container_width=True, type="primary"):
        if ca:
            st.session_state.ca_ativo = ca
            st.session_state.invest_usd = valor_invest / taxa_c
            st.session_state.running = True
            st.rerun()

# --- TELA DE EXECUÇÃO ---
else:
    st.header(f"🛰️ Executando Estratégia")
    if st.button("🛑 PARAR AGORA", use_container_width=True):
        st.session_state.running = False
        st.rerun()

    m1, m2, m3 = st.columns(3)
    pnl_m = m1.empty()
    status_m = m2.empty()
    banca_m = m3.empty()
    
    grafico_place = st.empty()
    t_resumo = st.empty()

    ca_ativo = st.session_state.ca_ativo
    invest_usd = st.session_state.invest_usd
    precos_gerais = [] # Para a média móvel

    for t_num in range(len(st.session_state.resultados_trades) + 1, 11):
        if not st.session_state.running: break
        
        # 1. FILTRO DE TENDÊNCIA ANTES DE ENTRAR
        buscando_entrada = True
        while buscando_entrada and st.session_state.running:
            d = obter_dados(ca_ativo)
            if d:
                precos_gerais.append(d['preco'])
                tendencia_alta = checar_tendencia(precos_gerais)
                
                if tendencia_alta:
                    p_entrada = d['preco']
                    st.session_state.token_nome = d['nome']
                    buscando_entrada = False
                else:
                    status_m.warning("📉 Tendência de Queda: Aguardando...")
                    time.sleep(2)
            else: time.sleep(1)

        # 2. TRADE EM CURSO
        hist_trade = [p_entrada]
        topo_atingido = p_entrada
        stop_atual = p_entrada * (1 - (stop_inicial / 100))

        while st.session_state.running:
            d_atual = obter_dados(ca_ativo)
            if d_atual:
                p_atual = d_atual['preco']
                hist_trade.append(p_atual)
                pnl_bruto = ((p_atual / p_entrada) - 1) * 100
                
                # Atualiza Topo e Trailing Stop
                if p_atual > topo_atingido:
                    topo_atingido = p_atual
                    # Se subiu 1%, o stop loss sobe junto (Trailing)
                    if ativar_trailing and pnl_bruto > 1.0:
                        novo_stop = topo_atingido * (1 - (stop_inicial / 100))
                        if novo_stop > stop_atual:
                            stop_atual = novo_stop

                # UI
                pnl_m.metric(f"Trade #{t_num} ({st.session_state.token_nome})", f"{pnl_bruto:+.2f}%")
                status_m.info("✅ Posição Aberta" if pnl_bruto > 0 else "❌ Posição em Loss")
                banca_m.metric("Banca", f"${st.session_state.saldo_demo:,.2f}")

                with grafico_place.container():
                    fig = go.Figure(data=[go.Scatter(y=hist_trade[-50:], mode='lines', line=dict(color='#00ff00' if pnl_bruto > 0 else '#ff0000'))])
                    fig.update_layout(template="plotly_dark", height=200, margin=dict(l=0,r=0,t=0,b=0))
                    st.plotly_chart(fig, use_container_width=True, key=f"tr_{t_num}_{time.time()}")

                # LÓGICA DE SAÍDA
                lucro_liquido = (invest_usd * (pnl_bruto/100)) - (invest_usd * TAXA_EXECUCAO_SIMULADA)
                
                if pnl_bruto >= alvo_gain: # Take Profit
                    motivo = "ALVO ATINGIDO"
                    break
                if p_atual <= stop_atual: # Stop Loss ou Trailing Stop
                    motivo = "STOP LOSS / TRAILING"
                    break
            
            time.sleep(0.6)

        # Finaliza o Trade
        if st.session_state.running:
            st.session_state.saldo_demo += lucro_liquido
            st.session_state.resultados_trades.insert(0, {
                "ID": f"#{t_num}",
                "TOKEN": st.session_state.token_nome,
                "RESULT": "WIN" if lucro_liquido > 0 else "LOSS",
                "MOTIVO": motivo,
                "VALOR NET": f"${lucro_liquido:+.2f}",
                "PNL %": f"{pnl_bruto:+.2f}%"
            })
            t_resumo.table(pd.DataFrame(st.session_state.resultados_trades))

    st.session_state.running = False
    st.rerun()
