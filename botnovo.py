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
    page_title="🚀 SNIPER AI PRO - SEUS TOKENS",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# SISTEMA DE TRADING - MOTOR PRINCIPAL
# ==========================================================
class TradingEngine:
    """Motor de trading que roda em background - SEM TOKENS PRÉ-DEFINIDOS"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.trade_queue = queue.Queue()
        self.last_scan = datetime.now()
        self.stats = {
            'total_scans': 0,
            'signals_found': 0,
            'trades_executed': 0,
            'last_signal_time': None,
            'tokens_monitorados': 0
        }
        
        # LISTA VAZIA - VOCÊ ADICIONA OS TOKENS QUE QUISER
        self.token_pool = []
        
        # Tokens de exemplo (só para teste - remova se quiser começar 100% vazio)
        self.example_tokens = [
            {"ca": "0x2170Ed0880ac9A755fd29B2688956BD959F933F8", "name": "ETH", "type": "MAIN"},
            {"ca": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", "name": "BNB", "type": "MAIN"},
            {"ca": "0x55d398326f99059fF775485246999027B3197955", "name": "USDT", "type": "STABLE"},
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
        except Exception as e:
            print(f"Erro ao buscar token {ca}: {e}")
        return None
    
    def analyze_token(self, token_data, token_type="CUSTOM"):
        """Análise rápida e eficiente"""
        try:
            price = float(token_data.get('priceUsd', 0))
            volume_24h = float(token_data.get('volume', {}).get('h24', 0))
            
            price_change = token_data.get('priceChange', {})
            change_5m = float(price_change.get('m5', 0))
            change_1h = float(price_change.get('h1', 0))
            
            # Score de oportunidade
            score = 0
            
            # Critério 1: Volume (mais flexível para tokens personalizados)
            if volume_24h > 100000:
                score += 40
            elif volume_24h > 50000:
                score += 30
            elif volume_24h > 10000:
                score += 20
            elif volume_24h > 5000:
                score += 10
            else:
                return None  # Volume muito baixo
            
            # Critério 2: Momentum
            if change_5m > 5:  # +5% em 5min
                score += 50
            elif change_5m > 2:
                score += 30
            elif change_5m > 0:
                score += 15
            elif change_5m < -5:  # Queda forte
                score -= 20  # Penalidade maior
            
            # Critério 3: Tendência consistente
            if change_5m > 0 and change_1h > 0:
                score += 25
            
            # Critério 4: Preço adequado para trading
            if price > 0.00000001 and price < 0.1:
                score += 20
            elif price < 1.0:
                score += 10
            
            # Se score for alto o suficiente
            if score >= 60:
                symbol = token_data.get('baseToken', {}).get('symbol', 'TOKEN')
                
                # Definir stop loss e take profit dinâmicos
                if score >= 80:
                    stop_loss = 0.96  # -4%
                    take_profit = 1.05  # +5%
                    confidence = "HIGH"
                elif score >= 70:
                    stop_loss = 0.97  # -3%
                    take_profit = 1.04  # +4%
                    confidence = "MEDIUM"
                else:
                    stop_loss = 0.98  # -2%
                    take_profit = 1.03  # +3%
                    confidence = "LOW"
                
                return {
                    'symbol': symbol,
                    'price': price,
                    'score': score,
                    'confidence': confidence,
                    'stop_loss': price * stop_loss,
                    'take_profit': price * take_profit,
                    'volume': volume_24h,
                    'change_5m': change_5m,
                    'change_1h': change_1h,
                    'timestamp': datetime.now(),
                    'token_type': token_type
                }
                
        except Exception as e:
            print(f"Erro na análise: {e}")
        return None
    
    def add_token(self, ca, name="TOKEN", token_type="CUSTOM"):
        """Adiciona um token à lista de monitoramento"""
        ca = ca.strip()
        
        # Validar formato básico do CA
        if not ca.startswith("0x") or len(ca) < 20:
            return False, "CA inválido"
        
        # Verificar se já existe
        if any(t['ca'].lower() == ca.lower() for t in self.token_pool):
            return False, "Token já existe"
        
        # Verificar se o token existe na blockchain
        token_data = self.fetch_token_data(ca)
        if not token_data:
            return False, "Token não encontrado na API"
        
        # Obter símbolo real do token
        symbol = token_data.get('baseToken', {}).get('symbol', name)
        
        new_token = {
            "ca": ca,
            "name": symbol,
            "type": token_type,
            "added_time": datetime.now(),
            "last_checked": datetime.now(),
            "total_scans": 0,
            "signals_found": 0
        }
        
        self.token_pool.append(new_token)
        self.stats['tokens_monitorados'] = len(self.token_pool)
        
        return True, f"✅ {symbol} adicionado com sucesso!"
    
    def remove_token(self, ca):
        """Remove um token da lista"""
        initial_count = len(self.token_pool)
        self.token_pool = [t for t in self.token_pool if t['ca'] != ca]
        removed = initial_count - len(self.token_pool)
        
        if removed > 0:
            self.stats['tokens_monitorados'] = len(self.token_pool)
            return True, f"Token removido"
        return False, "Token não encontrado"
    
    def clear_all_tokens(self):
        """Remove todos os tokens"""
        count = len(self.token_pool)
        self.token_pool = []
        self.stats['tokens_monitorados'] = 0
        return count
    
    def load_example_tokens(self):
        """Carrega tokens de exemplo (opcional)"""
        loaded = 0
        for token in self.example_tokens:
            success, _ = self.add_token(token['ca'], token['name'], token['type'])
            if success:
                loaded += 1
        return loaded
    
    def get_token_info(self, ca):
        """Retorna informações de um token específico"""
        for token in self.token_pool:
            if token['ca'] == ca:
                return token
        return None
    
    def scan_tokens(self):
        """Escaneia tokens em busca de oportunidades"""
        while self.running:
            try:
                current_time = datetime.now()
                
                # Intervalo entre scans
                if (current_time - self.last_scan).total_seconds() < 3:  # 3 segundos
                    time.sleep(0.1)
                    continue
                
                self.stats['total_scans'] += 1
                
                # Se não houver tokens, esperar
                if len(self.token_pool) == 0:
                    time.sleep(1)
                    continue
                
                # Selecionar até 3 tokens para escanear
                tokens_to_scan = random.sample(
                    self.token_pool, 
                    min(3, len(self.token_pool))
                )
                
                for token_info in tokens_to_scan:
                    # Atualizar contagem de scans
                    token_info['total_scans'] = token_info.get('total_scans', 0) + 1
                    token_info['last_checked'] = current_time
                    
                    # Buscar dados
                    token_data = self.fetch_token_data(token_info['ca'])
                    
                    if token_data:
                        signal = self.analyze_token(token_data, token_info['type'])
                        
                        if signal:
                            self.stats['signals_found'] += 1
                            self.stats['last_signal_time'] = current_time
                            token_info['signals_found'] = token_info.get('signals_found', 0) + 1
                            
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
        stats = self.stats.copy()
        stats['token_pool_count'] = len(self.token_pool)
        return stats

# ==========================================================
# INICIALIZAÇÃO DO SISTEMA
# ==========================================================

if 'initialized' not in st.session_state:
    st.session_state.update({
        'initialized': True,
        'saldo': 1000.0,
        'trades_ativos': [],
        'historico_trades': [],
        'estatisticas': {
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
        },
        'config': {
            'auto_trading': True,
            'max_trades_ativos': 5,
            'tamanho_trade_percent': 1.0,
            'use_examples': False  # Não usar exemplos por padrão
        },
        'ultima_atualizacao': datetime.now(),
        'token_manager_tab': "adicionar"  # Controla a aba ativa
    })
    
    # Inicializar motor de trading vazio
    st.session_state.trading_engine = TradingEngine()
    st.session_state.trading_engine.start()

# ==========================================================
# FUNÇÕES DE TRADING
# ==========================================================

def executar_trade(sinal):
    """Executa um trade baseado no sinal"""
    try:
        base_percent = st.session_state.config['tamanho_trade_percent']
        tamanho_trade = st.session_state.saldo * (base_percent / 100)
        tamanho_trade = min(tamanho_trade, 50)
        
        if tamanho_trade < 0.50:
            return None
        
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
            'confidence': sinal.get('confidence', 'MEDIUM'),
            'profit_loss': 0.0,
            'profit_loss_percent': 0.0,
            'token_type': sinal.get('token_type', 'CUSTOM'),
            'volume': sinal.get('volume', 0)
        }
        
        st.session_state.saldo -= tamanho_trade
        st.session_state.trades_ativos.append(trade)
        st.session_state.estatisticas['total_trades'] += 1
        st.session_state.estatisticas['trades_hoje'] += 1
        
        print(f"✅ Trade: {trade['symbol']} | Score: {trade['score']}")
        return trade
        
    except Exception as e:
        print(f"Erro ao executar trade: {e}")
        return None

def atualizar_trades():
    """Atualiza todos os trades ativos"""
    trades_fechados = []
    
    for trade in st.session_state.trades_ativos[:]:
        try:
            variation = random.uniform(-0.03, 0.04)
            current_price = trade['entry_price'] * (1 + variation)
            trade['current_price'] = current_price
            
            profit_loss = (current_price - trade['entry_price']) / trade['entry_price'] * 100
            profit_loss_value = trade['position_size'] * (profit_loss / 100)
            
            trade['profit_loss'] = profit_loss_value
            trade['profit_loss_percent'] = profit_loss
            
            if current_price >= trade['take_profit']:
                fechar_trade(trade, 'TAKE_PROFIT', trades_fechados)
            elif current_price <= trade['stop_loss']:
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
        
        retorno = trade['position_size'] + trade['profit_loss']
        st.session_state.saldo += retorno
        
        stats = st.session_state.estatisticas
        
        if trade['profit_loss'] > 0:
            stats['trades_ganhos'] += 1
            stats['melhor_trade'] = max(stats['melhor_trade'], trade['profit_loss'])
        else:
            stats['trades_perdidos'] += 1
            stats['pior_trade'] = min(stats['pior_trade'], trade['profit_loss'])
        
        stats['lucro_total'] += trade['profit_loss']
        stats['lucro_dia'] += trade['profit_loss']
        
        if stats['total_trades'] > 0:
            stats['win_rate'] = (stats['trades_ganhos'] / stats['total_trades']) * 100
        
        if st.session_state.saldo > 0:
            stats['roi_total'] = ((st.session_state.saldo - 1000) / 1000) * 100
        
        st.session_state.historico_trades.append(trade.copy())
        st.session_state.trades_ativos.remove(trade)
        trades_fechados.append(trade)
        
        print(f"📊 Trade fechado: {trade['symbol']} | P&L: ${trade['profit_loss']:.2f}")
        
    except Exception as e:
        print(f"Erro ao fechar trade: {e}")

# ==========================================================
# INTERFACE PRINCIPAL
# ==========================================================

st.markdown("""
<div style="text-align: center; padding: 20px; background: linear-gradient(45deg, #1a1a2e, #16213e); border-radius: 10px; margin-bottom: 20px;">
    <h1 style="color: #00FFFF; margin: 0;">🚀 SNIPER AI PRO - SEUS TOKENS</h1>
    <p style="color: #CCCCCC; font-size: 18px;">Adicione apenas os tokens que você quer monitorar</p>
