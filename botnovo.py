import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import random
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import queue

# ==========================================================
# CONFIGURAÇÃO
# ==========================================================
st.set_page_config(
    page_title="⚡ SNIPER AI ULTRA - HIGH FREQUENCY",
    page_icon="⚡",
    layout="wide"
)

# ==========================================================
# SISTEMA DE FILA PARA ENTRADAS AUTOMÁTICAS
# ==========================================================

class TradingQueue:
    """Sistema de fila para gerenciar entradas em alta frequência"""
    def __init__(self):
        self.queue = queue.Queue()
        self.running = True
        self.last_entry_time = datetime.now()
        self.entry_count = 0
        
    def add_trade_signal(self, signal):
        """Adiciona sinal de trade à fila"""
        self.queue.put(signal)
        
    def process_queue(self):
        """Processa a fila de trades"""
        try:
            while self.running and not self.queue.empty():
                # Verificar intervalo mínimo (0.3 segundos)
                current_time = datetime.now()
                time_diff = (current_time - self.last_entry_time).total_seconds()
                
                if time_diff >= 0.3:
                    signal = self.queue.get_nowait()
                    # Processar sinal
                    if signal and st.session_state.auto_mode:
                        self.execute_trade(signal)
                        self.last_entry_time = current_time
                        self.entry_count += 1
                        print(f"✅ Entrada automática #{self.entry_count} executada")
                else:
                    # Aguardar tempo restante
                    time.sleep(0.3 - time_diff)
        except Exception as e:
            print(f"Erro na fila: {e}")

# Inicializar fila
if 'trade_queue' not in st.session_state:
    st.session_state.trade_queue = TradingQueue()

# ==========================================================
# FUNÇÕES OTIMIZADAS PARA ALTA FREQUÊNCIA
# ==========================================================

