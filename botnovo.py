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
import google.generativeai as genai  # Para Gemini
# Para DeepSeek (opcional): import openai
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
# CONFIGURAÇÃO DA IA (ESCOLHA UMA)
# ==========================================================
class IAAnalyzer:
    """Analisador IA para decisões de trade"""
    
    def __init__(self, ia_type="gemini", api_key=None):
        self.ia_type = ia_type
        
        if ia_type == "gemini" and api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        elif ia_type == "deepseek" and api_key:
            # Configuração para DeepSeek
            import openai
            openai.api_key = api_key
            openai.api_base = "https://api.deepseek.com/v1"
            self.client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        else:
            self.model = None
    
    def analyze_token(self, token_data: Dict, price_history: List[float] = None) -> Dict:
        """Analisa token usando IA"""
        
        if not self.model and self.ia_type != "deepseek":
            return self._get_fallback_analysis()
        
        try:
            # Preparar prompt com dados do token
            prompt = self._create_analysis_prompt(token_data, price_history)
            
            if self.ia_type == "gemini":
                response = self.model.generate_content(prompt)
                analysis_text = response.text
            else:  # deepseek
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "Você é um especialista em trading de criptomoedas."},
                        {"role": "user", "content": prompt}
                    ]
                )
                analysis_text = response.choices[0].message.content
            
            # Extrair informações da resposta
            return self._parse_ia_response(analysis_text, token_data)
            
        except Exception as e:
            st.error(f"Erro na análise IA: {e}")
            return self._get_fallback_analysis()
    
    def _create_analysis_prompt(self, token_data: Dict, price_history: List[float]) -> str:
        """Cria prompt para a IA"""
        
        symbol = token_data.get('symbol', 'TOKEN')
        price = float(token_data.get('pairs', [{}])[0].get('priceUsd', 0))
        volume_24h = float(token_data.get('pairs', [{}])[0].get('volume', {}).get('h24', 0))
        liquidity = float(token_data.get('pairs', [{}])[0].get('liquidity', {}).get('usd', 0))
        price_change = float(token_data.get('pairs', [{}])[0].get('priceChange', {}).get('h24', 0))
        
        # Dados de transações
        txns = token_data.get('pairs', [{}])[0].get('txns', {}).get('h24', {})
        buys = txns.get('buys', 0)
        sells = txns.get('sells', 0)
        
        prompt = f"""
        ANALISE DE TOKEN PARA TRADING - RESPONDA APENAS COM JSON

        DADOS DO TOKEN:
        - Símbolo: {symbol}
        - Preço atual: ${price}
        - Volume 24h: ${volume_24h:,.2f}
        - Liquidez: ${liquidity:,.2f}
        - Variação 24h: {price_change}%
        - Compras 24h: {buys}
        - Vendas 24h: {sells}

        ANALISE ESTE TOKEN E RETORNE UM OBJETO JSON COM:
        1. decision: "BUY", "HOLD" ou "AVOID"
        2. confidence_score: 0.0 a 1.0
        3. reasoning: breve explicação (máximo 50 palavras)
        4. suggested_stop_loss_percent: -5 a -20
        5. suggested_take_profit_percent: 10 a 50
        6. risk_level: "LOW", "MEDIUM", "HIGH"
        7. position_size_percent: 1 a 20 (percentual do capital)
        8. time_frame: "SHORT" (minutos/horas), "MEDIUM" (horas/dias), "LONG" (dias/semanas)

        CONSIDERE:
        - Volume acima de $50k é bom, acima de $100k é excelente
        - Liquidez acima de $20k é aceitável
        - Relação compra/venda > 1.5 é positivo
        - Variação muito alta (>50%) pode ser pump
        - Combine análise técnica com fundamentos

        RESPOSTA APENAS EM JSON, NADA MAIS:
        """
        
        return prompt
    
    def _parse_ia_response(self, response: str, token_data: Dict) -> Dict:
        """Parseia resposta da IA"""
        
        try:
            # Extrair JSON da resposta
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != 0:
                json_str = response[json_start:json_end]
                analysis = json.loads(json_str)
                
                # Garantir todos os campos
                defaults = {
                    'decision': 'HOLD',
                    'confidence_score': 0.5,
                    'reasoning': 'Análise padrão',
                    'suggested_stop_loss_percent': -10,
                    'suggested_take_profit_percent': 20,
                    'risk_level': 'MEDIUM',
                    'position_size_percent': 5,
                    'time_frame': 'SHORT'
                }
                
                for key, value in defaults.items():
                    if key not in analysis:
                        analysis[key] = value
                
                return analysis
                
        except Exception:
            pass
        
        return self._get_fallback_analysis()
    
    def _get_fallback_analysis(self) -> Dict:
        """Análise de fallback se IA falhar"""
        return {
            'decision': 'HOLD',
            'confidence_score': 0.5,
            'reasoning': 'Sistema padrão - IA indisponível',
            'suggested_stop_loss_percent': -10,
            'suggested_take_profit_percent': 20,
            'risk_level': 'MEDIUM',
            'position_size_percent': 5,
            'time_frame': 'SHORT'
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
        """Cria um novo trade com parâmetros definidos"""
        
        trade = {
            'id': len(self.active_trades) + 1,
            'symbol': token_data.get('symbol', 'TOKEN'),
            'ca': token_data.get('ca', ''),
            'entry_price': entry_price,
            'current_price': entry_price,
            'position_size': position_size,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'ia_analysis': ia_analysis,
            'status': 'ACTIVE',
            'entry_time': datetime.now(),
            'max_profit_percent': 0.0,
            'current_profit_percent': 0.0,
            'exit_price': None,
            'exit_time': None,
            'exit_reason': None,
            'trailing_stop_activated': False,
            'trailing_stop_price': stop_loss,
            'risk_level': ia_analysis.get('risk_level', 'MEDIUM') if ia_analysis else 'MEDIUM'
        }
        
        self.active_trades.append(trade)
        return trade
    
    def update_trade_prices(self, ca: str, current_price: float):
        """Atualiza preços de todos os trades do token"""
        for trade in self.active_trades:
            if trade['ca'] == ca and trade['status'] == 'ACTIVE':
                trade['current_price'] = current_price
                
                trade['current_profit_percent'] = (
                    (current_price - trade['entry_price']) / trade['entry_price']
                ) * 100
                
                if trade['current_profit_percent'] > trade['max_profit_percent']:
                    trade['max_profit_percent'] = trade['current_profit_percent']
                
                self._update_trailing_stop(trade, current_price)
    
    def _update_trailing_stop(self, trade: Dict, current_price: float):
        """Atualiza trailing stop dinâmico"""
        if trade['max_profit_percent'] >= 5.0:
            trail_distance = trade['max_profit_percent'] * 0.3
            new_stop = trade['entry_price'] * (1 + (trade['max_profit_percent'] - trail_distance) / 100)
            
            if new_stop > trade['trailing_stop_price']:
                trade['trailing_stop_price'] = new_stop
                trade['trailing_stop_activated'] = True
    
    def check_exit_conditions(self, trade: Dict) -> Tuple[bool, str, float]:
        """Verifica condições de saída do trade"""
        
        current_price = trade['current_price']
        entry_price = trade['entry_price']
        
        # Níveis de take profit baseados na análise de risco
        risk_level = trade.get('risk_level', 'MEDIUM')
        
        if risk_level == 'LOW':
            tp_levels = [1.05, 1.08, 1.12, 1.15]
        elif risk_level == 'HIGH':
            tp_levels = [1.10, 1.15, 1.25, 1.35]
        else:  # MEDIUM
            tp_levels = [1.08, 1.12, 1.18, 1.25]
        
        for tp_multiplier in tp_levels:
            tp_price = entry_price * tp_multiplier
            if current_price >= tp_price:
                return True, f"TAKE_PROFIT_{int((tp_multiplier-1)*100)}%", current_price
        
        # Stop loss conditions
        if current_price <= trade['stop_loss']:
            return True, "STOP_LOSS_ORIGINAL", current_price
        
        if trade['current_profit_percent'] <= -10.0:
            return True, "STOP_LOSS_10%", current_price
        
        if trade['trailing_stop_activated'] and current_price <= trade['trailing_stop_price']:
            return True, "TRAILING_STOP", current_price
        
        if trade['max_profit_percent'] >= 20.0 and trade['current_profit_percent'] <= trade['max_profit_percent'] * 0.5:
            return True, "DYNAMIC_STOP", current_price
        
        return False, "", 0.0
    
    def execute_auto_exit(self):
        """Executa saídas automáticas para todos os trades ativos"""
        closed_trades = []
        
        for trade in self.active_trades[:]:
            if trade['status'] == 'ACTIVE':
                should_exit, reason, exit_price = self.check_exit_conditions(trade)
                
                if should_exit:
                    trade['status'] = 'CLOSED'
                    trade['exit_price'] = exit_price
                    trade['exit_time'] = datetime.now()
                    trade['exit_reason'] = reason
                    
                    profit_percent = ((exit_price - trade['entry_price']) / trade['entry_price']) * 100
                    profit_value = trade['position_size'] * (profit_percent / 100)
                    
                    trade['final_profit_percent'] = profit_percent
                    trade['final_profit_value'] = profit_value
                    
                    self.performance['total_trades'] += 1
                    if profit_percent > 0:
                        self.performance['winning_trades'] += 1
                    self.performance['total_profit'] += profit_value
                    
                    if profit_value > 0:
                        self.performance['max_profit'] = max(self.performance['max_profit'], profit_value)
                    else:
                        self.performance['max_loss'] = min(self.performance['max_loss'], profit_value)
                    
                    self.trade_history.append(trade.copy())
                    self.active_trades.remove(trade)
                    
                    closed_trades.append(trade)
        
        return closed_trades
    
    def get_performance_stats(self) -> Dict:
        """Retorna estatísticas de performance"""
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
            return default_stats

# ==========================================================
# SISTEMA DE DECISÃO AUTOMÁTICA COM IA
# ==========================================================
class AutoDecisionEngine:
    """Motor de decisão automática com IA"""
    
    def __init__(self, ia_analyzer=None):
        self.min_confidence = 0.7
        self.max_position_percent = 20
        self.risk_reward_ratio = 2.0
        self.ia_analyzer = ia_analyzer
    
    def analyze_entry_signal(self, token_data: Dict, current_price: float) -> Dict:
        """Analisa se deve entrar no trade usando IA"""
        
        # Usar IA se disponível
        ia_analysis = None
        if self.ia_analyzer:
            ia_analysis = self.ia_analyzer.analyze_token(token_data)
            confidence = ia_analysis.get('confidence_score', 0.5)
            
            if confidence >= self.min_confidence and ia_analysis.get('decision') == 'BUY':
                # Usar parâmetros sugeridos pela IA
                stop_loss_pct = ia_analysis.get('suggested_stop_loss_percent', -10)
                take_profit_pct = ia_analysis.get('suggested_take_profit_percent', 20)
                position_pct = ia_analysis.get('position_size_percent', 5)
                
                stop_loss = current_price * (1 + stop_loss_pct/100)
                take_profit = current_price * (1 + take_profit_pct/100)
                
                return {
                    'should_enter': True,
                    'confidence': confidence,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'position_percent': min(position_pct, self.max_position_percent),
                    'risk_reward': (take_profit - current_price) / (current_price - stop_loss),
                    'ia_analysis': ia_analysis,
                    'decision_type': 'IA_RECOMMENDED'
                }
        
        # Fallback para análise técnica tradicional
        analysis_score = self._calculate_technical_score(token_data)
        
        if analysis_score >= self.min_confidence:
            stop_loss = current_price * 0.90
            take_profit = current_price * 1.20
            
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
                'risk_reward': (take_profit - current_price) / (current_price - stop_loss),
                'ia_analysis': ia_analysis,
                'decision_type': 'TECHNICAL'
            }
        
        return {
            'should_enter': False, 
            'confidence': analysis_score,
            'ia_analysis': ia_analysis
        }
    
    def _calculate_technical_score(self, token_data: Dict) -> float:
        """Calcula score técnico"""
        try:
            factors = []
            
            volume = float(token_data.get('pairs', [{}])[0].get('volume', {}).get('h24', 0))
            if volume > 100000:
                factors.append(0.8)
            elif volume > 50000:
                factors.append(0.6)
            elif volume > 10000:
                factors.append(0.4)
            else:
                factors.append(0.2)
            
            liquidity = float(token_data.get('pairs', [{}])[0].get('liquidity', {}).get('usd', 0))
            if liquidity > 50000:
                factors.append(0.9)
            elif liquidity > 20000:
                factors.append(0.7)
            elif liquidity > 5000:
                factors.append(0.5)
            else:
                factors.append(0.3)
            
            price_change = float(token_data.get('pairs', [{}])[0].get('priceChange', {}).get('h24', 0))
            if 5 < price_change < 30:
                factors.append(0.8)
            elif price_change > 0:
                factors.append(0.6)
            else:
                factors.append(0.4)
            
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
            
            return round(np.mean(factors), 2)
            
        except:
            return 0.0

