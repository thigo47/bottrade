import streamlit as st
import time
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# ==========================================================
# 🔑 ESTADO DA SESSÃO E CONFIGURAÇÕES
# ==========================================================
if "sessao_http" not in st.session_state:
    st.session_state.sessao_http = requests.Session()
if "resultados_trades" not in st.session_state:
    st.session_state.resultados_trades = []
if "running" not in st.session_state:
    st.session_state.running = False
if "saldo_demo" not in st.session_state:
    st.session_state.saldo_demo = 1000.0

TAXA_EXECUCAO_SIMULADA = 0.01 

# ==========================================================
# ⚙️ FUNÇÕES DE APOIO
# ==========================================================
def formatar_moeda(valor, moeda_ref):
    if moeda_ref == "BRL":
        return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    return f"$ {valor:,.2f}"

def obter_dados(address):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
        res = st.session_state.sessao_http.get(url, timeout=5).json()
        pair = res['pairs'][0]
        return {
            "nome": pair['baseToken']['symbol'].upper(),
            "preco": float(pair['priceUsd']),
            "liquidez": pair.get('liquidity', {}).get('usd', 0)
        }
    except: return None

def checar_tendencia(precos):
    if len(precos) < 10: return True
    ma_curta = sum(precos[-5:]) / 5
    ma_longa = sum(precos[-10:]) / 10
    return ma_curta > ma_longa

# ==========================================================
# 🖥️ INTERFACE COMPLETA
# ==========================================================
st.set_page_config(page_title="Sniper Bot Pro Terminal", layout="wide")

with st.sidebar:
    st.header("⚙️ Configurações")
    
    # 1. EDITAR SALDO
    novo_saldo = st.number_input("Editar Saldo Carteira:", value=float(st.session_state.saldo_demo))
    if st.button("Atualizar Saldo"):
        st.session_state.saldo_demo = novo_saldo
        st.rerun()
    
    st.divider()
    # 2. SELETOR DE MOEDA
    moeda_ref = st.radio("Exibir valores em:", ["USD", "BRL"])
    taxa_c = 5.05 if moeda_ref == "BRL" else 1.0
    
    st.divider()
    # 3. ESTRATÉGIA
    st.subheader("🤖 Estratégia")
    alvo_gain = st.slider("Alvo de Gain (%)", 1.0, 10.0, 2.5)
    stop_inicial = st.slider("Stop Loss Inicial (%)", 1.0, 10.0, 3.0)
    ativar_trailing = st.checkbox("Ativar Trailing Stop", value=True)
    
    if st.button("Limpar Histórico"):
        st.session_state.resultados_trades = []
        st.session_state.running = False
        st.rerun()

# --- TELA INICIAL ---
if not st.session_state.running:
    st.title("🛡️ Sniper Pro Terminal")
    st.metric("Banca Disponível", formatar_moeda(st.session_state.saldo_demo * taxa_c, moeda_ref))
    
    ca = st.text_input("Insira o Mint Address (CA):")
    valor_invest = st.number_input(f"Investimento por Ordem ({moeda_ref}):", value=10.0)
    
    if st.button("🚀 INICIAR OPERAÇÕES", use_container_width=True, type="primary"):
        if ca:
            st.session_state.ca_ativo = ca
            st.session_state.invest_usd = valor_invest / taxa_c
            st.session_state.running = True
            st.rerun()

