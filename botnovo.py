import streamlit as st
import requests
import pandas as pd
import numpy as np
import time
import os
import logging
import plotly.graph_objects as go
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from functools import lru_cache
from datetime import datetime, timedelta
import threading
import queue
import json

# ==========================================================
# CONFIGURAÇÃO INICIAL
# ==========================================================

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Segurança: Sem fallback para senha
SNIPER_SENHA = os.getenv('SNIPER_SENHA')
if not SNIPER_SENHA:
    st.error("❌ Variável de ambiente SNIPER_SENHA não configurada")
    st.stop()

# ==========================================================
# CLASSES DE DADOS
# ==========================================================

@dataclass
class Trade:
    """Classe para representar uma ordem de trade"""
    id: int
    entrada: float
    pnl: float = 0.0
    ativo: bool = True
    pnl_max: float = 0.0
    motivo_saida: str = ""
    historico_precos: List[float] = field(default_factory=list)
    timestamp_entrada: float = field(default_factory=time.time)
    timestamp_saida: Optional[float] = None
    
    def __post_init__(self):
        self.historico_precos = [self.entrada]
    
    def atualizar(self, preco_atual: float):
        """Atualiza PnL e histórico"""
        self.pnl = ((preco_atual / self.entrada) - 1) * 100
        if self.pnl > self.pnl_max:
            self.pnl_max = self.pnl
        self.historico_precos.append(preco_atual)
        # Mantém apenas últimos 20 preços
        if len(self.historico_precos) > 20:
            self.historico_precos.pop(0)
    
    def fechar(self, motivo: str):
        """Fecha o trade"""
        self.ativo = False
        self.motivo_saida = motivo
        self.timestamp_saida = time.time()

@dataclass
class RiskManager:
    """Gerenciador de risco"""
    saldo_inicial: float
    stop_loss_global: float = -10.0  # -10% do saldo
    stop_loss_trade: float = -5.0    # -5% por trade
    take_profit: float = 15.0        # +15% por trade
    max_drawdown_diario: float = 5.0 # 5% máximo de perda diária
    max_trades_consecutivos_perda: int = 3
    
    def __post_init__(self):
        self.saldo_atual = self.saldo_inicial
        self.drawdown_atual = 0.0
        self.trades_hoje = []
        self.perdas_consecutivas = 0
        self.saldo_max = self.saldo_inicial
    
    def pode_operar(self, valor_operacao: float) -> tuple[bool, str]:
        """Verifica se pode abrir nova operação"""
        # Verifica drawdown diário
        perda_diaria = sum([t for t in self.trades_hoje if t < 0])
        if abs(perda_diaria) > self.saldo_inicial * (self.max_drawdown_diario / 100):
            return False, "Limite diário de perda atingido"
        
        # Verifica perdas consecutivas
        if self.perdas_consecutivas >= self.max_trades_consecutivos_perda:
            return False, f"{self.perdas_consecutivas} perdas consecutivas - pausa"
        
        # Verifica se há saldo suficiente
        if valor_operacao > self.saldo_atual * 0.1:  # No máximo 10% do saldo por trade
            return False, "Valor da operação muito alto"
        
        return True, ""
    
    def registrar_trade(self, resultado: float):
        """Registra resultado do trade"""
        self.trades_hoje.append(resultado)
        self.saldo_atual += resultado
        
        # Atualiza drawdown
        if self.saldo_atual > self.saldo_max:
            self.saldo_max = self.saldo_atual
        self.drawdown_atual = ((self.saldo_max - self.saldo_atual) / self.saldo_max) * 100
        
        # Atualiza contador de perdas consecutivas
        if resultado < 0:
            self.perdas_consecutivas += 1
        else:
            self.perdas_consecutivas = 0
    
    def get_metrics(self) -> Dict:
        """Retorna métricas de risco"""
        return {
            'saldo': self.saldo_atual,
            'drawdown': self.drawdown_atual,
            'perdas_consecutivas': self.perdas_consecutivas,
            'trades_hoje': len(self.trades_hoje),
            'win_rate': self.calcular_win_rate()
        }
    
    def calcular_win_rate(self) -> float:
        """Calcula win rate dos trades de hoje"""
        if not self.trades_hoje:
            return 0.0
        vitorias = sum(1 for t in self.trades_hoje if t > 0)
        return (vitorias / len(self.trades_hoje)) * 100

