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
        hovermode='x unified',
        showlegend=True
    )
    
    return fig

def criar_grafico_distribuicao_simples():
    """Cria gráfico de distribuição sem scipy"""
    if not st.session_state.historico_trades:
        return None
    
    trades = st.session_state.historico_trades
    profits = [t['profit_loss'] for t in trades]
    
    if len(profits) < 2:
        return None
    
    fig = go.Figure()
    
    # Histograma simples
    fig.add_trace(go.Histogram(
        x=profits,
        nbinsx=15,
        name='Distribuição',
        marker_color='#1f77b4',
        opacity=0.75,
        hovertemplate='Lucro: $%{x:.2f}<br>Frequência: %{y}<extra></extra>'
    ))
    
    # Linha de média móvel simples (sem scipy)
    if len(profits) > 5:
        # Calcular histograma manualmente
        hist, bin_edges = np.histogram(profits, bins=15)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        # Suavização simples
        window_size = 3
        smoothed = np.convolve(hist, np.ones(window_size)/window_size, mode='valid')
        smoothed_centers = bin_centers[:len(smoothed)]
        
        fig.add_trace(go.Scatter(
            x=smoothed_centers,
            y=smoothed,
            mode='lines',
            name='Tendência',
            line=dict(color='#FFA500', width=2),
            yaxis='y2'
        ))
    
    # Linha vertical na média
    mean_profit = np.mean(profits)
    fig.add_vline(
        x=mean_profit, 
        line_dash="dash", 
        line_color="yellow",
        annotation_text=f"Média: ${mean_profit:.2f}",
        annotation_position="top right"
    )
    
    # Linha vertical em zero
    fig.add_vline(
        x=0, 
        line_dash="solid", 
        line_color="white",
        annotation_text="Break Even",
        annotation_position="bottom right"
    )
    
    fig.update_layout(
        title='📊 Distribuição dos Lucros/Prejuízos',
        xaxis_title='Lucro/Prejuízo ($)',
        yaxis_title='Frequência',
        yaxis2=dict(
            title='Tendência',
            overlaying='y',
            side='right',
            showgrid=False
        ),
        template='plotly_dark',
        height=300,
        bargap=0.1,
        showlegend=True
    )
    
    return fig

def criar_grafico_tipo_trades():
    """Cria gráfico de pizza por tipo de token"""
    if not st.session_state.historico_trades:
        return None
    
    trades = st.session_state.historico_trades
    type_counts = {}
    
    for trade in trades:
        ttype = trade.get('token_type', 'UNKNOWN')
        type_counts[ttype] = type_counts.get(ttype, 0) + 1
    
    if not type_counts:
        return None
    
    labels = list(type_counts.keys())
    values = list(type_counts.values())
    
    # Cores por tipo
    color_map = {
        'MEME': '#FF6B6B',
        'ALT': '#4ECDC4',
        'MAIN': '#45B7D1',
        'DEFI': '#96CEB4',
        'STABLE': '#FECA57',
        'UNKNOWN': '#999999'
    }
    
    colors = [color_map.get(label, '#999999') for label in labels]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.3,
        marker_colors=colors,
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>Trades: %{value}<br>Percentual: %{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        title='🎯 Distribuição por Tipo de Token',
        template='plotly_dark',
        height=300,
        showlegend=True
    )
    
    return fig

# ==========================================================
# INTERFACE PRINCIPAL
# ==========================================================

# Título principal
st.markdown("""
<div style="text-align: center; padding: 20px; background: linear-gradient(45deg, #1a1a2e, #16213e); border-radius: 10px; margin-bottom: 20px;">
    <h1 style="color: #00FFFF; margin: 0;">🚀 SNIPER AI PRO - AUTO TRADING BOT</h1>
    <p style="color: #CCCCCC; font-size: 18px;">Sistema Automático com Suporte a Memecoins | Entradas em Tempo Real</p>
</div>
""", unsafe_allow_html=True)

