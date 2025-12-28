import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import json
from datetime import datetime, timedelta
import plotly.graph_objects as go
import google.generativeai as genai
import os
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# ==========================================================
# CONFIGURAÇÃO
# ==========================================================
st.set_page_config(
    page_title="Sniper Pro AI - Auto Trader",
    page_icon="🤖",
    layout="wide"
)

# ==========================================================
# CONFIGURAÇÃO DA IA GEMINI
# ==========================================================
class GeminiAI:
    """Classe para integração com Gemini AI"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.model = None
        
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-pro')
            except Exception as e:
                st.error(f"Erro ao configurar Gemini: {e}")
    
    def analyze_token(self, token_data: Dict) -> Dict:
        """Analisa um token usando Gemini AI"""
        
        if not self.model:
            return self._get_fallback_analysis()
        
        try:
            # Preparar os dados para análise
            symbol = token_data.get('symbol', 'TOKEN')
            price = float(token_data.get('pairs', [{}])[0].get('priceUsd', 0))
            volume = float(token_data.get('pairs', [{}])[0].get('volume', {}).get('h24', 0))
            liquidity = float(token_data.get('pairs', [{}])[0].get('liquidity', {}).get('usd', 0))
            price_change = float(token_data.get('pairs', [{}])[0].get('priceChange', {}).get('h24', 0))
            
            # Criar prompt detalhado
            prompt = f"""
            Você é um especialista em trading de criptomoedas. Analise este token:

            TOKEN: {symbol}
            PREÇO: ${price}
            VOLUME 24H: ${volume:,.2f}
            LIQUIDEZ: ${liquidity:,.2f}
            VARIAÇÃO 24H: {price_change}%

            Retorne APENAS um objeto JSON com estas informações:
            {{
                "decision": "BUY", "HOLD" ou "AVOID",
                "confidence": 0.0 a 1.0,
                "reason": "explicação breve",
                "stop_loss_percent": -5 a -15,
                "take_profit_percent": 10 a 30,
                "risk_level": "LOW", "MEDIUM" ou "HIGH",
                "time_frame": "SHORT_TERM", "MEDIUM_TERM" ou "LONG_TERM"
            }}

            Considere:
            1. Volume > $50,000 é positivo
            2. Liquidez > $20,000 é necessário
            3. Variação moderada (5-30%) é saudável
            4. Volume crescente é bom sinal

            IMPORTANTE: Retorne APENAS o JSON, nada mais.
            """
            
            # Gerar resposta
            response = self.model.generate_content(prompt)
            
            # Extrair JSON da resposta
            response_text = response.text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                analysis = json.loads(json_str)
                return analysis
            
        except Exception as e:
            st.warning(f"Erro na análise IA: {e}")
        
        return self._get_fallback_analysis()
    
    def _get_fallback_analysis(self) -> Dict:
        """Retorna análise padrão se IA falhar"""
        return {
            'decision': 'HOLD',
            'confidence': 0.5,
            'reason': 'Análise técnica padrão',
            'stop_loss_percent': -10,
            'take_profit_percent': 20,
            'risk_level': 'MEDIUM',
            'time_frame': 'SHORT_TERM'
        }

# ==========================================================
# SISTEMA DE MONITORAMENTO AUTOMÁTICO
# ==========================================================
class AutoTradeMonitor:
    """Monitora e executa trades automaticamente"""
    
    def __init__(self):
        self.active_trades = []
        self.trade_history = []
        self.performance = {
            'total_trades': 0,
            'winning_trades': 0,
            'total_profit': 0.0,
            'max_profit': 0.0,
            'max_loss': 0.0
        }
    
    def create_trade(self, token_data: Dict, position_size: float, 
                     entry_price: float, stop_loss: float, 
                     take_profit: float, ia_analysis: Dict = None) -> Dict:
        """Cria um novo trade"""
        
        trade = {
            'id': len(self.active_trades) + 1,
            'symbol': token_data.get('symbol', 'TOKEN'),
            'ca': token_data.get('ca', ''),
            'entry_price': entry_price,
            'current_price': entry_price,
            'position_size': position_size,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'status': 'ACTIVE',
            'entry_time': datetime.now(),
            'max_profit_percent': 0.0,
            'current_profit_percent': 0.0,
            'exit_price': None,
            'exit_time': None,
            'exit_reason': None,
            'ia_analysis': ia_analysis,
            'trailing_stop_activated': False,
            'trailing_stop_price': stop_loss
        }
        
        self.active_trades.append(trade)
        return trade
    
    def update_trade_prices(self, ca: str, current_price: float):
        """Atualiza preços dos trades"""
        for trade in self.active_trades:
            if trade['ca'] == ca and trade['status'] == 'ACTIVE':
                trade['current_price'] = current_price
                trade['current_profit_percent'] = ((current_price - trade['entry_price']) / trade['entry_price']) * 100
                
                if trade['current_profit_percent'] > trade['max_profit_percent']:
                    trade['max_profit_percent'] = trade['current_profit_percent']
    
    def execute_auto_exit(self):
        """Executa saídas automáticas"""
        closed_trades = []
        
        for trade in self.active_trades[:]:
            if trade['status'] == 'ACTIVE':
                current_price = trade['current_price']
                
                # Take Profit
                if current_price >= trade['take_profit']:
                    trade['status'] = 'CLOSED'
                    trade['exit_price'] = current_price
                    trade['exit_time'] = datetime.now()
                    trade['exit_reason'] = 'TAKE_PROFIT'
                    closed_trades.append(trade)
                
                # Stop Loss
                elif current_price <= trade['stop_loss']:
                    trade['status'] = 'CLOSED'
                    trade['exit_price'] = current_price
                    trade['exit_time'] = datetime.now()
                    trade['exit_reason'] = 'STOP_LOSS'
                    closed_trades.append(trade)
        
        # Mover trades fechados para histórico
        for trade in closed_trades:
            profit_percent = ((trade['exit_price'] - trade['entry_price']) / trade['entry_price']) * 100
            profit_value = trade['position_size'] * (profit_percent / 100)
            
            trade['final_profit_percent'] = profit_percent
            trade['final_profit_value'] = profit_value
            
            # Atualizar estatísticas
            self.performance['total_trades'] += 1
            if profit_percent > 0:
                self.performance['winning_trades'] += 1
            self.performance['total_profit'] += profit_value
            
            # Mover para histórico
            self.trade_history.append(trade.copy())
            self.active_trades.remove(trade)
        
        return closed_trades
    
    def get_performance_stats(self) -> Dict:
        """Retorna estatísticas de performance"""
        stats = {
            'win_rate': 0.0,
            'total_profit': self.performance['total_profit'],
            'total_trades': self.performance['total_trades'],
            'active_trades': len(self.active_trades)
        }
        
        if stats['total_trades'] > 0:
            stats['win_rate'] = (self.performance['winning_trades'] / stats['total_trades']) * 100
        
        return stats

# ==========================================================
# INICIALIZAÇÃO DO STREAMLIT
# ==========================================================
if 'trade_monitor' not in st.session_state:
    st.session_state.trade_monitor = AutoTradeMonitor()

if 'gemini_ai' not in st.session_state:
    st.session_state.gemini_ai = None

if 'balance' not in st.session_state:
    st.session_state.balance = 1000.0

if 'token_watchlist' not in st.session_state:
    st.session_state.token_watchlist = []

if 'auto_trading' not in st.session_state:
    st.session_state.auto_trading = False

# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================
def fetch_token_data(ca: str) -> Optional[Dict]:
    """Busca dados do token"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('pairs'):
                data['ca'] = ca
                data['symbol'] = data['pairs'][0].get('baseToken', {}).get('symbol', 'TOKEN')
                return data
    except:
        pass
    return None