async def fetch_token_data_async(ca):
    """Busca dados do token de forma assíncrona"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=2) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('pairs'):
                        data['ca'] = ca
                        return data
    except:
        pass
    return None

def analise_ultra_rapida(token_data):
    """Análise ultra rápida para decisão em milissegundos"""
    try:
        pair = token_data['pairs'][0]
        
        symbol = pair.get('baseToken', {}).get('symbol', 'TOKEN')
        price = float(pair.get('priceUsd', 0))
        volume_24h = float(pair.get('volume', {}).get('h24', 0))
        
        # Análise de momentum muito rápida
        price_change = pair.get('priceChange', {})
        change_5m = float(price_change.get('m5', 0))
        change_1h = float(price_change.get('h1', 0))
        
        # Critérios SIMPLES mas eficientes
        score = 0
        
        # 1. Volume mínimo
        if volume_24h < 10000:  # Volume muito baixo
            return {'decisao': 'IGNORAR', 'symbol': symbol}
        
        # 2. Momentum positivo
        if change_5m > 0:
            score += 30
            if change_5m > 5:
                score += 20
        else:
            score -= 10
            
        # 3. Tendência consistente
        if change_5m > 0 and change_1h > 0:
            score += 40
            
        # 4. Preço adequado para micro trades
        if 0.00001 < price < 0.01:
            score += 30
            
        # DECISÃO RÁPIDA
        if score >= 70:
            return {
                'decisao': 'COMPRAR_AGGRESSIVE',
                'symbol': symbol,
                'price': price,
                'stop_loss': price * 0.98,
                'take_profit': price * 1.03,
                'score': score
            }
        elif score >= 50:
            return {
                'decisao': 'COMPRAR_MODERATE',
                'symbol': symbol,
                'price': price,
                'stop_loss': price * 0.985,
                'take_profit': price * 1.025,
                'score': score
            }
        elif score >= 30:
            return {
                'decisao': 'COMPRAR_CONSERVATIVE',
                'symbol': symbol,
                'price': price,
                'stop_loss': price * 0.99,
                'take_profit': price * 1.02,
                'score': score
            }
        else:
            return {'decisao': 'IGNORAR', 'symbol': symbol}
            
    except Exception as e:
        return {'decisao': 'ERRO', 'erro': str(e)}

def criar_entrada_automatica(token_data, analise):
    """Cria entrada automática ultra rápida"""
    try:
        # Tamanho fixo para maior velocidade
        percentual = 1.0  # 1% fixo para começar
        
        valor_trade = st.session_state.saldo * (percentual / 100)
        valor_trade = max(0.50, min(valor_trade, 50))  # $0.50 a $50
        
        if valor_trade > st.session_state.saldo * 0.9:
            return None
            
        trade = {
            'id': len(st.session_state.historico) + len(st.session_state.trades) + 1,
            'symbol': analise['symbol'],
            'ca': token_data.get('ca'),
            'entry_price': analise['price'],
            'current_price': analise['price'],
            'position_size': valor_trade,
            'stop_loss': analise['stop_loss'],
            'take_profit': analise['take_profit'],
            'status': 'ACTIVE',
            'entry_time': datetime.now(),
            'profit_percent': 0.0,
            'profit_value': 0.0,
            'percentual_usado': percentual,
            'tipo': 'AUTO',
            'score': analise.get('score', 0)
        }
        
        # Deduzir do saldo
        st.session_state.saldo -= valor_trade
        st.session_state.trades.append(trade)
        st.session_state.estatisticas['total_trades'] += 1
        st.session_state.estatisticas['trades_dia'] += 1
        
        return trade
        
    except:
        return None

# ==========================================================
# SISTEMA DE SCANNER CONTÍNUO
# ==========================================================

class TokenScanner:
    """Scanner contínuo de tokens para oportunidades"""
    
    def __init__(self):
        self.scanning = True
        self.tokens_pool = [
            # Tokens principais
            "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",  # ETH
            "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # BNB
            "0x55d398326f99059fF775485246999027B3197955",  # USDT
            "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",  # CAKE
            
            # Altcoins voláteis
            "0x1CE0c2827e2eF14D5C4f29a091d735A204794041",  # AVAX
            "0xCC42724C6683B7E57334c4E856f4c9965ED682bD",  # MATIC
            "0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE",  # XRP
            
            # Meme coins (alta volatilidade)
            "0x8076C74C5e3F5852037F31Ff0093Eeb8c8ADd8D3",  # SAFEMOON
            "0x603c7f932ED1fc6575303D8Fb018fDCBb0f39a95",  # BANANA
        ]
        
    async def scan_tokens(self):
        """Escaneia tokens continuamente"""
        while self.scanning:
            try:
                if not st.session_state.auto_mode:
                    await asyncio.sleep(1)
                    continue
                    
                # Limitar número de trades ativos
                if len(st.session_state.trades) >= st.session_state.get('max_trades', 20):
                    await asyncio.sleep(0.5)
                    continue
                
                # Selecionar 2-3 tokens aleatoriamente para escanear
                tokens_to_scan = random.sample(self.tokens_pool, min(3, len(self.tokens_pool)))
                
                for ca in tokens_to_scan:
                    # Verificar se já tem trade ativo
                    if any(t['ca'] == ca for t in st.session_state.trades):
                        continue
                    
                    # Buscar dados
                    token_data = await fetch_token_data_async(ca)
                    if token_data:
                        # Análise ultra rápida
                        analise = analise_ultra_rapida(token_data)
                        
                        if analise['decisao'].startswith('COMPRAR'):
                            # Verificar score
                            if analise.get('score', 0) >= 50:
                                # Criar trade
                                trade = criar_entrada_automatica(token_data, analise)
                                if trade:
                                    print(f"🎯 Sinal de COMPRA: {trade['symbol']} | Score: {analise['score']}")
                                    # Adicionar à fila
                                    st.session_state.trade_queue.add_trade_signal({
                                        'token_data': token_data,
                                        'analise': analise,
                                        'trade': trade
                                    })
                
                # Intervalo entre scans (0.3 segundos)
                await asyncio.sleep(0.3)
                
            except Exception as e:
                print(f"Erro no scanner: {e}")
                await asyncio.sleep(1)
                
    def start(self):
        """Inicia o scanner"""
        self.scanning = True
        asyncio.create_task(self.scan_tokens())
        
    def stop(self):
        """Para o scanner"""
        self.scanning = False

# Inicializar scanner
if 'token_scanner' not in st.session_state:
    st.session_state.token_scanner = TokenScanner()

# ==========================================================
# INICIALIZAÇÃO DO SESSION_STATE
# ==========================================================
if 'saldo' not in st.session_state:
    st.session_state.saldo = 1000.0

if 'trades' not in st.session_state:
    st.session_state.trades = []

if 'historico' not in st.session_state:
    st.session_state.historico = []

if 'ultimo_trade' not in st.session_state:
    st.session_state.ultimo_trade = datetime.now()

if 'monitorando' not in st.session_state:
    st.session_state.monitorando = []

if 'auto_mode' not in st.session_state:
    st.session_state.auto_mode = True

if 'estatisticas' not in st.session_state:
    st.session_state.estatisticas = {
        'total_trades': 0,
        'ganhos': 0,
        'perdas': 0,
        'lucro_total': 0.0,
        'lucro_dia': 0.0,
        'trades_dia': 0
    }

if 'cache_tokens' not in st.session_state:
    st.session_state.cache_tokens = {}

# ==========================================================
# FUNÇÕES BÁSICAS
# ==========================================================

def buscar_token_sincrono(ca):
    """Busca dados do token de forma síncrona"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data.get('pairs'):
                data['ca'] = ca
                return data
    except:
        pass
    return None

