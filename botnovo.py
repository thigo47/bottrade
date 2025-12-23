import streamlit as st
import time
import requests
import pandas as pd
import plotly.graph_objects as go
import statistics
from datetime import datetime

# ==========================================================
# 🔑 CONFIGURAÇÃO E ESTADO DA SESSÃO
# ==========================================================
if "sessao_http" not in st.session_state:
    st.session_state.sessao_http = requests.Session()
if "resultados_trades" not in st.session_state:
    st.session_state.resultados_trades = []
if "running" not in st.session_state:
    st.session_state.running = False
if "saldo_demo" not in st.session_state:
    st.session_state.saldo_demo = 1000.0

# ==========================================================
# ⚙️ FUNÇÕES DE MOTOR
# ==========================================================
def obter_dados_moeda(address):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
        response = st.session_state.sessao_http.get(url, timeout=5)
        dados = response.json()
        pair = dados['pairs'][0]
        return {
            "nome": pair.get('baseToken', {}).get('symbol', 'UNK'),
            "preco": float(pair.get('priceUsd', 0)),
        }
    except: return None

def ajustar_parametros_por_volatilidade(volatilidade):
    if volatilidade < 2: return {'L_TRAIL': 0.8, 'D_TRAIL': 0.2, 'STOP': 3.0, 'tipo': 'Baixa'}
    elif volatilidade < 5: return {'L_TRAIL': 1.5, 'D_TRAIL': 0.3, 'STOP': 5.0, 'tipo': 'Média'}
    else: return {'L_TRAIL': 2.5, 'D_TRAIL': 0.5, 'STOP': 8.0, 'tipo': 'Alta'}

def calcular_volatilidade_simulada(precos):
    if len(precos) < 2: return 0
    mudancas = [abs((precos[i] - precos[i-1]) / precos[i-1]) * 100 for i in range(1, len(precos))]
    return statistics.mean(mudancas)

# ==========================================================
# 🖥️ INTERFACE MOBILE FRIENDLY
# ==========================================================
st.set_page_config(page_title="Sniper Mobile", layout="wide", initial_sidebar_state="collapsed")

# Estilo para melhorar visualização no celular
st.markdown("""<style> 
    .stMetric { background-color: #161a25; border: 1px solid #2d323e; padding: 10px; border-radius: 8px; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
</style>""", unsafe_allow_html=True)

if not st.session_state.running:
    st.title("🏦 Sniper Demo")
    st.metric("Banca Atual", f"${st.session_state.saldo_demo:.2f}")
    
    ca = st.text_input("CA do Token:")
    valor_input = st.number_input("Investimento por Trade ($):", value=10.0)
    
    if st.button("🚀 INICIAR 10 TRADES", use_container_width=True, type="primary"):
        if ca:
            st.session_state.investimento_atual = valor_input
            st.session_state.ca_ativo = ca
            st.session_state.running = True
            st.rerun()
else:
    # --- DASHBOARD DE EXECUÇÃO ---
    st.subheader(f"📟 Operando: {st.session_state.investimento_atual}$")
    
    if st.button("🛑 PARAR BOT", use_container_width=True):
        st.session_state.running = False
        st.rerun()

    # Cards Principais (No celular ficam um abaixo do outro)
    c1, c2 = st.columns(2)
    pnl_m = c1.empty()
    cash_m = c1.empty() # Empilhado
    price_m = c2.empty()
    banca_m = c2.empty() # Empilhado

    grafico_place = st.empty()
    
    ca_ativo = st.session_state.ca_ativo
    invest = st.session_state.investimento_atual

    for t_num in range(len(st.session_state.resultados_trades) + 1, 11):
        if not st.session_state.running: break
        
        d_init = obter_dados_moeda(ca_ativo)
        if not d_init: continue
        p_entrada = d_init['preco']
        precos_hist = [p_entrada]
        topo = p_entrada
        trail_ativo = False

        while st.session_state.running:
            d_atual = obter_dados_moeda(ca_ativo)
            if d_atual:
                p_atual = d_atual['preco']
                precos_hist.append(p_atual)
                if p_atual > topo: topo = p_atual
                
                pnl = ((p_atual / p_entrada) - 1) * 100
                lucro_sessao = invest * (pnl / 100)
                volat = calcular_volatilidade_simulada(precos_hist[-20:])
                params = ajustar_parametros_por_volatilidade(volat)
                
                # Update UI
                pnl_m.metric(f"Trade #{t_num}", f"{pnl:+.2f}%")
                cash_m.metric("Lucro do Trade", f"${lucro_sessao:+.4f}")
                price_m.metric("Preço Atual", f"${p_atual:.8f}")
                banca_m.metric("Saldo Banca", f"${st.session_state.saldo_demo:.2f}")

                with grafico_place.container():
                    fig = go.Figure(data=[go.Scatter(y=precos_hist[-40:], mode='lines', line=dict(color='#00ff00' if pnl > 0 else '#ff0000'))])
                    fig.update_layout(template="plotly_dark", height=200, margin=dict(l=0,r=0,t=0,b=0), xaxis=dict(visible=False))
                    st.plotly_chart(fig, use_container_width=True, key=f"m_{t_num}_{time.time()}", config={'displayModeBar': False})

                # Saída
                venda_trail = topo * (1 - params['D_TRAIL']/100)
                if (not trail_ativo and pnl >= params['L_TRAIL']): trail_ativo = True
                
                if (trail_ativo and p_atual <= venda_trail) or (pnl <= -params['STOP']):
                    st.session_state.saldo_demo += lucro_sessao
                    st.session_state.resultados_trades.append({
                        "RESULTADO": "WIN" if lucro_sessao > 0 else "LOSS",
                        "VALOR": lucro_sessao,
                        "PNL": pnl
                    })
                    break
            time.sleep(0.5)
    st.session_state.running = False
    st.rerun()

# --- RESUMO FINANCEIRO (ACUMULADO) ---
if st.session_state.resultados_trades:
    st.divider()
    df = pd.DataFrame(st.session_state.resultados_trades)
    
    lucro_total = df[df['VALOR'] > 0]['VALOR'].sum()
    perda_total = df[df['VALOR'] < 0]['VALOR'].sum()
    balanco = lucro_total + perda_total

    st.subheader("📊 Balanço Geral")
    res1, res2, res3 = st.columns(3)
    res1.metric("Soma Lucros", f"${lucro_total:.2f}", delta_color="normal")
    res2.metric("Soma Perdas", f"${perda_total:.2f}", delta_color="normal")
    res3.metric("Balanço Líquido", f"${balanco:.2f}", delta=f"{balanco:.2f}")

    # Gráfico de Pizza
    counts = df['RESULTADO'].value_counts()
    fig_pizza = go.Figure(data=[go.Pie(labels=counts.index, values=counts.values, hole=.4, marker_colors=['#00ff00', '#ff0000'])])
    fig_pizza.update_layout(template="plotly_dark", height=250, margin=dict(l=0,r=0,t=50,b=0))
    st.plotly_chart(fig_pizza, use_container_width=True)
