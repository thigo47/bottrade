import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import random
import threading
import queue
import json
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
        
        # Pool de tokens otimizado
        self.token_pool = [
            # Tokens líquidos e populares
            {"ca": "0x2170Ed0880ac9A755fd29B2688956BD959F933F8", "name": "ETH"},
            {"ca": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", "name": "BNB"},
            {"ca": "0x55d398326f99059fF775485246999027B3197955", "name": "USDT"},
            {"ca": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82", "name": "CAKE"},
            {"ca": "0x1CE0c2827e2eF14D5C4f29a091d735A204794041", "name": "AVAX"},
            {"ca": "0xCC42724C6683B7E57334c4E856f4c9965ED682bD", "name": "MATIC"},
            {"ca": "0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE", "name": "XRP"},
            {"ca": "0x4338665CBB7B2485A8855A139b75D5e34AB0DB94", "name": "LTC"},
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
    
    def analyze_token(self, token_data):
        """Análise rápida e eficiente"""
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
            
            # Critério 1: Volume suficiente
            if volume_24h > 50000:
                score += 25
            elif volume_24h > 10000:
                score += 15
            else:
                return None  # Volume muito baixo
            
            # Critério 2: Momentum positivo
            if change_5m > 2:
                score += 35
                if change_1h > 1:
                    score += 20
            elif change_5m > 0:
                score += 15
            
            # Critério 3: Liquidez
            if liquidity > 100000:
                score += 20
            elif liquidity > 50000:
                score += 10
            
            # Critério 4: Preço adequado
            if 0.00001 < price < 0.01:
                score += 20
            
            # Se score for alto o suficiente, criar sinal
            if score >= 60:
                symbol = token_data.get('baseToken', {}).get('symbol', 'TOKEN')
                
                # Definir stop loss e take profit dinâmicos
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
                    'timestamp': datetime.now()
                }
                
        except Exception as e:
            print(f"Erro na análise: {e}")
        
        return None
    
    def scan_tokens(self):
        """Escaneia tokens em busca de oportunidades"""
        while self.running:
            try:
                current_time = datetime.now()
                
                # Intervalo entre scans (ajustável)
                if (current_time - self.last_scan).total_seconds() < 2:  # 2 segundos
                    time.sleep(0.1)
                    continue
                
                self.stats['total_scans'] += 1
                
                # Selecionar tokens aleatoriamente
                tokens_to_scan = random.sample(
                    self.token_pool, 
                    min(3, len(self.token_pool))
                )
                
                for token_info in tokens_to_scan:
                    # Buscar dados
                    token_data = self.fetch_token_data(token_info['ca'])
                    
                    if token_data:
                        # Analisar
                        signal = self.analyze_token(token_data)
                        
                        if signal:
                            self.stats['signals_found'] += 1
                            self.stats['last_signal_time'] = current_time
                            
                            # Adicionar à fila
                            self.trade_queue.put({
                                'type': 'TRADE_SIGNAL',
                                'data': signal,
                                'token_ca': token_info['ca'],
                                'token_name': token_info['name']
                            })
                
                self.last_scan = current_time
                time.sleep(0.5)  # Pausa curta entre ciclos
                
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
        'frequencia_scan': 2.0
    }
    st.session_state.trading_engine = TradingEngine()
    st.session_state.trading_engine.start()
    st.session_state.ultima_atualizacao = datetime.now()

# ==========================================================
# FUNÇÕES DE TRADING
# ==========================================================

def executar_trade(sinal):
    """Executa um trade baseado no sinal"""
    try:
        # Calcular tamanho do trade
        tamanho_trade = st.session_state.saldo * (st.session_state.config['tamanho_trade_percent'] / 100)
        tamanho_trade = min(tamanho_trade, 100)  # Máximo $100 por trade
        
        if tamanho_trade < 1 or tamanho_trade > st.session_state.saldo * 0.9:
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
            'profit_loss_percent': 0.0
        }
        
        # Atualizar saldo
        st.session_state.saldo -= tamanho_trade
        
        # Adicionar à lista de trades ativos
        st.session_state.trades_ativos.append(trade)
        
        # Atualizar estatísticas
        st.session_state.estatisticas['total_trades'] += 1
        st.session_state.estatisticas['trades_hoje'] += 1
        
        return trade
        
    except Exception as e:
        print(f"Erro ao executar trade: {e}")
        return None

