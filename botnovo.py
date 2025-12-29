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
    page_title="🔥 SNIPER AI - BOT ULTRA AGRESSIVO",
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
            'volume_minimo': 10000,
            'liquidez_minima': 5000,
            'confianca_minima': 60,
        }
    
    def analisar_token(self, token_data: Dict) -> Dict:
        """Análise ultra-agressiva para day trading"""
        try:
            pair = token_data.get('pairs', [{}])[0]
            
            symbol = pair.get('baseToken', {}).get('symbol', 'TOKEN')
            price = float(pair.get('priceUsd', 0))
            volume_24h = float(pair.get('volume', {}).get('h24', 0))
            liquidity = float(pair.get('liquidity', {}).get('usd', 0))
            price_change_24h = float(pair.get('priceChange', {}).get('h24', 0))
            price_change_5m = float(pair.get('priceChange', {}).get('m5', 0))
            price_change_1h = float(pair.get('priceChange', {}).get('h1', 0))
            
            txns = pair.get('txns', {}).get('h24', {})
            buys = txns.get('buys', 0)
            sells = txns.get('sells', 0)
            buy_ratio = buys / (buys + sells) if (buys + sells) > 0 else 0
            
            # Score calculado
            score = 0
            fatores = []
            
            # Volatilidade
            volatilidade = abs(price_change_5m) + abs(price_change_1h)
            if volatilidade > 20:
                score += 40
                fatores.append("⚡ VOLATILIDADE EXTREMA")
            elif volatilidade > 10:
                score += 30
                fatores.append("🔥 Alta volatilidade")
            elif volatilidade > 5:
                score += 20
                fatores.append("📈 Volatilidade moderada")
            else:
                score += 10
                fatores.append("📊 Volatilidade baixa")
            
            # Momentum
            momentum = (price_change_5m * 3) + (price_change_1h * 1)
            if momentum > 15:
                score += 30
                fatores.append(f"🚀 FORTE MOMENTUM")
            elif momentum > 5:
                score += 20
                fatores.append(f"📈 Momentum positivo")
            else:
                score += 10
                fatores.append(f"⚖️ Neutro")
            
            # Volume
            if volume_24h > 50000:
                score += 25
                fatores.append("📈 Volume alto")
            elif volume_24h > 20000:
                score += 20
                fatores.append("📊 Volume bom")
            else:
                score += 10
                fatores.append("📉 Volume baixo")
            
            # Determinar decisão
            confianca = min(95, max(40, score * 0.7))
            
            if score >= 80:
                decisao = "COMPRAR AGORA"
                risco = "MÉDIO-ALTO"
                stop_loss = -3
                take_profit = 8
                cor = "🟢"
                agressividade = "MAXIMA"
            elif score >= 50:
                decisao = "COMPRAR"
                risco = "ALTO"
                stop_loss = -5
                take_profit = 12
                cor = "🟡"
                agressividade = "ALTA"
            else:
                decisao = "MONITORAR"
                risco = "MUITO ALTO"
                stop_loss = -8
                take_profit = 15
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
                'timeframe': 'ULTRA-CURTO',
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
                'fatores': [f"Entrada agressiva"],
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
            'trades_ganhos': 0,
            'trades_perdidos': 0,
            'lucro_total': 0.0,
            'maior_lucro': 0.0,
            'maior_perda': 0.0,
            'win_rate': 0.0,
            'trades_dia': 0,
            'lucro_dia': 0.0
        }
        
        # PARÂMETROS AGRESSIVOS
        self.max_trades_simultaneos = 20
        self.posicao_por_trade_percent = 15
        self.stop_loss_tight = True
        self.take_profit_agressivo = True
        self.reentrar_perdas = True
        self.trailing_stop_agressivo = True
        
        # CONTROLE DE RISCO
        self.risk_multiplier = 1.0
        self.last_trade_time = None
        self.perdas_consecutivas = 0
        
    def calcular_posicao_trade(self) -> float:
        """Calcula valor para cada trade"""
        num_trades_ativos = len(self.trades_ativos)
        
        if num_trades_ativos >= self.max_trades_simultaneos * 0.8:
            valor_por_trade = (self.saldo * 0.05) / 10
        else:
            trades_disponiveis = max(1, self.max_trades_simultaneos - num_trades_ativos)
            valor_por_trade = (self.saldo * (self.posicao_por_trade_percent / 100)) / trades_disponiveis
        
        valor_por_trade *= self.risk_multiplier
        
        return max(5.0, min(valor_por_trade, self.saldo * 0.3))
    
    def ajustar_agressividade(self, resultado: str):
        """Ajusta agressividade baseado nos resultados"""
        if resultado == 'GANHO':
            self.perdas_consecutivas = 0
            self.risk_multiplier = min(2.0, self.risk_multiplier * 1.1)
        elif resultado == 'PERDA':
            self.perdas_consecutivas += 1
            if self.perdas_consecutivas >= 3:
                self.risk_multiplier = max(0.5, self.risk_multiplier * 0.8)
            else:
                self.risk_multiplier = max(0.7, self.risk_multiplier * 0.9)
    
    def criar_trade_agressivo(self, token_data: Dict, analise: Dict) -> Optional[Dict]:
        """Cria trade AGGRESSIVO"""
        
        if analise['confianca'] < 40:
            return None
        
        for trade in self.trades_ativos:
            if trade['ca'] == token_data.get('ca'):
                if trade['profit_percent'] < -15 and self.reentrar_perdas:
                    continue
                return None
        
        valor_trade = self.calcular_posicao_trade()
        
        if valor_trade <= 0 or valor_trade > self.saldo * 0.9:
            return None
        
        price = analise['dados']['price']
        
        if self.stop_loss_tight:
            stop_loss = price * (1 - abs(analise['stop_loss_percent']) / 100)
        else:
            stop_loss = price * 0.9
        
        if self.take_profit_agressivo:
            take_profit = price * (1 + analise['take_profit_percent'] / 100)
        else:
            take_profit = price * 1.15
        
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
        
        self.saldo -= valor_trade
        self.trades_ativos.append(trade)
        self.last_trade_time = datetime.now()
        
        return trade
    
    def atualizar_trades(self):
        """Atualiza preços e executa saídas"""
        trades_fechados = []
        
        for trade in self.trades_ativos[:]:
            try:
                url = f"https://api.dexscreener.com/latest/dex/tokens/{trade['ca']}"
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('pairs'):
                        current_price = float(data['pairs'][0].get('priceUsd', 0))
                        trade['current_price'] = current_price
                        
                        profit_percent = ((current_price - trade['entry_price']) / trade['entry_price']) * 100
                        profit_value = trade['position_size'] * (profit_percent / 100)
                        
                        trade['profit_percent'] = profit_percent
                        trade['profit_value'] = profit_value
                        trade['max_profit'] = max(trade['max_profit'], profit_percent)
                        
                        if self.verificar_saida_agressiva(trade):
                            self.fechar_trade(trade, trades_fechados)
            except:
                continue
        
        return trades_fechados
    
    def verificar_saida_agressiva(self, trade: Dict) -> bool:
        """Condições de saída"""
        current_price = trade['current_price']
        
        if current_price >= trade['take_profit']:
            trade['exit_reason'] = 'TAKE_PROFIT_RÁPIDO'
            return True
        
        if current_price <= trade['stop_loss']:
            trade['exit_reason'] = 'STOP_LOSS_TIGHT'
            return True
        
        if self.trailing_stop_agressivo and trade['profit_percent'] >= 2:
            trail_level = trade['entry_price'] * (1 + (trade['max_profit'] * 0.5) / 100)
            if trail_level > trade['trailing_stop']:
                trade['trailing_stop'] = trail_level
            
            if current_price <= trade['trailing_stop']:
                trade['exit_reason'] = 'TRAILING_STOP'
                return True
        
        tempo_trade = (datetime.now() - trade['entry_time']).seconds / 60
        if tempo_trade > 30 and trade['profit_percent'] > 0:
            trade['exit_reason'] = 'SAÍDA_TEMPORIZADA'
            return True
        
        if trade['max_profit'] >= 5 and trade['profit_percent'] <= trade['max_profit'] - 8:
            trade['exit_reason'] = 'CORTE_RÁPIDO'
            return True
        
        return False
    
    def fechar_trade(self, trade: Dict, trades_fechados: List):
        """Fecha trade"""
        trade['status'] = 'CLOSED'
        trade['exit_price'] = trade['current_price']
        trade['exit_time'] = datetime.now()
        trade['duracao_min'] = (trade['exit_time'] - trade['entry_time']).seconds / 60
        
        self.saldo += trade['position_size'] + trade['profit_value']
        
        self.estatisticas['total_trades'] += 1
        self.estatisticas['trades_dia'] += 1
        self.estatisticas['lucro_dia'] += trade['profit_value']
        
        if trade['profit_value'] > 0:
            self.estatisticas['trades_ganhos'] += 1
            self.estatisticas['lucro_total'] += trade['profit_value']
            self.estatisticas['maior_lucro'] = max(self.estatisticas['maior_lucro'], trade['profit_value'])
            self.ajustar_agressividade('GANHO')
        else:
            self.estatisticas['trades_perdidos'] += 1
            self.estatisticas['lucro_total'] += trade['profit_value']
            self.estatisticas['maior_perda'] = min(self.estatisticas['maior_perda'], trade['profit_value'])
            self.ajustar_agressividade('PERDA')
        
        total = self.estatisticas['trades_ganhos'] + self.estatisticas['trades_perdidos']
        if total > 0:
            self.estatisticas['win_rate'] = (self.estatisticas['trades_ganhos'] / total) * 100
        
        self.historico_trades.append(trade.copy())
        self.trades_ativos.remove(trade)
        trades_fechados.append(trade)
    
    def get_estatisticas(self) -> Dict:
        """Retorna estatísticas atualizadas - VERSÃO CORRIGIDA"""
        return {
            'saldo': self.saldo,
            'trades_ativos': len(self.trades_ativos),
            'trades_total': self.estatisticas['total_trades'],
            'trades_ganhos': self.estatisticas['trades_ganhos'],
            'trades_perdidos': self.estatisticas['trades_perdidos'],
            'trades_dia': self.estatisticas['trades_dia'],
            'win_rate': round(self.estatisticas['win_rate'], 2),
            'lucro_total': round(self.estatisticas['lucro_total'], 2),
            'lucro_dia': round(self.estatisticas['lucro_dia'], 2),
            'maior_lucro': round(self.estatisticas['maior_lucro'], 2),
            'maior_perda': round(self.estatisticas['maior_perda'], 2),
            'risk_multiplier': round(self.risk_multiplier, 2),
            'perdas_consecutivas': self.perdas_consecutivas
        }

