import streamlit as st
import requests
import google.generativeai as genai

# ========== CONFIGURAÇÃO ==========
st.set_page_config(page_title="Sniper AI", layout="wide")

st.title("🤖 SNIPER AI - COM GEMINI")

# ========== CONFIGURAR IA ==========
with st.sidebar:
    st.header("🔧 CONFIGURAR IA")
    
    # 1. Cole sua chave do Gemini aqui:
    api_key = st.text_input(
        "Cole sua chave Gemini API:",
        type="password",
        placeholder="AIzaSyD...",
        help="Obtenha em: https://aistudio.google.com/app/apikey"
    )
    
    if st.button("✅ CONECTAR IA") and api_key:
        try:
            genai.configure(api_key=api_key)
            st.session_state.ia_model = genai.GenerativeModel('gemini-pro')
            st.success("IA conectada com sucesso!")
        except:
            st.error("Chave inválida")

# ========== BUSCAR TOKEN ==========
st.header("🔍 ANALISAR TOKEN")

ca = st.text_input("Cole o CA do token:", placeholder="0x...")

if ca and st.button("🔎 ANALISAR COM IA"):
    # Buscar dados do token
    url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if 'pairs' in data and data['pairs']:
            pair = data['pairs'][0]
            
            # Mostrar dados básicos
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Preço", f"${float(pair.get('priceUsd', 0)):.10f}")
            with col2:
                st.metric("Volume 24h", f"${float(pair.get('volume', {}).get('h24', 0)):,.0f}")
            
            # Analisar com IA
            if 'ia_model' in st.session_state:
                with st.spinner("🧠 Analisando com IA..."):
                    # Criar prompt
                    prompt = f"""
                    Analise este token de criptomoeda para trading:
                    
                    Nome: {pair.get('baseToken', {}).get('name', '')}
                    Símbolo: {pair.get('baseToken', {}).get('symbol', '')}
                    Preço: ${pair.get('priceUsd', 0)}
                    Volume 24h: ${pair.get('volume', {}).get('h24', 0)}
                    Variação 24h: {pair.get('priceChange', {}).get('h24', 0)}%
                    
                    Dê sua análise em 3 partes:
                    1. Recomendação: COMPRAR, ESPERAR ou EVITAR
                    2. Razão (máximo 2 linhas)
                    3. Risco: BAIXO, MÉDIO ou ALTO
                    """
                    
                    # Chamar IA
                    response = st.session_state.ia_model.generate_content(prompt)
                    
                    # Mostrar resultado
                    st.success("**ANÁLISE DA IA:**")
                    st.write(response.text)
                    
                    # Sugerir ação
                    if "COMPRAR" in response.text.upper():
                        st.balloons()
                        st.info("""
                        **SUGESTÃO DE TRADE:**
                        - Stop Loss: -10%
                        - Take Profit: +20%
                        - Posição: 5-10% do capital
                        """)
            else:
                st.warning("Configure a IA primeiro na sidebar!")
                
        else:
            st.error("Token não encontrado")
            
    except Exception as e:
        st.error(f"Erro: {e}")

# ========== CSS ==========
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        padding: 12px;
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)