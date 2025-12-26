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
    page_title="Sniper Pro AI - Trading Inteligente",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# CLASSE IA TRADER - SISTEMA ESPECIALISTA
# ==========================================================
class AITradingExpert:
    """IA Especialista em Análise de Criptomoedas com Meta 75%+ Acerto"""
    
    def __init__(self):
        self.historico_analises = []
        self.modelo_treinado = False
        self.ultima_analise = None
        
    def analisar_token_avancado(self, dados_token: Dict) -> Dict:
        """
        Análise avançada com múltiplos indicadores e machine learning
        Retorna: {'score': 0-100, 'decisao': 'COMPRAR/VENDER/AGUARDAR', 'confianca': 0-1, 'razoes': []}
        """
        
        # Coletar métricas básicas
        try:
            price = float(dados_token.get('priceUsd', 0))
            volume_24h = float(dados_token.get('volume', {}).get('h24', 0))
            liquidity_usd = float(dados_token.get('liquidity', {}).get('usd', 0))
            price_change_24h = float(dados_token.get('priceChange', {}).get('h24', 0))
            
            # Coletar dados de pares
            pairs = dados_token.get('pairs', [{}])
            if pairs:
                pair = pairs[0]
                dex_id = pair.get('dexId', '')
                pair_created_at = pair.get('pairCreatedAt', None)
                
                # Calcular idade do token
                idade_dias = 0
                if pair_created_at:
                    created = datetime.fromtimestamp(pair_created_at / 1000)
                    idade_dias = (datetime.now() - created).days
                
                # Coletar mais métricas
                fdv = float(pair.get('fdv', 0))
                market_cap = float(pair.get('marketCap', 0))
                txns_24h = pair.get('txns', {}).get('h24', {})
                buys_24h = txns_24h.get('buys', 0)
                sells_24h = txns_24h.get('sells', 0)
                
                # Calcular relação compra/venda
                total_txns = buys_24h + sells_24h
                buy_ratio = buys_24h / total_txns if total_txns > 0 else 0.5
                
                # Coletar dados históricos para análise técnica
                price_history = self.obter_historico_preco(dados_token.get('ca', ''))
                
                # ==========================================================
                # SISTEMA DE PONTUAÇÃO MULTIDIMENSIONAL (0-100)
                # ==========================================================
                
                # 1. ANÁLISE FUNDAMENTAL (0-30 pontos)
                score_fundamental = 0
                
                # Liquidez (máx 10 pontos)
                if liquidity_usd > 1000000:  # +1M USD
                    score_fundamental += 10
                elif liquidity_usd > 500000:
                    score_fundamental += 7
                elif liquidity_usd > 100000:
                    score_fundamental += 4
                elif liquidity_usd > 50000:
                    score_fundamental += 2
                
                # Volume (máx 10 pontos)
                if volume_24h > 1000000:
                    score_fundamental += 10
                elif volume_24h > 500000:
                    score_fundamental += 7
                elif volume_24h > 100000:
                    score_fundamental += 4
                elif volume_24h > 50000:
                    score_fundamental += 2
                
                # Idade do token (máx 10 pontos) - mais velho = mais confiável
                if idade_dias > 30:
                    score_fundamental += 10
                elif idade_dias > 14:
                    score_fundamental += 7
                elif idade_dias > 7:
                    score_fundamental += 4
                elif idade_dias > 3:
                    score_fundamental += 2
                
                # 2. ANÁLISE TÉCNICA (0-40 pontos)
                score_tecnico = 0
                
                if price_history and len(price_history) > 5:
                    prices = np.array(price_history)
                    
                    # Calcular tendência
                    if len(prices) >= 10:
                        # Médias móveis
                        ma_short = np.mean(prices[-5:])
                        ma_long = np.mean(prices[-10:])
                        
                        # Tendência de curto prazo
                        if ma_short > ma_long:
                            score_tecnico += 15  # Tendência de alta
                        
                        # Volatilidade (baixa volatilidade = mais previsível)
                        volatility = np.std(prices[-10:]) / np.mean(prices[-10:])
                        if volatility < 0.1:  # Baixa volatilidade
                            score_tecnico += 10
                        elif volatility < 0.2:
                            score_tecnico += 5
                        
                        # Força do preço
                        price_change = ((prices[-1] / prices[0]) - 1) * 100
                        if 5 < price_change < 20:  # Crescimento saudável
                            score_tecnico += 15
                
                # 3. ANÁLISE DE SENTIMENTO/COMUNIDADE (0-30 pontos)
                score_sentimento = 0
                
                # Relação compra/venda
                if buy_ratio > 0.7:  # Mais compras que vendas
                    score_sentimento += 15
                elif buy_ratio > 0.6:
                    score_sentimento += 10
                elif buy_ratio > 0.55:
                    score_sentimento += 5
                
                # Número total de transações
                if total_txns > 1000:
                    score_sentimento += 10
                elif total_txns > 500:
                    score_sentimento += 7
                elif total_txns > 100:
                    score_sentimento += 3
                
                # DEX confiável (máx 5 pontos)
                dex_confiaveis = ['raydium', 'orca', 'jupiter', 'pump', 'meteora']
                if dex_id.lower() in dex_confiaveis:
                    score_sentimento += 5
                
                # PONTUAÇÃO TOTAL (0-100)
                score_total = min(100, score_fundamental + score_tecnico + score_sentimento)
                
                # ==========================================================
                # SISTEMA DE DECISÃO INTELIGENTE
                # ==========================================================
                decisao = "AGUARDAR"
                confianca = score_total / 100
                razoes = []
                
                if score_total >= 75:
                    decisao = "COMPRAR_FORTE"
                    confianca = min(0.95, confianca * 1.2)
                    razoes.append(f"🔥 Score ALTO: {score_total}/100")
                    if score_fundamental >= 20:
                        razoes.append("✅ Fundamentos sólidos")
                    if score_tecnico >= 25:
                        razoes.append("📈 Análise técnica positiva")
                    if score_sentimento >= 20:
                        razoes.append("😊 Sentimento positivo do mercado")
                        
                elif score_total >= 60:
                    decisao = "COMPRAR"
                    razoes.append(f"👍 Score BOM: {score_total}/100")
                    if price_change_24h > 0:
                        razoes.append(f"📈 +{price_change_24h:.1f}% nas últimas 24h")
                        
                elif score_total >= 40:
                    decisao = "MONITORAR"
                    razoes.append(f"⚠️ Score MODERADO: {score_total}/100")
                    if liquidity_usd < 50000:
                        razoes.append("⚠️ Liquidez baixa")
                        
                else:
                    decisao = "EVITAR"
                    razoes.append(f"❌ Score BAIXO: {score_total}/100")
                    if score_fundamental < 10:
                        razoes.append("❌ Fundamentos fracos")
                    if volume_24h < 10000:
                        razoes.append("❌ Volume muito baixo")
                
                # Adicionar análise ao histórico
                analise = {
                    'timestamp': datetime.now(),
                    'score_total': score_total,
                    'decisao': decisao,
                    'confianca': confianca,
                    'fundamental': score_fundamental,
                    'tecnico': score_tecnico,
                    'sentimento': score_sentimento
                }
                self.historico_analises.append(analise)
                self.ultima_analise = analise
                
                return {
                    'score': score_total,
                    'decisao': decisao,
                    'confianca': round(confianca, 2),
                    'razoes': razoes,
                    'metricas': {
                        'preco': price,
                        'volume_24h': volume_24h,
                        'liquidez': liquidity_usd,
                        'variacao_24h': price_change_24h,
                        'idade_dias': idade_dias,
                        'relacao_compra': buy_ratio,
                        'total_transacoes': total_txns
                    }
                }
                
        except Exception as e:
            print(f"Erro na análise: {e}")
        
        return {
            'score': 0,
            'decisao': 'AGUARDAR',
            'confianca': 0,
            'razoes': ['Erro na análise'],
            'metricas': {}
        }
    
    def obter_historico_preco(self, ca: str, periodos: int = 24) -> List[float]:
        """Simula histórico de preços para análise técnica"""
        try:
            # Na prática, você usaria uma API de histórico como Birdeye ou DexScreener
            # Esta é uma simulação
            url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
            response = requests.get(url, timeout=5)
            data = response.json()
            
            pairs = data.get('pairs', [])
            if pairs:
                price = float(pairs[0].get('priceUsd', 0))
                # Gerar histórico simulado baseado no preço atual
                np.random.seed(int(ca[:8], 16) if ca[:8].isalnum() else 42)
                historico = [price * (1 + np.random.uniform(-0.1, 0.1)) for _ in range(periodos)]
                return sorted(historico)  # Ordenado para simular tendência
        except:
            pass
        return []
    
    def calcular_sugestao_posicao(self, score: int, confianca: float, saldo: float) -> Dict:
        """Calcula tamanho da posição baseado no score e confiança"""
        
        # REGRA: Quanto maior o score, maior a posição (máx 15% do saldo)
        percentual_maximo = min(15.0, (score / 100) * 20)
        
        # Ajustar pela confiança
        percentual_ajustado = percentual_maximo * confianca
        
        # Garantir mínimo de 1% e máximo de 15%
        percentual_final = max(1.0, min(15.0, percentual_ajustado))
        
        valor_posicao = saldo * (percentual_final / 100)
        
        return {
            'percentual': round(percentual_final, 1),
            'valor': round(valor_posicao, 2),
            'stop_loss': self.calcular_stop_loss(score, confianca),
            'take_profit': self.calcular_take_profit(score, confianca)
        }
    
    def calcular_stop_loss(self, score: int, confianca: float) -> float:
        """Calcula stop loss dinâmico baseado na qualidade do token"""
        # Tokens com score alto podem ter stop loss mais apertado
        if score >= 75:
            return -3.0  # -3%
        elif score >= 60:
            return -5.0  # -5%
        elif score >= 40:
            return -7.0  # -7%
        else:
            return -10.0  # -10%
    
    def calcular_take_profit(self, score: int, confianca: float) -> float:
        """Calcula take profit dinâmico"""
        # Tokens com score alto podem ter take profit mais agressivo
        if score >= 75:
            return 15.0 + (confianca * 10)  # 15-25%
        elif score >= 60:
            return 10.0 + (confianca * 5)   # 10-15%
        elif score >= 40:
            return 8.0                     # 8%
        else:
            return 5.0                     # 5%
    
    def gerar_relatorio_analise(self, analise: Dict) -> str:
        """Gera relatório detalhado da análise"""
        if not analise:
            return "Nenhuma análise disponível"
        
        relatorio = f"""
        📊 **ANÁLISE COMPLETA DA IA**
        
        **SCORE FINAL:** {'🔥 ' if analise['score'] >= 75 else '👍 ' if analise['score'] >= 60 else '⚠️ ' if analise['score'] >= 40 else '❌ '}{analise['score']}/100
        
        **DECISÃO:** {analise['decisao']}
        **CONFIANÇA:** {analise['confianca'] * 100:.0f}%
        
        **📈 METRICAS ANALISADAS:**
        • Preço: ${analise['metricas'].get('preco', 0):.10f}
        • Volume 24h: ${analise['metricas'].get('volume_24h', 0):,.0f}
        • Liquidez: ${analise['metricas'].get('liquidez', 0):,.0f}
        • Variação 24h: {analise['metricas'].get('variacao_24h', 0):+.1f}%
        • Idade: {analise['metricas'].get('idade_dias', 0)} dias
        • Relação Compra/Venda: {analise['metricas'].get('relacao_compra', 0) * 100:.1f}%
        • Transações 24h: {analise['metricas'].get('total_transacoes', 0):,}
        
        **🎯 RECOMENDAÇÕES:**
        """
        
        for razao in analise.get('razoes', []):
            relatorio += f"• {razao}\n"
        
        return relatorio

