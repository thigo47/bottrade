import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import json
from datetime import datetime, timedelta
import plotly.graph_objects as go
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
                     take_profit: float) -> Dict:
        """Cria um novo trade com parâmetros definidos"""
        
        trade = {
            'id': len(self.active_trades) + 1,
            'symbol': token_data.get('symbol', 'TOKEN'),
            'ca': token_data.get('ca', ''),
            'entry_price': entry_price,
            'current_price': entry_price,
            'position_size': position_size,
            'stop_loss': stop_loss,  # Preço absoluto
            'take_profit': take_profit,  # Preço absoluto
            'status': 'ACTIVE',
            'entry_time': datetime.now(),
            'max_profit_percent': 0.0,
            'current_profit_percent': 0.0,
            'exit_price': None,
            'exit_time': None,
            'exit_reason': None,
            'trailing_stop_activated': False,
            'trailing_stop_price': stop_loss
        }
        
        self.active_trades.append(trade)
        return trade
    
    def update_trade_prices(self, ca: str, current_price: float):
        """Atualiza preços de todos os trades do token"""
        for trade in self.active_trades:
            if trade['ca'] == ca and trade['status'] == 'ACTIVE':
                trade['current_price'] = current_price
                
                # Calcular PnL atual
                trade['current_profit_percent'] = (
                    (current_price - trade['entry_price']) / trade['entry_price']
                ) * 100
                
                # Atualizar máximo profit
                if trade['current_profit_percent'] > trade['max_profit_percent']:
                    trade['max_profit_percent'] = trade['current_profit_percent']
                
                # Atualizar trailing stop
                self._update_trailing_stop(trade, current_price)
    
    def _update_trailing_stop(self, trade: Dict, current_price: float):
        """Atualiza trailing stop dinâmico"""
        if trade['max_profit_percent'] >= 5.0:  # Só ativa trailing após 5% de gain
            # Trailing stop: mantém 30% do lucro máximo
            trail_distance = trade['max_profit_percent'] * 0.3
            new_stop = trade['entry_price'] * (1 + (trade['max_profit_percent'] - trail_distance) / 100)
            
            if new_stop > trade['trailing_stop_price']:
                trade['trailing_stop_price'] = new_stop
                trade['trailing_stop_activated'] = True
    
    def check_exit_conditions(self, trade: Dict) -> Tuple[bool, str, float]:
        """Verifica condições de saída do trade"""
        
        current_price = trade['current_price']
        entry_price = trade['entry_price']
        
        # 1. TAKE PROFIT - Vários níveis
        take_profit_levels = [
            (trade['take_profit'], "TAKE_PROFIT_FULL"),
            (entry_price * 1.05, "TAKE_PROFIT_5%"),
            (entry_price * 1.10, "TAKE_PROFIT_10%"),
            (entry_price * 1.15, "TAKE_PROFIT_15%"),
            (entry_price * 1.20, "TAKE_PROFIT_20%")
        ]
        
        for tp_price, reason in take_profit_levels:
            if current_price >= tp_price:
                return True, reason, current_price
        
        # 2. STOP LOSS - Múltiplas condições
        # Stop loss original
        if current_price <= trade['stop_loss']:
            return True, "STOP_LOSS_ORIGINAL", current_price
        
        # Stop loss por percentual fixo (-10%)
        if trade['current_profit_percent'] <= -10.0:
            return True, "STOP_LOSS_10%", current_price
        
        # Trailing stop
        if trade['trailing_stop_activated'] and current_price <= trade['trailing_stop_price']:
            return True, "TRAILING_STOP", current_price
        
        # Stop loss dinâmico (se teve alto gain e caiu muito)
        if trade['max_profit_percent'] >= 20.0 and trade['current_profit_percent'] <= trade['max_profit_percent'] * 0.5:
            return True, "DYNAMIC_STOP", current_price
        
        return False, "", 0.0
    
    def execute_auto_exit(self):
        """Executa saídas automáticas para todos os trades ativos"""
        closed_trades = []
        
        for trade in self.active_trades[:]:  # Copia para poder remover
            if trade['status'] == 'ACTIVE':
                should_exit, reason, exit_price = self.check_exit_conditions(trade)
                
                if should_exit:
                    # Fechar trade
                    trade['status'] = 'CLOSED'
                    trade['exit_price'] = exit_price
                    trade['exit_time'] = datetime.now()
                    trade['exit_reason'] = reason
                    
                    # Calcular resultado final
                    profit_percent = ((exit_price - trade['entry_price']) / trade['entry_price']) * 100
                    profit_value = trade['position_size'] * (profit_percent / 100)
                    
                    trade['final_profit_percent'] = profit_percent
                    trade['final_profit_value'] = profit_value
                    
                    # Atualizar performance
                    self.performance['total_trades'] += 1
                    if profit_percent > 0:
                        self.performance['winning_trades'] += 1
                    self.performance['total_profit'] += profit_value
                    
                    if profit_value > 0:
                        self.performance['max_profit'] = max(self.performance['max_profit'], profit_value)
                    else:
                        self.performance['max_loss'] = min(self.performance['max_loss'], profit_value)
                    
                    # Mover para histórico
                    self.trade_history.append(trade.copy())
                    self.active_trades.remove(trade)
                    
                    closed_trades.append(trade)
        
        return closed_trades
    
    def get_performance_stats(self) -> Dict:
        """Retorna estatísticas de performance - VERSÃO CORRIGIDA"""
        # Garantir que sempre retorna os campos necessários
        default_stats = {
            'win_rate': 0.0,
            'avg_profit': 0.0,
            'total_profit': 0.0,
            'profit_factor': 0.0,
            'active_trades': len(self.active_trades),
            'total_trades': self.performance.get('total_trades', 0)
        }
        
        if self.performance['total_trades'] == 0:
            return default_stats
        
        try:
            win_rate = (self.performance['winning_trades'] / self.performance['total_trades']) * 100
            avg_profit = self.performance['total_profit'] / self.performance['total_trades']
            
            # Calcular profit factor (lucro total / prejuízo total)
            winning_trades = [t for t in self.trade_history if t.get('final_profit_percent', 0) > 0]
            losing_trades = [t for t in self.trade_history if t.get('final_profit_percent', 0) < 0]
            
            total_wins = sum(t.get('final_profit_value', 0) for t in winning_trades)
            total_losses = abs(sum(t.get('final_profit_value', 0) for t in losing_trades))
            
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
            
            return {
                'win_rate': round(win_rate, 2),
                'avg_profit': round(avg_profit, 2),
                'total_profit': round(self.performance['total_profit'], 2),
                'profit_factor': round(profit_factor, 2),
                'active_trades': len(self.active_trades),
                'total_trades': self.performance['total_trades']
            }
            
        except Exception:
            # Se der erro, retorna os defaults
            return default_stats

