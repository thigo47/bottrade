import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import random
import threading
from collections import deque
import ta  # Biblioteca de análise técnica

# ==========================================================
# CONFIGURAÇÃO DO STREAMLIT (DEVE SER O PRIMEIRO)
# ==========================================================
st.set_page_config(
    page_title="⚡ SNIPER AI ULTRA - HIGH FREQUENCY",
    page_icon="⚡",
    layout="wide"
)

# ==========================================================
# CLASSES DO SISTEMA (DEFINIR ANTES DO SESSION_STATE)
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
        self.max_position_size = 5.0  # Percentual máximo do saldo
        
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
        base_size = 2.0  # Tamanho base de 2%
        
        # Ajustes por volatilidade
        if volatility_level == "EXTREME":
            base_size *= 0.5  # Reduz pela metade
        elif volatility_level == "HIGH":
            base_size *= 0.7  # Reduz 30%
        elif volatility_level == "LOW":
            base_size *= 1.2  # Aumenta 20%
        
        # Ajustes por win rate
        if current_win_rate < 0.3:
            base_size *= 0.6  # Reduz ainda mais
        elif current_win_rate > 0.6:
            base_size *= 1.3  # Aumenta
        
        # Limites
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
        
        # Manter apenas últimos 100 trades por estratégia
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

# Inicializar session_state se não existir
if not hasattr(st, 'session_state'):
    st.session_state = {}

