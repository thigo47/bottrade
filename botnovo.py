import asyncio
import time
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import threading

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from concurrent.futures import ThreadPoolExecutor

# ============================================================================
# CONFIGURAÇÃO E CLASSES BASE
# ============================================================================

class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"

@dataclass
class Order:
    id: str
    symbol: str
    order_type: OrderType
    price: float
    quantity: float
    timestamp: datetime
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Optional[float] = None
    filled_time: Optional[datetime] = None
    
@dataclass
class Position:
    symbol: str
    quantity: float = 0.0
    entry_price: float = 0.0
    pnl: float = 0.0
    unrealized_pnl: float = 0.0
    last_update: datetime = field(default_factory=datetime.now)

@dataclass
class MarketData:
    symbol: str
    bid: float
    ask: float
    last: float
    timestamp: datetime
    volume_24h: float = 0.0

# ============================================================================
# SIMULADOR DE MERCADO
# ============================================================================

class SolanaMarketSimulator:
    """Simula o mercado de SOL com volatilidade realística"""
    
    def __init__(self, initial_price: float = 100.0):
        self.price = initial_price
        self.bid = initial_price * 0.999
        self.ask = initial_price * 1.001
        self.volatility = 0.002  # 0.2% de volatilidade
        self.trend = 0.0
        self.spread = 0.001  # 0.1% de spread
        self.last_update = datetime.now()
        self.price_history = deque(maxlen=1000)
        self.volume = 0.0
        
    def update_price(self) -> MarketData:
        """Atualiza o preço com movimento browniano geométrico"""
        current_time = datetime.now()
        time_diff = (current_time - self.last_update).total_seconds()
        
        # Random walk com reversão à média e tendência estocástica
        drift = 0.0001 * time_diff
        shock = random.gauss(0, 1) * self.volatility * np.sqrt(time_diff)
        
        # Ocasionalmente adiciona "spikes" de volatilidade (simulando memecoin)
        if random.random() < 0.05:  # 5% de chance de spike
            shock *= random.uniform(2, 5)
        
        # Atualiza tendência estocástica
        if random.random() < 0.1:
            self.trend = random.uniform(-0.001, 0.001)
        
        new_price = self.price * np.exp(drift + shock + self.trend)
        
        # Limita movimentos extremos
        max_move = 0.02  # 2% máximo por update
        price_change = (new_price - self.price) / self.price
        if abs(price_change) > max_move:
            new_price = self.price * (1 + np.sign(price_change) * max_move)
        
        self.price = new_price
        self.bid = self.price * (1 - self.spread/2)
        self.ask = self.price * (1 + self.spread/2)
        self.last_update = current_time
        
        # Atualiza volume
        self.volume += abs(shock) * random.uniform(1000, 10000)
        
        # Mantém histórico
        self.price_history.append({
            'timestamp': current_time,
            'price': self.price,
            'bid': self.bid,
            'ask': self.ask
        })
        
        return MarketData(
            symbol="SOL/USD",
            bid=self.bid,
            ask=self.ask,
            last=self.price,
            timestamp=current_time,
            volume_24h=self.volume
        )

# ============================================================================
# ESTRATÉGIA DE SCALPING
# ============================================================================