# ==========================================================
# SISTEMA DE DECISÃO AUTOMÁTICA
# ==========================================================
class AutoDecisionEngine:
    """Motor de decisão automática para entrada/saída"""
    
    def __init__(self):
        self.min_confidence = 0.7  # 70% de confiança mínima
        self.max_position_percent = 15  # Máximo 15% por trade
        self.risk_reward_ratio = 2.0  # 1:2 mínimo
    
    def analyze_entry_signal(self, token_data: Dict, current_price: float) -> Dict:
        """Analisa se deve entrar no trade"""
        
        # Simulação de análise IA
        analysis_score = self._calculate_analysis_score(token_data)
        
        if analysis_score >= self.min_confidence:
            # Calcular parâmetros do trade
            stop_loss = current_price * 0.90  # -10%
            take_profit = current_price * 1.20  # +20%
            
            # Calcular tamanho da posição baseado no score
            position_percent = min(
                self.max_position_percent,
                analysis_score * self.max_position_percent
            )
            
            return {
                'should_enter': True,
                'confidence': analysis_score,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'position_percent': position_percent,
                'risk_reward': (take_profit - current_price) / (current_price - stop_loss)
            }
        
        return {'should_enter': False, 'confidence': analysis_score}
    
    def _calculate_analysis_score(self, token_data: Dict) -> float:
        """Calcula score de análise (simulação)"""
        try:
            # Fatores de análise
            factors = []
            
            # 1. Volume
            volume = float(token_data.get('pairs', [{}])[0].get('volume', {}).get('h24', 0))
            if volume > 100000:
                factors.append(0.8)
            elif volume > 50000:
                factors.append(0.6)
            elif volume > 10000:
                factors.append(0.4)
            else:
                factors.append(0.2)
            
            # 2. Liquidez
            liquidity = float(token_data.get('pairs', [{}])[0].get('liquidity', {}).get('usd', 0))
            if liquidity > 50000:
                factors.append(0.9)
            elif liquidity > 20000:
                factors.append(0.7)
            elif liquidity > 5000:
                factors.append(0.5)
            else:
                factors.append(0.3)
            
            # 3. Variação recente
            price_change = float(token_data.get('pairs', [{}])[0].get('priceChange', {}).get('h24', 0))
            if 5 < price_change < 30:  # Crescimento saudável
                factors.append(0.8)
            elif price_change > 0:
                factors.append(0.6)
            else:
                factors.append(0.4)
            
            # 4. Relação compra/venda
            txns = token_data.get('pairs', [{}])[0].get('txns', {}).get('h24', {})
            buys = txns.get('buys', 1)
            sells = txns.get('sells', 1)
            buy_ratio = buys / (buys + sells)
            
            if buy_ratio > 0.6:
                factors.append(0.9)
            elif buy_ratio > 0.5:
                factors.append(0.7)
            else:
                factors.append(0.4)
            
            # Score médio
            return round(np.mean(factors), 2)
            
        except:
            return 0.0