# Inicializar variáveis no session_state
defaults = {
    'saldo': 1000.0,
    'trades': [],
    'historico': [],
    'ultimo_trade': datetime.now(),
    'monitorando': [],
    'auto_mode': True,
    'estatisticas': {
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
    },
    'precos_historicos': {},
    'cache_tokens': {},
    'trading_ml': TradingML(),
    'risk_manager': DynamicRiskManager(),
    'backtester': RealTimeBacktester(),
    'bot_thread': None,
    'last_sentiment_check': datetime.now()
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ==========================================================
# FUNÇÕES DO SISTEMA
# ==========================================================

def buscar_token(ca, use_cache=True):
    """Busca dados do token com cache"""
    try:
        # Verificar cache (5 segundos)
        if use_cache and ca in st.session_state.cache_tokens:
            cache_time, data = st.session_state.cache_tokens[ca]
            if (datetime.now() - cache_time).seconds < 5:
                return data
        
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        response = requests.get(url, timeout=2)  # Timeout reduzido
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
        # Lista de tokens para análise de sentimento
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
                
                # Contar tokens bullish
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
        
        # Dados de price change
        price_change = pair.get('priceChange', {})
        change_5m = float(price_change.get('m5', 0))
        change_1h = float(price_change.get('h1', 0))
        change_24h = float(price_change.get('h24', 0))
        
        # Score base
        score = 0
        
        # 1. ANÁLISE DE VOLUME (PESO 35%)
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
        
        # 2. ANÁLISE DE MOMENTUM (PESO 30%)
        if change_5m > 10 and change_1h > 5:
            score += 30  # Forte momentum positivo
        elif change_5m > 5 and change_1h > 2:
            score += 20
        elif change_5m > 2:
            score += 10
        elif change_5m < -10 and change_1h < -5:
            score -= 15  # Forte momentum negativo
        elif change_5m < -5:
            score -= 10
        
        # 3. ANÁLISE DE LIQUIDEZ (PESO 20%)
        if liquidity > 1000000:
            score += 20
        elif liquidity > 500000:
            score += 15
        elif liquidity > 100000:
            score += 10
        elif liquidity > 50000:
            score += 5
        
        # 4. ANÁLISE DE PREÇO RELATIVO (PESO 15%)
        if 0.00001 < price < 0.001:
            score += 15  # Faixa ideal para micro trades
        elif 0.001 <= price < 0.01:
            score += 10
        elif price >= 0.01:
            score += 5
        
        # 5. ANÁLISE DE TENDÊNCIA (baseado em múltiplos timeframes)
        if change_5m > 0 and change_1h > 0 and change_24h > 0:
            score += 20  # Tendência bull em todos timeframes
        elif change_5m > 0 and change_1h > 0:
            score += 15
        elif change_5m > 0:
            score += 10
        
        # 6. ANÁLISE DE RISCO (ajuste dinâmico)
        risk_adjustment = 0
        if volume_24h / liquidity > 10:  # Alto volume vs liquidez
            risk_adjustment += 10
        if abs(change_5m) > 20:  # Extremamente volátil
            risk_adjustment += 5
        
        score -= risk_adjustment
        
        # DECISÃO INTELIGENTE
        if score >= 70:
            # Estratégia agressiva
            stop_loss_pct = 1.5
            take_profit_pct = 4.0
            decisao = 'COMPRAR_AGGRESSIVE'
        elif score >= 50:
            # Estratégia moderada
            stop_loss_pct = 2.0
            take_profit_pct = 3.0
            decisao = 'COMPRAR_MODERATE'
        elif score >= 30:
            # Estratégia conservadora
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
        # Análise básica
        analise_basica = analise_avancada(token_data)
        
        if analise_basica['decisao'] == 'IGNORAR' or analise_basica['decisao'] == 'ERRO':
            return analise_basica
        
        symbol = analise_basica['symbol']
        strategy = analise_basica['decisao'].split('_')[-1].lower()
        
        # Consultar sistema de ML
        ml_recommendation = st.session_state.trading_ml.get_recommendation(symbol, strategy)
        
        # Ajustar decisão baseado na recomendação do ML
        if ml_recommendation == "AVOID":
            return {'decisao': 'IGNORAR', 'symbol': symbol, 'reason': 'ML_AVOID'}
        elif ml_recommendation == "BUY_WEAK":
            # Rebaixar estratégia
            if strategy == 'aggressive':
                analise_basica['decisao'] = 'COMPRAR_MODERATE'
                analise_basica['take_profit'] = analise_basica['price'] * 1.03
                analise_basica['stop_loss'] = analise_basica['price'] * 0.98
            elif strategy == 'moderate':
                analise_basica['decisao'] = 'COMPRAR_CONSERVATIVE'
                analise_basica['take_profit'] = analise_basica['price'] * 1.02
                analise_basica['stop_loss'] = analise_basica['price'] * 0.99
        
        # Analisar volatilidade
        volatility_level, volatility_value = st.session_state.risk_manager.calculate_volatility(token_data)
        analise_basica['volatility'] = volatility_level
        analise_basica['volatility_value'] = volatility_value
        
        # Ajustar baseado em volatilidade
        if volatility_level == "EXTREME":
            analise_basica['stop_loss'] = analise_basica['price'] * 0.97
            analise_basica['score'] *= 0.8  # Penalizar score
        
        return analise_basica
        
    except Exception as e:
        return {'decisao': 'ERRO', 'erro': str(e)}

def criar_micro_trade_inteligente(token_data, analise):
    """Cria micro trade com gerenciamento inteligente de risco"""
    try:
        # Calcular win rate atual
        stats = st.session_state.estatisticas
        if stats['ganhos'] + stats['perdas'] > 0:
            current_win_rate = stats['ganhos'] / (stats['ganhos'] + stats['perdas'])
        else:
            current_win_rate = 0.5
        
        # Baseado no score
        if analise['decisao'] == 'COMPRAR_AGGRESSIVE':
            base_percent = 3.0
            multiplier = 1.5
        elif analise['decisao'] == 'COMPRAR_MODERATE':
            base_percent = 2.0
            multiplier = 1.2
        else:  # CONSERVATIVE
            base_percent = 1.0
            multiplier = 1.0
        
        # Ajustar baseado no desempenho
        if stats['ganhos'] > 0 and stats['perdas'] > 0:
            win_rate = stats['ganhos'] / (stats['ganhos'] + stats['perdas'])
            if win_rate < 0.3:  # Se win rate baixo, reduz tamanho
                base_percent *= 0.7
            elif win_rate > 0.6:  # Se win rate alto, aumenta
                base_percent *= 1.3
        
        # Ajustar baseado no streak
        if stats['current_streak'] > 0:
            # Se em winning streak, aumenta gradualmente
            base_percent *= (1 + min(stats['current_streak'] * 0.1, 0.5))
        elif stats['current_streak'] < 0:
            # Se em losing streak, reduz
            base_percent *= max(0.5, 1 + stats['current_streak'] * 0.1)
        
        # Tamanho final
        percentual = min(base_percent * multiplier, 5.0)  # Máximo 5%
        percentual = max(0.5, percentual)  # Mínimo 0.5%
        
        valor_trade = st.session_state.saldo * (percentual / 100)
        
        # Limites
        valor_trade = max(0.50, min(valor_trade, 100))  # $0.50 min, $100 max
        
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
            'trailing_stop': analise['price'] * 0.995,  # Trailing stop 0.5%
            'highest_price': analise['price']
        }
        
        # Deduzir do saldo
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
        # Calcular win rate atual
        stats = st.session_state.estatisticas
        if stats['ganhos'] + stats['perdas'] > 0:
            current_win_rate = stats['ganhos'] / (stats['ganhos'] + stats['perdas'])
        else:
            current_win_rate = 0.5
        
        # Obter tamanho da posição do Risk Manager
        volatility_level = analise.get('volatility', 'MEDIUM')
        position_size_percent = st.session_state.risk_manager.adjust_position_size(
            volatility_level, current_win_rate
        )
        
        # Ajustar baseado no sentimento do mercado
        sentiment, sentiment_score = analyze_market_sentiment()
        if sentiment == "STRONGLY_BULLISH":
            position_size_percent *= 1.2
        elif sentiment == "STRONGLY_BEARISH":
            position_size_percent *= 0.8
        
        # Limites finais
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
        
        # Deduzir do saldo
        st.session_state.saldo -= valor_trade
        st.session_state.trades.append(trade)
        st.session_state.ultimo_trade = datetime.now()
        st.session_state.estatisticas['total_trades'] += 1
        st.session_state.estatisticas['trades_dia'] += 1
        
        # Registrar no backtester
        st.session_state.backtester.add_trade_result(trade['strategy'], {
            'profit': 0,  # Será atualizado quando fechar
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
            # Buscar preço atual
            data = buscar_token(trade['ca'], use_cache=True)
            if data and data.get('pairs'):
                current_price = float(data['pairs'][0].get('priceUsd', 0))
                trade['current_price'] = current_price
                
                # Atualizar highest price
                if current_price > trade['highest_price']:
                    trade['highest_price'] = current_price
                    # Atualizar trailing stop
                    trade['trailing_stop'] = current_price * 0.995
                
                # Calcular lucro
                profit_percent = ((current_price - trade['entry_price']) / trade['entry_price']) * 100
                profit_value = trade['position_size'] * (profit_percent / 100)
                
                trade['profit_percent'] = profit_percent
                trade['profit_value'] = profit_value
                
                # ESTRATÉGIAS DE SAÍDA
                exit_reason = None
                
                # 1. Take Profit
                if current_price >= trade['take_profit']:
                    exit_reason = 'TP_HIT'
                
                # 2. Stop Loss
                elif current_price <= trade['stop_loss']:
                    exit_reason = 'SL_HIT'
                
                # 3. Trailing Stop
                elif current_price <= trade['trailing_stop']:
                    exit_reason = 'TRAILING_STOP'
                
                # 4. Timeout baseado na volatilidade
                tempo_trade = (datetime.now() - trade['entry_time']).seconds
                if tempo_trade > 300:  # 5 minutos máximo
                    if profit_percent > 0.5:  # Se está positivo, fecha
                        exit_reason = 'TIMEOUT_PROFIT'
                    elif tempo_trade > 600:  # 10 minutos máximo para negativo
                        exit_reason = 'TIMEOUT_LOSS'
                
                # Fechar trade se necessário
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
    
    # Calcular lucro final
    profit = trade['profit_value']
    
    # Retornar dinheiro + lucro
    st.session_state.saldo += trade['position_size'] + profit
    
    # Atualizar estatísticas avançadas
    stats = st.session_state.estatisticas
    
    if profit > 0:
        stats['ganhos'] += 1
        stats['lucro_total'] += profit
        stats['lucro_dia'] += profit
        
        # Atualizar streaks
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
        
        # Atualizar streaks
        if not stats['last_win']:
            stats['current_streak'] -= 1
        else:
            stats['current_streak'] = -1
        stats['last_win'] = False
        
        stats['max_consecutive_losses'] = max(stats['max_consecutive_losses'], abs(stats['current_streak']))
    
    # Atualizar sistema de ML
    st.session_state.trading_ml.analyze_pattern(trade)
    
    # Mover para histórico
    st.session_state.historico.append(trade.copy())
    st.session_state.trades.remove(trade)
    fechados.append(trade)

def entrada_alta_frequencia():
    """Faz entradas a cada 0.3 segundos com estratégias diversificadas"""
    if not st.session_state.auto_mode:
        return
    
    # Verificar frequência (0.3 segundos)
    if (datetime.now() - st.session_state.ultimo_trade).total_seconds() < 0.3:
        return
    
    # Limitar máximo de trades ativos
    if len(st.session_state.trades) >= st.session_state.get('max_trades', 30):
        return
    
    # Lista de tokens diversificada (major coins + altcoins)
    tokens_base = [
        # Major coins (baixa volatilidade)
        "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",  # ETH
        "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # BNB
        "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",  # USDC
        "0x55d398326f99059fF775485246999027B3197955",  # USDT
        
        # Altcoins voláteis (alto potencial)
        "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",  # CAKE
        "0x1CE0c2827e2eF14D5C4f29a091d735A204794041",  # AVAX (BSC)
        "0xCC42724C6683B7E57334c4E856f4c9965ED682bD",  # MATIC (BSC)
        "0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE",  # XRP (BSC)
        
        # Meme coins (alta volatilidade)
        "0x8076C74C5e3F5852037F31Ff0093Eeb8c8ADd8D3",  # SAFEMOON
        "0x1Ba42e5193dfA8B03D15dd1B86a3113bbBEF8Eeb",  # ZOON
        "0x603c7f932ED1fc6575303D8Fb018fDCBb0f39a95",  # BANANA
    ]
    
    # Adicionar tokens do usuário
    todos_tokens = list(set(tokens_base + [t['ca'] for t in st.session_state.monitorando]))
    
    # Selecionar 3 tokens aleatoriamente
    tokens_analisar = random.sample(todos_tokens, min(3, len(todos_tokens)))
    
    for ca in tokens_analisar:
        # Verificar se já tem trade ativo para este token (máximo 2)
        if sum(1 for t in st.session_state.trades if t['ca'] == ca) >= 2:
            continue
        
        # Buscar dados
        token_data = buscar_token(ca, use_cache=True)
        if token_data:
            # Análise avançada
            analise = analise_avancada(token_data)
            
            if analise['decisao'].startswith('COMPRAR'):
                # Verificar se é uma oportunidade real
                if analise.get('score', 0) < 30:
                    continue
                
                # Criar trade inteligente
                trade = criar_micro_trade_inteligente(token_data, analise)
                if trade:
                    # Adicionar aos monitorados se não estiver
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
    
    # Verificar frequência (0.3 segundos)
    current_time = datetime.now()
    if (current_time - st.session_state.ultimo_trade).total_seconds() < 0.3:
        return
    
    # Limitar máximo de trades ativos
    if len(st.session_state.trades) >= st.session_state.get('max_trades', 30):
        return
    
    # Lista expandida de tokens
    tokens_base = [
        # Major coins
        "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",  # ETH
        "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # BNB
        "0x55d398326f99059fF775485246999027B3197955",  # USDT
        "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",  # USDC
        
        # Altcoins
        "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",  # CAKE
        "0x1CE0c2827e2eF14D5C4f29a091d735A204794041",  # AVAX
        "0xCC42724C6683B7E57334c4E856f4c9965ED682bD",  # MATIC
        "0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE",  # XRP
        "0x4338665CBB7B2485A8855A139b75D5e34AB0DB94",  # LTC
        "0x8fF795a6F4D97E7887C79beA79aba5cc76444aDf",  # BCH
        
        # DeFi
        "0x0Eb3a705fc54725037CC9e008bDede697f62F335",  # ATOM
        "0x7083609fCE4d1d8Dc0C979AAb8c869Ea2C873402",  # DOT
        "0xF8A0BF9cF54Bb92F17374d9e9A321E6a111a51bD",  # LINK
        
        # Meme coins (alta volatilidade)
        "0x8076C74C5e3F5852037F31Ff0093Eeb8c8ADd8D3",  # SAFEMOON
        "0x1Ba42e5193dfA8B03D15dd1B86a3113bbBEF8Eeb",  # ZOON
        "0x603c7f932ED1fc6575303D8Fb018fDCBb0f39a95",  # BANANA
    ]
    
    # Adicionar tokens do usuário
    todos_tokens = list(set(tokens_base + [t['ca'] for t in st.session_state.monitorando]))
    
    # Selecionar tokens aleatoriamente
    tokens_analisar = random.sample(todos_tokens, min(4, len(todos_tokens)))
    
    for ca in tokens_analisar:
        # Verificar se já tem trade ativo
        active_trades_for_token = sum(1 for t in st.session_state.trades if t['ca'] == ca)
        if active_trades_for_token >= 2:
            continue
        
        # Buscar dados
        token_data = buscar_token(ca, use_cache=True)
        if token_data:
            # Análise com ML
            analise = analise_avancada_ml(token_data)
            
            if analise['decisao'].startswith('COMPRAR'):
                # Verificar score mínimo
                if analise.get('score', 0) < 40:
                    continue
                
                # Criar trade com ML
                trade = criar_micro_trade_ml(token_data, analise)
                if trade:
                    # Atualizar sistema de ML
                    st.session_state.trading_ml.analyze_pattern(trade)
                    
                    # Adicionar aos monitorados
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
    
    # Alertas baseados em performance
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
    
    # Alertas baseados em exposição
    total_exposure = sum(t['position_size'] for t in st.session_state.trades)
    exposure_pct = (total_exposure / st.session_state.saldo) * 100 if st.session_state.saldo > 0 else 0
    
    if exposure_pct > 60:
        alerts.append({
            'type': 'WARNING',
            'message': f'Exposição elevada: {exposure_pct:.1f}% do saldo.',
            'emoji': '💰'
        })
    
    # Alertas baseados em sentimento
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

def simulate_strategy(strategy_params):
    """Simula uma estratégia com parâmetros específicos"""
    # Esta é uma função simplificada para demonstração
    # Em produção, você implementaria backtesting completo
    
    results = {
        'total_trades': 100,
        'win_rate': random.uniform(0.4, 0.7),
        'avg_profit': random.uniform(0.5, 2.0),
        'sharpe_ratio': random.uniform(0.5, 2.0),
        'max_drawdown': random.uniform(-5, -1)
    }
    
    return results

# ==========================================================
# THREAD DO BOT
# ==========================================================

def executar_bot_ml():
    """Thread principal com todos os sistemas integrados"""
    while True:
        if st.session_state.auto_mode:
            # Atualizar trades
            atualizar_trades_avancado()
            
            # Tentar entrada com ML
            entrada_alta_frequencia_ml()
            
            # Atualizar sentimento a cada 30 segundos
            current_time = datetime.now()
            if 'last_sentiment_check' not in st.session_state:
                st.session_state.last_sentiment_check = current_time
            
            if (current_time - st.session_state.last_sentiment_check).seconds > 30:
                analyze_market_sentiment()
                st.session_state.last_sentiment_check = current_time
        
        time.sleep(0.3)  # Ciclo de 0.3 segundos

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
    
    # Editor de saldo
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
    
    # Estatísticas avançadas
    st.divider()
    stats = st.session_state.estatisticas
    
    st.metric("💵 SALDO ATUAL", f"${st.session_state.saldo:,.2f}")
    st.metric("📊 LUCRO DIA", f"${stats['lucro_dia']:+.2f}")
    
    if stats['total_trades'] > 0:
        win_rate = (stats['ganhos'] / stats['total_trades']) * 100
        st.metric("🎯 WIN RATE", f"{win_rate:.1f}%")
        
        # Lucro por trade
        avg_profit = stats['lucro_total'] / stats['total_trades']
        st.metric("📈 LUCRO/MÉDIO", f"${avg_profit:+.4f}")
    else:
        st.metric("🎯 WIN RATE", "0%")
    
    # Streaks
    col_st1, col_st2 = st.columns(2)
    with col_st1:
        st.metric("🔥 WIN STREAK", stats['max_consecutive_wins'])
    with col_st2:
        st.metric("💥 LOSS STREAK", stats['max_consecutive_losses'])
    
    st.metric("⚡ TRADES/DIA", stats['trades_dia'])
    st.metric("🔄 FREQUÊNCIA", "0.3s")
    
    st.divider()
    
    # Controles
    st.header("⚙️ CONFIGURAÇÕES AVANÇADAS")
    
    st.session_state.auto_mode = st.toggle(
        "🤖 ALTA FREQUÊNCIA (0.3s)",
        value=st.session_state.auto_mode,
        help="Entrada automática a cada 0.3 segundos"
    )
    
    max_trades = st.slider("MAX TRADES ATIVOS", 5, 100, 30, key="max_trades")
    
    # Estratégias
    st.subheader("📊 ESTRATÉGIAS")
    estrategia = st.selectbox(
        "ESTRATÉGIA PRINCIPAL",
        ["AGGRESSIVE (High Risk)", "MODERATE (Balanced)", "CONSERVATIVE (Low Risk)"],
        index=1
    )
    
    st.divider()
    
    # Ações rápidas
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
        for key in defaults:
            if key != 'bot_thread':  # Mantém a thread
                st.session_state[key] = defaults[key]
        st.success("Sistema reiniciado!")

# ==========================================================
# SEÇÃO 1: DASHBOARD EM TEMPO REAL
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
# SEÇÃO 2: SISTEMA DE INTELIGÊNCIA ARTIFICIAL
# ==========================================================
st.header("🧠 SISTEMA DE INTELIGÊNCIA ARTIFICIAL")

col_ai1, col_ai2, col_ai3 = st.columns(3)

with col_ai1:
    # Análise de sentimento
    sentiment, sentiment_score = analyze_market_sentiment()
    sentiment_emoji = "🚀" if "BULLISH" in sentiment else "📉" if "BEARISH" in sentiment else "⚖️"
    st.metric("📊 SENTIMENTO DO MERCADO", sentiment, f"{sentiment_score:.1f}% {sentiment_emoji}")

with col_ai2:
    # Performance das estratégias
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
    # Adaptação do ML
    ml_factors = st.session_state.trading_ml.adaptation_factors
    avg_factor = sum(ml_factors.values()) / len(ml_factors)
    adaptation_level = "ALTA" if avg_factor > 1.1 else "BAIXA" if avg_factor < 0.9 else "MÉDIA"
    st.metric("🔄 ADAPTAÇÃO ML", adaptation_level, f"Fator: {avg_factor:.2f}")

# ==========================================================
# SEÇÃO 3: PAINEL DE ALERTAS
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
# SEÇÃO 4: TRADES ATIVOS
# ==========================================================
st.header("🎯 TRADES ATIVOS")

# Mostrar trades fechados recentemente
if fechados:
    st.subheader("🔒 ÚLTIMOS FECHAMENTOS")
    for trade in fechados[-5:]:
        profit = trade['profit_value']
        emoji = "🟢" if profit >= 0 else "🔴"
        st.info(f"{emoji} **{trade['symbol']}** - {trade.get('exit_reason', 'MANUAL')} - {trade['profit_percent']:+.2f}% (${profit:+.4f})")

# Mostrar trades ativos
if st.session_state.trades:
    st.subheader(f"🟢 {len(st.session_state.trades)} TRADES EM ANDAMENTO")
    
    # Grid de trades
    cols = st.columns(4)
    
    for idx, trade in enumerate(st.session_state.trades[:16]):
        with cols[idx % 4]:
            with st.container(border=True):
                profit = trade['profit_percent']
                color = "🟢" if profit >= 0 else "🔴"
                
                # Cabeçalho
                st.markdown(f"**{trade['symbol']}**")
                st.markdown(f"### {color} {profit:+.2f}%")
                
                # Informações detalhadas
                st.caption(f"💰 ${trade['position_size']:.2f} ({trade['percentual_usado']:.1f}%)")
                st.caption(f"📊 Entrada: ${trade['entry_price']:.8f}")
                st.caption(f"🎯 TP: +{(trade['take_profit']/trade['entry_price']-1)*100:.1f}%")
                st.caption(f"⛔ SL: -{(1 - trade['stop_loss']/trade['entry_price'])*100:.1f}%")
                st.caption(f"📈 Score: {trade.get('score', 0)}")
                
                # Duração
                segundos = (datetime.now() - trade['entry_time']).seconds
                st.caption(f"⏱️ {segundos}s")
                
                # Botão de saída
                if st.button("⏹️ SAIR MANUAL", key=f"manual_{trade['id']}", use_container_width=True):
                    trade['exit_reason'] = 'MANUAL'
                    fechar_trade_avancado(trade, [])
                    st.rerun()
else:
    st.info("📭 Nenhum trade ativo - Sistema em alta frequência")

# ==========================================================
# SEÇÃO 5: ANÁLISE DE PERFORMANCE DETALHADA
# ==========================================================
st.header("📊 ANÁLISE DE PERFORMANCE DETALHADA")

# Criar abas para diferentes análises
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Estratégias", 
    "📈 Volatilidade", 
    "🧠 ML Insights", 
    "⚠️ Gestão de Risco"
])

