# bot_simples.py
import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

# ==========================================================
# CONFIGURAÇÃO
# ==========================================================
st.set_page_config(
    page_title="Sniper Pro - Trade Bot",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# INICIALIZAÇÃO DO ESTADO
# ==========================================================
# Inicializar todas as variáveis de estado
if 'running' not in st.session_state:
    st.session_state.running = False
if 'saldo' not in st.session_state:
    st.session_state.saldo = 1000.0
if 'trades' not in st.session_state:
    st.session_state.trades = []
if 'historico' not in st.session_state:
    st.session_state.historico = []
if 'moeda' not in st.session_state:
    st.session_state.moeda = "USD"
if 'ciclo' not in st.session_state:
    st.session_state.ciclo = 0
if 'alertas' not in st.session_state:
    st.session_state.alertas = []
if 'token_info' not in st.session_state:
    st.session_state.token_info = {"symbol": "Nenhum", "ca": ""}

# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================
def fetch_price(ca):
    """Busca preço do token de forma simplificada"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            pairs = data.get('pairs', [])
            if pairs and pairs[0].get('priceUsd'):
                return float(pairs[0]['priceUsd'])
    except Exception as e:
        st.warning(f"Erro ao buscar preço: {e}")
    return None

def get_token_info(ca):
    """Busca informação do token"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        response = requests.get(url, timeout=5)
        data = response.json()
        symbol = data.get('pairs', [{}])[0].get('baseToken', {}).get('symbol', 'TOKEN')
        return symbol
    except:
        return "TOKEN"

def adicionar_alerta(mensagem, tipo="info"):
    """Adiciona alerta ao sistema"""
    alerta = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "mensagem": mensagem,
        "tipo": tipo
    }
    st.session_state.alertas.insert(0, alerta)
    if len(st.session_state.alertas) > 10:
        st.session_state.alertas.pop()

def formatar_moeda(valor, moeda):
    """Formata valor monetário"""
    if moeda == "BRL":
        return f"R$ {valor:,.2f}"
    return f"${valor:,.2f}"

# ==========================================================
# LÓGICA DE TRADING SIMPLIFICADA
# ==========================================================
def analisar_trade(preco_atual, preco_entrada, historico):
    """Lógica simples de trading"""
    # Calcular PnL
    pnl = ((preco_atual / preco_entrada) - 1) * 100
    
    # Regras básicas
    if pnl <= -5:  # Stop loss 5%
        return True, f"Stop Loss ({pnl:.1f}%)"
    elif pnl >= 10:  # Take profit 10%
        return True, f"Take Profit ({pnl:.1f}%)"
    
    return False, f"Monitorando ({pnl:.1f}%)"

# ==========================================================
# INTERFACE PRINCIPAL
# ==========================================================
st.title("🤖 Sniper Pro - Bot de Trading")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Controles")
    
    # Seleção de moeda
    st.session_state.moeda = st.radio(
        "Moeda de exibição:",
        ["USD", "BRL"],
        index=0
    )
    
    # Informações da conta
    st.subheader("💰 Banca")
    st.metric("Saldo Disponível", formatar_moeda(st.session_state.saldo, st.session_state.moeda))
    
    # Ajuste de saldo
    with st.expander("Ajustar Saldo"):
        novo_saldo = st.number_input(
            "Novo saldo:",
            min_value=0.0,
            value=float(st.session_state.saldo),
            step=100.0
        )
        if st.button("Atualizar"):
            st.session_state.saldo = novo_saldo
            adicionar_alerta(f"Saldo atualizado: {formatar_moeda(novo_saldo, st.session_state.moeda)}", "success")
            st.rerun()
    
    # Controles gerais
    st.markdown("---")
    st.subheader("🎮 Ações")
    
    if st.button("🔄 Atualizar Página", use_container_width=True):
        st.rerun()
    
    if st.session_state.historico:
        if st.button("📊 Exportar Dados", use_container_width=True):
            df = pd.DataFrame(st.session_state.historico)
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇️ Baixar CSV",
                data=csv,
                file_name="trades_historico.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    if st.button("🧹 Limpar Histórico", use_container_width=True):
        st.session_state.historico = []
        st.session_state.alertas = []
        adicionar_alerta("Histórico limpo", "info")
        st.rerun()