class ScalpingStrategy:
    """Implementa estratégia de scalping com triggers baseados em porcentagem"""
    
    def __init__(self):
        self.buy_threshold = -0.001  # -0.1% para compra
        self.sell_threshold = 0.0015  # +0.15% para venda
        self.stop_loss = -0.003  # -0.3% stop loss
        self.take_profit = 0.002  # +0.2% take profit
        self.max_position_size = 10.0  # Máximo de SOL por posição
        self.entry_price = None
        
    def should_buy(self, current_price: float, last_buy_price: Optional[float]) -> bool:
        """Decide se deve comprar baseado na variação do preço"""
        if last_buy_price:
            # Só compra se estiver X% abaixo da última compra
            price_change = (current_price - last_buy_price) / last_buy_price
            return price_change <= self.buy_threshold
        else:
            # Primeira compra - usa um threshold aleatório
            return random.random() < 0.3  # 30% de chance para primeira entrada
    
    def should_sell(self, entry_price: float, current_price: float) -> Tuple[bool, str]:
        """Decide se deve vender baseado em TP/SL"""
        if not entry_price:
            return False, "NO_POSITION"
            
        price_change = (current_price - entry_price) / entry_price
        
        if price_change <= self.stop_loss:
            return True, "STOP_LOSS"
        elif price_change >= self.take_profit:
            return True, "TAKE_PROFIT"
        elif price_change >= self.sell_threshold:
            return True, "PROFIT_TARGET"
            
        return False, "HOLD"

# ============================================================================
# MOTOR DE TRADING ASSÍNCRONO
# ============================================================================