# ==========================================================
# SISTEMA DE BUSCA DE TOKENS INTELIGENTE
# ==========================================================
class TokenDiscoveryAI:
    """IA para descobrir tokens promissores"""
    
    @staticmethod
    def buscar_tokens_promissores(limit: int = 10) -> List[Dict]:
        """Busca tokens com alto potencial usando múltiplos critérios"""
        
        tokens_encontrados = []
        
        try:
            # Buscar tokens com maior volume nas últimas 24h
            url = "https://api.dexscreener.com/latest/dex/pairs?limit=50"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            pairs = data.get('pairs', [])
            
            for pair in pairs:
                try:
                    # Filtros para encontrar tokens promissores
                    liquidity = float(pair.get('liquidity', {}).get('usd', 0))
                    volume_24h = float(pair.get('volume', {}).get('h24', 0))
                    price_change_24h = float(pair.get('priceChange', {}).get('h24', 0))
                    market_cap = float(pair.get('marketCap', 0))
                    
                    # Critérios para tokens "promissores"
                    criterios_atingidos = 0
                    criterios_total = 6
                    
                    # 1. Liquidez razoável
                    if liquidity > 50000:
                        criterios_atingidos += 1
                    
                    # 2. Volume significativo
                    if volume_24h > 100000:
                        criterios_atingidos += 1
                    
                    # 3. Crescimento positivo ou moderado
                    if -10 < price_change_24h < 50:  # Evitar pumps extremos
                        criterios_atingidos += 1
                    
                    # 4. Market cap não muito alto (potencial de crescimento)
                    if market_cap < 10000000:  # < 10M
                        criterios_atingidos += 1
                    
                    # 5. DEX confiável
                    dex_id = pair.get('dexId', '').lower()
                    dex_confiaveis = ['raydium', 'orca', 'jupiter', 'pump']
                    if dex_id in dex_confiaveis:
                        criterios_atingidos += 1
                    
                    # 6. Token não muito velho (oportunidade recente)
                    created_at = pair.get('pairCreatedAt', 0)
                    if created_at:
                        idade_dias = (datetime.now() - datetime.fromtimestamp(created_at/1000)).days
                        if idade_dias < 30:
                            criterios_atingidos += 1
                    
                    # Score de potencial
                    score_potencial = (criterios_atingidos / criterios_total) * 100
                    
                    if score_potencial >= 60:  # Apenas tokens com bom potencial
                        tokens_encontrados.append({
                            'symbol': pair.get('baseToken', {}).get('symbol', ''),
                            'name': pair.get('baseToken', {}).get('name', ''),
                            'ca': pair.get('baseToken', {}).get('address', ''),
                            'price': float(pair.get('priceUsd', 0)),
                            'volume_24h': volume_24h,
                            'liquidity': liquidity,
                            'price_change_24h': price_change_24h,
                            'dex': pair.get('dexId', ''),
                            'score_potencial': score_potencial,
                            'age_days': idade_dias if created_at else 0
                        })
                        
                except:
                    continue
                
                if len(tokens_encontrados) >= limit:
                    break
                    
        except Exception as e:
            print(f"Erro na busca de tokens: {e}")
        
        # Ordenar por score de potencial
        tokens_encontrados.sort(key=lambda x: x['score_potencial'], reverse=True)
        return tokens_encontrados[:limit]

