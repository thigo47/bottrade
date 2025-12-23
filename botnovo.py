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
    simbolo = "R$" if moeda_ref == "BRL" else "$"
    return f"{simbolo} {v:,.2f}"

def obter_preco_atual(address):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
        res = requests.get(url, timeout=2).json()
        return float(res['pairs'][0]['priceUsd'])
    except: return None

# ==========================================================
# 🖥️ INTERFACE CORRIGIDA
# ==========================================================
st.set_page_config(page_title="Sniper Minimal v9.1", layout="wide")

# CSS para forçar o visual minimalista e esconder erros de Markdown
st.markdown("""
    <style>
    .trade-row { font-family: monospace; font-size: 16px; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Config")
    st.session_state.saldo_demo = st.number_input("Banca (USD):", value=float(st.session_state.saldo_demo))
    moeda_ref = st.radio("Moeda:", ["USD", "BRL"])
    taxa_exibicao = 5.05 if moeda_ref == "BRL" else 1.0
    st.divider()
    alvo_gain = st.slider("Gain %", 0.5, 20.0, 2.0)
    stop_loss = st.slider("Loss %", 0.5, 15.0, 3.0)
    if st.button("Reset Total"):
        st.session_state.resultados_trades = []
        st.session_state.ciclo_atual = 1
        st.rerun()

if not st.session_state.running:
    st.title("🛡️ Sniper Minimal v9.1")
    st.metric("Banca", formatar_moeda(st.session_state.saldo_demo, moeda_ref))
    
    ca = st.text_input("Token CA:")
    invest_total = st.number_input("Investimento p/ Trade (USD):", value=10.0)
    
    if st.button("🚀 INICIAR OPERAÇÃO PARALELA", use_container_width=True, type="primary"):
        if ca:
            st.session_state.ca_ativo = ca
            st.session_state.invest_slot = invest_total
            st.session_state.running = True
            st.rerun()
else:
    # --- CABEÇALHO ---
    col_c1, col_c2 = st.columns([4, 1])
    col_c1.subheader(f"🛰️ Ciclo {st.session_state.ciclo_atual}/100")
    if col_c2.button("🛑 PARAR"):
        st.session_state.running = False
        st.rerun()

    # Placeholders para os 10 slots
    slots_visuais = [st.empty() for _ in range(10)]

    st.divider()
    col_t, col_p = st.columns([2, 1])
    t_resumo = col_t.empty()
    p_pizza = col_p.empty()

    ca_ativo = st.session_state.ca_ativo
    p_base = obter_preco_atual(ca_ativo)
    
    if p_base:
        trades = [{"id": i+1, "entrada": p_base, "pnl": 0.0, "ativo": True, "res": ""} for i in range(10)]

        while st.session_state.running and any(t['ativo'] for t in trades):
            p_agora = obter_preco_atual(ca_ativo)
            if not p_agora: continue

            for i, t in enumerate(trades):
                if t['ativo']:
                    t['pnl'] = ((p_agora / t['entrada']) - 1) * 100
                    valor_pnl_finan = (st.session_state.invest_slot * (t['pnl']/100)) * taxa_exibicao
                    
                    if t['pnl'] >= alvo_gain or t['pnl'] <= -stop_loss:
                        t['ativo'] = False
                        t['res'] = "WIN" if t['pnl'] > 0 else "LOSS"
                        lucro_liq = (st.session_state.invest_slot * (t['pnl']/100)) - (st.session_state.invest_slot * TAXA_EXECUCAO_SIMULADA)
                        st.session_state.saldo_demo += lucro_liq
                        st.session_state.resultados_trades.insert(0, {
                            "HORA": datetime.now().strftime("%H:%M:%S"),
                            "CICLO": st.session_state.ciclo_atual,
                            "RESULT": t['res'],
                            "PNL %": f"{t['pnl']:.2f}%"
                        })

                    # VISUAL CORRIGIDO
                    cor = "#00FF00" if t['pnl'] >= 0 else "#FF4B4B"
                    simbolo = "R$" if moeda_ref == "BRL" else "$"
                    status_icon = "🔵" if t['ativo'] else ("✅" if t['res'] == "WIN" else "❌")
                    invest_exibicao = st.session_state.invest_slot * taxa_exibicao
                    
                    # Usando st.markdown com unsafe_allow_html=True corretamente em cada slot
                    slots_visuais[i].markdown(
                        f"""<div class='trade-row'>
                        {status_icon} <b>{simbolo} {invest_exibicao:.2f}</b> &nbsp;&nbsp; 
                        <span style='color:{cor}; font-weight:bold;'>{t['pnl']:+.2f}%</span> &nbsp;&nbsp; 
                        <span style='color:{cor};'>{simbolo} {valor_pnl_finan:+.2f}</span>
                        </div>""", 
                        unsafe_allow_html=True
                    )

            if st.session_state.resultados_trades:
                df = pd.DataFrame(st.session_state.resultados_trades)
                t_resumo.table(df.head(10))
                counts = df['RESULT'].value_counts()
                fig_p = go.Figure(data=[go.Pie(labels=counts.index, values=counts.values, hole=.5, marker_colors=['#00FF00', '#FF4B4B'])])
                fig_p.update_layout(template="plotly_dark", height=180, margin=dict(l=0,r=0,t=0,b=0), showlegend=False)
                p_pizza.plotly_chart(fig_p, use_container_width=True, key=f"v9_{time.time()}")
            
            time.sleep(0.4)

        if st.session_state.running:
            st.session_state.ciclo_atual += 1
            st.rerun()
