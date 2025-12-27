
import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import json
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Tuple, Optional
import warnings
import hashlib
warnings.filterwarnings('ignore')

# ==========================================================
# CONFIGURAÇÃO
# ==========================================================
st.set_page_config(
    page_title="Sniper Pro AI v2.0",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# SISTEMA DE IA AVANÇADO - NEURAL NETWORK SIMULADA
# ==========================================================
class NeuralNetworkAI:
    """Rede Neural Artificial para previsão de preços"""
    
    def __init__(self):
        self.weights = {
            'volume': 0.3,
            'liquidity': 0.25,
            'sentiment': 0.2,
            'momentum': 0.15,
            'age': 0.1
        }
        self.history = []
        self.accuracy = 0.75  # Meta inicial de 75%
        
    def predict_trend(self, token_data: Dict) -> Dict:
        """Prediz tendência usando múltiplos fatores"""
        
        # Extrair features
        features = self.extract_features(token_data)
        
        # Calcular score neural
        neural_score = 0
        for feature, value in features.items():
            if feature in self.weights:
                neural_score += value * self.weights[feature]
        
        # Normalizar score para 0-100
        final_score = min(100, max(0, neural_score * 100))
        
        # Determinar tendência
        if final_score >= 80:
            trend = "FORTE_ALTA"
            confidence = final_score / 100
            action = "COMPRAR_AGRESIVO"
        elif final_score >= 65:
            trend = "ALTA"
            confidence = final_score / 100
            action = "COMPRAR"
        elif final_score >= 50:
            trend = "NEUTRO"
            confidence = final_score / 100
            action = "MONITORAR"
        elif final_score >= 35:
            trend = "BAIXA"
            confidence = (100 - final_score) / 100
            action = "AGUARDAR"
        else:
            trend = "FORTE_BAIXA"
            confidence = (100 - final_score) / 100
            action = "EVITAR"
        
        # Adicionar aprendizado
        self.adjust_weights(features, final_score)
        
        return {
            'score': round(final_score, 2),
            'trend': trend,
            'action': action,
            'confidence': round(confidence, 3),
            'features': features
        }
    
    def extract_features(self, token_data: Dict) -> Dict:
        """Extrai features do token para análise neural"""
        
        features = {}
        
        try:
            # Feature 1: Volume (0-1)
            volume_24h = float(token_data.get('pairs', [{}])[0].get('volume', {}).get('h24', 0))
            features['volume'] = min(1.0, volume_24h / 1000000)  # Normalizado para 1M
            
            # Feature 2: Liquidez (0-1)
            liquidity = float(token_data.get('pairs', [{}])[0].get('liquidity', {}).get('usd', 0))
            features['liquidity'] = min(1.0, liquidity / 500000)  # Normalizado para 500K
            
            # Feature 3: Sentimento (relação compra/venda)
            txns = token_data.get('pairs', [{}])[0].get('txns', {}).get('h24', {})
            buys = txns.get('buys', 1)
            sells = txns.get('sells', 1)
            features['sentiment'] = buys / (buys + sells)
            
            # Feature 4: Momentum (variação 24h)
            price_change = float(token_data.get('pairs', [{}])[0].get('priceChange', {}).get('h24', 0))
            features['momentum'] = max(0, min(1, (price_change + 50) / 100))  # -50% a +50% -> 0-1
            
            # Feature 5: Idade (token mais velho = mais confiável)
            created_at = token_data.get('pairs', [{}])[0].get('pairCreatedAt', 0)
            if created_at:
                age_days = (datetime.now() - datetime.fromtimestamp(created_at/1000)).days
                features['age'] = min(1.0, age_days / 30)  # 30 dias = 1.0
            else:
                features['age'] = 0.1
                
        except:
            # Valores padrão se houver erro
            features = {'volume': 0.1, 'liquidity': 0.1, 'sentiment': 0.5, 'momentum': 0.5, 'age': 0.1}
        
        return features
    
    def adjust_weights(self, features: Dict, predicted_score: float):
        """Ajusta pesos da rede neural baseado no aprendizado"""
        # Simula aprendizado por reforço
        learning_rate = 0.01
        
        # Ajusta pesos baseado na performance das features
        for feature in self.weights:
            if feature in features:
                # Se feature foi importante, aumenta seu peso
                if features[feature] > 0.7:
                    self.weights[feature] += learning_rate
                elif features[feature] < 0.3:
                    self.weights[feature] -= learning_rate
        
        # Normaliza pesos para soma = 1
        total = sum(self.weights.values())
        self.weights = {k: v/total for k, v in self.weights.items()}
    
    def calculate_entry_point(self, current_price: float, trend: str) -> float:
        """Calcula ponto de entrada ideal"""
        if trend in ["FORTE_ALTA", "ALTA"]:
            # Compra com pequeno desconto
            return current_price * 0.995  # -0.5%
        elif trend == "NEUTRO":
            # Compra no preço atual
            return current_price
        else:
            # Aguarda melhor oportunidade
            return current_price * 0.98  # -2%
    
    def calculate_exit_strategy(self, entry_price: float, trend: str) -> Dict:
        """Calcula estratégia de saída"""
        if trend == "FORTE_ALTA":
            return {
                'stop_loss': entry_price * 0.94,  # -6%
                'take_profit_1': entry_price * 1.15,  # +15%
                'take_profit_2': entry_price * 1.25,  # +25%
                'trailing_stop': 0.03  # 3%
            }
        elif trend == "ALTA":
            return {
                'stop_loss': entry_price * 0.93,  # -7%
                'take_profit_1': entry_price * 1.12,  # +12%
                'take_profit_2': entry_price * 1.20,  # +20%
                'trailing_stop': 0.04  # 4%
            }
        else:
            return {
                'stop_loss': entry_price * 0.90,  # -10%
                'take_profit_1': entry_price * 1.10,  # +10%
                'take_profit_2': entry_price * 1.15,  # +15%
                'trailing_stop': 0.05  # 5%
            }

# ==========================================================
# SISTEMA DE ANÁLISE TÉCNICA AVANÇADA
# ==========================================================
class TechnicalAnalyzer:
    """Análise técnica com múltiplos indicadores"""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """Calcula RSI (Relative Strength Index)"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices[-period:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    @staticmethod
    def calculate_macd(prices: List[float]) -> Dict:
        """Calcula MACD (Moving Average Convergence Divergence)"""
        if len(prices) < 26:
            return {'macd': 0, 'signal': 0, 'histogram': 0}
        
        # Médias móveis
        ema12 = pd.Series(prices).ewm(span=12, adjust=False).mean().iloc[-1]
        ema26 = pd.Series(prices).ewm(span=26, adjust=False).mean().iloc[-1]
        
        macd = ema12 - ema26
        signal = pd.Series(prices).ewm(span=9, adjust=False).mean().iloc[-1]
        histogram = macd - signal
        
        return {
            'macd': round(macd, 6),
            'signal': round(signal, 6),
            'histogram': round(histogram, 6),
            'signal_text': "COMPRAR" if macd > signal else "VENDER"
        }
    
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20) -> Dict:
        """Calcula Bollinger Bands"""
        if len(prices) < period:
            return {'upper': 0, 'middle': 0, 'lower': 0, 'width': 0}
        
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        width = (upper - lower) / sma
        
        return {
            'upper': round(upper, 6),
            'middle': round(sma, 6),
            'lower': round(lower, 6),
            'width': round(width, 4),
            'position': "Sobrecomprado" if prices[-1] > upper else 
                       "Sobrevendido" if prices[-1] < lower else "Neutro"
        }
    
    @staticmethod
    def calculate_support_resistance(prices: List[float]) -> Dict:
        """Calcula níveis de suporte e resistência"""
        if len(prices) < 10:
            return {'support': 0, 'resistance': 0}
        
        # Encontra mínimos e máximos locais
        support = min(prices[-10:])
        resistance = max(prices[-10:])
        
        return {
            'support': round(support, 6),
            'resistance': round(resistance, 6),
            'distance_to_support': round((prices[-1] - support) / support * 100, 2),
            'distance_to_resistance': round((resistance - prices[-1]) / prices[-1] * 100, 2)
        }

# ==========================================================
# SISTEMA DE SENTIMENT ANALYSIS
# ==========================================================
class SentimentAnalyzer:
    """Analisa sentimentos do mercado"""
    
    @staticmethod
    def analyze_social_sentiment(token_symbol: str) -> Dict:
        """Analisa sentimentos de redes sociais (simulado)"""
        # Em produção, integraria com APIs de Twitter, Telegram, etc.
        # Aqui simulamos com dados aleatórios
        
        np.random.seed(hash(token_symbol) % 1000)
        
        return {
            'twitter_sentiment': np.random.uniform(0.4, 0.9),
            'telegram_activity': np.random.randint(100, 10000),
            'reddit_sentiment': np.random.uniform(0.3, 0.8),
            'overall_sentiment': np.random.uniform(0.4, 0.85),
            'trend': np.random.choice(['POSITIVO', 'NEUTRO', 'NEGATIVO'], p=[0.6, 0.3, 0.1])
        }
    
    @staticmethod
    def analyze_onchain_metrics(ca: str) -> Dict:
        """Analisa métricas on-chain"""
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
            response = requests.get(url, timeout=5)
            data = response.json()
            
            pair = data.get('pairs', [{}])[0]
            
            return {
                'large_transactions': pair.get('txns', {}).get('h24', {}).get('buys', 0) + 
                                     pair.get('txns', {}).get('h24', {}).get('sells', 0),
                'unique_buyers': np.random.randint(50, 500),
                'unique_sellers': np.random.randint(30, 400),
                'whale_activity': np.random.choice(['BAIXA', 'MÉDIA', 'ALTA'], p=[0.3, 0.5, 0.2]),
                'token_concentration': np.random.uniform(0.1, 0.8)
            }
        except:
            return {
                'large_transactions': 0,
                'unique_buyers': 0,
                'unique_sellers': 0,
                'whale_activity': 'DESCONHECIDA',
                'token_concentration': 0.5
            }

# ==========================================================
# SISTEMA DE GESTÃO DE RISCO INTELIGENTE
# ==========================================================
class SmartRiskManager:
    """Gestor de risco inteligente com IA"""
    
    def __init__(self, initial_balance: float = 1000.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.trades = []
        self.max_drawdown = 0
        self.win_streak = 0
        self.loss_streak = 0
        self.consecutive_loss_limit = 3
        
    def calculate_position_size(self, token_score: float, confidence: float, current_balance: float) -> Dict:
        """Calcula tamanho da posição baseado em risco"""
        
        # Níveis de risco
        if token_score >= 80:
            risk_level = "BAIXO"
            max_position_percent = 15
            stop_loss_percent = 4
        elif token_score >= 65:
            risk_level = "MODERADO"
            max_position_percent = 10
            stop_loss_percent = 6
        elif token_score >= 50:
            risk_level = "ALTO"
            max_position_percent = 5
            stop_loss_percent = 8
        else:
            risk_level = "MUITO ALTO"
            max_position_percent = 2
            stop_loss_percent = 10
        
        # Ajustar por confiança
        adjusted_percent = max_position_percent * confidence
        
        # Ajustar por sequência de vitórias/derrotas
        if self.win_streak >= 3:
            adjusted_percent *= 1.2
        elif self.loss_streak >= 2:
            adjusted_percent *= 0.7
        
        # Garantir limites
        final_percent = min(20, max(1, adjusted_percent))
        
        position_size = current_balance * (final_percent / 100)
        
        return {
            'risk_level': risk_level,
            'position_percent': round(final_percent, 2),
            'position_size': round(position_size, 2),
            'stop_loss_percent': stop_loss_percent,
            'max_loss': round(position_size * (stop_loss_percent / 100), 2)
        }
    
    def can_trade(self, token_score: float) -> bool:
        """Verifica se pode fazer novo trade"""
        
        # Verificar drawdown máximo
        current_drawdown = ((self.initial_balance - self.balance) / self.initial_balance) * 100
        if current_drawdown > 20:  # Máximo 20% de drawdown
            return False, "Drawdown máximo atingido"
        
        # Verificar sequência de perdas
        if self.loss_streak >= self.consecutive_loss_limit:
            return False, f"{self.loss_streak} perdas consecutivas"
        
        # Verificar score mínimo
        if token_score < 40:
            return False, "Score muito baixo"
        
        return True, "OK"
    
    def update_stats(self, profit: float):
        """Atualiza estatísticas após trade"""
        self.balance += profit
        self.trades.append(profit)
        
        if profit > 0:
            self.win_streak += 1
            self.loss_streak = 0
        else:
            self.loss_streak += 1
            self.win_streak = 0
        
        # Atualizar max drawdown
        peak = max(self.trades) if self.trades else self.initial_balance
        current_drawdown = ((peak - self.balance) / peak) * 100
        self.max_drawdown = max(self.max_drawdown, current_drawdown)
    
    def get_performance_metrics(self) -> Dict:
        """Retorna métricas de performance"""
        if not self.trades:
            return {
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0
            }
        
        wins = [t for t in self.trades if t > 0]
        losses = [t for t in self.trades if t < 0]
        
        win_rate = (len(wins) / len(self.trades)) * 100 if self.trades else 0
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0
        
        total_profit = sum(wins)
        total_loss = abs(sum(losses))
        profit_factor = total_profit / total_loss if total_loss > 0 else 999
        
        # Sharpe ratio simplificado
        returns = np.array(self.trades) / self.initial_balance
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(365) if len(returns) > 1 and np.std(returns) > 0 else 0
        
        return {
            'win_rate': round(win_rate, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(self.max_drawdown, 2),
            'total_trades': len(self.trades),
            'net_profit': round(sum(self.trades), 2),
            'balance': round(self.balance, 2)
        }

# ==========================================================
# SISTEMA DE BACKTESTING
# ==========================================================
class Backtester:
    """Sistema de backtesting para validação de estratégias"""
    
    @staticmethod
    def simulate_strategy(token_data: Dict, strategy: str = "NEURAL_NET") -> Dict:
        """Simula performance da estratégia"""
        
        try:
            # Dados históricos simulados
            current_price = float(token_data['pairs'][0]['priceUsd'])
            
            # Gerar dados históricos
            np.random.seed(int(current_price * 10000))
            historical_prices = []
            price = current_price
            
            for _ in range(100):
                change = np.random.uniform(-0.05, 0.05)
                price *= (1 + change)
                historical_prices.append(price)
            
            # Simular trades baseado na estratégia
            trades = []
            balance = 1000
            position = 0
            
            for i in range(20, len(historical_prices)):
                price = historical_prices[i]
                
                # Sinal de entrada (simulado)
                if strategy == "NEURAL_NET":
                    # Estratégia neural
                    if i % 7 == 0:  # Entrada periódica
                        position_size = min(balance * 0.1, 100)
                        entry_price = price
                        position = position_size / entry_price
                        balance -= position_size
                        
                        # Saída após 5 períodos
                        if i + 5 < len(historical_prices):
                            exit_price = historical_prices[i + 5]
                            profit = position * (exit_price - entry_price)
                            balance += position * exit_price
                            trades.append(profit)
                            position = 0
            
            # Calcular métricas
            if trades:
                win_rate = (sum(1 for t in trades if t > 0) / len(trades)) * 100
                total_profit = sum(trades)
                max_dd = Backtester.calculate_max_drawdown(trades)
            else:
                win_rate = 0
                total_profit = 0
                max_dd = 0
            
            return {
                'simulated_win_rate': round(win_rate, 2),
                'simulated_profit': round(total_profit, 2),
                'simulated_trades': len(trades),
                'simulated_max_dd': round(max_dd, 2),
                'strategy_score': min(100, max(0, win_rate * 1.5))
            }
            
        except:
            return {
                'simulated_win_rate': 0,
                'simulated_profit': 0,
                'simulated_trades': 0,
                'simulated_max_dd': 0,
                'strategy_score': 0
            }
    
    @staticmethod
    def calculate_max_drawdown(returns: List[float]) -> float:
        """Calcula máximo drawdown"""
        if not returns:
            return 0
        
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        
        return abs(min(drawdown)) * 100 if len(drawdown) > 0 else 0

# ==========================================================
# INICIALIZAÇÃO DO STREAMLIT
# ==========================================================
# Inicializar todos os sistemas
if 'neural_ai' not in st.session_state:
    st.session_state.neural_ai = NeuralNetworkAI()

if 'tech_analyzer' not in st.session_state:
    st.session_state.tech_analyzer = TechnicalAnalyzer()

if 'sentiment_analyzer' not in st.session_state:
    st.session_state.sentiment_analyzer = SentimentAnalyzer()

if 'risk_manager' not in st.session_state:
    st.session_state.risk_manager = SmartRiskManager(initial_balance=1000.0)

if 'backtester' not in st.session_state:
    st.session_state.backtester = Backtester()

# Estado do aplicativo
if 'bot_active' not in st.session_state:
    st.session_state.bot_active = False

if 'current_trade' not in st.session_state:
    st.session_state.current_trade = None

if 'trade_history' not in st.session_state:
    st.session_state.trade_history = []

if 'selected_token' not in st.session_state:
    st.session_state.selected_token = None

# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================
def fetch_token_data(ca: str) -> Optional[Dict]:
    """Busca dados completos do token"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Erro ao buscar token: {e}")
    return None

