import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime
import plotly.graph_objects as go
import openai  # Versão 0.28.1

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
    st.subheader("🧠 CONFIGURAR DEEPSEEK")
    
    api_key = st.text_input(
        "Chave API DeepSeek:",
        type="password",
        placeholder="sk-...",
        help="Obtenha em: https://platform.deepseek.com/api_keys"
    )
    
    if api_key:
        try:
            # Configurar para DeepSeek (versão 0.28.1)
            openai.api_key = api_key
            openai.api_base = "https://api.deepseek.com/v1"
            
            # Testar conexão
            response = openai.ChatCompletion.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "Teste"}],
                max_tokens=10
            )
            
            st.success("✅ DeepSeek conectado com sucesso!")
            st.session_state.ia_configurada = True
            st.balloons()
            
        except Exception as e:
            st.error(f"❌ Erro: {str(e)[:100]}")
            st.info("""
            **Soluções:**
            1. Verifique se a chave está correta
            2. Gere uma nova chave em: https://platform.deepseek.com
            3. A DeepSeek é gratuita!
            """)
    
    st.divider()
    
    # Status
    st.subheader("📊 STATUS")
    if st.session_state.get('ia_configurada'):
        st.success("✅ IA PRONTA")
    else:
        st.warning("⚠️ Configure a IA acima")
    
    st.divider()
    
    # Configurações
    st.subheader("⚙️ PARÂMETROS")
    st.slider("Confiança mínima", 60, 95, 75, key="conf_min")
    st.slider("Stop Loss (%)", 5, 20, 10, key="sl_pct")
    st.slider("Take Profit (%)", 15, 50, 25, key="tp_pct")

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

def analisar_com_ia(token_data):
    """Analisa token usando DeepSeek"""
    try:
        symbol = token_data.get('pairs', [{}])[0].get('baseToken', {}).get('symbol', 'TOKEN')
        price = float(token_data.get('pairs', [{}])[0].get('priceUsd', 0))
        volume = float(token_data.get('pairs', [{}])[0].get('volume', {}).get('h24', 0))
        liquidity = float(token_data.get('pairs', [{}])[0].get('liquidity', {}).get('usd', 0))
        change = float(token_data.get('pairs', [{}])[0].get('priceChange', {}).get('h24', 0))
        
        prompt = f"""
        Analise este token de criptomoeda para trading:

        TOKEN: {symbol}
        PREÇO: ${price}
        VOLUME 24H: ${volume:,.0f}
        LIQUIDEZ: ${liquidity:,.0f}
        VARIAÇÃO 24H: {change}%

        Forneça uma recomendação clara em português:
        - Devo COMPRAR, ESPERAR ou EVITAR?
        - Qual o nível de confiança (0-100%)?
        - Breve explicação (1-2 linhas)
        """
        
        response = openai.ChatCompletion.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Você é um especialista em trading de criptomoedas."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Erro na análise: {str(e)[:100]}"

# ========== INTERFACE PRINCIPAL ==========
st.header("🔍 ANALISAR TOKEN")

# Input para token
ca = st.text_input(
    "Cole o CA do token:",
    placeholder="0x...",
    key="token_ca",
    help="Exemplo: 0x2170Ed0880ac9A755fd29B2688956BD959F933F8 (ETH)"
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
                    
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        price = float(pair.get('priceUsd', 0))
                        st.metric("💰 Preço", f"${price:.10f}")
                    
                    with col_b:
                        volume = float(pair.get('volume', {}).get('h24', 0))
                        st.metric("📊 Volume", f"${volume:,.0f}")
                    
                    with col_c:
                        liquidity = float(pair.get('liquidity', {}).get('usd', 0))
                        st.metric("💧 Liquidez", f"${liquidity:,.0f}")
                    
                    st.divider()
                    
                    # Análise com IA
                    if st.session_state.get('ia_configurada'):
                        st.subheader("🧠 ANÁLISE DEEPSEEK AI")
                        
                        with st.spinner("Consultando IA..."):
                            analise = analisar_com_ia(token_data)
                            
                            # Mostrar análise
                            st.info(f"**{analise}**")
                            
                            # Sugerir ação
                            if "COMPRAR" in analise.upper() and "CONFIANÇA" in analise.upper():
                                st.success("✅ FORTE SINAL DE COMPRA!")
                                
                                # Calcular parâmetros
                                sl_price = price * (1 - st.session_state.get('sl_pct', 10)/100)
                                tp_price = price * (1 + st.session_state.get('tp_pct', 25)/100)
                                
                                col_x, col_y = st.columns(2)
                                
                                with col_x:
                                    st.metric("⛔ Stop Loss", 
                                             f"{st.session_state.get('sl_pct', 10)}%",
                                             f"${sl_price:.10f}")
                                
                                with col_y:
                                    st.metric("🎯 Take Profit",
                                             f"+{st.session_state.get('tp_pct', 25)}%",
                                             f"${tp_price:.10f}")
                                
                                # Botão de ação
                                if st.button("🚀 ENTRAR NO TRADE", use_container_width=True):
                                    st.balloons()
                                    st.success(f"Trade iniciado para {pair.get('baseToken', {}).get('symbol', 'TOKEN')}!")
                            
                            elif "ESPERAR" in analise.upper():
                                st.warning("⏸️ AGUARDAR MELHOR OPORTUNIDADE")
                            else:
                                st.error("❌ EVITAR ESTE TOKEN")
                    else:
                        st.error("⚠️ Configure a IA DeepSeek na sidebar primeiro!")
                        
                    # Mostrar dados completos
                    with st.expander("📋 Ver dados completos"):
                        st.json(pair)
                        
                else:
                    st.error("❌ Token não encontrado")

# ========== TOKENS PARA TESTE ==========
st.divider()
st.header("🎯 TESTAR RÁPIDO")

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
    
    **1️⃣ OBTER CHAVE DEEPSEEK:**
    - Acesse: https://platform.deepseek.com
    - Cadastre-se (gratuito)
    - Vá em "API Keys"
    - Clique em "Create New Key"
    - Copie a chave (começa com sk-)
    
    **2️⃣ CONFIGURAR NO APP:**
    - Cole a chave na sidebar
    - Aguarde aparecer "✅ DeepSeek conectado"
    
    **3️⃣ ANALISAR TOKENS:**
    - Cole qualquer CA de token
    - Clique em "ANALISAR COM IA"
    - Veja a recomendação completa
    
    **💡 DICA:** Comece testando com ETH, BNB ou USDC
    """)

# ========== CSS ==========
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        height: 50px;
        font-size: 18px;
        border-radius: 10px;
        margin: 5px 0;
    }
    
    .stTextInput input {
        height: 55px;
        font-size: 18px;
        border-radius: 10px;
    }
    
    h1, h2, h3 {
        color: #1E3A8A;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 22px;
    }
    
    /* Cards */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
</style>
""", unsafe_allow_html=True)