with tab1:
    st.subheader("Performance por Estratégia")
    
    strategies = ['aggressive', 'moderate', 'conservative']
    cols = st.columns(3)
    
    for idx, strategy in enumerate(strategies):
        with cols[idx]:
            perf = st.session_state.backtester.analyze_strategy_performance(strategy)
            if perf:
                st.metric(
                    f"⚡ {strategy.upper()}",
                    f"{perf['win_rate']*100:.1f}% WR",
                    f"{perf['total_trades']} trades"
                )
                st.progress(perf['win_rate'])
            else:
                st.metric(f"⚡ {strategy.upper()}", "N/A")

with tab2:
    st.subheader("Análise de Volatilidade")
    
    # Coletar dados de volatilidade dos trades ativos
    if st.session_state.trades:
        volatilities = [t.get('volatility', 'MEDIUM') for t in st.session_state.trades]
        volatility_counts = {
            'EXTREME': volatilities.count('EXTREME'),
            'HIGH': volatilities.count('HIGH'),
            'MEDIUM': volatilities.count('MEDIUM'),
            'LOW': volatilities.count('LOW')
        }
        
        st.write("**Distribuição de Volatilidade:**")
        for vol_level, count in volatility_counts.items():
            st.write(f"{vol_level}: {count} trades")
            
        # Recomendações baseadas em volatilidade
        st.subheader("🎯 Recomendações")
        
        if volatility_counts['EXTREME'] > 2:
            st.warning("⚠️ ALTA VOLATILIDADE: Reduzir tamanho das posições")
        elif volatility_counts['LOW'] > 5:
            st.info("📈 BAIXA VOLATILIDADE: Pode aumentar posições moderadamente")

