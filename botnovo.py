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
if "ciclo_atual" not in st.session_state:
    st.session_state.ciclo_atual = 1

TAXA_EXECUCAO_SIMULADA = 0.01 

def formatar_moeda(valor, moeda_ref):
    taxa = 5.05 if moeda_ref == "BRL" else 1.0
    v = valor * taxa
    if moeda_ref == "BRL":
        return f"R$ {v:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    return f"$ {v:,.2f}"

def obter_preco_atual(address):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
        res = requests.get(url, timeout=2).json()
        return float(res['pairs'][0]['priceUsd'])
    except: return None

# ==========================================================
# 🖥️ INTERFACE
# ==========================================================
st.set_page_config(page_title="Sniper Parallel v8.5", layout="wide")

with st.sidebar:
    st.header("⚙️ Painel Multi-Trade")
    st.session_state.saldo_demo = st.number_input("Banca (USD):", value=float(st.session_state.saldo_demo))
    moeda_ref = st.radio("Moeda:", ["USD", "BRL"])
    st.divider()
    alvo_gain = st.slider("Alvo Gain (%)", 0.5, 20.0, 2.0)
    stop_loss = st.slider("Stop Loss (%)", 0.5, 15.0, 3.0)
    st.divider()
    if st.button("Resetar Tudo"):
        st.session_state.resultados_trades = []
        st.session_state.ciclo_atual = 1
        st.rerun()

if not st.session_state.running:
    st.title("🚀 Sniper Parallel - 10 Simultâneos")
    st.metric("Banca Total", formatar_moeda(st.session_state.saldo_demo, moeda_ref))
    
    ca = st.text_input("CA do Token:")
    invest_total = st.number_input("Investimento por Slot (USD):", value=10.0)
    
    if st.button("🔥 INICIAR 100 CICLOS X 10 TRADES", use_container_width=True, type="primary"):
        if ca:
            st.session_state.ca_ativo = ca
            st.session_state.invest_slot = invest_total
            st.session_state.running = True
            st.rerun()
else:
    # --- TELA DE EXECUÇÃO PARALELA ---
    st.header(f"🛰️ Ciclo: {st.session_state.ciclo_atual} / 100")
    if st.button("🛑 PARAR AGORA", use_container_width=True):
        st.session_state.running = False
        st.rerun()

    # Criar o Grid Visual de 10 Slots (2 linhas de 5)
    slots_visuais = []
    col_group1 = st.columns(5)
    col_group2 = st.columns(5)
    for c in col_group1 + col_group2:
        slots_visuais.append(c.empty())

    # Área Inferior: Tabela e Pizza
    st.divider()
    c_tab, c_pie = st.columns([2, 1])
    t_resumo = c_tab.empty()
    p_pizza = c_pie.empty()

    # Iniciar os 10 trades do ciclo atual
    ca_ativo = st.session_state.ca_ativo
    preco_base = obter_preco_atual(ca_ativo)
    
    if preco_base:
        # Prepara os 10 trades
        trades = []
        for i in range(10):
            trades.append({
                "id": i + 1,
                "entrada": preco_base,
                "pnl": 0.0,
                "ativo": True,
                "resultado": ""
            })

        # Loop de Vida dos 10 Trades Simultâneos
        while st.session_state.running and any(t['ativo'] for t in trades):
            preco_agora = obter_preco_atual(ca_ativo)
            if not preco_agora: continue

            for i, t in enumerate(trades):
                if t['ativo']:
                    t['pnl'] = ((preco_agora / t['entrada']) - 1) * 100
                    
                    # Checar Saída
                    if t['pnl'] >= alvo_gain or t['pnl'] <= -stop_loss:
                        t['ativo'] = False
                        t['resultado'] = "WIN" if t['pnl'] > 0 else "LOSS"
                        # Contabiliza na banca
                        lucro_liq = (st.session_state.invest_slot * (t['pnl']/100)) - (st.session_state.invest_slot * TAXA_EXECUCAO_SIMULADA)
                        st.session_state.saldo_demo += lucro_liq
                        st.session_state.resultados_trades.insert(0, {
                            "HORA": datetime.now().strftime("%H:%M:%S"),
                            "CICLO": st.session_state.ciclo_atual,
                            "SLOT": t['id'],
                            "RESULT": t['resultado'],
                            "PNL %": f"{t['pnl']:.2f}%"
                        })

                # Atualiza Visual do Slot em Tempo Real
                cor = "#00ff00" if t['pnl'] > 0 else "#ff0000"
                status_txt = "⏳" if t['ativo'] else ("✅" if t['resultado'] == "WIN" else "❌")
                with slots_visuais[i].container():
                    st.markdown(f"""
                    <div style="border:1px solid #333; padding:10px; border-radius:5px; text-align:center;">
                        <small>SLOT {t['id']}</small>
                        <h2 style="color:{cor}; margin:0;">{t['pnl']:+.2f}%</h2>
                        <small>{status_txt}</small>
                    </div>
                    """, unsafe_allow_html=True)

            # Atualiza Tabela e Pizza Geral
            if st.session_state.resultados_trades:
                df = pd.DataFrame(st.session_state.resultados_trades)
                t_resumo.table(df.head(10))
                counts = df['RESULT'].value_counts()
                fig_p = go.Figure(data=[go.Pie(labels=counts.index, values=counts.values, hole=.4, marker_colors=['#00ff00', '#ff0000'])])
                fig_p.update_layout(template="plotly_dark", height=200, margin=dict(l=0,r=0,t=0,b=0), showlegend=False)
                p_pizza.plotly_chart(fig_p, use_container_width=True, key=f"p_{time.time()}")
            
            time.sleep(0.5)

        # Se todos os 10 ativos terminaram, pula para o próximo ciclo
        if st.session_state.running:
            st.session_state.ciclo_atual += 1
            if st.session_state.ciclo_atual <= 100:
                st.rerun()
            else:
                st.success("PARABÉNS! 100 Ciclos Completados.")
                st.session_state.running = False
                st.rerun()
