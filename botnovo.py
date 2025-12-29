import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import random

# ==========================================================
# CONFIGURAÇÃO
# ==========================================================
st.set_page_config(
    page_title="🔥 SNIPER AI - MICRO TRADES",
    page_icon="⚡",
    layout="wide"
)

# ==========================================================
# INICIALIZAÇÃO
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

# ==========================================================
# FUNÇÕES
# ==========================================================
def buscar_token(ca):
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

def analise_rapida(token_data):
    """Análise ultra rápida para micro trades"""
    try:
        pair = token_data['pairs'][0]
        
        symbol = pair.get('baseToken', {}).get('symbol', 'TOKEN')
        price = float(pair.get('priceUsd', 0))
        volume = float(pair.get('volume', {}).get('h24', 0))
        change_5m = float(pair.get('priceChange', {}).get('m5', 0))
        
        # Análise super simples para entrar rápido
        if volume > 5000:  # Volume mínimo muito baixo
            score = 0
            
            if volume > 10000:
                score += 2
            if abs(change_5m) > 2:  # Volatilidade
                score += 3
            if price < 0.001:  # Tokens baratos
                score += 2
            
            if score >= 3:
                return {
                    'decisao': 'COMPRAR',
                    'symbol': symbol,
                    'price': price,
                    'stop_loss': price * 0.98,  # -2% STOP APERTADO
                    'take_profit': price * 1.03,  # +3% TP CURTO
                    'score': score
                }
        
        return {'decisao': 'IGNORAR', 'symbol': symbol}
        
    except:
        return {'decisao': 'ERRO'}

def criar_micro_trade(token_data, analise):
    """Cria micro trade automático"""
    try:
        # Tamanho muito pequeno do trade (1-3% do saldo)
        tamanhos = [0.5, 1, 1.5, 2, 2.5, 3]
        percentual = random.choice(tamanhos)
        
        # Se está ganhando, aumenta um pouco o tamanho
        if st.session_state.estatisticas['lucro_dia'] > 0:
            percentual = min(percentual * 1.5, 5)
        
        valor_trade = st.session_state.saldo * (percentual / 100)
        
        # Mínimo $0.50, máximo $50 (para micro trades)
        valor_trade = max(0.50, min(valor_trade, 50))
        
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
            'tipo': 'MICRO'
        }
        
        # Deduzir do saldo
        st.session_state.saldo -= valor_trade
        st.session_state.trades.append(trade)
        st.session_state.ultimo_trade = datetime.now()
        st.session_state.estatisticas['total_trades'] += 1
        st.session_state.estatisticas['trades_dia'] += 1
        
        return trade
        
    except:
        return None

def atualizar_trades():
    """Atualiza e fecha trades automaticamente"""
    fechados = []
    
    for trade in st.session_state.trades[:]:
        try:
            # Buscar preço atual
            data = buscar_token(trade['ca'])
            if data and data.get('pairs'):
                current_price = float(data['pairs'][0].get('priceUsd', 0))
                trade['current_price'] = current_price
                
                # Calcular lucro
                profit_percent = ((current_price - trade['entry_price']) / trade['entry_price']) * 100
                profit_value = trade['position_size'] * (profit_percent / 100)
                
                trade['profit_percent'] = profit_percent
                trade['profit_value'] = profit_value
                
                # Verificar saída AUTOMÁTICA
                if current_price >= trade['take_profit']:
                    trade['exit_reason'] = 'TP_HIT'
                    fechar_trade(trade, fechados)
                elif current_price <= trade['stop_loss']:
                    trade['exit_reason'] = 'SL_HIT'
                    fechar_trade(trade, fechados)
                # Saída por tempo (máximo 30 minutos)
                elif (datetime.now() - trade['entry_time']).seconds > 1800:
                    trade['exit_reason'] = 'TIMEOUT'
                    fechar_trade(trade, fechados)
                    
        except:
            continue
    
    return fechados

def fechar_trade(trade, fechados):
    """Fecha trade e atualiza estatísticas"""
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