def get_current_price(ca: str) -> Optional[float]:
    """Busca preço atual"""
    data = fetch_token_data(ca)
    if data and data.get('pairs'):
        return float(data['pairs'][0].get('priceUsd', 0))
    return None

# ==========================================================
# INTERFACE PRINCIPAL
# ==========================================================
st.title("🤖 SNIPER PRO AI - COM GEMINI IA")
st.markdown("### Sistema de Trading Inteligente com IA")

# ==========================================================
# SIDEBAR - CONFIGURAÇÃO DA IA
# ==========================================================
with st.sidebar:
    st.header("⚙️ CONFIGURAÇÃO")
    
    # Configuração da IA Gemini
    st.subheader("🧠 CONFIGURAR GEMINI AI")
    
    api_key = st.text_input(
        "Chave API Gemini:",
        type="password",
        placeholder="Cole sua chave aqui...",
        help="Obtenha em: https://aistudio.google.com/app/apikey"
    )
    
    if st.button("🔗 CONECTAR IA", use_container_width=True) and api_key:
        try:
            st.session_state.gemini_ai = GeminiAI(api_key)
            st.success("✅ Gemini AI conectado com sucesso!")
            st.balloons()
        except Exception as e:
            st.error(f"❌ Erro: {e}")
    
    if st.session_state.gemini_ai:
        st.info("✅ IA Conectada e Pronta!")
    
    st.divider()
    
    # Saldo e estatísticas
    stats = st.session_state.trade_monitor.get_performance_stats()
    
    st.metric("💰 SALDO", f"${st.session_state.balance:,.2f}")
    st.metric("🎯 WIN RATE", f"{stats['win_rate']:.1f}%")
    st.metric("📊 LUCRO TOTAL", f"${stats['total_profit']:+,.2f}")
    
    st.divider()
    
    # Controles
    st.subheader("🎮 CONTROLES")
    
    st.session_state.auto_trading = st.toggle(
        "🤖 AUTO TRADING", 
        value=st.session_state.auto_trading
    )
    
    if st.button("🔄 ATUALIZAR TUDO", use_container_width=True):
        st.rerun()
    
    if st.button("📊 EXPORTAR DADOS", use_container_width=True):
        if st.session_state.trade_monitor.trade_history:
            df = pd.DataFrame(st.session_state.trade_monitor.trade_history)
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇️ BAIXAR CSV",
                data=csv,
                file_name="trades.csv",
                mime="text/csv"
            )