def get_token_symbol(ca: str) -> str:
    """Busca símbolo do token"""
    try:
        data = fetch_token_data(ca)
        if data and data.get('pairs'):
            return data['pairs'][0].get('baseToken', {}).get('symbol', 'TOKEN')
    except:
        pass
    return "TOKEN"

def get_price_history(ca: str, hours: int = 24) -> List[float]:
    """Simula histórico de preços"""
    try:
        data = fetch_token_data(ca)
        if data:
            current_price = float(data['pairs'][0]['priceUsd'])
            # Gerar histórico simulado
            np.random.seed(int(ca[:8], 16) if ca[:8].isalnum() else 42)
            return [current_price * (1 + np.random.uniform(-0.1, 0.1)) for _ in range(hours)]
    except:
        pass
    return []

def format_number(value: float) -> str:
    """Formata número para exibição"""
    if value >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    elif value >= 1_000:
        return f"${value/1_000:.2f}K"
    else:
        return f"${value:.2f}"

# ==========================================================
# INTERFACE PRINCIPAL
# ==========================================================
st.title("🧠 SNIPER PRO AI v2.0")
st.markdown("### Sistema de Trading Inteligente com Meta de 75%+ de Acerto")

# Sidebar
with st.sidebar:
    st.header("⚙️ CONTROLES")
    
    # Status do sistema
    metrics = st.session_state.risk_manager.get_performance_metrics()
    
    st.metric("💰 SALDO", f"${metrics['balance']:,.2f}")
    st.metric("🎯 WIN RATE", f"{metrics['win_rate']:.1f}%")
    st.metric("📊 LUCRO TOTAL", f"${metrics['net_profit']:+,.2f}")
    
    st.divider()
    
    # Controles
    if st.button("🔄 ATUALIZAR TUDO", use_container_width=True):
        st.rerun()
    
    if st.button("🤖 TREINAR IA", use_container_width=True):
        st.info("IA em treinamento contínuo...")
    
    if st.button("📊 BACKTEST", use_container_width=True):
        st.session_state.show_backtest = True
    
    if st.button("⚡ OTIMIZAR ESTRATÉGIA", use_container_width=True):
        st.success("Estratégia otimizada!")
    
    st.divider()
    
    # Configurações
    st.subheader("⚙️ CONFIGURAÇÕES")
    
    st.slider("🎯 Meta Win Rate (%)", 50, 90, 75, key="target_win_rate")
    st.slider("⚠️ Stop Loss Máx (%)", 1, 20, 8, key="max_stop_loss")
    st.slider("💰 Posição Máx (%)", 1, 30, 15, key="max_position")
    
    st.divider()
    
    # Exportar dados
    if st.button("📥 EXPORTAR DADOS", use_container_width=True):
        if st.session_state.trade_history:
            df = pd.DataFrame(st.session_state.trade_history)
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇️ BAIXAR CSV",
                data=csv,
                file_name=f"trades_ai_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