def entrada_automatica():
    """Faz entradas automáticas baseadas em tokens monitorados"""
    if not st.session_state.auto_mode:
        return
    
    # Limitar frequência (máximo 1 trade a cada 10 segundos)
    if (datetime.now() - st.session_state.ultimo_trade).seconds < 10:
        return
    
    # Limitar máximo de trades ativos
    if len(st.session_state.trades) >= 20:
        return
    
    # Lista de tokens populares para monitorar automaticamente
    tokens_base = [
        "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",  # ETH
        "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # BNB
        "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",  # USDC
        "0x55d398326f99059fF775485246999027B3197955",  # USDT
        "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",  # CAKE
    ]
    
    # Adicionar tokens do usuário
    todos_tokens = list(set(tokens_base + [t['ca'] for t in st.session_state.monitorando]))
    
    # Selecionar aleatoriamente alguns tokens para analisar
    tokens_analisar = random.sample(todos_tokens, min(3, len(todos_tokens)))
    
    for ca in tokens_analisar:
        # Verificar se já tem trade ativo para este token
        if any(t['ca'] == ca for t in st.session_state.trades):
            continue
        
        # Buscar dados
        token_data = buscar_token(ca)
        if token_data:
            # Análise rápida
            analise = analise_rapida(token_data)
            
            if analise['decisao'] == 'COMPRAR':
                # Criar micro trade
                trade = criar_micro_trade(token_data, analise)
                if trade:
                    # Adicionar aos monitorados se não estiver
                    if not any(m['ca'] == ca for m in st.session_state.monitorando):
                        st.session_state.monitorando.append({
                            'ca': ca,
                            'symbol': analise['symbol'],
                            'adicionado': datetime.now()
                        })
                    return trade  # Uma entrada por ciclo

# ==========================================================
# INTERFACE
# ==========================================================
st.title("🔥 SNIPER AI - AUTO MICRO TRADES")
st.markdown("### Entradas Automáticas 24/7 | Crescimento Exponencial")

# ==========================================================
# SIDEBAR
# ==========================================================
with st.sidebar:
    st.header("💰 SALDO & CONTROLE")
    
    # Editor de saldo
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        novo_saldo = st.number_input(
            "DEFINIR SALDO",
            min_value=100.0,
            max_value=100000.0,
            value=float(st.session_state.saldo),
            step=100.0
        )
    with col_s2:
        if st.button("💾 ATUALIZAR", use_container_width=True):
            st.session_state.saldo = novo_saldo
            st.success(f"Saldo: ${novo_saldo:,.2f}")
            st.rerun()
    
    # Estatísticas
    st.divider()
    stats = st.session_state.estatisticas
    
    st.metric("💵 SALDO ATUAL", f"${st.session_state.saldo:,.2f}")
    st.metric("📊 LUCRO DIA", f"${stats['lucro_dia']:+.2f}")
    
    if stats['total_trades'] > 0:
        win_rate = (stats['ganhos'] / stats['total_trades']) * 100
        st.metric("🎯 WIN RATE", f"{win_rate:.1f}%")
    else:
        st.metric("🎯 WIN RATE", "0%")
    
    st.metric("⚡ TRADES/DIA", stats['trades_dia'])
    
    st.divider()
    
    # Controles
    st.header("⚙️ CONFIGURAÇÕES")
    
    st.session_state.auto_mode = st.toggle(
        "🤖 AUTO ENTRADAS",
        value=st.session_state.auto_mode,
        help="Entrada automática de micro trades"
    )
    
    st.slider("MAX TRADES ATIVOS", 5, 50, 20, key="max_trades")
    
    st.divider()
    
    # Ações rápidas
    if st.button("🎯 FORÇAR ENTRADA", use_container_width=True):
        trade = entrada_automatica()
        if trade:
            st.success(f"✅ Entrada em {trade['symbol']}")
        else:
            st.info("⏳ Aguardando oportunidade")
        st.rerun()
    
    if st.button("🔄 ATUALIZAR TUDO", use_container_width=True):
        fechados = atualizar_trades()
        if fechados:
            st.info(f"{len(fechados)} trades fechados")
        st.rerun()
    
    if st.button("📊 EXPORTAR", use_container_width=True):
        if st.session_state.historico:
            df = pd.DataFrame(st.session_state.historico)
            csv = df.to_csv(index=False)
            st.download_button(
                "⬇️ BAIXAR CSV",
                csv,
                "trades.csv",
                "text/csv",
                use_container_width=True
            )
    
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
        st.rerun()