# ==========================================================
# ÁREA DE OPERAÇÃO
# ==========================================================
if not st.session_state.running:
    # Bot parado - mostrar configuração
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🎯 Configurar Nova Operação")
        
        # Input do token
        ca = st.text_input(
            "Contract Address do Token:",
            placeholder="Cole o CA do token aqui...",
            help="Exemplo: So11111111111111111111111111111111111111112"
        )
        
        # Valor por trade
        valor_trade = st.number_input(
            f"Valor por Trade ({st.session_state.moeda}):",
            min_value=1.0,
            value=10.0,
            step=5.0
        )
        
        # Botão para verificar token
        if ca and st.button("🔍 Verificar Token", use_container_width=True):
            with st.spinner("Buscando informações do token..."):
                preco = fetch_price(ca.strip())
                simbolo = get_token_info(ca.strip())
                
                if preco:
                    st.success(f"✅ **{simbolo}** | Preço atual: ${preco:.10f}")
                    st.session_state.token_info = {"symbol": simbolo, "ca": ca.strip(), "preco": preco}
                else:
                    st.error("❌ Não foi possível encontrar o token. Verifique o CA.")
        
        # Botão para iniciar
        if st.button("🚀 Iniciar Bot", type="primary", use_container_width=True, disabled=not ca):
            if not ca.strip():
                st.error("Por favor, insira um Contract Address válido")
            else:
                with st.spinner("Iniciando bot..."):
                    preco = fetch_price(ca.strip())
                    if preco:
                        # Configurar estado
                        st.session_state.token_info = {
                            "symbol": get_token_info(ca.strip()),
                            "ca": ca.strip(),
                            "preco_entrada": preco
                        }
                        
                        # Criar trades
                        st.session_state.trades = []
                        for i in range(10):
                            st.session_state.trades.append({
                                "id": i + 1,
                                "entrada": preco,
                                "pnl": 0.0,
                                "ativo": True,
                                "motivo": "",
                                "historico": [preco]
                            })
                        
                        st.session_state.valor_trade = valor_trade
                        st.session_state.running = True
                        adicionar_alerta(f"Bot iniciado para {st.session_state.token_info['symbol']}", "success")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Não foi possível obter o preço do token")
    
    with col2:
        # Informações úteis
        st.info("""
        **📌 Instruções Rápidas:**
        
        1. Cole o CA do token
        2. Defina o valor por trade
        3. Clique em "Verificar Token"
        4. Inicie o bot
        
        **🔍 Onde encontrar tokens?**
        - DexScreener
        - Birdeye
        - Jupiter
        
        **⚠️ Aviso:**
        Este é um simulador educativo.
        """)

