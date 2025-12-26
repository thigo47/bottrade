import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

# ==========================================================
# CONFIGURAÇÃO
# ==========================================================
st.set_page_config(
    page_title="Sniper Pro Bot",
    page_icon="🤖",
    layout="wide"
)

# ==========================================================
# INICIALIZAÇÃO DO ESTADO
# ==========================================================
# Inicializar todas variáveis de sessão
if 'bot_rodando' not in st.session_state:
    st.session_state.bot_rodando = False
if 'saldo' not in st.session_state:
    st.session_state.saldo = 1000.0
if 'trades' not in st.session_state:
    st.session_state.trades = []
if 'historico' not in st.session_state:
    st.session_state.historico = []
if 'ciclo' not in st.session_state:
    st.session_state.ciclo = 0
if 'token_info' not in st.session_state:
    st.session_state.token_info = {
        'symbol': 'Nenhum',
        'ca': '',
        'preco_entrada': 0.0
    }

# ==========================================================
# FUNÇÕES
# ==========================================================
def buscar_preco(ca):
    """Busca preço do token"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        resposta = requests.get(url, timeout=5)
        dados = resposta.json()
        preco = dados.get('pairs', [{}])[0].get('priceUsd')
        if preco:
            return float(preco)
    except:
        return None
    return None

def buscar_info_token(ca):
    """Busca símbolo do token"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        resposta = requests.get(url, timeout=5)
        dados = resposta.json()
        simbolo = dados.get('pairs', [{}])[0].get('baseToken', {}).get('symbol', 'TOKEN')
        return simbolo
    except:
        return "TOKEN"

def calcular_pnl(preco_atual, preco_entrada):
    """Calcula PnL em porcentagem"""
    if preco_entrada == 0:
        return 0.0
    return ((preco_atual / preco_entrada) - 1) * 100

# ==========================================================
# INTERFACE PRINCIPAL
# ==========================================================
st.title("🤖 SNIPER PRO - BOT DE TRADING")
st.markdown("---")

# SIDEBAR
with st.sidebar:
    st.header("⚙️ CONTROLES")
    
    # Saldo
    st.subheader("💰 SALDO")
    st.metric("Disponível", f"${st.session_state.saldo:,.2f}")
    
    # Ajustar saldo
    with st.expander("🔄 AJUSTAR SALDO"):
        novo_saldo = st.number_input(
            "Novo valor:",
            min_value=0.0,
            value=float(st.session_state.saldo),
            step=100.0
        )
        if st.button("Salvar", key="btn_salvar_saldo"):
            st.session_state.saldo = novo_saldo
            st.success(f"Saldo atualizado: ${novo_saldo:,.2f}")
            time.sleep(1)
            st.rerun()
    
    st.markdown("---")
    
    # Controles gerais
    if st.button("🔄 ATUALIZAR PÁGINA", use_container_width=True):
        st.rerun()
    
    if st.button("📊 VER HISTÓRICO", use_container_width=True):
        if st.session_state.historico:
            st.dataframe(pd.DataFrame(st.session_state.historico))
    
    if st.button("🧹 LIMPAR TUDO", use_container_width=True):
        st.session_state.bot_rodando = False
        st.session_state.trades = []
        st.session_state.historico = []
        st.session_state.ciclo = 0
        st.success("Sistema resetado!")
        time.sleep(1)
        st.rerun()

