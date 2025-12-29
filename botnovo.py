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
    page_title="🔥 SNIPER AI - BOT AGRESSIVO",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# SISTEMA DE ANÁLISE HIPER AGRESSIVA
# ==========================================================
class AnalisadorAgressivo:
    """Sistema de análise ultra-agressiva para day trading"""
    
    def __init__(self):
        self.parametros = {
            'volume_minimo': 10000,      # $10k mínimo (baixo para entrar rápido)
            'liquidez_minima': 5000,     # $5k mínimo (mais agressivo)
            'var_aceitavel_min': -15,    # Aceita até -15% (tolerante a quedas)
            'var_aceitavel_max': 50,     # Aceita até +50% (caça pumps)
            'buy_ratio_min': 0.45,       # 45% compras mínimo (muito baixo)
            'confianca_minima': 60,      # 60% já entra
            'timeframe_rapido': True     # Foca em variações rápidas
        }
    
    def analisar_token(self, token_data: Dict) -> Dict:
        """Análise ultra-agressiva para day trading"""
        try:
            pair = token_data.get('pairs', [{}])[0]
            
            # Dados básicos
            symbol = pair.get('baseToken', {}).get('symbol', 'TOKEN')
            price = float(pair.get('priceUsd', 0))
            volume_24h = float(pair.get('volume', {}).get('h24', 0))
            liquidity = float(pair.get('liquidity', {}).get('usd', 0))
            price_change_24h = float(pair.get('priceChange', {}).get('h24', 0))
            
            # Dados de minutos (para análise rápida)
            price_change_5m = float(pair.get('priceChange', {}).get('m5', 0))
            price_change_1h = float(pair.get('priceChange', {}).get('h1', 0))
            
            # Dados de transações
            txns = pair.get('txns', {}).get('h24', {})
            buys = txns.get('buys', 0)
            sells = txns.get('sells', 0)
            buy_ratio = buys / (buys + sells) if (buys + sells) > 0 else 0
            
            # Score AGREGADO (0-150) - Mais fatores
            score = 0
            fatores = []
            
            # 1. VOLATILIDADE (0-40 pontos) - Quanto mais volátil, melhor para day trade
            volatilidade = abs(price_change_5m) + abs(price_change_1h)
            if volatilidade > 20:
                score += 40
                fatores.append("⚡ VOLATILIDADE EXTREMA (ótimo para scalp)")
            elif volatilidade > 10:
                score += 30
                fatores.append("🔥 Alta volatilidade")
            elif volatilidade > 5:
                score += 20
                fatores.append("📈 Volatilidade moderada")
            else:
                score += 10
                fatores.append("📊 Volatilidade baixa")
            
            # 2. MOMENTUM DE CURTO PRAZO (0-30 pontos)
            momentum = (price_change_5m * 3) + (price_change_1h * 1)
            if momentum > 15:
                score += 30
                fatores.append(f"🚀 FORTE MOMENTUM ({momentum:.1f} pontos)")
            elif momentum > 5:
                score += 20
                fatores.append(f"📈 Momentum positivo")
            elif momentum > -5:
                score += 10
                fatores.append(f"⚖️ Neutro")
            else:
                score += 5
                fatores.append(f"📉 Momentum negativo")
            
            # 3. VOLUME RELATIVO (0-25 pontos) - Aceita baixo volume
            if volume_24h > 50000:
                score += 25
                fatores.append("📈 Volume alto")
            elif volume_24h > 20000:
                score += 20
                fatores.append("📊 Volume bom")
            elif volume_24h > self.parametros['volume_minimo']:
                score += 15
                fatores.append("📉 Volume mínimo")
            else:
                score += 5
                fatores.append("⚠️ Volume muito baixo")
            
            # 4. LIQUIDEZ (0-20 pontos) - Aceita baixa liquidez
            if liquidity > 20000:
                score += 20
                fatores.append("💧 Liquidez boa")
            elif liquidity > 10000:
                score += 15
                fatores.append("💦 Liquidez razoável")
            elif liquidity > self.parametros['liquidez_minima']:
                score += 10
                fatores.append("💧 Liquidez mínima")
            else:
                score += 5
                fatores.append("⚠️ Liquidez muito baixa")
            
            # 5. SENTIMENTO DE COMPRA (0-15 pontos) - Aceita ratio baixo
            if buy_ratio > 0.6:
                score += 15
                fatores.append(f"🟢 COMPRAS FORTES ({buy_ratio*100:.0f}%)")
            elif buy_ratio > 0.4:
                score += 10
                fatores.append(f"🟡 Compras moderadas")
            else:
                score += 5
                fatores.append(f"🔴 Mais vendas (oportunidade?)")
            
            # 6. PREÇO BAIXO (0-20 pontos) - Tokens baratos têm mais chance de pump
            if price < 0.000001:
                score += 20
                fatores.append("💰 PREÇO MUITO BAIXO (alto potencial)")
            elif price < 0.00001:
                score += 15
                fatores.append("💎 Preço baixo")
            elif price < 0.0001:
                score += 10
                fatores.append("📊 Preço médio")
            else:
                score += 5
                fatores.append("📈 Preço alto")
            
            # DETERMINAR DECISÃO (AGRESSSIVA)
            confianca = min(95, max(40, score * 0.7))  # Converte score 0-150 para 0-95
            
            if score >= 80:  # Baixa exigência
                decisao = "COMPRAR AGORA"
                risco = "MÉDIO-ALTO"
                stop_loss = -3  # STOP TIGHT: -3%
                take_profit = 8  # TP CURTO: +8%
                cor = "🟢"
                agressividade = "MAXIMA"
                
            elif score >= 50:
                decisao = "COMPRAR"
                risco = "ALTO"
                stop_loss = -5  # -5%
                take_profit = 12  # +12%
                cor = "🟡"
                agressividade = "ALTA"
                
            else:
                decisao = "MONITORAR"
                risco = "MUITO ALTO"
                stop_loss = -8  # -8%
                take_profit = 15  # +15%
                cor = "🔴"
                agressividade = "MODERADA"
            
            return {
                'decisao': decisao,
                'cor': cor,
                'confianca': confianca,
                'score': score,
                'risco': risco,
                'agressividade': agressividade,
                'stop_loss_percent': stop_loss,
                'take_profit_percent': take_profit,
                'timeframe': 'ULTRA-CURTO (1-15min)',
                'fatores': fatores,
                'dados': {
                    'symbol': symbol,
                    'price': price,
                    'volume': volume_24h,
                    'liquidez': liquidity,
                    'variacao_24h': price_change_24h,
                    'variacao_5m': price_change_5m,
                    'variacao_1h': price_change_1h,
                    'buy_ratio': buy_ratio,
                    'volatilidade': volatilidade,
                    'momentum': momentum
                }
            }
            
        except Exception as e:
            return {
                'decisao': 'ANALISAR',
                'cor': '⚫',
                'confianca': 50,
                'score': 50,
                'risco': 'ALTO',
                'agressividade': 'ALTA',
                'stop_loss_percent': -5,
                'take_profit_percent': 10,
                'timeframe': 'RÁPIDO',
                'fatores': [f"Entrada agressiva: {str(e)[:30]}"],
                'dados': {}
            }

