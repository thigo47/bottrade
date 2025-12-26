import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

# ==========================================================
# CONFIGURAÇÃO SIMPLES
# ==========================================================
st.set_page_config(
    page_title="Sniper Pro - Trading Bot",
    page_icon="💰",
    layout="wide"
)

# ==========================================================
# SISTEMA BÁSICO DE TRADING
# ==========================================================
class SimpleTradingBot:
    def __init__(self):
        self.balance = 1000.0
        self.active_trades = []
        self.trade_history = []
        self.last_update = datetime.now()
    
    def create_trade(self, symbol: str, ca: str, entry_price: float, 
                    position_size: float, stop_loss_percent: float = 10.0,
                    take_profit_percent: float = 20.0):
        """Cria um novo trade"""
        
        stop_loss_price = entry_price * (1 - stop_loss_percent/100)
        take_profit_price = entry_price * (1 + take_profit_percent/100)
        
        trade = {
            'id': len(self.active_trades) + 1,
            'symbol': symbol,
            'ca': ca,
            'entry_price': entry_price,
            'current_price': entry_price,
            'position_size': position_size,
            'stop_loss': stop_loss_price,
            'take_profit': take_profit_price,
            'status': 'ACTIVE',
            'entry_time': datetime.now(),
            'max_profit': 0.0,
            'current_profit': 0.0,
            'exit_price': None,
            'exit_time': None,
            'exit_reason': None
        }
        
        self.active_trades.append(trade)
        self.balance -= position_size
        return trade
    
    def update_prices(self):
        """Atualiza preços de todos os trades ativos"""
        for trade in self.active_trades:
            if trade['status'] == 'ACTIVE':
                try:
                    url = f"https://api.dexscreener.com/latest/dex/tokens/{trade['ca']}"
                    response = requests.get(url, timeout=5)
                    data = response.json()
                    
                    if data and data.get('pairs'):
                        current_price = float(data['pairs'][0].get('priceUsd', trade['current_price']))
                        trade['current_price'] = current_price
                        
                        # Calcular profit atual
                        profit = ((current_price - trade['entry_price']) / trade['entry_price']) * 100
                        trade['current_profit'] = profit
                        
                        # Atualizar máximo profit
                        if profit > trade['max_profit']:
                            trade['max_profit'] = profit
                except:
                    continue
        
        self.last_update = datetime.now()
    
    def check_exits(self):
        """Verifica condições de saída"""
        closed_trades = []
        
        for trade in self.active_trades[:]:
            if trade['status'] == 'ACTIVE':
                current_price = trade['current_price']
                
                # TAKE PROFIT
                if current_price >= trade['take_profit']:
                    trade['status'] = 'CLOSED'
                    trade['exit_price'] = current_price
                    trade['exit_time'] = datetime.now()
                    trade['exit_reason'] = 'TAKE_PROFIT'
                    closed_trades.append(trade)
                
                # STOP LOSS
                elif current_price <= trade['stop_loss']:
                    trade['status'] = 'CLOSED'
                    trade['exit_price'] = current_price
                    trade['exit_time'] = datetime.now()
                    trade['exit_reason'] = 'STOP_LOSS'
                    closed_trades.append(trade)
                
                # TRAILING STOP (se teve 10%+ e caiu 30% do máximo)
                elif trade['max_profit'] >= 10.0:
                    current_drop = trade['max_profit'] - trade['current_profit']
                    if current_drop >= (trade['max_profit'] * 0.3):
                        trade['status'] = 'CLOSED'
                        trade['exit_price'] = current_price
                        trade['exit_time'] = datetime.now()
                        trade['exit_reason'] = 'TRAILING_STOP'
                        closed_trades.append(trade)
        
        # Mover trades fechados para histórico
        for trade in closed_trades:
            self.active_trades.remove(trade)
            
            # Calcular resultado final
            profit_percent = trade['current_profit']
            profit_value = trade['position_size'] * (profit_percent / 100)
            
            trade['final_profit_percent'] = profit_percent
            trade['final_profit_value'] = profit_value
            
            # Adicionar ao saldo
            self.balance += trade['position_size'] + profit_value
            
            self.trade_history.append(trade)
        
        return closed_trades
    
    def get_stats(self):
        """Retorna estatísticas"""
        if not self.trade_history:
            return {
                'win_rate': 0,
                'total_profit': 0,
                'total_trades': 0
            }
        
        winning_trades = [t for t in self.trade_history if t['final_profit_percent'] > 0]
        win_rate = (len(winning_trades) / len(self.trade_history)) * 100
        total_profit = sum(t['final_profit_value'] for t in self.trade_history)
        
        return {
            'win_rate': round(win_rate, 2),
            'total_profit': round(total_profit, 2),
            'total_trades': len(self.trade_history),
            'active_trades': len(self.active_trades),
            'balance': round(self.balance, 2)
        }

