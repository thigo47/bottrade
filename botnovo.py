import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime
import plotly.graph_objects as go
from openai import OpenAI  # VERSÃO 1.0.0+

# ========== CONFIGURAÇÃO ==========
st.set_page_config(
    page_title="Sniper AI Trader",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 SNIPER AI TRADER - DEEPSEEK")

# ========== CONFIGURAÇÃO DEEPSEEK ==========
with st.sidebar:
    st.header("🔧 CONFIGURAÇÃO")
    
    # Configurar DeepSeek
    st.subheader("🧠 CONFIGURAR DEEPSEEK AI")
    
    api_key = st.text_input(
        "Chave API DeepSeek:",
        type="password",
        placeholder="sk-...",
        help="Obtenha em: https://platform.deepseek.com/api_keys"
    )
    
    if api_key:
        try:
            # VERSÃO CORRETA para openai>=1.0.0
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com/v1"
            )
            
            # Testar conexão (nova sintaxe)
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "Teste"}],
                max_tokens=10
            )
            
            if response.choices[0].message.content:
                st.session_state.client = client
                st.success("✅ DeepSeek conectado com sucesso!")
                st.balloons()
            else:
                st.error("❌ Erro na resposta")
                
        except Exception as e:
            st.error(f"❌ Erro: {str(e)[:100]}")
            st.info("Verifique a chave em: https://platform.deepseek.com")
    
    st.divider()
    
    # Status
    st.subheader("📊 STATUS")
    if 'client' in st.session_state:
        st.success("✅ IA PRONTA")
    else:
        st.warning("⚠️ Configure a IA")
    
    st.divider()
    
    # Configurações
    st.subheader("⚙️ PARÂMETROS")
    st.slider("Confiança mínima", 60, 95, 75, key="min_conf")
    st.slider("Stop Loss (%)", 5, 20, 10, key="stop_loss")
    st.slider("Take Profit (%)", 15, 50, 25, key="take_profit")