# ==========================================================
# INICIALIZAÇÃO DO STREAMLIT
# ==========================================================
# Inicializar sistemas
if 'trade_monitor' not in st.session_state:
    st.session_state.trade_monitor = AutoTradeMonitor()

if 'decision_engine' not in st.session_state:
    st.session_state.decision_engine = AutoDecisionEngine()

if 'auto_trading' not in st.session_state:
    st.session_state.auto_trading = False

if 'balance' not in st.session_state:
    st.session_state.balance = 1000.0

if 'token_watchlist' not in st.session_state:
    st.session_state.token_watchlist = []

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
            # Adicionar CA aos dados
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
st.title("🤖 SNIPER PRO AI - AUTO TRADER")
st.markdown("### Sistema Automático com Saída Inteligente")

# Sidebar
with st.sidebar:
    st.header("⚙️ CONTROLES")
    
    # Status do sistema
    stats = st.session_state.trade_monitor.get_performance_stats()
    
    st.metric("💰 SALDO", f"${st.session_state.balance:,.2f}")
    st.metric("🎯 WIN RATE", f"{stats.get('win_rate', 0):.1f}%")
    st.metric("📊 LUCRO TOTAL", f"${stats.get('total_profit', 0):+,.2f}")
    
    st.divider()
    
    # Controles de auto trading
    st.subheader("🤖 AUTO TRADING")
    
    auto_mode = st.toggle("MODO AUTOMÁTICO", value=st.session_state.auto_trading)
    if auto_mode != st.session_state.auto_trading:
        st.session_state.auto_trading = auto_mode
        if auto_mode:
            st.success("Auto trading ATIVADO!")
        else:
            st.warning("Auto trading DESATIVADO!")
    
    st.divider()
    
    # Configurações
    st.subheader("⚙️ CONFIGURAÇÕES")
    
    st.number_input("💰 SALDO INICIAL", value=1000.0, min_value=100.0, step=100.0, 
                   key="initial_balance")
    
    st.slider("🎯 CONFIANÇA MÍNIMA (%)", 50, 95, 70, key="min_confidence")
    st.slider("⚠️ STOP LOSS (%)", 5, 20, 10, key="stop_loss_percent")
    st.slider("🚀 TAKE PROFIT (%)", 10, 50, 20, key="take_profit_percent")
    st.slider("💰 POSIÇÃO MÁX (%)", 5, 30, 15, key="max_position_percent")
    
    st.divider()
    
    # Ações
    if st.button("🔄 ATUALIZAR TUDO"):
        st.rerun()
    
    if st.button("📊 EXPORTAR DADOS"):
        if st.session_state.trade_monitor.trade_history:
            df = pd.DataFrame(st.session_state.trade_monitor.trade_history)
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇️ BAIXAR CSV",
                data=csv,
                file_name="trades_auto.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    if st.button("🧹 LIMPAR HISTÓRICO"):
        st.session_state.trade_monitor.trade_history = []
        st.session_state.trade_monitor.active_trades = []
        st.session_state.trade_monitor.performance = {
            'total_trades': 0,
            'winning_trades': 0,
            'total_profit': 0.0,
            'max_profit': 0.0,
            'max_loss': 0.0
        }
        st.success("Histórico limpo!")
        st.rerun()