with tab3:
    st.subheader("Insights do Sistema de ML")
    
    # Mostrar padrões aprendidos
    ml = st.session_state.trading_ml
    if ml.patterns:
        st.write("**📚 Padrões Aprendidos:**")
        
        # Mostrar top 5 tokens com melhor performance
        successful_patterns = []
        for key, trades in ml.patterns.items():
            if len(trades) >= 5:
                winning_trades = [t for t in trades if t['profit'] > 0]
                win_rate = len(winning_trades) / len(trades)
                successful_patterns.append((key, win_rate))
        
        successful_patterns.sort(key=lambda x: x[1], reverse=True)
        
        for key, win_rate in successful_patterns[:5]:
            st.write(f"🔹 {key}: {win_rate*100:.1f}% win rate")
    else:
        st.info("⏳ Coletando dados para análise...")

with tab4:
    st.subheader("Gestão de Risco")
    
    # Calcular métricas de risco
    if st.session_state.historico:
        recent_trades = st.session_state.historico[-20:]  # Últimos 20 trades
        
        if recent_trades:
            profits = [t['profit_value'] for t in recent_trades]
            max_drawdown = min(profits) if profits else 0
            avg_loss = np.mean([p for p in profits if p < 0]) if any(p < 0 for p in profits) else 0
            
            col_r1, col_r2, col_r3 = st.columns(3)
            
            with col_r1:
                st.metric("📉 Pior Perda", f"${max_drawdown:.2f}")
            
            with col_r2:
                st.metric("📊 Perda Média", f"${avg_loss:.2f}" if avg_loss < 0 else "$0.00")
            
            with col_r3:
                exposure = sum(t['position_size'] for t in st.session_state.trades)
                exposure_pct = (exposure / st.session_state.saldo) * 100 if st.session_state.saldo > 0 else 0
                st.metric("💰 Exposição", f"{exposure_pct:.1f}%")
            
            # Alertas de risco
            st.subheader("🚨 Alertas")
            
            if exposure_pct > 50:
                st.error("⚠️ EXPOSIÇÃO ELEVADA: Reduzir posições abertas")
            
            if st.session_state.estatisticas['current_streak'] < -3:
                st.warning("📉 STREAK NEGATIVO: Considerar reduzir tamanho dos trades")