def atualizar_trades():
    """Atualiza todos os trades ativos"""
    trades_fechados = []
    
    for trade in st.session_state.trades_ativos[:]:
        try:
            # Simular variação de preço (em produção, buscar da API)
            # Para demonstração, simular variação aleatória
            variation = random.uniform(-0.02, 0.03)  # -2% a +3%
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
        
    except Exception as e:
        print(f"Erro ao fechar trade: {e}")

# ==========================================================
# FUNÇÕES DE INTERFACE
# ==========================================================

def criar_grafico_performance():
    """Cria gráfico de performance"""
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
            marker=dict(color='#00FF00', size=10, symbol='circle')
        ))
    
    if len(negative_trades) > 0:
        fig.add_trace(go.Scatter(
            x=negative_trades.index,
            y=negative_trades['cumulative_profit'],
            mode='markers',
            name='Trades Negativos',
            marker=dict(color='#FF0000', size=10, symbol='x')
        ))
    
    # Layout do gráfico
    fig.update_layout(
        title='📈 Performance dos Trades',
        xaxis_title='Número do Trade',
        yaxis_title='Lucro Acumulado ($)',
        template='plotly_dark',
        height=400,
        hovermode='x unified'
    )
    
    return fig

def criar_grafico_distribuicao():
    """Cria gráfico de distribuição dos trades"""
    if not st.session_state.historico_trades:
        return None
    
    trades = st.session_state.historico_trades
    profits = [t['profit_loss'] for t in trades]
    
    fig = go.Figure()
    
    # Histograma
    fig.add_trace(go.Histogram(
        x=profits,
        nbinsx=20,
        name='Distribuição',
        marker_color='#1f77b4',
        opacity=0.75
    ))
    
    # Linha de densidade
    if len(profits) > 1:
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(profits)
        x_range = np.linspace(min(profits), max(profits), 100)
        fig.add_trace(go.Scatter(
            x=x_range,
            y=kde(x_range) * len(profits) * (max(profits) - min(profits)) / 20,
            mode='lines',
            name='Densidade',
            line=dict(color='#FFA500', width=2)
        ))
    
    fig.update_layout(
        title='📊 Distribuição dos Lucros/Prejuízos',
        xaxis_title='Lucro/Prejuízo ($)',
        yaxis_title='Frequência',
        template='plotly_dark',
        height=300,
        bargap=0.1
    )
    
    return fig

# ==========================================================
# INTERFACE PRINCIPAL
# ==========================================================

# Título principal
st.markdown("""
<div style="text-align: center; padding: 20px; background: linear-gradient(45deg, #1a1a2e, #16213e); border-radius: 10px; margin-bottom: 20px;">
    <h1 style="color: #00FFFF; margin: 0;">🚀 SNIPER AI PRO - AUTO TRADING BOT</h1>
    <p style="color: #CCCCCC; font-size: 18px;">Sistema Automático de Alta Frequência | Entradas em Tempo Real</p>
</div>
""", unsafe_allow_html=True)