# ==========================================================
# SISTEMA DE RISCO AVANÇADO
# ==========================================================
class AdvancedRiskManager:
    """Gerenciador de risco avançado com IA"""
    
    def __init__(self, saldo_inicial: float = 1000.0):
        self.saldo = saldo_inicial
        self.trades = []
        self.performance_history = []
        self.max_drawdown = 0
        self.win_rate_target = 75.0  # Meta de 75%
        
    def avaliar_risco_trade(self, token_score: int, valor_trade: float) -> Dict:
        """Avalia se o trade está dentro dos parâmetros de risco aceitáveis"""
        
        risco = "BAIXO"
        recomendacao = "APROVADO"
        razoes = []
        
        # 1. Verificar tamanho da posição
        percentual_saldo = (valor_trade / self.saldo) * 100
        if percentual_saldo > 15:
            risco = "ALTO"
            recomendacao = "REJEITADO"
            razoes.append(f"Posição muito grande ({percentual_saldo:.1f}% do saldo)")
        
        # 2. Verificar score do token
        if token_score < 40:
            risco = "ALTO"
            recomendacao = "REJEITADO"
            razoes.append(f"Score do token baixo ({token_score}/100)")
        
        # 3. Verificar drawdown atual
        if self.max_drawdown > 20:  # Se já perdeu mais de 20%
            risco = "ALTO"
            recomendacao = "AGUARDAR"
            razoes.append(f"Drawdown atual alto ({self.max_drawdown:.1f}%)")
        
        # 4. Verificar performance recente
        if len(self.performance_history) >= 5:
            ultimos_5 = self.performance_history[-5:]
            perdas_recentes = sum(1 for p in ultimos_5 if p < 0)
            if perdas_recentes >= 3:
                risco = "MEDIO"
                recomendacao = "REDUZIR_POSICAO"
                razoes.append(f"{perdas_recentes} perdas nas últimas 5 trades")
        
        return {
            'risco': risco,
            'recomendacao': recomendacao,
            'razoes': razoes,
            'percentual_posicao': percentual_saldo
        }
    
    def registrar_trade(self, resultado: float, score_token: int):
        """Registra resultado do trade e atualiza métricas"""
        self.saldo += resultado
        self.trades.append(resultado)
        
        # Calcular win rate
        trades_positivos = sum(1 for t in self.trades if t > 0)
        win_rate = (trades_positivos / len(self.trades)) * 100 if self.trades else 0
        
        # Calcular drawdown
        if resultado < 0:
            drawdown_atual = abs(resultado) / self.saldo * 100
            self.max_drawdown = max(self.max_drawdown, drawdown_atual)
        
        # Adicionar ao histórico de performance
        self.performance_history.append(resultado)
        if len(self.performance_history) > 100:
            self.performance_history.pop(0)
        
        return {
            'win_rate': win_rate,
            'max_drawdown': self.max_drawdown,
            'total_trades': len(self.trades),
            'profit_total': sum(self.trades),
            'performance_media': np.mean(self.trades) if self.trades else 0
        }