# ==========================================================
# SISTEMA DE TRADING ULTRA AGRESSIVO
# ==========================================================
class BotAgressivo:
    """Bot ultra-agressivo para day trading"""
    
    def __init__(self, saldo_inicial: float = 1000.0):
        self.saldo = saldo_inicial
        self.trades_ativos = []
        self.historico_trades = []
        self.estatisticas = {
            'total_trades': 0,
            'trades_vencedores': 0,
            'trades_perdedores': 0,
            'lucro_total': 0.0,
            'maior_lucro': 0.0,
            'maior_perda': 0.0,
            'win_rate': 0.0,
            'trades_dia': 0,
            'lucro_dia': 0.0
        }
        
        # PARÂMETROS AGRESSIVOS
        self.max_trades_simultaneos = 20  # MUITOS trades ao mesmo tempo
        self.posicao_por_trade_percent = 15  # 15% por trade
        self.stop_loss_tight = True  # Stops apertados
        self.take_profit_agressivo = True  # TPs curtos
        self.reentrar_perdas = True  # Reentra após stop
        self.trailing_stop_agressivo = True  # Trailing stop ativo
        
        # CONTROLE DE RISCO (ajustes automáticos)
        self.risk_multiplier = 1.0  # Multiplicador de risco
        self.last_trade_time = None
        self.consecutive_losses = 0
        
    def calcular_posicao_trade(self) -> float:
        """Calcula valor para cada trade - DISTRIBUIÇÃO AGRESSIVA"""
        num_trades_ativos = len(self.trades_ativos)
        
        # Se já tem muitos trades, reduz tamanho mas ainda entra
        if num_trades_ativos >= self.max_trades_simultaneos * 0.8:
            valor_por_trade = (self.saldo * 0.05) / 10  # 5% dividido
        else:
            trades_disponiveis = max(1, self.max_trades_simultaneos - num_trades_ativos)
            valor_por_trade = (self.saldo * (self.posicao_por_trade_percent / 100)) / trades_disponiveis
        
        # Aplica multiplicador de risco
        valor_por_trade *= self.risk_multiplier
        
        # Mínimo $5, máximo 30% do saldo
        return max(5.0, min(valor_por_trade, self.saldo * 0.3))
    
    def ajustar_agressividade(self, ultimo_resultado: str):
        """Ajusta agressividade baseado nos resultados"""
        if ultimo_resultado == 'WIN':
            self.consecutive_losses = 0
            self.risk_multiplier = min(2.0, self.risk_multiplier * 1.1)  # Aumenta risco após ganho
        elif ultimo_resultado == 'LOSS':
            self.consecutive_losses += 1
            if self.consecutive_losses >= 3:
                self.risk_multiplier = max(0.5, self.risk_multiplier * 0.8)  # Reduz risco após 3 perdas
            else:
                self.risk_multiplier = max(0.7, self.risk_multiplier * 0.9)  # Reduz levemente
    
    def criar_trade_agressivo(self, token_data: Dict, analise: Dict) -> Optional[Dict]:
        """Cria trade AGGRESSIVO - entra em quase tudo"""
        
        # NÃO FILTRA POR DECISÃO - Entra em qualquer coisa com confiança > 40%
        if analise['confianca'] < 40:
            return None
        
        # Verificar se já existe trade ativo para este token (evita duplicar)
        for trade in self.trades_ativos:
            if trade['ca'] == token_data.get('ca'):
                # Se o trade atual está perdendo muito, pode reentrar
                if trade['profit_percent'] < -15 and self.reentrar_perdas:
                    continue  # Permite reentrada
                return None
        
        # Calcular valor do trade
        valor_trade = self.calcular_posicao_trade()
        
        if valor_trade <= 0 or valor_trade > self.saldo * 0.9:
            return None
        
        # Dados do token
        price = analise['dados']['price']
        
        # STOP LOSS MUITO APERTADO para day trade
        if self.stop_loss_tight:
            stop_loss = price * (1 - abs(analise['stop_loss_percent']) / 100)
        else:
            stop_loss = price * (1 - 10 / 100)  # Fallback
        
        # TAKE PROFIT CURTO
        if self.take_profit_agressivo:
            take_profit = price * (1 + analise['take_profit_percent'] / 100)
        else:
            take_profit = price * (1 + 15 / 100)  # Fallback
        
        # Criar trade
        trade = {
            'id': len(self.historico_trades) + 1,
            'symbol': analise['dados']['symbol'],
            'ca': token_data.get('ca'),
            'entry_price': price,
            'current_price': price,
            'position_size': valor_trade,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'status': 'ACTIVE',
            'entry_time': datetime.now(),
            'analise': analise,
            'profit_percent': 0.0,
            'profit_value': 0.0,
            'exit_price': None,
            'exit_time': None,
            'exit_reason': None,
            'trailing_stop': stop_loss,
            'max_profit': 0.0,
            'risk_level': analise['risco'],
            'agressividade': analise['agressividade']
        }
        
        # Deduzir do saldo
        self.saldo -= valor_trade
        self.trades_ativos.append(trade)
        self.last_trade_time = datetime.now()
        
        return trade
    
    def atualizar_trades(self):
        """Atualiza preços e executa saídas AGRESSIVAS"""
        trades_fechados = []
        
        for trade in self.trades_ativos[:]:
            try:
                # Buscar preço atual
                url = f"https://api.dexscreener.com/latest/dex/tokens/{trade['ca']}"
                response = requests.get(url, timeout=3)  # Timeout curto
                if response.status_code == 200:
                    data = response.json()
                    if data.get('pairs'):
                        current_price = float(data['pairs'][0].get('priceUsd', 0))
                        trade['current_price'] = current_price
                        
                        # Calcular PnL
                        profit_percent = ((current_price - trade['entry_price']) / trade['entry_price']) * 100
                        profit_value = trade['position_size'] * (profit_percent / 100)
                        
                        trade['profit_percent'] = profit_percent
                        trade['profit_value'] = profit_value
                        
                        # Atualizar máximo profit
                        trade['max_profit'] = max(trade['max_profit'], profit_percent)
                        
                        # Verificar condições de saída AGRESSIVAS
                        if self.verificar_saida_agressiva(trade):
                            self.fechar_trade(trade, trades_fechados)
            except:
                continue
        
        return trades_fechados
    
    def verificar_saida_agressiva(self, trade: Dict) -> bool:
        """Condições de saída ULTRA AGRESSIVAS"""
        current_price = trade['current_price']
        
        # 1. TAKE PROFIT RÁPIDO (2-8%)
        if current_price >= trade['take_profit']:
            trade['exit_reason'] = 'TAKE_PROFIT_RÁPIDO'
            return True
        
        # 2. STOP LOSS APERTADO (3-5%)
        if current_price <= trade['stop_loss']:
            trade['exit_reason'] = 'STOP_LOSS_TIGHT'
            return True
        
        # 3. TRAILING STOP AGRESSIVO (ativa com 2% de gain)
        if self.trailing_stop_agressivo and trade['profit_percent'] >= 2:
            # Trailing dinâmico: mantém 50% do lucro máximo
            trail_level = trade['entry_price'] * (1 + (trade['max_profit'] * 0.5) / 100)
            if trail_level > trade['trailing_stop']:
                trade['trailing_stop'] = trail_level
            
            if current_price <= trade['trailing_stop']:
                trade['exit_reason'] = 'TRAILING_STOP_AGGR'
                return True
        
        # 4. SAÍDA POR TEMPO (máximo 30 minutos por trade)
        tempo_trade = (datetime.now() - trade['entry_time']).seconds / 60
        if tempo_trade > 30 and trade['profit_percent'] > 0:
            trade['exit_reason'] = 'SAÍDA_TEMPORIZADA'
            return True
        
        # 5. CORTE RÁPIDO se cair muito rápido (mais que 8% do topo)
        if trade['max_profit'] >= 5 and profit_percent <= trade['max_profit'] - 8:
            trade['exit_reason'] = 'CORTE_RÁPIDO'
            return True
        
        return False
    
    def fechar_trade(self, trade: Dict, trades_fechados: List):
        """Fecha trade e atualiza estatísticas"""
        trade['status'] = 'CLOSED'
        trade['exit_price'] = trade['current_price']
        trade['exit_time'] = datetime.now()
        
        # Duração do trade
        trade['duracao_min'] = (trade['exit_time'] - trade['entry_time']).seconds / 60
        
        # Adicionar lucro/perda ao saldo
        self.saldo += trade['position_size'] + trade['profit_value']
        
        # Atualizar estatísticas
        self.estatisticas['total_trades'] += 1
        self.estatisticas['trades_dia'] += 1
        self.estatisticas['lucro_dia'] += trade['profit_value']
        
        if trade['profit_value'] > 0:
            self.estatisticas['trades_vencedores'] += 1
            self.estatisticas['lucro_total'] += trade['profit_value']
            self.estatisticas['maior_lucro'] = max(self.estatisticas['maior_lucro'], trade['profit_value'])
            self.ajustar_agressividade('WIN')
        else:
            self.estatisticas['trades_perdedores'] += 1
            self.estatisticas['lucro_total'] += trade['profit_value']
            self.estatisticas['maior_perda'] = min(self.estatisticas['maior_perda'], trade['profit_value'])
            self.ajustar_agressividade('LOSS')
        
        # Calcular win rate
        total = self.estatisticas['trades_vencedores'] + self.estatisticas['trades_perdedores']
        if total > 0:
            self.estatisticas['win_rate'] = (self.estatisticas['trades_vencedores'] / total) * 100
        
        # Mover para histórico
        self.historico_trades.append(trade.copy())
        self.trades_ativos.remove(trade)
        trades_fechados.append(trade)
    
    def get_estatisticas(self) -> Dict:
        """Retorna estatísticas atualizadas"""
        return {
            'saldo': self.saldo,
            'trades_ativos': len(self.trades_ativos),
            'trades_total': self.estatisticas['total_trades'],
            'trades_dia': self.estatisticas['trades_dia'],
            'win_rate': round(self.estatisticas['win_rate'], 2),
            'lucro_total': round(self.estatisticas['lucro_total'], 2),
            'lucro_dia': round(self.estatisticas['lucro_dia'], 2),
            'maior_lucro': round(self.estatisticas['maior_lucro'], 2),
            'maior_perda': round(self.estatisticas['maior_perda'], 2),
            'risk_multiplier': round(self.risk_multiplier, 2),
            'consecutive_losses': self.consecutive_losses
        }

