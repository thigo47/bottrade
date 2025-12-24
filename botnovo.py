import streamlit as st
import time
import requests
import pandas as pd

# ==========================================================
# 🔑 ESTADO DA SESSÃO (Preservando tudo)
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
TAXA_EXEC_SIMULADA = 0.01 

# ==========================================================
# ⚙️ FUNÇÕES ESSENCIAIS
# ==========================================================
def formatar_moeda(valor_usd, moeda_ref):
    valor = valor_usd * TAXA_BRL if moeda_ref == "BRL" else valor_usd
    simbolo = "R$" if moeda_ref == "BRL" else "$"
    return f"{simbolo} {valor:,.2f}"

def obter_dados_fundo(ca):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        res = requests.get(url, timeout=5).json()
        if res.get('pairs'):
            p = res['pairs'][0]
            return {"nome": p['baseToken']['symbol'].upper(), "pair": p['pairAddress'], "preco": float(p['priceUsd'])}
    except: return None

def check_preco(pair_addr):
    try:
        url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{pair_addr}"
        res = requests.get(url, timeout=1).json()
        if 'pair' in res:
            return float(res['pair']['priceUsd'])
    except: return None
    return None

# ==========================================================
# 🖥️ INTERFACE v15.1
# ==========================================================
st.set_page_config(page_title="Sniper Pro v15.1", layout="wide")

with st.sidebar:
    st.header("⚙️ Painel de Controlo")
    modo_operacao = st.toggle("🚀 MODO REAL (Mainnet)", value=False)
    
    st.divider()
    moeda_ref = st.radio("Moeda:", ["USD", "BRL"])
    taxa_view = TAXA_BRL if moeda_ref == "BRL" else 1.0
    
    # Possibilidade de mudar o saldo (Recuperado)
    val_banca = st.number_input(f"Banca ({moeda_ref}):", 
                                value=float(st.session_state.saldo_usd * taxa_view))
    if st.button("Atualizar Saldo"):
        st.session_state.saldo_usd = val_banca / taxa_view
        st.rerun()

    st.divider()
    alvo_gain = st.slider("Alvo de Saída (%)", 0.5, 20.0, 2.5)
    stop_cfg = st.slider("Stop Loss Máximo (%)", 0.5, 15.0, 3.0)
    
    if st.button("Limpar Histórico"):
        st.session_state.resultados_ciclos = []
        st.session_state.ciclo_atual = 1
        st.rerun()

# --- TELA INICIAL ---
if not st.session_state.running:
    st.title("🛡️ Sniper Pro v15.1")
    st.write(f"**Saldo disponível:** {formatar_moeda(st.session_state.saldo_usd, moeda_ref)}")
    
    ca = st.text_input("Token CA (Solana):")
    invest_input = st.number_input(f"Valor por Ordem ({moeda_ref}):", value=10.0 * taxa_view)
    
    if st.button("⚡ INICIAR ESTRATÉGIA", use_container_width=True, type="primary"):
        invest_total_usd = (invest_input / taxa_view) * 10
        if invest_total_usd > st.session_state.saldo_usd:
            st.error("Saldo insuficiente para abrir 10 ordens.")
        else:
            info = obter_dados_fundo(ca)
            if info:
                st.session_state.token_nome = info['nome']
                st.session_state.pair_address = info['pair']
                st.session_state.invest_usd = invest_input / taxa_view
                st.session_state.running = True
                st.session_state.ultimo_preco_track = info['preco']
                st.rerun()
            else: st.error("Erro ao localizar Token.")