# ==========================================================
# INICIALIZAÇÃO DO STREAMLIT
# ==========================================================
# Inicializar sistemas
if 'trade_monitor' not in st.session_state:
    st.session_state.trade_monitor = AutoTradeMonitor()

if 'ia_analyzer' not in st.session_state:
    # Configurar IA (escolha uma)
    ia_type = "gemini"  # Ou "deepseek"
    api_key = None  # Será configurado via interface
    
    st.session_state.ia_analyzer = IAAnalyzer(ia_type=ia_type, api_key=api_key)

if 'decision_engine' not in st.session_state:
    st.session_state.decision_engine = AutoDecisionEngine(
        ia_analyzer=st.session_state.ia_analyzer
    )

if 'auto_trading' not in st.session_state:
    st.session_state.auto_trading = False

if 'balance' not in st.session_state:
    st.session_state.balance = 1000.0

if 'token_watchlist' not in st.session_state:
    st.session_state.token_watchlist = []

if 'price_history' not in st.session_state:
    st.session_state.price_history = {}

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
                
                # Atualizar histórico de preços
                current_price = float(data['pairs'][0].get('priceUsd', 0))
                if ca not in st.session_state.price_history:
                    st.session_state.price_history[ca] = []
                
                st.session_state.price_history[ca].append({
                    'time': datetime.now(),
                    'price': current_price
                })
                
                # Manter apenas últimos 100 preços
                if len(st.session_state.price_history[ca]) > 100:
                    st.session_state.price_history[ca] = st.session_state.price_history[ca][-100:]
                
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