class TradingBot:
    """Classe principal do bot de trading"""
    
    def __init__(self, saldo_inicial: float = 1000.0):
        self.risk_manager = RiskManager(saldo_inicial)
        self.trades_ativos: List[Trade] = []
        self.historico_trades = []
        self.token_ca = ""
        self.token_symbol = ""
        self.valor_por_trade = 0.0
        self.ciclo = 1
        self.status = "parado"
        self.ultimo_preco = 0.0
        self.falhas_consecutivas = 0
        
    def iniciar(self, token_ca: str, valor_por_trade: float):
        """Inicia o bot com um token"""
        preco = self.obter_preco(token_ca)
        if not preco:
            raise ValueError("Não foi possível obter preço do token")
        
        self.token_ca = token_ca
        self.token_symbol = self.obter_info_token(token_ca)
        self.valor_por_trade = valor_por_trade
        self.ultimo_preco = preco
        
        # Cria 10 ordens
        self.trades_ativos = []
        for i in range(10):
            trade = Trade(id=i+1, entrada=preco)
            self.trades_ativos.append(trade)
        
        self.status = "rodando"
        logger.info(f"Bot iniciado para {self.token_symbol} ({token_ca[:8]}...)")
        return True
    
    def parar(self):
        """Para o bot"""
        self.status = "parado"
        logger.info("Bot parado")
    
    def processar_ciclo(self):
        """Processa um ciclo de trading"""
        if self.status != "rodando":
            return
        
        # Obtém preço atual
        preco = self.obter_preco(self.token_ca)
        if preco is None:
            self.falhas_consecutivas += 1
            if self.falhas_consecutivas > 3:
                logger.error("Múltiplas falhas ao obter preço - parando")
                self.parar()
            return
        
        self.falhas_consecutivas = 0
        self.ultimo_preco = preco
        
        # Processa cada trade ativo
        for trade in self.trades_ativos:
            if trade.ativo:
                trade.atualizar(preco)
                
                # Verifica se deve fechar
                fechar, motivo = self.analisar_trade(trade)
                if fechar:
                    trade.fechar(motivo)
                    lucro = self.valor_por_trade * (trade.pnl / 100)
                    self.risk_manager.registrar_trade(lucro)
                    
                    self.historico_trades.append({
                        'ciclo': self.ciclo,
                        'trade_id': trade.id,
                        'entrada': trade.entrada,
                        'saida': preco,
                        'pnl': round(trade.pnl, 2),
                        'lucro_usd': round(lucro, 2),
                        'motivo': motivo,
                        'duracao': trade.timestamp_saida - trade.timestamp_entrada,
                        'timestamp': datetime.now().isoformat()
                    })
        
        self.ciclo += 1
    
    def analisar_trade(self, trade: Trade) -> tuple[bool, str]:
        """Analisa se deve fechar o trade"""
        # Stop loss por trade
        if trade.pnl <= self.risk_manager.stop_loss_trade:
            return True, f"Stop Loss ({trade.pnl:.1f}%)"
        
        # Take profit
        if trade.pnl >= self.risk_manager.take_profit:
            return True, f"Take Profit ({trade.pnl:.1f}%)"
        
        # Stop loss global
        if self.risk_manager.drawdown_atual >= abs(self.risk_manager.stop_loss_global):
            return True, f"Stop Loss Global ({self.risk_manager.drawdown_atual:.1f}%)"
        
        # Trailing stop (se teve alta de 10% e caiu 3%)
        if trade.pnl_max >= 10.0 and trade.pnl < trade.pnl_max - 3.0:
            return True, f"Trailing Stop ({trade.pnl:.1f}%)"
        
        return False, ""
    
    @staticmethod
    @lru_cache(maxsize=100)
    def obter_preco(token_ca: str) -> Optional[float]:
        """Obtém preço do token com cache"""
        try:
            # Tentativa 1: Jupiter API
            url = f"https://api.jup.ag/price/v2?ids={token_ca}"
            response = requests.get(url, timeout=5)
            data = response.json()
            price = data.get('data', {}).get(token_ca, {}).get('price')
            if price:
                return float(price)
        except:
            pass
        
        try:
            # Tentativa 2: DexScreener
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_ca}"
            response = requests.get(url, timeout=5)
            data = response.json()
            pairs = data.get('pairs', [])
            if pairs:
                return float(pairs[0].get('priceUsd', 0))
        except:
            pass
        
        return None
    
    @staticmethod
    def obter_info_token(token_ca: str) -> str:
        """Obtém informação do token"""
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_ca}"
            response = requests.get(url, timeout=5)
            data = response.json()
            return data.get('pairs', [{}])[0].get('baseToken', {}).get('symbol', 'TOKEN')
        except:
            return "TOKEN"

# ==========================================================
# SISTEMA DE ALERTAS
# ==========================================================

