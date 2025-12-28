import streamlit as st
import requests
import json
from datetime import datetime

# ========== CONFIGURAÇÃO ==========
st.set_page_config(
    page_title="Sniper AI Trader",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 SNIPER AI TRADER - GEMINI 1.5")

# ========== CONFIGURAÇÃO DA IA ==========
with st.sidebar:
    st.header("🔧 CONFIGURAÇÃO DA IA")
    
    # Instruções para obter a chave
    st.markdown("""
    **Como obter a chave:**
    1. Acesse: https://aistudio.google.com/app/apikey
    2. Faça login com Google
    3. Clique em **"Create API Key"**
    4. Escolha **"Create API key in new project"**
    5. Copie a chave (começa com AIzaSy...)
    """)
    
    gemini_api_key = st.text_input(
        "Cole sua chave Gemini API:",
        type="password",
        placeholder="AIzaSyD...",
        help="Cole a chave que você copiou do Google AI Studio"
    )
    
    if gemini_api_key:
        try:
            import google.generativeai as genai
            
            # CONFIGURAÇÃO CORRETA - versão mais recente
            genai.configure(api_key=gemini_api_key)
            
            # Modelo correto para a nova API
            model = genai.GenerativeModel('gemini-1.5-pro-latest')
            
            # Testar conexão
            response = model.generate_content("Responda apenas: OK")
            
            if response and response.text:
                st.session_state.gemini_api_key = gemini_api_key
                st.session_state.gemini_model = model
                st.success("✅ IA Conectada com sucesso!")
                st.balloons()
            else:
                st.error("❌ Erro na resposta da IA")
                
        except Exception as e:
            error_msg = str(e)
            st.error(f"❌ Erro: {error_msg[:100]}")
            
            # Dicas baseadas no erro
            if "404" in error_msg:
                st.info("""
                **Solução:** Use `gemini-1.5-pro-latest` ou `gemini-1.0-pro`
                """)
            elif "API key" in error_msg:
                st.info("**Solução:** Gere uma nova chave no Google AI Studio")
            elif "quota" in error_msg.lower():
                st.info("**Solução:** Espere 1 hora ou use outra conta Google")
    
    st.divider()
    
    # Mostrar status
    st.subheader("📊 STATUS")
    if 'gemini_model' in st.session_state:
        st.success("✅ IA PRONTA")
    else:
        st.warning("⚠️ IA NÃO CONFIGURADA")
    
    st.divider()
    
    # Configurações
    st.subheader("⚙️ CONFIGURAÇÕES")
    st.slider("Confiança mínima (%)", 50, 95, 70)
    st.slider("Stop Loss (%)", 5, 20, 10)
    st.slider("Take Profit (%)", 10, 50, 20)

# ========== FUNÇÕES ==========
def fetch_token_data(ca):
    """Busca dados do token"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def analyze_with_gemini(token_data, model):
    """Analisa token usando Gemini"""
    try:
        symbol = token_data.get('pairs', [{}])[0].get('baseToken', {}).get('symbol', 'TOKEN')
        price = float(token_data.get('pairs', [{}])[0].get('priceUsd', 0))
        volume = float(token_data.get('pairs', [{}])[0].get('volume', {}).get('h24', 0))
        liquidity = float(token_data.get('pairs', [{}])[0].get('liquidity', {}).get('usd', 0))
        
        prompt = f"""
        Você é um analista especializado em criptomoedas.
        
        ANALISE ESTE TOKEN:
        
        TOKEN: {symbol}
        PREÇO: ${price:,.10f}
        VOLUME 24H: ${volume:,.0f}
        LIQUIDEZ: ${liquidity:,.0f}
        
        FORNECE UMA RECOMENDAÇÃO DE TRADE:
        
        1. DECISÃO: [COMPRAR/ESPERAR/EVITAR]
        2. CONFIANÇA: [0-100]%
        3. RAZÃO: [breve explicação]
        4. STOP LOSS SUGERIDO: [-5 a -20]%
        5. TAKE PROFIT SUGERIDO: [10 a 50]%
        
        FORMATE A RESPOSTA ASSIM:
        DECISÃO: COMPRAR
        CONFIANÇA: 85%
        RAZÃO: Volume alto e liquidez boa
        STOP LOSS: -10%
        TAKE PROFIT: +25%
        """
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"Erro na IA: {str(e)[:100]}"

def parse_ia_response(response_text):
    """Converte resposta da IA em dicionário"""
    result = {
        'decisao': 'INDEFINIDO',
        'confianca': 50,
        'razao': 'Não analisado',
        'stop_loss': -10,
        'take_profit': 20
    }
    
    try:
        lines = response_text.split('\n')
        for line in lines:
            line = line.strip()
            if 'DECISÃO:' in line:
                result['decisao'] = line.split(':')[1].strip()
            elif 'CONFIANÇA:' in line:
                conf_str = line.split(':')[1].strip().replace('%', '')
                result['confianca'] = int(conf_str)
            elif 'RAZÃO:' in line:
                result['razao'] = line.split(':')[1].strip()
            elif 'STOP LOSS:' in line:
                sl_str = line.split(':')[1].strip().replace('%', '').replace('-', '')
                result['stop_loss'] = -int(sl_str)
            elif 'TAKE PROFIT:' in line:
                tp_str = line.split(':')[1].strip().replace('%', '').replace('+', '')
                result['take_profit'] = int(tp_str)
    except:
        pass
    
    return result

# ========== INTERFACE PRINCIPAL ==========
st.header("🔍 ANALISAR TOKEN COM IA")

# Input para CA do token
ca = st.text_input(
    "Cole o CA do token:",
    placeholder="0x...",
    key="token_input",
    help="Exemplo: 0x2170Ed0880ac9A755fd29B2688956BD959F933F8"
)

if ca:
    if st.button("🔎 ANALISAR COM IA", type="primary", use_container_width=True):
        with st.spinner("Buscando dados do token..."):
            token_data = fetch_token_data(ca)
            
            if token_data and 'pairs' in token_data and token_data['pairs']:
                pair = token_data['pairs'][0]
                
                # Mostrar dados básicos
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    price = float(pair.get('priceUsd', 0))
                    st.metric("💰 Preço", f"${price:.8f}")
                
                with col2:
                    volume = float(pair.get('volume', {}).get('h24', 0))
                    st.metric("📊 Volume 24h", f"${volume:,.0f}")
                
                with col3:
                    liquidity = float(pair.get('liquidity', {}).get('usd', 0))
                    st.metric("💧 Liquidez", f"${liquidity:,.0f}")
                
                st.divider()
                
                # Análise com IA
                if 'gemini_model' in st.session_state:
                    st.subheader("🧠 ANÁLISE COM GEMINI AI")
                    
                    with st.spinner("Consultando IA Gemini..."):
                        ia_response = analyze_with_gemini(token_data, st.session_state.gemini_model)
                        analysis = parse_ia_response(ia_response)
                        
                        # Mostrar resultado
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            st.markdown(f"### {analysis['decisao']}")
                            st.markdown(f"**Confiança:** {analysis['confianca']}%")
                            st.markdown(f"**Razão:** {analysis['razao']}")
                        
                        with col_b:
                            st.markdown("**⚙️ Parâmetros Sugeridos:**")
                            st.markdown(f"- Stop Loss: {analysis['stop_loss']}%")
                            st.markdown(f"- Take Profit: +{analysis['take_profit']}%")
                            
                            # Calcular preços
                            sl_price = price * (1 + analysis['stop_loss']/100)
                            tp_price = price * (1 + analysis['take_profit']/100)
                            
                            st.caption(f"Stop Loss: ${sl_price:.8f}")
                            st.caption(f"Take Profit: ${tp_price:.8f}")
                        
                        # Botão de ação
                        if analysis['decisao'] == 'COMPRAR' and analysis['confianca'] >= 70:
                            st.success("✅ FORTE SINAL DE COMPRA!")
                            
                            if st.button("🚀 ENTRAR NO TRADE", use_container_width=True):
                                st.balloons()
                                st.success(f"Trade iniciado para {pair.get('baseToken', {}).get('symbol', 'TOKEN')}!")
                        elif analysis['decisao'] == 'ESPERAR':
                            st.info("⏸️ AGUARDAR MELHOR OPORTUNIDADE")
                        else:
                            st.error("❌ EVITAR ESTE TOKEN")
                
                else:
                    st.error("⚠️ Configure a IA Gemini na sidebar primeiro!")
                    
                # Mostrar dados brutos
                with st.expander("📊 Ver dados completos"):
                    st.json(pair)
                    
            else:
                st.error("❌ Token não encontrado. Verifique o CA.")

# ========== EXEMPLOS PARA TESTE ==========
st.divider()
st.header("🎯 TOKENS PARA TESTE")

col_a, col_b, col_c = st.columns(3)

with col_a:
    if st.button("💰 ETH", use_container_width=True):
        st.session_state.token_input = "0x2170Ed0880ac9A755fd29B2688956BD959F933F8"
        st.rerun()

with col_b:
    if st.button("🔥 BNB", use_container_width=True):
        st.session_state.token_input = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
        st.rerun()

with col_c:
    if st.button("💎 USDC", use_container_width=True):
        st.session_state.token_input = "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"
        st.rerun()

# ========== TESTE DA IA ==========
st.divider()
st.header("🧪 TESTAR CONEXÃO DA IA")

if st.button("🔬 TESTAR IA GEMINI", use_container_width=True):
    if 'gemini_model' in st.session_state:
        with st.spinner("Testando conexão..."):
            try:
                response = st.session_state.gemini_model.generate_content(
                    "Responda em uma palavra: Funciona"
                )
                if response.text:
                    st.success(f"✅ IA Funcionando! Resposta: {response.text}")
                else:
                    st.error("❌ IA não retornou resposta")
            except Exception as e:
                st.error(f"❌ Erro no teste: {str(e)[:200]}")
    else:
        st.warning("⚠️ Configure a IA primeiro na sidebar")

# ========== INSTRUÇÕES ==========
with st.expander("📖 GUIA RÁPIDO", expanded=True):
    st.markdown("""
    ## 🚀 COMO USAR:
    
    **1️⃣ OBTER CHAVE GEMINI:**
    - Acesse: https://aistudio.google.com/app/apikey
    - Clique em **"Create API Key"**
    - Escolha **"Create API key in new project"**
    - Copie a chave (começa com AIzaSy...)
    
    **2️⃣ CONFIGURAR NO APP:**
    - Cole a chave na sidebar
    - Aguarde aparecer "✅ IA Conectada"
    
    **3️⃣ ANALISAR TOKENS:**
    - Cole qualquer CA de token
    - Clique em "ANALISAR COM IA"
    - Veja a recomendação completa
    
    **💡 DICAS:**
    - Comece testando com ETH, BNB ou USDC
    - Use confiança mínima de 70% para trades
    - Sempre configure Stop Loss
    """)

# ========== CSS ==========
st.markdown("""
<style>
    /* Estilo para celular */
    .stButton > button {
        width: 100%;
        height: 50px;
        font-size: 18px;
        font-weight: bold;
        border-radius: 10px;
        margin: 5px 0;
    }
    
    /* Inputs maiores */
    .stTextInput > div > div > input {
        height: 55px;
        font-size: 18px;
        border-radius: 10px;
    }
    
    /* Métricas */
    [data-testid="stMetricValue"] {
        font-size: 24px;
    }
    
    /* Títulos */
    h1, h2, h3 {
        margin-top: 1rem !important;
        color: #1E3A8A;
    }
    
    /* Container principal */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 100%;
    }
    
    /* Cards */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 15px;
        border: 2px solid #e0e0e0;
        padding: 20px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)