# ==========================================================
# INICIALIZAÇÃO DO STREAMLIT
# ==========================================================
if 'bot' not in st.session_state:
    st.session_state.bot = BotAgressivo(saldo_inicial=1000.0)

if 'analisador' not in st.session_state:
    st.session_state.analisador = AnalisadorAgressivo()

if 'auto_mode' not in st.session_state:
    st.session_state.auto_mode = True

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

# ==========================================================
# INTERFACE PRINCIPAL - TEMA ESCURO
# ==========================================================
st.title("🔥 SNIPER AI - BOT ULTRA AGRESSIVO")
st.markdown("### ⚡ DAY TRADING AUTOMÁTICO | HIGH FREQUENCY")

# ==========================================================
# SIDEBAR - TEMA ESCURO
# ==========================================================
with st.sidebar:
    # Configuração do tema escuro
    st.markdown("""
    <style>
    .sidebar .sidebar-content {
        background-color: #0E1117 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.header("💰 CONTROLE DO BOT")
    
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
    
    # CORREÇÃO AQUI: Usando trades_ganhos em vez de trades_vencedores
    st.metric("💵 SALDO ATUAL", f"${stats['saldo']:,.2f}",
              delta=f"{stats['lucro_dia']:+.2f} hoje")
    
    # CORREÇÃO AQUI: Usando trades_ganhos
    st.metric("📊 WIN RATE", f"{stats['win_rate']:.1f}%",
              delta=f"{stats['trades_ganhos']}/{stats['trades_total']}")
    
    st.metric("⚡ TRADES/HOJE", f"{stats['trades_dia']}",
              delta=f"${stats['lucro_dia']:+.2f}")
    
    st.metric("🔥 RISCO MULT.", f"{stats['risk_multiplier']}x",
              delta=f"Loss streak: {stats['perdas_consecutivas']}")
    
    st.divider()
    
    # CONFIGURAÇÕES AGRESSIVAS
    st.header("⚙️ CONFIG AGRESSIVA")
    
    st.session_state.auto_mode = st.toggle(
        "🤖 MODO AUTOMÁTICO",
        value=True,
        disabled=True,
        help="Bot sempre ativo"
    )
    
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
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.metric("MAX TRADES", st.session_state.bot.max_trades_simultaneos)
    with col_p2:
        st.metric("POSIÇÃO %", f"{st.session_state.bot.posicao_por_trade_percent}%")
    
    st.divider()
    
    # AÇÕES RÁPIDAS
    if st.button("🎯 FORÇAR ENTRADA", use_container_width=True, type="primary"):
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
        help="Cole qualquer token"
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
        help="Entra sem análise detalhada"
    )

if token_ca and (btn_analisar or btn_entrar_agressivo):
    token_data = buscar_token(token_ca.strip())
    
    if token_data:
        analise = st.session_state.analisador.analisar_token(token_data)
        
        # Mostrar resultado
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
        
        # BOTÃO DE ENTRADA
        if analise['confianca'] > 40 or btn_entrar_agressivo:
            st.success(f"✅ PRONTO PARA ENTRADA AGRESSIVA!")
            
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
        
        # Adicionar à lista de monitoramento
        if analise['confianca'] > 30:
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
# SEÇÃO 2: TRADES ATIVOS
# ==========================================================
st.header("📈 TRADES ATIVOS - MONITORAMENTO EM TEMPO REAL")

# Atualizar trades
trades_fechados = st.session_state.bot.atualizar_trades()

# Mostrar trades fechados recentemente
if trades_fechados:
    st.subheader("🔒 ÚLTIMOS FECHAMENTOS")
    for trade in trades_fechados[-5:]:
        profit = trade['profit_value']
        emoji = "🟢" if profit >= 0 else "🔴"
        
        col_f1, col_f2, col_f3 = st.columns([3, 2, 1])
        with col_f1:
            st.write(f"{emoji} **{trade['symbol']}** - {trade.get('exit_reason', 'N/A')}")
        with col_f2:
            st.write(f"⏱️ {trade.get('duracao_min', 0):.1f}min")
        with col_f3:
            st.write(f"**${profit:+.2f}** ({trade['profit_percent']:+.1f}%)")

# Mostrar trades ativos
if st.session_state.bot.trades_ativos:
    st.subheader(f"🟢 {len(st.session_state.bot.trades_ativos)} TRADES EM ABERTO")
    
    cols = st.columns(4)
    
    for idx, trade in enumerate(st.session_state.bot.trades_ativos):
        with cols[idx % 4]:
            with st.container(border=True):
                profit = trade['profit_percent']
                color = "🟢" if profit >= 0 else "🔴"
                
                # Cabeçalho colorido
                profit_color = "#00FF00" if profit >= 5 else "#FF0000" if profit <= -3 else "#FFA500"
                st.markdown(f"<div style='background-color:{profit_color}; padding:5px; border-radius:5px;'>", unsafe_allow_html=True)
                st.markdown(f"**{trade['symbol']}** ({trade.get('agressividade', 'N/A')})</div>", unsafe_allow_html=True)
                
                st.markdown(f"### {color} {profit:+.2f}%")
                st.caption(f"💰 ${trade['position_size']:.2f}")
                st.caption(f"🎯 TP: +{trade['analise']['take_profit_percent']}%")
                st.caption(f"⛔ SL: {trade['analise']['stop_loss_percent']}%")
                
                if st.button(f"⏹️ SAIR", key=f"exit_{trade['id']}", use_container_width=True):
                    trade['exit_reason'] = 'SAÍDA_MANUAL'
                    st.session_state.bot.fechar_trade(trade, [])
                    st.rerun()
else:
    st.info("📭 Nenhum trade ativo - Bot aguardando oportunidades")

# ==========================================================
# SEÇÃO 3: SISTEMA AUTOMÁTICO
# ==========================================================
st.header("🤖 SISTEMA AUTOMÁTICO - CAÇANDO OPORTUNIDADES")

if st.session_state.auto_mode and st.session_state.tokens_monitorados:
    for token in st.session_state.tokens_monitorados[:]:
        try:
            token_data = buscar_token(token['ca'])
            if token_data:
                analise = st.session_state.analisador.analisar_token(token_data)
                token['analise'] = analise
                
                if analise['confianca'] > 40:
                    trade = st.session_state.bot.criar_trade_agressivo(token_data, analise)
                    if trade:
                        token['entradas_tentadas'] += 1
                        st.success(f"⚡ ENTRADA AUTOMÁTICA em {trade['symbol']}")
        except:
            continue
    
    # Mostrar tokens monitorados
    if st.session_state.tokens_monitorados:
        st.subheader(f"🎯 {len(st.session_state.tokens_monitorados)} TOKENS EM MONITORAMENTO")
        
        for token in st.session_state.tokens_monitorados[-10:]:
            analise = token.get('analise', {})
            col_m1, col_m2, col_m3 = st.columns([2, 2, 1])
            
            with col_m1:
                st.write(f"**{token.get('symbol', 'N/A')}**")
                st.caption(f"Conf: {analise.get('confianca', 0):.0f}%")
            
            with col_m2:
                st.write(f"{analise.get('cor', '⚫')} {analise.get('decisao', 'N/A')}")
                st.caption(f"Vol: {analise.get('dados', {}).get('volatilidade', 0):.1f}")
            
            with col_m3:
                if st.button("🗑️", key=f"remove_{token['ca']}"):
                    st.session_state.tokens_monitorados.remove(token)
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
             delta=f"{stats['trades_ganhos']}/{stats['trades_total']}")

with col_s3:
    st.metric("⚡ TRADES/DIA", f"{stats['trades_dia']}",
             delta=f"${stats['lucro_dia']:+.2f}")

with col_s4:
    st.metric("🔥 MULT. RISCO", f"{stats['risk_multiplier']}x",
             delta=f"Streak: {stats['perdas_consecutivas']}")

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
        
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['lucro_acumulado'],
            mode='lines',
            name='Lucro Acumulado',
            line=dict(color='#00FF00', width=4)
        ))
        
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['media_movel'],
            mode='lines',
            name='Média Móvel (10)',
            line=dict(color='#FFA500', width=2, dash='dash')
        ))
        
        fig.update_layout(
            title='PERFORMANCE DO BOT',
            xaxis_title='Número do Trade',
            yaxis_title='Lucro Acumulado ($)',
            height=400,
            plot_bgcolor='#1E1E1E',
            paper_bgcolor='#1E1E1E',
            font=dict(color='white')
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
    section[data-testid="stSidebar"] > div {
        background-color: #0E1117;
        border-right: 1px solid #2D3746;
    }
    
    .st-emotion-cache-1cypcdb {
        background-color: #0E1117;
    }
    
    /* Textos brancos */
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        color: white !important;
    }
    
    /* Inputs com tema escuro */
    .stTextInput input, .stNumberInput input {
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
    
    /* Scrollbar personalizada */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1E1E1E;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #FF0000;
        border-radius: 4px;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #1E1E1E !important;
        color: white !important;
        border: 1px solid #2D3746 !important;
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
# AUTO-REFRESH
# ==========================================================
if st.session_state.auto_mode:
    time.sleep(15)
    st.rerun()