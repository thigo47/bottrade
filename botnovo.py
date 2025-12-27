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

st.title("🤖 SNIPER AI TRADER")

# ========== CONFIGURAÇÃO DA IA ==========
with st.sidebar:
    st.header("🔧 CONFIGURAÇÃO DA IA")
    
    # Opção 1: Usar Google AI Studio (simples)
    st.markdown("**Método 1: Google AI Studio**")
    gemini_api_key = st.text_input(
        "Cole sua chave Gemini API:",
        type="password",
        placeholder="AIzaSyD...",
        help="Obtenha em: https://aistudio.google.com/app/apikey"
    )
    
    if gemini_api_key:
        try:
            # Testar a chave
            import google.generativeai as genai
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel('gemini-pro')
            test_response = model.generate_content("Teste de conexão")
            
            if test_response:
                st.session_state.gemini_api_key = gemini_api_key
                st.session_state.gemini_model = model
                st.success("✅ IA Conectada com sucesso!")
        except Exception as e:
            st.error(f"❌ Erro: {str(e)[:100]}...")
            st.info("Tente gerar uma nova chave em: https://aistudio.google.com/app/apikey")
    
    st.divider()
    
    # Opção 2: Usar API externa (fallback)
    st.markdown("**Método 2: API Externa (backup)**")
    use_backup = st.checkbox("Usar sistema de backup", value=True)
    
    if use_backup:
        st.info("Usando sistema de análise automática")

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
        price = token_data.get('pairs', [{}])[0].get('priceUsd', 0)
        volume = token_data.get('pairs', [{}])[0].get('volume', {}).get('h24', 0)
        
        prompt = f"""
        Analise este token para trading rápido:
        
        Token: {symbol}
        Preço: ${price}
        Volume 24h: ${volume}
        
        Responda em 1 linha: COMPRAR, ESPERAR ou EVITAR
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "IA indisponível"

def auto_analyze(token_data):
    """Análise automática sem IA"""
    try:
        price = float(token_data.get('pairs', [{}])[0].get('priceUsd', 0))
        volume = float(token_data.get('pairs', [{}])[0].get('volume', {}).get('h24', 0))
        liquidity = float(token_data.get('pairs', [{}])[0].get('liquidity', {}).get('usd', 0))
        
        score = 0
        
        if volume > 50000:
            score += 2
        elif volume > 20000:
            score += 1
            
        if liquidity > 20000:
            score += 2
        elif liquidity > 5000:
            score += 1
            
        if score >= 3:
            return "COMPRAR", score
        elif score >= 2:
            return "ESPERAR", score
        else:
            return "EVITAR", score
            
    except:
        return "ERRO", 0

# ========== INTERFACE PRINCIPAL ==========
st.header("🔍 ANALISAR TOKEN")

# Input para CA do token
ca = st.text_input(
    "Cole o CA do token:",
    placeholder="0x...",
    help="Exemplo: 0x2170Ed0880ac9A755fd29B2688956BD959F933F8 (ETH)"
)

if ca and st.button("🔎 ANALISAR"):
    with st.spinner("Buscando dados..."):
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
                st.subheader("🧠 Análise com IA Gemini")
                
                with st.spinner("Consultando IA..."):
                    ia_result = analyze_with_gemini(token_data, st.session_state.gemini_model)
                    
                    if "COMPRAR" in ia_result.upper():
                        st.success(f"✅ {ia_result}")
                        st.balloons()
                    elif "ESPERAR" in ia_result.upper():
                        st.info(f"⏸️ {ia_result}")
                    else:
                        st.error(f"❌ {ia_result}")
            else:
                st.subheader("⚡ Análise Automática")
                
                result, score = auto_analyze(token_data)
                
                if result == "COMPRAR":
                    st.success(f"✅ {result} (Score: {score}/4)")
                    
                    # Sugerir parâmetros
                    st.info("""
                    **Sugestão de Trade:**
                    - Stop Loss: -10%
                    - Take Profit: +20%
                    - Posição: 5-10% do capital
                    """)
                elif result == "ESPERAR":
                    st.warning(f"⚠️ {result} (Score: {score}/4)")
                else:
                    st.error(f"❌ {result} (Score: {score}/4)")
            
            # Mostrar mais informações
            with st.expander("📊 Ver detalhes completos"):
                st.json(pair)
                
        else:
            st.error("❌ Token não encontrado ou CA inválido")

# ========== EXEMPLOS PARA TESTE ==========
st.divider()
st.header("🎯 EXEMPLOS PARA TESTAR")

col_a, col_b, col_c = st.columns(3)

with col_a:
    if st.button("Testar com ETH", use_container_width=True):
        st.session_state.test_ca = "0x2170Ed0880ac9A755fd29B2688956BD959F933F8"
        st.rerun()

with col_b:
    if st.button("Testar com BNB", use_container_width=True):
        st.session_state.test_ca = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
        st.rerun()

with col_c:
    if st.button("Testar com USDC", use_container_width=True):
        st.session_state.test_ca = "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"
        st.rerun()

if 'test_ca' in st.session_state:
    ca = st.session_state.test_ca
    # Remove após usar
    del st.session_state.test_ca

# ========== INSTRUÇÕES ==========
with st.expander("📖 COMO USAR"):
    st.markdown("""
    **1️⃣ Obtenha uma chave da API Gemini:**
    - Acesse: https://aistudio.google.com/app/apikey
    - Faça login com Google
    - Clique em "Create API Key"
    - Copie a chave (começa com AIzaSy...)
    
    **2️⃣ Configure no app:**
    - Cole a chave na sidebar
    - O sistema testará automaticamente
    
    **3️⃣ Analise tokens:**
    - Cole o CA de qualquer token
    - Clique em ANALISAR
    - Veja a recomendação da IA
    
    **Dica:** Comece testando com os exemplos acima!
    """)

# ========== CSS ==========
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        height: 50px;
        font-size: 16px;
        font-weight: bold;
    }
    
    input {
        font-size: 18px !important;
        height: 50px !important;
    }
    
    h1, h2, h3 {
        color: #1E3A8A;
    }
</style>
""", unsafe_allow_html=True)