# ==========================================================
# BARRA LATERAL (COMPLETA)
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
    
    # GESTÃO DE SALDO
    st.markdown("---")
    st.markdown("### 💰 GESTÃO DE SALDO")
    
    # Saldo atual
    st.metric(
        label="SALDO ATUAL",
        value=f"${st.session_state.saldo:,.2f}",
        delta=f"{st.session_state.estatisticas['lucro_dia']:+.2f} (Dia)"
    )
    
    # Editar saldo
    with st.expander("✏️ EDITAR SALDO", expanded=False):
        novo_saldo = st.number_input(
            "Definir novo saldo:",
            min_value=100.0,
            max_value=1000000.0,
            value=float(st.session_state.saldo),
            step=100.0,
            key="input_novo_saldo"
        )
        
        col_edit1, col_edit2 = st.columns(2)
        with col_edit1:
            if st.button("💾 Salvar", use_container_width=True):
                st.session_state.saldo = float(novo_saldo)
                st.success(f"✅ Saldo atualizado: ${novo_saldo:,.2f}")
        
        with col_edit2:
            if st.button("🔄 Resetar", use_container_width=True, type="secondary"):
                st.session_state.saldo = 10000.0
                st.session_state.estatisticas['lucro_total'] = 0.0
                st.session_state.estatisticas['roi_total'] = 0.0
                st.success("✅ Saldo resetado para $10,000")
    
    # GESTÃO DE TOKENS
    st.markdown("---")
    st.markdown("### 🎯 GESTÃO DE TOKENS")
    
    with st.expander("➕ ADICIONAR TOKEN", expanded=False):
        # Input para adicionar token
        token_ca = st.text_input(
            "CA do Token:",
            placeholder="0x...",
            key="input_token_ca",
            help="Cole o Contract Address do token"
        )
        
        col_token1, col_token2 = st.columns(2)
        with col_token1:
            token_name = st.text_input(
                "Nome (opcional):",
                placeholder="Ex: SHIB, DOGE",
                key="input_token_name"
            )
        
        with col_token2:
            token_type = st.selectbox(
                "Tipo:",
                ["MEME", "ALT", "MAIN", "DEFI", "STABLE", "CUSTOM"],
                index=0,
                key="select_token_type"
            )
        
        if st.button("➕ Adicionar Token", use_container_width=True):
            if token_ca and len(token_ca) > 10:
                success = st.session_state.trading_engine.add_custom_token(
                    token_ca, 
                    token_name if token_name else "CUSTOM",
                    token_type
                )
                if success:
                    st.success(f"✅ Token {token_type} adicionado!")
                    if token_ca not in st.session_state.custom_tokens:
                        st.session_state.custom_tokens.append(token_ca)
                else:
                    st.warning("⚠️ Token já existe na lista")
            else:
                st.error("❌ CA inválido")
    
    # Lista de tokens
    with st.expander("📋 TOKENS MONITORADOS", expanded=False):
        token_info = st.session_state.trading_engine.get_token_pool_info()
        
        st.write(f"**Total:** {token_info['total_tokens']} tokens")
        
        for ttype, count in token_info['types_distribution'].items():
            st.write(f"• {ttype}: {count}")
        
        # Mostrar alguns tokens
        st.write("**Alguns tokens na lista:**")
        for token in token_info['token_list'][:5]:
            st.code(f"{token['name']} ({token['type']})", language=None)
    
    # Controles principais
    st.markdown("---")
    st.markdown("### 🎮 CONTROLES PRINCIPAIS")
    
    # Botão para forçar entrada
    if st.button("🎯 FORÇAR ENTRADA MANUAL", use_container_width=True, type="primary"):
        # Criar sinal de teste
        token_types = ["MEME", "ALT", "MAIN"]
        selected_type = random.choice(token_types)
        
        sinal_teste = {
            'symbol': f'TEST{random.randint(100, 999)}',
            'price': random.uniform(0.00001, 0.01) if selected_type == "MEME" else random.uniform(0.001, 0.1),
            'score': random.randint(65, 95),
            'confidence': random.choice(['LOW', 'MEDIUM', 'HIGH']),
            'stop_loss': 0.0008 if selected_type == "MEME" else 0.001,
            'take_profit': 0.0012 if selected_type == "MEME" else 0.0015,
            'volume': random.randint(10000, 100000),
            'timestamp': datetime.now(),
            'token_type': selected_type
        }
        
        trade = executar_trade(sinal_teste)
        if trade:
            st.success(f"✅ Trade manual: {trade['symbol']} ({trade['token_type']})")
        else:
            st.error("❌ Não foi possível executar o trade")
    
    # Configurações
    st.markdown("---")
    st.markdown("### ⚙️ CONFIGURAÇÕES AVANÇADAS")
    
    st.session_state.config['auto_trading'] = st.toggle(
        "Trading Automático",
        value=st.session_state.config['auto_trading'],
        help="Ativa/desativa entradas automáticas"
    )
    
    st.session_state.config['memecoin_aggressive'] = st.toggle(
        "Modo Agressivo Memecoins",
        value=st.session_state.config['memecoin_aggressive'],
        help="Entradas mais agressivas em memecoins"
    )
    
    st.session_state.config['max_trades_ativos'] = st.slider(
        "Máx. Trades Ativos",
        min_value=1,
        max_value=25,
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
    if st.button("🧹 LIMPAR TUDO", use_container_width=True, type="secondary"):
        st.session_state.trades_ativos = []
        st.session_state.historico_trades = []
        st.session_state.estatisticas['trades_hoje'] = 0
        st.session_state.estatisticas['lucro_dia'] = 0
        st.session_state.estatisticas['total_trades'] = 0
        st.session_state.estatisticas['trades_ganhos'] = 0
        st.session_state.estatisticas['trades_perdidos'] = 0
        st.success("✅ Sistema limpo com sucesso!")

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
                    # Verificar se é memecoin e se o modo agressivo está ativo
                    if item['token_type'] == "MEME" and not st.session_state.config['memecoin_aggressive']:
                        continue  # Pular memecoins se modo não agressivo
                    
                    trade = executar_trade(item['data'])
                    if trade:
                        # Mostrar notificação
                        emoji = "🐕" if trade['token_type'] == "MEME" else "📈"
                        st.toast(f"{emoji} AUTO: {trade['symbol']} | Score: {item['data']['score']} | Tipo: {trade['token_type']}")
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
    lucro_dia_color = "normal" if st.session_state.estatisticas['lucro_dia'] >= 0 else "inverse"
    st.metric(
        "Lucro Hoje",
        f"${st.session_state.estatisticas['lucro_dia']:+.2f}",
        f"Trades: {st.session_state.estatisticas['trades_hoje']}",
        delta_color=lucro_dia_color
    )

# ==========================================================
# LINHA 2: GRÁFICOS
# ==========================================================
col_graph1, col_graph2, col_graph3 = st.columns([2, 1, 1])

with col_graph1:
    # Gráfico de performance
    fig_performance = criar_grafico_performance()
    if fig_performance:
        st.plotly_chart(fig_performance, use_container_width=True)
    else:
        st.info("⏳ Aguardando dados de trades para mostrar performance...")

with col_graph2:
    # Gráfico de distribuição (CORRIGIDO)
    fig_distribuicao = criar_grafico_distribuicao_simples()
    if fig_distribuicao:
        st.plotly_chart(fig_distribuicao, use_container_width=True)
    else:
        st.info("📊 Coletando dados para distribuição...")

with col_graph3:
    # Gráfico de tipos de trade
    fig_tipos = criar_grafico_tipo_trades()
    if fig_tipos:
        st.plotly_chart(fig_tipos, use_container_width=True)
    
    # Estatísticas rápidas
    st.markdown("### 📊 RESUMO POR TIPO")
    if st.session_state.historico_trades:
        tipos = {}
        for trade in st.session_state.historico_trades:
            ttype = trade.get('token_type', 'UNKNOWN')
            if ttype not in tipos:
                tipos[ttype] = {'count': 0, 'total_profit': 0}
            tipos[ttype]['count'] += 1
            tipos[ttype]['total_profit'] += trade['profit_loss']
        
        for ttype, data in list(tipos.items())[:3]:
            avg = data['total_profit'] / data['count'] if data['count'] > 0 else 0
            st.metric(f"{ttype}", f"{data['count']} trades", f"${avg:+.2f} médio")

# ==========================================================
# LINHA 3: TRADES ATIVOS
# ==========================================================
st.markdown("### 🎯 TRADES EM ANDAMENTO")

if st.session_state.trades_ativos:
    # Organizar por tipo
    memecoin_trades = [t for t in st.session_state.trades_ativos if t.get('token_type') == "MEME"]
    other_trades = [t for t in st.session_state.trades_ativos if t.get('token_type') != "MEME"]
    
    # Mostrar memecoins primeiro (se houver)
    if memecoin_trades:
        st.markdown("#### 🐕 MEMECOINS")
        memecoin_df = pd.DataFrame(memecoin_trades)
        
        if not memecoin_df.empty:
            display_cols = ['symbol', 'entry_price', 'current_price', 'profit_loss_percent', 
                          'profit_loss', 'score', 'volume']
            
            if all(col in memecoin_df.columns for col in display_cols):
                display_df = memecoin_df[display_cols].copy()
                display_df.columns = ['Símbolo', 'Entrada', 'Atual', 'P/L %', 'P/L $', 'Score', 'Volume']
                
                # Formatando valores
                display_df['Entrada'] = display_df['Entrada'].apply(lambda x: f"${x:.8f}")
                display_df['Atual'] = display_df['Atual'].apply(lambda x: f"${x:.8f}")
                display_df['P/L %'] = display_df['P/L %'].apply(lambda x: f"{x:+.2f}%")
                display_df['P/L $'] = display_df['P/L $'].apply(lambda x: f"${x:+.2f}")
                display_df['Volume'] = display_df['Volume'].apply(lambda x: f"${x:,.0f}")
                
                # Colorir P/L
                def color_pl(val):
                    try:
                        if '%' in val:
                            num = float(val.replace('%', '').replace('+', ''))
                        else:
                            num = float(val.replace('$', '').replace('+', ''))
                        
                        if num > 0:
                            return 'color: #00FF00; font-weight: bold; background-color: #003300;'
                        elif num < 0:
                            return 'color: #FF0000; font-weight: bold; background-color: #330000;'
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
    
    # Mostrar outros trades
    if other_trades:
        st.markdown("#### 📈 OUTROS TOKENS")
        other_df = pd.DataFrame(other_trades)
        
        if not other_df.empty and len(other_df) > 0:
            display_cols = ['symbol', 'token_type', 'entry_price', 'current_price', 
                          'profit_loss_percent', 'profit_loss', 'score']
            
            if all(col in other_df.columns for col in display_cols):
                display_df = other_df[display_cols].copy()
                display_df.columns = ['Símbolo', 'Tipo', 'Entrada', 'Atual', 'P/L %', 'P/L $', 'Score']
                
                # Formatando valores
                display_df['Entrada'] = display_df['Entrada'].apply(lambda x: f"${x:.6f}")
                display_df['Atual'] = display_df['Atual'].apply(lambda x: f"${x:.6f}")
                display_df['P/L %'] = display_df['P/L %'].apply(lambda x: f"{x:+.2f}%")
                display_df['P/L $'] = display_df['P/L $'].apply(lambda x: f"${x:+.2f}")
                
                # Aplicar estilo
                styled_df = display_df.style.applymap(color_pl, subset=['P/L %', 'P/L $'])
                
                # Mostrar tabela
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True
                )
    
    # Botões de ação
    st.markdown("#### 🎮 AÇÕES RÁPIDAS")
    if st.session_state.trades_ativos:
        # Fechar todos os trades
        if st.button("⏹️ FECHAR TODOS OS TRADES", use_container_width=True, type="primary"):
            for trade in st.session_state.trades_ativos[:]:
                fechar_trade(trade, 'MANUAL_ALL', [])
            st.rerun()
        
        # Fechar apenas memecoins
        if memecoin_trades:
            if st.button("⏹️ FECHAR TODOS MEMECOINS", use_container_width=True):
                for trade in memecoin_trades:
                    if trade in st.session_state.trades_ativos:
                        fechar_trade(trade, 'MANUAL_MEME', [])
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
        
        # Mostrar pool de tokens
        token_info = st.session_state.trading_engine.get_token_pool_info()
        st.caption(f"📋 Monitorando {token_info['total_tokens']} tokens")

