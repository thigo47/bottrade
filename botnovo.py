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
    page_title="Sniper Pro AI - Auto Trader",
    page_icon="🤖",
    layout="wide"
)

# ==========================================================
# SISTEMA DE ANÁLISE INTELIGENTE
# ==========================================================
class AnalisadorInteligente:
    """Sistema de análise automática para decisão de trades"""
    
    def __init__(self):
        self.parametros = {
            'volume_minimo': 50000,      # $50k mínimo
            'liquidez_minima': 20000,    # $20k mínimo
            'var_ideal_min': 5,          # 5% mínimo
            'var_ideal_max': 30,         # 30% máximo (evita pump)
            'buy_ratio_min': 0.6,        # 60% compras mínimo
            'confianca_minima': 70       # 70% confiança mínima
        }
    
    def analisar_token(self, token_data: Dict) -> Dict:
        """Analisa token e retorna decisão completa"""
        try:
            pair = token_data.get('pairs', [{}])[0]
            
            # Dados básicos
            symbol = pair.get('baseToken', {}).get('symbol', 'TOKEN')
            price = float(pair.get('priceUsd', 0))
            volume_24h = float(pair.get('volume', {}).get('h24', 0))
            liquidity = float(pair.get('liquidity', {}).get('usd', 0))
            price_change_24h = float(pair.get('priceChange', {}).get('h24', 0))
            
            # Dados de transações
            txns = pair.get('txns', {}).get('h24', {})
            buys = txns.get('buys', 0)
            sells = txns.get('sells', 0)
            buy_ratio = buys / (buys + sells) if (buys + sells) > 0 else 0
            
            # Calcula score (0-100)
            score = 0
            fatores = []
            
            # 1. Volume (0-30 pontos)
            if volume_24h > 100000:
                score += 30
                fatores.append("📈 Volume alto (>100k)")
            elif volume_24h > 50000:
                score += 20
                fatores.append("📊 Volume bom (>50k)")
            elif volume_24h > self.parametros['volume_minimo']:
                score += 10
                fatores.append("📉 Volume mínimo aceitável")
            else:
                fatores.append("❌ Volume insuficiente")
            
            # 2. Liquidez (0-25 pontos)
            if liquidity > 50000:
                score += 25
                fatores.append("💧 Liquidez excelente")
            elif liquidity > 20000:
                score += 15
                fatores.append("💦 Liquidez boa")
            elif liquidity > self.parametros['liquidez_minima']:
                score += 5
                fatores.append("💧 Liquidez mínima aceitável")
            else:
                fatores.append("❌ Liquidez insuficiente")
            
            # 3. Variação de preço (0-20 pontos)
            if self.parametros['var_ideal_min'] < price_change_24h < self.parametros['var_ideal_max']:
                score += 20
                fatores.append(f"🚀 Crescimento saudável ({price_change_24h:.1f}%)")
            elif price_change_24h > 0:
                score += 10
                fatores.append(f"📈 Em alta ({price_change_24h:.1f}%)")
            elif price_change_24h > -10:
                score += 5
                fatores.append(f"📉 Leve queda ({price_change_24h:.1f}%)")
            else:
                fatores.append(f"❌ Queda acentuada ({price_change_24h:.1f}%)")
            
            # 4. Relação compra/venda (0-15 pontos)
            if buy_ratio > 0.7:
                score += 15
                fatores.append(f"🟢 Forte demanda ({buy_ratio*100:.0f}% compras)")
            elif buy_ratio > self.parametros['buy_ratio_min']:
                score += 10
                fatores.append(f"🟡 Demanda positiva ({buy_ratio*100:.0f}% compras)")
            else:
                fatores.append(f"🔴 Mais vendas ({buy_ratio*100:.0f}% compras)")
            
            # 5. Dados adicionais (0-10 pontos)
            price_impact = pair.get('priceChange', {}).get('m5', 0)
            if isinstance(price_impact, (int, float)) and abs(price_impact) < 3:
                score += 10
                fatores.append("⚖️ Estável (baixo impacto)")
            else:
                fatores.append("🎢 Volátil")
            
            # Determinar decisão
            confianca = min(95, max(30, score))
            
            if score >= 70:
                decisao = "COMPRAR"
                risco = "BAIXO"
                stop_loss = -8  # -8%
                take_profit = 30  # +30%
                cor = "🟢"
                
            elif score >= 50:
                decisao = "AGUARDAR"
                risco = "MÉDIO"
                stop_loss = -10  # -10%
                take_profit = 25  # +25%
                cor = "🟡"
                
            else:
                decisao = "EVITAR"
                risco = "ALTO"
                stop_loss = -12  # -12%
                take_profit = 20  # +20%
                cor = "🔴"
            
            return {
                'decisao': decisao,
                'cor': cor,
                'confianca': confianca,
                'score': score,
                'risco': risco,
                'stop_loss_percent': stop_loss,
                'take_profit_percent': take_profit,
                'fatores': fatores,
                'dados': {
                    'symbol': symbol,
                    'price': price,
                    'volume': volume_24h,
                    'liquidez': liquidity,
                    'variacao': price_change_24h,
                    'buy_ratio': buy_ratio
                }
            }
            
        except Exception as e:
            return {
                'decisao': 'ERRO',
                'cor': '⚫',
                'confianca': 0,
                'score': 0,
                'risco': 'ALTO',
                'stop_loss_percent': -10,
                'take_profit_percent': 20,
                'fatores': [f"Erro na análise: {str(e)[:50]}"],
                'dados': {}
            }

