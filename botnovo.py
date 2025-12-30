import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import random
import threading
import queue
import warnings

warnings.filterwarnings('ignore')

# ==========================================================
# CONFIGURAÇÃO INICIAL
# ==========================================================
st.set_page_config(
    page_title="🚀 SNIPER AI PRO - AUTO TRADER",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# SISTEMA DE TRADING - MOTOR PRINCIPAL
# ==========================================================
class TradingEngine:
    """Motor de trading que roda em background"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.trade_queue = queue.Queue()
        self.last_scan = datetime.now()
        self.stats = {
            'total_scans': 0,
            'signals_found': 0,
            'trades_executed': 0,
            'last_signal_time': None
        }
        
        self.token_pool = [
            {"ca": "0x2170Ed0880ac9A755fd29B2688956BD959F933F8", "name": "ETH", "type": "MAIN"},
            {"ca": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", "name": "BNB", "type": "MAIN"},
            {"ca": "0x55d398326f99059fF775485246999027B3197955", "name": "USDT", "type": "STABLE"},
            {"ca": "0x8076C74C5e3F5852037F31Ff0093Eeb8c8ADd8D3", "name": "SAFEMOON", "type": "MEME"},
            {"ca": "0x603c7f932ED1fc6575303D8Fb018fDCBb0f39a95", "name": "BANANA", "type": "MEME"},
        ]
        
    def fetch_token_data(self, ca):
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data.get('pairs'):
                    return data['pairs'][0]
        except:
            pass
        return None
    
    def analyze_token(self, token_data, token_type="MAIN"):
        try:
            price = float(token_data.get('priceUsd', 0))
            volume_24h = float(token_data.get('volume', {}).get('h24', 0))
            liquidity = float(token_data.get('liquidity', {}).get('usd', 0))
            price_change = token_data.get('priceChange', {})
            change_5m = float(price_change.get('m5', 0))
            
            score = 0
            if change_5m > 1: score += 40
            if liquidity > 10000: score += 20
            
            if score >= 50:
                return {
                    'symbol': token_data.get('baseToken', {}).get('symbol', 'TOKEN'),
                    'price': price,
                    'score': score,
                    'confidence': "HIGH" if score > 70 else "MEDIUM",
                    'stop_loss': price * 0.95,
                    'take_profit': price * 1.10,
                    'volume': volume_24h,
                    'liquidity': liquidity,
                    'change_5m': change_5m,
                    'timestamp': datetime.now(),
                    'token_type': token_type
                }
        except:
            pass
        return None

    def scan_tokens(self):
        while self.running:
            self.stats['total_scans'] += 1
            for token_info in self.token_pool:
                token_data = self.fetch_token_data(token_info['ca'])
                if token_data:
                    signal = self.analyze_token(token_data, token_info['type'])
                    if signal:
                        self.trade_queue.put(signal)
            time.sleep(5)

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.scan_tokens, daemon=True)
            self.thread.start()

# ==========================================================
# INICIALIZAÇÃO E FUNÇÕES DE TRADING
# ==========================================================

if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.saldo = 10000.0
    st.session_state.trades_ativos = []
    st.session_state.historico_trades = []
    st.session_state.estatisticas = {
        'total_trades': 0, 'trades_ganhos': 0, 'trades_perdidos': 0,
        'lucro_total': 0.0, 'win_rate': 0.0
    }
    st.session_state.engine = TradingEngine()
    st.session_state.engine.start()

def processar_sinais():
    while not st.session_state.engine.trade_queue.empty():
        sinal = st.session_state.engine.trade_queue.get()
        if len(st.session_state.trades_ativos) < 5:
            tamanho = 100.0
            st.session_state.saldo -= tamanho
            sinal['id'] = random.randint(1000, 9999)
            sinal['entry_price'] = sinal['price']
            sinal['current_price'] = sinal['price']
            sinal['position_size'] = tamanho
            sinal['profit_loss'] = 0.0
            st.session_state.trades_ativos.append(sinal)
            st.session_state.estatisticas['total_trades'] += 1

def atualizar_precos():
    for trade in st.session_state.trades_ativos[:]:
        # Simulação de variação realística
        variacao = random.uniform(-0.02, 0.025)
        trade['current_price'] *= (1 + variacao)
        trade['profit_loss'] = (trade['current_price'] - trade['entry_price']) * (trade['position_size'] / trade['entry_price'])
        
        # Lógica de Fechamento
        if trade['current_price'] >= trade['take_profit'] or trade['current_price'] <= trade['stop_loss']:
            st.session_state.saldo += (trade['position_size'] + trade['profit_loss'])
            if trade['profit_loss'] > 0: st.session_state.estatisticas['trades_ganhos'] += 1
            else: st.session_state.estatisticas['trades_perdidos'] += 1
            st.session_state.estatisticas['lucro_total'] += trade['profit_loss']
            st.session_state.historico_trades.append(trade)
            st.session_state.trades_ativos.remove(trade)

def criar_grafico_performance():
    if not st.session_state.historico_trades:
        return None
    df = pd.DataFrame(st.session_state.historico_trades)
    df['cum_profit'] = df['profit_loss'].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=df['cum_profit'], mode='lines+markers', name='Lucro Acumulado', line=dict(color='#00FF00')))
    fig.update_layout(template="plotly_dark", height=300, margin=dict(l=20, r=20, t=20, b=20))
    return fig

# ==========================================================
# INTERFACE STREAMLIT
# ==========================================================

st.title("🚀 SNIPER AI PRO")

# Sidebar - Stats
with st.sidebar:
    st.header("📊 Dashboard")
    st.metric("Saldo", f"${st.session_state.saldo:.2f}")
    st.metric("Lucro Total", f"${st.session_state.estatisticas['lucro_total']:.2f}")
    st.write(f"Trades Ativos: {len(st.session_state.trades_ativos)}")

# Top Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Win Rate", f"{st.session_state.estatisticas['win_rate']:.1f}%")
col2.metric("Ganhos", st.session_state.estatisticas['trades_ganhos'])
col3.metric("Perdas", st.session_state.estatisticas['trades_perdidos'])
col4.metric("Total Trades", st.session_state.estatisticas['total_trades'])

# Gráfico
grafico = criar_grafico_performance()
if grafico:
    st.plotly_chart(grafico, use_container_width=True)

# Listagem de Trades
st.subheader("🎯 Trades em Execução")
if st.session_state.trades_ativos:
    df_ativos = pd.DataFrame(st.session_state.trades_ativos)
    st.dataframe(df_ativos[['symbol', 'entry_price', 'current_price', 'profit_loss']], use_container_width=True)
else:
    st.info("Aguardando sinais do mercado...")

# Loop de Atualização Automática
processar_sinais()
atualizar_precos()
time.sleep(2)
st.rerun()
