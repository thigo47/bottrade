import streamlit as st
import time
import requests
import pandas as pd
import os

# ==========================================================
# 💾 INICIALIZAÇÃO SEGURA DO ESTADO
# ==========================================================
if "saldo" not in st.session_state: st.session_state.saldo = 1000.0
if "running" not in st.session_state: st.session_state.running = False
if "historico" not in st.session_state: st.session_state.historico = []
if "ciclo" not in st.session_state: st.session_state.ciclo = 1
if "auth" not in st.session_state: st.session_state.auth = False

# ==========================================================
# ⚙️ FUNÇÕES DE MOTOR
# ==========================================================
def fetch_price(ca):
    try:
        url = f"https://api.jup.ag/price/v2?ids={ca}"
        response = requests.get(url, timeout=5)
        data = response.json()
        price = data.get('data', {}).get(ca, {}).get('price')
        if price is not None:
            return float(price)
    except:
        pass
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        res = requests.get(url, timeout=5).json()
        price = res.get('pairs', [{}])[0].get('priceUsd')
        if price is not None:
            return float(price)
    except:
        pass
    return None

def get_token_info(ca):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        res = requests.get(url, timeout=5).json()
        return res.get('pairs', [{}])[0].get('baseToken', {}).get('symbol', 'TOKEN')
    except:
        return "TOKEN"

# ==========================================================
# 🧠 CÉREBRO IA v29
# ==========================================================
def ia_brain(pnl, pnl_max, h_precos):
    if len(h_precos) < 3: return False, ""
    if pnl_max > 1.0 and (pnl < pnl_max - 0.2):
        return True, "IA: Realização de Lucro"
    if pnl < -2.0:
        return True, "IA: Stop Preventivo"
    return False, ""

# ==========================================================
# 💱 CÂMBIO DINÂMICO
# ==========================================================
@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        data = requests.get(url, timeout=5).json()
        return float(data['rates'].get('BRL', 5.05))
    except:
        return 5.05

# ==========================================================
# 🖥️ INTERFACE STREAMLIT
# ==========================================================
st.set_page_config(page_title="Sniper Pro v29", layout="wide")

SENHA = os.getenv('SNIPER_SENHA', '1234')

if not st.session_state.auth:
    st.title("🛡️ Acesso Sniper v29")
    senha = st.text_input("Senha de Operação", type="password")
    if st.button("Entrar"):
        if senha == SENHA:
            st.session_state.auth = True
            st.rerun()
else:
    with st.sidebar:
        st.header("💰 Gestão Financeira")
        st.session_state.moeda = st.radio("Exibição:", ["USD", "BRL"])
        st.session_state.taxa = 1.0 if st.session_state.moeda == "USD" else get_exchange_rate()

        st.metric("Saldo", f"{'R\( ' if st.session_state.moeda == 'BRL' else ' \)'} {st.session_state.saldo * st.session_state.taxa:,.2f}")

        novo_s = st.number_input("Alterar Saldo", value=float(st.session_state.saldo * st.session_state.taxa))
        if st.button("💾 Salvar Novo Saldo"):
            st.session_state.saldo = novo_s / st.session_state.taxa
            st.rerun()

        if st.button("🔴 Logout"):
            st.session_state.auth = False
            st.rerun()

    if not st.session_state.running:
        st.title("🚀 Sniper Pro v29.0 - Atualização Automática Estável")
        st.write("Usando st.autorefresh para updates suaves em tempo real")

        ca_input = st.text_input("CA do Token (Solana):")
        invest_input = st.number_input(f"Valor por Ordem ({st.session_state.moeda})", value=10.0 * st.session_state.taxa)

        if st.button("⚡ INICIAR MOTOR IA"):
            price_test = fetch_price(ca_input.strip())
            if price_test:
                st.session_state.t_nome = get_token_info(ca_input.strip())
                st.session_state.ca = ca_input.strip()
                st.session_state.invest_usd = invest_input / st.session_state.taxa

                p_inicio = price_test
                st.session_state.trades = [{"ent": p_inicio, "pnl": 0.0, "on": True, "max": 0.0, "res": "", "h": [p_inicio]} for _ in range(10)]
                st.session_state.order_texts = [""] * 10

                st.session_state.running = True
                st.rerun()
            else:
                st.error("Erro: Não foi possível detectar o preço. Verifique o CA.")
    else:
        col_title, col_btn = st.columns([3, 1])
        col_title.subheader(f"🟢 Monitorando: {st.session_state.t_nome}")
        if col_btn.button("🛑 DESATIVAR BOT", use_container_width=True):
            st.session_state.running = False
            st.rerun()

        # Auto refresh a cada 2 segundos (mude para 1000 para 1s)
        st.autorefresh(interval=2000, key="auto")

        # Fetch preço atual
        p_atual = fetch_price(st.session_state.ca)
        if p_atual:
            ultima_atualizacao = time.strftime('%H:%M:%S')
        else:
            p_atual = st.session_state.trades[0]['ent'] if st.session_state.trades else 0
            ultima_atualizacao = "Erro no fetch"

        # Atualiza UI
        st.markdown(f"### Preço Atual: `{p_atual:.10f}` (às {ultima_atualizacao})")
        st.markdown(f"**Banca:** {'R\( ' if st.session_state.moeda == 'BRL' else ' \)'} {st.session_state.saldo * st.session_state.taxa:,.2f}")

        for i, t in enumerate(st.session_state.trades):
            if t['on']:
                t['pnl'] = ((p_atual / t['ent']) - 1) * 100
                if t['pnl'] > t['max']: t['max'] = t['pnl']
                t['h'].append(p_atual)
                if len(t['h']) > 5: t['h'].pop(0)

                fechar, motivo = ia_brain(t['pnl'], t['max'], t['h'])
                if fechar:
                    t['on'] = False
                    t['res'] = motivo
                    lucro_usd = st.session_state.invest_usd * (t['pnl'] / 100)
                    st.session_state.saldo += lucro_usd
                    st.session_state.historico.append({
                        'ciclo': st.session_state.ciclo,
                        'ordem': i+1,
                        'pnl': round(t['pnl'], 2),
                        'motivo': motivo
                    })

                cor = "#00FF00" if t['pnl'] >= 0 else "#FF4B4B"
                status_txt = "🔵" if t['on'] else "🤖"
                st.session_state.order_texts[i] = f"{status_txt} Ordem {i+1}: <b style='color:{cor}'>{t['pnl']:+.2f}%</b> | {t['res']}"

            st.markdown(st.session_state.order_texts[i], unsafe_allow_html=True)

        if st.session_state.historico:
            st.subheader("📜 Histórico de Trades")
            df_hist = pd.DataFrame(st.session_state.historico)
            st.dataframe(df_hist)

        # Incrementa ciclo ao final de cada "ciclo manual" se quiser
        if p_atual != st.session_state.trades[0]['ent']:  # Só se preço mudou significativamente
            pass  # Pode adicionar lógica aqui se quiser ciclos separados