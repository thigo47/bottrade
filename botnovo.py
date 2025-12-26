import streamlit as st
import time
import requests
import pandas as pd
from datetime import datetime

# ==========================================================
# 💾 BANCO DE DADOS
# ==========================================================
@st.cache_resource
def get_db():
    return {"saldo": 1000.0, "historico": [], "ciclo": 1}

db = get_db()

# ==========================================================
# 🧠 CÉREBRO IA v24 - DECISÃO EM TEMPO REAL
# ==========================================================
def motor_ia_decisao(pnl, pnl_max, historico_precos):
    """
    Decide o momento exato de sair baseado no comportamento do preço.
    Retorna (True/False, Motivo)
    """
    if len(historico_precos) < 5: return False, ""

    # 1. PROTEÇÃO CONTRA QUEDA BRUSCA (FLASH DUMP)
    preco_atual = historico_precos[-1]
    preco_anterior = historico_precos[-2]
    queda_rapida = ((preco_atual / preco_anterior) - 1) * 100
    
    if queda_rapida < -1.5: # Caiu 1.5% em 0.1s? Sai fora.
        return True, "IA: Flash Dump Detectado"

    # 2. SURFANDO A TENDÊNCIA (TRAILING INTELIGENTE)
    if pnl_max > 2.0:
        distancia_do_topo = pnl_max - pnl
        # Quanto mais ganhamos, menos aceitamos perder de volta
        limite_retorno = 0.5 if pnl_max < 5.0 else 1.2
        if distancia_do_topo > limite_retorno:
            return True, f"IA: Lucro Realizado ({pnl:+.2f}%)"

    # 3. STOP LOSS DINÂMICO (BASEADO NA VOLATILIDADE)
    # Se nunca ficou positivo e caiu mais de 2.5%, corta o risco
    if pnl < -2.5 and pnl_max < 0.5:
        return True, "IA: Risco Excessivo (Stop)"

    # 4. EXAUSTÃO (PREÇO PARADO NO TOPO)
    if pnl > 1.0:
        ultimos_3 = historico_precos[-3:]
        if max(ultimos_3) == min(ultimos_3): # Preço não mexe mais
            return True, "IA: Exaustão de Compra"

    return False, ""

# ==========================================================
# ⚙️ FUNÇÕES DE MERCADO
# ==========================================================
def buscar_melhor_pool(ca):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        res = requests.get(url, timeout=5).json()
        pools = [p for p in res['pairs'] if p['chainId'] == 'solana' and 'SOL' in p['quoteToken']['symbol']]
        if pools:
            melhor = max(pools, key=lambda x: float(x.get('liquidity', {}).get('usd', 0)))
            return {"nome": melhor['baseToken']['symbol'], "pair": melhor['pairAddress'], "preco": float(melhor['priceUsd'])}
    except: return None

def monitorar_preco_pool(pair_address):
    try:
        url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{pair_address}"
        return float(requests.get(url, timeout=1).json()['pair']['priceUsd'])
    except: return None

# ==========================================================
# 🖥️ INTERFACE v24.0 (FULL AI)
# ==========================================================
st.set_page_config(page_title="Sniper Pro v24 - Full AI", layout="wide")

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "running" not in st.session_state: st.session_state.running = False

if not st.session_state.logged_in:
    st.title("🤖 Sniper Full AI")
    u, p = st.text_input("Usuário"), st.text_input("Senha", type="password")
    if st.button("Aceder ao Sistema"):
        if u == "admin" and p == "1234":
            st.session_state.logged_in = True
            st.rerun()
else:
    with st.sidebar:
        st.header("📊 Painel de Controlo")
        moeda = st.radio("Moeda:", ["USD", "BRL"])
        taxa = 5.05 if moeda == "BRL" else 1.0
        st.metric("Banca Total", f"{'R$' if moeda == 'BRL' else '$'} {db['saldo'] * taxa:,.2f}")
        
        st.info("💡 A IA está configurada para Autopiloto. Os sliders foram removidos para decisão 100% algorítmica.")
        
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.rerun()

    if not st.session_state.running:
        st.title("🚀 Sniper Pro v24.0 - Autopiloto")
        ca_input = st.text_input("Endereço do Token (CA):")
        invest_input = st.number_input(f"Valor por Ordem ({moeda})", value=10.0 * taxa)

        if st.button("⚡ ACTIVAR IA"):
            data = buscar_melhor_pool(ca_input.strip())
            if data:
                st.session_state.update({"t_nome": data['nome'], "t_pair": data['pair'], 
                                        "t_preco": data['preco'], "invest_usd": invest_input/taxa, "running": True})
                st.rerun()
    else:
        # EXECUÇÃO IA
        col_head, col_ctrl = st.columns([3, 1])
        col_head.subheader(f"🤖 IA Operando: {st.session_state.t_nome}")
        if col_ctrl.button("🛑 DESATIVAR IA", use_container_width=True):
            st.session_state.running = False
            st.rerun()

        monitor_preco, saldo_place = col_ctrl.empty(), col_ctrl.empty()
        slots = [st.empty() for _ in range(10)]
        
        while st.session_state.running:
            p_start = monitorar_preco_pool(st.session_state.t_pair)
            if not p_start: continue
            
            # Reset de Ciclo
            trades = [{"ent": p_start, "pnl": 0.0, "on": True, "max": 0.0, "res": "", "hist_p": [p_start]} for _ in range(10)]
            ultimo_p = p_start

            while any(t['on'] for t in trades) and st.session_state.running:
                p_now = monitorar_preco_pool(st.session_state.t_pair)
                if p_now:
                    # Atualiza Global
                    cor = "#00FF00" if p_now >= ultimo_p else "#FF4B4B"
                    monitor_preco.markdown(f"<h2 style='text-align:center; color:{cor};'>{p_now:.8f}</h2>", unsafe_allow_html=True)
                    saldo_place.markdown(f"<p style='text-align:center;'>Saldo: {db['saldo']*taxa:,.2f}</p>", unsafe_allow_html=True)
                    ultimo_p = p_now

                    for i, t in enumerate(trades):
                        if t['on']:
                            t['pnl'] = ((p_now / t['ent']) - 1) * 100
                            if t['pnl'] > t['max']: t['max'] = t['pnl']
                            t['hist_p'].append(p_now)
                            if len(t['hist_p']) > 10: t['hist_p'].pop(0)

                            # DECISÃO DA IA
                            deve_fechar, motivo = motor_ia_decisao(t['pnl'], t['max'], t['hist_p'])
                            
                            if deve_fechar:
                                t['on'] = False
                                t['res'] = motivo
                                liq = (st.session_state.invest_usd * (t['pnl']/100)) - (st.session_state.invest_usd * 0.01)
                                db['saldo'] += liq

                            icon = "🔵" if t['on'] else "🤖"
                            slots[i].markdown(f"{icon} Ordem {i+1}: **{t['pnl']:+.2f}%** | {t['res']}")
                
                time.sleep(0.05)
            
            # Log de Ciclo
            db['historico'].insert(0, {"CICLO": f"#{db['ciclo']}", "STATUS": "Finalizado pela IA"})
            db['ciclo'] += 1