# ==========================================================
# SEÇÃO 1: ADICIONAR E ANALISAR TOKENS
# ==========================================================
st.header("🔍 ANALISAR TOKENS COM IA")

col1, col2 = st.columns([3, 1])

with col1:
    token_ca = st.text_input(
        "CA do Token:",
        placeholder="Cole o CA do token...",
        key="token_input"
    )

with col2:
    analyze_btn = st.button(
        "🤖 ANALISAR COM IA", 
        use_container_width=True,
        disabled=not st.session_state.gemini_ai
    )

if token_ca and analyze_btn:
    with st.spinner("Buscando dados do token..."):
        token_data = fetch_token_data(token_ca.strip())
        
        if token_data:
            st.success(f"✅ Token encontrado: {token_data.get('symbol', 'TOKEN')}")
            
            # Mostrar dados básicos
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                price = float(token_data['pairs'][0].get('priceUsd', 0))
                st.metric("💰 PREÇO", f"${price:.10f}")
            
            with col_b:
                volume = float(token_data['pairs'][0].get('volume', {}).get('h24', 0))
                st.metric("📊 VOLUME 24H", f"${volume:,.0f}")
            
            with col_c:
                change = float(token_data['pairs'][0].get('priceChange', {}).get('h24', 0))
                st.metric("📈 VARIAÇÃO 24H", f"{change:.1f}%")
            
            st.divider()
            
            # Análise com IA
            with st.spinner("🧠 Analisando com Gemini AI..."):
                ia_analysis = st.session_state.gemini_ai.analyze_token(token_data)
                
                # Mostrar análise
                st.subheader("📋 ANÁLISE DA IA")
                
                col_x, col_y = st.columns(2)
                
                with col_x:
                    decision = ia_analysis['decision']
                    confidence = ia_analysis['confidence'] * 100
                    
                    if decision == 'BUY':
                        st.success(f"✅ **{decision}** ({confidence:.1f}% confiança)")
                    elif decision == 'HOLD':
                        st.info(f"⏸️ **{decision}** ({confidence:.1f}% confiança)")
                    else:
                        st.error(f"❌ **{decision}** ({confidence:.1f}% confiança)")
                    
                    st.write(f"**Razão:** {ia_analysis['reason']}")
                    st.write(f"**Risco:** {ia_analysis['risk_level']}")
                    st.write(f"**Time Frame:** {ia_analysis['time_frame']}")
                
                with col_y:
                    st.write("**⚙️ PARÂMETROS SUGERIDOS:**")
                    
                    stop_loss = price * (1 + ia_analysis['stop_loss_percent']/100)
                    take_profit = price * (1 + ia_analysis['take_profit_percent']/100)
                    
                    st.write(f"• Stop Loss: {ia_analysis['stop_loss_percent']}% (${stop_loss:.10f})")
                    st.write(f"• Take Profit: {ia_analysis['take_profit_percent']}% (${take_profit:.10f})")
                    st.write(f"• Risk/Reward: 1:{abs(ia_analysis['take_profit_percent']/ia_analysis['stop_loss_percent']):.1f}")
                
                # Botão para entrar no trade
                if decision == 'BUY' and confidence >= 70:
                    st.divider()
                    
                    col_p1, col_p2, col_p3 = st.columns([2, 1, 1])
                    
                    with col_p1:
                        position_percent = st.slider(
                            "Tamanho da posição (% do saldo):",
                            1.0, 30.0, 10.0, 0.5
                        )
                    
                    position_value = st.session_state.balance * (position_percent / 100)
                    
                    with col_p2:
                        st.metric("💰 VALOR", f"${position_value:.2f}")
                    
                    with col_p3:
                        if st.button("🚀 ENTRAR NO TRADE", type="primary", use_container_width=True):
                            trade = st.session_state.trade_monitor.create_trade(
                                token_data=token_data,
                                position_size=position_value,
                                entry_price=price,
                                stop_loss=stop_loss,
                                take_profit=take_profit,
                                ia_analysis=ia_analysis
                            )
                            
                            st.session_state.balance -= position_value
                            st.success(f"✅ Trade iniciado para {token_data['symbol']}!")
                            st.rerun()
        else:
            st.error("❌ Token não encontrado. Verifique o CA.")