# ==========================================================
# SEÇÃO DE MONITORAMENTO DE TOKENS
# ==========================================================
st.header("🔍 MONITORAR TOKENS")

col_watch1, col_watch2 = st.columns([3, 1])

with col_watch1:
    new_token_ca = st.text_input(
        "Adicionar token à watchlist:",
        placeholder="Cole o CA do token...",
        key="new_token_input"
    )

with col_watch2:
    if st.button("➕ ADICIONAR", use_container_width=True) and new_token_ca:
        data = fetch_token_data(new_token_ca.strip())
        if data:
            token_info = {
                'ca': new_token_ca.strip(),
                'symbol': data.get('symbol', 'TOKEN'),
                'last_price': float(data['pairs'][0].get('priceUsd', 0)),
                'last_update': datetime.now()
            }
            # Verificar se já existe
            if not any(t['ca'] == token_info['ca'] for t in st.session_state.token_watchlist):
                st.session_state.token_watchlist.append(token_info)
                st.success(f"Token {token_info['symbol']} adicionado!")
                st.rerun()
            else:
                st.warning("Token já está na watchlist")
        else:
            st.error("Token não encontrado")

# Mostrar watchlist
if st.session_state.token_watchlist:
    st.subheader("📊 TOKENS MONITORADOS")
    
    # Atualizar preços
    for token in st.session_state.token_watchlist:
        current_price = get_current_price(token['ca'])
        if current_price:
            token['last_price'] = current_price
            token['last_update'] = datetime.now()
    
    # Mostrar em colunas
    cols = st.columns(min(5, len(st.session_state.token_watchlist)))
    
    for idx, token in enumerate(st.session_state.token_watchlist[:5]):
        with cols[idx % 5]:
            with st.container(border=True):
                st.markdown(f"**{token['symbol']}**")
                st.markdown(f"`${token['last_price']:.10f}`")
                st.caption(f"Última: {token['last_update'].strftime('%H:%M:%S')}")
                
                # Botão para análise rápida
                if st.button("🧠 ANALISAR", key=f"analyze_{token['ca']}", use_container_width=True):
                    st.session_state.selected_token_ca = token['ca']
                    st.rerun()

