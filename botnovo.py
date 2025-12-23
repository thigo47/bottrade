import streamlit as st
import time
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# ==========================================================
# 🔑 CONFIGURAÇÕES DE ALTA FIDELIDADE (PRE-REAL)
# ==========================================================
if "resultados_trades" not in st.session_state:
    st.session_state.resultados_trades = []
if "running" not in st.session_state:
    st.session_state.running = False
if "saldo_demo" not in st.session_state:
    st.session_state.saldo_demo = 1000.0

# Simulação de custo real: Taxa da rede + Slippage médio
TAXA_EXECUCAO_SIMULADA = 0.01 # 1% de custo por operação

# ==========================================================
# ⚙️ MOTORES DE ANALISE (SIMULANDO WEB3)
# ==========================================================
def analisar_seguranca_token(address):
    """Simula a checagem de Rugcheck/Honeypot"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
        res = requests.get(url, timeout=5).json()
        pair = res['pairs'][0]
        
        # Simulando critérios de segurança reais
        liquidez = pair.get('liquidity', {}).get('usd', 0)
        mkt_cap = pair.get('fdv', 0)
        
        status = "✅ SEGURO"
        if liquidez < 10000: status = "⚠️ BAIXA LIQUIDEZ"
        if mkt_cap < 50000: status = "🚨 ALTO RISCO (RUG)"
        
        return {
            "nome": pair['baseToken']['symbol'].upper(),
            "preco": float(pair['priceUsd']),
            "status": status,
            "liquidez": liquidez
        }
    except: return None

# ==========================================================
# 🖥️ INTERFACE PROFISSIONAL
# ==========================================================
st.set_page_config(page_title="Sniper Pro Terminal", layout="wide")

with st.sidebar:
    st.header("⚡ Terminal de Execução")
    moeda_ref = st.radio("Moeda:", ["USD", "BRL"])
    taxa_c = 5.05 if moeda_ref == "BRL" else 1.0
    
    st.divider()
    st.subheader("Configurações de Rede")
    prioridade = st.select_slider("Taxa de Prioridade (Jito):", ["Baixa", "Média", "Turbo"])
    slippage = st.slider("Slippage Máximo (%)", 0.5, 10.0, 1.0)
    
    if st.button("Resetar Sistema"):
        st.session_state.saldo_demo = 1000.0
        st.session_state.resultados_trades = []
        st.rerun()

# --- TELA INICIAL ---
if not st.session_state.running:
    st.title("🛡️ Sniper Pro - Alpha Mode")
    
    # Dashboard de Banca
    col_b1, col_b2 = st.columns(2)
    col_b1.metric("Saldo em Carteira", formatar_moeda(st.session_state.saldo_demo * taxa_c, moeda_ref) if 'formatar_moeda' in globals() else f"${st.session_state.saldo_demo:.2f}")
    
    ca = st.text_input("Insira o Mint Address (CA) da Solana:")
    
    if ca:
        analise = analisar_seguranca_token(ca)
        if analise:
            st.info(f"Token Detectado: {analise['nome']} | Segurança: {analise['status']}")
            st.write(f"Liquidez em Pool: ${analise['liquidez']:,.2f}")
            
            valor_invest = st.number_input(f"Montante por Ordem ({moeda_ref}):", value=10.0)
            
            if analise['status'] == "✅ SEGURO":
                if st.button("🚀 EXECUTAR ESTRATÉGIA", use_container_width=True, type="primary"):
                    st.session_state.token_nome = analise['nome']
                    st.session_state.invest_usd = valor_invest / taxa_c
                    st.session_state.ca_ativo = ca
                    st.session_state.running = True
                    st.rerun()
            else:
                st.warning("O robô bloqueou a operação por risco de segurança.")
        else:
            st.error("Contrato não encontrado na rede.")

# --- TELA DE EXECUÇÃO ---
else:
    st.header(f"🛰️ Conectado: {st.session_state.token_nome}")
    st.caption(f"Slippage: {slippage}% | Prioridade: {prioridade} | Modo: Emulação Real")

    if st.button("🛑 CANCELAR TODAS AS ORDENS", use_container_width=True):
        st.session_state.running = False
        st.rerun()

    # Métricas de Alta Velocidade
    m1, m2, m3 = st.columns(3)
    pnl_m = m1.empty()
    lucro_m = m2.empty()
    banca_m = m3.empty()
    
    grafico_place = st.empty()
    
    st.divider()
    c_tab, c_pie = st.columns([2, 1])
    t_resumo = c_tab.empty()
    p_resumo = c_pie.empty()

    invest_usd = st.session_state.invest_usd
    ca_ativo = st.session_state.ca_ativo

    for t_num in range(len(st.session_state.resultados_trades) + 1, 11):
        if not st.session_state.running: break
        
        d = analisar_seguranca_token(ca_ativo)
        if not d: continue
        p_entrada = d['preco']
        hist = [p_entrada]
        
        while st.session_state.running:
            d_atual = analisar_seguranca_token(ca_ativo)
            if d_atual:
                p_atual = d_atual['preco']
                hist.append(p_atual)
                pnl_bruto = ((p_atual / p_entrada) - 1) * 100
                
                # Simulando Lucro Líquido (descontando taxas de entrada/saída)
                lucro_bruto_usd = invest_usd * (pnl_bruto / 100)
                taxas_simuladas = invest_usd * TAXA_EXECUCAO_SIMULADA
                lucro_liquido_usd = lucro_bruto_usd - taxas_simuladas
                
                # Update UI
                pnl_m.metric(f"Trade #{t_num}", f"{pnl_bruto:+.2f}%")
                lucro_m.metric("P&L Líquido (Estimado)", f"${lucro_liquido_usd:+.2f}")
                banca_m.metric("Banca", f"${st.session_state.saldo_demo:.2f}")

                with grafico_place.container():
                    fig = go.Figure(data=[go.Scatter(y=hist[-50:], mode='lines', line=dict(color='#00ff00' if pnl_bruto > 0 else '#ff0000', width=2))])
                    fig.update_layout(template="plotly_dark", height=200, margin=dict(l=0,r=0,t=0,b=0))
                    st.plotly_chart(fig, use_container_width=True, key=f"L_{t_num}_{time.time()}", config={'displayModeBar': False})

                # Histórico e Pizza
                if st.session_state.resultados_trades:
                    df = pd.DataFrame(st.session_state.resultados_trades)
                    t_resumo.table(df)
                    counts = df['RESULT'].value_counts()
                    fig_p = go.Figure(data=[go.Pie(labels=counts.index, values=counts.values, hole=.4, marker_colors=['#00ecff', '#ff0055'])])
                    fig_p.update_layout(template="plotly_dark", height=180, margin=dict(l=0,r=0,t=0,b=0), showlegend=False)
                    p_resumo.plotly_chart(fig_p, use_container_width=True, key=f"P_{t_num}_{time.time()}")

                # Saída lógica (2% profit ou 3% stop)
                if pnl_bruto >= 2.0 or pnl_bruto <= -3.0:
                    st.session_state.saldo_demo += lucro_liquido_usd
                    st.session_state.resultados_trades.insert(0, {
                        "HORA": datetime.now().strftime("%H:%M:%S"),
                        "RESULT": "WIN" if lucro_liquido_usd > 0 else "LOSS",
                        "VALOR NET": f"${lucro_liquido_usd:+.2f}",
                        "PNL %": f"{pnl_bruto:+.2f}%"
                    })
                    break
            time.sleep(0.5)
    
    st.session_state.running = False
    st.rerun()

def formatar_moeda(v, m):
    if m == "BRL": return f"R$ {v:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    return f"$ {v:,.2f}"
