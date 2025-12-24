import streamlit as st
import time
import requests
import pandas as pd

# ==========================================================
# 💾 PERSISTÊNCIA DE DADOS (CACHE DE LONGO PRAZO)
# ==========================================================
# Isso mantém os dados vivos no servidor mesmo que você feche a aba
@st.cache_resource
def banco_dados_persistente():
    return {
        "saldo": 1000.0,
        "historico": [],
        "ciclo": 1
    }

db = banco_dados_persistente()

# ==========================================================
# 🔑 LOGIN E SESSÃO
# ==========================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def tela_login():
    st.title("🛡️ Sniper Pro Login")
    user = st.text_input("Usuário")
    pw = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if user == "admin" and pw == "1234":
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Credenciais Inválidas")

# ==========================================================
# ⚙️ FUNÇÕES DE PREÇO (Preservando a velocidade)
# ==========================================================
def check_preco(pair_addr):
    try:
        url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{pair_addr}"
        res = requests.get(url, timeout=1).json()
        if 'pair' in res:
            return float(res['pair']['priceUsd'])
    except: return None
    return None

# ==========================================================
# 🛰️ INTERFACE PRINCIPAL
# ==========================================================
if not st.session_state.logged_in:
    tela_login()
else:
    st.set_page_config(page_title="Sniper Pro v18", layout="wide")

    with st.sidebar:
        st.header("👤 Admin")
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.rerun()
        
        st.divider()
        moeda_ref = st.radio("Moeda:", ["USD", "BRL"])
        taxa_view = 5.05 if moeda_ref == "BRL" else 1.0
        
        st.metric("Saldo Atual", f"{'R$' if moeda_ref == 'BRL' else '$'} {db['saldo'] * taxa_view:,.2f}")
        
        # Possibilidade de mudar o saldo (Recuperada)
        val_banca = st.number_input(f"Ajustar Banca ({moeda_ref})", value=db['saldo'] * taxa_view)
        if st.button("Salvar Saldo"):
            db['saldo'] = val_banca / taxa_view
            st.success("Saldo Atualizado!")
            st.rerun()

        st.divider()
        alvo_gain = st.slider("Alvo de Saída (%)", 0.5, 20.0, 2.5)
        stop_cfg = st.slider("Stop Loss Máximo (%)", 0.5, 15.0, 3.0)

    # --- LÓGICA DE TRADING ---
    if "running" not in st.session_state: st.session_state.running = False

    if not st.session_state.running:
        st.title("🚀 Terminal Sniper v18")
        ca = st.text_input("Token CA (Solana):")
        invest_input = st.number_input(f"Valor Ordem ({moeda_ref}):", value=10.0 * taxa_view)
        
        if st.button("⚡ INICIAR ESTRATÉGIA", use_container_width=True, type="primary"):
            # Validação antes de rodar
            invest_usd = invest_input / taxa_view
            if (invest_usd * 10) > db['saldo']:
                st.error("Saldo insuficiente para 10 ordens!")
            else:
                try:
                    url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
                    info = requests.get(url).json()['pairs'][0]
                    st.session_state.token_nome = info['baseToken']['symbol']
                    st.session_state.pair_addr = info['pairAddress']
                    st.session_state.invest_usd = invest_usd
                    st.session_state.running = True
                    st.rerun()
                except: st.error("Token não encontrado.")
    else:
        # --- PAINEL DE OPERAÇÃO ATIVO ---
        st.markdown(f"**Saldo: {'R$' if moeda_ref == 'BRL' else '$'} {db['saldo'] * taxa_view:,.2f}**")
        
        col_info, col_btn = st.columns([3, 1])
        col_info.subheader(f"🛰️ Ciclo #{db['ciclo']} | {st.session_state.token_nome}")
        
        if col_btn.button("🛑 PARAR AGORA", use_container_width=True):
            st.session_state.running = False
            st.rerun()
        
        price_place = col_btn.empty()
        slots = [st.empty() for _ in range(10)]
        t_resumo = st.empty()

        p_ini = check_preco(st.session_state.pair_addr)
        if p_ini:
            trades = [{"ent": p_ini, "pnl": 0.0, "on": True, "max": 0.0, "res": "", "liq": 0.0} for _ in range(10)]
            ultimo_p = p_ini

            while st.session_state.running and any(t['on'] for t in trades):
                p_now = check_preco(st.session_state.pair_addr)
                if p_now is None: 
                    time.sleep(0.5)
                    continue

                # Monitor de Preço (Minimalista com Seta)
                seta = "▲" if p_now >= ultimo_p else "▼"
                cor_s = "#00FF00" if p_now >= ultimo_p else "#FF4B4B"
                price_place.markdown(f"<div style='text-align:center; font-size:18px;'>{p_now:.8f} <span style='color:{cor_s};'>{seta}</span></div>", unsafe_allow_html=True)
                ultimo_p = p_now

                for i, t in enumerate(trades):
                    if t['on']:
                        # Proteção de Saldo Negativo
                        if db['saldo'] <= 0:
                            t['on'] = False
                            t['res'] = "LOSS"
                            t['liq'] = -st.session_state.invest_usd
                            continue

                        t['pnl'] = ((p_now / t['ent']) - 1) * 100
                        if t['pnl'] > t['max']: t['max'] = t['pnl']

                        # Lógica Breakeven
                        st_din = -stop_cfg
                        if t['max'] > 1.2: st_din = 0.1

                        if t['pnl'] >= alvo_gain or t['pnl'] <= st_din:
                            t['on'] = False
                            t['res'] = "WIN" if t['pnl'] > 0 else "LOSS"
                            t['liq'] = (st.session_state.invest_usd * (t['pnl']/100)) - (st.session_state.invest_usd * 0.01)
                            db['saldo'] += t['liq']

                        # Sinais Visuais
                        cor_p = "#00FF00" if t['pnl'] >= 0 else "#FF4B4B"
                        icon = "🔵" if t['on'] else ("✅" if t['res'] == "WIN" else "❌")
                        slots[i].markdown(f"{icon} Order {i+1}: <span style='color:{cor_p}; font-weight:bold;'>{t['pnl']:+.2f}%</span>", unsafe_allow_html=True)

                time.sleep(0.1)

            # Fim do Ciclo
            if st.session_state.running:
                liq_c = sum(tr['liq'] for tr in trades)
                db['historico'].insert(0, {
                    "CICLO": f"#{db['ciclo']}",
                    "TOKEN": st.session_state.token_nome,
                    "RESULTADO": "WIN" if liq_c > 0 else "LOSS",
                    "LÍQUIDO": f"{'R$' if moeda_ref == 'BRL' else '$'} {liq_c * taxa_view:,.2f}"
                })
                db['ciclo'] += 1
                st.rerun()

    st.divider()
    st.subheader("📜 Histórico de Ciclos (Persistente)")
    if db['historico']:
        st.table(pd.DataFrame(db['historico']).head(10))
