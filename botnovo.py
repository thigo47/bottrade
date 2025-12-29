import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# ==========================================================
# CONFIGURAÇÃO
# ==========================================================
st.set_page_config(
    page_title="🔥 SNIPER AI - BOT AGRESSIVO",
    page_icon="⚡",
    layout="wide"
)

# ==========================================================
# SISTEMA SIMPLIFICADO
# ==========================================================
if 'saldo' not in st.session_state:
    st.session_state.saldo = 1000.0

if 'trades' not in st.session_state:
    st.session_state.trades = []

if 'historico' not in st.session_state:
    st.session_state.historico = []

# ==========================================================
# FUNÇÕES SIMPLES
# ==========================================================
def buscar_token(ca):
    """Busca dados do token"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('pairs'):
                data['ca'] = ca
                return data
    except:
        pass
    return None

def analisar_token(token_data):
    """Análise simples e agressiva"""
    try:
        pair = token_data['pairs'][0]
        
        symbol = pair.get('baseToken', {}).get('symbol', 'TOKEN')
        price = float(pair.get('priceUsd', 0))
        volume = float(pair.get('volume', {}).get('h24', 0))
        
        # Análise básica
        if volume > 10000:  # Volume mínimo
            return {
                'decisao': 'COMPRAR',
                'symbol': symbol,
                'price': price,
                'stop_loss': price * 0.97,  # -3%
                'take_profit': price * 1.05,  # +5%
                'volume': volume
            }
        else:
            return {'decisao': 'EVITAR', 'symbol': symbol}
            
    except:
        return {'decisao': 'ERRO'}

def criar_trade(token_data, analise, percentual=10):
    """Cria um novo trade"""
    try:
        # Calcular valor do trade (10% do saldo por padrão)
        valor_trade = st.session_state.saldo * (percentual / 100)
        
        if valor_trade < 1:  # Mínimo $1
            return None
        
        trade = {
            'id': len(st.session_state.historico) + len(st.session_state.trades) + 1,
            'symbol': analise['symbol'],
            'ca': token_data.get('ca'),
            'entry_price': analise['price'],
            'current_price': analise['price'],
            'position_size': valor_trade,
            'stop_loss': analise['stop_loss'],
            'take_profit': analise['take_profit'],
            'status': 'ACTIVE',
            'entry_time': datetime.now(),
            'profit_percent': 0.0,
            'profit_value': 0.0
        }
        
        # Deduzir do saldo
        st.session_state.saldo -= valor_trade
        st.session_state.trades.append(trade)
        
        return trade
        
    except:
        return None

def atualizar_trades():
    """Atualiza preços e fecha trades"""
    fechados = []
    
    for trade in st.session_state.trades[:]:
        try:
            # Buscar preço atual
            data = buscar_token(trade['ca'])
            if data and data.get('pairs'):
                current_price = float(data['pairs'][0].get('priceUsd', 0))
                trade['current_price'] = current_price
                
                # Calcular lucro
                trade['profit_percent'] = ((current_price - trade['entry_price']) / trade['entry_price']) * 100
                trade['profit_value'] = trade['position_size'] * (trade['profit_percent'] / 100)
                
                # Verificar saída
                if current_price >= trade['take_profit'] or current_price <= trade['stop_loss']:
                    # Fechar trade
                    trade['status'] = 'CLOSED'
                    trade['exit_time'] = datetime.now()
                    
                    # Retornar dinheiro + lucro
                    st.session_state.saldo += trade['position_size'] + trade['profit_value']
                    
                    # Mover para histórico
                    st.session_state.historico.append(trade.copy())
                    st.session_state.trades.remove(trade)
                    fechados.append(trade)
                    
        except:
            continue
    
    return fechados

# ==========================================================
# INTERFACE SIMPLES
# ==========================================================
st.title("🔥 SNIPER AI - BOT AGRESSIVO")
st.markdown("### Sistema Automático de Trading")

# ==========================================================
# SIDEBAR
# ==========================================================
with st.sidebar:
    st.header("💰 CONTROLE")
    
    # Saldo
    st.metric("SALDO", f"${st.session_state.saldo:,.2f}")
    
    # Configurações
    st.divider()
    st.header("⚙️ CONFIG")
    
    percent_trade = st.slider("Tamanho por Trade (%)", 5, 30, 10, key="percent")
    
    st.divider()
    
    # Ações
    if st.button("🔄 ATUALIZAR", use_container_width=True):
        atualizar_trades()
        st.rerun()
    
    if st.button("🧹 LIMPAR", use_container_width=True):
        st.session_state.trades = []
        st.session_state.historico = []
        st.session_state.saldo = 1000.0
        st.success("Reiniciado!")
        st.rerun()

# ==========================================================
# SEÇÃO 1: ENTRADA
# ==========================================================
st.header("🎯 ENTRAR NO TRADE")

col1, col2 = st.columns([3, 1])
with col1:
    ca = st.text_input("CA do Token:", placeholder="0x...")
with col2:
    btn = st.button("⚡ ANALISAR E ENTRAR", type="primary", use_container_width=True)

if ca and btn:
    with st.spinner("Analisando..."):
        token_data = buscar_token(ca.strip())
        
        if token_data:
            # Analisar
            analise = analisar_token(token_data)
            
            if analise['decisao'] == 'COMPRAR':
                st.success(f"✅ {analise['symbol']} - Volume: ${analise['volume']:,.0f}")
                
                # Criar trade
                trade = criar_trade(token_data, analise, st.session_state.percent)
                
                if trade:
                    st.balloons()
                    st.success(f"✅ Trade criado! Entrada: ${trade['entry_price']:.8f}")
                    st.rerun()
                else:
                    st.error("❌ Erro ao criar trade")
            else:
                st.warning("❌ Volume muito baixo para trade")
        else:
            st.error("❌ Token não encontrado")

# ==========================================================
# SEÇÃO 2: TRADES ATIVOS
# ==========================================================
st.header("📈 TRADES ATIVOS")

# Atualizar automaticamente
fechados = atualizar_trades()

if fechados:
    st.subheader("🔒 FECHADOS AGORA")
    for trade in fechados:
        st.info(f"**{trade['symbol']}** - {trade['profit_percent']:+.2f}%")

# Mostrar trades ativos
if st.session_state.trades:
    st.subheader(f"🟢 {len(st.session_state.trades)} TRADES ABERTOS")
    
    for trade in st.session_state.trades:
        with st.container(border=True):
            col_t1, col_t2, col_t3 = st.columns([2, 2, 1])
            
            with col_t1:
                st.markdown(f"**{trade['symbol']}**")
                st.caption(f"Entrada: ${trade['entry_price']:.8f}")
                st.caption(f"Atual: ${trade['current_price']:.8f}")
            
            with col_t2:
                profit = trade['profit_percent']
                color = "🟢" if profit >= 0 else "🔴"
                st.markdown(f"{color} **{profit:+.2f}%**")
                st.caption(f"TP: ${trade['take_profit']:.8f}")
                st.caption(f"SL: ${trade['stop_loss']:.8f}")
            
            with col_t3:
                if st.button("⏹️ SAIR", key=f"exit_{trade['id']}", use_container_width=True):
                    # Forçar saída
                    trade['status'] = 'CLOSED'
                    trade['exit_time'] = datetime.now()
                    st.session_state.saldo += trade['position_size'] + trade['profit_value']
                    st.session_state.historico.append(trade.copy())
                    st.session_state.trades.remove(trade)
                    st.success("Trade fechado!")
                    st.rerun()
else:
    st.info("📭 Nenhum trade ativo")

# ==========================================================
# SEÇÃO 3: HISTÓRICO
# ==========================================================
if st.session_state.historico:
    st.header("📊 HISTÓRICO")
    
    for trade in st.session_state.historico[-10:]:
        profit = trade['profit_percent']
        emoji = "🟢" if profit >= 0 else "🔴"
        
        st.write(f"{emoji} **{trade['symbol']}** - {profit:+.2f}% (${trade['profit_value']:+.2f})")

# ==========================================================
# CSS SIMPLES
# ==========================================================
st.markdown("""
<style>
    .stButton > button {
        border-radius: 8px;
        font-weight: bold;
    }
    
    .stButton > button:hover {
        transform: scale(1.02);
    }
    
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# AUTO-REFRESH
# ==========================================================
if st.session_state.trades:
    time.sleep(10)
    st.rerun()