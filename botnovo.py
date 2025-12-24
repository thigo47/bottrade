import streamlit as st
import time
import requests
import pandas as pd

# --- ESTADO DA SESSÃO ---
if "resultados_ciclos" not in st.session_state:
    st.session_state.resultados_ciclos = []
if "running" not in st.session_state:
    st.session_state.running = False
if "saldo_usd" not in st.session_state:
    st.session_state.saldo_usd = 1000.0
if "ciclo_atual" not in st.session_state:
    st.session_state.ciclo_atual = 1

TAXA_BRL = 5.05
TAXA_EXEC_SIMULADA = 0.01 

def formatar_moeda(valor_usd, moeda_ref):
    valor = valor_usd * TAXA_BRL if moeda_ref == "BRL" else valor_usd
    simbolo = "R$" if moeda_ref == "BRL" else "$"
    return f"{simbolo} {valor:,.2f}"

def check_preco(pair_addr):
    try:
        url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{pair_addr}"
        res = requests.get(url, timeout=2).json()
        return float(res['pair']['priceUsd'])
    except: return None

# --- INTERFACE ---
st.set_page_config(page_title="Sniper Pro v15", layout="wide")

with st.sidebar:
    st.header("⚙️ Painel de Controlo")
    moeda_ref = st.radio("Moeda:", ["USD", "BRL"])
    taxa_view = TAXA_BRL if moeda_ref == "BRL" else 1.0
    
    st.metric("Saldo Atual", formatar_moeda(st.session_state.saldo_usd, moeda_ref))
    
    if st.button("Resetar Histórico"):
        st.session_state.resultados_ciclos = []
        st.session_state.ciclo_atual = 1
        st.rerun()

if not st.session_state.running:
    st.title("🛡️ Sniper Pro v15")
    ca = st.text_input("Token CA:")
    invest_input = st.number_input(f"Valor por Ordem ({moeda_ref}):", value=10.0 * taxa_view)
    
    if st.button("🚀 INICIAR", use_container_width=True, type="primary"):
        # Verificação de Saldo antes de começar
        invest_necessario = (invest_input / taxa_view) * 10
        if invest_necessario > st.session_state.saldo_usd:
            st.error(f"Saldo insuficiente! Você precisa de {formatar_moeda(invest_necessario, moeda_ref)}")
        else:
            try:
                url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
                info = requests.get(url).json()['pairs'][0]
                st.session_state.token_nome = info['baseToken']['symbol']
                st.session_state.pair_address = info['pairAddress']
                st.session_state.invest_usd = invest_input / taxa_view
                st.session_state.running = True
                st.rerun()
            except: st.error("Token não encontrado ou erro de conexão.")
else:
    # --- LOOP DE OPERAÇÃO ---
    col_info, col_btn = st.columns([3, 1])
    col_info.subheader(f"🛰️ Ciclo {st.session_state.ciclo_atual} | {st.session_state.token_nome}")
    
    if col_btn.button("🛑 PARAR"):
        st.session_state.running = False
        st.rerun()
    
    price_place = col_btn.empty()
    slots = [st.empty() for _ in range(10)]
    t_resumo = st.empty()

    p_ini = check_preco(st.session_state.pair_address)
    if p_ini:
        trades = [{"id": i, "ent": p_ini, "pnl": 0.0, "on": True, "res": "", "liq": 0.0, "max": 0.0} for i in range(10)]
        
        # O LOOP PRINCIPAL AGORA TEM UM TRY PARA NÃO "SUMIR" TUDO
        while st.session_state.running and any(t['on'] for t in trades):
            try:
                p_now = check_preco(st.session_state.pair_address)
                if p_now is None: 
                    time.sleep(1) # Falha na API, aguarda e continua
                    continue

                price_place.metric("Preço Atual", f"{p_now:.8f}")

                for i, t in enumerate(trades):
                    if t['on']:
                        # --- TRAVA DE SEGURANÇA: SALDO ACABOU ---
                        # Se o saldo ficar abaixo de zero, encerra o trade imediatamente
                        if st.session_state.saldo_usd <= 0:
                            t['on'] = False
                            t['res'] = "STOP"
                            continue

                        t['pnl'] = ((p_now / t['ent']) - 1) * 100
                        if t['pnl'] > t['max']: t['max'] = t['pnl']

                        # Stop de Proteção (Breakeven)
                        st_dinamico = -3.0 # Stop fixo inicial
                        if t['max'] > 1.2: st_dinamico = 0.1

                        if t['pnl'] >= 2.5 or t['pnl'] <= st_dinamico:
                            t['on'] = False
                            t['res'] = "WIN" if t['pnl'] > 0 else "LOSS"
                            t['liq'] = (st.session_state.invest_usd * (t['pnl']/100)) - (st.session_state.invest_usd * TAXA_EXEC_SIMULADA)
                            st.session_state.saldo_usd += t['liq']

                        cor = "#00FF00" if t['pnl'] >= 0 else "#FF4B4B"
                        slots[i].markdown(f"**Ordem {i+1}:** {t['pnl']:+.2f}%", unsafe_allow_html=True)

                time.sleep(0.1)
            except Exception as e:
                # Se houver erro de rede, o bot não trava
                time.sleep(1)
                continue

        # Fim do Ciclo
        if st.session_state.running:
            liq_total = sum(tr['liq'] for tr in trades)
            st.session_state.resultados_ciclos.insert(0, {
                "CICLO": f"#{st.session_state.ciclo_atual}",
                "TOKEN": st.session_state.token_nome,
                "RESULTADO": formatar_moeda(liq_total, moeda_ref)
            })
            st.session_state.ciclo_atual += 1
            
            # Verificação final de saldo pós-ciclo
            if st.session_state.saldo_usd <= 0:
                st.session_state.running = False
                st.warning("BANCA ZERADA. Operações interrompidas.")
                time.sleep(3)
            
            st.rerun()