def get_price_history(ca: str) -> List[float]:
    """Retorna histórico de preços"""
    if ca in st.session_state.price_history:
        return [item['price'] for item in st.session_state.price_history[ca]]
    return []

# ==========================================================
# INTERFACE PRINCIPAL
# ==========================================================
st.title("🤖 SNIPER PRO AI - AUTO TRADER COM IA")
st.markdown("### Sistema Inteligente com Análise de IA")

# Sidebar
with st.sidebar:
    st.header("⚙️ CONFIGURAÇÕES")
    
    # Configuração da IA
    st.subheader("🧠 CONFIGURAÇÃO DA IA")
    
    ia_type = st.selectbox(
        "Escolha o modelo de IA:",
        ["gemini", "deepseek", "nenhum"],
        index=0
    )
    
    if ia_type != "nenhum":
        api_key = st.text_input(
            f"Chave API {ia_type.upper()}:",
            type="password",
            help=f"Obtenha em: {'ai.google.dev' if ia_type == 'gemini' else 'platform.deepseek.com'}"
        )
        
        if api_key:
            if 'ia_analyzer' not in st.session_state or st.session_state.ia_analyzer.ia_type != ia_type:
                st.session_state.ia_analyzer = IAAnalyzer(
                    ia_type=ia_type,
                    api_key=api_key
                )
                st.session_state.decision_engine = AutoDecisionEngine(
                    ia_analyzer=st.session_state.ia_analyzer
                )
                st.success(f"IA {ia_type.upper()} configurada!")
    
    st.divider()
    
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
        st.rerun()
    
    # Configurações avançadas
    st.divider()
    st.subheader("⚙️ CONFIGURAÇÕES AVANÇADAS")
    
    st.slider("🎯 CONFIANÇA MÍNIMA IA (%)", 50, 95, 70, key="min_confidence")
    st.slider("💰 POSIÇÃO MÁX (%)", 5, 30, 20, key="max_position_percent")
    st.slider("⏱️ ATUALIZAÇÃO (seg)", 5, 60, 10, key="update_interval")
    
    st.divider()
    
    # Ações rápidas
    if st.button("🔄 ATUALIZAR TUDO", use_container_width=True):
        st.rerun()
    
    if st.button("📊 EXPORTAR DADOS", use_container_width=True):
        if st.session_state.trade_monitor.trade_history:
            df = pd.DataFrame(st.session_state.trade_monitor.trade_history)
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇️ BAIXAR CSV",
                data=csv,
                file_name="trades_ia.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    if st.button("🧹 LIMPAR TUDO", use_container_width=True):
        st.session_state.trade_monitor = AutoTradeMonitor()
        st.session_state.balance = 1000.0
        st.session_state.token_watchlist = []
        st.success("Sistema reiniciado!")
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
                'last_update': datetime.now(),
                'ia_analysis': None
            }
            
            if not any(t['ca'] == token_info['ca'] for t in st.session_state.token_watchlist):
                st.session_state.token_watchlist.append(token_info)
                st.success(f"Token {token_info['symbol']} adicionado!")
                st.rerun()
            else:
                st.warning("Token já está na watchlist")
        else:
            st.error("Token não encontrado")