# ==========================================================
# BARRA LATERAL
# ==========================================================
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 10px; background: #1a1a2e; border-radius: 10px; margin-bottom: 20px;">
        <h3 style="color: #00FFFF; margin: 0;">⚙️ PAINEL DE CONTROLE</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Status do sistema
    st.markdown("### 📊 STATUS DO SISTEMA")
    
    col_status1, col_status2 = st.columns(2)
    with col_status1:
        status_color = "🟢" if st.session_state.config['auto_trading'] else "🔴"
        st.metric("Modo Auto", status_color)
    
    with col_status2:
        engine_stats = st.session_state.trading_engine.get_stats()
        st.metric("Scans", engine_stats['total_scans'])
    
    # Saldo e estatísticas
    st.markdown("---")
    st.markdown("### 💰 FINANCEIRO")
    
    st.metric(
        label="SALDO ATUAL",
        value=f"${st.session_state.saldo:,.2f}",
        delta=f"{st.session_state.estatisticas['lucro_dia']:+.2f} (Dia)"
    )
    
    # Controles principais
    st.markdown("---")
    st.markdown("### 🎮 CONTROLES")
    
    # Botão para forçar entrada
    if st.button("🎯 FORÇAR ENTRADA MANUAL", use_container_width=True, type="primary"):
        # Criar sinal de teste
        sinal_teste = {
            'symbol': 'TEST' + str(random.randint(100, 999)),
            'price': random.uniform(0.001, 0.01),
            'score': random.randint(70, 95),
            'confidence': random.choice(['LOW', 'MEDIUM', 'HIGH']),
            'stop_loss': 0.0008,
            'take_profit': 0.0012,
            'volume': random.randint(10000, 100000),
            'timestamp': datetime.now()
        }
        
        trade = executar_trade(sinal_teste)
        if trade:
            st.success(f"✅ Trade manual executado: {trade['symbol']}")
        else:
            st.error("❌ Não foi possível executar o trade")
    
    # Configurações
    st.markdown("---")
    st.markdown("### ⚙️ CONFIGURAÇÕES")
    
    st.session_state.config['auto_trading'] = st.toggle(
        "Trading Automático",
        value=st.session_state.config['auto_trading'],
        help="Ativa/desativa entradas automáticas"
    )
    
    st.session_state.config['max_trades_ativos'] = st.slider(
        "Máx. Trades Ativos",
        min_value=1,
        max_value=20,
        value=st.session_state.config['max_trades_ativos'],
        help="Número máximo de trades simultâneos"
    )
    
    st.session_state.config['tamanho_trade_percent'] = st.slider(
        "Tamanho do Trade (%)",
        min_value=0.5,
        max_value=5.0,
        value=st.session_state.config['tamanho_trade_percent'],
        step=0.5,
        help="Percentual do saldo por trade"
    )
    
    # Botão de limpeza
    if st.button("🧹 LIMPAR HISTÓRICO", use_container_width=True, type="secondary"):
        st.session_state.historico_trades = []
        st.session_state.estatisticas['trades_hoje'] = 0
        st.session_state.estatisticas['lucro_dia'] = 0
        st.success("Histórico limpo com sucesso!")

# ==========================================================
# ÁREA PRINCIPAL
# ==========================================================

# Atualizar trades
trades_fechados = atualizar_trades()

# Processar fila do motor de trading
if st.session_state.config['auto_trading']:
    engine = st.session_state.trading_engine
    try:
        while not engine.trade_queue.empty():
            item = engine.trade_queue.get_nowait()
            
            if item['type'] == 'TRADE_SIGNAL':
                # Verificar se podemos abrir mais trades
                if len(st.session_state.trades_ativos) < st.session_state.config['max_trades_ativos']:
                    trade = executar_trade(item['data'])
                    if trade:
                        # Mostrar notificação
                        st.toast(f"✅ AUTO: {trade['symbol']} | Score: {item['data']['score']}")
    except:
        pass

# ==========================================================
# LINHA 1: ESTATÍSTICAS PRINCIPAIS
# ==========================================================
st.markdown("### 📈 DASHBOARD DE PERFORMANCE")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Win Rate",
        f"{st.session_state.estatisticas['win_rate']:.1f}%",
        f"{st.session_state.estatisticas['trades_ganhos']}/{st.session_state.estatisticas['total_trades']}"
    )

with col2:
    st.metric(
        "ROI Total",
        f"{st.session_state.estatisticas['roi_total']:.2f}%",
        f"${st.session_state.estatisticas['lucro_total']:+.2f}"
    )