else:
    # Bot rodando
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.subheader(f"📈 Monitorando: {st.session_state.token_info['symbol']}")
    
    with col2:
        if st.button("⏸️ Pausar", use_container_width=True):
            st.session_state.running = False
            adicionar_alerta("Bot pausado", "warning")
            st.rerun()
    
    with col3:
        if st.button("⏹️ Parar", type="secondary", use_container_width=True):
            st.session_state.running = False
            st.session_state.trades = []
            adicionar_alerta("Bot parado", "info")
            st.rerun()
    
    # Buscar preço atual
    preco_atual = fetch_price(st.session_state.token_info['ca'])
    if preco_atual is None:
        preco_atual = st.session_state.token_info.get('preco_entrada', 0)
        st.warning("Usando último preço conhecido")
    
    # Informações em tempo real
    st.markdown("---")
    
    col_info1, col_info2, col_info3 = st.columns(3)
    
    with col_info1:
        st.metric("Preço Atual", f"${preco_atual:.10f}")
    
    with col_info2:
        st.metric("Saldo", formatar_moeda(st.session_state.saldo, st.session_state.moeda))
    
    with col_info3:
        st.metric("Última Atualização", datetime.now().strftime("%H:%M:%S"))
    
    # Trades ativos
    st.markdown("---")
    st.subheader("📊 Trades Ativos")
    
    # Mostrar trades em colunas
    cols = st.columns(5)
    
    for i, trade in enumerate(st.session_state.trades):
        col_idx = i % 5
        
        with cols[col_idx]:
            if trade["ativo"]:
                # Atualizar trade
                fechar, motivo = analisar_trade(
                    preco_atual, 
                    trade["entrada"], 
                    trade["historico"]
                )
                
                # Calcular PnL
                pnl = ((preco_atual / trade["entrada"]) - 1) * 100
                trade["pnl"] = pnl
                trade["historico"].append(preco_atual)
                
                if len(trade["historico"]) > 5:
                    trade["historico"].pop(0)
                
                if fechar:
                    trade["ativo"] = False
                    trade["motivo"] = motivo
                    
                    # Calcular resultado
                    resultado = st.session_state.valor_trade * (pnl / 100)
                    st.session_state.saldo += resultado
                    
                    # Registrar no histórico
                    st.session_state.historico.append({
                        "trade_id": trade["id"],
                        "entrada": trade["entrada"],
                        "saida": preco_atual,
                        "pnl": round(pnl, 2),
                        "resultado": round(resultado, 2),
                        "motivo": motivo,
                        "hora": datetime.now().strftime("%H:%M:%S")
                    })
            
            # Mostrar trade
            with st.container(border=True):
                # Status
                status = "🟢" if trade["ativo"] else "🔴"
                st.markdown(f"**{status} Trade {trade['id']}**")
                
                # PnL
                cor = "green" if trade["pnl"] >= 0 else "red"
                st.markdown(f"<span style='color:{cor}'>**{trade['pnl']:+.2f}%**</span>", 
                           unsafe_allow_html=True)
                
                # Informações adicionais
                st.caption(f"Entrada: ${trade['entrada']:.8f}")
                
                if trade["motivo"]:
                    st.caption(f"📌 {trade['motivo']}")
    
    st.session_state.ciclo += 1
    
    # Histórico de trades
    if st.session_state.historico:
        st.markdown("---")
        st.subheader("📜 Histórico de Trades")
        
        df = pd.DataFrame(st.session_state.historico)
        
        # Métricas rápidas
        col_met1, col_met2, col_met3 = st.columns(3)
        
        with col_met1:
            total = len(df)
            st.metric("Total Trades", total)
        
        with col_met2:
            positivos = len(df[df['pnl'] > 0])
            win_rate = (positivos / total * 100) if total > 0 else 0
            st.metric("Win Rate", f"{win_rate:.1f}%")
        
        with col_met3:
            lucro_total = df['resultado'].sum()
            st.metric("Lucro Total", f"${lucro_total:+.2f}")
        
        # Tabela
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
    
    # Alertas recentes
    if st.session_state.alertas:
        with st.expander("🚨 Alertas Recentes"):
            for alerta in st.session_state.alertas[:5]:
                if alerta['tipo'] == 'success':
                    st.success(f"{alerta['time']} - {alerta['mensagem']}")
                elif alerta['tipo'] == 'warning':
                    st.warning(f"{alerta['time']} - {alerta['mensagem']}")
                else:
                    st.info(f"{alerta['time']} - {alerta['mensagem']}")
    
    # Atualização automática
    time.sleep(3)
    st.rerun()

# ==========================================================
# RODAPÉ
# ==========================================================
st.markdown("---")
footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption(f"🔄 Ciclo: {st.session_state.ciclo}")

with footer_col2:
    st.caption("⚠️ Simulador educativo - Use por sua conta")

with footer_col3:
    st.caption("🤖 Sniper Pro v1.0")

# ==========================================================
# ESTILOS CSS ADICIONAIS
# ==========================================================
st.markdown("""
<style>
    /* Melhorar a aparência dos containers */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
    }
    
    /* Estilo para métricas */
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
    }
    
    /* Alertas personalizados */
    .stAlert {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)