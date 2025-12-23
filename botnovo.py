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
if "token_nome" not in st.session_state:
    st.session_state.token_nome = ""

TAXA_BRL = 5.05
TAXA_EXECUCAO_SIMULADA = 0.01 

def formatar_moeda(valor_usd, moeda_ref):
    valor = valor_usd * TAXA_BRL if moeda_ref == "BRL" else valor_usd
    simbolo = "R$" if moeda_ref == "BRL" else "$"
    return f"{simbolo} {valor:,.2f}"

def obter_dados_token(address):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
        res = requests.get(url, timeout=2).json()
        pair = res['pairs'][0]
        return {"nome": pair['baseToken']['symbol'].upper(), "preco": float(pair['priceUsd'])}
    except: return None

# ==========================================================
# 🖥️ INTERFACE v10.2
# ==========================================================
st.set_page_config(page_title="Sniper Pro v10.2", layout="wide")

with st.sidebar:
    st.header("⚙️ Configuração")
    moeda_ref = st.radio("Moeda de Operação:", ["USD", "BRL"])
    
    val_banca = st.number_input(f"Banca Atual ({moeda_ref}):", 
                                value=float(st.session_state.saldo_usd * (TAXA_BRL if moeda_ref == "BRL" else 1.0)))
    
    if st.button("Atualizar Banca"):
        st.session_state.saldo_usd = val_banca / (TAXA_BRL if moeda_ref == "BRL" else 1.0)
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
    st.title("🛡️ Sniper Pro v10.2")
    st.markdown(f"### 👛 Saldo: {formatar_moeda(st.session_state.saldo_usd, moeda_ref)}")
    
    ca = st.text_input("Token CA (Memecoin):")
    invest_input = st.number_input(f"Investimento p/ Ordem ({moeda_ref}):", value=10.0 * taxa_view)
    
    invest_total_usd = (invest_input / taxa_view) * 10
    
    if st.button("🚀 INICIAR 100 CICLOS", use_container_width=True, type="primary"):
        dados = obter_dados_token(ca)
        if not ca: st.error("Insira o CA.")
        elif not dados: st.error("Token inválido.")
        elif invest_total_usd > st.session_state.saldo_usd: st.error("Saldo insuficiente.")
        else:
            st.session_state.token_nome = dados['nome']
            st.session_state.ca_ativo = ca
            st.session_state.invest_usd = invest_input / taxa_view
            st.session_state.running = True
            st.rerun()
else:
    # --- CABEÇALHO LÍPIDO ---
    h_col1, h_col2 = st.columns([3, 1])
    
    h_col1.subheader(f"🛰️ {st.session_state.ciclo_atual}/100 | {st.session_state.token_nome}")
    
    # SALDO MINIMALISTA COM EMOJI
    placeholder_saldo = h_col2.empty()
    
    if st.button("🛑 PARAR OPERAÇÃO", use_container_width=True):
        st.session_state.running = False
        st.rerun()

    slots_visuais = [st.empty() for _ in range(10)]
    st.divider()
    t_resumo = st.empty()

    dados_token = obter_dados_token(st.session_state.ca_ativo)
    
    if dados_token:
        p_base = dados_token['preco']
        trades = [{"id": i+1, "entrada": p_base, "pnl": 0.0, "ativo": True, "res": "", "liq": 0.0} for i in range(10)]

        while st.session_state.running and any(t['ativo'] for t in trades):
            # Atualização do Saldo Minimalista
            txt_saldo = formatar_moeda(st.session_state.saldo_usd, moeda_ref)
            placeholder_saldo.markdown(f"<h3 style='text-align:right; margin:0;'>👛 {txt_saldo}</h3>", unsafe_allow_html=True)
            
            dados_loop = obter_dados_token(st.session_state.ca_ativo)
            if not dados_loop: continue
            p_agora = dados_loop['preco']

            for i, t in enumerate(trades):
                if t['ativo']:
                    t['pnl'] = ((p_agora / t['entrada']) - 1) * 100
                    v_finan = (st.session_state.invest_usd * (t['pnl']/100)) * taxa_view
                    
                    if t['pnl'] >= alvo_gain or t['pnl'] <= -stop_loss:
                        t['ativo'] = False
                        t['res'] = "WIN" if t['pnl'] > 0 else "LOSS"
                        t['liq'] = (st.session_state.invest_usd * (t['pnl']/100)) - (st.session_state.invest_usd * TAXA_EXECUCAO_SIMULADA)
                        st.session_state.saldo_usd += t['liq']

                    cor = "#00FF00" if t['pnl'] >= 0 else "#FF4B4B"
                    simbolo = "R$" if moeda_ref == "BRL" else "$"
                    icon = "🔵" if t['ativo'] else ("✅" if t['res'] == "WIN" else "❌")
                    
                    slots_visuais[i].markdown(
                        f"<div style='font-family:monospace; font-size:15px;'>{icon} <b>{simbolo} {st.session_state.invest_usd * taxa_view:.2f}</b> &nbsp;&nbsp; "
                        f"<span style='color:{cor};'>{t['pnl']:+.2f}%</span> &nbsp;&nbsp; "
                        f"<span style='color:{cor};'>{simbolo} {v_finan:+.2f}</span></div>", 
                        unsafe_allow_html=True
                    )

            if st.session_state.resultados_ciclos:
                t_resumo.table(pd.DataFrame(st.session_state.resultados_ciclos).head(15))
            
            time.sleep(0.3)

        if st.session_state.running:
            liq_total = sum(t['liq'] for t in trades)
            pnl_avg = (liq_total / (st.session_state.invest_usd * 10)) * 100
            
            st.session_state.resultados_ciclos.insert(0, {
                "CICLO": f"#{st.session_state.ciclo_atual}",
                "TOKEN": st.session_state.token_nome,
                "RESULTADO": "WIN" if liq_total > 0 else "LOSS",
                "PNL CICLO": f"{pnl_avg:+.2f}%",
                "LÍQUIDO": formatar_moeda(liq_total, moeda_ref)
            })
            
            st.session_state.ciclo_atual += 1
            st.rerun()