# ==========================================================
# INICIALIZAÇÃO DO STREAMLIT
# ==========================================================
if 'bot' not in st.session_state:
    st.session_state.bot = BotAgressivo(saldo_inicial=1000.0)

if 'analisador' not in st.session_state:
    st.session_state.analisador = AnalisadorAgressivo()

if 'auto_mode' not in st.session_state:
    st.session_state.auto_mode = True  # SEMPRE ATIVO

if 'tokens_monitorados' not in st.session_state:
    st.session_state.tokens_monitorados = []

if 'ultima_atualizacao' not in st.session_state:
    st.session_state.ultima_atualizacao = datetime.now()

# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================
def buscar_token(ca: str) -> Optional[Dict]:
    """Busca dados do token"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('pairs'):
                data['ca'] = ca
                return data
    except:
        pass
    return None

def entrada_agressiva_automatica():
    """Entra automaticamente em tokens promissores"""
    if not st.session_state.auto_mode:
        return
    
    # Buscar tokens "em alta" automaticamente (simulado)
    tokens_populares = [
        "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",  # ETH
        "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # BNB
        "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",  # USDC
    ]
    
    for ca in tokens_populares:
        if ca not in [t['ca'] for t in st.session_state.tokens_monitorados]:
            token_data = buscar_token(ca)
            if token_data:
                analise = st.session_state.analisador.analisar_token(token_data)
                if analise['confianca'] > 40:  # Baixo threshold
                    st.session_state.tokens_monitorados.append({
                        'ca': ca,
                        'symbol': analise['dados'].get('symbol', 'TOKEN'),
                        'analise': analise,
                        'adicionado_em': datetime.now(),
                        'entradas_tentadas': 0
                    })

# ==========================================================
# INTERFACE PRINCIPAL - TEMA ESCURO
# ==========================================================
st.title("🔥 SNIPER AI - BOT ULTRA AGRESSIVO")
st.markdown("### ⚡ DAY TRADING AUTOMÁTICO | STOP TIGHT | TP CURTO | HIGH FREQUENCY")

# ==========================================================
# SIDEBAR - TEMA ESCURO
# ==========================================================
with st.sidebar:
    # Configuração do tema escuro
    st.markdown("""
    <style>
    .sidebar .sidebar-content {
        background-color: #0E1117;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.header("💰 CONTROLE DO BOT", anchor=False)
    
    # Editor de saldo
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        novo_saldo = st.number_input(
            "DEFINIR SALDO ($)",
            min_value=100.0,
            max_value=1000000.0,
            value=float(st.session_state.bot.saldo),
            step=100.0,
            key="saldo_input"
        )
    
    with col_s2:
        if st.button("💾 ATUALIZAR", use_container_width=True, type="primary"):
            st.session_state.bot.saldo = novo_saldo
            st.success(f"Saldo: ${novo_saldo:,.2f}")
            st.rerun()
    
    st.divider()
    
    # ESTATÍSTICAS EM TEMPO REAL
    stats = st.session_state.bot.get_estatisticas()
    
    st.metric("💵 SALDO ATUAL", f"${stats['saldo']:,.2f}",
              delta=f"{stats['lucro_dia']:+.2f} hoje")
    
    st.metric("📊 WIN RATE", f"{stats['win_rate']:.1f}%",
              delta=f"{stats['trades_vencedores']}/{stats['trades_total']}")
    
    st.metric("⚡ TRADES/HOJE", f"{stats['trades_dia']}",
              delta=f"${stats['lucro_dia']:+.2f}")
    
    st.metric("🔥 RISCO MULT.", f"{stats['risk_multiplier']}x",
              delta=f"Loss streak: {stats['consecutive_losses']}")
    
    st.divider()
    
    # CONFIGURAÇÕES AGRESSIVAS
    st.header("⚙️ CONFIG AGRESSIVA")
    
    st.session_state.auto_mode = st.toggle(
        "🤖 MODO AUTOMÁTICO",
        value=True,
        disabled=True,  # Sempre ativo
        help="Bot sempre ativo e caçando oportunidades"
    )
    
    # Sliders para controle agressivo
    agressividade = st.slider(
        "NÍVEL DE AGRESSIVIDADE",
        min_value=1,
        max_value=10,
        value=8,
        help="1=Conservador, 10=Máximo risco"
    )
    
    # Aplicar agressividade
    if agressividade >= 8:
        st.session_state.bot.risk_multiplier = 1.5
        st.session_state.bot.max_trades_simultaneos = 25
        st.session_state.bot.posicao_por_trade_percent = 20
    elif agressividade >= 6:
        st.session_state.bot.risk_multiplier = 1.2
        st.session_state.bot.max_trades_simultaneos = 20
        st.session_state.bot.posicao_por_trade_percent = 15
    else:
        st.session_state.bot.risk_multiplier = 1.0
        st.session_state.bot.max_trades_simultaneos = 15
        st.session_state.bot.posicao_por_trade_percent = 10
    
    # Parâmetros de trade
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.metric("MAX TRADES", st.session_state.bot.max_trades_simultaneos)
    with col_p2:
        st.metric("POSIÇÃO %", f"{st.session_state.bot.posicao_por_trade_percent}%")
    
    st.divider()
    
    # AÇÕES RÁPIDAS
    if st.button("🎯 FORÇAR ENTRADA", use_container_width=True, type="primary"):
        entrada_agressiva_automatica()
        st.success("Caçando oportunidades!")
        st.rerun()
    
    if st.button("🔄 ATUALIZAR TUDO", use_container_width=True):
        st.session_state.bot.atualizar_trades()
        st.rerun()
    
    if st.button("📊 EXPORTAR DADOS", use_container_width=True):
        if st.session_state.bot.historico_trades:
            df = pd.DataFrame(st.session_state.bot.historico_trades)
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇️ BAIXAR HISTÓRICO",
                data=csv,
                file_name="trades_agressivos.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    if st.button("🧨 REINICIAR BOT", use_container_width=True, type="secondary"):
        st.session_state.bot = BotAgressivo(saldo_inicial=1000.0)
        st.session_state.tokens_monitorados = []
        st.success("Bot reiniciado!")
        st.rerun()
    
    st.divider()
    st.caption(f"🕒 {datetime.now().strftime('%H:%M:%S')}")
    st.caption("🔥 BOT AGRESSIVO ATIVO")

# ==========================================================
# SEÇÃO 1: ENTRADA MANUAL AGRESSIVA
# ==========================================================
st.header("🎯 ENTRADA MANUAL AGRESSIVA")

col_input1, col_input2, col_input3 = st.columns([3, 1, 1])

with col_input1:
    token_ca = st.text_input(
        "COLE O CA DO TOKEN:",
        placeholder="0x...",
        key="input_token",
        help="Cole qualquer token - bot analisa e entra AGGRESSIVAMENTE"
    )

with col_input2:
    btn_analisar = st.button(
        "🔎 ANALISAR",
        type="primary",
        use_container_width=True,
        disabled=not token_ca
    )

with col_input3:
    btn_entrar_agressivo = st.button(
        "⚡ ENTRAR AGORA",
        type="secondary",
        use_container_width=True,
        disabled=not token_ca,
        help="Entra sem análise detalhada - MÁXIMA AGRESSIVIDADE"
    )

if token_ca:
    token_data = buscar_token(token_ca.strip())
    
    if token_data:
        # Análise AGGRESSIVA
        analise = st.session_state.analisador.analisar_token(token_data)
        
        # Mostrar resultado IMEDIATO
        col_status1, col_status2, col_status3, col_status4 = st.columns(4)
        
        with col_status1:
            st.metric("🎯 DECISÃO", analise['decisao'],
                     delta=f"{analise['confianca']:.0f}% conf")
        
        with col_status2:
            st.metric("📊 SCORE", f"{analise['score']}/150")
        
        with col_status3:
            st.metric("⚠️ RISCO", analise['risco'])
        
        with col_status4:
            st.metric("🔥 NIVEL", analise['agressividade'])
        
        # DADOS RÁPIDOS
        with st.expander("📈 DADOS INSTANTÂNEOS", expanded=True):
            col_d1, col_d2, col_d3, col_d4 = st.columns(4)
            
            with col_d1:
                st.metric("💰 Preço", f"${analise['dados']['price']:.10f}")
            
            with col_d2:
                st.metric("📈 5min", f"{analise['dados']['variacao_5m']:.1f}%")
            
            with col_d3:
                st.metric("📊 1h", f"{analise['dados']['variacao_1h']:.1f}%")
            
            with col_d4:
                st.metric("⚡ Volat.", f"{analise['dados']['volatilidade']:.1f}")
        
        # PARÂMETROS AGRESSIVOS
        st.subheader("⚙️ PARÂMETROS DE ENTRADA")
        
        price = analise['dados']['price']
        stop_price = price * (1 - abs(analise['stop_loss_percent']) / 100)
        tp_price = price * (1 + analise['take_profit_percent'] / 100)
        
        col_p1, col_p2, col_p3 = st.columns(3)
        
        with col_p1:
            st.metric("⛔ STOP LOSS", f"{analise['stop_loss_percent']}%",
                     f"${stop_price:.10f}")
        
        with col_p2:
            st.metric("🎯 TAKE PROFIT", f"+{analise['take_profit_percent']}%",
                     f"${tp_price:.10f}")
        
        with col_p3:
            rr = abs(analise['take_profit_percent'] / analise['stop_loss_percent'])
            st.metric("📈 R:R", f"1:{rr:.1f}",
                     f"Time: {analise['timeframe']}")
        
        # BOTÃO DE ENTRADA AGRESSIVA
        if analise['confianca'] > 40 or btn_entrar_agressivo:  # THRESHOLD BAIXO
            st.success(f"✅ PRONTO PARA ENTRADA AGRESSIVA!")
            
            # Calcular posição
            valor_trade = st.session_state.bot.calcular_posicao_trade()
            
            col_e1, col_e2 = st.columns([2, 1])
            
            with col_e1:
                st.info(f"💰 **Posição sugerida:** ${valor_trade:.2f}")
                st.caption(f"📊 {len(st.session_state.bot.trades_ativos)} trades ativos")
            
            with col_e2:
                if st.button("🚀 EXECUTAR TRADE", type="primary", use_container_width=True):
                    trade = st.session_state.bot.criar_trade_agressivo(token_data, analise)
                    if trade:
                        st.balloons()
                        st.success(f"✅ ENTRADA AGRESSIVA em {trade['symbol']}!")
                        st.rerun()
                    else:
                        st.error("❌ Erro na entrada")
        
        # Adicionar à lista de monitoramento automático
        if analise['confianca'] > 30:  # THRESHOLD MUITO BAIXO
            if st.button("➕ MONITORAR AUTOMATICAMENTE", use_container_width=True):
                st.session_state.tokens_monitorados.append({
                    'ca': token_data['ca'],
                    'symbol': analise['dados']['symbol'],
                    'analise': analise,
                    'adicionado_em': datetime.now(),
                    'entradas_tentadas': 0
                })
                st.success(f"✅ {analise['dados']['symbol']} em monitoramento AGGRESSIVO!")
                st.rerun()

# ==========================================================
# SEÇÃO 2: TRADES ATIVOS - VISUALIZAÇÃO AGRESSIVA
# ==========================================================
st.header("📈 TRADES ATIVOS - MONITORAMENTO EM TEMPO REAL")

# Atualizar trades
trades_fechados = st.session_state.bot.atualizar_trades()

# Mostrar trades fechados recentemente (rápido)
if trades_fechados:
    st.subheader("🔒 ÚLTIMOS FECHAMENTOS")
    for trade in trades_fechados[-5:]:
        profit = trade['profit_value']
        emoji = "🟢" if profit >= 0 else "🔴"
        
        col_f1, col_f2, col_f3 = st.columns([3, 2, 1])
        with col_f1:
            st.write(f"{emoji} **{trade['symbol']}** - {trade['exit_reason']}")
        with col_f2:
            st.write(f"⏱️ {trade['duracao_min']:.1f}min")
        with col_f3:
            st.write(f"**${profit:+.2f}** ({trade['profit_percent']:+.1f}%)")

# Mostrar trades ativos
if st.session_state.bot.trades_ativos:
    st.subheader(f"🟢 {len(st.session_state.bot.trades_ativos)} TRADES EM ABERTO")
    
    # Grid de trades
    cols = st.columns(4)
    
    for idx, trade in enumerate(st.session_state.bot.trades_ativos):
        with cols[idx % 4]:
            with st.container(border=True):
                profit = trade['profit_percent']
                color = "🟢" if profit >= 0 else "🔴"
                
                # Cabeçalho colorido
                if profit >= 5:
                    st.markdown(f"<div style='background-color:#00FF00; padding:5px; border-radius:5px;'>", unsafe_allow_html=True)
                elif profit <= -3:
                    st.markdown(f"<div style='background-color:#FF0000; padding:5px; border-radius:5px;'>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='background-color:#FFA500; padding:5px; border-radius:5px;'>", unsafe_allow_html=True)
                
                st.markdown(f"**{trade['symbol']}** ({trade['agressividade']})</div>", unsafe_allow_html=True)
                
                # Dados principais
                st.markdown(f"### {color} {profit:+.2f}%")
                st.caption(f"💰 ${trade['position_size']:.2f}")
                st.caption(f"🎯 TP: +{trade['analise']['take_profit_percent']}%")
                st.caption(f"⛔ SL: {trade['analise']['stop_loss_percent']}%")
                
                # Botão de saída manual
                if st.button(f"⏹️ SAIR", key=f"exit_{trade['id']}", use_container_width=True):
                    trade['exit_reason'] = 'SAÍDA_MANUAL'
                    st.session_state.bot.fechar_trade(trade, [])
                    st.rerun()
else:
    st.info("📭 Nenhum trade ativo - Bot aguardando oportunidades")

# ==========================================================
# SEÇÃO 3: SISTEMA AUTOMÁTICO AGRESSIVO
# ==========================================================
st.header("🤖 SISTEMA AUTOMÁTICO - CAÇANDO OPORTUNIDADES")

# Entrada automática agressiva
if st.session_state.auto_mode:
    # Atualizar tokens monitorados
    for token in st.session_state.tokens_monitorados[:]:
        try:
            token_data = buscar_token(token['ca'])
            if token_data:
                analise = st.session_state.analisador.analisar_token(token_data)
                token['analise'] = analise
                
                # Tentar entrada AGGRESSIVA
                if analise['confianca'] > 40:
                    trade = st.session_state.bot.criar_trade_agressivo(token_data, analise)
                    if trade:
                        token['entradas_tentadas'] += 1
                        st.success(f"⚡ ENTRADA AUTOMÁTICA em {trade['symbol']}")
        except:
            continue
    
    # Mostrar tokens sendo monitorados
    if st.session_state.tokens_monitorados:
        st.subheader(f"🎯 {len(st.session_state.tokens_monitorados)} TOKENS EM MONITORAMENTO")
        
        for token in st.session_state.tokens_monitorados[-10:]:
            analise = token['analise']
            col_m1, col_m2, col_m3 = st.columns([2, 2, 1])
            
            with col_m1:
                st.write(f"**{token['symbol']}**")
                st.caption(f"Conf: {analise['confianca']:.0f}%")
            
            with col_m2:
                st.write(f"{analise['cor']} {analise['decisao']}")
                st.caption(f"Vol: {analise['dados'].get('volatilidade', 0):.1f}")
            
            with col_m3:
                if st.button("🗑️", key=f"remove_{token['ca']}"):
                    st.session_state.tokens_monitorados.remove(token)
                    st.rerun()
    
    # Auto-refresh agressivo
    if (datetime.now() - st.session_state.ultima_atualizacao).seconds > 10:
        st.session_state.ultima_atualizacao = datetime.now()
        st.rerun()

# ==========================================================
# SEÇÃO 4: DASHBOARD DE PERFORMANCE
# ==========================================================
st.header("📊 DASHBOARD DE PERFORMANCE AGRESSIVA")

stats = st.session_state.bot.get_estatisticas()

# Métricas principais
col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)