def atualizar_trades():
    """Atualiza trades ativos"""
    fechados = []
    
    for trade in st.session_state.trades[:]:
        try:
            data = buscar_token_sincrono(trade['ca'])
            if data and data.get('pairs'):
                current_price = float(data['pairs'][0].get('priceUsd', 0))
                trade['current_price'] = current_price
                
                profit_percent = ((current_price - trade['entry_price']) / trade['entry_price']) * 100
                profit_value = trade['position_size'] * (profit_percent / 100)
                
                trade['profit_percent'] = profit_percent
                trade['profit_value'] = profit_value
                
                # Verificar saídas
                if current_price >= trade['take_profit']:
                    trade['exit_reason'] = 'TP_HIT'
                    fechar_trade(trade, fechados)
                elif current_price <= trade['stop_loss']:
                    trade['exit_reason'] = 'SL_HIT'
                    fechar_trade(trade, fechados)
                    
        except:
            continue
            
    return fechados

def fechar_trade(trade, fechados):
    """Fecha um trade"""
    trade['status'] = 'CLOSED'
    trade['exit_time'] = datetime.now()
    trade['exit_price'] = trade['current_price']
    
    # Retornar dinheiro + lucro
    st.session_state.saldo += trade['position_size'] + trade['profit_value']
    
    # Atualizar estatísticas
    if trade['profit_value'] > 0:
        st.session_state.estatisticas['ganhos'] += 1
        st.session_state.estatisticas['lucro_total'] += trade['profit_value']
        st.session_state.estatisticas['lucro_dia'] += trade['profit_value']
    else:
        st.session_state.estatisticas['perdas'] += 1
        st.session_state.estatisticas['lucro_total'] += trade['profit_value']
        st.session_state.estatisticas['lucro_dia'] += trade['profit_value']
    
    # Mover para histórico
    st.session_state.historico.append(trade.copy())
    st.session_state.trades.remove(trade)
    fechados.append(trade)

# ==========================================================
# INICIAR SISTEMA AUTOMÁTICO
# ==========================================================

