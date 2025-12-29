import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import random
import threading
from collections import deque

# ==========================================================
# CONFIGURAÇÃO DO STREAMLIT (DEVE SER O PRIMEIRO)
# ==========================================================
st.set_page_config(
    page_title="⚡ SNIPER AI ULTRA - HIGH FREQUENCY",
    page_icon="⚡",
    layout="wide"
)

# ==========================================================
# FUNÇÕES DE ANÁLISE TÉCNICA SIMPLIFICADAS
# (Para substituir a biblioteca 'ta')
# ==========================================================

def calculate_rsi(prices, period=14):
    """Calcula RSI (Relative Strength Index) simplificado"""
    if len(prices) < period + 1:
        return 50
    
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    
    if down == 0:
        return 100
    
    rs = up / down
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_sma(prices, period=20):
    """Calcula Simple Moving Average"""
    if len(prices) < period:
        return prices[-1] if len(prices) > 0 else 0
    
    return np.mean(prices[-period:])

def calculate_ema(prices, period=12):
    """Calcula Exponential Moving Average"""
    if len(prices) < period:
        return prices[-1] if len(prices) > 0 else 0
    
    weights = np.exp(np.linspace(-1., 0., period))
    weights /= weights.sum()
    
    return np.convolve(prices[-period*2:], weights, mode='valid')[-1]

def calculate_macd(prices):
    """Calcula MACD simplificado"""
    if len(prices) < 26:
        return 0, 0, 0
    
    ema12 = calculate_ema(prices, 12)
    ema26 = calculate_ema(prices, 26)
    
    macd_line = ema12 - ema26
    signal_line = calculate_ema([macd_line], 9) if 'macd_line' in locals() else 0
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(prices, period=20):
    """Calcula Bollinger Bands"""
    if len(prices) < period:
        sma = prices[-1] if len(prices) > 0 else 0
        return sma, sma, sma
    
    sma = np.mean(prices[-period:])
    std = np.std(prices[-period:])
    
    upper_band = sma + (std * 2)
    lower_band = sma - (std * 2)
    
    return upper_band, sma, lower_band

# ==========================================================
# CLASSES DO SISTEMA
# ==========================================================

class TradingML:
    """Sistema de aprendizado simplificado para ajustar estratégias"""
    
    def __init__(self):
        self.patterns = {}
        self.success_rate = {}
        self.adaptation_factors = {
            'aggressive': 1.0,
            'moderate': 1.0,
            'conservative': 1.0
        }
        
    def analyze_pattern(self, trade_data):
        """Analisa padrões nos trades para ajustar estratégias"""
        try:
            symbol = trade_data.get('symbol')
            strategy = trade_data.get('strategy', 'moderate')
            profit = trade_data.get('profit_percent', 0)
            
            # Registrar padrão
            key = f"{symbol}_{strategy}"
            if key not in self.patterns:
                self.patterns[key] = []
            
            self.patterns[key].append({
                'profit': profit,
                'timestamp': datetime.now(),
                'score': trade_data.get('score', 0)
            })
            
            # Manter apenas últimos 50 registros
            if len(self.patterns[key]) > 50:
                self.patterns[key] = self.patterns[key][-50:]
            
            # Calcular taxa de sucesso
            if len(self.patterns[key]) >= 10:
                recent_trades = self.patterns[key][-10:]
                winning_trades = [t for t in recent_trades if t['profit'] > 0]
                success_rate = len(winning_trades) / len(recent_trades)
                self.success_rate[key] = success_rate
                
                # Ajustar fatores de adaptação
                if success_rate < 0.3:
                    self.adaptation_factors[strategy] = max(0.5, self.adaptation_factors[strategy] * 0.9)
                elif success_rate > 0.6:
                    self.adaptation_factors[strategy] = min(1.5, self.adaptation_factors[strategy] * 1.1)
            
            return self.adaptation_factors[strategy]
            
        except:
            return 1.0
    
    def get_recommendation(self, symbol, strategy):
        """Obtém recomendação baseada em histórico"""
        key = f"{symbol}_{strategy}"
        if key in self.success_rate:
            if self.success_rate[key] > 0.5:
                return "BUY_STRONG"
            elif self.success_rate[key] > 0.3:
                return "BUY_WEAK"
            else:
                return "AVOID"
        return "NEUTRAL"

class DynamicRiskManager:
    """Gerenciador de risco dinâmico baseado em volatilidade"""
    
    def __init__(self):
        self.volatility_history = {}
        self.risk_level = "MEDIUM"
        self.max_position_size = 5.0
        
    def calculate_volatility(self, token_data):
        """Calcula volatilidade baseado em múltiplos timeframes"""
        try:
            pair = token_data['pairs'][0]
            price_change = pair.get('priceChange', {})
            
            changes = [
                abs(float(price_change.get('m5', 0))),
                abs(float(price_change.get('h1', 0))),
                abs(float(price_change.get('h6', 0))),
                abs(float(price_change.get('h24', 0)))
            ]
            
            # Remover valores nulos
            changes = [c for c in changes if c > 0]
            
            if changes:
                volatility = sum(changes) / len(changes)
                
                # Classificar volatilidade
                if volatility > 10:
                    return "EXTREME", volatility
                elif volatility > 5:
                    return "HIGH", volatility
                elif volatility > 2:
                    return "MEDIUM", volatility
                else:
                    return "LOW", volatility
            
            return "LOW", 0
            
        except:
            return "LOW", 0
    
    def adjust_position_size(self, volatility_level, current_win_rate):
        """Ajusta o tamanho da posição baseado em volatilidade e win rate"""
        base_size = 2.0
        
        if volatility_level == "EXTREME":
            base_size *= 0.5
        elif volatility_level == "HIGH":
            base_size *= 0.7
        elif volatility_level == "LOW":
            base_size *= 1.2
        
        if current_win_rate < 0.3:
            base_size *= 0.6
        elif current_win_rate > 0.6:
            base_size *= 1.3
        
        base_size = max(0.5, min(base_size, self.max_position_size))
        return base_size