</div>
""", unsafe_allow_html=True)

# ==========================================================
# BARRA LATERAL - GESTÃO DE TOKENS (VERSÃO PARA CELULAR)
# ==========================================================
with st.sidebar:
    st.markdown("### 🎯 GESTÃO DE TOKENS")
    
    # Tabs para gerenciamento de tokens
    tab1, tab2, tab3 = st.tabs(["➕ Adicionar", "📋 Lista", "⚙️ Config"])
    
    with tab1:
        st.markdown("#### Adicionar Novo Token")
        
        # Input para CA do token - VERSÃO PARA CELULAR
        token_ca = st.text_input(
            "CA do Token:",
            placeholder="Cole o Contract Address aqui (0x...)",
            key="input_token_ca_mobile",
            help="Cole o endereço do contrato do token. Exemplo: 0x2170Ed0880ac9A755fd29B2688956BD959F933F8"
        )
        
        col_name, col_type = st.columns(2)
        with col_name:
            token_name = st.text_input(
                "Nome personalizado:",
                placeholder="Ex: ETH, BNB, etc",
                key="input_token_name_mobile"
            )
        
        with col_type:
            token_type = st.selectbox(
                "Tipo:",
                ["MEME", "ALT", "DEFI", "STABLE", "CUSTOM"],
                index=0,
                key="select_token_type_mobile"
            )
        
        # Botão para adicionar um token
        if st.button("✅ Adicionar Token", use_container_width=True, type="primary", key="btn_add_single"):
            if token_ca.strip():
                success, message = st.session_state.trading_engine.add_token(
                    token_ca.strip(), 
                    token_name if token_name else "TOKEN",
                    token_type
                )
                
                if success:
                    st.success(message)
                    # Limpar o campo após adicionar
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
            else:
                st.error("❌ Por favor, cole o CA do token")
        
        st.markdown("---")
        st.markdown("#### Adicionar Múltiplos Tokens")
        
        # Opção para múltiplos tokens
        multiple_tokens = st.text_area(
            "Vários CAs (um por linha):",
            placeholder="Cole vários CAs, um por linha\n0x...\n0x...\n0x...",
            height=80,
            key="input_multiple_tokens",
            help="Para adicionar vários tokens de uma vez"
        )
        
        if st.button("📥 Adicionar Vários Tokens", use_container_width=True, key="btn_add_multiple"):
            if multiple_tokens.strip():
                tokens_list = [ca.strip() for ca in multiple_tokens.strip().split('\n') if ca.strip()]
                
                added = 0
                errors = []
                
                for ca in tokens_list:
                    success, message = st.session_state.trading_engine.add_token(
                        ca, 
                        "TOKEN",  # Nome genérico
                        token_type
                    )
                    
                    if success:
                        added += 1
                    else:
                        errors.append(f"{ca[:15]}...: {message}")
                
                if added > 0:
                    st.success(f"✅ {added} token(s) adicionado(s)!")
                
                if errors:
                    st.warning(f"⚠️ {len(errors)} token(s) falharam:")
                    for error in errors:
                        st.error(error)
                
                st.rerun()
            else:
                st.warning("⚠️ Cole pelo menos um CA")
    
    with tab2:
        st.markdown("#### Tokens Monitorados")
        
        engine = st.session_state.trading_engine
        token_count = len(engine.token_pool)
        
        if token_count == 0:
            st.info("📭 Nenhum token adicionado ainda")
            
            # Opção para carregar exemplos
            if st.button("📥 Carregar Tokens de Exemplo", use_container_width=True):
                loaded = engine.load_example_tokens()
                st.success(f"✅ {loaded} tokens de exemplo carregados")
                st.rerun()
        else:
            st.metric("Tokens Monitorados", token_count)
            
            # Listar tokens com opção de remover
            for i, token in enumerate(engine.token_pool[:10]):  # Mostrar apenas 10
                with st.expander(f"{token['name']} ({token['type']})", expanded=False):
                    col_t1, col_t2 = st.columns([3, 1])
                    
                    with col_t1:
                        st.code(token['ca'][:30] + "...", language="text")
                        st.caption(f"Adicionado: {token.get('added_time', 'N/A')}")
                        st.caption(f"Scans: {token.get('total_scans', 0)} | Sinais: {token.get('signals_found', 0)}")
                    
                    with col_t2:
                        if st.button("🗑️", key=f"remove_{token['ca'][:10]}"):
                            success, message = engine.remove_token(token['ca'])
                            if success:
                                st.success("Token removido!")
                                time.sleep(0.5)
                                st.rerun()
            
            # Botão para limpar todos
            if st.button("🗑️ Limpar Todos os Tokens", use_container_width=True, type="secondary"):
                count = engine.clear_all_tokens()
                st.success(f"✅ {count} tokens removidos")
                time.sleep(0.5)
                st.rerun()
    
    with tab3:
        st.markdown("#### Configurações do Motor")
        
        st.checkbox(
            "Auto Trading",
            value=st.session_state.config['auto_trading'],
            key="auto_trading",
            help="Executa trades automaticamente quando sinais são encontrados"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            st.number_input(
                "Máx. Trades Ativos",
                min_value=1,
                max_value=20,
                value=st.session_state.config['max_trades_ativos'],
                key="max_trades_ativos"
            )
        
        with col2:
            st.number_input(
                "% por Trade",
                min_value=0.1,
                max_value=10.0,
                value=st.session_state.config['tamanho_trade_percent'],
                key="tamanho_trade_percent",
                format="%.1f"
            )
        
        # Atualizar configurações
        if st.button("💾 Salvar Configurações", use_container_width=True):
            st.session_state.config.update({
                'auto_trading': st.session_state.auto_trading,
                'max_trades_ativos': st.session_state.max_trades_ativos,
                'tamanho_trade_percent': st.session_state.tamanho_trade_percent
            })
            st.success("Configurações salvas!")

# ==========================================================
# PRINCIPAL - DASHBOARD
# ==========================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("💰 Saldo", f"${st.session_state.saldo:.2f}")
with col2:
    st.metric("📊 Win Rate", f"{st.session_state.estatisticas['win_rate']:.1f}%")
with col3:
    st.metric("🎯 Trades Ativos", len(st.session_state.trades_ativos))

# Estatísticas do motor
engine = st.session_state.trading_engine
stats = engine.get_stats()

col4, col5, col6 = st.columns(3)
with col4:
    st.metric("🔍 Total Scans", stats['total_scans'])
with col5:
    st.metric("🚨 Sinais Encontrados", stats['signals_found'])
with col6:
    st.metric("📈 Tokens Monitorados", stats['tokens_monitorados'])

# Processar sinais da fila
if st.session_state.config['auto_trading'] and stats['signals_found'] > 0:
    try:
        while not engine.trade_queue.empty():
            signal = engine.trade_queue.get_nowait()
            if signal['type'] == 'TRADE_SIGNAL':
                # Verificar se já não temos muitos trades
                if len(st.session_state.trades_ativos) < st.session_state.config['max_trades_ativos']:
                    trade = executar_trade(signal['data'])
                    if trade:
                        st.success(f"🚀 Trade executado: {trade['symbol']} | Score: {trade['score']}")
    except queue.Empty:
        pass

# Atualizar trades ativos
if st.session_state.trades_ativos:
    trades_fechados = atualizar_trades()
    if trades_fechados:
        for trade in trades_fechados:
            emoji = "✅" if trade['profit_loss'] > 0 else "❌"
            st.info(f"{emoji} Trade fechado: {trade['symbol']} | P&L: ${trade['profit_loss']:.2f}")

# Seção de trades ativos
st.markdown("### 📈 Trades Ativos")
if st.session_state.trades_ativos:
    trades_df = pd.DataFrame(st.session_state.trades_ativos)
    
    # Formatar colunas
    trades_display = trades_df.copy()
    trades_display['entry_price'] = trades_display['entry_price'].apply(lambda x: f"${x:.6f}")
    trades_display['current_price'] = trades_display['current_price'].apply(lambda x: f"${x:.6f}")
    trades_display['stop_loss'] = trades_display['stop_loss'].apply(lambda x: f"${x:.6f}")
    trades_display['take_profit'] = trades_display['take_profit'].apply(lambda x: f"${x:.6f}")
    trades_display['profit_loss'] = trades_display['profit_loss'].apply(lambda x: f"${x:.2f}")
    trades_display['profit_loss_percent'] = trades_display['profit_loss_percent'].apply(lambda x: f"{x:.2f}%")
    
    st.dataframe(
        trades_display[['symbol', 'entry_price', 'current_price', 'profit_loss', 'profit_loss_percent', 'confidence']],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("📭 Nenhum trade ativo no momento")

# Gráfico de performance
st.markdown("### 📊 Performance")
if st.session_state.historico_trades:
    hist_df = pd.DataFrame(st.session_state.historico_trades)
    
    if not hist_df.empty:
        hist_df['cumulative_pnl'] = hist_df['profit_loss'].cumsum() + 1000
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hist_df['exit_time'],
            y=hist_df['cumulative_pnl'],
            mode='lines+markers',
            name='Patrimônio',
            line=dict(color='#00FFAA', width=3),
            fill='tozeroy',
            fillcolor='rgba(0, 255, 170, 0.1)'
        ))
        
        fig.update_layout(
            title="Evolução do Patrimônio",
            xaxis_title="Data",
            yaxis_title="Patrimônio ($)",
            template="plotly_dark",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

# Seção de histórico de trades
st.markdown("### 📋 Histórico de Trades")
if st.session_state.historico_trades:
    hist_display = pd.DataFrame(st.session_state.historico_trades[-10:])  # Últimos 10 trades
    
    if not hist_display.empty:
        # Formatar colunas
        hist_display['entry_price'] = hist_display['entry_price'].apply(lambda x: f"${x:.6f}")
        hist_display['exit_price'] = hist_display['exit_price'].apply(lambda x: f"${x:.6f}")
        hist_display['profit_loss'] = hist_display['profit_loss'].apply(lambda x: f"${x:.2f}")
        hist_display['profit_loss_percent'] = hist_display['profit_loss_percent'].apply(lambda x: f"{x:.2f}%")
        
        # Adicionar emoji para resultado
        def get_emoji(pl):
            return "✅" if float(pl.replace('$', '')) > 0 else "❌"
        
        hist_display['result'] = hist_display['profit_loss'].apply(get_emoji)
        
        st.dataframe(
            hist_display[['result', 'symbol', 'entry_price', 'exit_price', 'profit_loss', 'profit_loss_percent', 'exit_reason']],
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("📭 Nenhum trade no histórico")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 12px;">
    <p>🚀 SNIPER AI PRO - Sistema de trading automatizado | Use por sua conta e risco</p>
    <p>⚠️ Este é um simulador educacional. Não use com dinheiro real.</p>
</div>
""", unsafe_allow_html=True)

# Atualizar a página automaticamente
if st.button("🔄 Atualizar Dados", use_container_width=True):
    st.rerun()

# Auto-refresh a cada 30 segundos
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.now()

if (datetime.now() - st.session_state.last_refresh).seconds > 30:
    st.session_state.last_refresh = datetime.now()
    st.rerun()