# ==========================================================
# SEÇÃO 1: ADICIONAR TOKENS PARA MONITORAR
# ==========================================================
st.header("🎯 ADICIONAR TOKENS")

col_a1, col_a2 = st.columns([3, 1])
with col_a1:
    novo_token = st.text_input("CA do Token:", placeholder="0x...")
with col_a2:
    if st.button("➕ ADICIONAR", type="primary", use_container_width=True) and novo_token:
        token_data = buscar_token(novo_token.strip())
        if token_data:
            symbol = token_data['pairs'][0].get('baseToken', {}).get('symbol', 'TOKEN')
            if not any(m['ca'] == novo_token.strip() for m in st.session_state.monitorando):
                st.session_state.monitorando.append({
                    'ca': novo_token.strip(),
                    'symbol': symbol,
                    'adicionado': datetime.now()
                })
                st.success(f"✅ {symbol} adicionado!")
                st.rerun()
        else:
            st.error("❌ Token não encontrado")

# Mostrar tokens monitorados
if st.session_state.monitorando:
    st.subheader(f"📋 {len(st.session_state.monitorando)} TOKENS MONITORADOS")
    
    cols = st.columns(4)
    for idx, token in enumerate(st.session_state.monitorando[:8]):
        with cols[idx % 4]:
            with st.container(border=True):
                st.write(f"**{token['symbol']}**")
                st.caption(f"`{token['ca'][:15]}...`")
                if st.button("🗑️", key=f"del_{token['ca']}", use_container_width=True):
                    st.session_state.monitorando.remove(token)
                    st.rerun()

# ==========================================================
# SEÇÃO 2: TRADES ATIVOS
# ==========================================================
st.header("📈 TRADES ATIVOS")

# Executar sistema automático
fechados = atualizar_trades()
if st.session_state.auto_mode:
    entrada_automatica()

# Mostrar trades fechados recentemente
if fechados:
    st.subheader("🔒 ÚLTIMOS FECHAMENTOS")
    for trade in fechados[-3:]:
        profit = trade['profit_value']
        emoji = "🟢" if profit >= 0 else "🔴"
        st.info(f"{emoji} **{trade['symbol']}** - {trade.get('exit_reason', 'MANUAL')} - {trade['profit_percent']:+.2f}% (${profit:+.2f})")

# Mostrar trades ativos
if st.session_state.trades:
    st.subheader(f"🟢 {len(st.session_state.trades)} TRADES EM ANDAMENTO")
    
    # Grid de trades
    cols = st.columns(4)
    
    for idx, trade in enumerate(st.session_state.trades[:12]):
        with cols[idx % 4]:
            with st.container(border=True):
                profit = trade['profit_percent']
                color = "🟢" if profit >= 0 else "🔴"
                
                # Cabeçalho
                st.markdown(f"**{trade['symbol']}** ({trade['tipo']})")
                st.markdown(f"### {color} {profit:+.2f}%")
                
                # Informações
                st.caption(f"💰 ${trade['position_size']:.2f}")
                st.caption(f"📊 Entrada: ${trade['entry_price']:.8f}")
                st.caption(f"🎯 TP: +3% | ⛔ SL: -2%")
                
                # Duração
                minutos = (datetime.now() - trade['entry_time']).seconds // 60
                st.caption(f"⏱️ {minutos}min")
                
                # Botão de saída
                if st.button("⏹️ SAIR", key=f"manual_{trade['id']}", use_container_width=True):
                    trade['exit_reason'] = 'MANUAL'
                    fechar_trade(trade, [])
                    st.rerun()
else:
    st.info("📭 Nenhum trade ativo - Sistema aguardando entradas automáticas")