class RealTimeBacktester:
    """Backtesting em tempo real para validação de estratégias"""
    
    def __init__(self):
        self.strategy_results = {}
        self.performance_metrics = {}
        
    def add_trade_result(self, strategy, trade_result):
        """Adiciona resultado de trade para análise"""
        if strategy not in self.strategy_results:
            self.strategy_results[strategy] = []
        
        self.strategy_results[strategy].append(trade_result)
        
        if len(self.strategy_results[strategy]) > 100:
            self.strategy_results[strategy] = self.strategy_results[strategy][-100:]
    
    def analyze_strategy_performance(self, strategy):
        """Analisa performance de uma estratégia específica"""
        if strategy not in self.strategy_results:
            return None
        
        trades = self.strategy_results[strategy]
        if not trades:
            return None
        
        winning_trades = [t for t in trades if t['profit'] > 0]
        losing_trades = [t for t in trades if t['profit'] <= 0]
        
        total_trades = len(trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        avg_win = np.mean([t['profit'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['profit'] for t in losing_trades]) if losing_trades else 0
        
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': self.calculate_sharpe_ratio(trades)
        }
    
    def calculate_sharpe_ratio(self, trades):
        """Calcula Sharpe Ratio simplificado"""
        if len(trades) < 2:
            return 0
        
        returns = [t['profit'] for t in trades]
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0
        
        return avg_return / std_return

# ==========================================================
# INICIALIZAÇÃO DO SESSION_STATE
# ==========================================================
if 'saldo' not in st.session_state:
    st.session_state.saldo = 1000.0

if 'trades' not in st.session_state:
    st.session_state.trades = []

if 'historico' not in st.session_state:
    st.session_state.historico = []

if 'ultimo_trade' not in st.session_state:
    st.session_state.ultimo_trade = datetime.now()

if 'monitorando' not in st.session_state:
    st.session_state.monitorando = []

if 'auto_mode' not in st.session_state:
    st.session_state.auto_mode = True

if 'estatisticas' not in st.session_state:
    st.session_state.estatisticas = {
        'total_trades': 0,
        'ganhos': 0,
        'perdas': 0,
        'lucro_total': 0.0,
        'lucro_dia': 0.0,
        'trades_dia': 0,
        'max_consecutive_wins': 0,
        'max_consecutive_losses': 0,
        'current_streak': 0,
        'last_win': False
    }

if 'precos_historicos' not in st.session_state:
    st.session_state.precos_historicos = {}

if 'cache_tokens' not in st.session_state:
    st.session_state.cache_tokens = {}

if 'trading_ml' not in st.session_state:
    st.session_state.trading_ml = TradingML()

if 'risk_manager' not in st.session_state:
    st.session_state.risk_manager = DynamicRiskManager()

if 'backtester' not in st.session_state:
    st.session_state.backtester = RealTimeBacktester()

if 'bot_thread' not in st.session_state:
    st.session_state.bot_thread = None

if 'last_sentiment_check' not in st.session_state:
    st.session_state.last_sentiment_check = datetime.now()

# ==========================================================
# FUNÇÕES DO SISTEMA
# ==========================================================

def buscar_token(ca, use_cache=True):
    """Busca dados do token com cache"""
    try:
        if use_cache and ca in st.session_state.cache_tokens:
            cache_time, data = st.session_state.cache_tokens[ca]
            if (datetime.now() - cache_time).seconds < 5:
                return data
        
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get('pairs'):
                data['ca'] = ca
                st.session_state.cache_tokens[ca] = (datetime.now(), data)
                return data
    except:
        pass
    return None

def analyze_market_sentiment():
    """Analisa o sentimento geral do mercado"""
    try:
        sentiment_tokens = [
            "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",  # ETH
            "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # BNB
            "0x55d398326f99059fF775485246999027B3197955",  # USDT
            "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",  # CAKE
        ]
        
        bullish_count = 0
        total_tokens = 0
        
        for ca in sentiment_tokens:
            data = buscar_token(ca, use_cache=True)
            if data and data.get('pairs'):
                pair = data['pairs'][0]
                change_5m = float(pair.get('priceChange', {}).get('m5', 0))
                change_1h = float(pair.get('priceChange', {}).get('h1', 0))
                
                if change_5m > 0 and change_1h > 0:
                    bullish_count += 1
                total_tokens += 1
        
        if total_tokens > 0:
            sentiment_score = (bullish_count / total_tokens) * 100
            
            if sentiment_score >= 75:
                return "STRONGLY_BULLISH", sentiment_score
            elif sentiment_score >= 50:
                return "BULLISH", sentiment_score
            elif sentiment_score >= 25:
                return "BEARISH", sentiment_score
            else:
                return "STRONGLY_BEARISH", sentiment_score
        
        return "NEUTRAL", 50
        
    except:
        return "NEUTRAL", 50

def analise_avancada(token_data):
    """Análise avançada com múltiplos indicadores"""
    try:
        pair = token_data['pairs'][0]
        
        symbol = pair.get('baseToken', {}).get('symbol', 'TOKEN')
        price = float(pair.get('priceUsd', 0))
        volume_24h = float(pair.get('volume', {}).get('h24', 0))
        liquidity = float(pair.get('liquidity', {}).get('usd', 0))
        
        price_change = pair.get('priceChange', {})
        change_5m = float(price_change.get('m5', 0))
        change_1h = float(price_change.get('h1', 0))
        change_24h = float(price_change.get('h24', 0))
        
        score = 0
        
        # 1. ANÁLISE DE VOLUME
        if volume_24h > 1000000:
            score += 35
        elif volume_24h > 500000:
            score += 25
        elif volume_24h > 100000:
            score += 15
        elif volume_24h > 50000:
            score += 10
        elif volume_24h > 10000:
            score += 5
        
        # 2. ANÁLISE DE MOMENTUM
        if change_5m > 10 and change_1h > 5:
            score += 30
        elif change_5m > 5 and change_1h > 2:
            score += 20
        elif change_5m > 2:
            score += 10
        elif change_5m < -10 and change_1h < -5:
            score -= 15
        elif change_5m < -5:
            score -= 10
        
        # 3. ANÁLISE DE LIQUIDEZ
        if liquidity > 1000000:
            score += 20
        elif liquidity > 500000:
            score += 15
        elif liquidity > 100000:
            score += 10
        elif liquidity > 50000:
            score += 5
        
        # 4. ANÁLISE DE PREÇO RELATIVO
        if 0.00001 < price < 0.001:
            score += 15
        elif 0.001 <= price < 0.01:
            score += 10
        elif price >= 0.01:
            score += 5
        
        # 5. ANÁLISE DE TENDÊNCIA
        if change_5m > 0 and change_1h > 0 and change_24h > 0:
            score += 20
        elif change_5m > 0 and change_1h > 0:
            score += 15
        elif change_5m > 0:
            score += 10
        
        # 6. ANÁLISE DE RISCO
        risk_adjustment = 0
        if volume_24h / liquidity > 10:
            risk_adjustment += 10
        if abs(change_5m) > 20:
            risk_adjustment += 5
        
        score -= risk_adjustment
        
        # DECISÃO
        if score >= 70:
            stop_loss_pct = 1.5
            take_profit_pct = 4.0
            decisao = 'COMPRAR_AGGRESSIVE'
        elif score >= 50:
            stop_loss_pct = 2.0
            take_profit_pct = 3.0
            decisao = 'COMPRAR_MODERATE'
        elif score >= 30:
            stop_loss_pct = 1.0
            take_profit_pct = 2.0
            decisao = 'COMPRAR_CONSERVATIVE'
        else:
            decisao = 'IGNORAR'
        
        if decisao.startswith('COMPRAR'):
            return {
                'decisao': decisao,
                'symbol': symbol,
                'price': price,
                'stop_loss': price * (1 - stop_loss_pct/100),
                'take_profit': price * (1 + take_profit_pct/100),
                'score': score,
                'volume': volume_24h,
                'liquidity': liquidity,
                'change_5m': change_5m,
                'change_1h': change_1h
            }
        else:
            return {'decisao': 'IGNORAR', 'symbol': symbol, 'score': score}
        
    except Exception as e:
        return {'decisao': 'ERRO', 'erro': str(e)}

def analise_avancada_ml(token_data):
    """Análise avançada com sistema de ML integrado"""
    try:
        analise_basica = analise_avancada(token_data)
        
        if analise_basica['decisao'] == 'IGNORAR' or analise_basica['decisao'] == 'ERRO':
            return analise_basica
        
        symbol = analise_basica['symbol']
        strategy = analise_basica['decisao'].split('_')[-1].lower()
        
        ml_recommendation = st.session_state.trading_ml.get_recommendation(symbol, strategy)
        
        if ml_recommendation == "AVOID":
            return {'decisao': 'IGNORAR', 'symbol': symbol, 'reason': 'ML_AVOID'}
        elif ml_recommendation == "BUY_WEAK":
            if strategy == 'aggressive':
                analise_basica['decisao'] = 'COMPRAR_MODERATE'
                analise_basica['take_profit'] = analise_basica['price'] * 1.03
                analise_basica['stop_loss'] = analise_basica['price'] * 0.98
            elif strategy == 'moderate':
                analise_basica['decisao'] = 'COMPRAR_CONSERVATIVE'
                analise_basica['take_profit'] = analise_basica['price'] * 1.02
                analise_basica['stop_loss'] = analise_basica['price'] * 0.99
        
        volatility_level, volatility_value = st.session_state.risk_manager.calculate_volatility(token_data)
        analise_basica['volatility'] = volatility_level
        analise_basica['volatility_value'] = volatility_value
        
        if volatility_level == "EXTREME":
            analise_basica['stop_loss'] = analise_basica['price'] * 0.97
            analise_basica['score'] *= 0.8
        
        return analise_basica
        
    except Exception as e:
        return {'decisao': 'ERRO', 'erro': str(e)}

def criar_micro_trade_inteligente(token_data, analise):
    """Cria micro trade com gerenciamento inteligente de risco"""
    try:
        stats = st.session_state.estatisticas
        if stats['ganhos'] + stats['perdas'] > 0:
            current_win_rate = stats['ganhos'] / (stats['ganhos'] + stats['perdas'])
        else:
            current_win_rate = 0.5
        
        if analise['decisao'] == 'COMPRAR_AGGRESSIVE':
            base_percent = 3.0
            multiplier = 1.5
        elif analise['decisao'] == 'COMPRAR_MODERATE':
            base_percent = 2.0
            multiplier = 1.2
        else:
            base_percent = 1.0
            multiplier = 1.0
        
        if stats['ganhos'] > 0 and stats['perdas'] > 0:
            win_rate = stats['ganhos'] / (stats['ganhos'] + stats['perdas'])
            if win_rate < 0.3:
                base_percent *= 0.7
            elif win_rate > 0.6:
                base_percent *= 1.3
        
        if stats['current_streak'] > 0:
            base_percent *= (1 + min(stats['current_streak'] * 0.1, 0.5))
        elif stats['current_streak'] < 0:
            base_percent *= max(0.5, 1 + stats['current_streak'] * 0.1)
        
        percentual = min(base_percent * multiplier, 5.0)
        percentual = max(0.5, percentual)
        
        valor_trade = st.session_state.saldo * (percentual / 100)
        valor_trade = max(0.50, min(valor_trade, 100))
        
        if valor_trade > st.session_state.saldo * 0.9:
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
            'profit_value': 0.0,
            'percentual_usado': percentual,
            'tipo': 'HIGH_FREQ',
            'score': analise.get('score', 0),
            'strategy': analise['decisao'].split('_')[-1].lower(),
            'trailing_stop': analise['price'] * 0.995,
            'highest_price': analise['price']
        }
        
        st.session_state.saldo -= valor_trade
        st.session_state.trades.append(trade)
        st.session_state.ultimo_trade = datetime.now()
        st.session_state.estatisticas['total_trades'] += 1
        st.session_state.estatisticas['trades_dia'] += 1
        
        return trade
        
    except Exception as e:
        return None