# ==========================================================
# SISTEMA DE TRADING AUTOMÁTICO
# ==========================================================
class AutoTrader:
    """Sistema automático de execução de trades"""
    
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
            'win_rate': 0.0
        }
        self.max_trades_simultaneos = 10
        self.posicao_por_trade_percent = 10  # 10% por trade
    
    def calcular_posicao_trade(self) -> float:
        """Calcula valor para cada trade proporcionalmente"""
        num_trades_ativos = len(self.trades_ativos)
        
        if num_trades_ativos >= self.max_trades_simultaneos:
            return 0.0
        
        # Distribui igualmente entre trades disponíveis
        trades_disponiveis = self.max_trades_simultaneos - num_trades_ativos
        valor_por_trade = (self.saldo * (self.posicao_por_trade_percent / 100)) / trades_disponiveis
        
        return max(valor_por_trade, 1.0)  # Mínimo $1
    
    def criar_trade_automatico(self, token_data: Dict, analise: Dict) -> Optional[Dict]:
        """Cria trade automaticamente se análise for positiva"""
        
        if analise['decisao'] != 'COMPRAR':
            return None
        
        if analise['confianca'] < 70:
            return None
        
        # Verificar se já existe trade ativo para este token
        for trade in self.trades_ativos:
            if trade['ca'] == token_data.get('ca'):
                return None
        
        # Calcular valor do trade
        valor_trade = self.calcular_posicao_trade()
        
        if valor_trade <= 0 or valor_trade > self.saldo:
            return None
        
        # Dados do token
        price = analise['dados']['price']
        stop_loss = price * (1 + analise['stop_loss_percent'] / 100)
        take_profit = price * (1 + analise['take_profit_percent'] / 100)
        
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
            'trailing_stop': stop_loss
        }
        
        # Deduzir do saldo
        self.saldo -= valor_trade
        self.trades_ativos.append(trade)
        
        return trade
    
    def atualizar_trades(self):
        """Atualiza preços e executa saídas automáticas"""
        trades_fechados = []
        
        for trade in self.trades_ativos[:]:
            # Buscar preço atual
            try:
                url = f"https://api.dexscreener.com/latest/dex/tokens/{trade['ca']}"
                response = requests.get(url, timeout=5)
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
                        
                        # Verificar condições de saída
                        if self.verificar_saida_trade(trade):
                            self.fechar_trade(trade, trades_fechados)
            except:
                continue
        
        return trades_fechados
    
    def verificar_saida_trade(self, trade: Dict) -> bool:
        """Verifica se trade deve ser fechado"""
        current_price = trade['current_price']
        
        # TAKE PROFIT
        if current_price >= trade['take_profit']:
            trade['exit_reason'] = 'TAKE_PROFIT'
            return True
        
        # STOP LOSS
        if current_price <= trade['stop_loss']:
            trade['exit_reason'] = 'STOP_LOSS'
            return True
        
        # TRAILING STOP (ativa após 15% de gain)
        if trade['profit_percent'] >= 15:
            new_trailing = current_price * 0.85  # Mantém 15% do lucro
            if new_trailing > trade['trailing_stop']:
                trade['trailing_stop'] = new_trailing
            
            if current_price <= trade['trailing_stop']:
                trade['exit_reason'] = 'TRAILING_STOP'
                return True
        
        return False
    
    def fechar_trade(self, trade: Dict, trades_fechados: List):
        """Fecha trade e atualiza estatísticas"""
        trade['status'] = 'CLOSED'
        trade['exit_price'] = trade['current_price']
        trade['exit_time'] = datetime.now()
        
        # Adicionar lucro/perda ao saldo
        self.saldo += trade['position_size'] + trade['profit_value']
        
        # Atualizar estatísticas
        self.estatisticas['total_trades'] += 1
        
        if trade['profit_value'] > 0:
            self.estatisticas['trades_vencedores'] += 1
            self.estatisticas['lucro_total'] += trade['profit_value']
            self.estatisticas['maior_lucro'] = max(self.estatisticas['maior_lucro'], trade['profit_value'])
        else:
            self.estatisticas['trades_perdedores'] += 1
            self.estatisticas['lucro_total'] += trade['profit_value']
            self.estatisticas['maior_perda'] = min(self.estatisticas['maior_perda'], trade['profit_value'])
        
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
            'win_rate': round(self.estatisticas['win_rate'], 2),
            'lucro_total': round(self.estatisticas['lucro_total'], 2),
            'maior_lucro': round(self.estatisticas['maior_lucro'], 2),
            'maior_perda': round(self.estatisticas['maior_perda'], 2)
        }

