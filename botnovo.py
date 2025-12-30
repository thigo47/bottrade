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
# BARRA LATERAL - GESTÃO DE TOKENS
# ==========================================================
with st.sidebar:
    st.markdown("### 🎯 GESTÃO DE TOKENS")
    
    # Tabs para gerenciamento de tokens
    tab1, tab2, tab3 = st.tabs(["➕ Adicionar", "📋 Lista", "⚙️ Config"])
    
    with tab1:
        st.markdown("#### Adicionar Novo Token")
        
        # Input para CA do token
        token_ca = st.text_area(
            "CA do Token:",
            placeholder="Cole o Contract Address aqui\nEx: 0x2170Ed0880ac9A755fd29B2688956BD959F933F8",
            height=100,
            key="input_token_ca"
        )
        
        col_name, col_type = st.columns(2)
        with col_name:
            token_name = st.text_input(
                "Nome personalizado:",
                placeholder="Deixe em branco para usar o símbolo oficial",
                key="input_token_name"
            )
        
        with col_type:
            token_type = st.selectbox(
                "Tipo:",
                ["MEME", "ALT", "DEFI", "STABLE", "CUSTOM"],
                index=0,
                key="select_token_type"
            )
        
        # Botão para adicionar
        if st.button("✅ Adicionar Token", use_container_width=True, type="primary"):
            if token_ca.strip():
                # Processar múltiplos tokens (um por linha)
                tokens_to_add = [ca.strip() for ca in token_ca.strip().split('\n') if ca.strip()]
                
                added = 0
                errors = []
                
                for ca in tokens_to_add:
                    success, message = st.session_state.trading_engine.add_token(
                        ca, 
                        token_name if token_name else "TOKEN",
                        token_type
                    )
                    
                    if success:
                        added += 1
                    else:
                        errors.append(f"{ca[:20]}...: {message}")
                
                if added > 0:
                    st.success(f"✅ {added} token(s) adicionado(s)!")
                
                if errors:
                    for error in errors:
                        st.error(f"❌ {error}")
                    
                st.rerun()
            else:
                st.error("❌ Cole pelo menos um CA de token")
    
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
                col_t1, col_t2 = st.columns([3, 1])
                
                with col_t1:
                    st.write(f"**{token['name']}**")
                    st.caption(f"`{token['ca'][:15]}...`")
                    st.caption(f"Tipo: {token['type']} | Scans: {token.get('total_scans', 0)}")
                
                with col_t2:
                    if st.button("🗑️", key=f"remove_{token['ca']}"):
                        success, message = engine.remove_token(token['ca'])
                        if success:
                            st.success("Removido!")
                            st.rerun()
            
            # Botão para limpar todos
            if st.button("🧹 Limpar Todos os Tokens", use_container_width=True, type="secondary"):
                count = engine.clear_all_tokens()
                st.success(f"✅ {count} tokens removidos")
                st.rerun()
    
    with tab3:
        st.markdown("#### Configurações do Sistema")
        
        st.session_state.config['auto_trading'] = st.toggle(
            "Trading Automático",
            value=st.session_state.config['auto_trading'],
            key="toggle_auto"
        )
        
        st.session_state.config['max_trades_ativos'] = st.slider(
            "Máx. Trades Ativos",
            1, 10, 5,
            key="slider_max_trades"
        )
        
        st.session_state.config['tamanho_trade_percent'] = st.slider(
            "Tamanho do Trade (%)",
            0.5, 5.0, 1.0,
            step=0.5,
            key="slider_trade_size"
        )
        
        st.divider()
        
        # GESTÃO DE SALDO
        st.markdown("#### 💰 Gerenciar Saldo")
        
        st.metric("Saldo Atual", f"${st.session_state.saldo:.2f}")
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            novo_saldo = st.number_input(
                "Novo saldo:",
                min_value=10.0,
                max_value=100000.0,
                value=float(st.session_state.saldo),
                step=100.0,
                key="input_novo_saldo"
            )
        
        with col_s2:
            if st.button("💾 Atualizar", use_container_width=True):
                st.session_state.saldo = novo_saldo
                st.success(f"Saldo: ${novo_saldo:.2f}")
                st.rerun()
        
        st.divider()
        
        # CONTROLES RÁPIDOS
        if st.button("🎯 Forçar Entrada de Teste", use_container_width=True):
            sinal_teste = {
                'symbol': f'TEST{random.randint(100, 999)}',
                'price': random.uniform(0.00001, 0.001),
                'score': random.randint(60, 90),
                'stop_loss': 0.000008,
                'take_profit': 0.000012,
                'confidence': random.choice(['LOW', 'MEDIUM', 'HIGH']),
                'token_type': 'TEST'
            }
            
            trade = executar_trade(sinal_teste)
            if trade:
                st.success(f"✅ {trade['symbol']} executado")
            st.rerun()
        
        if st.button("🔄 Atualizar Tudo", use_container_width=True):
            st.rerun()