# ==========================================================
# SEÇÃO 3: HISTÓRICO
# ==========================================================
if st.session_state.historico:
    st.header("📊 HISTÓRICO RECENTE")
    
    # Resumo
    total = st.session_state.estatisticas['total_trades']
    ganhos = st.session_state.estatisticas['ganhos']
    if total > 0:
        win_rate = (ganhos / total) * 100
        st.metric("📈 PERFORMANCE", f"{win_rate:.1f}% Win Rate", f"{total} trades totais")
    
    # Últimos trades
    for trade in st.session_state.historico[-5:]:
        profit = trade['profit_value']
        emoji = "🟢" if profit >= 0 else "🔴"
        
        col_h1, col_h2, col_h3 = st.columns([2, 2, 1])
        with col_h1:
            st.write(f"{emoji} **{trade['symbol']}**")
            st.caption(f"${trade['position_size']:.2f} | {trade.get('exit_reason', 'N/A')}")
        with col_h2:
            st.write(f"Entrada: ${trade['entry_price']:.8f}")
            st.write(f"Saída: ${trade.get('exit_price', 0):.8f}")
        with col_h3:
            st.write(f"**{trade['profit_percent']:+.2f}%**")
            st.write(f"**${profit:+.2f}**")

# ==========================================================
# SEÇÃO 4: DASHBOARD DE CRESCIMENTO
# ==========================================================
st.header("🚀 CRESCIMENTO EXPONENCIAL")

# Calcular crescimento projetado
if st.session_state.estatisticas['total_trades'] > 0:
    trades_hora = st.session_state.estatisticas['trades_dia'] / 24
    lucro_medio = st.session_state.estatisticas['lucro_total'] / st.session_state.estatisticas['total_trades']
    
    col_c1, col_c2, col_c3 = st.columns(3)
    
    with col_c1:
        st.metric("📊 LUCRO/MÉDIO", f"${lucro_medio:+.2f}")
    
    with col_c2:
        st.metric("⚡ TRADES/HORA", f"{trades_hora:.1f}")
    
    with col_c3:
        crescimento_diario = (st.session_state.estatisticas['lucro_dia'] / st.session_state.saldo) * 100
        st.metric("📈 CRESC./DIA", f"{crescimento_diario:+.1f}%")
    
    # Projeção de crescimento
    st.subheader("🎯 PROJEÇÕES")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    
    with col_p1:
        # 1 dia
        proj_1dia = st.session_state.saldo * (1 + (crescimento_diario/100))
        st.metric("1 DIA", f"${proj_1dia:,.2f}")
    
    with col_p2:
        # 7 dias (composição)
        proj_7dias = st.session_state.saldo * ((1 + (crescimento_diario/100)) ** 7)
        st.metric("7 DIAS", f"${proj_7dias:,.2f}")
    
    with col_p3:
        # 30 dias
        proj_30dias = st.session_state.saldo * ((1 + (crescimento_diario/100)) ** 30)
        st.metric("30 DIAS", f"${proj_30dias:,.2f}")

# ==========================================================
# CSS
# ==========================================================
st.markdown("""
<style>
    /* Interface agressiva */
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
        background: linear-gradient(45deg, #00FF00, #00AA00);
    }
    
    .stButton > button[kind="secondary"] {
        background: linear-gradient(45deg, #FFA500, #FF4500);
    }
    
    /* Cards de trade */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 10px;
        border: 2px solid;
        padding: 15px;
        margin: 10px 0;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(255, 0, 0, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 0, 0, 0); }
    }
    
    /* Métricas */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: bold;
    }
    
    /* Títulos coloridos */
    h1, h2, h3 {
        background: linear-gradient(45deg, #FF0000, #FF8C00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# AUTO-REFRESH E ENTRADAS AUTOMÁTICAS
# ==========================================================
if st.session_state.auto_mode:
    # Se está em modo automático, faz entradas constantes
    tempo_espera = 15  # Segundos entre ciclos
    
    # Mostrar status
    st.toast(f"⚡ Entradas automáticas ativas! Próximo ciclo em {tempo_espera}s")
    
    # Auto-refresh
    time.sleep(tempo_espera)
    st.rerun()