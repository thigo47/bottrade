import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go

# ========== CONFIGURAÇÃO ==========
st.set_page_config(
    page_title="Sniper AI Trader Pro",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 SNIPER AI TRADER PRO")
st.markdown("### Sistema de Análise Inteligente - **100% GRATUITO**")

# ========== INICIALIZAÇÃO ==========
if 'saldo' not in st.session_state:
    st.session_state.saldo = 1000.0
    
if 'trades' not in st.session_state:
    st.session_state.trades = []
    
if 'historico' not in st.session_state:
    st.session_state.historico = []

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("💰 STATUS")
    
    st.metric("SALDO ATUAL", f"${st.session_state.saldo:,.2f}")
    st.metric("TRADES ATIVOS", len(st.session_state.trades))
    st.metric("LUCRO TOTAL", f"${sum(t.get('lucro', 0) for t in st.session_state.historico):+,.2f}")
    
    st.divider()
    
    st.header("⚙️ CONFIGURAÇÕES")
    
    st.slider("Confiança mínima", 60, 95, 75, key="min_conf")
    st.slider("Stop Loss (%)", 5, 20, 10, key="stop_loss")
    st.slider("Take Profit (%)", 15, 50, 25, key="take_profit")
    st.slider("Posição máxima (%)", 5, 30, 15, key="max_pos")
    
    st.divider()
    
    if st.button("🔄 ATUALIZAR TUDO", use_container_width=True):
        st.rerun()
    
    if st.button("🧹 LIMPAR TUDO", use_container_width=True):
        st.session_state.trades = []
        st.session_state.saldo = 1000.0
        st.session_state.historico = []
        st.success("Reiniciado!")
        st.rerun()

# ========== SISTEMA DE ANÁLISE INTELIGENTE ==========
class AnalisadorIA:
    """Sistema de análise inteligente sem API externa"""
    
    def analisar_token(self, token_data):
        """Analisa token usando lógica inteligente"""
        try:
            pair = token_data['pairs'][0]
            
            # Extrair dados
            symbol = pair.get('baseToken', {}).get('symbol', 'TOKEN')
            price = float(pair.get('priceUsd', 0))
            volume_24h = float(pair.get('volume', {}).get('h24', 0))
            liquidity = float(pair.get('liquidity', {}).get('usd', 0))
            price_change = float(pair.get('priceChange', {}).get('h24', 0))
            
            # Análise de transações
            txns = pair.get('txns', {}).get('h24', {})
            buys = txns.get('buys', 0)
            sells = txns.get('sells', 0)
            buy_ratio = buys / max(buys + sells, 1)
            
            # Calcula score (0-100)
            score = 0
            
            # 1. Análise de Volume (0-30 pontos)
            if volume_24h > 100000:
                score += 30
                vol_status = "📈 VOLUME ALTO"
            elif volume_24h > 50000:
                score += 20
                vol_status = "📊 VOLUME BOM"
            elif volume_24h > 20000:
                score += 10
                vol_status = "📉 VOLUME RAZOÁVEL"
            else:
                vol_status = "⚠️ VOLUME BAIXO"
            
            # 2. Análise de Liquidez (0-25 pontos)
            if liquidity > 50000:
                score += 25
                liq_status = "💧 LIQUIDEZ EXCELENTE"
            elif liquidity > 20000:
                score += 15
                liq_status = "💦 LIQUIDEZ BOA"
            elif liquidity > 5000:
                score += 5
                liq_status = "💧 LIQUIDEZ ACEITÁVEL"
            else:
                liq_status = "⚠️ LIQUIDEZ BAIXA"
            
            # 3. Análise de Tendência (0-20 pontos)
            if 5 < price_change < 30:
                score += 20
                trend_status = "🚀 CRESCIMENTO SAUDÁVEL"
            elif price_change > 30:
                score += 10
                trend_status = "⚡ ALTA FORTE (cuidado com pump)"
            elif price_change > 0:
                score += 5
                trend_status = "📈 EM ALTA"
            else:
                trend_status = "📉 EM QUEDA"
            
            # 4. Análise de Compras/Vendas (0-15 pontos)
            if buy_ratio > 0.7:
                score += 15
                txn_status = "🟢 MAIS COMPRAS (bullish)"
            elif buy_ratio > 0.5:
                score += 8
                txn_status = "🟡 EQUILÍBRIO"
            else:
                txn_status = "🔴 MAIS VENDAS (bearish)"
            
            # 5. Análise de Price Impact (0-10 pontos)
            price_impact = pair.get('priceChange', {}).get('m5', 0)
            if isinstance(price_impact, (int, float)) and abs(price_impact) < 5:
                score += 10
                impact_status = "⚖️ ESTÁVEL"
            else:
                impact_status = "🎢 VOLÁTIL"
            
            # Determinar decisão baseada no score
            if score >= 70:
                decisao = "COMPRAR"
                cor = "🟢"
                confianca = min(95, 70 + (score - 70))
                razao = f"Score alto ({score}/100) - {vol_status}, {liq_status}"
                risco = "BAIXO"
                stop_loss = -8
                take_profit = 30
                
            elif score >= 50:
                decisao = "ESPERAR"
                cor = "🟡"
                confianca = 50 + (score - 50)
                razao = f"Score moderado ({score}/100) - {trend_status}"
                risco = "MÉDIO"
                stop_loss = -10
                take_profit = 25
                
            else:
                decisao = "EVITAR"
                cor = "🔴"
                confianca = max(30, score)
                razao = f"Score baixo ({score}/100) - {txn_status}, {impact_status}"
                risco = "ALTO"
                stop_loss = -12
                take_profit = 20
            
            return {
                'decisao': decisao,
                'cor': cor,
                'confianca': confianca,
                'score': score,
                'razao': razao,
                'risco': risco,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'detalhes': {
                    'volume_status': vol_status,
                    'liquidez_status': liq_status,
                    'tendencia_status': trend_status,
                    'transacoes_status': txn_status,
                    'impacto_status': impact_status
                }
            }
            
        except Exception as e:
            return {
                'decisao': 'ERRO',
                'cor': '⚫',
                'confianca': 0,
                'score': 0,
                'razao': f'Erro na análise: {str(e)[:50]}',
                'risco': 'ALTO',
                'stop_loss': -10,
                'take_profit': 20
            }

# ========== FUNÇÕES ==========
def buscar_token(ca):
    """Busca dados do token"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('pairs'):
                # Adicionar CA aos dados
                data['ca'] = ca
                return data
    except:
        pass
    return None

def criar_trade(token_data, analise, posicao_percent):
    """Cria um novo trade"""
    try:
        pair = token_data['pairs'][0]
        price = float(pair.get('priceUsd', 0))
        
        # Calcular valores
        valor_posicao = st.session_state.saldo * (posicao_percent / 100)
        stop_loss = price * (1 + analise['stop_loss']/100)
        take_profit = price * (1 + analise['take_profit']/100)
        
        trade = {
            'id': len(st.session_state.trades) + 1,
            'symbol': pair.get('baseToken', {}).get('symbol', 'TOKEN'),
            'ca': token_data.get('ca', ''),
            'entry_price': price,
            'current_price': price,
            'position_size': valor_posicao,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'status': 'ACTIVE',
            'entry_time': datetime.now(),
            'analise': analise,
            'lucro_percent': 0.0,
            'lucro_valor': 0.0
        }
        
        st.session_state.trades.append(trade)
        st.session_state.saldo -= valor_posicao
        
        return trade
        
    except:
        return None

# ========== INTERFACE PRINCIPAL ==========
st.header("🔍 ANALISAR TOKEN")

# Input para token
col1, col2 = st.columns([3, 1])
with col1:
    ca = st.text_input(
        "Cole o CA do token:",
        placeholder="0x...",
        key="token_input"
    )
with col2:
    btn_analisar = st.button("🔎 ANALISAR", type="primary", use_container_width=True)

if ca and btn_analisar:
    with st.spinner("Analisando token..."):
        token_data = buscar_token(ca)
        
        if token_data:
            pair = token_data['pairs'][0]
            
            # Mostrar dados básicos
            st.subheader("📊 DADOS DO TOKEN")
            
            col_a, col_b, col_c, col_d = st.columns(4)
            
            with col_a:
                price = float(pair.get('priceUsd', 0))
                st.metric("💰 Preço", f"${price:.10f}")
            
            with col_b:
                volume = float(pair.get('volume', {}).get('h24', 0))
                st.metric("📊 Volume 24h", f"${volume:,.0f}")
            
            with col_c:
                liquidity = float(pair.get('liquidity', {}).get('usd', 0))
                st.metric("💧 Liquidez", f"${liquidity:,.0f}")
            
            with col_d:
                change = float(pair.get('priceChange', {}).get('h24', 0))
                st.metric("📈 Variação 24h", f"{change:.1f}%")
            
            st.divider()
            
            # Análise inteligente
            st.subheader("🧠 ANÁLISE INTELIGENTE")
            
            analisador = AnalisadorIA()
            analise = analisador.analisar_token(token_data)
            
            # Mostrar resultado
            col_x, col_y = st.columns(2)
            
            with col_x:
                st.markdown(f"### {analise['cor']} {analise['decisao']}")
                st.markdown(f"**Confiança:** {analise['confianca']:.0f}%")
                st.markdown(f"**Score:** {analise['score']}/100")
                st.markdown(f"**Risco:** {analise['risco']}")
                st.markdown(f"**Razão:** {analise['razao']}")
            
            with col_y:
                # Calcular parâmetros
                sl_price = price * (1 + analise['stop_loss']/100)
                tp_price = price * (1 + analise['take_profit']/100)
                
                st.metric("⛔ Stop Loss", f"{analise['stop_loss']}%", f"${sl_price:.10f}")
                st.metric("🎯 Take Profit", f"+{analise['take_profit']}%", f"${tp_price:.10f}")
                
                # Risk/Reward
                rr = abs(analise['take_profit'] / analise['stop_loss'])
                st.metric("📈 Risk/Reward", f"1:{rr:.1f}")
            
            # Detalhes da análise
            with st.expander("📋 VER DETALHES DA ANÁLISE"):
                for chave, valor in analise['detalhes'].items():
                    st.write(f"**{chave.replace('_', ' ').title()}:** {valor}")
            
            # Ação recomendada
            st.divider()
            
            if analise['decisao'] == 'COMPRAR' and analise['confianca'] >= st.session_state.get('min_conf', 70):
                st.success("✅ **SINAL DE COMPRA FORTE DETECTADO!**")
                
                # Controles para entrada
                col_p1, col_p2, col_p3 = st.columns([2, 1, 1])
                
                with col_p1:
                    max_pos = st.session_state.get('max_pos', 15)
                    posicao = st.slider(
                        "Tamanho da posição (% do saldo):",
                        1.0, float(max_pos), 5.0, 0.5
                    )
                
                with col_p2:
                    valor_posicao = st.session_state.saldo * (posicao / 100)
                    st.metric("💰 Valor", f"${valor_posicao:.2f}")
                
                with col_p3:
                    if st.button("🚀 ENTRAR NO TRADE", type="primary", use_container_width=True):
                        trade = criar_trade(token_data, analise, posicao)
                        if trade:
                            st.balloons()
                            st.success(f"✅ Trade iniciado para {trade['symbol']}!")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao criar trade")
            
            elif analise['decisao'] == 'ESPERAR':
                st.warning("⚠️ **AGUARDAR MELHOR OPORTUNIDADE**")
                st.info("O token não atingiu os critérios mínimos para entrada.")
            
            else:
                st.error("❌ **EVITAR ESTE TOKEN**")
                st.warning("Recomendação: Procure outras oportunidades.")
        
        else:
            st.error("❌ Token não encontrado. Verifique o CA.")

# ========== TOKENS PARA TESTE ==========
st.divider()
st.header("🎯 TOKENS PARA TESTE")

col_t1, col_t2, col_t3, col_t4 = st.columns(4)

with col_t1:
    if st.button("💰 ETH", use_container_width=True):
        st.session_state.token_input = "0x2170Ed0880ac9A755fd29B2688956BD959F933F8"
        st.rerun()

with col_t2:
    if st.button("🔥 BNB", use_container_width=True):
        st.session_state.token_input = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
        st.rerun()

with col_t3:
    if st.button("💎 USDC", use_container_width=True):
        st.session_state.token_input = "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"
        st.rerun()

with col_t4:
    if st.button("🦄 UNI", use_container_width=True):
        st.session_state.token_input = "0xBf5140A22578168FD562DCcF235E5D43A02ce9B1"
        st.rerun()

# ========== TRADES ATIVOS ==========
if st.session_state.trades:
    st.divider()
    st.header("📈 TRADES ATIVOS")
    
    # Atualizar preços
    for trade in st.session_state.trades:
        if trade['status'] == 'ACTIVE':
            token_data = buscar_token(trade['ca'])
            if token_data:
                current_price = float(token_data['pairs'][0].get('priceUsd', 0))
                trade['current_price'] = current_price
                trade['lucro_percent'] = ((current_price - trade['entry_price']) / trade['entry_price']) * 100
                trade['lucro_valor'] = trade['position_size'] * (trade['lucro_percent'] / 100)
    
    # Mostrar trades
    cols = st.columns(3)
    
    for idx, trade in enumerate(st.session_state.trades[:6]):
        with cols[idx % 3]:
            with st.container(border=True, height=280):
                lucro = trade['lucro_percent']
                cor = "🟢" if lucro >= 0 else "🔴"
                
                st.markdown(f"**{trade['symbol']}** (ID: {trade['id']})")
                st.markdown(f"### {cor} {lucro:+.2f}%")
                
                # Informações
                st.caption(f"💰 Entrada: ${trade['entry_price']:.10f}")
                st.caption(f"📊 Atual: ${trade['current_price']:.10f}")
                st.caption(f"⛔ Stop: ${trade['stop_loss']:.10f}")
                st.caption(f"🎯 TP: ${trade['take_profit']:.10f}")
                
                # Botão de saída
                if st.button(f"⏹️ SAIR {trade['symbol']}", key=f"exit_{trade['id']}", use_container_width=True):
                    # Fechar trade
                    trade['status'] = 'CLOSED'
                    trade['exit_time'] = datetime.now()
                    trade['exit_price'] = trade['current_price']
                    
                    # Adicionar ao histórico
                    st.session_state.historico.append(trade.copy())
                    
                    # Retornar dinheiro ao saldo
                    st.session_state.saldo += trade['position_size'] + trade['lucro_valor']
                    
                    # Remover dos ativos
                    st.session_state.trades = [t for t in st.session_state.trades if t['id'] != trade['id']]
                    
                    st.success(f"Trade fechado: {lucro:+.2f}%")
                    st.rerun()

# ========== HISTÓRICO ==========
if st.session_state.historico:
    st.divider()
    st.header("📋 HISTÓRICO DE TRADES")
    
    for trade in st.session_state.historico[-5:]:  # Últimos 5
        lucro = trade['lucro_percent']
        cor = "🟢" if lucro >= 0 else "🔴"
        
        st.write(f"{cor} **{trade['symbol']}** - {lucro:+.2f}% (${trade['lucro_valor']:+.2f})")

# ========== CSS ==========
st.markdown("""
<style>
    /* Interface mobile-first */
    .stButton > button {
        width: 100%;
        height: 50px;
        font-size: 16px;
        font-weight: bold;
        border-radius: 10px;
        margin: 5px 0;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Botões coloridos */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        color: white;
    }
    
    /* Inputs grandes */
    .stTextInput input {
        height: 55px;
        font-size: 16px;
        border-radius: 10px;
    }
    
    /* Títulos */
    h1, h2, h3 {
        color: #1E3A8A;
        margin-top: 1rem;
    }
    
    /* Cards de trade */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 15px;
        border: 2px solid #e0e0e0;
        padding: 15px;
        margin: 10px 0;
        background: white;
    }
    
    /* Status colors */
    .success-card {
        border-left: 5px solid #28a745;
    }
    
    .warning-card {
        border-left: 5px solid #ffc107;
    }
    
    .danger-card {
        border-left: 5px solid #dc3545;
    }
    
    /* Ajuste para mobile */
    @media (max-width: 768px) {
        .stButton > button {
            height: 45px;
            font-size: 14px;
        }
        
        .stTextInput input {
            height: 45px;
            font-size: 14px;
        }
        
        h1 { font-size: 24px; }
        h2 { font-size: 20px; }
        h3 { font-size: 18px; }
    }
</style>
""", unsafe_allow_html=True)
