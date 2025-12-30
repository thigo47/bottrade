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
        
        # Pool de tokens otimizado (inclui memecoins)
        self.token_pool = [
            # Tokens principais
            {"ca": "0x2170Ed0880ac9A755fd29B2688956BD959F933F8", "name": "ETH", "type": "MAIN"},
            {"ca": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", "name": "BNB", "type": "MAIN"},
            {"ca": "0x55d398326f99059fF775485246999027B3197955", "name": "USDT", "type": "STABLE"},
            {"ca": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82", "name": "CAKE", "type": "DEFI"},
            
            # Altcoins
            {"ca": "0x1CE0c2827e2eF14D5C4f29a091d735A204794041", "name": "AVAX", "type": "ALT"},
            {"ca": "0xCC42724C6683B7E57334c4E856f4c9965ED682bD", "name": "MATIC", "type": "ALT"},
            {"ca": "0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE", "name": "XRP", "type": "ALT"},
            
            # Memecoins (alta volatilidade)
            {"ca": "0x8076C74C5e3F5852037F31Ff0093Eeb8c8ADd8D3", "name": "SAFEMOON", "type": "MEME"},
            {"ca": "0x1Ba42e5193dfA8B03D15dd1B86a3113bbBEF8Eeb", "name": "ZOON", "type": "MEME"},
            {"ca": "0x603c7f932ED1fc6575303D8Fb018fDCBb0f39a95", "name": "BANANA", "type": "MEME"},
            {"ca": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", "name": "BNB", "type": "MAIN"},  # BNB para referência
            {"ca": "0x55d398326f99059fF775485246999027B3197955", "name": "USDT", "type": "STABLE"},  # USDT para referência
        ]
        
    def fetch_token_data(self, ca):
        """Busca dados do token com cache"""
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
        """Análise rápida e eficiente com ajustes por tipo"""
        try:
            price = float(token_data.get('priceUsd', 0))
            volume_24h = float(token_data.get('volume', {}).get('h24', 0))
            liquidity = float(token_data.get('liquidity', {}).get('usd', 0))
            
            # Dados de momentum
            price_change = token_data.get('priceChange', {})
            change_5m = float(price_change.get('m5', 0))
            change_1h = float(price_change.get('h1', 0))
            
            # Score de oportunidade
            score = 0
            
            # AJUSTES POR TIPO DE TOKEN
            volume_multiplier = 1.0
            score_multiplier = 1.0
            
            if token_type == "MEME":
                # Memecoins: menor volume necessário, maior tolerância
                volume_multiplier = 0.5
                score_multiplier = 1.2  # Bônus para memecoins
                min_volume = 5000  # $5k volume mínimo
            elif token_type == "ALT":
                volume_multiplier = 0.8
                score_multiplier = 1.1
                min_volume = 10000  # $10k volume mínimo
            else:  # MAIN ou DEFI
                volume_multiplier = 1.0
                score_multiplier = 1.0
                min_volume = 20000  # $20k volume mínimo
            
            # Critério 1: Volume suficiente (ajustado por tipo)
            adjusted_volume = volume_24h * volume_multiplier
            
            if adjusted_volume > min_volume * 3:
                score += 30
            elif adjusted_volume > min_volume * 2:
                score += 20
            elif adjusted_volume > min_volume:
                score += 10
            else:
                return None  # Volume muito baixo
            
            # Critério 2: Momentum positivo
            if change_5m > 3:  # +3% em 5min
                score += 40
                if change_1h > 2:
                    score += 25
            elif change_5m > 1:
                score += 20
            elif change_5m < -5:  # Queda forte
                score -= 15  # Penalidade
            
            # Critério 3: Liquidez
            if liquidity > 50000:
                score += 15
            elif liquidity > 10000:
                score += 5
            
            # Critério 4: Preço adequado
            if token_type == "MEME":
                # Memecoins: preços muito baixos são normais
                if 0.00000001 < price < 0.0001:
                    score += 25
                elif price < 0.001:
                    score += 15
            else:
                if 0.0001 < price < 0.01:
                    score += 20
                elif price < 0.1:
                    score += 10
            
            # Aplicar multiplicador por tipo
            score = int(score * score_multiplier)
            
            # Se score for alto o suficiente, criar sinal
            min_score = 55 if token_type == "MEME" else 60
            
            if score >= min_score:
                symbol = token_data.get('baseToken', {}).get('symbol', 'TOKEN')
                
                # Definir stop loss e take profit dinâmicos
                if token_type == "MEME":
                    # Memecoins: stops mais apertados
                    if score >= 80:
                        stop_loss = 0.95  # -5%
                        take_profit = 1.06  # +6%
                        confidence = "HIGH"
                    elif score >= 65:
                        stop_loss = 0.96  # -4%
                        take_profit = 1.05  # +5%
                        confidence = "MEDIUM"
                    else:
                        stop_loss = 0.97  # -3%
                        take_profit = 1.04  # +4%
                        confidence = "LOW"
                else:
                    if score >= 80:
                        stop_loss = 0.97  # -3%
                        take_profit = 1.04  # +4%
                        confidence = "HIGH"
                    elif score >= 70:
                        stop_loss = 0.98  # -2%
                        take_profit = 1.03  # +3%
                        confidence = "MEDIUM"
                    else:
                        stop_loss = 0.99  # -1%
                        take_profit = 1.02  # +2%
                        confidence = "LOW"
                
                return {
                    'symbol': symbol,
                    'price': price,
                    'score': score,
                    'confidence': confidence,
                    'stop_loss': price * stop_loss,
                    'take_profit': price * take_profit,
                    'volume': volume_24h,
                    'liquidity': liquidity,
                    'change_5m': change_5m,
                    'change_1h': change_1h,
                    'timestamp': datetime.now(),
                    'token_type': token_type
                }
                
        except Exception as e:
            print(f"Erro na análise: {e}")
        
        return None
    
    def add_custom_token(self, ca, name="CUSTOM", token_type="CUSTOM"):
        """Adiciona um token personalizado à pool"""
        new_token = {"ca": ca.strip(), "name": name, "type": token_type}
        
        # Verificar se já existe
        if not any(t['ca'] == ca.strip() for t in self.token_pool):
            self.token_pool.append(new_token)
            return True
        return False
    
    def remove_token(self, ca):
        """Remove um token da pool"""
        self.token_pool = [t for t in self.token_pool if t['ca'] != ca]
    
    def scan_tokens(self):
        """Escaneia tokens em busca de oportunidades"""
        while self.running:
            try:
                current_time = datetime.now()
                
                # Intervalo entre scans (ajustável)
                if (current_time - self.last_scan).total_seconds() < 2:
                    time.sleep(0.1)
                    continue
                
                self.stats['total_scans'] += 1
                
                # Selecionar tokens aleatoriamente (inclui mais memecoins)
                tokens_to_scan = random.sample(
                    self.token_pool, 
                    min(4, len(self.token_pool))
                )
                
                for token_info in tokens_to_scan:
                    # Buscar dados
                    token_data = self.fetch_token_data(token_info['ca'])
                    
                    if token_data:
                        # Analisar com tipo específico
                        signal = self.analyze_token(token_data, token_info['type'])
                        
                        if signal:
                            self.stats['signals_found'] += 1
                            self.stats['last_signal_time'] = current_time
                            
                            # Adicionar à fila
                            self.trade_queue.put({
                                'type': 'TRADE_SIGNAL',
                                'data': signal,
                                'token_ca': token_info['ca'],
                                'token_name': token_info['name'],
                                'token_type': token_info['type']
                            })
                
                self.last_scan = current_time
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Erro no scanner: {e}")
                time.sleep(1)
    
    def start(self):
        """Inicia o motor de trading"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.scan_tokens, daemon=True)
            self.thread.start()
            print("🚀 Motor de trading INICIADO")
    
    def stop(self):
        """Para o motor de trading"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("🛑 Motor de trading PARADO")
    
    def get_stats(self):
        """Retorna estatísticas atuais"""
        return self.stats.copy()
    
    def get_token_pool_info(self):
        """Retorna informações sobre a pool de tokens"""
        types_count = {}
        for token in self.token_pool:
            ttype = token.get('type', 'UNKNOWN')
            types_count[ttype] = types_count.get(ttype, 0) + 1
        
        return {
            'total_tokens': len(self.token_pool),
            'types_distribution': types_count,
            'token_list': self.token_pool[:10]  # Primeiros 10
        }

# ==========================================================
# INICIALIZAÇÃO DO SISTEMA
# ==========================================================

# Inicializar session_state
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.saldo = 10000.0
    st.session_state.trades_ativos = []
    st.session_state.historico_trades = []
    st.session_state.estatisticas = {
        'total_trades': 0,
        'trades_ganhos': 0,
        'trades_perdidos': 0,
        'lucro_total': 0.0,
        'lucro_dia': 0.0,
        'win_rate': 0.0,
        'roi_total': 0.0,
        'melhor_trade': 0.0,
        'pior_trade': 0.0,
        'trades_hoje': 0
    }
    st.session_state.config = {
        'auto_trading': True,
        'max_trades_ativos': 10,
        'tamanho_trade_percent': 2.0,
        'stop_loss_padrao': 2.0,
        'take_profit_padrao': 3.0,
        'frequencia_scan': 2.0,
        'memecoin_aggressive': True  # Modo agressivo para memecoins
    }
    st.session_state.trading_engine = TradingEngine()
    st.session_state.trading_engine.start()
    st.session_state.ultima_atualizacao = datetime.now()
    st.session_state.custom_tokens = []  # Tokens personalizados adicionados

# ==========================================================
# FUNÇÕES DE TRADING
# ==========================================================

def executar_trade(sinal):
    """Executa um trade baseado no sinal"""
    try:
        # Ajustar tamanho do trade baseado no tipo
        base_percent = st.session_state.config['tamanho_trade_percent']
        
        if sinal.get('token_type') == "MEME":
            # Memecoins: trade menor (mais arriscado)
            trade_percent = base_percent * 0.7  # 70% do tamanho normal
        elif sinal.get('token_type') == "ALT":
            trade_percent = base_percent * 0.9  # 90% do tamanho normal
        else:
            trade_percent = base_percent  # 100% para tokens principais
        
        tamanho_trade = st.session_state.saldo * (trade_percent / 100)
        tamanho_trade = min(tamanho_trade, 100)  # Máximo $100 por trade
        
        if tamanho_trade < 0.50 or tamanho_trade > st.session_state.saldo * 0.9:
            return None
        
        # Criar objeto do trade
        trade_id = len(st.session_state.historico_trades) + len(st.session_state.trades_ativos) + 1
        
        trade = {
            'id': trade_id,
            'symbol': sinal['symbol'],
            'entry_price': sinal['price'],
            'current_price': sinal['price'],
            'position_size': tamanho_trade,
            'stop_loss': sinal['stop_loss'],
            'take_profit': sinal['take_profit'],
            'entry_time': datetime.now(),
            'status': 'ACTIVE',
            'score': sinal['score'],
            'confidence': sinal['confidence'],
            'profit_loss': 0.0,
            'profit_loss_percent': 0.0,
            'token_type': sinal.get('token_type', 'UNKNOWN'),
            'volume': sinal.get('volume', 0),
            'change_5m': sinal.get('change_5m', 0)
        }
        
        # Atualizar saldo
        st.session_state.saldo -= tamanho_trade
        
        # Adicionar à lista de trades ativos
        st.session_state.trades_ativos.append(trade)
        
        # Atualizar estatísticas
        st.session_state.estatisticas['total_trades'] += 1
        st.session_state.estatisticas['trades_hoje'] += 1
        
        # Log
        print(f"✅ Trade executado: {trade['symbol']} | Tipo: {trade['token_type']} | Score: {trade['score']}")
        
        return trade
        
    except Exception as e:
        print(f"Erro ao executar trade: {e}")
        return None

def atualizar_trades():
    """Atualiza todos os trades ativos"""
    trades_fechados = []
    
    for trade in st.session_state.trades_ativos[:]:
        try:
            # Simular variação de preço baseada no tipo
            if trade.get('token_type') == "MEME":
                # Memecoins: mais voláteis
                variation = random.uniform(-0.05, 0.08)  # -5% a +8%
            elif trade.get('token_type') == "ALT":
                variation = random.uniform(-0.03, 0.05)  # -3% a +5%
            else:
                variation = random.uniform(-0.02, 0.04)  # -2% a +4%
            
            current_price = trade['entry_price'] * (1 + variation)
            trade['current_price'] = current_price
            
            # Calcular P&L
            profit_loss = (current_price - trade['entry_price']) / trade['entry_price'] * 100
            profit_loss_value = trade['position_size'] * (profit_loss / 100)
            
            trade['profit_loss'] = profit_loss_value
            trade['profit_loss_percent'] = profit_loss
            
            # Verificar condições de saída
            if current_price >= trade['take_profit']:
                # TAKE PROFIT atingido
                fechar_trade(trade, 'TAKE_PROFIT', trades_fechados)
                
            elif current_price <= trade['stop_loss']:
                # STOP LOSS atingido
                fechar_trade(trade, 'STOP_LOSS', trades_fechados)
                
        except Exception as e:
            print(f"Erro ao atualizar trade: {e}")
            continue
    
    return trades_fechados

def fechar_trade(trade, motivo, trades_fechados):
    """Fecha um trade e atualiza estatísticas"""
    try:
        trade['exit_time'] = datetime.now()
        trade['exit_price'] = trade['current_price']
        trade['status'] = 'CLOSED'
        trade['exit_reason'] = motivo
        
        # Retornar fundos + lucro/prejuízo
        retorno = trade['position_size'] + trade['profit_loss']
        st.session_state.saldo += retorno
        
        # Atualizar estatísticas
        stats = st.session_state.estatisticas
        
        if trade['profit_loss'] > 0:
            stats['trades_ganhos'] += 1
            stats['melhor_trade'] = max(stats['melhor_trade'], trade['profit_loss'])
        else:
            stats['trades_perdidos'] += 1
            stats['pior_trade'] = min(stats['pior_trade'], trade['profit_loss'])
        
        stats['lucro_total'] += trade['profit_loss']
        stats['lucro_dia'] += trade['profit_loss']
        
        # Calcular win rate
        if stats['total_trades'] > 0:
            stats['win_rate'] = (stats['trades_ganhos'] / stats['total_trades']) * 100
        
        # Calcular ROI
        if st.session_state.saldo > 0:
            stats['roi_total'] = ((st.session_state.saldo - 10000) / 10000) * 100
        
        # Mover para histórico
        st.session_state.historico_trades.append(trade.copy())
        st.session_state.trades_ativos.remove(trade)
        trades_fechados.append(trade)
        
        # Log
        print(f"📊 Trade fechado: {trade['symbol']} | Motivo: {motivo} | P&L: ${trade['profit_loss']:.2f}")
        
    except Exception as e:
        print(f"Erro ao fechar trade: {e}")

# ==========================================================
# FUNÇÕES DE GRÁFICO CORRIGIDAS (SEM SCIPY)
# ==========================================================

def criar_grafico_performance():
    """Cria gráfico de performance sem dependências externas"""
    if not st.session_state.historico_trades:
        return None
    
    # Preparar dados
    trades = st.session_state.historico_trades[-20:]  # Últimos 20 trades
    if not trades:
        return None
    
    # Criar DataFrame
    df = pd.DataFrame(trades)
    df['cumulative_profit'] = df['profit_loss'].cumsum()
    
    # Criar gráfico
    fig = go.Figure()
    
    # Linha de lucro acumulado
    fig.add_trace(go.Scatter(
        x=list(range(len(df))),
        y=df['cumulative_profit'],
        mode='lines+markers',
        name='Lucro Acumulado',
        line=dict(color='#00FF00', width=3),
        marker=dict(size=8)
    ))
    
    # Adicionar trades positivos e negativos
    positive_trades = df[df['profit_loss'] > 0]
    negative_trades = df[df['profit_loss'] <= 0]
    
    if len(positive_trades) > 0:
    fig.add_trace(go.Scatter(
        x=positive_trades.index,
        y=positive_trades['cumulative_profit'],
        mode='markers',
        name='Trades Positivos',
        marker=dict(color='#00FF00', size=10) # Fechamento do dict e definição do tamanho
    )) # Fechamento do go.Scatter e do add_trace