# ========== FUNÇÕES ==========
def buscar_token(ca):
    """Busca dados do token"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def analisar_com_deepseek(token_data):
    """Analisa token usando DeepSeek"""
    try:
        symbol = token_data.get('pairs', [{}])[0].get('baseToken', {}).get('symbol', 'TOKEN')
        price = float(token_data.get('pairs', [{}])[0].get('priceUsd', 0))
        volume = float(token_data.get('pairs', [{}])[0].get('volume', {}).get('h24', 0))
        liquidity = float(token_data.get('pairs', [{}])[0].get('liquidity', {}).get('usd', 0))
        change = float(token_data.get('pairs', [{}])[0].get('priceChange', {}).get('h24', 0))
        
        prompt = f"""
        Você é um especialista em trading de criptomoedas.
        
        ANALISE ESTE TOKEN PARA TRADING:
        
        TOKEN: {symbol}
        PREÇO: ${price}
        VOLUME 24H: ${volume:,.0f}
        LIQUIDEZ: ${liquidity:,.0f}
        VARIAÇÃO 24H: {change}%
        
        FORNECE UMA ANÁLISE CLARA:
        1. DECISÃO: COMPRAR, ESPERAR ou EVITAR
        2. CONFIANÇA: 0-100%
        3. RAZÃO: explicação breve
        4. STOP LOSS SUGERIDO: -5% a -15%
        5. TAKE PROFIT SUGERIDO: 15% a 35%
        
        FORMATO DA RESPOSTA:
        DECISÃO: [sua decisão]
        CONFIANÇA: [XX]%
        RAZÃO: [sua explicação]
        STOP LOSS: -[X]%
        TAKE PROFIT: +[X]%
        """
        
        response = st.session_state.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Você é um analista de criptomoedas."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Erro: {str(e)[:100]}"

# ========== INTERFACE PRINCIPAL ==========
st.header("🔍 ANALISAR TOKEN COM IA")

# Input para token
ca = st.text_input(
    "Cole o CA do token:",
    placeholder="0x...",
    key="token_ca",
    help="Exemplo: 0x2170Ed0880ac9A755fd29B2688956BD959F933F8"
)

if ca:
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🤖 ANALISAR COM IA", type="primary", use_container_width=True):
            with st.spinner("Buscando dados..."):
                token_data = buscar_token(ca)
                
                if token_data and token_data.get('pairs'):
                    pair = token_data['pairs'][0]
                    
                    # Mostrar dados
                    st.subheader("📊 DADOS DO TOKEN")
                    
                    col_a, col_b, col_c, col_d = st.columns(4)
                    
                    with col_a:
                        price = float(pair.get('priceUsd', 0))
                        st.metric("💰 Preço", f"${price:.10f}")
                    
                    with col_b:
                        volume = float(pair.get('volume', {}).get('h24', 0))
                        st.metric("📊 Volume", f"${volume:,.0f}")
                    
                    with col_c:
                        liquidity = float(pair.get('liquidity', {}).get('usd', 0))
                        st.metric("💧 Liquidez", f"${liquidity:,.0f}")
                    
                    with col_d:
                        change = float(pair.get('priceChange', {}).get('h24', 0))
                        st.metric("📈 Variação", f"{change:.1f}%")
                    
                    st.divider()
                    
                    # Análise com IA
                    if 'client' in st.session_state:
                        st.subheader("🧠 ANÁLISE DEEPSEEK AI")
                        
                        with st.spinner("Consultando IA..."):
                            analise = analisar_com_deepseek(token_data)
                            
                            # Mostrar análise
                            st.info(analise)
                            
                            # Extrair dados da análise
                            lines = analise.split('\n')
                            decisao = ""
                            confianca = 0
                            stop_loss = st.session_state.get('stop_loss', 10)
                            take_profit = st.session_state.get('take_profit', 25)
                            
                            for line in lines:
                                line = line.strip()
                                if 'DECISÃO:' in line:
                                    decisao = line.split(':')[1].strip()
                                elif 'CONFIANÇA:' in line:
                                    conf_str = line.split(':')[1].strip().replace('%', '')
                                    confianca = int(conf_str) if conf_str.isdigit() else 0
                                elif 'STOP LOSS:' in line:
                                    sl_str = line.split(':')[1].strip().replace('-', '').replace('%', '')
                                    stop_loss = int(sl_str) if sl_str.isdigit() else stop_loss
                                elif 'TAKE PROFIT:' in line:
                                    tp_str = line.split(':')[1].strip().replace('+', '').replace('%', '')
                                    take_profit = int(tp_str) if tp_str.isdigit() else take_profit
                            
                            # Mostrar parâmetros
                            st.subheader("⚙️ PARÂMETROS SUGERIDOS")
                            
                            sl_price = price * (1 - stop_loss/100)
                            tp_price = price * (1 + take_profit/100)
                            
                            col_x, col_y = st.columns(2)
                            
                            with col_x:
                                st.metric("⛔ Stop Loss", f"-{stop_loss}%", f"${sl_price:.10f}")
                            
                            with col_y:
                                st.metric("🎯 Take Profit", f"+{take_profit}%", f"${tp_price:.10f}")
                            
                            # Ação recomendada
                            st.divider()
                            if "COMPRAR" in decisao.upper() and confianca >= 70:
                                st.success(f"✅ FORTE SINAL DE COMPRA! ({confianca}% confiança)")
                                
                                col_p1, col_p2 = st.columns([2, 1])
                                with col_p1:
                                    posicao = st.slider("Tamanho da posição (%)", 1, 20, 5)
                                with col_p2:
                                    if st.button("🚀 ENTRAR NO TRADE", use_container_width=True):
                                        st.balloons()
                                        st.success(f"Trade iniciado com {posicao}% do capital!")
                            
                            elif "ESPERAR" in decisao.upper():
                                st.warning(f"⏸️ AGUARDAR ({confianca}% confiança)")
                            
                            else:
                                st.error(f"❌ EVITAR ({confianca}% confiança)")
                    else:
                        st.error("⚠️ Configure a DeepSeek na sidebar primeiro!")
                        
                else:
                    st.error("❌ Token não encontrado")

# ========== TOKENS PARA TESTE ==========
st.divider()
st.header("🎯 TESTE RÁPIDO")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("💰 ETH", use_container_width=True):
        st.session_state.token_ca = "0x2170Ed0880ac9A755fd29B2688956BD959F933F8"
        st.rerun()

with col2:
    if st.button("🔥 BNB", use_container_width=True):
        st.session_state.token_ca = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
        st.rerun()

with col3:
    if st.button("💎 USDC", use_container_width=True):
        st.session_state.token_ca = "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"
        st.rerun()

# ========== INSTRUÇÕES ==========
with st.expander("📖 COMO USAR", expanded=True):
    st.markdown("""
    ## 🚀 PASSO A PASSO:
    
    **1️⃣ OBTER CHAVE DEEPSEEK (GRATUITA):**
    - Acesse: https://platform.deepseek.com
    - Cadastre-se (gratuito)
    - Vá em "API Keys" → "Create New Key"
    - Copie a chave (começa com sk-)
    
    **2️⃣ CONFIGURAR NO APP:**
    - Cole a chave na sidebar
    - Aguarde aparecer "✅ DeepSeek conectado"
    
    **3️⃣ ANALISAR TOKENS:**
    - Cole qualquer CA de token
    - Clique em "ANALISAR COM IA"
    - Veja a recomendação completa
    
    **💡 DICA:** Comece testando com os tokens acima
    """)

# ========== CSS ==========
st.markdown("""
<style>
    /* Botões grandes para celular */
    .stButton > button {
        width: 100%;
        height: 50px;
        font-size: 18px;
        font-weight: bold;
        border-radius: 10px;
        margin: 5px 0;
    }
    
    /* Inputs maiores */
    .stTextInput input {
        height: 55px;
        font-size: 18px;
        border-radius: 10px;
    }
    
    /* Títulos coloridos */
    h1, h2, h3 {
        color: #1E3A8A;
        margin-top: 0.5rem;
    }
    
    /* Métricas destacadas */
    [data-testid="stMetricValue"] {
        font-size: 24px;
        font-weight: bold;
    }
    
    /* Cards com gradiente */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Melhor espaçamento */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Sidebar mais bonita */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
</style>
""", unsafe_allow_html=True)