def criar_micro_trade_ml(token_data, analise):
    """Cria micro trade com todos os sistemas integrados"""
    try:
        stats = st.session_state.estatisticas
        if stats['ganhos'] + stats['perdas'] > 0:
            current_win_rate = stats['ganhos'] / (stats['ganhos'] + stats['perdas'])
        else:
            current_win_rate = 0.5
        
        volatility_level = analise.get('volatility', 'MEDIUM')
        position_size_percent = st.session_state.risk_manager.adjust_position_size(
            volatility_level, current_win_rate
        )
        
        sentiment, sentiment_score = analyze_market_sentiment()
        if sentiment == "STRONGLY_BULLISH":
            position_size_percent *= 1.2
        elif sentiment == "STRONGLY_BEARISH":
            position_size_percent *= 0.8
        
        position_size_percent = max(0.5, min(position_size_percent, 5.0))
        
        valor_trade = st.session_state.saldo * (position_size_percent / 100)
        valor_trade = max(0.50, min(valor_trade, 100))
        
        if valor_trade > st.session_state.saldo * 0.9:
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
            'profit_value': 0.0,
            'percentual_usado': position_size_percent,
            'tipo': 'ML_OPTIMIZED',
            'score': analise.get('score', 0),
            'strategy': analise['decisao'].split('_')[-1].lower(),
            'trailing_stop': analise['price'] * 0.995,
            'highest_price': analise['price'],
            'volatility': analise.get('volatility', 'MEDIUM'),
            'sentiment': sentiment,
            'ml_score': analise.get('score', 0)
        }
        
        st.session_state.saldo -= valor_trade
        st.session_state.trades.append(trade)
        st.session_state.ultimo_trade = datetime.now()
        st.session_state.estatisticas['total_trades'] += 1
        st.session_state.estatisticas['trades_dia'] += 1
        
        st.session_state.backtester.add_trade_result(trade['strategy'], {
            'profit': 0,
            'score': trade['score'],
            'timestamp': datetime.now()
        })
        
        return trade
        
    except Exception as e:
        return None