# ==========================================================
# SEÇÃO 2: TRADES ATIVOS
# ==========================================================
st.header("📈 TRADES ATIVOS")

# Atualizar preços
if st.session_state.trade_monitor.active_trades:
    for trade in st.session_state.trade_monitor.active_trades:
        current_price = get_current_price(trade['ca'])
        if current_price:
            st.session_state.trade_monitor.update_trade_prices(trade['ca'], current_price)
    
    # Verificar saídas automáticas
    closed_trades = st.session_state.trade_monitor.execute_auto_exit()
    
    # Mostrar trades fechados
    if closed_trades:
        for trade in closed_trades:
            profit = trade['final_profit_percent']
            st.info(f"✅ **{trade['symbol']}** fechado: {profit:+.2f}% ({trade['exit_reason']})")
            
            # Atualizar saldo
            st.session_state.balance += trade['position_size'] + trade['final_profit_value']
    
    # Mostrar trades ativos
    st.subheader("🟢 TRADES EM ANDAMENTO")
    
    cols = st.columns(3)
    
    for idx, trade in enumerate(st.session_state.trade_monitor.active_trades[:6]):
        with cols[idx % 3]:
            with st.container(border=True, height=220):
                profit = trade['current_profit_percent']
                color = "🟢" if profit >= 0 else "🔴"
                
                st.write(f"**{trade['symbol']}** (ID: {trade['id']})")
                st.write(f"{color} **{profit:+.2f}%**")
                
                st.caption(f"Entrada: ${trade['entry_price']:.10f}")
                st.caption(f"Atual: ${trade['current_price']:.10f}")
                st.caption(f"Stop: ${trade['stop_loss']:.10f}")
                st.caption(f"TP: ${trade['take_profit']:.10f}")
                
                # Botão de saída manual
                if st.button("⏹️ SAIR", key=f"exit_{trade['id']}", use_container_width=True):
                    current_price = get_current_price(trade['ca'])
                    if current_price:
                        profit_percent = ((current_price - trade['entry_price']) / trade['entry_price']) * 100
                        
                        trade['status'] = 'CLOSED'
                        trade['exit_price'] = current_price
                        trade['exit_time'] = datetime.now()
                        trade['exit_reason'] = 'MANUAL'
                        trade['final_profit_percent'] = profit_percent
                        trade['final_profit_value'] = trade['position_size'] * (profit_percent / 100)
                        
                        st.session_state.trade_monitor.trade_history.append(trade.copy())
                        st.session_state.trade_monitor.active_trades.remove(trade)
                        
                        st.session_state.balance += trade['position_size'] + trade['final_profit_value']
                        st.success(f"Trade fechado: {profit_percent:+.2f}%")
                        st.rerun()