# ==========================================================
# ÁREA PRINCIPAL
# ==========================================================

# Atualizar trades
trades_fechados = atualizar_trades()

# Processar sinais do motor
engine = st.session_state.trading_engine
if st.session_state.config['auto_trading'] and len(engine.token_pool) > 0:
    try:
        while not engine.trade_queue.empty():
            item = engine.trade_queue.get_nowait()
            
            if item['type'] == 'TRADE_SIGNAL':
                if len(st.session_state.trades_ativos) < st.session_state.config['max_trades_ativos']:
                    trade = executar_trade(item['data'])
                    if trade:
                        st.toast(f"🤖 AUTO: {trade['symbol']} | Score: {item['data']['score']}")
    except:
        pass

# ==========================================================
# DASHBOARD PRINCIPAL
# ==========================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Tokens Monitorados",
        len(engine.token_pool),
        f"Scans: {engine.stats['total_scans']}"
    )

with col2:
    win_rate = st.session_state.estatisticas['win_rate']
    delta = f"{st.session_state.estatisticas['trades_ganhos']}/{st.session_state.estatisticas['total_trades']}"
    st.metric("Win Rate", f"{win_rate:.1f}%", delta)

with col3:
    st.metric(
        "Trades Ativos",
        len(st.session_state.trades_ativos),
        f"Max: {st.session_state.config['max_trades_ativos']}"
    )

with col4:
    lucro_color = "normal" if st.session_state.estatisticas['lucro_dia'] >= 0 else "inverse"
    st.metric(
        "Lucro Hoje",
        f"${st.session_state.estatisticas['lucro_dia']:+.2f}",
        f"Total: ${st.session_state.estatisticas['lucro_total']:+.2f}",
        delta_color=lucro_color
    )

# ==========================================================
# SEÇÃO DE TRADES ATIVOS
# ==========================================================
st.markdown("### 📊 TRADES EM ANDAMENTO")

if st.session_state.trades_ativos:
    # Criar DataFrame para display
    trades_data = []
    for trade in st.session_state.trades_ativos:
        trades_data.append({
            'ID': trade['id'],
            'Símbolo': trade['symbol'],
            'Tipo': trade.get('token_type', 'CUSTOM'),
            'Entrada': f"${trade['entry_price']:.8f}",
            'Atual': f"${trade['current_price']:.8f}",
            'P/L %': f"{trade['profit_loss_percent']:+.2f}%",
            'P/L $': f"${trade['profit_loss']:+.2f}",
            'Score': trade['score']
        })
    
    df = pd.DataFrame(trades_data)
    
    # Função para colorir P/L
    def color_pl(val):
        try:
            if '%' in val:
                num = float(val.replace('%', '').replace('+', ''))
            else:
                num = float(val.replace('$', '').replace('+', ''))
            
            if num > 0:
                return 'background-color: #003300; color: #00FF00; font-weight: bold;'
            elif num < 0:
                return 'background-color: #330000; color: #FF0000; font-weight: bold;'
            else:
                return ''
        except:
            return ''
    
    # Aplicar estilo
    styled_df = df.style.applymap(color_pl, subset=['P/L %', 'P/L $'])
    
    # Mostrar tabela
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # Botões de ação
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("⏹️ Fechar Todos", use_container_width=True):
            for trade in st.session_state.trades_ativos[:]:
                fechar_trade(trade, 'MANUAL', [])
            st.rerun()
    
    with col_btn2:
        if st.button("📈 Atualizar Preços", use_container_width=True):
            st.rerun()
    
    with col_btn3:
        if st.button("📊 Ver Estatísticas", use_container_width=True):
            st.session_state.token_manager_tab = "estatisticas"
            st.rerun()

else:
    st.info("""
    📭 **Nenhum trade ativo no momento**
    
    Para começar:
    1. Vá para a sidebar e clique em **"➕ Adicionar"**
    2. Cole o CA do token que quer monitorar
    3. O sistema começará a escanear automaticamente
    4. Quando encontrar oportunidades, executará trades
    """)
    
    # Status do scanner
    if len(engine.token_pool) == 0:
        st.warning("⚠️ **Adicione pelo menos um token para começar o monitoramento**")
    else:
        stats = engine.get_stats()
        st.success(f"🔍 **Scanner ativo** - Monitorando {len(engine.token_pool)} tokens")