# Mostrar watchlist com análise IA
if st.session_state.token_watchlist:
    st.subheader("📊 TOKENS MONITORADOS")
    
    # Atualizar dados
    for token in st.session_state.token_watchlist:
        current_price = get_current_price(token['ca'])
        if current_price:
            token['last_price'] = current_price
            token['last_update'] = datetime.now()
    
    # Mostrar em colunas
    cols = st.columns(min(4, len(st.session_state.token_watchlist)))
    
    for idx, token in enumerate(st.session_state.token_watchlist[:8]):
        with cols[idx % 4]:
            with st.container(border=True, height=200):
                st.markdown(f"**{token['symbol']}**")
                st.markdown(f"`${token['last_price']:.10f}`")
                st.caption(f"Última: {token['last_update'].strftime('%H:%M:%S')}")
                
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.button("🧠 IA", key=f"ia_{token['ca']}", use_container_width=True):
                        # Executar análise IA
                        data = fetch_token_data(token['ca'])
                        if data and st.session_state.ia_analyzer:
                            price_history = get_price_history(token['ca'])
                            analysis = st.session_state.ia_analyzer.analyze_token(data, price_history)
                            token['ia_analysis'] = analysis
                            
                            if analysis.get('decision') == 'BUY':
                                st.success(f"✅ {analysis.get('confidence_score', 0)*100:.0f}% confiança")
                            else:
                                st.warning(f"⚠️ {analysis.get('reasoning', 'Sem análise')}")
                
                with col_btn2:
                    if st.button("📈 Analisar", key=f"analyze_{token['ca']}", use_container_width=True):
                        st.session_state.selected_token_ca = token['ca']
                        st.rerun()