# ==========================================================
# LINHA 4: HISTÓRICO RECENTE
# ==========================================================
if st.session_state.historico_trades:
    st.markdown("### 📋 HISTÓRICO RECENTE")
    
    # Últimos 5 trades fechados
    recent_trades = st.session_state.historico_trades[-5:]
    
    for trade in reversed(recent_trades):
        profit = trade['profit_loss']
        emoji = "🐕" if trade.get('token_type') == "MEME" else ("🟢" if profit > 0 else "🔴")
        
        col_hist1, col_hist2, col_hist3, col_hist4 = st.columns([2, 2, 2, 1])
        
        with col_hist1:
            type_badge = f"`{trade.get('token_type', 'UNKNOWN')}`"
            st.write(f"{emoji} **{trade['symbol']}** {type_badge}")
            st.caption(f"{trade.get('exit_reason', 'N/A')}")
        
        with col_hist2:
            st.write(f"**Entrada:** ${trade['entry_price']:.8f}")
            st.write(f"**Saída:** ${trade.get('exit_price', 0):.8f}")
        
        with col_hist3:
            duration = "N/A"
            if 'entry_time' in trade and 'exit_time' in trade:
                if isinstance(trade['entry_time'], datetime) and isinstance(trade['exit_time'], datetime):
                    duration_seconds = (trade['exit_time'] - trade['entry_time']).seconds
                    duration = f"{duration_seconds // 60}:{duration_seconds % 60:02d}"
            
            st.write(f"**Duração:** {duration}")
            st.write(f"**Score:** {trade.get('score', 0)}")
        
        with col_hist4:
            profit_color = "🟢" if profit > 0 else "🔴"
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
        status = "🤖 **AUTO ATIVO**"
        if st.session_state.config['memecoin_aggressive']:
            status += " | 🐕 **MEME AGGRESSIVE**"
        st.caption(status)
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
        transition: all 0.3s;
    }
    
    .stMetric:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0, 255, 255, 0.3);
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
    
    /* Badges para tipos de token */
    [class*="st-emotion-cache"] code {
        background: linear-gradient(45deg, #FF6B6B, #FF8E53) !important;
        color: white !important;
        padding: 2px 8px !important;
        border-radius: 12px !important;
        font-size: 12px !important;
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
        margin: 2px 0;
    }
    
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 0 15px #00FFFF;
    }
    
    /* Tabelas */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #00FFFF;
    }
    
    .dataframe th {
        background: #1a1a2e !important;
        color: #00FFFF !important;
        font-weight: bold !important;
        text-align: center !important;
    }
    
    .dataframe td {
        background: #16213e !important;
        color: #FFFFFF !important;
        text-align: center !important;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background: #1a1a2e !important;
        color: #00FFFF !important;
        font-weight: bold !important;
        border-radius: 5px;
    }
    
    /* Sliders */
    .stSlider > div > div {
        background: #00FFFF !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: #1a1a2e;
        border-radius: 5px 5px 0 0;
        padding: 10px 20px;
    }
    
    .stTabs [aria-selected="true"] {
        background: #00FFFF !important;
        color: #000000 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# AUTO-REFRESH
# ==========================================================

# Auto-refresh a cada 3 segundos
time.sleep(3)
st.rerun()