def atualizar_trades_avancado():
    """Atualiza trades com estratégias avançadas"""
    fechados = []
    
    for trade in st.session_state.trades[:]:
        try:
            data = buscar_token(trade['ca'], use_cache=True)
            if data and data.get('pairs'):
                current_price = float(data['pairs'][0].get('priceUsd', 0))
                trade['current_price'] = current_price
                
                if current_price > trade['highest_price']:
                    trade['highest_price'] = current_price
                    trade['trailing_stop'] = current_price * 0.995
                
                profit_percent = ((current_price - trade['entry_price']) / trade['entry_price']) * 100
                profit_value = trade['position_size'] * (profit_percent / 100)
                
                trade['profit_percent'] = profit_percent
                trade['profit_value'] = profit_value
                
                exit_reason = None
                
                if current_price >= trade['take_profit']:
                    exit_reason = 'TP_HIT'
                elif current_price <= trade['stop_loss']:
                    exit_reason = 'SL_HIT'
                elif current_price <= trade['trailing_stop']:
                    exit_reason = 'TRAILING_STOP'
                
                tempo_trade = (datetime.now() - trade['entry_time']).seconds
                if tempo_trade > 300:
                    if profit_percent > 0.5:
                        exit_reason = 'TIMEOUT_PROFIT'
                    elif tempo_trade > 600:
                        exit_reason = 'TIMEOUT_LOSS'
                
                if exit_reason:
                    trade['exit_reason'] = exit_reason
                    fechar_trade_avancado(trade, fechados)
                    
        except:
            continue
    
    return fechados

def fechar_trade_avancado(trade, fechados):
    """Fecha trade com atualização de estatísticas avançadas"""
    trade['status'] = 'CLOSED'
    trade['exit_time'] = datetime.now()
    trade['exit_price'] = trade['current_price']
    
    profit = trade['profit_value']
    
    st.session_state.saldo += trade['position_size'] + profit
    
    stats = st.session_state.estatisticas
    
    if profit > 0:
        stats['ganhos'] += 1
        stats['lucro_total'] += profit
        stats['lucro_dia'] += profit
        
        if stats['last_win']:
            stats['current_streak'] += 1
        else:
            stats['current_streak'] = 1
        stats['last_win'] = True
        
        stats['max_consecutive_wins'] = max(stats['max_consecutive_wins'], stats['current_streak'])
        
    else:
        stats['perdas'] += 1
        stats['lucro_total'] += profit
        stats['lucro_dia'] += profit
        
        if not stats['last_win']:
            stats['current_streak'] -= 1
        else:
            stats['current_streak'] = -1
        stats['last_win'] = False
        
        stats['max_consecutive_losses'] = max(stats['max_consecutive_losses'], abs(stats['current_streak']))
    
    st.session_state.trading_ml.analyze_pattern(trade)
    
    st.session_state.historico.append(trade.copy())
    st.session_state.trades.remove(trade)
    fechados.append(trade)