# ==========================================================
# SEÇÃO DE ANÁLISE DETALHADA COM IA
# ==========================================================
if 'selected_token_ca' in st.session_state and st.session_state.selected_token_ca:
    st.header("🎯 ANÁLISE DETALHADA COM IA")
    
    token_data = fetch_token_data(st.session_state.selected_token_ca)
    
    if token_data:
        current_price = float(token_data['pairs'][0].get('priceUsd', 0))
        price_history = get_price_history(st.session_state.selected_token_ca)
        
        col_analysis1, col_analysis2, col_analysis3 = st.columns([2, 1, 1])
        
        with col_analysis1:
            # Análise IA
            if st.session_state.ia_analyzer:
                with st.spinner("Consultando IA..."):
                    ia_analysis = st.session_state.ia_analyzer.analyze_token(token_data, price_history)
                    
                st.markdown(f"### 🧠 ANÁLISE DA IA")
                
                # Mostrar decisão
                decision = ia_analysis.get('decision', 'HOLD')
                confidence = ia_analysis.get('confidence_score', 0.5)
                
                if decision == 'BUY':
                    st.success(f"✅ **COMPRAR** ({confidence*100:.1f}% confiança)")
                elif decision == 'HOLD':
                    st.info(f"⏸️ **MANTER** ({confidence*100:.1f}% confiança)")
                else:
                    st.error(f"❌ **EVITAR** ({confidence*100:.1f}% confiança)")
                
                st.markdown(f"**Razão:** {ia_analysis.get('reasoning', 'N/A')}")
                st.markdown(f"**Nível de Risco:** {ia_analysis.get('risk_level', 'MEDIUM')}")
                st.markdown(f"**Time Frame:** {ia_analysis.get('time_frame', 'SHORT')}")
                
                # Mostrar parâmetros sugeridos
                st.markdown("### ⚙️ PARÂMETROS SUGERIDOS")
                
                stop_loss_pct = ia_analysis.get('suggested_stop_loss_percent', -10)
                take_profit_pct = ia_analysis.get('suggested_take_profit_percent', 20)
                position_pct = ia_analysis.get('position_size_percent', 5)
                
                stop_loss_price = current_price * (1 + stop_loss_pct/100)
                take_profit_price = current_price * (1 + take_profit_pct/100)
                position_value = st.session_state.balance * (position_pct/100)
                
                col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
                
                with col_metrics1:
                    st.metric("⛔ Stop Loss", f"{stop_loss_pct}%", f"${stop_loss_price:.10f}")
                
                with col_metrics2:
                    st.metric("🎯 Take Profit", f"{take_profit_pct}%", f"${take_profit_price:.10f}")
                
                with col_metrics3:
                    st.metric("💰 Posição", f"{position_pct}%", f"${position_value:.2f}")
                
                # Botão de entrada com IA
                if decision == 'BUY' and confidence >= 0.7:
                    if st.button("🚀 ENTRAR COM RECOMENDAÇÃO DA IA", type="primary", use_container_width=True):
                        trade = st.session_state.trade_monitor.create_trade(
                            token_data=token_data,
                            position_size=position_value,
                            entry_price=current_price,
                            stop_loss=stop_loss_price,
                            take_profit=take_profit_price,
                            ia_analysis=ia_analysis
                        )
                        
                        st.session_state.balance -= position_value
                        st.success(f"Trade iniciado com IA para {token_data['symbol']}!")
                        st.rerun()
        
        with col_analysis2:
            # Análise técnica tradicional
            st.markdown("### 📊 ANÁLISE TÉCNICA")
            
            analysis = st.session_state.decision_engine.analyze_entry_signal(token_data, current_price)
            
            st.metric("💰 PREÇO", f"${current_price:.10f}")
            st.metric("🎯 CONFIANÇA", f"{analysis['confidence']*100:.1f}%")
            
            if analysis['should_enter'] and analysis['decision_type'] == 'TECHNICAL':
                st.info("📈 Sinal Técnico Positivo")
        
        with col_analysis3:
            # Dados do token
            st.markdown("### 📈 DADOS")
            
            volume = float(token_data.get('pairs', [{}])[0].get('volume', {}).get('h24', 0))
            liquidity = float(token_data.get('pairs', [{}])[0].get('liquidity', {}).get('usd', 0))
            price_change = float(token_data.get('pairs', [{}])[0].get('priceChange', {}).get('h24', 0))
            
            st.metric("📊 Volume 24h", f"${volume:,.0f}")
            st.metric("💧 Liquidez", f"${liquidity:,.0f}")
            st.metric("📈 Variação 24h", f"{price_change:.1f}%")
            
            # Entrada manual
            st.divider()
            st.markdown("### 🎮 ENTRADA MANUAL")
            
            manual_position = st.slider("Posição (%)", 1.0, 30.0, 10.0, 1.0)
            manual_stop = st.slider("Stop Loss (%)", 5.0, 30.0, 10.0, 1.0)
            manual_tp = st.slider("Take Profit (%)", 10.0, 100.0, 20.0, 5.0)
            
            if st.button("🎯 ENTRAR MANUAL", use_container_width=True):
                position_value = st.session_state.balance * (manual_position/100)
                stop_loss_price = current_price * (1 - manual_stop/100)
                take_profit_price = current_price * (1 + manual_tp/100)
                
                trade = st.session_state.trade_monitor.create_trade(
                    token_data=token_data,
                    position_size=position_value,
                    entry_price=current_price,
                    stop_loss=stop_loss_price,
                    take_profit=take_profit_price
                )
                
                st.session_state.balance -= position_value
                st.success(f"Trade manual para {token_data['symbol']}!")
                st.rerun()