with col3:
    trades_ativos = len(st.session_state.trades_ativos)
    st.metric(
        "Trades Ativos",
        trades_ativos,
        f"Max: {st.session_state.config['max_trades_ativos']}"
    )

with col4:
    st.metric(
        "Trades Hoje",
        st.session_state.estatisticas['trades_hoje'],
        f"Lucro: ${st.session_state.estatisticas['lucro_dia']:+.2f}"
    )

# ==========================================================
# LINHA 2: GRÁFICOS
# ==========================================================
col_graph1, col_graph2 = st.columns([2, 1])

with col_graph1:
    # Gráfico de performance
    fig_performance = criar_grafico_performance()
    if fig_performance:
        st.plotly_chart(fig_performance, use_container_width=True)
    else:
        st.info("⏳ Aguardando dados de trades para mostrar performance...")

with col_graph2:
    # Gráfico de distribuição
    fig_distribuicao = criar_grafico_distribuicao()
    if fig_distribuicao:
        st.plotly_chart(fig_distribuicao, use_container_width=True)
    
    # Estatísticas rápidas
    st.markdown("### 📊 RESUMO")
    if st.session_state.historico_trades:
        profits = [t['profit_loss'] for t in st.session_state.historico_trades]
        st.metric("Lucro Médio", f"${np.mean(profits):.2f}")
        st.metric("Melhor Trade", f"${st.session_state.estatisticas['melhor_trade']:.2f}")
        st.metric("Pior Trade", f"${st.session_state.estatisticas['pior_trade']:.2f}")

# ==========================================================
# LINHA 3: TRADES ATIVOS
# ==========================================================
st.markdown("### 🎯 TRADES EM ANDAMENTO")

if st.session_state.trades_ativos:
    # Criar DataFrame para display
    trades_df = pd.DataFrame(st.session_state.trades_ativos)
    
    # Selecionar e formatar colunas
    display_cols = ['symbol', 'entry_price', 'current_price', 'profit_loss_percent', 
                   'profit_loss', 'score', 'confidence']
    
    if all(col in trades_df.columns for col in display_cols):
        display_df = trades_df[display_cols].copy()
        display_df.columns = ['Símbolo', 'Entrada', 'Atual', 'P/L %', 'P/L $', 'Score', 'Confiança']
        
        # Formatando valores
        display_df['Entrada'] = display_df['Entrada'].apply(lambda x: f"${x:.8f}")
        display_df['Atual'] = display_df['Atual'].apply(lambda x: f"${x:.8f}")
        display_df['P/L %'] = display_df['P/L %'].apply(lambda x: f"{x:+.2f}%")
        display_df['P/L $'] = display_df['P/L $'].apply(lambda x: f"${x:+.2f}")
        
        # Colorir P/L
        def color_pl(val):
            try:
                num = float(val.replace('%', '').replace('$', '').replace('+', ''))
                if num > 0:
                    return 'color: #00FF00; font-weight: bold;'
                elif num < 0:
                    return 'color: #FF0000; font-weight: bold;'
                else:
                    return 'color: #CCCCCC;'
            except:
                return ''
        
        # Aplicar estilo
        styled_df = display_df.style.applymap(color_pl, subset=['P/L %', 'P/L $'])
        
        # Mostrar tabela
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("Algumas colunas não estão disponíveis nos dados.")
    
    # Botões de ação para cada trade
    st.markdown("#### 🎮 Ações Rápidas")
    cols_actions = st.columns(min(4, len(st.session_state.trades_ativos)))
    
    for idx, trade in enumerate(st.session_state.trades_ativos[:4]):
        with cols_actions[idx % 4]:
            if st.button(f"⏹️ Fechar {trade['symbol']}", key=f"close_{trade['id']}", use_container_width=True):
                fechar_trade(trade, 'MANUAL', [])
                st.rerun()