def entrada_alta_frequencia():
    """Faz entradas a cada 0.3 segundos"""
    if not st.session_state.auto_mode:
        return
    
    if (datetime.now() - st.session_state.ultimo_trade).total_seconds() < 0.3:
        return
    
    if len(st.session_state.trades) >= st.session_state.get('max_trades', 30):
        return
    
    tokens_base = [
        "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",  # ETH
        "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # BNB
        "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",  # USDC
        "0x55d398326f99059fF775485246999027B3197955",  # USDT
        "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",  # CAKE
        "0x1CE0c2827e2eF14D5C4f29a091d735A204794041",  # AVAX
        "0xCC42724C6683B7E57334c4E856f4c9965ED682bD",  # MATIC
        "0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE",  # XRP
        "0x8076C74C5e3F5852037F31Ff0093Eeb8c8ADd8D3",  # SAFEMOON
        "0x1Ba42e5193dfA8B03D15dd1B86a3113bbBEF8Eeb",  # ZOON
        "0x603c7f932ED1fc6575303D8Fb018fDCBb0f39a95",  # BANANA
    ]
    
    todos_tokens = list(set(tokens_base + [t['ca'] for t in st.session_state.monitorando]))
    
    tokens_analisar = random.sample(todos_tokens, min(3, len(todos_tokens)))
    
    for ca in tokens_analisar:
        if sum(1 for t in st.session_state.trades if t['ca'] == ca) >= 2:
            continue
        
        token_data = buscar_token(ca, use_cache=True)
        if token_data:
            analise = analise_avancada(token_data)
            
            if analise['decisao'].startswith('COMPRAR'):
                if analise.get('score', 0) < 30:
                    continue
                
                trade = criar_micro_trade_inteligente(token_data, analise)
                if trade:
                    if not any(m['ca'] == ca for m in st.session_state.monitorando):
                        st.session_state.monitorando.append({
                            'ca': ca,
                            'symbol': analise['symbol'],
                            'adicionado': datetime.now(),
                            'score_medio': analise.get('score', 0)
                        })
                    return trade

def entrada_alta_frequencia_ml():
    """Versão ML da entrada de alta frequência"""
    if not st.session_state.auto_mode:
        return
    
    current_time = datetime.now()
    if (current_time - st.session_state.ultimo_trade).total_seconds() < 0.3:
        return
    
    if len(st.session_state.trades) >= st.session_state.get('max_trades', 30):
        return
    
    tokens_base = [
        "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",  # ETH
        "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # BNB
        "0x55d398326f99059fF775485246999027B3197955",  # USDT
        "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",  # USDC
        "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",  # CAKE
        "0x1CE0c2827e2eF14D5C4f29a091d735A204794041",  # AVAX
        "0xCC42724C6683B7E57334c4E856f4c9965ED682bD",  # MATIC
        "0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE",  # XRP
        "0x4338665CBB7B2485A8855A139b75D5e34AB0DB94",  # LTC
        "0x8fF795a6F4D97E7887C79beA79aba5cc76444aDf",  # BCH
        "0x0Eb3a705fc54725037CC9e008bDede697f62F335",  # ATOM
        "0x7083609fCE4d1d8Dc0C979AAb8c869Ea2C873402",  # DOT
        "0xF8A0BF9cF54Bb92F17374d9e9A321E6a111a51bD",  # LINK
        "0x8076C74C5e3F5852037F31Ff0093Eeb8c8ADd8D3",  # SAFEMOON
        "0x1Ba42e5193dfA8B03D15dd1B86a3113bbBEF8Eeb",  # ZOON
        "0x603c7f932ED1fc6575303D8Fb018fDCBb0f39a95",  # BANANA
    ]
    
    todos_tokens = list(set(tokens_base + [t['ca'] for t in st.session_state.monitorando]))
    
    tokens_analisar = random.sample(todos_tokens, min(4, len(todos_tokens)))
    
    for ca in tokens_analisar:
        active_trades_for_token = sum(1 for t in st.session_state.trades if t['ca'] == ca)
        if active_trades_for_token >= 2:
            continue
        
        token_data = buscar_token(ca, use_cache=True)
        if token_data:
            analise = analise_avancada_ml(token_data)
            
            if analise['decisao'].startswith('COMPRAR'):
                if analise.get('score', 0) < 40:
                    continue
                
                trade = criar_micro_trade_ml(token_data, analise)
                if trade:
                    st.session_state.trading_ml.analyze_pattern(trade)
                    
                    if not any(m['ca'] == ca for m in st.session_state.monitorando):
                        st.session_state.monitorando.append({
                            'ca': ca,
                            'symbol': analise['symbol'],
                            'adicionado': datetime.now(),
                            'score_medio': analise.get('score', 0),
                            'ml_status': 'ACTIVE'
                        })
                    return trade

def check_alerts():
    """Verifica e gera alertas inteligentes"""
    alerts = []
    
    stats = st.session_state.estatisticas
    
    if stats['ganhos'] + stats['perdas'] > 10:
        win_rate = stats['ganhos'] / (stats['ganhos'] + stats['perdas'])
        
        if win_rate < 0.25:
            alerts.append({
                'type': 'CRITICAL',
                'message': f'Win rate muito baixo: {win_rate*100:.1f}%. Revisar estratégias.',
                'emoji': '⚠️'
            })
        
        if stats['current_streak'] < -5:
            alerts.append({
                'type': 'WARNING',
                'message': f'Streak negativo de {abs(stats["current_streak"])} trades consecutivos.',
                'emoji': '📉'
            })
    
    total_exposure = sum(t['position_size'] for t in st.session_state.trades)
    exposure_pct = (total_exposure / st.session_state.saldo) * 100 if st.session_state.saldo > 0 else 0
    
    if exposure_pct > 60:
        alerts.append({
            'type': 'WARNING',
            'message': f'Exposição elevada: {exposure_pct:.1f}% do saldo.',
            'emoji': '💰'
        })
    
    sentiment, sentiment_score = analyze_market_sentiment()
    if sentiment == "STRONGLY_BEARISH" and exposure_pct > 30:
        alerts.append({
            'type': 'INFO',
            'message': 'Mercado bearish. Considerar posições defensivas.',
            'emoji': '📉'
        })
    
    return alerts