else:
    st.info("📭 Nenhum trade ativo no momento.")

# ==========================================================
# SEÇÃO 3: HISTÓRICO E ESTATÍSTICAS
# ==========================================================
st.header("📊 ESTATÍSTICAS")

col_s1, col_s2, col_s3, col_s4 = st.columns(4)

with col_s1:
    stats = st.session_state.trade_monitor.get_performance_stats()
    st.metric("🎯 WIN RATE", f"{stats['win_rate']:.1f}%")

with col_s2:
    st.metric("💰 LUCRO TOTAL", f"${stats['total_profit']:+,.2f}")

with col_s3:
    st.metric("📊 TOTAL TRADES", stats['total_trades'])

with col_s4:
    st.metric("🟢 ATIVOS", stats['active_trades'])

# Gráfico de performance
if st.session_state.trade_monitor.trade_history:
    df = pd.DataFrame(st.session_state.trade_monitor.trade_history)
    
    if 'final_profit_percent' in df.columns:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['final_profit_percent'].cumsum(),
            mode='lines+markers',
            name='Lucro Acumulado',
            line=dict(color='green', width=2)
        ))
        
        fig.update_layout(
            title='Performance dos Trades',
            xaxis_title='Número do Trade',
            yaxis_title='Lucro Acumulado (%)',
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True)

# ==========================================================
# SEÇÃO 4: AUTO TRADING
# ==========================================================
if st.session_state.auto_trading:
    st.header("🤖 AUTO TRADING ATIVO")
    
    st.info("O sistema está monitorando automaticamente...")
    
    # Aqui você pode adicionar lógica para auto trading
    # Por exemplo: monitorar uma lista de tokens e entrar automaticamente
    
    # Atualizar a cada 10 segundos
    time.sleep(10)
    st.rerun()

# ==========================================================
# FOOTER
# ==========================================================
st.divider()

footer_col1, footer_col2 = st.columns(2)

with footer_col1:
    st.caption(f"🔄 Última atualização: {datetime.now().strftime('%H:%M:%S')}")

with footer_col2:
    if st.session_state.gemini_ai:
        st.caption("🤖 Gemini AI: ✅ CONECTADO")
    else:
        st.caption("🤖 Gemini AI: ❌ DESCONECTADO")

# ==========================================================
# CSS PARA MELHOR VISUALIZAÇÃO NO CELULAR
# ==========================================================
st.markdown("""
<style>
    /* Botões maiores para celular */
    .stButton > button {
        width: 100%;
        height: 48px;
        font-size: 16px;
        border-radius: 8px;
    }
    
    /* Inputs maiores */
    .stTextInput > div > div > input {
        height: 48px;
        font-size: 16px;
    }
    
    /* Títulos */
    h1, h2, h3 {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Espaçamento geral */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Cards de trade */
    .stContainer {
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        padding: 15px;
        margin: 10px 0;
    }
    
    /* Status colors */
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 10px;
        margin: 5px 0;
    }
    
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 10px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)