# ==========================================================
# ÁREA PRINCIPAL
# ==========================================================
if not st.session_state.bot_rodando:
    # BOT PARADO - CONFIGURAR
    st.header("🎯 CONFIGURAR NOVA OPERAÇÃO")
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Input do token
        ca_token = st.text_input(
            "📝 CONTRACT ADDRESS (CA):",
            placeholder="Cole aqui o CA do token...",
            help="Exemplo: So11111111111111111111111111111111111111112"
        )
        
        # Valor do trade
        valor_trade = st.number_input(
            "💰 VALOR POR TRADE (USD):",
            min_value=1.0,
            value=10.0,
            step=5.0
        )
        
        # Botões de ação
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🔍 VERIFICAR TOKEN", use_container_width=True, disabled=not ca_token):
                if ca_token.strip():
                    with st.spinner("Buscando informações..."):
                        preco = buscar_preco(ca_token.strip())
                        simbolo = buscar_info_token(ca_token.strip())
                        
                        if preco:
                            st.success(f"✅ TOKEN ENCONTRADO")
                            st.info(f"""
                            **Símbolo:** {simbolo}
                            **Preço atual:** ${preco:.10f}
                            **Valor/trade:** ${valor_trade:,.2f}
                            """)
                        else:
                            st.error("❌ Token não encontrado ou sem preço")
        
        with col_btn2:
            if st.button("🚀 INICIAR BOT", type="primary", use_container_width=True, disabled=not ca_token):
                if ca_token.strip():
                    with st.spinner("Iniciando bot..."):
                        preco = buscar_preco(ca_token.strip())
                        
                        if preco:
                            # Salvar informações do token
                            st.session_state.token_info = {
                                'symbol': buscar_info_token(ca_token.strip()),
                                'ca': ca_token.strip(),
                                'preco_entrada': preco
                            }
                            
                            # Criar 10 trades
                            st.session_state.trades = []
                            for i in range(10):
                                st.session_state.trades.append({
                                    'id': i + 1,
                                    'entrada': preco,
                                    'pnl': 0.0,
                                    'ativo': True,
                                    'motivo': ''
                                })
                            
                            st.session_state.valor_trade = valor_trade
                            st.session_state.bot_rodando = True
                            st.success("✅ Bot iniciado com sucesso!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Não foi possível obter preço do token")
    
    with col2:
        # Informações de ajuda
        st.info("""
        **📌 COMO USAR:**
        
        1. Cole o CA do token
        2. Defina o valor por trade
        3. Clique em "Verificar Token"
        4. Inicie o bot
        
        **🎯 REGRAS DO BOT:**
        - Stop Loss: -5%
        - Take Profit: +10%
        - 10 trades simultâneos
        
        **⚠️ AVISO:**
        Este é um simulador para fins educacionais.
        Não use com dinheiro real.
        """)