# ==========================================================
# SEÇÃO DE TRADES ATIVOS
# ==========================================================
st.header("📈 TRADES ATIVOS")

if st.session_state.trade_monitor.active_trades:
    # Atualizar preços
    for trade in st.session_state.trade_monitor.active_trades:
        current_price = get_current_price(trade['ca'])
        if current_price:
            st.session_state.trade_monitor.update_trade_prices(trade['ca'], current_price)
    
    # Executar saídas automáticas
    closed_trades = st.session_state.trade_monitor.execute_auto_exit()
    
    # Mostrar trades fechados
    if closed_trades:
        st.subheader("🔒 TRADES FECHADOS")
        for trade in closed_trades[-3:]:
            profit_percent = trade.get('final_profit_percent', 0)
            
            st.info(f"""
            **{trade.get('symbol', 'TOKEN')}** - {trade.get('exit_reason', 'DESCONHECIDO')}
            • Entrada: ${trade.get('entry_price', 0):.10f}
            • Saída: ${trade.get('exit_price', 0):.10f}
            • Resultado: **{profit_percent:+.2f}%** (${trade.get('final_profit_value', 0):+.2f})
            """)
            
            # Adicionar ao saldo
            st.session_state.balance += trade.get('position_size', 0) + trade.get('final_profit_value', 0)
    
    # Mostrar trades ativos
    st.subheader("🟢 TRADES EM ANDAMENTO")
    
    cols = st.columns(3)
    
    for idx, trade in enumerate(st.session_state.trade_monitor.active_trades[:6]):
        with cols[idx % 3]:
            with st.container(border=True, height=280):
                profit_percent = trade.get('current_profit_percent', 0)
                profit_color = "🟢" if profit_percent >= 0 else "🔴"
                
                st.markdown(f"**{trade.get('symbol', 'TOKEN')}** (ID: {trade.get('id', '?')})")
                st.markdown(f"### {profit_color} {profit_percent:+.2f}%")
                
                # Informações
                st.caption(f"💰 Entrada: ${trade.get('entry_price', 0):.10f}")
                st.caption(f"📊 Atual: ${trade.get('current_price', 0):.10f}")
                st.caption(f"⛔ Stop: ${trade.get('stop_loss', 0):.10f}")
                st.caption(f"🎯 TP: ${trade.get('take_profit', 0):.10f}")
                
                if trade.get('ia_analysis'):
                    st.caption(f"🧠 IA: {trade['ia_analysis'].get('risk_level', 'N/A')}")
                
                if trade.get('trailing_stop_activated', False):
                    st.caption(f"📈 Trailing: ${trade.get('trailing_stop_price', 0):.10f}")
                
                # Botões de ação
                if st.button("⏹️ SAIR", key=f"exit_{trade.get('id', '?')}", use_container_width=True):
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
                        st.success(f"Trade fechado: {profit_percent:+.2f}%")
                        st.rerun()