with col_s1:
    st.metric("💵 SALDO TOTAL", f"${stats['saldo']:,.2f}",
             delta=f"{stats['lucro_total']:+.2f}")

with col_s2:
    st.metric("📊 WIN RATE", f"{stats['win_rate']:.1f}%",
             delta=f"{stats['trades_vencedores']}/{stats['trades_total']}")

with col_s3:
    st.metric("⚡ TRADES/DIA", f"{stats['trades_dia']}",
             delta=f"${stats['lucro_dia']:+.2f}")

with col_s4:
    st.metric("🔥 MULT. RISCO", f"{stats['risk_multiplier']}x",
             delta=f"Streak: {stats['consecutive_losses']}")

with col_s5:
    st.metric("📈 TRADES ATIVOS", f"{stats['trades_ativos']}",
             delta=f"Max: {st.session_state.bot.max_trades_simultaneos}")

# Gráfico de performance
if st.session_state.bot.historico_trades:
    df = pd.DataFrame(st.session_state.bot.historico_trades)
    
    if 'profit_value' in df.columns:
        df['lucro_acumulado'] = df['profit_value'].cumsum()
        df['media_movel'] = df['profit_value'].rolling(window=10, min_periods=1).mean()
        
        fig = go.Figure()
        
        # Lucro acumulado
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['lucro_acumulado'],
            mode='lines',
            name='Lucro Acumulado',
            line=dict(color='#00FF00', width=4)
        ))
        
        # Média móvel
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['media_movel'],
            mode='lines',
            name='Média Móvel (10)',
            line=dict(color='#FFA500', width=2, dash='dash')
        ))
        
        fig.update_layout(
            title='PERFORMANCE AGRESSIVA DO BOT',
            xaxis_title='Número do Trade',
            yaxis_title='Lucro Acumulado ($)',
            height=400,
            plot_bgcolor='#1E1E1E',
            paper_bgcolor='#1E1E1E',
            font=dict(color='white'),
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)