# ==========================================================
# SEÇÃO DE ANÁLISE E ENTRADA
# ==========================================================
if 'selected_token_ca' in st.session_state and st.session_state.selected_token_ca:
    st.header("🎯 ANÁLISE DE ENTRADA")
    
    token_data = fetch_token_data(st.session_state.selected_token_ca)
    
    if token_data:
        current_price = float(token_data['pairs'][0].get('priceUsd', 0))
        
        col_analysis1, col_analysis2 = st.columns([2, 1])
        
        with col_analysis1:
            # Análise automática
            analysis = st.session_state.decision_engine.analyze_entry_signal(
                token_data, current_price
            )
            
            st.metric("💰 PREÇO ATUAL", f"${current_price:.10f}")
            st.metric("🎯 CONFIANÇA", f"{analysis['confidence']*100:.1f}%")
            
            if analysis['should_enter']:
                st.success("✅ SINAL DE COMPRA DETECTADO!")
                
                # Mostrar parâmetros sugeridos
                st.info(f"""
                **Parâmetros Sugeridos:**
                • Stop Loss: ${analysis['stop_loss']:.10f} (-10%)
                • Take Profit: ${analysis['take_profit']:.10f} (+20%)
                • Tamanho Posição: {analysis['position_percent']:.1f}% do saldo
                • Risk/Reward: 1:{analysis['risk_reward']:.1f}
                """)
                
                # Calcular valores
                position_value = st.session_state.balance * (analysis['position_percent'] / 100)
                
                # Botão de entrada manual
                if st.button("🚀 ENTRAR COM PARÂMETROS SUGERIDOS", type="primary", use_container_width=True):
                    # Criar trade
                    trade = st.session_state.trade_monitor.create_trade(
                        token_data=token_data,
                        position_size=position_value,
                        entry_price=current_price,
                        stop_loss=analysis['stop_loss'],
                        take_profit=analysis['take_profit']
                    )
                    
                    st.session_state.balance -= position_value
                    st.success(f"Trade iniciado para {token_data['symbol']}!")
                    st.rerun()
            
            else:
                st.warning(f"⚠️ NÃO ENTRAR - Confiança muito baixa ({analysis['confidence']*100:.1f}%)")
        
        with col_analysis2:
            # Entrada manual
            st.subheader("🎮 ENTRADA MANUAL")
            
            position_percent = st.slider("Tamanho da posição (%):", 1.0, 30.0, 10.0, 1.0)
            stop_loss_percent = st.slider("Stop Loss (%):", 5.0, 30.0, 10.0, 1.0)
            take_profit_percent = st.slider("Take Profit (%):", 10.0, 100.0, 20.0, 5.0)
            
            position_value = st.session_state.balance * (position_percent / 100)
            stop_loss_price = current_price * (1 - stop_loss_percent/100)
            take_profit_price = current_price * (1 + take_profit_percent/100)
            
            st.metric("💰 VALOR POSIÇÃO", f"${position_value:,.2f}")
            st.metric("⚠️ STOP LOSS", f"${stop_loss_price:.10f}")
            st.metric("🚀 TAKE PROFIT", f"${take_profit_price:.10f}")
            
            if st.button("🎯 ENTRAR MANUALMENTE", use_container_width=True):
                trade = st.session_state.trade_monitor.create_trade(
                    token_data=token_data,
                    position_size=position_value,
                    entry_price=current_price,
                    stop_loss=stop_loss_price,
                    take_profit=take_profit_price
                )
                
                st.session_state.balance -= position_value
                st.success(f"Trade manual iniciado para {token_data['symbol']}!")
                st.rerun()

# ==========================================================
# SEÇÃO DE TRADES ATIVOS
# ==========================================================
st.header("📈 TRADES ATIVOS")