def generate_daily_report():
    """Gera relatório diário automático"""
    stats = st.session_state.estatisticas
    
    report = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'total_trades': stats['total_trades'],
        'total_trades_day': stats['trades_dia'],
        'wins': stats['ganhos'],
        'losses': stats['perdas'],
        'win_rate': stats['ganhos'] / stats['total_trades'] if stats['total_trades'] > 0 else 0,
        'total_profit': stats['lucro_total'],
        'daily_profit': stats['lucro_dia'],
        'current_balance': st.session_state.saldo,
        'active_trades': len(st.session_state.trades),
        'max_consecutive_wins': stats['max_consecutive_wins'],
        'max_consecutive_losses': stats['max_consecutive_losses']
    }
    
    return report

# ==========================================================
# THREAD DO BOT
# ==========================================================

def executar_bot_ml():
    """Thread principal com todos os sistemas integrados"""
    while True:
        if st.session_state.auto_mode:
            atualizar_trades_avancado()
            entrada_alta_frequencia_ml()
            
            current_time = datetime.now()
            if 'last_sentiment_check' not in st.session_state:
                st.session_state.last_sentiment_check = current_time
            
            if (current_time - st.session_state.last_sentiment_check).seconds > 30:
                analyze_market_sentiment()
                st.session_state.last_sentiment_check = current_time
        
        time.sleep(0.3)

# Iniciar thread do bot
if st.session_state.bot_thread is None:
    st.session_state.bot_thread = threading.Thread(target=executar_bot_ml, daemon=True)
    st.session_state.bot_thread.start()

# ==========================================================
# INTERFACE DO USUÁRIO
# ==========================================================

st.title("⚡ SNIPER AI ULTRA - HIGH FREQUENCY TRADING")
st.markdown("### Entradas a cada 0.3s | Algoritmo Avançado | Win Rate Otimizado")

# Executar atualização inicial
fechados = atualizar_trades_avancado()

# ==========================================================
# SIDEBAR
# ==========================================================
with st.sidebar:
    st.header("💰 SALDO & CONTROLE")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        novo_saldo = st.number_input(
            "DEFINIR SALDO",
            min_value=100.0,
            max_value=100000.0,
            value=float(st.session_state.saldo),
            step=100.0
        )
    with col_s2:
        if st.button("💾 ATUALIZAR", use_container_width=True):
            st.session_state.saldo = novo_saldo
            st.success(f"Saldo: ${novo_saldo:,.2f}")
    
    st.divider()
    stats = st.session_state.estatisticas
    
    st.metric("💵 SALDO ATUAL", f"${st.session_state.saldo:,.2f}")
    st.metric("📊 LUCRO DIA", f"${stats['lucro_dia']:+.2f}")
    
    if stats['total_trades'] > 0:
        win_rate = (stats['ganhos'] / stats['total_trades']) * 100
        st.metric("🎯 WIN RATE", f"{win_rate:.1f}%")
        
        avg_profit = stats['lucro_total'] / stats['total_trades']
        st.metric("📈 LUCRO/MÉDIO", f"${avg_profit:+.4f}")
    else:
        st.metric("🎯 WIN RATE", "0%")
    
    col_st1, col_st2 = st.columns(2)
    with col_st1:
        st.metric("🔥 WIN STREAK", stats['max_consecutive_wins'])
    with col_st2:
        st.metric("💥 LOSS STREAK", stats['max_consecutive_losses'])
    
    st.metric("⚡ TRADES/DIA", stats['trades_dia'])
    st.metric("🔄 FREQUÊNCIA", "0.3s")
    
    st.divider()
    
    st.header("⚙️ CONFIGURAÇÕES AVANÇADAS")
    
    st.session_state.auto_mode = st.toggle(
        "🤖 ALTA FREQUÊNCIA (0.3s)",
        value=st.session_state.auto_mode,
        help="Entrada automática a cada 0.3 segundos"
    )
    
    max_trades = st.slider("MAX TRADES ATIVOS", 5, 100, 30, key="max_trades")
    
    st.subheader("📊 ESTRATÉGIAS")
    estrategia = st.selectbox(
        "ESTRATÉGIA PRINCIPAL",
        ["AGGRESSIVE (High Risk)", "MODERATE (Balanced)", "CONSERVATIVE (Low Risk)"],
        index=1
    )
    
    st.divider()
    
    if st.button("🎯 FORÇAR ENTRADA RÁPIDA", use_container_width=True):
        trade = entrada_alta_frequencia_ml()
        if trade:
            st.success(f"✅ Entrada em {trade['symbol']} | Score: {trade['score']}")
        else:
            st.info("⏳ Aguardando oportunidade")
    
    if st.button("🔄 ATUALIZAR TUDO AGORA", use_container_width=True):
        fechados = atualizar_trades_avancado()
        if fechados:
            st.info(f"{len(fechados)} trades fechados")
    
    if st.button("📊 EXPORTAR DADOS", use_container_width=True):
        if st.session_state.historico:
            df = pd.DataFrame(st.session_state.historico)
            csv = df.to_csv(index=False)
            st.download_button(
                "⬇️ BAIXAR CSV COMPLETO",
                csv,
                f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                use_container_width=True
            )
    
    if st.button("🧹 REINICIAR SISTEMA", type="secondary", use_container_width=True):
        for key in ['saldo', 'trades', 'historico', 'monitorando']:
            if key in st.session_state:
                if key == 'saldo':
                    st.session_state[key] = 1000.0
                else:
                    st.session_state[key] = []
        
        st.session_state.estatisticas = {
            'total_trades': 0,
            'ganhos': 0,
            'perdas': 0,
            'lucro_total': 0.0,
            'lucro_dia': 0.0,
            'trades_dia': 0,
            'max_consecutive_wins': 0,
            'max_consecutive_losses': 0,
            'current_streak': 0,
            'last_win': False
        }
        
        st.session_state.trading_ml = TradingML()
        st.session_state.risk_manager = DynamicRiskManager()
        st.session_state.backtester = RealTimeBacktester()
        
        st.success("Sistema reiniciado!")

