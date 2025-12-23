import streamlit as st
import time
import requests
import pandas as pd
from datetime import datetime

# ==========================================================
# 🔑 ESTADO DA SESSÃO
# ==========================================================
if "resultados_ciclos" not in st.session_state:
    st.session_state.resultados_ciclos = []
if "running" not in st.session_state:
    st.session_state.running = False
if "saldo_usd" not in st.session_state:
    st.session_state.saldo_usd = 1000.0
if "ciclo_atual" not in st.session_state:
    st.session_state.ciclo_atual = 1

TAXA_BRL = 5.05
TAXA_EXECUCAO_SIMULADA = 0.01 

def formatar_moeda(valor_usd, moeda_ref):
    valor = valor_usd * TAXA_BRL if moeda_ref == "BRL" else valor_usd
    simbolo = "R$" if moeda_ref == "BRL" else "$"
    return f"{simbolo} {valor:,.2f}"

def obter_preco_atual(address):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
        res = requests.get(url, timeout=2).json()
        return float(res['pairs'][0]['priceUsd'])
    except: return None

# ==========================================================
# 🖥️ INTERFACE v9.5
# ==========================================================
st.set_page_config(page_title="Sniper Ciclos v9.5", layout="wide")

with st.sidebar:
    st.header("⚙️ Configuração")
    moeda_ref = st.radio("Moeda de Operação:", ["USD", "BRL"])
    
    # CORREÇÃO DO BUG: Input adaptável à moeda selecionada
    label_banca = f"Banca Atual ({moeda_ref}):"
    valor_input = st.number_input(label_banca, value=float(st.session_state.saldo_usd * (TAXA_BRL if moeda_ref == "BRL" else 1.0)))
    
    if st.button("Atualizar Banca"):
        st.session_state.saldo_usd = valor_input / TAXA_BRL if moeda_ref == "BRL" else valor_input
        st.rerun()

    st.divider()
    alvo_gain = st.slider("Alvo Ciclo (%)", 0.5, 20.0, 2.0)
    stop_loss = st.slider("Stop Ciclo (%)", 0.5, 15.0, 3.0)
    
    if st.button("Resetar Histórico"):
        st.session_state.resultados_ciclos = []
        st.session_state.ciclo_atual = 1
        st.rerun()

taxa_view = TAXA_BRL if moeda_ref == "BRL" else 1.0

if not st.session_state.running:
    st.title("🛡️ Sniper Pro - Ciclos")
    st.metric("Banca Disponível", formatar_moeda(st.session_state.saldo_usd, moeda_ref))
    
    ca = st.text_input("Token CA:")
    invest_input = st.number_input(f"Investimento por Ordem ({moeda_ref}):", value=10.0 * taxa_view)
    
    if st.button("🚀 INICIAR 100 CICLOS", use_container_width=True, type="primary"):
        if ca:
            st.session_state.ca_ativo = ca
            st.session_state.invest_usd = invest_input / taxa_view
            st.session_state.running = True
            st.rerun()
else:
    # --- PAINEL DE EXECUÇÃO ---
    c1, c2, c3 = st.columns([2, 2, 1])
    c1.subheader(f"🛰️ Ciclo {st.session_state.ciclo_atual}/100")
    
    # Cálculo de Win Rate para substituir a pizza
    if st.session_state.resultados_ciclos:
        wins = sum(1 for x in st.session_state.resultados_ciclos if x['RESULTADO'] == "WIN")
        rate = (wins / len(st.session_state.resultados_ciclos)) * 100
        c2.metric("Assertividade (Win Rate)", f"{rate:.1f}%")
    
    if c3.button("🛑 PARAR"):
        st.session_state.running = False
        st.rerun()

    slots_visuais = [st.empty() for _ in range(10)]
    st.divider()
    st.write("### 📜 Histórico de Ciclos")
    t_resumo = st.empty()

    p_base = obter_preco_atual(st.session_state.ca_ativo)
    
    if p_base:
        trades = [{"id": i+1, "entrada": p_base, "pnl": 0.0, "ativo": True, "res": "", "liq": 0.0} for i in range(10)]

        while st.session_state.running and any(t['ativo'] for t in trades):
            p_agora = obter_preco_atual(st.session_state.ca_ativo)
            if not p_agora: continue

            for i, t in enumerate(trades):
                if t['ativo']:
                    t['pnl'] = ((p_agora / t['entrada']) - 1) * 100
                    valor_finan = (st.session_state.invest_usd * (t['pnl']/100)) * taxa_view
                    
                    if t['pnl'] >= alvo_gain or t['pnl'] <= -stop_loss:
                        t['ativo'] = False
                        t['res'] = "WIN" if t['pnl'] > 0 else "LOSS"
                        t['liq'] = (st.session_state.invest_usd * (t['pnl']/100)) - (st.session_state.invest_usd * TAXA_EXECUCAO_SIMULADA)
                        st.session_state.saldo_usd += t['liq']

                    # Visual dos slots ativos
                    cor = "#00FF00" if t['pnl'] >= 0 else "#FF4B4B"
                    simbolo = "R$" if moeda_ref == "BRL" else "$"
                    icon = "🔵" if t['ativo'] else ("✅" if t['res'] == "WIN" else "❌")
                    
                    slots_visuais[i].markdown(
                        f"<div style='font-family:monospace;'>{icon} <b>{simbolo} {st.session_state.invest_usd * taxa_view:.2f}</b> &nbsp;&nbsp; "
                        f"<span style='color:{cor};'>{t['pnl']:+.2f}%</span> &nbsp;&nbsp; "
                        f"<span style='color:{cor};'>{simbolo} {valor_finan:+.2f}</span></div>", 
                        unsafe_allow_html=True
                    )

            # Atualizar Tabela de Ciclos (Somente após fechar ciclos ou para mostrar os anteriores)
            if st.session_state.resultados_ciclos:
                t_resumo.table(pd.DataFrame(st.session_state.resultados_ciclos).head(15))
            
            time.sleep(0.4)

        # FIM DO CICLO: Agrupa os dados e salva
        if st.session_state.running:
            pnl_total_ciclo = sum(t['pnl'] for t in trades) / 10
            liq_total_ciclo = sum(t['liq'] for t in trades)
            
            st.session_state.resultados_ciclos.insert(0, {
                "CICLO": f"#{st.session_state.ciclo_atual}",
                "RESULTADO": "WIN" if liq_total_ciclo > 0 else "LOSS",
                "PNL MÉDIO %": f"{pnl_total_ciclo:+.2f}%",
                "TOTAL LÍQUIDO": formatar_moeda(liq_total_ciclo, moeda_ref)
            })
            
            st.session_state.ciclo_atual += 1
            st.rerun()