# ==========================================================
# CSS - TEMA ESCURO COMPLETO
# ==========================================================
st.markdown("""
<style>
    /* TEMA ESCURO COMPLETO */
    .stApp {
        background-color: #0E1117;
        color: white;
    }
    
    /* Sidebar escura */
    section[data-testid="stSidebar"] {
        background-color: #0E1117;
        border-right: 1px solid #2D3746;
    }
    
    .css-1d391kg, .css-12oz5g7, .css-1y4p8pa {
        background-color: #0E1117;
    }
    
    /* Textos brancos */
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        color: white !important;
    }
    
    /* Inputs com tema escuro */
    .stTextInput input, .stNumberInput input, .stSelectbox select {
        background-color: #1E1E1E !important;
        color: white !important;
        border: 1px solid #2D3746 !important;
    }
    
    /* Botões AGRESSIVOS */
    .stButton > button {
        background: linear-gradient(45deg, #FF0000, #FF4500);
        color: white;
        border: none;
        font-weight: bold;
        border-radius: 8px;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 0 15px #FF0000;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(45deg, #FF0000, #DC143C);
    }
    
    .stButton > button[kind="secondary"] {
        background: linear-gradient(45deg, #FF8C00, #FF4500);
    }
    
    /* Métricas com tema escuro */
    [data-testid="stMetricValue"] {
        color: white !important;
        font-size: 1.8rem;
        font-weight: bold;
    }
    
    [data-testid="stMetricLabel"] {
        color: #AAAAAA !important;
    }
    
    [data-testid="stMetricDelta"] {
        color: #00FF00 !important;
    }
    
    /* Containers com bordas neon */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #1E1E1E;
        border: 1px solid #FF0000;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 0 10px rgba(255, 0, 0, 0.2);
    }
    
    /* Títulos com gradiente vermelho */
    h1, h2, h3 {
        background: linear-gradient(45deg, #FF0000, #FF8C00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Divider vermelho */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, #FF0000, transparent);
        margin: 2rem 0;
    }
    
    /* Cards de trade */
    .trade-card-win {
        border-left: 5px solid #00FF00;
        background: rgba(0, 255, 0, 0.1);
    }
    
    .trade-card-loss {
        border-left: 5px solid #FF0000;
        background: rgba(255, 0, 0, 0.1);
    }
    
    .trade-card-neutral {
        border-left: 5px solid #FFA500;
        background: rgba(255, 165, 0, 0.1);
    }
    
    /* Scrollbar personalizada */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1E1E1E;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #FF0000;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #DC143C;
    }
    
    /* Tooltips */
    .stTooltip {
        background-color: #1E1E1E !important;
        color: white !important;
        border: 1px solid #FF0000 !important;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #1E1E1E !important;
        color: white !important;
        border: 1px solid #2D3746 !important;
    }
    
    /* Selectboxes e dropdowns */
    .st-ae, .st-ag, .st-af {
        background-color: #1E1E1E !important;
        color: white !important;
    }
    
    /* Tabelas */
    .stDataFrame {
        background-color: #1E1E1E !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# RODAPÉ
# ==========================================================
st.divider()

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption(f"🕒 {datetime.now().strftime('%H:%M:%S')}")
    
with footer_col2:
    bot_stats = st.session_state.bot.get_estatisticas()
    st.caption(f"🔥 RISCO: {bot_stats['risk_multiplier']}x")
    
with footer_col3:
    if st.session_state.auto_mode:
        st.caption("🤖 MODO: ⚡ AGRESSIVO")
    else:
        st.caption("🤖 MODO: 🔴 INATIVO")

# ==========================================================
# AUTO-REFRESH PARA DAY TRADING
# ==========================================================
if st.session_state.auto_mode:
    # Refresh a cada 15 segundos para day trading
    time.sleep(15)
    st.rerun()