# ==========================================================
# DASHBOARD EM TEMPO REAL
# ==========================================================
st.header("📈 DASHBOARD EM TEMPO REAL")

col1, col2, col3, col4 = st.columns(4)

with col1:
    trades_ativos = len(st.session_state.trades)
    st.metric("🟢 TRADES ATIVOS", trades_ativos, 
             f"{trades_ativos}/{max_trades}")

with col2:
    freq = (datetime.now() - st.session_state.ultimo_trade).total_seconds()
    st.metric("⏱️ ÚLTIMA ENTRADA", f"{freq:.1f}s", 
             "ALTA FREQUÊNCIA" if freq < 1 else "AGUARDANDO")

with col3:
    total_trades = stats['total_trades']
    st.metric("📊 TOTAL TRADES", total_trades)

with col4:
    if total_trades > 0:
        eficiencia = (stats['lucro_total'] / (st.session_state.saldo + abs(stats['lucro_total']))) * 100
        st.metric("🚀 EFICIÊNCIA", f"{eficiencia:.2f}%")

# ==========================================================
# SISTEMA DE INTELIGÊNCIA ARTIFICIAL
# ==========================================================
st.header("🧠 SISTEMA DE INTELIGÊNCIA ARTIFICIAL")

col_ai1, col_ai2, col_ai3 = st.columns(3)

with col_ai1:
    sentiment, sentiment_score = analyze_market_sentiment()
    sentiment_emoji = "🚀" if "BULLISH" in sentiment else "📉" if "BEARISH" in sentiment else "⚖️"
    st.metric("📊 SENTIMENTO DO MERCADO", sentiment, f"{sentiment_score:.1f}% {sentiment_emoji}")

with col_ai2:
    strategies = ['aggressive', 'moderate', 'conservative']
    best_strategy = None
    best_performance = 0
    
    for strategy in strategies:
        perf = st.session_state.backtester.analyze_strategy_performance(strategy)
        if perf and perf['win_rate'] > best_performance:
            best_performance = perf['win_rate']
            best_strategy = strategy
    
    if best_strategy:
        st.metric("🎯 MELHOR ESTRATÉGIA", best_strategy.upper(), f"{best_performance*100:.1f}% WR")
    else:
        st.metric("🎯 MELHOR ESTRATÉGIA", "N/A")

with col_ai3:
    ml_factors = st.session_state.trading_ml.adaptation_factors
    avg_factor = sum(ml_factors.values()) / len(ml_factors)
    adaptation_level = "ALTA" if avg_factor > 1.1 else "BAIXA" if avg_factor < 0.9 else "MÉDIA"
    st.metric("🔄 ADAPTAÇÃO ML", adaptation_level, f"Fator: {avg_factor:.2f}")

# ==========================================================
# PAINEL DE ALERTAS
# ==========================================================
st.header("🚨 PAINEL DE ALERTAS")

alerts = check_alerts()

if alerts:
    for alert in alerts:
        if alert['type'] == 'CRITICAL':
            st.error(f"{alert['emoji']} {alert['message']}")
        elif alert['type'] == 'WARNING':
            st.warning(f"{alert['emoji']} {alert['message']}")
        else:
            st.info(f"{alert['emoji']} {alert['message']}")
else:
    st.success("✅ Nenhum alerta crítico no momento")

# ==========================================================
# TRADES ATIVOS
# ==========================================================
st.header("🎯 TRADES ATIVOS")

if fechados:
    st.subheader("🔒 ÚLTIMOS FECHAMENTOS")
    for trade in fechados[-5:]:
        profit = trade['profit_value']
        emoji = "🟢" if profit >= 0 else "🔴"
        st.info(f"{emoji} **{trade['symbol']}** - {trade.get('exit_reason', 'MANUAL')} - {trade['profit_percent']:+.2f}% (${profit:+.4f})")

if st.session_state.trades:
    st.subheader(f"🟢 {len(st.session_state.trades)} TRADES EM ANDAMENTO")
    
    cols = st.columns(4)
    
    for idx, trade in enumerate(st.session_state.trades[:16]):
        with cols[idx % 4]:
            with st.container(border=True):
                profit = trade['profit_percent']
                color = "🟢" if profit >= 0 else "🔴"
                
                st.markdown(f"**{trade['symbol']}**")
                st.markdown(f"### {color} {profit:+.2f}%")
                
                st.caption(f"💰 ${trade['position_size']:.2f} ({trade['percentual_usado']:.1f}%)")
                st.caption(f"📊 Entrada: ${trade['entry_price']:.8f}")
                st.caption(f"🎯 TP: +{(trade['take_profit']/trade['entry_price']-1)*100:.1f}%")
                st.caption(f"⛔ SL: -{(1 - trade['stop_loss']/trade['entry_price'])*100:.1f}%")
                st.caption(f"📈 Score: {trade.get('score', 0)}")
                
                segundos = (datetime.now() - trade['entry_time']).seconds
                st.caption(f"⏱️ {segundos}s")
                
                if st.button("⏹️ SAIR MANUAL", key=f"manual_{trade['id']}", use_container_width=True):
                    trade['exit_reason'] = 'MANUAL'
                    fechar_trade_avancado(trade, [])
                    st.rerun()