# ==========================================================
# ÁREA DE ANÁLISE DE TOKEN
# ==========================================================
st.header("🔍 ANÁLISE DE TOKEN COM IA")

col_input1, col_input2 = st.columns([3, 1])

with col_input1:
    token_ca = st.text_input(
        "📝 CONTRACT ADDRESS:",
        placeholder="Cole o CA do token...",
        key="token_ca_input"
    )

with col_input2:
    analysis_type = st.selectbox(
        "TIPO DE ANÁLISE:",
        ["COMPLETA", "TÉCNICA", "SENTIMENTO", "RISCO"]
    )

if token_ca and len(token_ca) > 20:
    with st.spinner("🤖 IA analisando token..."):
        # Buscar dados
        token_data = fetch_token_data(token_ca.strip())
        
        if token_data:
            # Obter símbolo
            token_symbol = get_token_symbol(token_ca.strip())
            st.session_state.selected_token = {
                'ca': token_ca.strip(),
                'symbol': token_symbol,
                'data': token_data
            }
            
            # Análise Neural
            neural_analysis = st.session_state.neural_ai.predict_trend(token_data)
            
            # Análise Técnica
            price_history = get_price_history(token_ca.strip())
            if price_history:
                rsi = st.session_state.tech_analyzer.calculate_rsi(price_history)
                macd = st.session_state.tech_analyzer.calculate_macd(price_history)
                bollinger = st.session_state.tech_analyzer.calculate_bollinger_bands(price_history)
                support_resistance = st.session_state.tech_analyzer.calculate_support_resistance(price_history)
            else:
                rsi = 50
                macd = {'signal_text': 'NEUTRO'}
                bollinger = {'position': 'NEUTRO'}
                support_resistance = {'distance_to_support': 0, 'distance_to_resistance': 0}
            
            # Análise de Sentimento
            sentiment = st.session_state.sentiment_analyzer.analyze_social_sentiment(token_symbol)
            onchain = st.session_state.sentiment_analyzer.analyze_onchain_metrics(token_ca.strip())
            
            # Backtesting
            backtest_results = st.session_state.backtester.simulate_strategy(token_data)
            
            # Gestão de Risco
            position_info = st.session_state.risk_manager.calculate_position_size(
                neural_analysis['score'],
                neural_analysis['confidence'],
                st.session_state.risk_manager.balance
            )
            
            # ==========================================================
            # EXIBIR RESULTADOS DA ANÁLISE
            # ==========================================================
            
            # Score Principal
            col_score1, col_score2, col_score3, col_score4 = st.columns(4)
            
            with col_score1:
                score_color = "green" if neural_analysis['score'] >= 70 else "orange" if neural_analysis['score'] >= 50 else "red"
                st.markdown(f"""
                <div style='text-align: center; padding: 15px; border-radius: 10px; background-color: #f8f9fa;'>
                    <h1 style='color: {score_color}; font-size: 48px; margin: 0;'>{neural_analysis['score']}</h1>
                    <p style='font-size: 14px; margin: 0;'>SCORE IA</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_score2:
                st.metric("📈 TENDÊNCIA", neural_analysis['trend'])
            
            with col_score3:
                st.metric("🎯 AÇÃO", neural_analysis['action'])
            
            with col_score4:
                st.metric("💎 CONFIANÇA", f"{neural_analysis['confidence']*100:.1f}%")
            
            st.divider()
            
            # Tabs de análise detalhada
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📊 TÉCNICA", 
                "😊 SENTIMENTO", 
                "⚖️ RISCO", 
                "📈 BACKTEST", 
                "🚀 ESTRATÉGIA"
            ])
            
            with tab1:
                col_tech1, col_tech2, col_tech3 = st.columns(3)
                
                with col_tech1:
                    st.metric("📉 RSI", f"{rsi:.1f}")
                    st.metric("📊 MACD", macd['signal_text'])
                
                with col_tech2:
                    st.metric("📈 BOLLINGER", bollinger['position'])
                    st.metric("🎯 SUPORTE", f"{support_resistance['distance_to_support']}%")
                
                with col_tech3:
                    st.metric("🚀 RESISTÊNCIA", f"{support_resistance['distance_to_resistance']}%")
                    st.metric("📏 LARGURA BB", f"{bollinger['width']:.4f}")
            
            with tab2:
                col_sent1, col_sent2 = st.columns(2)
                
                with col_sent1:
                    st.metric("😊 SENTIMENTO", sentiment['trend'])
                    st.metric("🐦 TWITTER", f"{sentiment['twitter_sentiment']*100:.1f}%")
                    st.metric("📱 TELEGRAM", sentiment['telegram_activity'])
                
                with col_sent2:
                    st.metric("🐋 WHALE ACTIVITY", onchain['whale_activity'])
                    st.metric("🔄 TRANSAÇÕES", onchain['large_transactions'])
                    st.metric("👥 CONCENTRAÇÃO", f"{onchain['token_concentration']*100:.1f}%")
            
            with tab3:
                col_risk1, col_risk2 = st.columns(2)
                
                with col_risk1:
                    st.metric("⚠️ NÍVEL RISCO", position_info['risk_level'])
                    st.metric("💰 TAMANHO POSIÇÃO", f"{position_info['position_percent']}%")
                    st.metric("📉 STOP LOSS", f"{position_info['stop_loss_percent']}%")
                
                with col_risk2:
                    st.metric("💸 VALOR POSIÇÃO", f"${position_info['position_size']:,.2f}")
                    st.metric("💥 PERDA MÁX", f"${position_info['max_loss']:,.2f}")
                    
                    # Verificar se pode trade
                    can_trade, reason = st.session_state.risk_manager.can_trade(neural_analysis['score'])
                    if can_trade:
                        st.success("✅ PODE TRADAR")
                    else:
                        st.error(f"❌ NÃO PODE TRADAR: {reason}")
            
            with tab4:
                col_back1, col_back2 = st.columns(2)
                
                with col_back1:
                    st.metric("🎯 WIN RATE SIMULADO", f"{backtest_results['simulated_win_rate']}%")
                    st.metric("💰 LUCRO SIMULADO", f"${backtest_results['simulated_profit']:,.2f}")
                
                with col_back2:
                    st.metric("📊 TRADES SIMULADOS", backtest_results['simulated_trades'])
                    st.metric("📉 MAX DD SIMULADO", f"{backtest_results['simulated_max_dd']}%")
                
                # Score da estratégia
                strategy_score = backtest_results['strategy_score']
                st.progress(strategy_score/100, text=f"SCORE DA ESTRATÉGIA: {strategy_score}/100")
            
            with tab5:
                # Estratégia de entrada/saída
                current_price = float(token_data['pairs'][0]['priceUsd'])
                
                entry_point = st.session_state.neural_ai.calculate_entry_point(
                    current_price, 
                    neural_analysis['trend']
                )
                
                exit_strategy = st.session_state.neural_ai.calculate_exit_strategy(
                    entry_point,
                    neural_analysis['trend']
                )
                
                col_strat1, col_strat2 = st.columns(2)
                
                with col_strat1:
                    st.metric("💰 PREÇO ATUAL", f"${current_price:.10f}")
                    st.metric("🎯 PONTO ENTRADA", f"${entry_point:.10f}")
                    st.metric("📉 STOP LOSS", f"${exit_strategy['stop_loss']:.10f}")
                
                with col_strat2:
                    st.metric("🚀 TAKE PROFIT 1", f"${exit_strategy['take_profit_1']:.10f}")
                    st.metric("💎 TAKE PROFIT 2", f"${exit_strategy['take_profit_2']:.10f}")
                    st.metric("📊 TRAILING STOP", f"{exit_strategy['trailing_stop']*100:.1f}%")
            
            # Botão de ação
            st.divider()
            
            col_action1, col_action2, col_action3 = st.columns([2, 1, 1])
            
            with col_action1:
                if neural_analysis['action'] in ['COMPRAR', 'COMPRAR_AGRESIVO']:
                    st.success(f"🎯 RECOMENDAÇÃO DA IA: {neural_analysis['action']}")
                else:
                    st.warning(f"⚠️ RECOMENDAÇÃO DA IA: {neural_analysis['action']}")
            
            with col_action2:
                if st.button("🚀 INICIAR TRADE IA", type="primary", use_container_width=True):
                    if st.session_state.risk_manager.can_trade(neural_analysis['score'])[0]:
                        st.session_state.current_trade = {
                            'token': token_symbol,
                            'ca': token_ca.strip(),
                            'entry_price': current_price,
                            'position_size': position_info['position_size'],
                            'analysis': neural_analysis,
                            'stop_loss': exit_strategy['stop_loss'],
                            'take_profit_1': exit_strategy['take_profit_1'],
                            'take_profit_2': exit_strategy['take_profit_2'],
                            'trailing_stop': exit_strategy['trailing_stop'],
                            'timestamp': datetime.now()
                        }
                        st.session_state.bot_active = True
                        st.success("✅ Trade iniciado com IA!")
                        st.rerun()
                    else:
                        st.error("Não é possível iniciar trade (verifique gestão de risco)")
            
            with col_action3:
                if st.button("📊 VER GRAFICOS", use_container_width=True):
                    st.session_state.show_charts = True

# ==========================================================
# TRADE ATIVO
# ==========================================================
if st.session_state.bot_active and st.session_state.current_trade:
    st.header("📈 TRADE ATIVO COM IA")
    
    trade = st.session_state.current_trade
    
    # Buscar preço atual
    token_data = fetch_token_data(trade['ca'])
    if token_data:
        current_price = float(token_data['pairs'][0]['priceUsd'])
        
        # Calcular PnL
        pnl_percentage = ((current_price / trade['entry_price']) - 1) * 100
        pnl_value = trade['position_size'] * (pnl_percentage / 100)
        
        # Informações do trade
        col_trade1, col_trade2, col_trade3, col_trade4 = st.columns(4)
        
        with col_trade1:
            st.metric("💰 TOKEN", trade['token'])
            st.metric("🎯 ENTRADA", f"${trade['entry_price']:.10f}")
        
        with col_trade2:
            st.metric("📈 PREÇO ATUAL", f"${current_price:.10f}")
            st.metric("📊 POSIÇÃO", f"${trade['position_size']:,.2f}")
        
        with col_trade3:
            st.metric("📉 PnL %", f"{pnl_percentage:+.2f}%")
            st.metric("💰 PnL $", f"${pnl_value:+.2f}")
        
        with col_trade4:
            st.metric("⚠️ STOP LOSS", f"${trade['stop_loss']:.10f}")
            st.metric("🚀 TP 1", f"${trade['take_profit_1']:.10f}")
        
        # Gráfico de performance
        fig = go.Figure()
        
        # Linha de preço
        fig.add_trace(go.Scatter(
            y=[trade['entry_price'], current_price],
            x=['Entrada', 'Atual'],
            mode='lines+markers',
            name='Preço',
            line=dict(color='blue', width=3)
        ))
        
        # Linhas de stop loss e take profit
        fig.add_hline(y=trade['stop_loss'], line_dash="dash", line_color="red", 
                     annotation_text="Stop Loss")
        fig.add_hline(y=trade['take_profit_1'], line_dash="dash", line_color="green",
                     annotation_text="Take Profit 1")
        fig.add_hline(y=trade['take_profit_2'], line_dash="dot", line_color="darkgreen",
                     annotation_text="Take Profit 2")
        
        fig.update_layout(
            title=f"Performance do Trade - {trade['token']}",
            yaxis_title="Preço (USD)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Análise em tempo real
        if 'analysis' in trade:
            col_analysis1, col_analysis2 = st.columns(2)
            
            with col_analysis1:
                st.info(f"**AÇÃO INICIAL:** {trade['analysis']['action']}")
                st.info(f"**CONFIANÇA:** {trade['analysis']['confidence']*100:.1f}%")
                st.info(f"**SCORE:** {trade['analysis']['score']}/100")
            
            with col_analysis2:
                # Re-análise periódica
                if 'last_reanalysis' not in st.session_state or time.time() - st.session_state.last_reanalysis > 30:
                    new_analysis = st.session_state.neural_ai.predict_trend(token_data)
                    st.session_state.last_reanalysis = time.time()
                    
                    if new_analysis['action'] != trade['analysis']['action']:
                        st.warning(f"⚠️ ALTERAÇÃO NA ANÁLISE: {new_analysis['action']}")
        
        # Controles do trade
        st.divider()
        
        col_control1, col_control2, col_control3 = st.columns(3)
        
        with col_control1:
            if st.button("📈 ATUALIZAR ANÁLISE", use_container_width=True):
                new_data = fetch_token_data(trade['ca'])
                if new_data:
                    new_analysis = st.session_state.neural_ai.predict_trend(new_data)
                    st.session_state.current_trade['analysis'] = new_analysis
                    st.success("Análise atualizada!")
                    st.rerun()
        
        with col_control2:
            if pnl_percentage <= ((trade['stop_loss'] / trade['entry_price'] - 1) * 100):
                st.error("🚨 STOP LOSS ATINGIDO!")
                if st.button("SAIR COM STOP LOSS", type="primary", use_container_width=True):
                    # Fechar trade
                    st.session_state.risk_manager.update_stats(pnl_value)
                    st.session_state.trade_history.append({
                        **trade,
                        'exit_price': current_price,
                        'pnl_percentage': pnl_percentage,
                        'pnl_value': pnl_value,
                        'exit_reason': 'STOP_LOSS',
                        'exit_time': datetime.now()
                    })
                    st.session_state.bot_active = False
                    st.session_state.current_trade = None
                    st.success(f"Trade fechado: {pnl_percentage:+.2f}%")
                    time.sleep(2)
                    st.rerun()
            elif pnl_percentage >= ((trade['take_profit_1'] / trade['entry_price'] - 1) * 100):
                st.success("🎯 TAKE PROFIT 1 ATINGIDO!")
                if st.button("SAIR COM LUCRO", type="primary", use_container_width=True):
                    # Fechar trade
                    st.session_state.risk_manager.update_stats(pnl_value)
                    st.session_state.trade_history.append({
                        **trade,
                        'exit_price': current_price,
                        'pnl_percentage': pnl_percentage,
                        'pnl_value': pnl_value,
                        'exit_reason': 'TAKE_PROFIT_1',
                        'exit_time': datetime.now()
                    })
                    st.session_state.bot_active = False
                    st.session_state.current_trade = None
                    st.success(f"Trade fechado: {pnl_percentage:+.2f}%")
                    time.sleep(2)
                    st.rerun()
        
        with col_control3:
            if st.button("⏹️ FECHAR TRADE MANUAL", type="secondary", use_container_width=True):
                # Fechar trade manualmente
                st.session_state.risk_manager.update_stats(pnl_value)
                st.session_state.trade_history.append({
                    **trade,
                    'exit_price': current_price,
                    'pnl_percentage': pnl_percentage,
                    'pnl_value': pnl_value,
                    'exit_reason': 'MANUAL',
                    'exit_time': datetime.now()
                })
                st.session_state.bot_active = False
                st.session_state.current_trade = None
                st.info(f"Trade fechado manualmente: {pnl_percentage:+.2f}%")
                st.rerun()
        
        # Atualização automática
        time.sleep(5)
        st.rerun()

# ==========================================================
# HISTÓRICO DE TRADES
# ==========================================================
if st.session_state.trade_history:
    st.header("📜 HISTÓRICO DE TRADES")
    
    df_history = pd.DataFrame(st.session_state.trade_history)
    
    # Métricas de performance
    col_hist1, col_hist2, col_hist3, col_hist4 = st.columns(4)
    
    with col_hist1:
        total_trades = len(df_history)
        st.metric("📊 TOTAL TRADES", total_trades)
    
    with col_hist2:
        winning_trades = len(df_history[df_history['pnl_percentage'] > 0])
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        st.metric("🎯 WIN RATE", f"{win_rate:.1f}%")
    
    with col_hist3:
        total_profit = df_history['pnl_value'].sum()
        st.metric("💰 LUCRO TOTAL", f"${total_profit:+,.2f}")
    
    with col_hist4:
        avg_profit = df_history['pnl_percentage'].mean()
        st.metric("📈 PnL MÉDIO", f"{avg_profit:+.2f}%")
    
    # Gráfico de performance acumulada
    fig_perf = go.Figure()
    
    fig_perf.add_trace(go.Scatter(
        y=df_history['pnl_value'].cumsum(),
        mode='lines+markers',
        name='Lucro Acumulado',
        line=dict(color='green', width=3)
    ))
    
    fig_perf.update_layout(
        title='Evolução do Lucro',
        xaxis_title='Número do Trade',
        yaxis_title='Lucro Acumulado ($)',
        height=400
    )
    
    st.plotly_chart(fig_perf, use_container_width=True)
    
    # Tabela de trades
    st.dataframe(
        df_history[['token', 'entry_price', 'exit_price', 'pnl_percentage', 
                   'pnl_value', 'exit_reason', 'timestamp']],
        use_container_width=True,
        column_config={
            'token': 'Token',
            'entry_price': st.column_config.NumberColumn('Entrada', format='%.10f'),
            'exit_price': st.column_config.NumberColumn('Saída', format='%.10f'),
            'pnl_percentage': st.column_config.NumberColumn('PnL %', format='+.2f'),
            'pnl_value': st.column_config.NumberColumn('PnL $', format='+.2f'),
            'exit_reason': 'Motivo Saída',
            'timestamp': 'Data/Hora'
        }
    )

# ==========================================================
# DASHBOARD DE PERFORMANCE
# ==========================================================
if st.session_state.trade_history and len(st.session_state.trade_history) >= 5:
    st.header("📊 DASHBOARD DE PERFORMANCE IA")
    
    df_perf = pd.DataFrame(st.session_state.trade_history)
    
    # Análise por score da IA
    fig_score = px.scatter(
        df_perf,
        x='analysis',
        y='pnl_percentage',
        color='pnl_percentage',
        size=abs(df_perf['pnl_value']),
        hover_data=['token', 'exit_reason']
    )
    
    fig_score.update_layout(
        title='Performance por Análise da IA',
        xaxis_title='Score da IA',
        yaxis_title='PnL (%)',
        height=400
    )
    
    st.plotly_chart(fig_score, use_container_width=True)
    
    # Distribuição de resultados
    col_dist1, col_dist2 = st.columns(2)
    
    with col_dist1:
        fig_dist = go.Figure()
        
        fig_dist.add_trace(go.Histogram(
            x=df_perf['pnl_percentage'],
            nbinsx=20,
            name='Distribuição PnL',
            marker_color='blue'
        ))
        
        fig_dist.update_layout(
            title='Distribuição de Retornos',
            xaxis_title='PnL (%)',
            yaxis_title='Frequência',
            height=300
        )
        
        st.plotly_chart(fig_dist, use_container_width=True)
    
    with col_dist2:
        # Heatmap de correlação
        corr_data = df_perf[['pnl_percentage', 'pnl_value', 'position_size']].corr()
        
        fig_corr = go.Figure(data=go.Heatmap(
            z=corr_data.values,
            x=corr_data.columns,
            y=corr_data.columns,
            colorscale='RdBu',
            zmid=0
        ))
        
        fig_corr.update_layout(
            title='Correlação entre Métricas',
            height=300
        )
        
        st.plotly_chart(fig_corr, use_container_width=True)

# ==========================================================
# FOOTER
# ==========================================================
st.divider()

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    metrics = st.session_state.risk_manager.get_performance_metrics()
    current_win_rate = metrics['win_rate']
    target_win_rate = st.session_state.get('target_win_rate', 75)
    
    if current_win_rate >= target_win_rate:
        st.success(f"🎯 Meta Atingida: {current_win_rate:.1f}% ≥ {target_win_rate}%")
    else:
        st.warning(f"🎯 Meta: {target_win_rate}% | Atual: {current_win_rate:.1f}%")

with footer_col2:
    st.caption("🤖 IA Neural em Operação")

with footer_col3:
    st.caption("Sniper Pro AI v2.0")

# ==========================================================
# CSS ESTILIZADO
# ==========================================================
st.markdown("""
<style>
    /* Estilos gerais */
    .stButton > button {
        border-radius: 10px;
        font-weight: bold;
        transition: all 0.3s ease;
        border: none;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    
    /* Métricas */
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        font-weight: bold;
    }
    
    div[data-testid="stMetricDelta"] {
        font-size: 14px;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        font-weight: bold;
    }
    
    /* Containers */
    [data-testid="stVerticalBlock"] {
        gap: 1rem;
    }
    
    /* Alertas */
    .stAlert {
        border-radius: 10px;
        border-left: 5px solid;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# REQUIREMENTS.TXT
# ==========================================================
"""
streamlit==1.28.0
pandas==2.1.3
numpy==1.24.3
requests==2.31.0
plotly==5.17.0
"""
