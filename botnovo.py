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
TAXA_EXEC_SIMULADA = 0.01 

# ==========================================================
# ⚙️ FUNÇÕES DE SUPORTE
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
        return float(res['pair']['priceUsd'])
    except: return None

# ==========================================================
# 🖥️ INTERFACE v14.0
# ==========================================================
st.set_page_config(page_title="Sniper Pro v14", layout="wide")

with st.sidebar:
    st.header("⚙️ Painel de Controlo")
    
    # INTERRUPTOR DE MODO
    modo_operacao = st.toggle("🚀 MODO REAL (Mainnet)", value=False, help="Ative para conectar com a carteira Solana")
    
    if modo_operacao:
        st.warning("⚠️ O Modo Real requer uma chave RPC e Private Key configuradas.")
    else:
        st.success("📝 Modo Simulação Ativo")

    st.divider()
    moeda_ref = st.radio("Moeda:", ["USD", "BRL"])
    
    val_banca = st.number_input(f"Banca ({moeda_ref}):", 
                                value=float(st.session_state.saldo_usd * (TAXA_BRL if moeda_ref == "BRL" else 1.0)))
    if st.button("Atualizar Saldo"):
        st.session_state.saldo_usd = val_banca / (TAXA_BRL if moeda_ref == "BRL" else 1.0)
        st.rerun()

    st.divider()
    alvo_gain = st.slider("Alvo de Saída (%)", 0.5, 20.0, 2.5)
    stop_cfg = st.slider("Stop Loss Máximo (%)", 0.5, 15.0, 3.0)
    
    if st.button("Limpar Histórico"):
        st.session_state.resultados_ciclos = []
        st.session_state.ciclo_atual = 1
        st.rerun()

taxa_view = TAXA_BRL if moeda_ref == "BRL" else 1.0

if not st.session_state.running:
    st.title("🛡️ Sniper Pro v14")
    st.write(f"**Saldo em Carteira:** {formatar_moeda(st.session_state.saldo_usd, moeda_ref)}")
    
    ca = st.text_input("Token CA (Solana):", placeholder="Ex: 4k3DyjX...")
    invest_input = st.number_input(f"Valor por Ordem ({moeda_ref}):", value=10.0 * taxa_view)
    
    if st.button("⚡ INICIAR ESTRATÉGIA", use_container_width=True, type="primary"):
        info = obter_dados_fundo(ca)
        invest_total_usd = (invest_input / taxa_view) * 10
        if info and invest_total_usd <= st.session_state.saldo_usd:
            st.session_state.token_nome = info['nome']
            st.session_state.pair_address = info['pair']
            st.session_state.invest_usd = invest_input / taxa_view
            st.session_state.running = True
            st.session_state.ultimo_preco_track = info['preco']
            st.rerun()
        else:
            st.error("Erro de Validação: Verifique o CA ou Saldo.")
else:
    # --- PAINEL EM OPERAÇÃO ---
    txt_saldo = formatar_moeda(st.session_state.saldo_usd, moeda_ref)
    st.markdown(f"**{txt_saldo}**")
    
    col_info, col_btn = st.columns([3, 1])
    tag_modo = "🟢 REAL" if modo_operacao else "🔵 SIM"
    col_info.subheader(f"[{tag_modo}] Ciclo {st.session_state.ciclo_atual} | {st.session_state.token_nome}")
    
    if col_btn.button("🛑 PARAR AGORA"):
        st.session_state.running = False
        st.rerun()
    
    price_place = col_btn.empty()
    slots = [st.empty() for _ in range(10)]
    st.divider()
    t_resumo = st.empty()

    p_ini = check_preco(st.session_state.pair_address)
    if p_ini:
        trades = [{"id": i, "ent": p_ini, "pnl": 0.0, "on": True, "max": 0.0, "res": "", "liq": 0.0} for i in range(10)]

        while st.session_state.running and any(t['on'] for t in trades):
            p_now = check_preco(st.session_state.pair_address)
            if not p_now: continue

            # Update do Monitor de Preço
            seta = "▲" if p_now >= st.session_state.ultimo_preco_track else "▼"
            cor_s = "#00FF00" if p_now >= st.session_state.ultimo_preco_track else "#FF4B4B"
            price_place.markdown(f"<div style='text-align:center; font-weight:bold;'>{p_now:.8f} <span style='color:{cor_s};'>{seta}</span></div>", unsafe_allow_html=True)
            st.session_state.ultimo_preco_track = p_now

            for i, t in enumerate(trades):
                if t['on']:
                    t['pnl'] = ((p_now / t['ent']) - 1) * 100
                    if t['pnl'] > t['max']: t['max'] = t['pnl']

                    # --- LÓGICA DE PROTEÇÃO v14 (Trailing Breakeven) ---
                    st_dinamico = -stop_cfg
                    if t['max'] > 1.2: st_dinamico = 0.1 # Protege o capital se bater 1.2%

                    if t['pnl'] >= alvo_gain or t['pnl'] <= st_dinamico:
                        t['on'] = False
                        t['res'] = "WIN" if t['pnl'] > 0 else "LOSS"
                        
                        # Cálculo Líquido
                        t['liq'] = (st.session_state.invest_usd * (t['pnl']/100)) - (st.session_state.invest_usd * TAXA_EXEC_SIMULADA)
                        st.session_state.saldo_usd += t['liq']

                    cor = "#00FF00" if t['pnl'] >= 0 else "#FF4B4B"
                    simbolo = "R$" if moeda_ref == "BRL" else "$"
                    icon = "🔵" if t['on'] else ("✅" if t['res'] == "WIN" else "❌")
                    
                    slots[i].markdown(
                        f"<div style='font-family:monospace;'>{icon} <b>{simbolo}{st.session_state.invest_usd * taxa_view:.2f}</b> &nbsp; "
                        f"<span style='color:{cor}; font-weight:bold;'>{t['pnl']:+.2f}%</span></div>", 
                        unsafe_allow_html=True
                    )

            if st.session_state.resultados_ciclos:
                t_resumo.table(pd.DataFrame(st.session_state.resultados_ciclos).head(8))
            
            time.sleep(0.1)

        if st.session_state.running:
            liq_c = sum(tr['liq'] for tr in trades)
            pnl_c = (liq_c / (st.session_state.invest_usd * 10)) * 100
            st.session_state.resultados_ciclos.insert(0, {
                "CICLO": f"#{st.session_state.ciclo_atual}",
                "MODO": tag_modo,
                "TOKEN": st.session_state.token_nome,
                "PNL %": f"{pnl_c:+.2f}%",
                "LÍQUIDO": formatar_moeda(liq_c, moeda_ref)
            })
            st.session_state.ciclo_atual += 1
            st.rerun()