# ==========================================================
# INICIALIZAÇÃO
# ==========================================================
if 'bot' not in st.session_state:
    st.session_state.bot = SimpleTradingBot()

if 'selected_ca' not in st.session_state:
    st.session_state.selected_ca = None

# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================
def fetch_token_data(ca: str):
    """Busca dados do token"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if data and data.get('pairs'):
            pair = data['pairs'][0]
            return {
                'symbol': pair.get('baseToken', {}).get('symbol', 'TOKEN'),
                'price': float(pair.get('priceUsd', 0)),
                'volume_24h': float(pair.get('volume', {}).get('h24', 0)),
                'liquidity': float(pair.get('liquidity', {}).get('usd', 0))
            }
    except:
        pass
    return None

def format_price(price: float) -> str:
    """Formata preço para exibição"""
    if price >= 1:
        return f"${price:.4f}"
    elif price >= 0.0001:
        return f"${price:.6f}"
    else:
        return f"${price:.10f}"

# ==========================================================
# INTERFACE PRINCIPAL
# ==========================================================
st.title("💰 Sniper Pro - Trading Bot Simples")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Controles")
    
    stats = st.session_state.bot.get_stats()
    
    st.metric("💰 Saldo", f"${stats['balance']:,.2f}")
    st.metric("🎯 Win Rate", f"{stats['win_rate']:.1f}%")
    st.metric("📊 Lucro Total", f"${stats['total_profit']:+,.2f}")
    
    st.divider()
    
    if st.button("🔄 Atualizar Preços", use_container_width=True):
        st.session_state.bot.update_prices()
        st.session_state.bot.check_exits()
        st.rerun()
    
    if st.button("📊 Exportar Dados", use_container_width=True):
        if st.session_state.bot.trade_history:
            df = pd.DataFrame(st.session_state.bot.trade_history)
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇️ Baixar CSV",
                data=csv,
                file_name="trades.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    st.divider()
    
    st.info(f"Última atualização: {st.session_state.bot.last_update.strftime('%H:%M:%S')}")

# ==========================================================
# SEÇÃO DE ENTRADA DE TRADE
# ==========================================================
st.header("🎯 Nova Entrada")

col1, col2 = st.columns([2, 1])

with col1:
    token_ca = st.text_input(
        "Contract Address (CA):",
        placeholder="Cole o CA do token...",
        help="Exemplo: So11111111111111111111111111111111111111112"
    )
    
    if token_ca:
        token_data = fetch_token_data(token_ca.strip())
        
        if token_data:
            st.success(f"✅ Token encontrado: **{token_data['symbol']}**")
            st.info(f"Preço atual: {format_price(token_data['price'])}")
            
            position_size = st.number_input(
                "Valor da posição ($):",
                min_value=1.0,
                max_value=float(st.session_state.bot.balance),
                value=min(100.0, st.session_state.bot.balance * 0.1)
            )
            
            col_sl, col_tp = st.columns(2)
            
            with col_sl:
                stop_loss = st.slider("Stop Loss (%)", 1, 30, 10, 1)
            
            with col_tp:
                take_profit = st.slider("Take Profit (%)", 5, 100, 20, 5)
            
            if st.button("🚀 Iniciar Trade", type="primary", use_container_width=True):
                if position_size <= st.session_state.bot.balance:
                    trade = st.session_state.bot.create_trade(
                        symbol=token_data['symbol'],
                        ca=token_ca.strip(),
                        entry_price=token_data['price'],
                        position_size=position_size,
                        stop_loss_percent=stop_loss,
                        take_profit_percent=take_profit
                    )
                    
                    st.success(f"Trade iniciado para {token_data['symbol']}!")
                    st.rerun()
                else:
                    st.error("Saldo insuficiente!")
        else:
            st.error("Token não encontrado. Verifique o CA.")

with col2:
    st.subheader("📋 Informações")
    st.write(f"""
    **Trades Ativos:** {stats['active_trades']}
    **Total de Trades:** {stats['total_trades']}
    **Saldo Disponível:** ${stats['balance']:,.2f}
    """)
    
    st.divider()
    
    st.subheader("📌 Regras do Bot")
    st.write("""
    1. **Take Profit:** Sai automaticamente no alvo
    2. **Stop Loss:** Protege contra perdas grandes
    3. **Trailing Stop:** Protege lucros altos
    4. **Atualização:** A cada 30 segundos
    """)

# ==========================================================
# TRADES ATIVOS
# ==========================================================
if st.session_state.bot.active_trades:
    st.header("📈 Trades Ativos")
    
    # Atualizar preços
    st.session_state.bot.update_prices()
    closed_trades = st.session_state.bot.check_exits()
    
    if closed_trades:
        st.subheader("🔒 Trades Fechados Recentemente")
        for trade in closed_trades[-3:]:
            profit_color = "🟢" if trade['final_profit_percent'] > 0 else "🔴"
            st.write(f"""
            **{trade['symbol']}** - {trade['exit_reason']}
            Entrada: ${trade['entry_price']:.8f} | Saída: ${trade['exit_price']:.8f}
            Resultado: {profit_color} {trade['final_profit_percent']:+.2f}% (${trade['final_profit_value']:+.2f})
            """)
    
    # Mostrar trades ativos
    cols = st.columns(3)
    
    for idx, trade in enumerate(st.session_state.bot.active_trades[:6]):
        with cols[idx % 3]:
            profit = trade['current_profit']
            profit_color = "green" if profit >= 0 else "red"
            
            st.markdown(f"""
            <div style='border: 2px solid {profit_color}; border-radius: 10px; padding: 10px; margin: 5px 0;'>
                <strong>{trade['symbol']}</strong><br>
                <span style='color:{profit_color}; font-size:20px;'>{profit:+.2f}%</span><br>
                <small>Entrada: ${trade['entry_price']:.8f}</small><br>
                <small>Atual: ${trade['current_price']:.8f}</small><br>
                <small>SL: ${trade['stop_loss']:.8f} | TP: ${trade['take_profit']:.8f}</small>
            </div>
            """, unsafe_allow_html=True)
            
            # Botão de saída manual
            if st.button(f"⏹️ Sair {trade['symbol']}", key=f"exit_{trade['id']}", use_container_width=True):
                trade['status'] = 'CLOSED'
                trade['exit_price'] = trade['current_price']
                trade['exit_time'] = datetime.now()
                trade['exit_reason'] = 'MANUAL'
                
                profit_percent = trade['current_profit']
                profit_value = trade['position_size'] * (profit_percent / 100)
                
                trade['final_profit_percent'] = profit_percent
                trade['final_profit_value'] = profit_value
                
                st.session_state.bot.active_trades.remove(trade)
                st.session_state.bot.trade_history.append(trade)
                st.session_state.bot.balance += trade['position_size'] + profit_value
                
                st.success(f"Trade fechado manualmente: {profit_percent:+.2f}%")
                st.rerun()

# ==========================================================
# HISTÓRICO
# ==========================================================
if st.session_state.bot.trade_history:
    st.header("📜 Histórico de Trades")
    
    df_history = pd.DataFrame(st.session_state.bot.trade_history)
    
    # Métricas
    col_h1, col_h2, col_h3 = st.columns(3)
    
    with col_h1:
        total = len(df_history)
        st.metric("Total Trades", total)
    
    with col_h2:
        wins = len(df_history[df_history['final_profit_percent'] > 0])
        win_rate = (wins / total * 100) if total > 0 else 0
        st.metric("Win Rate", f"{win_rate:.1f}%")
    
    with col_h3:
        total_profit = df_history['final_profit_value'].sum()
        st.metric("Lucro Total", f"${total_profit:+,.2f}")
    
    # Tabela simples
    st.dataframe(
        df_history[['symbol', 'entry_price', 'exit_price', 'final_profit_percent', 
                   'final_profit_value', 'exit_reason']].tail(10),
        use_container_width=True,
        column_config={
            'symbol': 'Token',
            'entry_price': 'Entrada',
            'exit_price': 'Saída',
            'final_profit_percent': 'PnL %',
            'final_profit_value': 'PnL $',
            'exit_reason': 'Motivo'
        }
    )

# ==========================================================
# ATUALIZAÇÃO AUTOMÁTICA
# ==========================================================
if st.session_state.bot.active_trades:
    time.sleep(30)  # Atualiza a cada 30 segundos se houver trades ativos
    st.rerun()

# ==========================================================
# RODAPÉ
# ==========================================================
st.divider()
st.caption(f"🔄 Última atualização: {datetime.now().strftime('%H:%M:%S')}")
st.caption("Sniper Pro v1.0 - Bot de Trading Simples")