class LowLatencyTradingEngine:
    """Motor de trading assíncrono com execução simulada de ordens"""
    
    def __init__(self, initial_balance: float = 10000.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trade_history: List[Dict] = []
        self.market_simulator = SolanaMarketSimulator()
        self.strategy = ScalpingStrategy()
        self.running = False
        self.loop = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.last_trade_time = None
        self.position_size = 2.0  # Tamanho fixo da posição em SOL
        
        # Métricas de performance
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.max_drawdown = 0.0
        self.highest_balance = initial_balance
        
        # Estado
        self.current_market_data = None
        self.last_buy_price = None
        
    def start(self):
        """Inicia o motor de trading em uma thread separada"""
        if not self.running:
            self.running = True
            self.loop = asyncio.new_event_loop()
            thread = threading.Thread(target=self._run_async_loop, daemon=True)
            thread.start()
    
    def _run_async_loop(self):
        """Executa o loop assíncrono em uma thread separada"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._trading_loop())
    
    async def _trading_loop(self):
        """Loop principal de trading executado a cada 500ms"""
        while self.running:
            try:
                start_time = time.time()
                
                # 1. Atualiza dados de mercado
                self.current_market_data = self.market_simulator.update_price()
                
                # 2. Processa ordens pendentes
                await self._process_orders()
                
                # 3. Executa estratégia
                await self._execute_strategy()
                
                # 4. Atualiza PnL das posições
                self._update_positions_pnl()
                
                # 5. Atualiza métricas
                self._update_metrics()
                
                # 6. Mantém intervalo de 500ms
                elapsed = time.time() - start_time
                if elapsed < 0.5:
                    await asyncio.sleep(0.5 - elapsed)
                    
            except Exception as e:
                print(f"Erro no loop de trading: {e}")
                await asyncio.sleep(1)
    
    async def _process_orders(self):
        """Processa ordens pendentes com simulação de latência de rede"""
        for order in self.orders[:]:
            if order.status == OrderStatus.PENDING:
                # Simula latência de rede (1-10ms)
                await asyncio.sleep(random.uniform(0.001, 0.01))
                
                # Preenchimento da ordem
                if order.order_type == OrderType.BUY:
                    fill_price = self.current_market_data.ask
                else:
                    fill_price = self.current_market_data.bid
                
                order.filled_price = fill_price
                order.filled_time = datetime.now()
                order.status = OrderStatus.FILLED
                
                # Executa a ordem
                self._execute_order(order)
    
    def _execute_order(self, order: Order):
        """Executa uma ordem preenchida"""
        if order.order_type == OrderType.BUY:
            cost = order.filled_price * order.quantity
            if cost <= self.balance:
                self.balance -= cost
                
                if order.symbol not in self.positions:
                    self.positions[order.symbol] = Position(symbol=order.symbol)
                
                position = self.positions[order.symbol]
                
                # Média do preço de entrada
                if position.quantity > 0:
                    total_cost = (position.quantity * position.entry_price) + cost
                    total_quantity = position.quantity + order.quantity
                    position.entry_price = total_cost / total_quantity
                else:
                    position.entry_price = order.filled_price
                
                position.quantity += order.quantity
                position.last_update = datetime.now()
                
                self.last_buy_price = order.filled_price
                
        elif order.order_type == OrderType.SELL and order.symbol in self.positions:
            position = self.positions[order.symbol]
            
            if position.quantity >= order.quantity:
                revenue = order.filled_price * order.quantity
                self.balance += revenue
                
                # Calcula PnL realizado
                entry_value = position.entry_price * order.quantity
                exit_value = order.filled_price * order.quantity
                trade_pnl = exit_value - entry_value
                
                # Atualiza estatísticas
                self.total_trades += 1
                if trade_pnl > 0:
                    self.winning_trades += 1
                else:
                    self.losing_trades += 1
                
                position.quantity -= order.quantity
                position.pnl += trade_pnl
                position.last_update = datetime.now()
                
                # Remove posição se zerada
                if position.quantity <= 0.0001:
                    del self.positions[order.symbol]
        
        # Registra no histórico
        trade_record = {
            'id': order.id,
            'timestamp': order.filled_time,
            'symbol': order.symbol,
            'side': order.order_type.value,
            'price': order.filled_price,
            'quantity': order.quantity,
            'cost': order.filled_price * order.quantity,
            'balance': self.balance,
            'position': self.positions.get(order.symbol, Position(order.symbol)).quantity
        }
        
        self.trade_history.append(trade_record)
        self.last_trade_time = datetime.now()
    
    async def _execute_strategy(self):
        """Executa a lógica da estratégia de scalping"""
        if not self.current_market_data:
            return
        
        current_price = self.current_market_data.last
        sol_position = self.positions.get("SOL/USD")
        
        # Lógica de ENTRADA (BUY)
        if not sol_position or sol_position.quantity < self.strategy.max_position_size:
            if self.strategy.should_buy(current_price, self.last_buy_price):
                # Cria ordem de compra
                order_id = f"BUY_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
                order = Order(
                    id=order_id,
                    symbol="SOL/USD",
                    order_type=OrderType.BUY,
                    price=current_price * 0.995,  # Ordem limitada ligeiramente abaixo
                    quantity=self.position_size,
                    timestamp=datetime.now()
                )
                self.orders.append(order)
        
        # Lógica de SAÍDA (SELL)
        if sol_position and sol_position.quantity > 0:
            should_sell, reason = self.strategy.should_sell(
                sol_position.entry_price, 
                current_price
            )
            
            if should_sell:
                # Cria ordem de venda
                order_id = f"SELL_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
                order = Order(
                    id=order_id,
                    symbol="SOL/USD",
                    order_type=OrderType.SELL,
                    price=current_price * 1.005,  # Ordem limitada ligeiramente acima
                    quantity=min(sol_position.quantity, self.position_size),
                    timestamp=datetime.now()
                )
                self.orders.append(order)
    
    def _update_positions_pnl(self):
        """Atualiza PnL não realizado das posições"""
        if not self.current_market_data:
            return
            
        for symbol, position in self.positions.items():
            if position.quantity > 0:
                current_value = position.quantity * self.current_market_data.last
                entry_value = position.quantity * position.entry_price
                position.unrealized_pnl = current_value - entry_value
    
    def _update_metrics(self):
        """Atualiza métricas de performance"""
        # Drawdown
        if self.balance > self.highest_balance:
            self.highest_balance = self.balance
        
        drawdown = (self.highest_balance - self.balance) / self.highest_balance
        self.max_drawdown = max(self.max_drawdown, drawdown)
    
    def get_performance_metrics(self) -> Dict:
        """Retorna métricas de performance"""
        total_pnl = self.balance - self.initial_balance
        roi = (total_pnl / self.initial_balance) * 100 if self.initial_balance > 0 else 0
        
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        return {
            'balance': self.balance,
            'total_pnl': total_pnl,
            'roi': roi,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'max_drawdown': self.max_drawdown * 100,
            'active_positions': len(self.positions),
            'last_trade_time': self.last_trade_time
        }
    
    def stop(self):
        """Para o motor de trading"""
        self.running = False

# ============================================================================
# INTERFACE STREAMLIT
# ============================================================================

def setup_streamlit_ui():
    """Configura a interface do Streamlit"""
    st.set_page_config(
        page_title="Solana Low-Latency Trading Bot",
        page_icon="🚀",
        layout="wide"
    )
    
    # Inicializa o motor de trading na sessão
    if 'trading_engine' not in st.session_state:
        st.session_state.trading_engine = LowLatencyTradingEngine()
        st.session_state.trading_engine.start()
    
    engine = st.session_state.trading_engine
    
    # CSS personalizado
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            color: #00D4AA;
            text-align: center;
            margin-bottom: 2rem;
        }
        .metric-card {
            background-color: #0E1117;
            border-radius: 10px;
            padding: 1.5rem;
            border-left: 4px solid #00D4AA;
        }
        .positive {
            color: #00D4AA;
        }
        .negative {
            color: #FF4B4B;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="main-header">🚀 Solana Low-Latency Trading Bot</h1>', unsafe_allow_html=True)
    
    # Colunas principais
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Gráfico de preço em tempo real
        st.subheader("📈 Preço SOL/USD em Tempo Real")
        
        if engine.current_market_data:
            price_data = list(engine.market_simulator.price_history)
            if price_data:
                df_prices = pd.DataFrame(price_data)
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_prices['timestamp'],
                    y=df_prices['price'],
                    mode='lines',
                    name='SOL/USD',
                    line=dict(color='#00D4AA', width=2)
                ))
                
                # Adiciona bandas de bid/ask
                fig.add_trace(go.Scatter(
                    x=df_prices['timestamp'],
                    y=df_prices['ask'],
                    mode='lines',
                    name='Ask',
                    line=dict(color='#FF4B4B', width=1, dash='dash'),
                    opacity=0.5
                ))
                
                fig.add_trace(go.Scatter(
                    x=df_prices['timestamp'],
                    y=df_prices['bid'],
                    mode='lines',
                    name='Bid',
                    line=dict(color='#00D4AA', width=1, dash='dash'),
                    opacity=0.5
                ))
                
                fig.update_layout(
                    height=400,
                    template='plotly_dark',
                    xaxis_title="Tempo",
                    yaxis_title="Preço (USD)",
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Métricas de trading
        st.subheader("📊 Métricas de Trading")
        
        metrics = engine.get_performance_metrics()
        
        # Saldo e PnL
        col_balance, col_pnl = st.columns(2)
        with col_balance:
            st.metric(
                "Saldo",
                f"${metrics['balance']:,.2f}",
                delta=f"{metrics['total_pnl']:+.2f}"
            )
        
        with col_pnl:
            pnl_color = "positive" if metrics['roi'] >= 0 else "negative"
            st.markdown(f"""
                <div class="metric-card">
                    <h4 style="margin-bottom: 10px;">ROI Total</h4>
                    <h2 class="{pnl_color}">{metrics['roi']:+.2f}%</h2>
                </div>
            """, unsafe_allow_html=True)
        
        # Estatísticas
        st.markdown("---")
        
        col_stats1, col_stats2 = st.columns(2)
        
        with col_stats1:
            st.metric("Trades Totais", metrics['total_trades'])
            st.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
        
        with col_stats2:
            st.metric("Posições Ativas", metrics['active_positions'])
            st.metric("Max Drawdown", f"{metrics['max_drawdown']:.2f}%")
    
    # Posições ativas
    st.markdown("---")
    st.subheader("💰 Posições Ativas")
    
    if engine.positions:
        positions_data = []
        for symbol, position in engine.positions.items():
            if position.quantity > 0:
                positions_data.append({
                    'Symbol': symbol,
                    'Quantity': position.quantity,
                    'Entry Price': f"${position.entry_price:.4f}",
                    'Unrealized PnL': f"${position.unrealized_pnl:.2f}",
                    'Last Update': position.last_update.strftime("%H:%M:%S")
                })
        
        if positions_data:
            st.dataframe(pd.DataFrame(positions_data), use_container_width=True)
        else:
            st.info("Nenhuma posição ativa no momento")
    else:
        st.info("Nenhuma posição ativa no momento")
    
    # Histórico de trades
    st.markdown("---")
    st.subheader("📋 Histórico de Trades")
    
    if engine.trade_history:
        # Mostra apenas os últimos 20 trades
        recent_trades = engine.trade_history[-20:]
        df_trades = pd.DataFrame(recent_trades)
        
        # Formata colunas
        if not df_trades.empty:
            df_trades['timestamp'] = pd.to_datetime(df_trades['timestamp'])
            df_trades['timestamp'] = df_trades['timestamp'].dt.strftime("%H:%M:%S")
            df_trades['cost'] = df_trades['cost'].apply(lambda x: f"${x:.2f}")
            df_trades['price'] = df_trades['price'].apply(lambda x: f"${x:.4f}")
            
            # Adiciona cor para compra/venda
            def color_side(val):
                color = '#00D4AA' if val == 'BUY' else '#FF4B4B'
                return f'color: {color}; font-weight: bold;'
            
            styled_df = df_trades[['timestamp', 'side', 'quantity', 'price', 'cost', 'balance']].style.applymap(
                color_side, subset=['side']
            )
            
            st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("Nenhum trade executado ainda")
    
    # Controles
    st.markdown("---")
    st.subheader("🎮 Controles")
    
    col_controls1, col_controls2, col_controls3 = st.columns(3)
    
    with col_controls1:
        if st.button("🔄 Reiniciar Bot", use_container_width=True):
            engine.stop()
            time.sleep(0.5)
            st.session_state.trading_engine = LowLatencyTradingEngine()
            st.session_state.trading_engine.start()
            st.rerun()
    
    with col_controls2:
        # Ajuste de parâmetros da estratégia
        st.markdown("**Parâmetros da Estratégia**")
        
        new_buy_threshold = st.slider(
            "Buy Threshold (%)",
            min_value=-1.0,
            max_value=0.0,
            value=engine.strategy.buy_threshold * 100,
            step=0.05,
            format="%.2f%%"
        )
        
        new_sell_threshold = st.slider(
            "Sell Threshold (%)",
            min_value=0.0,
            max_value=2.0,
            value=engine.strategy.sell_threshold * 100,
            step=0.05,
            format="%.2f%%"
        )
        
        engine.strategy.buy_threshold = new_buy_threshold / 100
        engine.strategy.sell_threshold = new_sell_threshold / 100
    
    with col_controls3:
        # Informações do sistema
        st.markdown("**Status do Sistema**")
        
        status_color = "🟢" if engine.running else "🔴"
        st.write(f"{status_color} Bot: {'Ativo' if engine.running else 'Inativo'}")
        
        if engine.current_market_data:
            st.write(f"📊 Preço Atual: ${engine.current_market_data.last:.4f}")
            st.write(f"🔁 Spread: {(engine.current_market_data.ask - engine.current_market_data.bid) / engine.current_market_data.last * 100:.2f}%")
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; color: #666; margin-top: 2rem;">
            <p>⚠️ <strong>Aviso:</strong> Este é um sistema de paper trading para fins educacionais.</p>
            <p>Não utilize com fundos reais. Desenvolvido para simulação de baixa latência na Solana.</p>
        </div>
    """, unsafe_allow_html=True)

# ============================================================================
# EXECUÇÃO PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    setup_streamlit_ui()