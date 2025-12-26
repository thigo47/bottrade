import streamlit as st
import requests
import pandas as pd
import time
import os

# ==========================================================
# INICIALIZAÇÃO DO ESTADO
# ==========================================================
if "saldo" not in st.session_state: 
    st.session_state.saldo = 1000.0
if "running" not in st.session_state: 
    st.session_state.running = False
if "historico" not in st.session_state: 
    st.session_state.historico = []
if "ciclo" not in st.session_state: 
    st.session_state.ciclo = 1
if "auth" not in st.session_state: 
    st.session_state.auth = False
if "moeda" not in st.session_state:
    st.session_state.moeda = "USD"
if "taxa" not in st.session_state:
    st.session_state.taxa = 1.0

# ==========================================================
# FUNÇÕES DE PREÇO
# ==========================================================
def fetch_price(ca):
    """Busca preço do token"""
    try:
        url = f"https://api.jup.ag/price/v2?ids={ca}"
        data = requests.get(url, timeout=5).json()
        price = data.get('data', {}).get(ca, {}).get('price')
        if price is not None:
            return float(price)
    except:
        pass
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        data = requests.get(url, timeout=5).json()
        price = data.get('pairs', [{}])[0].get('priceUsd')
        if price is not None:
            return float(price)
    except:
        pass
    return None

