import streamlit as st
import time
import requests
import pandas as pd
import plotly.graph_objects as go
import statistics
from datetime import datetime

# ==========================================================
# 🔑 ESTADO DA SESSÃO
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
# ⚙️ FUNÇÕES DE APOIO
# ==========================================================
def formatar_moeda(valor, moeda_ref):
    if moeda_ref == "BRL":
        return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    return f"$ {valor:,.2f}"

def obter_dados_moeda(address):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
        response = st.session_state.sessao_http.get(url, timeout=5)
        pair = response.json()['pairs'][0]
        return {
            "nome": pair['baseToken']['symbol'].upper(), 
            "preco": float(pair['priceUsd'])
        }
    except: return None

# ==========================================================
# 🖥️ INTERFACE
# ==========================================================
st.set_page_config(page_title="Sniper Pro", layout="wide")

with st.sidebar:
    st.header("⚙️ Configurações")
    
    # EDITAR SALDO
    novo_saldo = st.number_input("Editar Saldo Carteira:", value=float(st.session_state.saldo_demo))
    if st.button("Atualizar Saldo"):
        st.session_state.saldo_demo = novo_saldo
        st.rerun()
        
    st.divider()
    moeda_ref = st.radio("Exibir valores em:", ["USD", "BRL"])
    taxa = 5.05 if moeda_ref == "BRL" else 1.0
    
    if st.button("Limpar Tudo"):
        st.session_state.resultados_trades = []
        st.session_state.running = False
        st.rerun()

if not st.session_state.running:
    st.title("🤖 Sniper Dashboard")
    st.metric("Banca Disponível", formatar_moeda(st.session_state.saldo_demo * taxa, moeda_ref))
    
    ca = st.text_input("Cole o CA do Token:")
    val_in = st.number_input(f"Valor por Trade ({moeda_ref}):", value=10.0)
    
    if st.button("🚀 INICIAR OPERAÇÕES", use_container_width=True, type="primary"):
        if ca:
            dados = obter_dados_moeda(ca)
            if dados:
                st.session_state.token_nome = dados['nome']
                st.session_state.investimento_usd = val_in / taxa
                st.session_state.ca_ativo = ca
                st.session_state.running = True
                st.rerun()

else:
    # --- TELA DE EXECUÇÃO ---
    st.header(f"⚡ Operando {st.session_state.token_nome}")
    
    if st.button("🛑 PARAR BOT", use_container_width=True):
        st.session_state.running = False
        st.rerun()

    c1, c2 = st.columns(2)
    pnl_display = c1.empty()
    lucro_display = c1.empty()
    price_display = c2.empty()
    banca_display = c2.empty()

    grafico_place = st.empty()
    
    st.divider()
    # Containers para evitar erro de ID duplicado
    col_tab, col_pie = st.columns([2, 1])
    tabela_resumo = col_tab.empty()
    pizza_resumo = col_pie.empty()

    invest_usd = st.session_state.investimento_usd
    ca_ativo = st.session_state.ca_ativo

    for t_num in range(len(st.session_state.resultados_trades) + 1, 11):
        if not st.session_state.running: break
        
        d_init = obter_dados_moeda(ca_ativo)
        if not d_init: continue
        p_entrada = d_init['preco']
        precos_hist = [p_entrada]
        
        while st.session_state.running:
            atual = obter_dados_moeda(ca_ativo)
            if atual:
                p_atual = atual['preco']
                precos_hist.append(p_atual)
                pnl = ((p_atual / p_entrada) - 1) * 100
                lucro_usd = invest_usd * (pnl / 100)
                
                # Update Dashboard
                pnl_display.metric(f"Trade #{t_num}", f"{pnl:+.2f}%")
                lucro_display.metric("Resultado", formatar_moeda(lucro_usd * taxa, moeda_ref))
                price_display.metric("Preço", f"${p_atual:.8f}")
                banca_display.metric("Banca", formatar_moeda(st.session_state.saldo_demo * taxa, moeda_ref))

                with grafico_place.container():
                    fig = go.Figure(data=[go.Scatter(y=precos_hist[-40:], mode='lines', line=dict(color='#00ff00' if pnl > 0 else '#ff0000', width=3))])
                    fig.update_layout(template="plotly_dark", height=200, margin=dict(l=0,r=0,t=0,b=0), xaxis=dict(visible=False))
                    # KEY ÚNICA PARA O GRÁFICO DE LINHA
                    st.plotly_chart(fig, use_container_width=True, key=f"line_{t_num}_{time.time()}", config={'displayModeBar': False})

                # Tabela e Pizza
                if st.session_state.resultados_trades:
                    df_res = pd.DataFrame(st.session_state.resultados_trades)
                    tabela_resumo.table(df_res)
                    
                    # CORREÇÃO DO ERRO: Adicionando Key única ao gráfico de pizza
                    counts = df_res['STATUS'].value_counts()
                    fig_p = go.Figure(data=[go.Pie(labels=counts.index, values=counts.values, hole=.3, marker_colors=['#00ff00', '#ff0000'])])
                    fig_p.update_layout(template="plotly_dark", height=200, margin=dict(l=0,r=0,t=0,b=0), showlegend=False)
                    pizza_resumo.plotly_chart(fig_p, use_container_width=True, key=f"pizza_{t_num}_{time.time()}")

                # Saída (2% Win ou 3% Loss)
                if pnl >= 2.0 or pnl <= -3.0:
                    st.session_state.saldo_demo += lucro_usd
                    st.session_state.resultados_trades.insert(0, {
                        "TRADE": f"#{t_num}",
                        "STATUS": "WIN" if pnl > 0 else "LOSS",
                        "VALOR": formatar_moeda(lucro_usd * taxa, moeda_ref),
                        "PNL %": f"{pnl:+.2f}%"
                    })
                    break
            time.sleep(0.7)
    
    st.session_state.running = False
    st.rerun()
