import streamlit as st
import time
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# ==========================================================
# 🔑 ESTADO DA SESSÃO
# ==========================================================
if "resultados_trades" not in st.session_state:
    st.session_state.resultados_trades = []
if "running" not in st.session_state:
    st.session_state.running = False
if "saldo_demo" not in st.session_state:
    st.session_state.saldo_demo = 1000.0

TAXA_EXECUCAO_SIMULADA = 0.01 

# ==========================================================
# ⚙️ MOTORES
# ==========================================================
def formatar_moeda(valor, moeda_ref):
    taxa = 5.05 if moeda_ref == "BRL" else 1.0
    v = valor * taxa
    if moeda_ref == "BRL":
        return f"R$ {v:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    return f"$ {v:,.2f}"

def obter_dados_fast(address):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
        res = requests.get(url, timeout=2).json()
        pair = res['pairs'][0]
        return {"nome": pair['baseToken']['symbol'].upper(), "preco": float(pair['priceUsd'])}
    except: return None

# ==========================================================
# 🖥️ INTERFACE
# ==========================================================
st.set_page_config(page_title="Sniper Parallel v8", layout="wide")

with st.sidebar:
    st.header("⚙️ Painel Multi-Trade")
    st.session_state.saldo_demo = st.number_input("Editar Banca (USD):", value=float(st.session_state.saldo_demo))
    moeda_ref = st.radio("Moeda de Exibição:", ["USD", "BRL"])
    
    st.divider()
    alvo_gain = st.slider("Alvo Gain (%)", 1.0, 20.0, 3.0)
    stop_loss = st.slider("Stop Loss (%)", 1.0, 15.0, 3.0)
    
    if st.button("Zerar Histórico"):
        st.session_state.resultados_trades = []
        st.rerun()

if not st.session_state.running:
    st.title("🚀 Sniper Parallel Hunter - 10 Simultâneos")
    st.subheader(f"Banca: {formatar_moeda(st.session_state.saldo_demo, moeda_ref)}")
    
    ca = st.text_input("CA do Token para operar em massa:")
    invest_por_slot = st.number_input("Investimento por cada Slot (USD):", value=10.0)
    
    if st.button("🔥 INICIAR 10 TRADES EM PARALELO", use_container_width=True, type="primary"):
        if ca:
            st.session_state.ca_ativo = ca
            st.session_state.invest_slot = invest_por_slot
            st.session_state.running = True
            st.rerun()
else:
    # --- TELA DE EXECUÇÃO MULTI-SLOT ---
    st.header(f"🛰️ Operando 10 Slots em Paralelo")
    if st.button("🛑 PARAR TUDO", use_container_width=True):
        st.session_state.running = False
        st.rerun()

    # Criar 10 colunas (ou 5x2) para os trades simultâneos
    cols = st.columns(5)
    cols2 = st.columns(5)
    slots = cols + cols2
    
    # Placeholders para cada slot
    placeholders = [s.empty() for s in slots]
    
    # Área de Resumo Geral abaixo
    st.divider()
    c_tab, c_pie = st.columns([2, 1])
    t_place = c_tab.empty()
    p_place = c_pie.empty()

    # Inicialização dos 10 Trades
    ca_ativo = st.session_state.ca_ativo
    dados_init = obter_dados_fast(ca_ativo)
    if not dados_init:
        st.error("Erro ao conectar. Verifique o CA.")
        st.session_state.running = False
        time.sleep(2)
        st.rerun()

    # Estrutura para controlar os 10 trades ativos
    trades_ativos = []
    for i in range(10):
        trades_ativos.append({
            "id": i + 1,
            "p_entrada": dados_init['preco'],
            "topo": dados_init['preco'],
            "status": "OPERANDO",
            "pnl": 0.0,
            "hist": [dados_init['preco']]
        })

    # Loop de Execução Paralela
    while st.session_state.running and any(t['status'] == "OPERANDO" for t in trades_ativos):
        dados_atual = obter_dados_fast(ca_ativo)
        if not dados_atual: continue
        
        preco_agora = dados_atual['preco']
        
        for i, t in enumerate(trades_ativos):
            if t['status'] == "OPERANDO":
                t['hist'].append(preco_agora)
                t['pnl'] = ((preco_agora / t['p_entrada']) - 1) * 100
                
                # Regra de Saída
                if t['pnl'] >= alvo_gain:
                    t['status'] = "WIN"
                    lucro = (st.session_state.invest_slot * (t['pnl']/100)) - (st.session_state.invest_slot * TAXA_EXECUCAO_SIMULADA)
                    st.session_state.saldo_demo += lucro
                    st.session_state.resultados_trades.insert(0, {"SLOT": t['id'], "RESULT": "WIN", "PNL": f"{t['pnl']:.2f}%"})
                
                elif t['pnl'] <= -stop_loss:
                    t['status'] = "LOSS"
                    preju = (st.session_state.invest_slot * (t['pnl']/100)) - (st.session_state.invest_slot * TAXA_EXECUCAO_SIMULADA)
                    st.session_state.saldo_demo += preju
                    st.session_state.resultados_trades.insert(0, {"SLOT": t['id'], "RESULT": "LOSS", "PNL": f"{t['pnl']:.2f}%"})

                # Atualizar visual de cada slot
                color = "green" if t['pnl'] > 0 else "red"
                with placeholders[i].container():
                    st.markdown(f"**Slot {t['id']}**")
                    st.markdown(f"<h3 style='color:{color};'>{t['pnl']:+.2f}%</h3>", unsafe_allow_html=True)
                    if t['status'] != "OPERANDO":
                        st.write(f"Finalizado: {t['status']}")
            
        # Tabela e Pizza Geral
        if st.session_state.resultados_trades:
            df = pd.DataFrame(st.session_state.resultados_trades)
            t_place.table(df.head(10))
            
            counts = df['RESULT'].value_counts()
            fig_p = go.Figure(data=[go.Pie(labels=counts.index, values=counts.values, hole=.4, marker_colors=['#00ff00', '#ff0000'])])
            fig_p.update_layout(template="plotly_dark", height=200, margin=dict(l=0,r=0,t=0,b=0), showlegend=False)
            p_place.plotly_chart(fig_p, use_container_width=True, key=f"multi_pizza_{time.time()}")

        time.sleep(0.5)

    st.success("Ciclo de 10 trades finalizado!")
    st.session_state.running = False
    if st.button("Iniciar Próximo Ciclo"):
        st.rerun()