def get_token_info(ca):
    """Busca informação do token"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        data = requests.get(url, timeout=5).json()
        return data.get('pairs', [{}])[0].get('baseToken', {}).get('symbol', 'TOKEN')
    except:
        return "TOKEN"

# ==========================================================
# CÉREBRO IA
# ==========================================================
def ia_brain(pnl, pnl_max, h_precos):
    """Lógica de decisão do bot"""
    if len(h_precos) < 3: 
        return False, ""
    if pnl_max > 1.0 and pnl < pnl_max - 0.2:
        return True, "IA: Realização de Lucro"
    if pnl < -2.0:
        return True, "IA: Stop Preventivo"
    return False, ""

# ==========================================================
# CÂMBIO
# ==========================================================
@st.cache_data(ttl=3600)
def get_exchange_rate():
    """Busca taxa de câmbio USD/BRL"""
    try:
        data = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5).json()
        return float(data['rates'].get('BRL', 5.05))
    except:
        return 5.05

# ==========================================================
# INTERFACE
# ==========================================================
st.set_page_config(page_title="Sniper Pro v29", layout="wide")

# Segurança - senha por variável de ambiente
SENHA = os.getenv('SNIPER_SENHA')
if not SENHA:
    st.error("❌ Configure a variável de ambiente SNIPER_SENHA")
    st.stop()

if not st.session_state.auth:
    st.title("🛡️ Acesso Sniper v29")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if senha == SENHA:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Senha incorreta!")
else:
    with st.sidebar:
        st.header("💰 Banca")
        
        # Seleção de moeda
        moeda_anterior = st.session_state.moeda
        st.session_state.moeda = st.radio("Moeda", ["USD", "BRL"])
        
        # Atualizar taxa se moeda mudou
        if st.session_state.moeda != moeda_anterior or st.session_state.taxa == 1.0:
            if st.session_state.moeda == "BRL":
                st.session_state.taxa = get_exchange_rate()
            else:
                st.session_state.taxa = 1.0
        
        # Exibir saldo
        saldo_formatado = st.session_state.saldo * st.session_state.taxa
        if st.session_state.moeda == "BRL":
            st.metric("Saldo", f"R$ {saldo_formatado:,.2f}")
        else:
            st.metric("Saldo", f"$ {saldo_formatado:,.2f}")
        
        # Ajustar saldo
        st.divider()
        st.subheader("🔄 Ajustes")
        novo_saldo = st.number_input(
            f"Novo saldo ({st.session_state.moeda})", 
            value=float(saldo_formatado),
            min_value=0.0
        )
        
        if st.button("Salvar Saldo"):
            st.session_state.saldo = novo_saldo / st.session_state.taxa
            st.success("Saldo atualizado!")
            time.sleep(1)
            st.rerun()
        
        st.divider()
        if st.button("Logout"):
            st.session_state.auth = False
            st.session_state.running = False
            st.rerun()
        
        # Histórico rápido
        if st.session_state.historico:
            st.divider()
            st.subheader("📊 Resumo")
            df_temp = pd.DataFrame(st.session_state.historico)
            total_trades = len(df_temp)
            trades_positivos = len(df_temp[df_temp['pnl'] > 0])
            win_rate = (trades_positivos / total_trades * 100) if total_trades > 0 else 0
            st.metric("Win Rate", f"{win_rate:.1f}%")
            st.metric("Total Trades", total_trades)

    if not st.session_state.running:
        st.title("🚀 Sniper Pro v29")
        
        # Formulário de configuração
        with st.form("config_form"):
            ca = st.text_input("Contract Address (CA) do token")
            
            valor_min = 0.1 * st.session_state.taxa
            valor = st.number_input(
                f"Valor por ordem ({st.session_state.moeda})", 
                value=10.0 * st.session_state.taxa,
                min_value=valor_min
            )
            
            submitted = st.form_submit_button("INICIAR BOT")
            
            if submitted:
                if not ca.strip():
                    st.error("Digite um Contract Address válido")
                else:
                    with st.spinner("Buscando preço..."):
                        preco = fetch_price(ca.strip())
                        if preco:
                            st.session_state.ca = ca.strip()
                            st.session_state.t_nome = get_token_info(ca.strip())
                            st.session_state.invest_usd = valor / st.session_state.taxa
                            entrada = preco
                            
                            # Inicializa 10 trades
                            st.session_state.trades = []
                            for i in range(10):
                                st.session_state.trades.append({
                                    "id": i+1,
                                    "ent": entrada,
                                    "pnl": 0.0,
                                    "on": True,
                                    "max": 0.0,
                                    "res": "",
                                    "h": [entrada]
                                })
                            
                            st.session_state.running = True
                            st.success(f"Bot iniciado para {st.session_state.t_nome}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Não foi possível obter o preço. Verifique o CA.")
    else:
        # Bot rodando
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.subheader(f"🟢 Monitorando: {st.session_state.t_nome}")
        
        with col2:
            if st.button("⏸️ Pausar"):
                st.session_state.running = False
                st.warning("Bot pausado")
                time.sleep(1)
                st.rerun()
        
        with col3:
            if st.button("⏹️ Parar"):
                st.session_state.running = False
                st.session_state.trades = []
                st.success("Bot parado")
                time.sleep(1)
                st.rerun()
        
        # Buscar preço atual
        preco_atual = fetch_price(st.session_state.ca)
        if preco_atual is None:
            preco_atual = st.session_state.trades[0]["ent"] if st.session_state.trades else 0
            st.warning("Não foi possível atualizar o preço. Usando último valor conhecido.")
        
        # Display info
        hora = time.strftime("%H:%M:%S")
        st.markdown(f"### Preço atual: `{preco_atual:.10f}` (às {hora})")
        
        # Exibir saldo atualizado
        saldo_display = st.session_state.saldo * st.session_state.taxa
        if st.session_state.moeda == "BRL":
            st.markdown(f"**Saldo:** R$ {saldo_display:,.2f}")
        else:
            st.markdown(f"**Saldo:** $ {saldo_display:,.2f}")
        
        # Processar trades
        st.divider()
        st.subheader("📈 Trades Ativos")
        
        # Criar colunas para os trades
        cols = st.columns(5)
        
        for i, trade in enumerate(st.session_state.trades):
            col_idx = i % 5
            
            with cols[col_idx]:
                if trade["on"]:
                    # Atualizar PnL
                    trade["pnl"] = ((preco_atual / trade["ent"]) - 1) * 100
                    if trade["pnl"] > trade["max"]:
                        trade["max"] = trade["pnl"]
                    
                    # Adicionar ao histórico
                    trade["h"].append(preco_atual)
                    if len(trade["h"]) > 5:
                        trade["h"].pop(0)
                    
                    # Verificar se deve fechar
                    fechar, motivo = ia_brain(trade["pnl"], trade["max"], trade["h"])
                    
                    if fechar:
                        trade["on"] = False
                        trade["res"] = motivo
                        lucro = st.session_state.invest_usd * (trade["pnl"] / 100)
                        st.session_state.saldo += lucro
                        
                        # Registrar no histórico
                        st.session_state.historico.append({
                            "ciclo": st.session_state.ciclo,
                            "ordem": trade["id"],
                            "pnl": round(trade["pnl"], 2),
                            "lucro_usd": round(lucro, 2),
                            "motivo": motivo,
                            "timestamp": hora
                        })
                
                # Display do trade
                with st.container(border=True):
                    status = "🟢" if trade["on"] else "🔴"
                    pnl_color = "green" if trade["pnl"] >= 0 else "red"
                    
                    st.markdown(f"**{status} Trade {trade['id']}**")
                    st.markdown(f"<span style='color:{pnl_color}'>{trade['pnl']:+.2f}%</span>", 
                               unsafe_allow_html=True)
                    
                    if not trade["on"]:
                        st.caption(f"✓ {trade['res']}")
        
        # Incrementar ciclo
        st.session_state.ciclo += 1
        
        # Histórico de trades fechados
        if st.session_state.historico:
            st.divider()
            st.subheader("📜 Histórico de Trades Fechados")
            
            df = pd.DataFrame(st.session_state.historico)
            
            # Mostrar métricas
            col1, col2, col3 = st.columns(3)
            with col1:
                total_trades = len(df)
                st.metric("Total Trades", total_trades)
            
            with col2:
                trades_positivos = len(df[df['pnl'] > 0])
                win_rate = (trades_positivos / total_trades * 100) if total_trades > 0 else 0
                st.metric("Win Rate", f"{win_rate:.1f}%")
            
            with col3:
                lucro_total = df['lucro_usd'].sum()
                st.metric("Lucro Total", f"$ {lucro_total:+.2f}")
            
            # Tabela
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ciclo": "Ciclo",
                    "ordem": "Ordem",
                    "pnl": st.column_config.NumberColumn("PnL %", format="+.2f"),
                    "lucro_usd": st.column_config.NumberColumn("Lucro $", format="+.2f"),
                    "motivo": "Motivo",
                    "timestamp": "Hora"
                }
            )
        
        # Gráfico simples sem Plotly
        if st.session_state.trades and any(trade["on"] for trade in st.session_state.trades):
            st.divider()
            st.subheader("📊 Evolução de Preços")
            
            # Coletar dados para o gráfico
            dados_grafico = []
            for trade in st.session_state.trades[:3]:  # Mostrar apenas 3 trades
                if trade["h"]:
                    for i, preco in enumerate(trade["h"]):
                        dados_grafico.append({
                            "Trade": f"Trade {trade['id']}",
                            "Período": i,
                            "Preço": preco
                        })
            
            if dados_grafico:
                df_grafico = pd.DataFrame(dados_grafico)
                st.line_chart(
                    df_grafico,
                    x="Período",
                    y="Preço",
                    color="Trade",
                    height=300
                )
        
        # Atualização automática (modo seguro)
        time.sleep(3)  # Espera 3 segundos
        st.rerun()