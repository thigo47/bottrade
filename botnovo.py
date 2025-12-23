import streamlit as st
import time
import requests
import pandas as pd
import plotly.graph_objects as go
import statistics
from datetime import datetime

# ==========================================================
# 🔑 ESTADO DA SESSÃO (CARTEIRA DEMO)
# ==========================================================
if "sessao_http" not in st.session_state:
    st.session_state.sessao_http = requests.Session()
if "resultados_trades" not in st.session_state:
    st.session_state.resultados_trades = []
if "running" not in st.session_state:
    st.session_state.running = False
# Saldo inicial da Carteira Demo
if "saldo_demo" not in st.session_state:
    st.session_state.saldo_demo = 1000.0  # Começa com $1000 fictícios

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
            "liquidez": float(pair.get('liquidity', {}).get('usd', 0)) if pair.get('liquidity') else 0
        }
    except: return None

def ajustar_parametros_por_volatilidade(volatilidade):
    if volatilidade < 2: return {'L_TRAIL': 0.8, 'D_TRAIL': 0.2, 'STOP': 3.0, 'tipo': 'Muito Baixa'}
    elif volatilidade < 5: return {'L_TRAIL': 1.5, 'D_TRAIL': 0.3, 'STOP': 5.0, 'tipo': 'Moderada'}
    elif volatilidade < 15: return {'L_TRAIL': 2.5, 'D_TRAIL': 0.5, 'STOP': 8.0, 'tipo': 'Alta'}
    else: return {'L_TRAIL': 4.0, 'D_TRAIL': 1.0, 'STOP': 12.0, 'tipo': 'Crítica'}

def calcular_volatilidade_simulada(precos):
    if len(precos) < 2: return 0
    mudancas = [abs((precos[i] - precos[i-1]) / precos[i-1]) * 100 for i in range(1, len(precos))]
    return statistics.mean(mudancas)

# ==========================================================
# 🖥️ INTERFACE
# ==========================================================
st.set_page_config(page_title="Sniper Pro - Demo Mode", layout="wide")

if not st.session_state.running:
    st.title("💰 Configuração Sniper (Demo)")
    
    # Exibição do Saldo Atual
    st.metric("🏦 Saldo Carteira Demo", f"${st.session_state.saldo_demo:.2f}")
    
    ca = st.text_input("👉 Endereço do Contrato (CA):")
    # Agora o valor do trade é capturado corretamente
    valor_input = st.number_input("Quanto investir por trade? ($)", value=10.0, step=1.0)
    
    if ca:
        token = obter_dados_moeda(ca)
        if token:
            st.success(f"Moeda: {token['nome']}")
            if st.button("🚀 INICIAR OPERAÇÕES", use_container_width=True, type="primary"):
                st.session_state.investimento_atual = valor_input # Salva o valor escolhido
                st.session_state.ca_ativo = ca
                st.session_state.running = True
                st.rerun()
else:
    # --- TELA DE EXECUÇÃO ---
    st.header(f"📈 Operando com ${st.session_state.investimento_atual}")
    
    if st.button("🛑 PARAR BOT", use_container_width=True):
        st.session_state.running = False
        st.rerun()

    # Layout de Métricas
    c1, c2, c3, c4 = st.columns(4)
    pnl_m = c1.empty()
    lucro_m = c2.empty()
    banca_m = c3.empty()
    status_m = c4.empty()

    grafico_place = st.empty()
    
    # Loop de 10 Trades
    ca_ativo = st.session_state.ca_ativo
    invest = st.session_state.investimento_atual # Usa o valor que você digitou

    for t_num in range(len(st.session_state.resultados_trades) + 1, 11):
        if not st.session_state.running: break
        
        d_init = obter_dados_moeda(ca_ativo)
        if not d_init: continue
        
        p_entrada = d_init['preco']
        precos_hist = [p_entrada]
        topo = p_entrada
        trail_ativo = False
        t_inicio = time.time()

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
                
                # Atualização Visual
                pnl_m.metric(f"PNL #{t_num}", f"{pnl:+.2f}%")
                lucro_m.metric("Resultado Trade", f"${lucro_sessao:+.4f}")
                banca_m.metric("Saldo Demo", f"${st.session_state.saldo_demo:.2f}")
                status_m.write(f"Volatilidade: {params['tipo']}")

                with grafico_place.container():
                    fig = go.Figure(data=[go.Scatter(y=precos_hist[-60:], mode='lines', line=dict(color='#00ff00' if pnl > 0 else '#ff0000'))])
                    fig.update_layout(template="plotly_dark", height=250, margin=dict(l=0,r=0,t=0,b=0))
                    st.plotly_chart(fig, use_container_width=True, key=f"ch_{t_num}_{time.time()}")

                # Lógica de Saída
                if not trail_ativo and pnl >= params['L_TRAIL']: trail_ativo = True
                
                venda_trail = topo * (1 - params['D_TRAIL']/100)
                if (trail_ativo and p_atual <= venda_trail) or (pnl <= -params['STOP']):
                    # ATUALIZA A CARTEIRA DEMO
                    st.session_state.saldo_demo += lucro_sessao
                    res = "WIN" if lucro_sessao > 0 else "LOSS"
                    
                    st.session_state.resultados_trades.append({
                        "TRADE": f"#{t_num}",
                        "STATUS": res,
                        "PNL (%)": f"{pnl:+.2f}%",
                        "LUCRO ($)": f"{lucro_sessao:+.4f}"
                    })
                    break
            time.sleep(0.5)

    st.session_state.running = False
    st.rerun()

# --- ÁREA DE ESTATÍSTICAS (Sempre visível se houver trades) ---
if st.session_state.resultados_trades:
    st.divider()
    df = pd.DataFrame(st.session_state.resultados_trades)
    
    col_tabela, col_pizza = st.columns([2, 1])
    
    with col_tabela:
        st.subheader("📋 Histórico")
        st.table(df)
        
    with col_pizza:
        st.subheader("📊 Assertividade")
        counts = df['STATUS'].value_counts()
        fig_pizza = go.Figure(data=[go.Pie(labels=counts.index, values=counts.values, hole=.3, marker_colors=['#00ff00', '#ff0000'])])
        fig_pizza.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig_pizza, use_container_width=True)