else:
    st.info("Nenhum trade ativo no momento.")

# ==========================================================
# SEÇÃO DE HISTÓRICO E ESTATÍSTICAS
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
            title='Lucro Acumulado',
            xaxis_title='Número do Trade',
            yaxis_title='Lucro ($)',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

# ==========================================================
# SISTEMA DE AUTO TRADING COM IA
# ==========================================================
if st.session_state.auto_trading and st.session_state.token_watchlist:
    st.header("🤖 AUTO TRADING ATIVO")
    
    st.info(f"Monitorando {len(st.session_state.token_watchlist)} tokens...")
    
    for token in st.session_state.token_watchlist:
        # Verificar se já tem trade ativo
        active_trade = any(
            t.get('ca') == token.get('ca') and t.get('status') == 'ACTIVE' 
            for t in st.session_state.trade_monitor.active_trades
        )
        
        if not active_trade:
            # Analisar com IA
            data = fetch_token_data(token.get('ca', ''))
            if data and st.session_state.ia_analyzer:
                price_history = get_price_history(token.get('ca', ''))
                analysis = st.session_state.ia_analyzer.analyze_token(data, price_history)
                
                if analysis.get('decision') == 'BUY' and analysis.get('confidence_score', 0) >= 0.7:
                    current_price = get_current_price(token.get('ca', ''))
                    if current_price:
                        # Calcular posição
                        position_pct = analysis.get('position_size_percent', 5)
                        position_value = st.session_state.balance * (position_pct / 100)
                        
                        if position_value > 1:  # Mínimo $1
                            stop_loss_pct = analysis.get('suggested_stop_loss_percent', -10)
                            take_profit_pct = analysis.get('suggested_take_profit_percent', 20)
                            
                            stop_loss = current_price * (1 + stop_loss_pct/100)
                            take_profit = current_price * (1 + take_profit_pct/100)
                            
                            trade = st.session_state.trade_monitor.create_trade(
                                token_data=data,
                                position_size=position_value,
                                entry_price=current_price,
                                stop_loss=stop_loss,
                                take_profit=take_profit,
                                ia_analysis=analysis
                            )
                            
                            st.session_state.balance -= position_value
                            st.success(f"🤖 Auto trade para {token.get('symbol', 'TOKEN')}!")

# ==========================================================
# ATUALIZAÇÃO AUTOMÁTICA
# ==========================================================
if st.session_state.auto_trading or st.session_state.trade_monitor.active_trades:
    time.sleep(st.session_state.get('update_interval', 10))
    st.rerun()

# ==========================================================
# FOOTER
# ==========================================================
st.divider()
footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption(f"🔄 {datetime.now().strftime('%H:%M:%S')}")

with footer_col2:
    active_trades = len(st.session_state.trade_monitor.active_trades)
    st.caption(f"📈 {active_trades} trades ativos")

with footer_col3:
    st.caption("🤖 Sniper Pro AI Trader v2.0")

# ==========================================================
# CSS
# ==========================================================
st.markdown("""
<style>
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)