else:
    # BOT RODANDO
    col_titulo1, col_titulo2, col_titulo3 = st.columns([3, 1, 1])
    
    with col_titulo1:
        st.header(f"📈 MONITORANDO: {st.session_state.token_info['symbol']}")
    
    with col_titulo2:
        if st.button("⏸️ PAUSAR", use_container_width=True):
            st.session_state.bot_rodando = False
            st.warning("Bot pausado!")
            time.sleep(1)
            st.rerun()
    
    with col_titulo3:
        if st.button("⏹️ PARAR", type="secondary", use_container_width=True):
            st.session_state.bot_rodando = False
            st.session_state.trades = []
            st.success("Bot parado!")
            time.sleep(1)
            st.rerun()
    
    st.markdown("---")
    
    # BUSCAR PREÇO ATUAL
    preco_atual = buscar_preco(st.session_state.token_info['ca'])
    
    if preco_atual is None:
        preco_atual = st.session_state.token_info['preco_entrada']
        st.warning("⚠️ Não foi possível atualizar o preço. Usando último valor conhecido.")
    
    # INFORMAÇÕES EM TEMPO REAL
    col_info1, col_info2, col_info3, col_info4 = st.columns(4)
    
    with col_info1:
        st.metric("📊 PREÇO ATUAL", f"${preco_atual:.10f}")
    
    with col_info2:
        st.metric("💰 SALDO", f"${st.session_state.saldo:,.2f}")
    
    with col_info3:
        trades_ativos = sum(1 for trade in st.session_state.trades if trade['ativo'])
        st.metric("🔢 TRADES ATIVOS", trades_ativos)
    
    with col_info4:
        st.metric("🕒 ÚLTIMA ATUALIZAÇÃO", datetime.now().strftime("%H:%M:%S"))
    
    st.markdown("---")
    
    # TRADES ATIVOS
    st.subheader("📊 TRADES ATIVOS")
    
    # Criar 5 colunas para mostrar os trades
    colunas = st.columns(5)
    
    for i, trade in enumerate(st.session_state.trades):
        col_idx = i % 5
        
        with colunas[col_idx]:
            # Calcular PnL atual
            pnl_atual = calcular_pnl(preco_atual, trade['entrada'])
            trade['pnl'] = pnl_atual
            
            # Verificar regras de fechamento
            if trade['ativo']:
                # STOP LOSS (-5%)
                if pnl_atual <= -5.0:
                    trade['ativo'] = False
                    trade['motivo'] = f"🔴 STOP LOSS ({pnl_atual:.1f}%)"
                    
                    # Calcular resultado
                    resultado = st.session_state.valor_trade * (pnl_atual / 100)
                    st.session_state.saldo += resultado
                    
                    # Adicionar ao histórico
                    st.session_state.historico.append({
                        'id_trade': trade['id'],
                        'entrada': trade['entrada'],
                        'saida': preco_atual,
                        'pnl': round(pnl_atual, 2),
                        'resultado': round(resultado, 2),
                        'motivo': trade['motivo'],
                        'hora': datetime.now().strftime("%H:%M:%S")
                    })
                
                # TAKE PROFIT (+10%)
                elif pnl_atual >= 10.0:
                    trade['ativo'] = False
                    trade['motivo'] = f"🟢 TAKE PROFIT ({pnl_atual:.1f}%)"
                    
                    # Calcular resultado
                    resultado = st.session_state.valor_trade * (pnl_atual / 100)
                    st.session_state.saldo += resultado
                    
                    # Adicionar ao histórico
                    st.session_state.historico.append({
                        'id_trade': trade['id'],
                        'entrada': trade['entrada'],
                        'saida': preco_atual,
                        'pnl': round(pnl_atual, 2),
                        'resultado': round(resultado, 2),
                        'motivo': trade['motivo'],
                        'hora': datetime.now().strftime("%H:%M:%S")
                    })
            
            # Mostrar trade
            with st.container(border=True):
                # Status
                if trade['ativo']:
                    st.markdown(f"**🟢 TRADE {trade['id']}**")
                else:
                    st.markdown(f"**🔴 TRADE {trade['id']}**")
                
                # PnL colorido
                if trade['pnl'] >= 0:
                    st.markdown(f"<span style='color:green; font-weight:bold; font-size:20px;'>{trade['pnl']:+.2f}%</span>", 
                               unsafe_allow_html=True)
                else:
                    st.markdown(f"<span style='color:red; font-weight:bold; font-size:20px;'>{trade['pnl']:+.2f}%</span>", 
                               unsafe_allow_html=True)
                
                # Informações adicionais
                st.caption(f"Entrada: ${trade['entrada']:.8f}")
                
                if trade['motivo']:
                    st.caption(f"{trade['motivo']}")
    
    # Incrementar ciclo
    st.session_state.ciclo += 1
    
    st.markdown("---")
    
    # HISTÓRICO DE TRADES
    if st.session_state.historico:
        st.subheader("📜 HISTÓRICO DE TRADES")
        
        # Converter para DataFrame
        df_historico = pd.DataFrame(st.session_state.historico)
        
        # Métricas
        col_met1, col_met2, col_met3 = st.columns(3)
        
        with col_met1:
            total_trades = len(df_historico)
            st.metric("TOTAL DE TRADES", total_trades)
        
        with col_met2:
            trades_positivos = len(df_historico[df_historico['pnl'] > 0])
            win_rate = (trades_positivos / total_trades * 100) if total_trades > 0 else 0
            st.metric("WIN RATE", f"{win_rate:.1f}%")
        
        with col_met3:
            lucro_total = df_historico['resultado'].sum()
            st.metric("LUCRO TOTAL", f"${lucro_total:+.2f}")
        
        # Tabela
        st.dataframe(
            df_historico,
            use_container_width=True,
            hide_index=True,
            column_config={
                'id_trade': 'ID',
                'entrada': st.column_config.NumberColumn('ENTRADA', format='%.8f'),
                'saida': st.column_config.NumberColumn('SAÍDA', format='%.8f'),
                'pnl': st.column_config.NumberColumn('PNL %', format='+.2f'),
                'resultado': st.column_config.NumberColumn('RESULTADO $', format='+.2f'),
                'motivo': 'MOTIVO',
                'hora': 'HORA'
            }
        )
    
    # Atualização automática
    time.sleep(3)
    st.rerun()

# ==========================================================
# RODAPÉ
# ==========================================================
st.markdown("---")
rodape_col1, rodape_col2, rodape_col3 = st.columns(3)

with rodape_col1:
    st.caption(f"🔄 CICLO: {st.session_state.ciclo}")

with rodape_col2:
    st.caption("⚠️ SIMULADOR EDUCATIVO")

with rodape_col3:
    st.caption("🤖 SNIPER PRO v1.0")

# ==========================================================
# ESTILO CSS
# ==========================================================
st.markdown("""
<style>
    /* Estilo para botões */
    .stButton > button {
        border-radius: 10px;
        font-weight: bold;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: scale(1.02);
    }
    
    /* Estilo para métricas */
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        font-weight: bold;
    }
    
    /* Estilo para containers */
    .stContainer {
        border-radius: 10px;
        padding: 10px;
    }
    
    /* Estilo para inputs */
    .stTextInput > div > div > input {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)