# --- TELA DE EXECUÇÃO ---
else:
    st.header(f"🛰️ Operando: {st.session_state.get('token_nome', 'Buscando...')}")
    
    if st.button("🛑 PARAR BOT AGORA", use_container_width=True):
        st.session_state.running = False
        st.rerun()

    m1, m2, m3 = st.columns(3)
    pnl_m = m1.empty()
    status_m = m2.empty()
    banca_m = m3.empty()
    
    grafico_linha_place = st.empty()
    
    st.divider()
    # ÁREA DO RESUMO (Tabela e Pizza Juntos)
    col_tab, col_pie = st.columns([2, 1])
    t_resumo_place = col_tab.empty()
    p_pizza_place = col_pie.empty()

    ca_ativo = st.session_state.ca_ativo
    invest_usd = st.session_state.invest_usd
    precos_gerais = [] 

    for t_num in range(len(st.session_state.resultados_trades) + 1, 11):
        if not st.session_state.running: break
        
        # FILTRO DE TENDÊNCIA
        buscando = True
        while buscando and st.session_state.running:
            d = obter_dados(ca_ativo)
            if d:
                precos_gerais.append(d['preco'])
                if checar_tendencia(precos_gerais):
                    p_entrada = d['preco']
                    st.session_state.token_nome = d['nome']
                    buscando = False
                else:
                    status_m.warning("📉 Aguardando Tendência de Alta...")
                    time.sleep(2)
            else: time.sleep(1)

        # TRADE ATIVO
        hist_trade = [p_entrada]
        topo_atingido = p_entrada
        stop_atual = p_entrada * (1 - (stop_inicial / 100))

        while st.session_state.running:
            atual = obter_dados(ca_ativo)
            if atual:
                p_atual = atual['preco']
                hist_trade.append(p_atual)
                pnl_bruto = ((p_atual / p_entrada) - 1) * 100
                
                # Trailing Stop Loss
                if p_atual > topo_atingido:
                    topo_atingido = p_atual
                    if ativar_trailing and pnl_bruto > 1.0:
                        novo_stop = topo_atingido * (1 - (stop_inicial / 100))
                        if novo_stop > stop_atual: stop_atual = novo_stop

                # Métricas
                lucro_liq_usd = (invest_usd * (pnl_bruto/100)) - (invest_usd * TAXA_EXECUCAO_SIMULADA)
                pnl_m.metric(f"Trade #{t_num}", f"{pnl_bruto:+.2f}%")
                status_m.info(f"Preço: ${p_atual:.8f}")
                banca_m.metric("Banca", formatar_moeda(st.session_state.saldo_demo * taxa_c, moeda_ref))

                # Gráfico de Linha
                with grafico_linha_place.container():
                    fig_l = go.Figure(data=[go.Scatter(y=hist_trade, mode='lines', line=dict(color='#00ff00' if pnl_bruto > 0 else '#ff0000', width=3))])
                    fig_l.update_layout(template="plotly_dark", height=250, margin=dict(l=0,r=0,t=0,b=0))
                    st.plotly_chart(fig_l, use_container_width=True, key=f"l_{t_num}_{time.time()}")

                # Atualizar Tabela e Pizza (Histórico)
                if st.session_state.resultados_trades:
                    df_res = pd.DataFrame(st.session_state.resultados_trades)
                    t_resumo_place.table(df_res)
                    
                    # Pizza
                    counts = df_res['RESULT'].value_counts()
                    fig_p = go.Figure(data=[go.Pie(labels=counts.index, values=counts.values, hole=.4, marker_colors=['#00ff00', '#ff0000'])])
                    fig_p.update_layout(template="plotly_dark", height=220, margin=dict(l=0,r=0,t=0,b=0), showlegend=True)
                    p_pizza_place.plotly_chart(fig_p, use_container_width=True, key=f"p_{t_num}_{time.time()}")

                # Condições de Saída
                if pnl_bruto >= alvo_gain:
                    motivo = "ALVO"
                    break
                if p_atual <= stop_atual:
                    motivo = "STOP"
                    break
            time.sleep(0.7)

        if st.session_state.running:
            st.session_state.saldo_demo += lucro_liq_usd
            st.session_state.resultados_trades.insert(0, {
                "ID": f"#{t_num}",
                "RESULT": "WIN" if lucro_liq_usd > 0 else "LOSS",
                "VALOR": formatar_moeda(lucro_liq_usd * taxa_c, moeda_ref),
                "PNL %": f"{pnl_bruto:+.2f}%",
                "MOTIVO": motivo
            })
    st.session_state.running = False
    st.rerun()
