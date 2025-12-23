import streamlit as st
import time
import requests
import pandas as pd

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
if "ultimo_preco_track" not in st.session_state:
    st.session_state.ultimo_preco_track = 0.0

TAXA_BRL = 5.05
TAXA_EXECUCAO_SIMULADA = 0.01 

def formatar_moeda(valor_usd, moeda_ref):
    valor = valor_usd * TAXA_BRL if moeda_ref == "BRL" else valor_usd
    simbolo = "R$" if moeda_ref == "BRL" else "$"
    return f"{simbolo} {valor:,.2f}"

def buscar_info_inicial(ca):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        res = requests.get(url, timeout=5).json()
        if res.get('pairs'):
            melhor_par = res['pairs'][0]
            return {
                "nome": melhor_par['baseToken']['symbol'].upper(),
                "pair_addr": melhor_par['pairAddress'],
                "preco": float(melhor_par['priceUsd'])
            }
    except: return None

def obter_preco_veloz(pair_addr):
    try:
        url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{pair_addr}"
        res = requests.get(url, timeout=1).json() # Timeout reduzido
        return float(res['pair']['priceUsd'])
    except: return None

# ==========================================================
# 🖥️ INTERFACE v12.0 - ANTI-GAP & EMERGENCY EXIT
# ==========================================================
st.set_page_config(page_title="Sniper Pro v12", layout="wide")

with st.sidebar:
    st.header("⚙️ Configuração")
    moeda_ref = st.radio("Moeda:", ["USD", "BRL"])
    val_banca = st.number_input(f"Banca ({moeda_ref}):", 
                                value=float(st.session_state.saldo_usd * (TAXA_BRL if moeda_ref == "BRL" else 1.0)))
    if st.button("Atualizar Banca"):
        st.session_state.saldo_usd = val_banca / (TAXA_BRL if moeda_ref == "BRL" else 1.0)
        st.rerun()

    st.divider()
    alvo_gain = st.slider("Alvo (%)", 0.5, 20.0, 2.0)
    stop_loss_config = st.slider("Stop (%)", 0.5, 15.0, 3.0)
    
    st.info("Atenção: Gaps de mercado podem exceder o Stop configurado em moedas de baixa liquidez.")
    
    if st.button("Resetar Histórico"):
        st.session_state.resultados_ciclos = []
        st.session_state.ciclo_atual = 1
        st.rerun()

taxa_view = TAXA_BRL if moeda_ref == "BRL" else 1.0

if not st.session_state.running:
    st.title("🛡️ Sniper Pro v12")
    st.write(f"**Saldo:** {formatar_moeda(st.session_state.saldo_usd, moeda_ref)}")
    
    ca = st.text_input("Token CA:")
    invest_input = st.number_input(f"Investimento p/ Ordem ({moeda_ref}):", value=10.0 * taxa_view)
    
    if st.button("🚀 INICIAR OPERAÇÃO", use_container_width=True, type="primary"):
        info = buscar_info_inicial(ca)
        invest_total_usd = (invest_input / taxa_view) * 10
        if info and invest_total_usd <= st.session_state.saldo_usd:
            st.session_state.token_nome = info['nome']
            st.session_state.pair_address = info['pair_addr']
            st.session_state.ca_ativo = ca
            st.session_state.invest_usd = invest_input / taxa_view
            st.session_state.running = True
            st.session_state.ultimo_preco_track = info['preco']
            st.rerun()
        else:
            st.error("Erro: CA inválido ou saldo insuficiente.")
else:
    # --- HEADER ---
    placeholder_saldo = st.empty()
    col_status, col_parar = st.columns([3, 1])
    col_status.subheader(f"🛰️ {st.session_state.ciclo_atual}/100 | {st.session_state.token_nome}")
    if col_parar.button("🛑 PARAR", use_container_width=True):
        st.session_state.running = False
        st.rerun()
    
    placeholder_preco = col_parar.empty()
    slots_visuais = [st.empty() for _ in range(10)]
    st.divider()
    t_resumo = st.empty()

    p_base = obter_preco_veloz(st.session_state.pair_address)
    if p_base:
        trades = [{"id": i+1, "entrada": p_base, "pnl": 0.0, "ativo": True, "res": "", "liq": 0.0, "max_pnl": 0.0} for i in range(10)]

        while st.session_state.running and any(t['ativo'] for t in trades):
            txt_saldo = formatar_moeda(st.session_state.saldo_usd, moeda_ref)
            placeholder_saldo.markdown(f"**{txt_saldo}**")
            
            p_agora = obter_preco_veloz(st.session_state.pair_address)
            if not p_agora: continue

            seta = "▲" if p_agora >= st.session_state.ultimo_preco_track else "▼"
            cor_seta = "#00FF00" if p_agora >= st.session_state.ultimo_preco_track else "#FF4B4B"
            placeholder_preco.markdown(f"<div style='text-align:center;font-size:18px;'>USD {p_agora:.8f} <span style='color:{cor_seta};'>{seta}</span></div>", unsafe_allow_html=True)
            st.session_state.ultimo_preco_track = p_agora

            for i, t in enumerate(trades):
                if t['ativo']:
                    t['pnl'] = ((p_agora / t['entrada']) - 1) * 100
                    if t['pnl'] > t['max_pnl']: t['max_pnl'] = t['pnl']
                    
                    # --- LÓGICA DE PROTEÇÃO v12 ---
                    # 1. Trava de Lucro (se subiu mais de 1%, o stop vira o preço de entrada)
                    stop_dinamico = -stop_loss_config
                    if t['max_pnl'] > 1.5: 
                        stop_dinamico = 0.1 # Garante o empate + taxas
                    
                    # 2. Check de Saída
                    if t['pnl'] >= alvo_gain or t['pnl'] <= stop_dinamico:
                        t['ativo'] = False
                        t['res'] = "WIN" if t['pnl'] > 0 else "LOSS"
                        t['liq'] = (st.session_state.invest_usd * (t['pnl']/100)) - (st.session_state.invest_usd * TAXA_EXECUCAO_SIMULADA)
                        st.session_state.saldo_usd += t['liq']

                    cor = "#00FF00" if t['pnl'] >= 0 else "#FF4B4B"
                    simbolo = "R$" if moeda_ref == "BRL" else "$"
                    icon = "🔵" if t['ativo'] else ("✅" if t['res'] == "WIN" else "❌")
                    
                    slots_visuais[i].markdown(
                        f"<div style='font-family:monospace; font-size:14px;'>{icon} <b>{simbolo}{st.session_state.invest_usd * taxa_view:.2f}</b> &nbsp; "
                        f"<span style='color:{cor}; font-weight:bold;'>{t['pnl']:+.2f}%</span></div>", 
                        unsafe_allow_html=True
                    )

            if st.session_state.resultados_ciclos:
                t_resumo.table(pd.DataFrame(st.session_state.resultados_ciclos).head(10))
            
            time.sleep(0.1) # Velocidade máxima permitida

        if st.session_state.running:
            liq_total = sum(t['liq'] for t in trades)
            pnl_avg = (liq_total / (st.session_state.invest_usd * 10)) * 100
            st.session_state.resultados_ciclos.insert(0, {
                "CICLO": f"#{st.session_state.ciclo_atual}",
                "TOKEN": st.session_state.token_nome,
                "RESULTADO": "WIN" if liq_total > 0 else "LOSS",
                "PNL %": f"{pnl_avg:+.2f}%",
                "LÍQUIDO": formatar_moeda(liq_total, moeda_ref)
            })
            st.session_state.ciclo_atual += 1
            st.rerun()