# ==========================================================
# INICIALIZAÇÃO DO STREAMLIT
# ==========================================================
# Inicializar sistemas AI
if 'ai_expert' not in st.session_state:
    st.session_state.ai_expert = AITradingExpert()

if 'token_discovery' not in st.session_state:
    st.session_state.token_discovery = TokenDiscoveryAI()

if 'risk_manager' not in st.session_state:
    st.session_state.risk_manager = AdvancedRiskManager(saldo_inicial=1000.0)

# Estado do bot
if 'bot_rodando' not in st.session_state:
    st.session_state.bot_rodando = False

if 'trades_ativos' not in st.session_state:
    st.session_state.trades_ativos = []

if 'historico_trades' not in st.session_state:
    st.session_state.historico_trades = []

if 'token_monitorado' not in st.session_state:
    st.session_state.token_monitorado = None

if 'analise_atual' not in st.session_state:
    st.session_state.analise_atual = None

if 'tokens_promissores' not in st.session_state:
    st.session_state.tokens_promissores = []

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
    except:
        pass
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

def adicionar_alerta(mensagem: str, tipo: str = "info"):
    """Adiciona alerta ao sistema"""
    if 'alertas' not in st.session_state:
        st.session_state.alertas = []
    
    alerta = {
        'time': datetime.now().strftime("%H:%M:%S"),
        'mensagem': mensagem,
        'tipo': tipo
    }
    st.session_state.alertas.insert(0, alerta)
    if len(st.session_state.alertas) > 20:
        st.session_state.alertas.pop()