else:
    st.info("📭 Nenhum trade ativo no momento. O sistema está escaneando o mercado...")
    
    # Mostrar status do scanner
    engine_stats = st.session_state.trading_engine.get_stats()
    if engine_stats['total_scans'] > 0:
        st.caption(f"🔍 Scanner ativo: {engine_stats['total_scans']} scans realizados")
        if engine_stats['last_signal_time']:
            last_signal = (datetime.now() - engine_stats['last_signal_time']).seconds
            st.caption(f"⏰ Último sinal: há {last_signal} segundos")

# ==========================================================
# LINHA 4: HISTÓRICO RECENTE
# ==========================================================
if st.session_state.historico_trades:
    st.markdown("### 📋 HISTÓRICO RECENTE")
    
    # Últimos 5 trades fechados
    recent_trades = st.session_state.historico_trades[-5:]
    
    for trade in reversed(recent_trades):
        profit = trade['profit_loss']
        emoji = "🟢" if profit > 0 else "🔴"
        
        col_hist1, col_hist2, col_hist3, col_hist4 = st.columns([2, 2, 2, 1])
        
        with col_hist1:
            st.write(f"{emoji} **{trade['symbol']}**")
            st.caption(f"{trade.get('exit_reason', 'N/A')}")
        
        with col_hist2:
            st.write(f"**Entrada:** ${trade['entry_price']:.6f}")
            st.write(f"**Saída:** ${trade.get('exit_price', 0):.6f}")
        
        with col_hist3:
            duration = "N/A"
            if 'entry_time' in trade and 'exit_time' in trade:
                if isinstance(trade['entry_time'], datetime) and isinstance(trade['exit_time'], datetime):
                    duration_seconds = (trade['exit_time'] - trade['entry_time']).seconds
                    duration = f"{duration_seconds // 60}:{duration_seconds % 60:02d}"
            
            st.write(f"**Duração:** {duration}")
            st.write(f"**Score:** {trade.get('score', 0)}")
        
        with col_hist4:
            st.metric("", f"{trade['profit_loss_percent']:+.2f}%", f"${profit:+.2f}")
        
        st.divider()

# ==========================================================
# RODAPÉ E STATUS
# ==========================================================
st.markdown("---")

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption(f"🔄 Última atualização: {datetime.now().strftime('%H:%M:%S')}")

with footer_col2:
    engine_stats = st.session_state.trading_engine.get_stats()
    st.caption(f"🔍 Scans: {engine_stats['total_scans']} | Sinais: {engine_stats['signals_found']}")

with footer_col3:
    if st.session_state.config['auto_trading']:
        st.caption("🤖 **MODO AUTOMÁTICO ATIVO**")
    else:
        st.caption("⏸️ **MODO MANUAL**")

# ==========================================================
# CSS PERSONALIZADO
# ==========================================================
st.markdown("""
<style>
    /* Estilos gerais */
    .stMetric {
        background: linear-gradient(45deg, #1a1a2e, #16213e);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #00FFFF;
    }
    
    .stMetric label {
        color: #CCCCCC !important;
        font-size: 14px !important;
    }
    
    .stMetric div {
        color: #FFFFFF !important;
        font-size: 24px !important;
        font-weight: bold !important;
    }
    
    /* Botões */
    .stButton > button {
        background: linear-gradient(45deg, #00FFFF, #0080FF);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 0 15px #00FFFF;
    }
    
    /* Tabelas */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
    }
    
    .dataframe th {
        background: #1a1a2e !important;
        color: #00FFFF !important;
        font-weight: bold !important;
    }
    
    .dataframe td {
        background: #16213e !important;
        color: #FFFFFF !important;
    }
    
    /* Toggle */
    .st-cb {
        background: #1a1a2e !important;
    }
    
    /* Sliders */
    .stSlider > div > div {
        background: #00FFFF !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# AUTO-REFRESH
# ==========================================================

# Auto-refresh a cada 3 segundos
time.sleep(3)
st.rerun()