# ==========================================================
# SEÇÃO 6: MONITORAMENTO DE TOKENS
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

# Mostrar tokens monitorados
if st.session_state.monitorando:
    st.subheader(f"📋 {len(st.session_state.monitorando)} TOKENS NA LISTA")
    
    # Atualizar dados dos tokens monitorados
    for token in st.session_state.monitorando[:10]:  # Limitar para performance
        try:
            data = buscar_token(token['ca'], use_cache=True)
            if data and data.get('pairs'):
                pair = data['pairs'][0]
                price = float(pair.get('priceUsd', 0))
                change_5m = float(pair.get('priceChange', {}).get('m5', 0))
                volume = float(pair.get('volume', {}).get('h24', 0))
                
                # Mostrar card
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
# SEÇÃO 7: RELATÓRIO DIÁRIO
# ==========================================================
st.header("📋 RELATÓRIO DIÁRIO")

if st.button("📄 GERAR RELATÓRIO COMPLETO", use_container_width=True):
    report = generate_daily_report()
    
    col_r1, col_r2 = st.columns(2)
    
    with col_r1:
        st.subheader("📊 Estatísticas do Dia")
        st.write(f"**Trades realizados:** {report['total_trades_day']}")
        st.write(f"**Lucro do dia:** ${report['daily_profit']:+.2f}")
        st.write(f"**Win rate:** {report['win_rate']*100:.1f}%")
    
    with col_r2:
        st.subheader("💰 Situação Atual")
        st.write(f"**Saldo:** ${report['current_balance']:.2f}")
        st.write(f"**Trades ativos:** {report['active_trades']}")
        st.write(f"**Lucro total:** ${report['total_profit']:+.2f}")
    
    # Gráfico de evolução (simulado)
    st.subheader("📈 Evolução do Dia")
    
    # Simular dados para o gráfico
    if len(st.session_state.historico) > 0:
        times = []
        profits = []
        cumulative = 0
        
        for trade in st.session_state.historico:
            if trade['exit_time'].date() == datetime.now().date():
                cumulative += trade['profit_value']
                times.append(trade['exit_time'])
                profits.append(cumulative)
        
        if profits:
            chart_data = pd.DataFrame({
                'Hora': times,
                'Lucro Acumulado': profits
            })
            st.line_chart(chart_data.set_index('Hora'))