# ==========================================================
# INICIALIZAÇÃO DO STREAMLIT
# ==========================================================
if 'trader' not in st.session_state:
    st.session_state.trader = AutoTrader(saldo_inicial=1000.0)

if 'analisador' not in st.session_state:
    st.session_state.analisador = AnalisadorInteligente()

if 'auto_mode' not in st.session_state:
    st.session_state.auto_mode = False

if 'monitorando' not in st.session_state:
    st.session_state.monitorando = []

# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================
def buscar_token(ca: str) -> Optional[Dict]:
    """Busca dados do token"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('pairs'):
                data['ca'] = ca
                return data
    except:
        pass
    return None

# ==========================================================
# INTERFACE PRINCIPAL
# ==========================================================
st.title("🤖 SNIPER PRO AI - AUTO TRADER PROFISSIONAL")
st.markdown("### Sistema Automático de Trading com Análise Inteligente")

# ==========================================================
# SIDEBAR - CONTROLES E CONFIGURAÇÕES
# ==========================================================
with st.sidebar:
    st.header("💰 CONTROLE DE SALDO")
    
    # Editor de saldo
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        novo_saldo = st.number_input(
            "Definir Saldo ($)",
            min_value=100.0,
            max_value=1000000.0,
            value=float(st.session_state.trader.saldo),
            step=100.0
        )
    
    with col_s2:
        if st.button("💾 ATUALIZAR", use_container_width=True):
            st.session_state.trader.saldo = novo_saldo
            st.success(f"Saldo atualizado: ${novo_saldo:,.2f}")
            st.rerun()
    
    st.divider()
    
    # Estatísticas
    stats = st.session_state.trader.get_estatisticas()
    
    st.metric("💵 SALDO ATUAL", f"${stats['saldo']:,.2f}")
    st.metric("📊 WIN RATE", f"{stats['win_rate']:.1f}%")
    st.metric("💰 LUCRO TOTAL", f"${stats['lucro_total']:+,.2f}")
    st.metric("📈 TRADES ATIVOS", stats['trades_ativos'])
    
    st.divider()
    
    # Configurações do sistema
    st.header("⚙️ CONFIGURAÇÕES")
    
    st.session_state.auto_mode = st.toggle(
        "🤖 MODO AUTOMÁTICO",
        value=st.session_state.auto_mode,
        help="Analisa e executa trades automaticamente"
    )
    
    st.number_input(
        "🎯 CONFIANÇA MÍNIMA (%)",
        min_value=50,
        max_value=95,
        value=70,
        key="conf_minima"
    )
    
    st.slider(
        "📊 TAMANHO POSIÇÃO/TOTAL (%)",
        min_value=1,
        max_value=20,
        value=10,
        key="pos_size_percent"
    )
    
    st.number_input(
        "🔢 MÁX. TRADES SIMULTÂNEOS",
        min_value=1,
        max_value=20,
        value=10,
        key="max_trades"
    )
    
    st.divider()
    
    # Ações rápidas
    if st.button("🔄 ATUALIZAR TRADES", use_container_width=True):
        fechados = st.session_state.trader.atualizar_trades()
        if fechados:
            st.success(f"{len(fechados)} trades atualizados!")
        st.rerun()
    
    if st.button("📊 EXPORTAR DADOS", use_container_width=True):
        if st.session_state.trader.historico_trades:
            df = pd.DataFrame(st.session_state.trader.historico_trades)
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇️ BAIXAR CSV",
                data=csv,
                file_name="trades_historico.csv",
                mime="text/csv"
            )
    
    if st.button("🧹 LIMPAR TUDO", type="secondary", use_container_width=True):
        st.session_state.trader = AutoTrader(saldo_inicial=1000.0)
        st.session_state.monitorando = []
        st.success("Sistema reiniciado!")
        st.rerun()

# ==========================================================
# SEÇÃO 1: ANALISAR E ADICIONAR TOKENS
# ==========================================================
st.header("🔍 ANALISAR TOKEN PARA TRADE")

col_input1, col_input2 = st.columns([3, 1])

with col_input1:
    token_ca = st.text_input(
        "Cole o CA do token:",
        placeholder="0x...",
        key="input_token_ca",
        help="Cole o Contract Address do token que deseja analisar"
    )

with col_input2:
    btn_analisar = st.button(
        "🔎 ANALISAR",
        type="primary",
        use_container_width=True,
        disabled=not token_ca
    )

if token_ca and btn_analisar:
    with st.spinner("Analisando token..."):
        token_data = buscar_token(token_ca.strip())
        
        if token_data:
            # Analisar token
            analise = st.session_state.analisador.analisar_token(token_data)
            
            # Mostrar resultado da análise
            st.subheader(f"📋 ANÁLISE: {analise['dados'].get('symbol', 'TOKEN')}")
            
            # Status da análise
            col_status1, col_status2, col_status3 = st.columns(3)
            
            with col_status1:
                st.metric(
                    "🎯 DECISÃO", 
                    analise['decisao'],
                    delta=f"{analise['confianca']:.0f}% confiança"
                )
            
            with col_status2:
                st.metric("📊 SCORE", f"{analise['score']}/100")
            
            with col_status3:
                st.metric("⚠️ RISCO", analise['risco'])
            
            # Dados do token
            st.subheader("📈 DADOS DO TOKEN")
            
            col_data1, col_data2, col_data3, col_data4 = st.columns(4)
            
            with col_data1:
                st.metric("💰 Preço", f"${analise['dados']['price']:.10f}")
            
            with col_data2:
                st.metric("📊 Volume", f"${analise['dados']['volume']:,.0f}")
            
            with col_data3:
                st.metric("💧 Liquidez", f"${analise['dados']['liquidez']:,.0f}")
            
            with col_data4:
                st.metric("📈 Variação", f"{analise['dados']['variacao']:.1f}%")
            
            # Fatores da análise
            with st.expander("📋 VER DETALHES DA ANÁLISE"):
                for fator in analise['fatores']:
                    st.write(f"• {fator}")
            
            # Parâmetros sugeridos
            st.subheader("⚙️ PARÂMETROS SUGERIDOS")
            
            price = analise['dados']['price']
            stop_price = price * (1 + analise['stop_loss_percent'] / 100)
            tp_price = price * (1 + analise['take_profit_percent'] / 100)
            
            col_param1, col_param2, col_param3 = st.columns(3)
            
            with col_param1:
                st.metric(
                    "⛔ Stop Loss", 
                    f"{analise['stop_loss_percent']}%",
                    f"${stop_price:.10f}"
                )
            
            with col_param2:
                st.metric(
                    "🎯 Take Profit",
                    f"+{analise['take_profit_percent']}%",
                    f"${tp_price:.10f}"
                )
            
            with col_param3:
                rr = abs(analise['take_profit_percent'] / analise['stop_loss_percent'])
                st.metric("📈 Risk/Reward", f"1:{rr:.1f}")
            
            # Botão para adicionar à lista de monitoramento
            if analise['decisao'] == 'COMPRAR' and analise['confianca'] >= st.session_state.get('conf_minima', 70):
                st.success("✅ TOKEN APROVADO PARA TRADE!")
                
                # Verificar se já está sendo monitorado
                ja_monitorando = any(m['ca'] == token_data['ca'] for m in st.session_state.monitorando)
                
                if not ja_monitorando:
                    if st.button("➕ ADICIONAR À LISTA DE TRADES", type="primary", use_container_width=True):
                        st.session_state.monitorando.append({
                            'ca': token_data['ca'],
                            'symbol': analise['dados']['symbol'],
                            'analise': analise,
                            'adicionado_em': datetime.now(),
                            'ultima_analise': datetime.now()
                        })
                        st.success(f"✅ {analise['dados']['symbol']} adicionado à lista!")
                        st.rerun()
                else:
                    st.info("ℹ️ Este token já está na lista de monitoramento")
            
            elif analise['decisao'] == 'AGUARDAR':
                st.warning("⚠️ AGUARDAR MELHOR OPORTUNIDADE")
            
            else:
                st.error("❌ EVITAR ESTE TOKEN")
        
        else:
            st.error("❌ Token não encontrado. Verifique o CA.")

# ==========================================================
# SEÇÃO 2: TOKENS MONITORADOS
# ==========================================================
if st.session_state.monitorando:
    st.header("📋 TOKENS NA LISTA DE TRADES")
    
    # Atualizar análises
    for token in st.session_state.monitorando[:]:
        try:
            token_data = buscar_token(token['ca'])
            if token_data:
                analise = st.session_state.analisador.analisar_token(token_data)
                token['analise'] = analise
                token['ultima_analise'] = datetime.now()
        except:
            continue
    
    # Mostrar tokens monitorados
    for idx, token in enumerate(st.session_state.monitorando):
        analise = token['analise']
        
        with st.container(border=True):
            col_t1, col_t2, col_t3, col_t4 = st.columns([2, 1, 1, 1])
            
            with col_t1:
                st.markdown(f"**{token['symbol']}**")
                st.caption(f"`{token['ca'][:20]}...`")
                st.caption(f"Adicionado: {token['adicionado_em'].strftime('%H:%M')}")
            
            with col_t2:
                st.markdown(f"{analise['cor']} **{analise['decisao']}**")
                st.caption(f"{analise['confianca']:.0f}% confiança")
            
            with col_t3:
                st.metric("Score", f"{analise['score']}/100")
            
            with col_t4:
                if st.button("🗑️ REMOVER", key=f"remove_{idx}", use_container_width=True):
                    st.session_state.monitorando.pop(idx)
                    st.rerun()

# ==========================================================
# SEÇÃO 3: TRADES ATIVOS
# ==========================================================
st.header("📈 TRADES ATIVOS")

# Atualizar trades ativos
trades_fechados = st.session_state.trader.atualizar_trades()

# Mostrar trades recentemente fechados
if trades_fechados:
    st.subheader("🔒 TRADES FECHADOS RECENTEMENTE")
    
    for trade in trades_fechados[-3:]:  # Últimos 3
        profit_color = "🟢" if trade['profit_value'] >= 0 else "🔴"
        
        with st.container(border=True):
            col_c1, col_c2, col_c3 = st.columns([2, 2, 1])
            
            with col_c1:
                st.markdown(f"**{trade['symbol']}** - {trade['exit_reason']}")
                st.caption(f"Entrada: ${trade['entry_price']:.10f}")
                st.caption(f"Saída: ${trade['exit_price']:.10f}")
            
            with col_c2:
                st.caption(f"Duração: {(trade['exit_time'] - trade['entry_time']).seconds // 60} min")
                st.caption(f"Valor: ${trade['position_size']:.2f}")
            
            with col_c3:
                st.markdown(f"**{profit_color} {trade['profit_percent']:+.2f}%**")
                st.markdown(f"**${trade['profit_value']:+.2f}**")

# Mostrar trades ativos
if st.session_state.trader.trades_ativos:
    st.subheader("🟢 TRADES EM ANDAMENTO")
    
    cols = st.columns(3)
    
    for idx, trade in enumerate(st.session_state.trader.trades_ativos[:9]):  # Máximo 9 por linha
        with cols[idx % 3]:
            with st.container(border=True, height=250):
                # Cabeçalho
                profit = trade['profit_percent']
                profit_color = "green" if profit >= 0 else "red"
                
                st.markdown(f"**{trade['symbol']}** (ID: {trade['id']})")
                st.markdown(f"<span style='color:{profit_color}; font-size:24px; font-weight:bold;'>{profit:+.2f}%</span>", 
                          unsafe_allow_html=True)
                
                # Informações
                st.caption(f"💰 Entrada: ${trade['entry_price']:.10f}")
                st.caption(f"📊 Atual: ${trade['current_price']:.10f}")
                st.caption(f"⛔ Stop: ${trade['stop_loss']:.10f}")
                st.caption(f"🎯 TP: ${trade['take_profit']:.10f}")
                st.caption(f"💵 Valor: ${trade['position_size']:.2f}")
                
                # Botão de saída manual
                if st.button("⏹️ SAIR MANUAL", key=f"manual_exit_{trade['id']}", use_container_width=True):
                    # Forçar fechamento
                    trade['exit_reason'] = 'MANUAL'
                    st.session_state.trader.fechar_trade(trade, [])
                    st.success(f"Trade {trade['symbol']} fechado manualmente!")
                    st.rerun()
else:
    st.info("📭 Nenhum trade ativo no momento.")

# ==========================================================
# SEÇÃO 4: SISTEMA DE TRADING AUTOMÁTICO
# ==========================================================
if st.session_state.auto_mode and st.session_state.monitorando:
    st.header("🤖 SISTEMA AUTOMÁTICO ATIVO")
    
    # Verificar tokens monitorados para entrada
    for token in st.session_state.monitorando:
        analise = token['analise']
        
        if analise['decisao'] == 'COMPRAR' and analise['confianca'] >= st.session_state.get('conf_minima', 70):
            # Buscar dados atualizados
            token_data = buscar_token(token['ca'])
            if token_data:
                # Tentar criar trade automático
                trade = st.session_state.trader.criar_trade_automatico(token_data, analise)
                
                if trade:
                    st.success(f"🤖 Trade automático iniciado para {trade['symbol']}!")
    
    st.info(f"🔄 Monitorando {len(st.session_state.monitorando)} tokens...")
    
    # Auto-refresh
    time.sleep(5)
    st.rerun()

# ==========================================================
# SEÇÃO 5: ESTATÍSTICAS E GRÁFICOS
# ==========================================================
st.header("📊 ESTATÍSTICAS DO SISTEMA")

stats = st.session_state.trader.get_estatisticas()

col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)

with col_stat1:
    st.metric("💵 SALDO", f"${stats['saldo']:,.2f}")

with col_stat2:
    st.metric("📊 WIN RATE", f"{stats['win_rate']:.1f}%")

with col_stat3:
    st.metric("💰 LUCRO TOTAL", f"${stats['lucro_total']:+,.2f}")

with col_stat4:
    st.metric("📈 TRADES ATIVOS", stats['trades_ativos'])

with col_stat5:
    st.metric("🔢 TOTAL TRADES", stats['trades_total'])

# Gráfico de performance
if st.session_state.trader.historico_trades:
    df = pd.DataFrame(st.session_state.trader.historico_trades)
    
    if 'profit_value' in df.columns:
        df['lucro_acumulado'] = df['profit_value'].cumsum()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['lucro_acumulado'],
            mode='lines+markers',
            name='Lucro Acumulado',
            line=dict(color='green', width=3)
        ))
        
        fig.update_layout(
            title='Desempenho dos Trades',
            xaxis_title='Número do Trade',
            yaxis_title='Lucro Acumulado ($)',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

# ==========================================================
# FOOTER
# ==========================================================
st.divider()

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption(f"🔄 Última atualização: {datetime.now().strftime('%H:%M:%S')}")

with footer_col2:
    st.caption(f"📋 Tokens monitorados: {len(st.session_state.monitorando)}")

with footer_col3:
    if st.session_state.auto_mode:
        st.caption("🤖 AUTO: 🟢 ATIVO")
    else:
        st.caption("🤖 AUTO: 🔴 INATIVO")

# ==========================================================
# CSS PARA INTERFACE PROFISSIONAL
# ==========================================================
st.markdown("""
<style>
    /* Interface profissional */
    .stButton > button {
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s ease;
        border: none;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    .stButton > button[kind="secondary"] {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
    }
    
    /* Inputs elegantes */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 2px solid #e0e0e0;
        transition: all 0.3s;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Métricas destacadas */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: bold;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem;
        color: #666;
    }
    
    /* Containers com sombra */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        padding: 20px;
        margin-bottom: 20px;
        background: white;
    }
    
    /* Títulos gradientes */
    h1, h2, h3 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-top: 1.5rem;
    }
    
    /* Sidebar moderna */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    /* Divider personalizado */
    hr {
        margin: 2rem 0;
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #667eea, transparent);
    }
    
    /* Cards de trade */
    .trade-card {
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid;
        background: white;
    }
    
    .trade-buy {
        border-left-color: #28a745;
        background: linear-gradient(90deg, rgba(40, 167, 69, 0.1) 0%, white 100%);
    }
    
    .trade-sell {
        border-left-color: #dc3545;
        background: linear-gradient(90deg, rgba(220, 53, 69, 0.1) 0%, white 100%);
    }
    
    /* Responsividade mobile */
    @media (max-width: 768px) {
        .stButton > button {
            font-size: 14px;
            padding: 8px 16px;
        }
        
        [data-testid="stMetricValue"] {
            font-size: 1.4rem;
        }
        
        h1 { font-size: 1.8rem; }
        h2 { font-size: 1.5rem; }
        h3 { font-size: 1.2rem; }
    }
</style>
""", unsafe_allow_html=True)