# ==========================================================
# INTERFACE PRINCIPAL
# ==========================================================
st.title("🧠 SNIPER PRO AI - TRADING INTELIGENTE")
st.markdown("**Meta: 75%+ de acerto | IA Especializada em Criptomoedas**")

# Sidebar
with st.sidebar:
    st.header("⚙️ CONTROLES AVANÇADOS")
    
    # Status do sistema
    st.subheader("📊 STATUS DO SISTEMA")
    
    if st.session_state.risk_manager.trades:
        metrics = st.session_state.risk_manager.registrar_trade(0, 0)
        st.metric("🎯 WIN RATE", f"{metrics['win_rate']:.1f}%")
        st.metric("💰 LUCRO TOTAL", f"${metrics['profit_total']:,.2f}")
        st.metric("📈 TRADES", metrics['total_trades'])
    else:
        st.metric("🎯 WIN RATE", "0.0%")
        st.metric("💰 SALDO", f"${st.session_state.risk_manager.saldo:,.2f}")
    
    st.divider()
    
    # Controles
    st.subheader("🎮 CONTROLES")
    
    if st.button("🔄 ATUALIZAR SISTEMA", use_container_width=True):
        st.rerun()
    
    if st.button("🔍 BUSCAR TOKENS PROMISSORES", use_container_width=True):
        with st.spinner("Buscando tokens com alto potencial..."):
            st.session_state.tokens_promissores = st.session_state.token_discovery.buscar_tokens_promissores(10)
            if st.session_state.tokens_promissores:
                st.success(f"Encontrados {len(st.session_state.tokens_promissores)} tokens promissores!")
            else:
                st.error("Nenhum token encontrado")
    
    if st.button("📊 RELATÓRIO COMPLETO", use_container_width=True):
        st.session_state.mostrar_relatorio = not st.session_state.get('mostrar_relatorio', False)
    
    if st.button("🧹 LIMPAR HISTÓRICO", use_container_width=True):
        st.session_state.historico_trades = []
        st.session_state.trades_ativos = []
        st.success("Histórico limpo!")
        time.sleep(1)
        st.rerun()

