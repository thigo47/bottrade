import streamlit as st
import time
import requests
import pandas as pd
from datetime import datetime

# ==========================================================
# 💾 BANCO DE DADOS EM CACHE
# ==========================================================
@st.cache_resource
def get_db():
    return {"saldo": 1000.0, "historico": [], "ciclo": 1}

db = get_db()

# ==========================================================
# ⚙️ FUNÇÕES DE API (CORRIGIDAS)
# ==========================================================
def buscar_token_com_retry(ca, tentativas=3):
    if not ca or len(ca.strip()) < 30: # CAs da Solana têm ~44 caracteres
        return None

    for i in range(tentativas):
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data.get('pairs'):
                    # Filtro para pegar o par com mais liquidez na Solana
                    pairs = [p for p in data['pairs'] if p.get('chainId') == 'solana']
                    if pairs:
                        p = pairs[0]
                        return {
                            "nome": p['baseToken']['symbol'].upper(),
                            "pair": p.get('pairAddress', ''),
                            "preco": float(p['priceUsd'])
                        }
        except:
            time.sleep(1)
    return None

def check_preco_fast(pair_addr):
    if not pair_addr: return None
    try:
        url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{pair_addr}"
        res = requests.get(url, timeout=2)
        if res.status_code == 200:
            data = res.json()
            return float(data['pair']['priceUsd'])
    except: pass
    return None

# ==========================================================
# 🖥️ INTERFACE
# ==========================================================
st.set_page_config(page_title="Sniper Pro v19", layout="wide")

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "running" not in st.session_state: st.session_state.running = False

if not st.session_state.logged_in:
    st.title("🛡️ Acesso Restrito")
    u = st.text_input("Usuário")
    p = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "admin" and p == "1234":
            st.session_state.logged_in = True
            st.rerun()
        else: st.error("Incorreto.")
else:
    # --- SIDEBAR ---
    with st.sidebar:
        st.header(f"💰 Banca")
        moeda_ref = st.radio("Moeda:", ["USD", "BRL"])
        taxa = 5.05 if moeda_ref == "BRL" else 1.0
        st.metric("Saldo Atual", f"{'R$' if moeda_ref == 'BRL' else '$'} {db['saldo'] * taxa:,.2f}")
        
        novo_saldo = st.number_input("Ajustar Saldo", value=float(db['saldo'] * taxa))
        if st.button("💾 Salvar Saldo"):
            db['saldo'] = novo_saldo / taxa
            st.rerun()

        st.divider()
        alvo = st.slider("Alvo (%)", 0.5, 20.0, 2.5)
        stop = st.slider("Stop (%)", 0.5, 15.0, 3.0)
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.rerun()

    # --- CORPO DO BOT ---
    if not st.session_state.running:
        st.title("🚀 Sniper Pro v19")
        ca_input = st.text_input("CA do Token (Solana):")
        invest_input = st.number_input(f"Valor p/ Ordem ({moeda_ref})", value=10.0 * taxa)

        if st.button("INICIAR OPERAÇÃO", use_container_width=True, type="primary"):
            token_data = buscar_token_com_retry(ca_input.strip())
            if token_data:
                st.session_state.t_nome = token_data['nome']
                st.session_state.t_pair = token_data['pair']
                st.session_state.t_preco = token_data['preco']
                st.session_state.invest_usd = invest_input / taxa
                st.session_state.running = True
                st.rerun()
            else: st.error("Token não encontrado.")
    else:
        # PAINEL DE EXECUÇÃO
        col_head, col_ctrl = st.columns([3, 1])
        col_head.subheader(f"🛰️ Ciclo #{db['ciclo']} | {st.session_state.t_nome}")
        
        if col_ctrl.button("🛑 PARAR AGORA", use_container_width=True):
            st.session_state.running = False
            st.rerun()

        monitor_preco = col_ctrl.empty()
        slots = [st.empty() for _ in range(10)]
        area_hist = st.empty()

        # BUG FIX: Os trades devem ser resetados no início de cada ciclo
        trades = [{"ent": st.session_state.t_preco, "pnl": 0.0, "on": True, "max": 0.0, "res": "", "liq": 0.0} for _ in range(10)]
        ultimo_p = st.session_state.t_preco

        while st.session_state.running and any(t['on'] for t in trades):
            p_now = check_preco_fast(st.session_state.t_pair)
            if p_now:
                seta = "▲" if p_now >= ultimo_p else "▼"
                cor_s = "#00FF00" if p_now >= ultimo_p else "#FF4B4B"
                monitor_preco.markdown(f"<div style='text-align:center; font-size:18px; font-weight:bold;'>{p_now:.8f} <span style='color:{cor_s};'>{seta}</span></div>", unsafe_allow_html=True)
                ultimo_p = p_now

                for i, t in enumerate(trades):
                    if t['on']:
                        # BUG FIX: Se o saldo acabar NO MEIO do ciclo, fechar ordens abertas
                        if db['saldo'] < st.session_state.invest_usd:
                            t['on'] = False
                            t['res'] = "STOP"
                            continue

                        t['pnl'] = ((p_now / t['ent']) - 1) * 100
                        if t['pnl'] > t['max']: t['max'] = t['pnl']
                        
                        st_din = -stop
                        if t['max'] > 1.2: st_din = 0.1

                        if t['pnl'] >= alvo or t['pnl'] <= st_din:
                            t['on'] = False
                            t['res'] = "WIN" if t['pnl'] > 0 else "LOSS"
                            t['liq'] = (st.session_state.invest_usd * (t['pnl']/100)) - (st.session_state.invest_usd * 0.01)
                            db['saldo'] += t['liq']

                        cor_pnl = "#00FF00" if t['pnl'] >= 0 else "#FF4B4B"
                        icon = "🔵" if t['on'] else ("✅" if t['res'] == "WIN" else "❌")
                        slots[i].markdown(f"{icon} Ordem {i+1}: <span style='color:{cor_pnl}; font-weight:bold;'>{t['pnl']:+.2f}%</span>", unsafe_allow_html=True)
            
            time.sleep(0.1)

        # BUG FIX: Bloco de finalização fora do while para evitar loops infinitos
        if st.session_state.running:
            liq_final = sum(tr['liq'] for tr in trades)
            db['historico'].insert(0, {
                "CICLO": f"#{db['ciclo']}",
                "TOKEN": st.session_state.t_nome,
                "PNL": f"{(liq_final/(st.session_state.invest_usd*10))*100:+.2f}%",
                "LÍQUIDO": f"{'R$' if moeda_ref == 'BRL' else '$'} {liq_final * taxa:,.2f}",
                "HORA": datetime.now().strftime("%H:%M:%S")
            })
            db['ciclo'] += 1
            st.session_state.running = False # Reset para próxima operação
            st.rerun()

    if db['historico']:
        st.divider()
        st.subheader("📜 Últimos Ciclos")
        st.table(pd.DataFrame(db['historico']).head(10))