else:
    # --- PAINEL EM OPERAÇÃO (Recuperando Visual Minimalista) ---
    txt_saldo_topo = formatar_moeda(st.session_state.saldo_usd, moeda_ref)
    st.markdown(f"**{txt_saldo_topo}**")
    
    col_info, col_btn = st.columns([3, 1])
    tag_modo = "🟢 REAL" if modo_operacao else "🔵 SIM"
    col_info.subheader(f"[{tag_modo}] Ciclo {st.session_state.ciclo_atual} | {st.session_state.token_nome}")
    
    if col_btn.button("🛑 PARAR AGORA", use_container_width=True):
        st.session_state.running = False
        st.rerun()
    
    price_place = col_btn.empty()
    slots = [st.empty() for _ in range(10)]
    st.divider()
    t_resumo = st.empty()

    # Ponto de entrada
    p_ini = check_preco(st.session_state.pair_address)
    if p_ini:
        trades = [{"id": i, "ent": p_ini, "pnl": 0.0, "on": True, "max": 0.0, "res": "", "liq": 0.0} for i in range(10)]

        # LOOP PRINCIPAL PROTEGIDO
        while st.session_state.running and any(t['on'] for t in trades):
            try:
                p_now = check_preco(st.session_state.pair_address)
                if p_now is None: 
                    time.sleep(0.5)
                    continue

                # Monitor de Preço (Recuperado)
                seta = "▲" if p_now >= st.session_state.ultimo_preco_track else "▼"
                cor_s = "#00FF00" if p_now >= st.session_state.ultimo_preco_track else "#FF4B4B"
                price_place.markdown(f"<div style='text-align:center; font-weight:bold; font-size:18px;'>{p_now:.8f} <span style='color:{cor_s};'>{seta}</span></div>", unsafe_allow_html=True)
                st.session_state.ultimo_preco_track = p_now

                for i, t in enumerate(trades):
                    if t['on']:
                        # --- PROTEÇÃO DE MARGEM: SALDO ACABOU ---
                        if st.session_state.saldo_usd <= 0:
                            t['on'] = False
                            t['res'] = "LOSS"
                            t['liq'] = -st.session_state.invest_usd # Perda da margem
                            continue

                        t['pnl'] = ((p_now / t['ent']) - 1) * 100
                        if t['pnl'] > t['max']: t['max'] = t['pnl']

                        # Lógica Breakeven (Recuperada)
                        st_dinamico = -stop_cfg
                        if t['max'] > 1.2: st_dinamico = 0.1

                        if t['pnl'] >= alvo_gain or t['pnl'] <= st_dinamico:
                            t['on'] = False
                            t['res'] = "WIN" if t['pnl'] > 0 else "LOSS"
                            t['liq'] = (st.session_state.invest_usd * (t['pnl']/100)) - (st.session_state.invest_usd * TAXA_EXEC_SIMULADA)
                            st.session_state.saldo_usd += t['liq']

                        # Sinais e Cores (Recuperados)
                        cor_pnl = "#00FF00" if t['pnl'] >= 0 else "#FF4B4B"
                        simb = "R$" if moeda_ref == "BRL" else "$"
                        icon = "🔵" if t['on'] else ("✅" if t['res'] == "WIN" else "❌")
                        
                        slots[i].markdown(
                            f"<div style='font-family:monospace; font-size:14px;'>{icon} <b>{simb}{st.session_state.invest_usd * taxa_view:.2f}</b> &nbsp; "
                            f"<span style='color:{cor_pnl}; font-weight:bold;'>{t['pnl']:+.2f}%</span></div>", 
                            unsafe_allow_html=True
                        )

                if st.session_state.resultados_ciclos:
                    t_resumo.table(pd.DataFrame(st.session_state.resultados_ciclos).head(8))
                
                time.sleep(0.1)
                
            except Exception:
                time.sleep(1) # Em caso de erro, espera e continua sem quebrar a tela
                continue

        # Finalização de Ciclo
        if st.session_state.running:
            liq_ciclo = sum(tr['liq'] for tr in trades)
            pnl_final = (liq_ciclo / (st.session_state.invest_usd * 10)) * 100
            st.session_state.resultados_ciclos.insert(0, {
                "CICLO": f"#{st.session_state.ciclo_atual}",
                "MODO": tag_modo,
                "TOKEN": st.session_state.token_nome,
                "PNL %": f"{pnl_final:+.2f}%",
                "LÍQUIDO": formatar_moeda(liq_ciclo, moeda_ref)
            })
            st.session_state.ciclo_atual += 1
            
            if st.session_state.saldo_usd <= 0:
                st.session_state.running = False
                st.warning("⚠️ SALDO ESGOTADO. Deposite para continuar.")
                time.sleep(2)
            
            st.rerun()
