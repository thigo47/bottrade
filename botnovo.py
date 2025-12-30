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
import json
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
            'last_signal_time': None,
            'tokens_monitorados': 0
        }
        
        # LISTA VAZIA - VOCÊ ADICIONA OS TOKENS QUE QUISER
        self.token_pool = []
        
    def fetch_token_data(self, ca):
        """Busca dados do token da API DexScreener"""
        try:
            # Limpar o CA (remover espaços e converter para minúsculas)
            ca_clean = ca.strip().lower()
            
            # URL da API DexScreener
            url = f"https://api.dexscreener.com/latest/dex/tokens/{ca_clean}"
            
            # Headers para evitar bloqueio
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Debug: Mostrar resposta da API (opcional)
                # print(f"API Response for {ca_clean}: {json.dumps(data, indent=2)[:500]}")
                
                if 'pairs' in data and len(data['pairs']) > 0:
                    # Encontrar o par com maior liquidez
                    pairs = data['pairs']
                    
                    # Filtrar apenas pares válidos
                    valid_pairs = []
                    for pair in pairs:
                        if all(key in pair for key in ['baseToken', 'quoteToken', 'priceUsd']):
                            valid_pairs.append(pair)
                    
                    if valid_pairs:
                        # Ordenar por volume (maior primeiro)
                        valid_pairs.sort(key=lambda x: float(x.get('volume', {}).get('h24', 0) or 0), reverse=True)
                        return valid_pairs[0]
                    else:
                        return None
                else:
                    # Tentar buscar por nome/símbolo como fallback
                    return self.fetch_by_symbol(ca_clean)
            else:
                print(f"API Error {response.status_code} for {ca_clean}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"Timeout para {ca}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Request error para {ca}: {e}")
            return None
        except Exception as e:
            print(f"Erro ao buscar token {ca}: {e}")
            return None
    
    def fetch_by_symbol(self, symbol):
        """Tenta buscar token por símbolo"""
        try:
            url = f"https://api.dexscreener.com/latest/dex/search?q={symbol}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'pairs' in data and len(data['pairs']) > 0:
                    # Retornar o primeiro par
                    return data['pairs'][0]
            
            return None
        except Exception as e:
            print(f"Erro na busca por símbolo {symbol}: {e}")
            return None
    
    def analyze_token(self, token_data, token_type="CUSTOM"):
        """Análise simplificada para testes"""
        try:
            if not token_data:
                return None
            
            # Extrair dados básicos
            price = float(token_data.get('priceUsd', 0))
            
            # Obter volume (com fallback)
            volume_data = token_data.get('volume', {})
            if isinstance(volume_data, dict):
                volume_24h = float(volume_data.get('h24', 0) or 0)
            else:
                volume_24h = float(volume_data or 0)
            
            # Obter mudança de preço (com fallback)
            price_change = token_data.get('priceChange', {})
            if isinstance(price_change, dict):
                change_5m = float(price_change.get('m5', 0) or 0)
                change_1h = float(price_change.get('h1', 0) or 0)
            else:
                change_5m = 0
                change_1h = 0
            
            # Obter símbolo
            base_token = token_data.get('baseToken', {})
            symbol = base_token.get('symbol', 'UNKNOWN')
            
            # Simples cálculo de score
            score = 50  # Base score
            
            # Ajustar baseado em volume
            if volume_24h > 10000:
                score += 20
            elif volume_24h > 1000:
                score += 10
            
            # Ajustar baseado em momentum
            if change_5m > 2:
                score += 20
            elif change_5m > 0:
                score += 10
            
            # Ajustar baseado em tendência
            if change_5m > 0 and change_1h > 0:
                score += 10
            
            # Determinar confiança
            if score >= 70:
                confidence = "HIGH"
                stop_loss = 0.97  # -3%
                take_profit = 1.04  # +4%
            elif score >= 60:
                confidence = "MEDIUM"
                stop_loss = 0.98  # -2%
                take_profit = 1.03  # +3%
            else:
                confidence = "LOW"
                stop_loss = 0.99  # -1%
                take_profit = 1.02  # +2%
            
            return {
                'symbol': symbol,
                'price': price,
                'score': min(score, 100),  # Limitar a 100
                'confidence': confidence,
                'stop_loss': price * stop_loss,
                'take_profit': price * take_profit,
                'volume': volume_24h,
                'change_5m': change_5m,
                'change_1h': change_1h,
                'timestamp': datetime.now(),
                'token_type': token_type,
                'dex': token_data.get('dexId', 'Unknown'),
                'pair_address': token_data.get('pairAddress', '')
            }
                
        except Exception as e:
            print(f"Erro na análise: {e}")
            return None
    
    def add_token(self, ca, name="TOKEN", token_type="CUSTOM"):
        """Adiciona um token à lista de monitoramento - VERSÃO SIMPLIFICADA"""
        try:
            ca = ca.strip()
            
            # Validar formato básico (deve começar com 0x e ter pelo menos 40 caracteres)
            if not ca.startswith("0x"):
                return False, "❌ CA deve começar com '0x'"
            
            if len(ca) < 40:
                return False, "❌ CA muito curto (mínimo 40 caracteres)"
            
            # Verificar se já existe
            for token in self.token_pool:
                if token['ca'].lower() == ca.lower():
                    return False, "⚠️ Token já está na lista"
            
            # Buscar dados do token
            token_data = self.fetch_token_data(ca)
            
            if not token_data:
                # Se não encontrou pelo CA, tentar buscar dados básicos
                return False, "❌ Token não encontrado na API. Verifique o CA."
            
            # Obter símbolo real do token
            base_token = token_data.get('baseToken', {})
            symbol = base_token.get('symbol', name)
            
            # Adicionar token à lista
            new_token = {
                "ca": ca,
                "name": symbol,
                "type": token_type,
                "added_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "total_scans": 0,
                "signals_found": 0,
                "dex": token_data.get('dexId', 'Unknown'),
                "pair_address": token_data.get('pairAddress', '')
            }
            
            self.token_pool.append(new_token)
            self.stats['tokens_monitorados'] = len(self.token_pool)
            
            return True, f"✅ {symbol} adicionado com sucesso!"
            
        except Exception as e:
            return False, f"❌ Erro: {str(e)}"
    
    def remove_token(self, ca):
        """Remove um token da lista"""
        initial_count = len(self.token_pool)
        self.token_pool = [t for t in self.token_pool if t['ca'] != ca]
        removed = initial_count - len(self.token_pool)
        
        if removed > 0:
            self.stats['tokens_monitorados'] = len(self.token_pool)
            return True, "Token removido"
        return False, "Token não encontrado"
    
    def clear_all_tokens(self):
        """Remove todos os tokens"""
        count = len(self.token_pool)
        self.token_pool = []
        self.stats['tokens_monitorados'] = 0
        return count
    
    def load_example_tokens(self):
        """Carrega tokens de exemplo (opcional)"""
        example_tokens = [
            {"ca": "0x2170Ed0880ac9A755fd29B2688956BD959F933F8", "name": "ETH", "type": "MAIN"},
            {"ca": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", "name": "BNB", "type": "MAIN"},
            {"ca": "0x55d398326f99059fF775485246999027B3197955", "name": "USDT", "type": "STABLE"},
        ]
        
        loaded = 0
        errors = []
        
        for token in example_tokens:
            success, message = self.add_token(token['ca'], token['name'], token['type'])
            if success:
                loaded += 1
            else:
                errors.append(message)
        
        return loaded, errors
    
    def scan_tokens(self):
        """Escaneia tokens em busca de oportunidades"""
        while self.running:
            try:
                current_time = datetime.now()
                
                # Intervalo entre scans
                if (current_time - self.last_scan).total_seconds() < 5:  # 5 segundos
                    time.sleep(0.1)
                    continue
                
                self.stats['total_scans'] += 1
                
                # Se não houver tokens, esperar
                if len(self.token_pool) == 0:
                    time.sleep(2)
                    continue
                
                # Escanear até 2 tokens por vez
                tokens_to_scan = self.token_pool[:2]
                
                for token_info in tokens_to_scan:
                    try:
                        # Atualizar contagem de scans
                        token_info['total_scans'] = token_info.get('total_scans', 0) + 1
                        token_info['last_checked'] = current_time.strftime("%Y-%m-%d %H:%M")
                        
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
                    except Exception as e:
                        print(f"Erro ao escanear token {token_info['name']}: {e}")
                        continue
                
                self.last_scan = current_time
                time.sleep(1)
                
            except Exception as e:
                print(f"Erro no scanner principal: {e}")
                time.sleep(2)
    
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
            'use_examples': False
        },
        'ultima_atualizacao': datetime.now()
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
            # Simular variação de preço
            variation = random.uniform(-0.02, 0.03)
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
        token_ca = st.text_input(
            "CA do Token (Contract Address):",
            placeholder="Cole aqui o CA (ex: 0x2170Ed0880ac9A755fd29B2688956BD959F933F8)",
            key="input_token_ca",
            help="O CA deve começar com '0x' e ter pelo menos 40 caracteres"
        )
        
        col_name, col_type = st.columns(2)
        with col_name:
            token_name = st.text_input(
                "Nome personalizado (opcional):",
                placeholder="Deixe em branco para usar o nome oficial",
                key="input_token_name"
            )
        
        with col_type:
            token_type = st.selectbox(
                "Tipo:",
                ["MEME", "ALT", "DEFI", "STABLE", "CUSTOM"],
                index=4,
                key="select_token_type"
            )
        
        # Botão para adicionar
        if st.button("✅ Adicionar Token", use_container_width=True, type="primary"):
            if token_ca.strip():
                success, message = st.session_state.trading_engine.add_token(
                    token_ca.strip(), 
                    token_name if token_name else "TOKEN",
                    token_type
                )
                
                if success:
                    st.success(message)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.error("❌ Por favor, cole o CA do token")
        
        st.markdown("---")
        st.markdown("#### 📥 Adicionar Múltiplos Tokens")
        
        multiple_tokens = st.text_area(
            "Vários CAs (um por linha):",
            placeholder="Cole vários CAs, um por linha:\n0x...\n0x...\n0x...",
            height=100,
            key="input_multiple_tokens"
        )
        
        if st.button("📥 Adicionar Todos", use_container_width=True):
            if multiple_tokens.strip():
                tokens_list = [ca.strip() for ca in multiple_tokens.strip().split('\n') if ca.strip()]
                
                added = 0
                errors = []
                
                for ca in tokens_list:
                    success, message = st.session_state.trading_engine.add_token(ca, "TOKEN", token_type)
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
                
                time.sleep(1)
                st.rerun()
    
    with tab2:
        st.markdown("#### Tokens Monitorados")
        
        engine = st.session_state.trading_engine
        token_count = len(engine.token_pool)
        
        if token_count == 0:
            st.info("📭 Nenhum token adicionado ainda")
            
            if st.button("📥 Carregar Tokens de Exemplo", use_container_width=True):
                loaded, errors = engine.load_example_tokens()
                if loaded > 0:
                    st.success(f"✅ {loaded} tokens de exemplo carregados!")
                if errors:
                    st.warning(f"⚠️ Alguns tokens falharam: {', '.join(errors)}")
                time.sleep(1)
                st.rerun()
        else:
            st.metric("Total de Tokens", token_count)
            
            # Listar tokens
            for i, token in enumerate(engine.token_pool):
                with st.expander(f"{token['name']} ({token['type']})", expanded=False):
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.code(f"CA: {token['ca'][:20]}...", language="text")
                        st.caption(f"🔍 Scans: {token.get('total_scans', 0)}")
                        st.caption(f"🚨 Sinais: {token.get('signals_found', 0)}")
                        st.caption(f"📅 Adicionado: {token.get('added_time', 'N/A')}")
                        
                        if 'dex' in token:
                            st.caption(f"🔄 DEX: {token.get('dex', 'Unknown')}")
                    
                    with col2:
                        if st.button("🗑️", key=f"remove_{i}"):
                            success, message = engine.remove_token(token['ca'])
                            if success:
                                st.success("Token removido!")
                                time.sleep(1)
                                st.rerun()
            
            # Botão para limpar todos
            if st.button("🗑️ Limpar Todos", use_container_width=True, type="secondary"):
                count = engine.clear_all_tokens()
                st.success(f"✅ {count} tokens removidos")
                time.sleep(1)
                st.rerun()
    
    with tab3:
        st.markdown("#### Configurações")
        
        # Configurações de trading
        st.session_state.config['auto_trading'] = st.checkbox(
            "Auto Trading",
            value=st.session_state.config['auto_trading'],
            help="Executa trades automaticamente"
        )
        
        st.session_state.config['max_trades_ativos'] = st.slider(
            "Máximo de Trades Ativos",
            min_value=1,
            max_value=10,
            value=st.session_state.config['max_trades_ativos'],
            help="Número máximo de trades simultâneos"
        )
        
        st.session_state.config['tamanho_trade_percent'] = st.slider(
            "Tamanho do Trade (%)",
            min_value=0.5,
            max_value=5.0,
            value=st.session_state.config['tamanho_trade_percent'],
            step=0.5,
            help="Percentual do saldo usado por trade"
        )
        
        st.markdown("---")
        
        # Controles do motor
        if st.button("🔄 Reiniciar Motor", use_container_width=True):
            engine = st.session_state.trading_engine
            engine.stop()
            time.sleep(1)
            engine.start()
            st.success("Motor reiniciado!")
        
        if st.button("📊 Limpar Estatísticas", use_container_width=True, type="secondary"):
            st.session_state.estatisticas.update({
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
            })
            st.success("Estatísticas limpas!")

# ==========================================================
# DASHBOARD PRINCIPAL
# ==========================================================

# Estatísticas principais
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("💰 Saldo", f"${st.session_state.saldo:.2f}")
with col2:
    win_rate = st.session_state.estatisticas['win_rate']
    st.metric("📊 Win Rate", f"{win_rate:.1f}%")
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
if st.session_state.config['auto_trading']:
    try:
        # Verificar sinais na fila
        while not engine.trade_queue.empty():
            signal = engine.trade_queue.get_nowait()
            if signal['type'] == 'TRADE_SIGNAL':
                # Verificar limite de trades
                if len(st.session_state.trades_ativos) < st.session_state.config['max_trades_ativos']:
                    trade = executar_trade(signal['data'])
                    if trade:
                        st.success(f"🚀 Trade executado: {trade['symbol']} (Score: {trade['score']})")
    except queue.Empty:
        pass

# Atualizar trades ativos
if st.session_state.trades_ativos:
    trades_fechados = atualizar_trades()
    if trades_fechados:
        for trade in trades_fechados:
            emoji = "✅" if trade['profit_loss'] > 0 else "❌"
            st.info(f"{emoji} Trade {trade['symbol']} fechado: ${trade['profit_loss']:.2f}")

# Trades ativos
st.markdown("### 📈 Trades Ativos")
if st.session_state.trades_ativos:
    trades_data = []
    for trade in st.session_state.trades_ativos:
        trades_data.append({
            'Símbolo': trade['symbol'],
            'Preço Entrada': f"${trade['entry_price']:.6f}",
            'Preço Atual': f"${trade['current_price']:.6f}",
            'P&L': f"${trade['profit_loss']:.2f}",
            'P&L %': f"{trade['profit_loss_percent']:.2f}%",
            'Confiança': trade['confidence'],
            'Score': trade['score']
        })
    
    trades_df = pd.DataFrame(trades_data)
    st.dataframe(trades_df, use_container_width=True, hide_index=True)
else:
    st.info("📭 Nenhum trade ativo no momento")

# Gráfico de performance
st.markdown("### 📊 Performance")
if st.session_state.historico_trades:
    hist_df = pd.DataFrame(st.session_state.historico_trades)
    
    if not hist_df.empty and 'exit_time' in hist_df.columns:
        hist_df = hist_df.sort_values('exit_time')
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

# Histórico de trades
st.markdown("### 📋 Histórico de Trades")
if st.session_state.historico_trades:
    hist_data = []
    for trade in st.session_state.historico_trades[-10:]:  # Últimos 10 trades
        hist_data.append({
            'Símbolo': trade['symbol'],
            'Entrada': f"${trade['entry_price']:.6f}",
            'Saída': f"${trade.get('exit_price', 0):.6f}",
            'P&L': f"${trade['profit_loss']:.2f}",
            'P&L %': f"{trade['profit_loss_percent']:.2f}%",
            'Razão': trade.get('exit_reason', 'N/A'),
            'Confiança': trade.get('confidence', 'N/A')
        })
    
    hist_df = pd.DataFrame(hist_data)
    st.dataframe(hist_df, use_container_width=True, hide_index=True)
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

# Auto-refresh
if st.button("🔄 Atualizar Dados", use_container_width=True):
    st.rerun()

# Auto-refresh automático a cada 15 segundos
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.now()

if (datetime.now() - st.session_state.last_refresh).seconds > 15:
    st.session_state.last_refresh = datetime.now()
    st.rerun()