# Função para iniciar o sistema automático
def iniciar_sistema_automatico():
    """Inicia o sistema de trading automático"""
    if not hasattr(st.session_state, 'scanner_started'):
        # Iniciar scanner
        st.session_state.token_scanner.start()
        
        # Iniciar processamento da fila em background
        import threading
        def processar_fila_continua():
            while True:
                try:
                    st.session_state.trade_queue.process_queue()
                    time.sleep(0.1)  # Pequena pausa
                except:
                    time.sleep(1)
        
        # Iniciar thread da fila
        fila_thread = threading.Thread(target=processar_fila_continua, daemon=True)
        fila_thread.start()
        
        st.session_state.scanner_started = True
        print("🚀 Sistema automático INICIADO!")

# ==========================================================
# INTERFACE STREAMLIT
# ==========================================================

st.title("⚡ SNIPER AI ULTRA - ALTA FREQUÊNCIA")
st.markdown("### Sistema Automático 24/7 | Entradas a cada 0.3s")

# Iniciar sistema automático
iniciar_sistema_automatico()

# ==========================================================
# SIDEBAR
# ==========================================================
with st.sidebar:
    st.header("💰 CONTROLE DO SISTEMA")
    
    # Saldo
    col1, col2 = st.columns(2)
    with col1:
        st.metric("SALDO", f"${st.session_state.saldo:,.2f}")
    with col2:
        st.metric("TRADES ATIVOS", len(st.session_state.trades))
    
    # Modo automático
    st.divider()
    auto_mode = st.toggle("🤖 MODO AUTOMÁTICO", value=True, key="auto_mode_toggle")
    if auto_mode != st.session_state.auto_mode:
        st.session_state.auto_mode = auto_mode
        if auto_mode:
            st.success("Sistema automático ATIVADO!")
        else:
            st.warning("Sistema automático DESATIVADO!")
    
    # Configurações
    st.subheader("⚙️ CONFIGURAÇÕES")
    max_trades = st.slider("Máx. Trades Ativos", 1, 50, 20, key="max_trades_slider")
    trade_size = st.slider("Tamanho do Trade (%)", 0.5, 5.0, 1.0, key="trade_size_slider")
    
    st.divider()
    
    # Ações
    if st.button("🎯 FORÇAR ENTRADA", use_container_width=True):
        # Buscar token aleatório
        tokens = st.session_state.token_scanner.tokens_pool
        if tokens:
            ca = random.choice(tokens)
            token_data = buscar_token_sincrono(ca)
            if token_data:
                analise = analise_ultra_rapida(token_data)
                if analise['decisao'].startswith('COMPRAR'):
                    trade = criar_entrada_automatica(token_data, analise)
                    if trade:
                        st.success(f"✅ Entrada forçada em {trade['symbol']}")
    
    if st.button("🔄 ATUALIZAR TRADES", use_container_width=True):
        fechados = atualizar_trades()
        if fechados:
            st.info(f"📊 {len(fechados)} trades fechados")
    
    if st.button("🧹 LIMPAR TUDO", type="secondary", use_container_width=True):
        st.session_state.trades = []
        st.session_state.historico = []
        st.session_state.saldo = 1000.0
        st.session_state.estatisticas = {
            'total_trades': 0,
            'ganhos': 0,
            'perdas': 0,
            'lucro_total': 0.0,
            'lucro_dia': 0.0,
            'trades_dia': 0
        }
        st.success("Sistema reiniciado!")

# ==========================================================
# SEÇÃO PRINCIPAL
# ==========================================================

# Atualizar trades periodicamente
fechados = atualizar_trades()

# Status do sistema
col_status1, col_status2, col_status3 = st.columns(3)
with col_status1:
    st.metric("📊 TOTAL TRADES", st.session_state.estatisticas['total_trades'])
with col_status2:
    st.metric("📈 LUCRO DIA", f"${st.session_state.estatisticas['lucro_dia']:+.2f}")