# ==========================================================
# SEÇÃO DE HISTÓRICO
# ==========================================================
if st.session_state.historico_trades:
    st.markdown("### 📋 HISTÓRICO RECENTE")
    
    # Últimos 5 trades
    recent_trades = st.session_state.historico_trades[-5:]
    
    for trade in reversed(recent_trades):
        profit = trade['profit_loss']
        emoji = "🐕" if trade.get('token_type') == "MEME" else ("🟢" if profit > 0 else "🔴")
        
        col_h1, col_h2, col_h3 = st.columns([2, 2, 1])
        
        with col_h1:
            type_badge = f"`{trade.get('token_type', 'CUSTOM')}`"
            st.write(f"{emoji} **{trade['symbol']}** {type_badge}")
            st.caption(f"{trade.get('exit_reason', '')}")
        
        with col_h2:
            st.write(f"**Entrada:** ${trade['entry_price']:.8f}")
            st.write(f"**Saída:** ${trade.get('exit_price', 0):.8f}")
        
        with col_h3:
            st.metric("", f"{trade['profit_loss_percent']:+.2f}%", f"${profit:+.2f}")
        
        st.divider()

# ==========================================================
# INFORMAÇÕES DO SISTEMA
# ==========================================================
st.markdown("---")

col_info1, col_info2 = st.columns(2)

with col_info1:
    st.markdown("#### ℹ️ Status do Sistema")
    
    stats = engine.get_stats()
    
    info_data = {
        "Trading Automático": "✅ ATIVO" if st.session_state.config['auto_trading'] else "⏸️ PAUSADO",
        "Tokens Monitorados": len(engine.token_pool),
        "Total de Scans": stats['total_scans'],
        "Sinais Encontrados": stats['signals_found'],
        "Último Sinal": f"Há {(datetime.now() - (stats['last_signal_time'] or datetime.now())).seconds}s" if stats['last_signal_time'] else "Nunca"
    }
    
    for key, value in info_data.items():
        st.write(f"**{key}:** {value}")

with col_info2:
    st.markdown("#### 💡 Dicas Rápidas")
    
    tips = [
        "✅ Adicione apenas tokens que você conhece",
        "🔍 O sistema escaneia a cada 3 segundos",
        "🎯 Score > 60 = oportunidade de compra",
        "📊 Comece com trades pequenos (0.5-1%)",
        "🗑️ Remova tokens que não performam bem"
    ]
    
    for tip in tips:
        st.write(f"• {tip}")

# ==========================================================
# RODAPÉ
# ==========================================================
st.markdown("---")

footer_col1, footer_col2 = st.columns(2)

with footer_col1:
    st.caption(f"🔄 Última atualização: {datetime.now().strftime('%H:%M:%S')}")

with footer_col2:
    if st.session_state.config['auto_trading']:
        st.caption("🤖 **MODO AUTOMÁTICO ATIVO**")
    else:
        st.caption("⏸️ **MODO MANUAL**")

# ==========================================================
# CSS
# ==========================================================
st.markdown("""
<style>
    /* Estilos gerais */
    .stMetric {
        background: linear-gradient(45deg, #1a1a2e, #16213e);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #00FFFF;
        transition: transform 0.3s;
    }
    
    .stMetric:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0, 255, 255, 0.3);
    }
    
    /* Tabs na sidebar */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        font-size: 14px;
        font-weight: bold;
    }
    
    /* Botões */
    .stButton > button {
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s;
        margin: 2px 0;
    }
    
    .stButton > button[type="primary"] {
        background: linear-gradient(45deg, #00FFFF, #0080FF);
        color: white;
        border: none;
    }
    
    .stButton > button[type="secondary"] {
        background: linear-gradient(45deg, #FF6B6B, #FF8E53);
        color: white;
        border: none;
    }
    
    .stButton > button:hover {
        transform: scale(1.02);
    }
    
    /* Text areas */
    .stTextArea textarea {
        font-family: monospace;
        font-size: 14px;
    }
    
    /* Badges */
    code {
        background: linear-gradient(45deg, #FF6B6B, #FF8E53) !important;
        color: white !important;
        padding: 2px 8px !important;
        border-radius: 12px !important;
        font-size: 12px !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# AUTO-REFRESH
# ==========================================================

time.sleep(3)
st.rerun()