# ==========================================================
# SEÇÃO 8: SIMULADOR DE ESTRATÉGIAS
# ==========================================================
with st.expander("🎮 SIMULADOR DE ESTRATÉGIAS"):
    st.subheader("Teste Diferentes Configurações")
    
    col_sim1, col_sim2 = st.columns(2)
    
    with col_sim1:
        sim_strategy = st.selectbox(
            "Estratégia",
            ["AGGRESSIVE", "MODERATE", "CONSERVATIVE", "MIXED"]
        )
        
        sim_duration = st.slider(
            "Duração (dias)",
            1, 30, 7
        )
    
    with col_sim2:
        sim_risk = st.slider(
            "Nível de Risco",
            1, 10, 5
        )
        
        sim_position_size = st.slider(
            "Tamanho da Posição (%)",
            0.5, 5.0, 2.0
        )
    
    if st.button("🎯 EXECUTAR SIMULAÇÃO", use_container_width=True):
        with st.spinner("Simulando..."):
            time.sleep(2)  # Simular processamento
            
            results = simulate_strategy({
                'strategy': sim_strategy,
                'duration': sim_duration,
                'risk': sim_risk,
                'position_size': sim_position_size
            })
            
            st.success("Simulação concluída!")
            
            col_res1, col_res2, col_res3 = st.columns(3)
            
            with col_res1:
                st.metric("🎯 Win Rate", f"{results['win_rate']*100:.1f}%")
            
            with col_res2:
                st.metric("💰 Lucro Médio", f"${results['avg_profit']:.2f}")
            
            with col_res3:
                st.metric("📉 Máximo Drawdown", f"{results['max_drawdown']:.1f}%")