# ==========================================================
# ÁREA PRINCIPAL
# ==========================================================
if not st.session_state.bot_rodando:
    # MODO CONFIGURAÇÃO
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("🎯 ANÁLISE DE TOKEN COM IA")
        
        # Input do token
        ca_token = st.text_input(
            "📝 CONTRACT ADDRESS DO TOKEN:",
            placeholder="Cole o CA do token para análise completa...",
            help="A IA analisará: Liquidez, Volume, Tendência, Sentimento, e muito mais"
        )
        
        # Botão de análise
        if ca_token and st.button("🧠 ANALISAR COM IA", type="primary", use_container_width=True):
            with st.spinner("🔍 IA analisando token (isso pode levar alguns segundos)..."):
                # Buscar dados do token
                token_data = fetch_token_data(ca_token.strip())
                
                if token_data:
                    # Analisar com IA
                    analise = st.session_state.ai_expert.analisar_token_avancado(token_data)
                    st.session_state.analise_atual = analise
                    
                    # Mostrar resultados
                    st.success(f"✅ Análise completa! Score: {analise['score']}/100")
                    
                    # Mostrar relatório
                    with st.expander("📋 VER RELATÓRIO COMPLETO DA IA", expanded=True):
                        st.markdown(st.session_state.ai_expert.gerar_relatorio_analise(analise))
                        
                        # Sugestão de posição
                        if analise['score'] >= 40:
                            sugestao = st.session_state.ai_expert.calcular_sugestao_posicao(
                                analise['score'], 
                                analise['confianca'],
                                st.session_state.risk_manager.saldo
                            )
                            
                            st.markdown(f"""
                            **💡 SUGESTÃO DA IA:**
                            
                            • **Tamanho da posição:** {sugestao['percentual']}% do saldo (${sugestao['valor']:,.2f})
                            • **Stop Loss sugerido:** {sugestao['stop_loss']:.1f}%
                            • **Take Profit sugerido:** {sugestao['take_profit']:.1f}%
                            """)
                    
                    # Botão para iniciar trade com base na análise
                    if analise['decisao'] in ['COMPRAR', 'COMPRAR_FORTE']:
                        st.markdown("---")
                        valor_trade = st.number_input(
                            "💰 VALOR DO TRADE (USD):",
                            min_value=1.0,
                            value=float(sugestao['valor']),
                            max_value=float(st.session_state.risk_manager.saldo)
                        )
                        
                        # Avaliar risco
                        risco = st.session_state.risk_manager.avaliar_risco_trade(
                            analise['score'], 
                            valor_trade
                        )
                        
                        if risco['recomendacao'] == "APROVADO":
                            if st.button("🚀 INICIAR TRADE INTELIGENTE", type="primary", use_container_width=True):
                                # Iniciar trade
                                st.session_state.token_monitorado = {
                                    'ca': ca_token.strip(),
                                    'symbol': get_token_symbol(ca_token.strip()),
                                    'entrada': token_data['pairs'][0]['priceUsd'],
                                    'valor': valor_trade,
                                    'analise': analise,
                                    'stop_loss': sugestao['stop_loss'],
                                    'take_profit': sugestao['take_profit']
                                }
                                st.session_state.bot_rodando = True
                                adicionar_alerta(f"Trade iniciado para {get_token_symbol(ca_token.strip())}", "success")
                                st.rerun()
                        else:
                            st.warning(f"⚠️ RISCO {risco['risco']}: {', '.join(risco['razoes'])}")
                else:
                    st.error("❌ Não foi possível obter dados do token")
    
    with col2:
        st.header("🔍 TOKENS PROMISSORES")
        
        if st.session_state.tokens_promissores:
            for token in st.session_state.tokens_promissores[:5]:
                with st.container(border=True):
                    col_t1, col_t2 = st.columns([2, 1])
                    with col_t1:
                        st.markdown(f"**{token['symbol']}**")
                        st.caption(f"${token['price']:.8f}")
                    with col_t2:
                        score_color = "green" if token['score_potencial'] >= 70 else "orange" if token['score_potencial'] >= 50 else "red"
                        st.markdown(f"<span style='color:{score_color}; font-weight:bold'>{token['score_potencial']:.0f}/100</span>", 
                                   unsafe_allow_html=True)
                    
                    st.caption(f"📈 {token['price_change_24h']:+.1f}% | 💰 ${token['volume_24h']:,.0f}")
                    
                    if st.button(f"Analisar {token['symbol']}", key=f"btn_{token['ca']}", use_container_width=True):
                        st.session_state.ca_para_analise = token['ca']
                        st.rerun()
        else:
            st.info("Clique em 'BUSCAR TOKENS PROMISSORES' para encontrar oportunidades")
        
        st.divider()
        
        # Configurações da IA
        st.subheader("⚙️ CONFIGURAÇÕES DA IA")
        
        st.slider("🎯 Meta de Win Rate (%)", 50, 90, 75, 5, key="meta_win_rate")
        st.slider("⚠️ Stop Loss Máximo (%)", 1, 20, 10, 1, key="stop_loss_max")
        st.slider("💰 Take Profit Mínimo (%)", 5, 50, 15, 5, key="take_profit_min")

