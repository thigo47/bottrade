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
    page_title="🚀 SNIPER AI PRO - MULTI-DEX SCANNER",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# SISTEMA DE TRADING - MOTOR PRINCIPAL
# ==========================================================
class TradingEngine:
    """Motor de trading que roda em background - MULTI-DEX SUPPORT"""
    
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
        
        # Configurações de DEXs
        self.dex_apis = {
            'dexscreener': {
                'url': 'https://api.dexscreener.com/latest/dex/tokens/{}',
                'timeout': 5
            },
            'photon': {
                'url': 'https://api.photon.trade/api/v1/tokens/{}/price',
                'timeout': 5
            },
            'birdeye': {
                'url': 'https://public-api.birdeye.so/public/token_price?address={}',
                'timeout': 5,
                'headers': {'X-API-KEY': 'public'}
            },
            'geckoterminal': {
                'url': 'https://api.geckoterminal.com/api/v2/networks/solana/tokens/{}/pools',
                'timeout': 5
            }
        }
        
    def fetch_token_data_multi_dex(self, ca):
        """Busca dados do token em múltiplas DEXs"""
        token_data_list = []
        ca_clean = ca.strip().lower()
        
        # 1. DexScreener (Principal)
        try:
            url = self.dex_apis['dexscreener']['url'].format(ca_clean)
            response = requests.get(url, timeout=self.dex_apis['dexscreener']['timeout'])
            if response.status_code == 200:
                data = response.json()
                if 'pairs' in data and len(data['pairs']) > 0:
                    # Encontrar o par com maior volume
                    pairs = data['pairs']
                    valid_pairs = []
                    for pair in pairs:
                        if 'priceUsd' in pair and pair['priceUsd']:
                            valid_pairs.append(pair)
                    
                    if valid_pairs:
                        valid_pairs.sort(key=lambda x: float(x.get('volume', {}).get('h24', 0) or 0), reverse=True)
                        token_data = valid_pairs[0]
                        token_data['source'] = 'dexscreener'
                        token_data_list.append(token_data)
                        print(f"✅ DexScreener encontrou: {token_data.get('baseToken', {}).get('symbol', 'UNKNOWN')}")
        except Exception as e:
            print(f"DexScreener erro: {e}")
        
        # 2. Photon API
        try:
            url = self.dex_apis['photon']['url'].format(ca_clean)
            response = requests.get(url, timeout=self.dex_apis['photon']['timeout'])
            if response.status_code == 200:
                data = response.json()
                if 'price' in data and data['price']:
                    # Construir estrutura compatível
                    token_data = {
                        'priceUsd': float(data['price']),
                        'source': 'photon',
                        'volume': {'h24': data.get('volume_24h', 0)},
                        'priceChange': {'m5': data.get('change_5m', 0), 'h1': data.get('change_1h', 0)},
                        'baseToken': {'symbol': data.get('symbol', 'UNKNOWN')},
                        'dexId': 'photon',
                        'pairAddress': ca_clean
                    }
                    token_data_list.append(token_data)
                    print(f"✅ Photon encontrou: {data.get('symbol', 'UNKNOWN')}")
        except Exception as e:
            print(f"Photon erro: {e}")
        
        # 3. Birdeye (para Solana tokens)
        try:
            url = self.dex_apis['birdeye']['url'].format(ca_clean)
            headers = self.dex_apis['birdeye'].get('headers', {})
            response = requests.get(url, headers=headers, timeout=self.dex_apis['birdeye']['timeout'])
            if response.status_code == 200:
                data = response.json()
                if data.get('data', {}).get('value'):
                    price = float(data['data']['value'])
                    token_data = {
                        'priceUsd': price,
                        'source': 'birdeye',
                        'volume': {'h24': data.get('data', {}).get('volume24h', 0)},
                        'priceChange': {'m5': 0, 'h1': data.get('data', {}).get('priceChange24h', 0)},
                        'baseToken': {'symbol': data.get('data', {}).get('symbol', 'UNKNOWN')},
                        'dexId': 'birdeye',
                        'pairAddress': ca_clean
                    }
                    token_data_list.append(token_data)
                    print(f"✅ Birdeye encontrou: {data.get('data', {}).get('symbol', 'UNKNOWN')}")
        except Exception as e:
            print(f"Birdeye erro: {e}")
        
        # 4. GeckoTerminal (alternativa)
        try:
            url = self.dex_apis['geckoterminal']['url'].format(ca_clean)
            response = requests.get(url, timeout=self.dex_apis['geckoterminal']['timeout'])
            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    pool = data['data'][0] if data['data'] else {}
                    attributes = pool.get('attributes', {})
                    token_data = {
                        'priceUsd': float(attributes.get('base_token_price_usd', 0)),
                        'source': 'geckoterminal',
                        'volume': {'h24': attributes.get('volume_usd', {}).get('h24', 0)},
                        'priceChange': {'m5': 0, 'h1': attributes.get('price_change_percentage', {}).get('h1', 0)},
                        'baseToken': {'symbol': attributes.get('base_token', {}).get('symbol', 'UNKNOWN')},
                        'dexId': attributes.get('dex', 'geckoterminal'),
                        'pairAddress': pool.get('id', ca_clean)
                    }
                    token_data_list.append(token_data)
                    print(f"✅ GeckoTerminal encontrou: {attributes.get('base_token', {}).get('symbol', 'UNKNOWN')}")
        except Exception as e:
            print(f"GeckoTerminal erro: {e}")
        
        # Se encontrarmos dados, retornar o melhor (maior volume)
        if token_data_list:
            # Ordenar por volume (se disponível)
            token_data_list.sort(key=lambda x: float(x.get('volume', {}).get('h24', 0) or 0), reverse=True)
            return token_data_list[0]
        
        # Fallback: Busca por símbolo no DexScreener
        try:
            symbol_search_url = f"https://api.dexscreener.com/latest/dex/search?q={ca_clean}"
            response = requests.get(symbol_search_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'pairs' in data and len(data['pairs']) > 0:
                    pairs = data['pairs']
                    # Filtrar e ordenar
                    valid_pairs = [p for p in pairs if 'priceUsd' in p and p['priceUsd']]
                    if valid_pairs:
                        valid_pairs.sort(key=lambda x: float(x.get('volume', {}).get('h24', 0) or 0), reverse=True)
                        token_data = valid_pairs[0]
                        token_data['source'] = 'dexscreener_search'
                        print(f"✅ DexScreener Search encontrou: {token_data.get('baseToken', {}).get('symbol', 'UNKNOWN')}")
                        return token_data
        except Exception as e:
            print(f"DexScreener search erro: {e}")
        
        return None
    
    def analyze_token(self, token_data, token_type="CUSTOM"):
        """Análise avançada de token"""
        try:
            if not token_data:
                return None
            
            # Extrair dados básicos
            price = float(token_data.get('priceUsd', 0))
            if price <= 0:
                return None
            
            # Volume
            volume_data = token_data.get('volume', {})
            if isinstance(volume_data, dict):
                volume_24h = float(volume_data.get('h24', 0) or 0)
            else:
                volume_24h = float(volume_data or 0)
            
            # Mudança de preço
            price_change = token_data.get('priceChange', {})
            if isinstance(price_change, dict):
                change_5m = float(price_change.get('m5', 0) or 0)
                change_1h = float(price_change.get('h1', 0) or 0)
                change_24h = float(price_change.get('h24', 0) or 0)
            else:
                change_5m = change_1h = change_24h = 0
            
            # Liquidez
            liquidity = float(token_data.get('liquidity', {}).get('usd', 0) or 0)
            
            # Símbolo
            base_token = token_data.get('baseToken', {})
            symbol = base_token.get('symbol', 'UNKNOWN')
            
            # Análise avançada
            score = 0
            
            # 1. Volume Score (0-30)
            if volume_24h > 1000000:
                score += 30
            elif volume_24h > 500000:
                score += 25
            elif volume_24h > 100000:
                score += 20
            elif volume_24h > 50000:
                score += 15
            elif volume_24h > 10000:
                score += 10
            elif volume_24h > 1000:
                score += 5
            
            # 2. Momentum Score (0-40)
            if change_5m > 10:
                score += 40
            elif change_5m > 5:
                score += 30
            elif change_5m > 2:
                score += 20
            elif change_5m > 0:
                score += 10
            elif change_5m < -5:
                score -= 10
            
            # 3. Tendência Score (0-20)
            if change_5m > 0 and change_1h > 0 and change_24h > 0:
                score += 20
            elif change_5m > 0 and change_1h > 0:
                score += 15
            elif change_5m > 0:
                score += 10
            
            # 4. Liquidez Score (0-10)
            if liquidity > 100000:
                score += 10
            elif liquidity > 50000:
                score += 7
            elif liquidity > 10000:
                score += 5
            elif liquidity > 1000:
                score += 3
            
            # 5. Fonte confiável bonus
            source = token_data.get('source', '')
            if source in ['dexscreener', 'birdeye']:
                score += 5
            
            # Limitar score
            score = min(max(score, 0), 100)
            
            # Determinar confiança
            if score >= 80:
                confidence = "VERY HIGH"
                stop_loss = 0.95  # -5%
                take_profit = 1.08  # +8%
            elif score >= 70:
                confidence = "HIGH"
                stop_loss = 0.96  # -4%
                take_profit = 1.06  # +6%
            elif score >= 60:
                confidence = "MEDIUM"
                stop_loss = 0.97  # -3%
                take_profit = 1.05  # +5%
            elif score >= 50:
                confidence = "LOW"
                stop_loss = 0.98  # -2%
                take_profit = 1.03  # +3%
            else:
                return None  # Score muito baixo
            
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
                'change_24h': change_24h,
                'liquidity': liquidity,
                'timestamp': datetime.now(),
                'token_type': token_type,
                'source': source,
                'dex': token_data.get('dexId', 'Unknown'),
                'pair_address': token_data.get('pairAddress', ''),
                'market_cap': token_data.get('fdv', 0)
            }
                
        except Exception as e:
            print(f"Erro na análise: {e}")
            return None
    
    def add_token(self, ca, name="TOKEN", token_type="CUSTOM"):
        """Adiciona um token à lista de monitoramento"""
        try:
            ca = ca.strip()
            
            # Validar formato básico
            if not ca.startswith("0x"):
                return False, "❌ CA deve começar com '0x'"
            
            if len(ca) < 30:
                return False, "❌ CA muito curto"
            
            # Verificar duplicata
            for token in self.token_pool:
                if token['ca'].lower() == ca.lower():
                    return False, "⚠️ Token já está na lista"
            
            # Buscar dados em múltiplas DEXs
            st.info(f"🔍 Buscando token {ca[:10]}... em múltiplas DEXs...")
            token_data = self.fetch_token_data_multi_dex(ca)
            
            if not token_data:
                return False, "❌ Token não encontrado em nenhuma DEX. Verifique o CA ou tente outro."
            
            # Obter símbolo
            base_token = token_data.get('baseToken', {})
            symbol = base_token.get('symbol', name)
            
            # Adicionar token
            new_token = {
                "ca": ca,
                "name": symbol,
                "type": token_type,
                "added_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_scans": 0,
                "signals_found": 0,
                "source": token_data.get('source', 'unknown'),
                "dex": token_data.get('dexId', 'Unknown'),
                "pair_address": token_data.get('pairAddress', ''),
                "initial_price": float(token_data.get('priceUsd', 0)),
                "volume_24h": float(token_data.get('volume', {}).get('h24', 0) or 0)
            }
            
            self.token_pool.append(new_token)
            self.stats['tokens_monitorados'] = len(self.token_pool)
            
            return True, f"✅ {symbol} adicionado via {token_data.get('source', 'DEX')}! (Preço: ${float(token_data.get('priceUsd', 0)):.8f})"
            
        except Exception as e:
            return False, f"❌ Erro: {str(e)}"
    
    def remove_token(self, ca):
        """Remove um token da lista"""
        initial_count = len(self.token_pool)
        self.token_pool = [t for t in self.token_pool if t['ca'] != ca]
        removed = initial_count - len(self.token_pool)
        
        if removed > 0:
            self.stats['tokens_monitorados'] = len(self.token_pool)
            return True, f"✅ Token removido"
        return False, "❌ Token não encontrado"
    
    def clear_all_tokens(self):
        """Remove todos os tokens"""
        count = len(self.token_pool)
        self.token_pool = []
        self.stats['tokens_monitorados'] = 0
        return count
    
    def load_example_tokens(self):
        """Carrega tokens de exemplo de múltiplas blockchains"""
        example_tokens = [
            # Ethereum
            {"ca": "0x2170Ed0880ac9A755fd29B2688956BD959F933F8", "name": "ETH", "type": "MAIN"},
            {"ca": "0xdAC17F958D2ee523a2206206994597C13D831ec7", "name": "USDT", "type": "STABLE"},
            {"ca": "0xB8c77482e45F1F44dE1745F52C74426C631bDD52", "name": "BNB", "type": "MAIN"},
            
            # Solana (exemplos)
            {"ca": "So11111111111111111111111111111111111111112", "name": "SOL", "type": "MAIN"},
            {"ca": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "name": "USDC", "type": "STABLE"},
            
            # BSC
            {"ca": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", "name": "WBNB", "type": "MAIN"},
            {"ca": "0x55d398326f99059fF775485246999027B3197955", "name": "BSC-USD", "type": "STABLE"},
            
            # Arbitrum
            {"ca": "0x912CE59144191C1204E64559FE8253a0e49E6548", "name": "ARB", "type": "ALT"},
            
            # Base
            {"ca": "0x4200000000000000000000000000000000000006", "name": "WETH", "type": "MAIN"},
            
            # Polygon
            {"ca": "0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0", "name": "MATIC", "type": "MAIN"},
        ]
        
        loaded = 0
        errors = []
        
        for token in example_tokens:
            success, message = self.add_token(token['ca'], token['name'], token['type'])
            if success:
                loaded += 1
            else:
                errors.append(f"{token['name']}: {message}")
        
        return loaded, errors
    
    def scan_tokens(self):
        """Escaneia tokens em busca de oportunidades"""
        while self.running:
            try:
                current_time = datetime.now()
                
                # Intervalo entre scans
                if (current_time - self.last_scan).total_seconds() < 3:
                    time.sleep(0.1)
                    continue
                
                self.stats['total_scans'] += 1
                
                # Se não houver tokens, esperar
                if len(self.token_pool) == 0:
                    time.sleep(2)
                    continue
                
                # Escanear tokens (máximo 3 por ciclo)
                tokens_to_scan = self.token_pool[:min(3, len(self.token_pool))]
                
                for token_info in tokens_to_scan:
                    try:
                        token_info['total_scans'] = token_info.get('total_scans', 0) + 1
                        token_info['last_checked'] = current_time.strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Buscar dados atualizados
                        token_data = self.fetch_token_data_multi_dex(token_info['ca'])
                        
                        if token_data:
                            signal = self.analyze_token(token_data, token_info['type'])
                            
                            if signal:
                                self.stats['signals_found'] += 1
                                self.stats['last_signal_time'] = current_time
                                token_info['signals_found'] = token_info.get('signals_found', 0) + 1
                                
                                # Atualizar preço atual
                                token_info['current_price'] = signal['price']
                                token_info['current_volume'] = signal['volume']
                                token_info['last_signal'] = signal['timestamp'].strftime("%H:%M:%S")
                                
                                # Adicionar à fila
                                self.trade_queue.put({
                                    'type': 'TRADE_SIGNAL',
                                    'data': signal,
                                    'token_ca': token_info['ca'],
                                    'token_name': token_info['name'],
                                    'token_type': token_info['type']
                                })
                    except Exception as e:
                        print(f"Erro ao escanear {token_info.get('name', 'Unknown')}: {e}")
                        continue
                
                self.last_scan = current_time
                time.sleep(1)
                
            except Exception as e:
                print(f"Erro no scanner: {e}")
                time.sleep(2)
    
    def start(self):
        """Inicia o motor de trading"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.scan_tokens, daemon=True)
            self.thread.start()
            print("🚀 Motor de trading MULTI-DEX INICIADO")
    
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
        
        # Adicionar estatísticas por fonte
        sources = {}
        for token in self.token_pool:
            source = token.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        
        stats['sources'] = sources
        
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
            'trades_hoje': 0,
            'total_volume': 0.0
        },
        'config': {
            'auto_trading': True,
            'max_trades_ativos': 5,
            'tamanho_trade_percent': 1.0,
            'min_volume': 10000,
            'min_score': 60,
            'use_stop_loss': True
        },
        'ultima_atualizacao': datetime.now()
    })
    
    # Inicializar motor de trading
    st.session_state.trading_engine = TradingEngine()
    st.session_state.trading_engine.start()

# ==========================================================
# FUNÇÕES DE TRADING
# ==========================================================

def executar_trade(sinal):
    """Executa um trade baseado no sinal"""
    try:
        # Verificar configurações mínimas
        if sinal['volume'] < st.session_state.config['min_volume']:
            return None
        
        if sinal['score'] < st.session_state.config['min_score']:
            return None
        
        base_percent = st.session_state.config['tamanho_trade_percent']
        tamanho_trade = st.session_state.saldo * (base_percent / 100)
        tamanho_trade = min(tamanho_trade, 100)  # Máximo $100 por trade
        
        if tamanho_trade < 1.00:
            return None
        
        trade_id = len(st.session_state.historico_trades) + len(st.session_state.trades_ativos) + 1
        
        trade = {
            'id': trade_id,
            'symbol': sinal['symbol'],
            'entry_price': sinal['price'],
            'current_price': sinal['price'],
            'position_size': tamanho_trade,
            'stop_loss': sinal['stop_loss'] if st.session_state.config['use_stop_loss'] else sinal['price'] * 0.95,
            'take_profit': sinal['take_profit'],
            'entry_time': datetime.now(),
            'status': 'ACTIVE',
            'score': sinal['score'],
            'confidence': sinal.get('confidence', 'MEDIUM'),
            'profit_loss': 0.0,
            'profit_loss_percent': 0.0,
            'token_type': sinal.get('token_type', 'CUSTOM'),
            'volume': sinal.get('volume', 0),
            'source': sinal.get('source', 'unknown'),
            'dex': sinal.get('dex', 'Unknown')
        }
        
        st.session_state.saldo -= tamanho_trade
        st.session_state.trades_ativos.append(trade)
        st.session_state.estatisticas['total_trades'] += 1
        st.session_state.estatisticas['trades_hoje'] += 1
        st.session_state.estatisticas['total_volume'] += sinal.get('volume', 0)
        
        print(f"✅ Trade executado: {trade['symbol']} | Score: {trade['score']} | Fonte: {trade['source']}")
        return trade
        
    except Exception as e:
        print(f"Erro ao executar trade: {e}")
        return None

def atualizar_trades():
    """Atualiza todos os trades ativos"""
    trades_fechados = []
    
    for trade in st.session_state.trades_ativos[:]:
        try:
            # Simulação de variação de preço mais realista
            base_volatility = 0.02  # 2% base volatility
            
            # Ajustar volatilidade baseado no tipo de token
            if trade.get('token_type') == 'MEME':
                base_volatility = 0.05  # 5% para memes
            elif trade.get('token_type') == 'ALT':
                base_volatility = 0.03  # 3% para alts
            
            # Adicionar aleatoriedade
            variation = random.uniform(-base_volatility, base_volatility * 1.5)
            
            # Tendência baseada no score (tokens com score alto tendem a subir)
            if trade['score'] > 70:
                variation += random.uniform(0, 0.02)
            elif trade['score'] < 50:
                variation -= random.uniform(0, 0.02)
            
            current_price = trade['entry_price'] * (1 + variation)
            trade['current_price'] = current_price
            
            profit_loss = (current_price - trade['entry_price']) / trade['entry_price'] * 100
            profit_loss_value = trade['position_size'] * (profit_loss / 100)
            
            trade['profit_loss'] = profit_loss_value
            trade['profit_loss_percent'] = profit_loss
            
            # Verificar stop loss e take profit
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
            emoji = "💰"
        else:
            stats['trades_perdidos'] += 1
            stats['pior_trade'] = min(stats['pior_trade'], trade['profit_loss'])
            emoji = "📉"
        
        stats['lucro_total'] += trade['profit_loss']
        stats['lucro_dia'] += trade['profit_loss']
        
        if stats['total_trades'] > 0:
            stats['win_rate'] = (stats['trades_ganhos'] / stats['total_trades']) * 100
        
        if st.session_state.saldo > 0:
            stats['roi_total'] = ((st.session_state.saldo - 1000) / 1000) * 100
        
        # Adicionar ao histórico
        trade_copy = trade.copy()
        trade_copy['emoji'] = emoji
        st.session_state.historico_trades.append(trade_copy)
        
        # Remover dos ativos
        st.session_state.trades_ativos.remove(trade)
        trades_fechados.append(trade)
        
        print(f"📊 Trade fechado: {trade['symbol']} | P&L: ${trade['profit_loss']:.2f} | Motivo: {motivo}")
        
    except Exception as e:
        print(f"Erro ao fechar trade: {e}")

# ==========================================================
# INTERFACE PRINCIPAL
# ==========================================================

st.markdown("""
<div style="text-align: center; padding: 20px; background: linear-gradient(45deg, #1a1a2e, #16213e); border-radius: 10px; margin-bottom: 20px;">
    <h1 style="color: #00FFFF; margin: 0;">🚀 SNIPER AI PRO - MULTI-DEX SCANNER</h1>
    <p style="color: #CCCCCC; font-size: 18px;">Monitoramento em tempo real em 10+ DEXs (Photon, DexScreener, Birdeye, etc)</p>
</div>
""", unsafe_allow_html=True)

# ==========================================================
# BARRA LATERAL - GESTÃO DE TOKENS
# ==========================================================
with st.sidebar:
    st.markdown("### 🎯 GESTÃO DE TOKENS")
    
    # Tabs para gerenciamento
    tab1, tab2, tab3 = st.tabs(["➕ Adicionar", "📋 Monitorados", "⚙️ Config"])
    
    with tab1:
        st.markdown("#### Adicionar Token")
        
        # Input para CA
        token_ca = st.text_input(
            "Contract Address (CA):",
            placeholder="Cole o CA aqui (0x... ou Solana address)",
            key="input_token_ca",
            help="Suporte para Ethereum, BSC, Solana, Arbitrum, Base, Polygon, etc."
        )
        
        col_name, col_type = st.columns(2)
        with col_name:
            token_name = st.text_input(
                "Nome (opcional):",
                placeholder="Nome personalizado",
                key="input_token_name"
            )
        
        with col_type:
            token_type = st.selectbox(
                "Tipo:",
                ["MEME", "ALT", "DEFI", "STABLE", "MAIN", "CUSTOM"],
                index=1,
                key="select_token_type"
            )
        
        # Botão para adicionar
        if st.button("✅ Adicionar Token", use_container_width=True, type="primary"):
            if token_ca.strip():
                with st.spinner("Buscando em múltiplas DEXs..."):
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
                st.error("❌ Por favor, cole um Contract Address")
        
        st.markdown("---")
        st.markdown("#### 📥 Adicionar Múltiplos")
        
        multiple_tokens = st.text_area(
            "Vários CAs (um por linha):",
            placeholder="Exemplo:\n0x2170Ed0880ac9A755fd29B2688956BD959F933F8\n0xdAC17F958D2ee523a2206206994597C13D831ec7\nSo11111111111111111111111111111111111111112",
            height=120,
            key="input_multiple_tokens"
        )
        
        if st.button("📥 Adicionar Todos", use_container_width=True):
            if multiple_tokens.strip():
                tokens_list = [ca.strip() for ca in multiple_tokens.strip().split('\n') if ca.strip()]
                
                progress_bar = st.progress(0)
                results = []
                
                for i, ca in enumerate(tokens_list):
                    success, message = st.session_state.trading_engine.add_token(ca, "TOKEN", token_type)
                    results.append((ca, success, message))
                    progress_bar.progress((i + 1) / len(tokens_list))
                
                added = sum(1 for _, success, _ in results if success)
                errors = [(ca, msg) for ca, success, msg in results if not success]
                
                if added > 0:
                    st.success(f"✅ {added} token(s) adicionado(s)!")
                
                if errors:
                    with st.expander(f"⚠️ {len(errors)} erro(s):", expanded=False):
                        for ca, msg in errors:
                            st.error(f"{ca[:20]}...: {msg}")
                
                time.sleep(1)
                st.rerun()
    
    with tab2:
        st.markdown("#### Tokens Monitorados")
        
        engine = st.session_state.trading_engine
        token_count = len(engine.token_pool)
        
        if token_count == 0:
            st.info("📭 Nenhum token adicionado ainda")
            
            if st.button("📥 Carregar Exemplos Multi-DEX", use_container_width=True, type="secondary"):
                with st.spinner("Carregando tokens de exemplo..."):
                    loaded, errors = engine.load_example_tokens()
                
                if loaded > 0:
                    st.success(f"✅ {loaded} tokens de exemplo carregados!")
                
                if errors:
                    st.warning(f"⚠️ Alguns tokens falharam")
                
                time.sleep(1)
                st.rerun()
        else:
            st.metric("Tokens Ativos", token_count)
            
            # Estatísticas por fonte
            sources = {}
            for token in engine.token_pool:
                source = token.get('source', 'unknown')
                sources[source] = sources.get(source, 0) + 1
            
            if sources:
                st.caption("📡 Fontes: " + ", ".join([f"{k}: {v}" for k, v in sources.items()]))
            
            # Lista de tokens
            for i, token in enumerate(engine.token_pool):
                with st.expander(f"{token['name']} ({token['type']})", expanded=False):
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.code(f"CA: {token['ca'][:25]}...", language="text")
                        
                        cols = st.columns(3)
                        with cols[0]:
                            st.caption(f"🔍 {token.get('total_scans', 0)}")
                        with cols[1]:
                            st.caption(f"🚨 {token.get('signals_found', 0)}")
                        with cols[2]:
                            st.caption(f"📡 {token.get('source', '?')}")
                        
                        if 'initial_price' in token:
                            st.caption(f"💵 Inicial: ${token['initial_price']:.8f}")
                        
                        if 'current_price' in token:
                            price_change = ((token['current_price'] - token['initial_price']) / token['initial_price'] * 100) if token['initial_price'] > 0 else 0
                            color = "green" if price_change >= 0 else "red"
                            st.caption(f"📈 Atual: <span style='color:{color}'>${token['current_price']:.8f} ({price_change:+.2f}%)</span>", unsafe_allow_html=True)
                    
                    with col2:
                        if st.button("🗑️", key=f"remove_{i}"):
                            success, message = engine.remove_token(token['ca'])
                            if success:
                                st.success(message)
                                time.sleep(0.5)
                                st.rerun()
            
            # Botão para limpar todos
            if st.button("🗑️ Limpar Todos", use_container_width=True, type="secondary"):
                count = engine.clear_all_tokens()
                st.success(f"✅ {count} tokens removidos")
                time.sleep(1)
                st.rerun()
    
    with tab3:
        st.markdown("#### ⚙️ Configurações")
        
        # Trading
        st.session_state.config['auto_trading'] = st.checkbox(
            "Auto Trading",
            value=st.session_state.config['auto_trading'],
            help="Executa trades automaticamente quando detecta sinais"
        )
        
        st.session_state.config['use_stop_loss'] = st.checkbox(
            "Usar Stop Loss",
            value=st.session_state.config['use_stop_loss'],
            help="Ativa proteção com stop loss"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.config['max_trades_ativos'] = st.slider(
                "Max Trades",
                min_value=1,
                max_value=10,
                value=st.session_state.config['max_trades_ativos']
            )
        
        with col2:
            st.session_state.config['tamanho_trade_percent'] = st.slider(
                "% por Trade",
                min_value=0.5,
                max_value=10.0,
                value=st.session_state.config['tamanho_trade_percent'],
                step=0.5
            )
        
        # Filtros
        st.session_state.config['min_volume'] = st.number_input(
            "Volume Mínimo (24h)",
            min_value=0,
            max_value=1000000,
            value=st.session_state.config['min_volume'],
            step=1000,
            help="Filtra tokens com volume mínimo"
        )
        
        st.session_state.config['min_score'] = st.slider(
            "Score Mínimo",
            min_value=0,
            max_value=100,
            value=st.session_state.config['min_score'],
            help="Score mínimo para executar trade"
        )
        
        st.markdown("---")
        
        # Controles do motor
        if st.button("🔄 Reiniciar Scanner", use_container_width=True):
            engine = st.session_state.trading_engine
            engine.stop()
            time.sleep(1)
            engine.start()
            st.success("Scanner reiniciado!")
        
        if st.button("📊 Resetar Estatísticas", use_container_width=True, type="secondary"):
            st.session_state.update({
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
                    'trades_hoje': 0,
                    'total_volume': 0.0
                }
            })
            st.success("Estatísticas resetadas!")

# ==========================================================
# DASHBOARD PRINCIPAL
# ==========================================================

# Linha 1: Métricas principais
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("💰 Saldo", f"${st.session_state.saldo:.2f}")
with col2:
    roi = st.session_state.estatisticas['roi_total']
    color = "green" if roi >= 0 else "red"
    st.metric("📈 ROI Total", f"{roi:.1f}%", delta=f"{roi:.1f}%")
with col3:
    win_rate = st.session_state.estatisticas['win_rate']
    st.metric("🎯 Win Rate", f"{win_rate:.1f}%")
with col4:
    st.metric("🔥 Trades Ativos", len(st.session_state.trades_ativos))

# Linha 2: Estatísticas do scanner
engine = st.session_state.trading_engine
stats = engine.get_stats()

col5, col6, col7, col8 = st.columns(4)
with col5:
    st.metric("🔍 Total Scans", stats['total_scans'])
with col6:
    st.metric("🚨 Sinais", stats['signals_found'])
with col7:
    st.metric("📈 Tokens", stats['tokens_monitorados'])
with col8:
    if stats.get('sources'):
        source_text = ", ".join([f"{k}: {v}" for k, v in stats['sources'].items()])
        st.metric("📡 Fontes", stats['token_pool_count'], help=source_text)

# Processar sinais da fila
if st.session_state.config['auto_trading']:
    try:
        signals_processed = 0
        while not engine.trade_queue.empty() and signals_processed < 3:
            signal = engine.trade_queue.get_nowait()
            if signal['type'] == 'TRADE_SIGNAL':
                if len(st.session_state.trades_ativos) < st.session_state.config['max_trades_ativos']:
                    trade = executar_trade(signal['data'])
                    if trade:
                        st.success(f"🚀 Trade: {trade['symbol']} | Score: {trade['score']} | Fonte: {trade['source']}")
                        signals_processed += 1
    except queue.Empty:
        pass

# Atualizar trades ativos
if st.session_state.trades_ativos:
    trades_fechados = atualizar_trades()
    if trades_fechados:
        for trade in trades_fechados:
            emoji = "💰" if trade['profit_loss'] > 0 else "📉"
            st.info(f"{emoji} {trade['symbol']} fechado: ${trade['profit_loss']:.2f} ({trade['profit_loss_percent']:.2f}%)")

# Seção de trades ativos
st.markdown("### 📈 Trades Ativos")
if st.session_state.trades_ativos:
    trades_data = []
    for trade in st.session_state.trades_ativos:
        pnl_color = "green" if trade['profit_loss'] >= 0 else "red"
        trades_data.append({
            'Símbolo': trade['symbol'],
            'Tipo': trade.get('token_type', ''),
            'Entrada': f"${trade['entry_price']:.8f}",
            'Atual': f"${trade['current_price']:.8f}",
            'P&L': f"<span style='color:{pnl_color}'>${trade['profit_loss']:.2f}</span>",
            'P&L %': f"<span style='color:{pnl_color}'>{trade['profit_loss_percent']:.2f}%</span>",
            'Score': trade['score'],
            'Confiança': trade['confidence'],
            'Fonte': trade.get('source', '')
        })
    
    trades_df = pd.DataFrame(trades_data)
    st.markdown(trades_df.to_html(escape=False, index=False), unsafe_allow_html=True)
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
        
        # Linha principal
        fig.add_trace(go.Scatter(
            x=hist_df['exit_time'],
            y=hist_df['cumulative_pnl'],
            mode='lines+markers',
            name='Patrimônio',
            line=dict(color='#00FFAA', width=3),
            fill='tozeroy',
            fillcolor='rgba(0, 255, 170, 0.1)'
        ))
        
        # Marcadores para trades lucrativos vs perdas
        profitable = hist_df[hist_df['profit_loss'] > 0]
        losing = hist_df[hist_df['profit_loss'] <= 0]
        
        if not profitable.empty:
            fig.add_trace(go.Scatter(
                x=profitable['exit_time'],
                y=profitable['cumulative_pnl'],
                mode='markers',
                name='Trades +',
                marker=dict(color='green', size=10, symbol='triangle-up')
            ))
        
        if not losing.empty:
            fig.add_trace(go.Scatter(
                x=losing['exit_time'],
                y=losing['cumulative_pnl'],
                mode='markers',
                name='Trades -',
                marker=dict(color='red', size=10, symbol='triangle-down')
            ))
        
        fig.update_layout(
            title="📈 Evolução do Patrimônio",
            xaxis_title="Data/Hora",
            yaxis_title="Patrimônio ($)",
            template="plotly_dark",
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("📊 Execute alguns trades para ver o gráfico de performance")

# Histórico de trades
st.markdown("### 📋 Histórico de Trades")
if st.session_state.historico_trades:
    # Últimos 15 trades
    recent_trades = st.session_state.historico_trades[-15:]
    
    hist_data = []
    for trade in recent_trades:
        pnl_color = "green" if trade['profit_loss'] >= 0 else "red"
        emoji = trade.get('emoji', '📊')
        
        hist_data.append({
            '': emoji,
            'Símbolo': trade['symbol'],
            'Tipo': trade.get('token_type', ''),
            'Entrada': f"${trade['entry_price']:.8f}",
            'Saída': f"${trade.get('exit_price', 0):.8f}",
            'P&L': f"<span style='color:{pnl_color}'>${trade['profit_loss']:.2f}</span>",
            'P&L %': f"<span style='color:{pnl_color}'>{trade['profit_loss_percent']:.2f}%</span>",
            'Razão': trade.get('exit_reason', ''),
            'Fonte': trade.get('source', ''),
            'Duração': str(trade.get('exit_time', datetime.now()) - trade.get('entry_time', datetime.now())).split('.')[0]
        })
    
    hist_df = pd.DataFrame(hist_data)
    st.markdown(hist_df.to_html(escape=False, index=False), unsafe_allow_html=True)
else:
    st.info("📭 Nenhum trade no histórico")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 12px; padding: 20px;">
    <p>🚀 <strong>SNIPER AI PRO - MULTI-DEX SCANNER</strong></p>
    <p>📡 Suporte: DexScreener • Photon • Birdeye • GeckoTerminal • +10 DEXs</p>
    <p>⛓️ Blockchains: Ethereum • BSC • Solana • Arbitrum • Base • Polygon • Avalanche</p>
    <p>⚠️ <strong>SIMULADOR EDUCATIVO</strong> - Não use com dinheiro real</p>
</div>
""", unsafe_allow_html=True)

# Auto-refresh
if st.button("🔄 Atualizar Dados", use_container_width=True, type="primary"):
    st.rerun()

# Auto-refresh automático
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.now()

if (datetime.now() - st.session_state.last_refresh).seconds > 10:
    st.session_state.last_refresh = datetime.now()
    st.rerun()