# Atualizar preços e verificar saídas
if st.session_state.trade_monitor.active_trades:
    # Atualizar todos os preços
    for trade in st.session_state.trade_monitor.active_trades:
        current_price = get_current_price(trade['ca'])
        if current_price:
            st.session_state.trade_monitor.update_trade_prices(trade['ca'], current_price)
    
    # Executar saídas automáticas
    closed_trades = st.session_state.trade_monitor.execute_auto_exit()
    
    # Mostrar trades fechados recentemente
    if closed_trades:
        st.subheader("🔒 TRADES FECHADOS RECENTEMENTE")
        for trade in closed_trades[-3:]:  # Mostrar últimos 3
            profit_color = "green" if trade.get('final_profit_percent', 0) > 0 else "red"
            
            st.markdown(f"""
            <div style='border: 2px solid {profit_color}; border-radius: 10px; padding: 10px; margin: 10px 0;'>
                <strong>{trade.get('symbol', 'TOKEN')}</strong> - {trade.get('exit_reason', 'DESCONHECIDO')}<br>
                Entrada: ${trade.get('entry_price', 0):.10f} | Saída: ${trade.get('exit_price', 0):.10f}<br>
                <span style='color:{profit_color}; font-weight:bold;'>
                    Resultado: {trade.get('final_profit_percent', 0):+.2f}% (${trade.get('final_profit_value', 0):+.2f})
                </span>
            </div>
            """, unsafe_allow_html=True)
            
            # Adicionar ao saldo
            st.session_state.balance += trade.get('position_size', 0) + trade.get('final_profit_value', 0)
    
    # Mostrar trades ativos
    st.subheader("🟢 TRADES EM ANDAMENTO")
    
    cols = st.columns(3)
    
    for idx, trade in enumerate(st.session_state.trade_monitor.active_trades[:6]):  # Mostrar até 6
        with cols[idx % 3]:
            with st.container(border=True, height=250):
                # Status
                profit_percent = trade.get('current_profit_percent', 0)
                profit_color = "green" if profit_percent >= 0 else "red"
                
                st.markdown(f"**{trade.get('symbol', 'TOKEN')}** (ID: {trade.get('id', '?')})")
                st.markdown(f"<span style='color:{profit_color}; font-size:24px; font-weight:bold;'>{profit_percent:+.2f}%</span>", 
                          unsafe_allow_html=True)
                
                # Informações
                st.caption(f"Entrada: ${trade.get('entry_price', 0):.10f}")
                st.caption(f"Atual: ${trade.get('current_price', 0):.10f}")
                
                # Stop Loss e Take Profit
                st.caption(f"⛔ Stop: ${trade.get('stop_loss', 0):.10f}")
                st.caption(f"🎯 Take Profit: ${trade.get('take_profit', 0):.10f}")
                
                if trade.get('trailing_stop_activated', False):
                    st.caption(f"📊 Trailing Stop: ${trade.get('trailing_stop_price', 0):.10f}")
                
                # Máximo atingido
                if trade.get('max_profit_percent', 0) > 0:
                    st.caption(f"📈 Máximo: {trade.get('max_profit_percent', 0):+.2f}%")
                
                # Botão de saída manual
                if st.button("⏹️ SAIR MANUAL", key=f"exit_{trade.get('id', '?')}", use_container_width=True):
                    # Fechar trade manualmente
                    current_price = get_current_price(trade.get('ca', ''))
                    if current_price:
                        profit_percent = ((current_price - trade.get('entry_price', 0)) / trade.get('entry_price', 1)) * 100
                        profit_value = trade.get('position_size', 0) * (profit_percent / 100)
                        
                        trade['status'] = 'CLOSED'
                        trade['exit_price'] = current_price
                        trade['exit_time'] = datetime.now()
                        trade['exit_reason'] = 'MANUAL_EXIT'
                        trade['final_profit_percent'] = profit_percent
                        trade['final_profit_value'] = profit_value
                        
                        st.session_state.trade_monitor.trade_history.append(trade.copy())
                        st.session_state.trade_monitor.active_trades.remove(trade)
                        
                        st.session_state.balance += trade.get('position_size', 0) + profit_value
                        st.success(f"Trade fechado manualmente: {profit_percent:+.2f}%")
                        st.rerun()
else:
    st.info("Nenhum trade ativo no momento.")

# ==========================================================
# SEÇÃO DE HISTÓRICO E ESTATÍSTICAS - VERSÃO CORRIGIDA
# ==========================================================
st.header("📊 HISTÓRICO E ESTATÍSTICAS")

col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)

with col_stats1:
    stats = st.session_state.trade_monitor.get_performance_stats()
    st.metric("🎯 WIN RATE", f"{stats.get('win_rate', 0):.1f}%")

with col_stats2:
    st.metric("💰 LUCRO TOTAL", f"${stats.get('total_profit', 0):+,.2f}")

with col_stats3:
    st.metric("📊 TRADES", stats.get('total_trades', 0))

with col_stats4:
    profit_factor = stats.get('profit_factor', 0)
    if profit_factor == float('inf'):
        st.metric("📈 FACTOR", "∞")
    else:
        st.metric("📈 FACTOR", f"{profit_factor:.2f}")