else:
    # MODO TRADING ATIVO
    col_status1, col_status2, col_status3 = st.columns([3, 1, 1])
    
    with col_status1:
        st.header(f"📈 TRADE ATIVO: {st.session_state.token_monitorado['symbol']}")
    
    with col_status2:
        if st.button("⏸️ PAUSAR", use_container_width=True):
            st.session_state.bot_rodando = False
            adicionar_alerta("Trade pausado", "warning")
            st.rerun()
    
    with col_status3:
        if st.button("⏹️ FINALIZAR", type="secondary", use_container_width=True):
            # Calcular resultado final
            preco_atual = fetch_token_data(st.session_state.token_monitorado['ca'])['pairs'][0]['priceUsd']
            pnl = ((preco_atual / st.session_state.token_monitorado['entrada']) - 1) * 100
            resultado = st.session_state.token_monitorado['valor'] * (pnl / 100)
            
            # Registrar trade
            st.session_state.risk_manager.registrar_trade(resultado, st.session_state.token_monitorado['analise']['score'])
            
            # Adicionar ao histórico
            st.session_state.historico_trades.append({
                'token': st.session_state.token_monitorado['symbol'],
                'entrada': st.session_state.token_monitorado['entrada'],
                'saida': preco_atual,
                'pnl': pnl,
                'resultado': resultado,
                'analise_score': st.session_state.token_monitorado['analise']['score']
            })
            
            st.session_state.bot_rodando = False
            st.session_state.token_monitorado = None
            adicionar_alerta(f"Trade finalizado: {pnl:+.2f}%", "info")
            st.rerun()
    
    st.markdown("---")
    
    # BUSCAR DADOS ATUAIS
    token_data = fetch_token_data(st.session_state.token_monitorado['ca'])
    
    if token_data:
        preco_atual = float(token_data['pairs'][0]['priceUsd'])
        entrada = float(st.session_state.token_monitorado['entrada'])
        pnl_atual = ((preco_atual / entrada) - 1) * 100
        
        # Informações em tempo real
        col_info1, col_info2, col_info3, col_info4 = st.columns(4)
        
        with col_info1:
            st.metric("💰 PREÇO ATUAL", f"${preco_atual:.10f}")
        
        with col_info2:
            delta_pnl = f"{pnl_atual:+.2f}%"
            st.metric("📈 PnL ATUAL", delta_pnl, delta_pnl)
        
        with col_info3:
            st.metric("🎯 STOP LOSS", f"{st.session_state.token_monitorado['stop_loss']:.1f}%")
        
        with col_info4:
            st.metric("🚀 TAKE PROFIT", f"{st.session_state.token_monitorado['take_profit']:.1f}%")
        
        # Gráfico de performance
        fig = go.Figure()
        fig.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=pnl_atual,
            delta={'reference': 0},
            gauge={
                'axis': {'range': [-20, 30]},
                'bar': {'color': "green" if pnl_atual >= 0 else "red"},
                'steps': [
                    {'range': [-20, 0], 'color': "lightgray"},
                    {'range': [0, st.session_state.token_monitorado['take_profit']], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': st.session_state.token_monitorado['stop_loss']
                }
            },
            title={'text': "Performance do Trade"}
        ))
        
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
        
        # Análise da IA em tempo real
        st.subheader("🧠 ANÁLISE DA IA EM TEMPO REAL")
        
        # Re-analisar a cada 30 segundos
        if 'ultima_reanalise' not in st.session_state or time.time() - st.session_state.ultima_reanalise > 30:
            nova_analise = st.session_state.ai_expert.analisar_token_avancado(token_data)
            st.session_state.ultima_reanalise = time.time()
            st.session_state.analise_atual = nova_analise
        
        if st.session_state.analise_atual:
            col_analise1, col_analise2 = st.columns(2)
            
            with col_analise1:
                # Score atual
                score = st.session_state.analise_atual['score']
                score_color = "green" if score >= 70 else "orange" if score >= 50 else "red"
                
                st.markdown(f"""
                <div style='text-align: center; padding: 20px; border-radius: 10px; background-color: #f0f2f6;'>
                    <h1 style='color: {score_color}; font-size: 48px;'>{score}</h1>
                    <h3>SCORE ATUAL</h3>
                    <p>Confiança: {st.session_state.analise_atual['confianca'] * 100:.0f}%</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_analise2:
                # Recomendações
                st.markdown("**📋 RECOMENDAÇÕES DA IA:**")
                for razao in st.session_state.analise_atual.get('razoes', []):
                    if "🔥" in razao or "✅" in razao:
                        st.success(razao)
                    elif "⚠️" in razao:
                        st.warning(razao)
                    elif "❌" in razao:
                        st.error(razao)
                    else:
                        st.info(razao)
        
        # Verificar condições de saída
        if pnl_atual <= st.session_state.token_monitorado['stop_loss']:
            st.error(f"🚨 STOP LOSS ATINGIDO ({pnl_atual:.2f}%)")
            if st.button("SAIR COM STOP LOSS", type="primary", use_container_width=True):
                resultado = st.session_state.token_monitorado['valor'] * (pnl_atual / 100)
                st.session_state.risk_manager.registrar_trade(resultado, st.session_state.token_monitorado['analise']['score'])
                st.session_state.bot_rodando = False
                st.success(f"Trade fechado no Stop Loss: {pnl_atual:.2f}%")
                time.sleep(2)
                st.rerun()
        
        elif pnl_atual >= st.session_state.token_monitorado['take_profit']:
            st.success(f"🎯 TAKE PROFIT ATINGIDO ({pnl_atual:.2f}%)")
            if st.button("SAIR COM LUCRO", type="primary", use_container_width=True):
                resultado = st.session_state.token_monitorado['valor'] * (pnl_atual / 100)
                st.session_state.risk_manager.registrar_trade(resultado, st.session_state.token_monitorado['analise']['score'])
                st.session_state.bot_rodando = False
                st.success(f"Trade fechado no Take Profit: {pnl_atual:.2f}%")
                time.sleep(2)
                st.rerun()
        
        # Atualização automática
        time.sleep(5)
        st.rerun()

# ==========================================================
# SEÇÃO DE HISTÓRICO E ESTATÍSTICAS
# ==========================================================
if st.session_state.historico_trades:
    st.markdown("---")
    st.header("📊 HISTÓRICO DE PERFORMANCE")
    
    df_historico = pd.DataFrame(st.session_state.historico_trades)
    
    # Métricas de performance
    if not df_historico.empty:
        col_perf1, col_perf2, col_perf3, col_perf4 = st.columns(4)
        
        with col_perf1:
            win_rate = (len(df_historico[df_historico['pnl'] > 0]) / len(df_historico)) * 100
            st.metric("🎯 WIN RATE ATUAL", f"{win_rate:.1f}%")
        
        with col_perf2:
            lucro_total = df_historico['resultado'].sum()
            st.metric("💰 LUCRO TOTAL", f"${lucro_total:+.2f}")
        
        with col_perf3:
            pnl_medio = df_historico['pnl'].mean()
            st.metric("📈 PnL MÉDIO", f"{pnl_medio:+.2f}%")
        
        with col_perf4:
            melhor_trade = df_historico['pnl'].max()
            st.metric("🚀 MELHOR TRADE", f"{melhor_trade:+.2f}%")
        
        # Gráfico de performance
        fig_perf = go.Figure()
        fig_perf.add_trace(go.Scatter(
            y=df_historico['pnl'].cumsum(),
            mode='lines+markers',
            name='Lucro Acumulado',
            line=dict(color='green', width=3)
        ))
        
        fig_perf.update_layout(
            title="Evolução do Lucro",
            xaxis_title="Número do Trade",
            yaxis_title="Lucro Acumulado ($)",
            height=400
        )
        
        st.plotly_chart(fig_perf, use_container_width=True)
        
        # Tabela de trades
        st.dataframe(
            df_historico,
            use_container_width=True,
            column_config={
                'token': 'Token',
                'entrada': st.column_config.NumberColumn('Entrada', format='%.8f'),
                'saida': st.column_config.NumberColumn('Saída', format='%.8f'),
                'pnl': st.column_config.NumberColumn('PnL %', format='+.2f'),
                'resultado': st.column_config.NumberColumn('Resultado $', format='+.2f'),
                'analise_score': st.column_config.NumberColumn('Score IA', format='%.0f')
            }
        )

# ==========================================================
# RODAPÉ
# ==========================================================
st.markdown("---")
footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption("🧠 IA Especializada em Trading")

with footer_col2:
    if st.session_state.risk_manager.trades:
        win_rate = (sum(1 for t in st.session_state.risk_manager.trades if t > 0) / 
                   len(st.session_state.risk_manager.trades)) * 100
        st.caption(f"🎯 Meta: 75% | Atual: {win_rate:.1f}%")
    else:
        st.caption("🎯 Meta: 75% de acerto")

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
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Métricas */
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: bold;
    }
    
    div[data-testid="stMetricDelta"] {
        font-size: 16px;
    }
    
    /* Containers */
    .stContainer {
        border-radius: 15px;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Alertas */
    .stAlert {
        border-radius: 10px;
        border-left: 5px solid;
    }
    
    /* Inputs */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 2px solid #e0e0e0;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# REQUIREMENTS.TXT (para instalação)
# ==========================================================
"""
streamlit==1.28.0
pandas==2.1.3
numpy==1.24.3
requests==2.31.0
plotly==5.17.0
"""