with col_status3:
    if st.session_state.estatisticas['total_trades'] > 0:
        win_rate = (st.session_state.estatisticas['ganhos'] / st.session_state.estatisticas['total_trades']) * 100
        st.metric("🎯 WIN RATE", f"{win_rate:.1f}%")
    else:
        st.metric("🎯 WIN RATE", "0%")

st.divider()

# TRADES ATIVOS
st.header("🎯 TRADES ATIVOS")

if st.session_state.trades:
    # Grid de trades
    cols = st.columns(4)
    
    for idx, trade in enumerate(st.session_state.trades[:16]):
        with cols[idx % 4]:
            with st.container(border=True):
                profit = trade['profit_percent']
                color = "🟢" if profit >= 0 else "🔴"
                
                st.markdown(f"**{trade['symbol']}**")
                st.markdown(f"### {color} {profit:+.2f}%")
                
                st.caption(f"Entrada: ${trade['entry_price']:.8f}")
                st.caption(f"Atual: ${trade.get('current_price', trade['entry_price']):.8f}")
                st.caption(f"Tamanho: ${trade['position_size']:.2f}")
                
                # Duração
                if 'entry_time' in trade:
                    minutos = (datetime.now() - trade['entry_time']).seconds // 60
                    st.caption(f"⏱️ {minutos}min")
                
                if st.button("⏹️ SAIR", key=f"sair_{trade['id']}", use_container_width=True):
                    trade['exit_reason'] = 'MANUAL'
                    fechar_trade(trade, [])
                    st.rerun()
else:
    st.info("📭 Aguardando entradas automáticas...")
    
    # Mostrar status do scanner
    if st.session_state.auto_mode:
        st.success("🔍 Scanner ativo - Procurando oportunidades...")
        
        # Mostrar últimos tokens escaneados
        st.caption("Últimos tokens analisados:")
        tokens_amostra = st.session_state.token_scanner.tokens_pool[:5]
        for token in tokens_amostra:
            st.code(f"{token[:15]}...", language=None)

# HISTÓRICO
if st.session_state.historico:
    st.divider()
    st.header("📊 HISTÓRICO RECENTE")
    
    # Últimos 5 trades
    for trade in st.session_state.historico[-5:]:
        profit = trade['profit_value']
        emoji = "🟢" if profit >= 0 else "🔴"
        
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.write(f"{emoji} **{trade['symbol']}**")
            st.caption(f"{trade.get('exit_reason', 'N/A')}")
        with col2:
            st.write(f"Entrada: ${trade['entry_price']:.8f}")
            st.write(f"Saída: ${trade.get('exit_price', 0):.8f}")
        with col3:
            st.write(f"**{trade['profit_percent']:+.2f}%**")
            st.write(f"**${profit:+.2f}**")

# ==========================================================
# MONITORAMENTO DE TOKENS
# ==========================================================
st.divider()
st.header("🎯 ADICIONAR TOKENS")

col_a1, col_a2 = st.columns([3, 1])
with col_a1:
    novo_token = st.text_input("CA do Token:", placeholder="0x...", key="novo_token_input")
with col_a2:
    if st.button("➕ ADICIONAR", use_container_width=True) and novo_token:
        # Adicionar ao pool do scanner
        if novo_token not in st.session_state.token_scanner.tokens_pool:
            st.session_state.token_scanner.tokens_pool.append(novo_token.strip())
            st.success(f"✅ Token adicionado ao scanner!")
            
            # Adicionar à lista de monitoramento
            if not any(m['ca'] == novo_token.strip() for m in st.session_state.monitorando):
                st.session_state.monitorando.append({
                    'ca': novo_token.strip(),
                    'symbol': 'NOVO',
                    'adicionado': datetime.now()
                })

# ==========================================================
# CSS PARA INTERFACE
# ==========================================================
st.markdown("""
<style>
    .stButton > button {
        background: linear-gradient(45deg, #FF0000, #FF8C00);
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
    
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# AUTO-REFRESH
# ==========================================================

# Auto-refresh a cada 5 segundos para atualizar a interface
time.sleep(5)
st.rerun()