class AlertSystem:
    """Sistema de alertas"""
    
    @staticmethod
    def enviar(mensagem: str, nivel: str = "info"):
        """Envia alerta"""
        # Log no console
        logger.log(
            logging.INFO if nivel == "info" else logging.WARNING,
            mensagem
        )
        
        # Alertas no Streamlit
        if nivel == "erro":
            st.error(f"🚨 {mensagem}")
        elif nivel == "aviso":
            st.warning(f"⚠️ {mensagem}")
        elif nivel == "sucesso":
            st.success(f"✅ {mensagem}")
        
        # Webhook (opcional)
        webhook_url = os.getenv("WEBHOOK_URL")
        if webhook_url:
            try:
                payload = {
                    "content": f"[SNIPER] {mensagem}",
                    "timestamp": datetime.now().isoformat()
                }
                requests.post(webhook_url, json=payload, timeout=2)
            except:
                pass

# ==========================================================
# THREAD DE BACKGROUND
# ==========================================================

class BotThread(threading.Thread):
    """Thread para executar o bot em background"""
    
    def __init__(self, bot: TradingBot, update_interval: int = 3):
        super().__init__()
        self.bot = bot
        self.update_interval = update_interval
        self.running = False
        self.queue = queue.Queue()
        self.daemon = True
    
    def run(self):
        """Loop principal da thread"""
        self.running = True
        while self.running:
            try:
                # Processa comandos da fila
                while not self.queue.empty():
                    cmd = self.queue.get_nowait()
                    if cmd == "stop":
                        self.running = False
                        break
                
                if self.running and self.bot.status == "rodando":
                    self.bot.processar_ciclo()
                
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Erro na thread do bot: {e}")
                time.sleep(self.update_interval * 2)
    
    def stop(self):
        """Para a thread"""
        self.running = False
        self.queue.put("stop")

# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================

@st.cache_data(ttl=3600)
def get_exchange_rate():
    """Obtém taxa de câmbio USD/BRL"""
    try:
        response = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5)
        data = response.json()
        return float(data['rates'].get('BRL', 5.05))
    except:
        return 5.05

def formatar_moeda(valor: float, moeda: str) -> str:
    """Formata valor monetário"""
    if moeda == "BRL":
        return f"R$ {valor:,.2f}"
    return f"$ {valor:,.2f}"

# ==========================================================
# INICIALIZAÇÃO DO STREAMLIT
# ==========================================================