else:
    st.info("📭 Nenhum trade ativo - Sistema em alta frequência")

# ==========================================================
# MONITORAMENTO DE TOKENS
# ==========================================================
st.header("🎯 TOKENS MONITORADOS")

col_m1, col_m2 = st.columns([3, 1])
with col_m1:
    novo_token = st.text_input("Adicionar Token (CA):", placeholder="0x...", key="new_token_ca")
with col_m2:
    if st.button("➕ ADICIONAR TOKEN", type="primary", use_container_width=True) and novo_token:
        token_data = buscar_token(novo_token.strip())
        if token_data:
            symbol = token_data['pairs'][0].get('baseToken', {}).get('symbol', 'TOKEN')
            if not any(m['ca'] == novo_token.strip() for m in st.session_state.monitorando):
                st.session_state.monitorando.append({
                    'ca': novo_token.strip(),
                    'symbol': symbol,
                    'adicionado': datetime.now(),
                    'score_medio': 0
                })
                st.success(f"✅ {symbol} adicionado!")
        else:
            st.error("❌ Token não encontrado")

if st.session_state.monitorando:
    st.subheader(f"📋 {len(st.session_state.monitorando)} TOKENS NA LISTA")
    
    for token in st.session_state.monitorando[:10]:
        try:
            data = buscar_token(token['ca'], use_cache=True)
            if data and data.get('pairs'):
                pair = data['pairs'][0]
                price = float(pair.get('priceUsd', 0))
                change_5m = float(pair.get('priceChange', {}).get('m5', 0))
                volume = float(pair.get('volume', {}).get('h24', 0))
                
                with st.container(border=True):
                    col_t1, col_t2, col_t3 = st.columns([2, 2, 1])
                    with col_t1:
                        st.write(f"**{token['symbol']}**")
                        st.write(f"${price:.8f}")
                    with col_t2:
                        st.write(f"5m: {change_5m:+.2f}%")
                        st.write(f"Vol: ${volume:,.0f}")
                    with col_t3:
                        if st.button("🗑️", key=f"del_{token['ca']}"):
                            st.session_state.monitorando.remove(token)
                            st.rerun()
        except:
            continue

# ==========================================================
# CSS FINAL
# ==========================================================
st.markdown("""
<style>
    .stButton > button {
        background: linear-gradient(45deg, #FF0000, #FF8C00, #FF0000);
        background-size: 200% 200%;
        animation: gradient 2s ease infinite;
        color: white;
        border: none;
        font-weight: bold;
        border-radius: 8px;
        transition: all 0.2s;
    }
    
    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 0 20px #FF0000;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: bold;
        background: linear-gradient(45deg, #00FF00, #00AA00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    h1, h2, h3 {
        background: linear-gradient(45deg, #FF0000, #FF4500, #FF0000);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: shine 3s linear infinite;
    }
    
    @keyframes shine {
        0% { background-position: -200px; }
        100% { background-position: 200px; }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# STATUS FINAL
# ==========================================================
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ STATUS DO SISTEMA")

col_status1, col_status2, col_status3 = st.sidebar.columns(3)

with col_status1:
    ml_active = len(st.session_state.trading_ml.patterns) > 0
    st.markdown(f"""
    <div style="text-align: center;">
        <div style="width: 10px; height: 10px; background-color: {'#00FF00' if ml_active else '#FFFF00'}; 
             border-radius: 50%; display: inline-block; margin-right: 5px;"></div>
        ML
    </div>
    """, unsafe_allow_html=True)

with col_status2:
    freq_ok = (datetime.now() - st.session_state.ultimo_trade).total_seconds() < 2
    st.markdown(f"""
    <div style="text-align: center;">
        <div style="width: 10px; height: 10px; background-color: {'#00FF00' if freq_ok else '#FF0000'}; 
             border-radius: 50%; display: inline-block; margin-right: 5px;"></div>
        Freq
    </div>
    """, unsafe_allow_html=True)

with col_status3:
    exposure = sum(t['position_size'] for t in st.session_state.trades)
    exposure_pct = (exposure / st.session_state.saldo) * 100 if st.session_state.saldo > 0 else 0
    risk_ok = exposure_pct < 50
    st.markdown(f"""
    <div style="text-align: center;">
        <div style="width: 10px; height: 10px; background-color: {'#00FF00' if risk_ok else '#FFFF00'}; 
             border-radius: 50%; display: inline-block; margin-right: 5px;"></div>
        Risco
    </div>
    """, unsafe_allow_html=True)

st.sidebar.caption(f"🕐 Última atualização: {datetime.now().strftime('%H:%M:%S')}")

# ==========================================================
# CONCLUSÃO
# ==========================================================
st.success("""
🚀 **SISTEMA SNIPER AI ULTRA CARREGADO COM SUCESSO!**

✅ **Recursos ativos:**
- Entradas a cada 0.3 segundos
- Sistema de ML para ajuste de estratégias
- Análise de sentimento do mercado
- Gestão de risco dinâmica
- Backtesting em tempo real
- Sistema de alertas inteligentes

📊 **Próximos passos:**
1. Comece com saldo pequeno ($100-$500)
2. Monitore por 1-2 horas
3. Ajuste parâmetros conforme performance
4. Gradualmente aumente o capital

⚠️ **AVISO:** Este é um sistema automatizado de alta frequência.
Sempre monitore e esteja preparado para interromper operações se necessário.
""")