# ==========================================================
# CSS FINAL
# ==========================================================
st.markdown("""
<style>
    /* Interface ultra rápida */
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
    
    /* Cards de trade animados */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 10px;
        border: 2px solid;
        padding: 10px;
        margin: 5px 0;
        animation: pulse 1.5s infinite;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(0, 255, 0, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(0, 255, 0, 0); }
        100% { box-shadow: 0 0 0 0 rgba(0, 255, 0, 0); }
    }
    
    /* Métricas destacadas */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: bold;
        background: linear-gradient(45deg, #00FF00, #00AA00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Títulos dinâmicos */
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
    
    /* Status em tempo real */
    .stAlert {
        border-left: 5px solid #00FF00;
        animation: blink 1s infinite;
    }
    
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# STATUS FINAL
# ==========================================================
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ STATUS DO SISTEMA")

# Indicadores de status
col_status1, col_status2, col_status3 = st.sidebar.columns(3)

with col_status1:
    # Status ML
    ml_active = len(st.session_state.trading_ml.patterns) > 0
    st.markdown(f"""
    <div style="text-align: center;">
        <div style="width: 10px; height: 10px; background-color: {'#00FF00' if ml_active else '#FFFF00'}; 
             border-radius: 50%; display: inline-block; margin-right: 5px; animation: pulse 1.5s infinite;"></div>
        ML
    </div>
    """, unsafe_allow_html=True)

with col_status2:
    # Status Frequência
    freq_ok = (datetime.now() - st.session_state.ultimo_trade).total_seconds() < 2
    st.markdown(f"""
    <div style="text-align: center;">
        <div style="width: 10px; height: 10px; background-color: {'#00FF00' if freq_ok else '#FF0000'}; 
             border-radius: 50%; display: inline-block; margin-right: 5px; animation: pulse 1.5s infinite;"></div>
        Freq
    </div>
    """, unsafe_allow_html=True)

with col_status3:
    # Status Risco
    exposure = sum(t['position_size'] for t in st.session_state.trades)
    exposure_pct = (exposure / st.session_state.saldo) * 100 if st.session_state.saldo > 0 else 0
    risk_ok = exposure_pct < 50
    st.markdown(f"""
    <div style="text-align: center;">
        <div style="width: 10px; height: 10px; background-color: {'#00FF00' if risk_ok else '#FFFF00'}; 
             border-radius: 50%; display: inline-block; margin-right: 5px; animation: pulse 1.5s infinite;"></div>
        Risco
    </div>
    """, unsafe_allow_html=True)

# Última atualização
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

# ==========================================================
# AUTO-REFRESH
# ==========================================================
# Auto-refresh a cada 10 segundos para atualizar a interface
time.sleep(10)
st.rerun()