# Gráfico de performance
if st.session_state.trade_monitor.trade_history:
    df_history = pd.DataFrame(st.session_state.trade_monitor.trade_history)
    
    # Gráfico de lucro acumulado
    if not df_history.empty and 'final_profit_value' in df_history.columns:
        df_history['cumulative_profit'] = df_history['final_profit_value'].cumsum()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_history.index,
            y=df_history['cumulative_profit'],
            mode='lines+markers',
            name='Lucro Acumulado',
            line=dict(color='green', width=3)
        ))
        
        fig.update_layout(
            title='Lucro Acumulado ao Longo do Tempo',
            xaxis_title='Número do Trade',
            yaxis_title='Lucro Acumulado ($)',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabela de histórico
        st.subheader("📜 ÚLTIMOS TRADES")
        
        # Filtrar colunas que existem
        available_columns = [col for col in ['symbol', 'exit_reason', 'entry_price', 'exit_price', 'final_profit_percent'] 
                           if col in df_history.columns]
        
        if available_columns:
            recent_trades = df_history[available_columns].tail(10).sort_index(ascending=False)
            
            for _, trade in recent_trades.iterrows():
                profit_percent = trade.get('final_profit_percent', 0)
                profit_color = "🟢" if profit_percent > 0 else "🔴"
                
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.text(f"{trade.get('symbol', 'TOKEN')} - {trade.get('exit_reason', 'DESCONHECIDO')}")
                
                with col2:
                    st.text(f"Entrada: ${trade.get('entry_price', 0):.8f}")
                    st.text(f"Saída: ${trade.get('exit_price', 0):.8f}")
                
                with col3:
                    st.markdown(f"**{profit_color} {profit_percent:+.2f}%**")

# ==========================================================
# SISTEMA DE AUTO TRADING
# ==========================================================
if st.session_state.auto_trading and st.session_state.token_watchlist:
    st.header("🤖 AUTO TRADING ATIVO")
    
    # Processar cada token na watchlist
    for token in st.session_state.token_watchlist:
        # Verificar se já tem trade ativo para este token
        active_trade_for_token = any(
            t.get('ca') == token.get('ca') and t.get('status') == 'ACTIVE' 
            for t in st.session_state.trade_monitor.active_trades
        )
        
        if not active_trade_for_token:
            # Analisar entrada
            token_data = fetch_token_data(token.get('ca', ''))
            if token_data:
                current_price = get_current_price(token.get('ca', ''))
                if current_price:
                    analysis = st.session_state.decision_engine.analyze_entry_signal(
                        token_data, current_price
                    )
                    
                    if analysis['should_enter']:
                        # Calcular posição
                        position_percent = analysis['position_percent']
                        position_value = st.session_state.balance * (position_percent / 100)
                        
                        # Criar trade automaticamente
                        if position_value > 1:  # Mínimo $1
                            trade = st.session_state.trade_monitor.create_trade(
                                token_data=token_data,
                                position_size=position_value,
                                entry_price=current_price,
                                stop_loss=analysis['stop_loss'],
                                take_profit=analysis['take_profit']
                            )
                            
                            st.session_state.balance -= position_value
                            st.success(f"🤖 Auto trade iniciado para {token.get('symbol', 'TOKEN')}!")
    
    st.info(f"Monitorando {len(st.session_state.token_watchlist)} tokens...")

# ==========================================================
# ATUALIZAÇÃO AUTOMÁTICA
# ==========================================================
if st.session_state.auto_trading or st.session_state.trade_monitor.active_trades:
    # Atualizar a cada 10 segundos
    time.sleep(10)
    st.rerun()

# ==========================================================
# FOOTER
# ==========================================================
st.divider()
footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption(f"🔄 Última atualização: {datetime.now().strftime('%H:%M:%S')}")

with footer_col2:
    active_trades = len(st.session_state.trade_monitor.active_trades)
    st.caption(f"📈 Trades ativos: {active_trades}")

with footer_col3:
    st.caption("🤖 Sniper Pro Auto Trader v1.0")

# ==========================================================
# CSS
# ==========================================================
# ==========================================================
# ATUALIZAÇÃO AUTOMÁTICA
# ==========================================================
if st.session_state.auto_trading or st.session_state.trade_monitor.active_trades:
    # Atualizar a cada 10 segundos
    time.sleep(10)
    st.rerun()

# ==========================================================
# FOOTER
# ==========================================================
st.divider()
footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption(f"🔄 Última atualização: {datetime.now().strftime('%H:%M:%S')}")

with footer_col2:
    active_trades = len(st.session_state.trade_monitor.active_trades)
    st.caption(f"📈 Trades ativos: {active_trades}")

with footer_col3:
    st.caption("🤖 Sniper Pro Auto Trader v1.0")

# ==========================================================
# CSS
# ==========================================================
# CSS simplificado para testar
st.markdown("""
<style>
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)