st.set_page_config(
    page_title="Sniper Pro v30",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialização do estado da sessão
if 'bot' not in st.session_state:
    st.session_state.bot = TradingBot(saldo_inicial=1000.0)

if 'bot_thread' not in st.session_state:
    st.session_state.bot_thread = None

if 'auth' not in st.session_state:
    st.session_state.auth = False

if 'moeda' not in st.session_state:
    st.session_state.moeda = "USD"

if 'taxa_cambio' not in st.session_state:
    st.session_state.taxa_cambio = 1.0

# ==========================================================
# INTERFACE - AUTENTICAÇÃO
# ==========================================================

if not st.session_state.auth:
    st.title("🔐 Acesso Sniper Pro v30")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            senha = st.text_input("Senha de acesso:", type="password")
            
            if st.button("🔓 Entrar", use_container_width=True):
                if senha == SNIPER_SENHA:
                    st.session_state.auth = True
                    st.rerun()
                else:
                    AlertSystem.enviar("Senha incorreta!", "erro")
    
    # Informações de segurança
    with st.expander("🔒 Informações de Segurança"):
        st.info("""
        **Recomendações de segurança:**
        1. Use uma senha forte na variável de ambiente SNIPER_SENHA
        2. Nunca exponha suas chaves de API
        3. Use VPN para acesso remoto
        4. Monitore os logs regularmente
        """)
    
    st.stop()

# ==========================================================
# INTERFACE PRINCIPAL
# ==========================================================

# Sidebar
with st.sidebar:
    st.title("⚙️ Controle")
    
    # Seleção de moeda
    st.session_state.moeda = st.radio(
        "Moeda de exibição:",
        ["USD", "BRL"],
        horizontal=True
    )
    
    if st.session_state.moeda == "BRL":
        st.session_state.taxa_cambio = get_exchange_rate()
    else:
        st.session_state.taxa_cambio = 1.0
    
    # Informações da conta
    st.divider()
    st.subheader("💰 Banca")
    
    metrics = st.session_state.bot.risk_manager.get_metrics()
    
    col_saldo1, col_saldo2 = st.columns(2)
    with col_saldo1:
        saldo_usd = metrics['saldo']
        st.metric(
            "Saldo USD",
            f"$ {saldo_usd:,.2f}",
            delta=f"{formatar_moeda(saldo_usd - 1000, 'USD')}"
        )
    
    with col_saldo2:
        saldo_moeda = saldo_usd * st.session_state.taxa_cambio
        st.metric(
            f"Saldo {st.session_state.moeda}",
            formatar_moeda(saldo_moeda, st.session_state.moeda)
        )
    
    # Métricas de risco
    st.divider()
    st.subheader("📊 Métricas")
    
    col_metrics1, col_metrics2 = st.columns(2)
    with col_metrics1:
        st.metric("Drawdown", f"{metrics['drawdown']:.1f}%")
        st.metric("Trades Hoje", metrics['trades_hoje'])
    
    with col_metrics2:
        st.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
        st.metric("Perdas Consec.", metrics['perdas_consecutivas'])
    
    # Controles
    st.divider()
    st.subheader("🎮 Controles")
    
    if st.button("🔄 Atualizar Dados", use_container_width=True):
        st.rerun()
    
    if st.button("📊 Exportar Dados", use_container_width=True):
        if st.session_state.bot.historico_trades:
            df = pd.DataFrame(st.session_state.bot.historico_trades)
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇️ Baixar CSV",
                data=csv,
                file_name=f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    if st.button("🚪 Logout", use_container_width=True):
        if st.session_state.bot_thread:
            st.session_state.bot_thread.stop()
            st.session_state.bot_thread = None
        
        st.session_state.auth = False
        st.rerun()

# ==========================================================
# TELA PRINCIPAL
# ==========================================================

# Título
st.title("🚀 Sniper Pro v30")
st.caption("Sistema de Trading Automatizado com Gestão de Risco Inteligente")

# Seção 1: Status do Bot
col_status1, col_status2, col_status3 = st.columns(3)
with col_status1:
    status_icon = "🟢" if st.session_state.bot.status == "rodando" else "🔴"
    st.metric("Status", f"{status_icon} {st.session_state.bot.status.upper()}")

with col_status2:
    if st.session_state.bot.token_symbol:
        st.metric("Token Monitorado", st.session_state.bot.token_symbol)
    else:
        st.metric("Token Monitorado", "Nenhum")

with col_status3:
    st.metric("Ciclos Processados", st.session_state.bot.ciclo)

# Seção 2: Controle do Bot
if st.session_state.bot.status == "parado":
    with st.container(border=True):
        st.subheader("🎯 Configurar Nova Operação")
        
        col_input1, col_input2 = st.columns(2)
        with col_input1:
            token_ca = st.text_input(
                "Contract Address (CA):",
                placeholder="Ex: So11111111111111111111111111111111111111112"
            )
        
        with col_input2:
            valor_trade = st.number_input(
                f"Valor por Trade ({st.session_state.moeda}):",
                min_value=0.1,
                value=10.0 * st.session_state.taxa_cambio,
                step=1.0
            )
        
        if st.button("▶️ Iniciar Bot", type="primary", use_container_width=True):
            if not token_ca.strip():
                AlertSystem.enviar("Por favor, insira um Contract Address", "erro")
            else:
                with st.spinner("Iniciando bot..."):
                    try:
                        valor_usd = valor_trade / st.session_state.taxa_cambio
                        sucesso = st.session_state.bot.iniciar(token_ca.strip(), valor_usd)
                        
                        if sucesso:
                            # Inicia thread em background
                            st.session_state.bot_thread = BotThread(st.session_state.bot)
                            st.session_state.bot_thread.start()
                            
                            AlertSystem.enviar(
                                f"Bot iniciado para {st.session_state.bot.token_symbol}",
                                "sucesso"
                            )
                            st.rerun()
                    except Exception as e:
                        AlertSystem.enviar(f"Erro ao iniciar bot: {str(e)}", "erro")
else:
    with st.container(border=True):
        st.subheader(f"📈 Monitorando: {st.session_state.bot.token_symbol}")
        
        # Preço atual
        if st.session_state.bot.ultimo_preco:
            col_price1, col_price2 = st.columns([2, 1])
            with col_price1:
                st.markdown(f"**Preço atual:** `{st.session_state.bot.ultimo_preco:.10f}`")
            
            with col_price2:
                if st.button("⏹️ Parar Bot", type="secondary", use_container_width=True):
                    st.session_state.bot.parar()
                    if st.session_state.bot_thread:
                        st.session_state.bot_thread.stop()
                        st.session_state.bot_thread = None
                    
                    AlertSystem.enviar("Bot parado com sucesso", "sucesso")
                    st.rerun()

# Seção 3: Trades Ativos
st.subheader("📊 Trades Ativos")

if st.session_state.bot.trades_ativos:
    # Criar gráfico de preços
    fig = go.Figure()
    
    for trade in st.session_state.bot.trades_ativos[:5]:  # Mostrar apenas 5 para não poluir
        if trade.historico_precos:
            fig.add_trace(go.Scatter(
                y=trade.historico_precos,
                mode='lines+markers',
                name=f'Trade {trade.id}',
                line=dict(width=2),
                marker=dict(size=6)
            ))
    
    fig.update_layout(
        title="Histórico de Preços dos Trades",
        xaxis_title="Período",
        yaxis_title="Preço (USD)",
        height=300,
        showlegend=True,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Lista de trades
    st.divider()
    
    cols = st.columns(5)
    for idx, trade in enumerate(st.session_state.bot.trades_ativos[:10]):
        col_idx = idx % 5
        with cols[col_idx]:
            with st.container(border=True):
                status_color = "🟢" if trade.ativo else "🔴"
                pnl_color = "green" if trade.pnl >= 0 else "red"
                
                st.markdown(f"**{status_color} Trade {trade.id}**")
                st.markdown(f"Entrada: `{trade.entrada:.8f}`")
                st.markdown(f"<span style='color:{pnl_color}'>PnL: {trade.pnl:+.2f}%</span>", 
                           unsafe_allow_html=True)
                
                if not trade.ativo:
                    st.caption(f"✅ {trade.motivo_saida}")
else:
    st.info("Nenhum trade ativo. Inicie o bot para começar.")

# Seção 4: Histórico de Trades
if st.session_state.bot.historico_trades:
    st.subheader("📜 Histórico de Trades Fechados")
    
    # Estatísticas do histórico
    df_hist = pd.DataFrame(st.session_state.bot.historico_trades)
    
    if not df_hist.empty:
        col_hist1, col_hist2, col_hist3, col_hist4 = st.columns(4)
        
        with col_hist1:
            total_trades = len(df_hist)
            st.metric("Total Trades", total_trades)
        
        with col_hist2:
            trades_vencedores = (df_hist['pnl'] > 0).sum()
            st.metric("Trades +", trades_vencedores)
        
        with col_hist3:
            win_rate = (trades_vencedores / total_trades * 100) if total_trades > 0 else 0
            st.metric("Win Rate", f"{win_rate:.1f}%")
        
        with col_hist4:
            lucro_total = df_hist['lucro_usd'].sum()
            st.metric("Lucro Total", f"$ {lucro_total:,.2f}")
        
        # Tabela de histórico
        st.dataframe(
            df_hist[['trade_id', 'entrada', 'saida', 'pnl', 'lucro_usd', 'motivo', 'timestamp']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "trade_id": "ID",
                "entrada": st.column_config.NumberColumn("Entrada", format="%.8f"),
                "saida": st.column_config.NumberColumn("Saída", format="%.8f"),
                "pnl": st.column_config.NumberColumn("PnL %", format="+.2f"),
                "lucro_usd": st.column_config.NumberColumn("Lucro $", format="+.2f"),
                "motivo": "Motivo",
                "timestamp": "Data/Hora"
            }
        )

# Seção 5: Logs do Sistema
with st.expander("📋 Logs do Sistema"):
    log_container = st.container(height=200)
    
    # Aqui você pode implementar um sistema de logs em tempo real
    # Para simplificar, mostramos apenas o último log
    log_container.code(
        f"""
        Última atualização: {datetime.now().strftime('%H:%M:%S')}
        Status: {st.session_state.bot.status}
        Trades ativos: {sum(1 for t in st.session_state.bot.trades_ativos if t.ativo)}
        Trades fechados: {len(st.session_state.bot.historico_trades)}
        Falhas consecutivas: {st.session_state.bot.falhas_consecutivas}
        """,
        language="text"
    )

# ==========================================================
# FOOTER
# ==========================================================

st.divider()
footer_col1, footer_col2, footer_col3 = st.columns(3)
with footer_col1:
    st.caption(f"🕒 Última atualização: {datetime.now().strftime('%H:%M:%S')}")

with footer_col2:
    st.caption("⚠️ Use por sua conta e risco")

with footer_col3:
    st.caption("v30.0 | © 2024 Sniper Pro")

# ==========================================================
# SCRIPT DE BACKGROUND (para atualização automática)
# ==========================================================

# Atualização automática a cada 5 segundos quando o bot está rodando
if st.session_state.bot.status == "rodando":
    time.sleep(5)  # Aguarda 5 segundos
    st.rerun()  # Atualiza a página
else:
    # Atualização mais lenta quando parado
    time.sleep(30)
    st.rerun()