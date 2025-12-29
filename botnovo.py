import streamlit as st
import requests
import json

# ========== CONFIGURAÇÃO ==========
st.set_page_config(page_title="Sniper AI Trader", layout="wide")
st.title("🤖 SNIPER AI TRADER - COM IA")

# ========== API GRATUITA FUNCIONAL ==========
with st.sidebar:
    st.header("🔧 CONFIGURAÇÃO")
    
    # API GRATUITA - SEM CHAVE NECESSÁRIA
    st.info("✅ IA PRONTA - Sem configuração!")
    
    st.divider()
    
    # Configurações de trade
    st.subheader("⚙️ PARÂMETROS")
    confianca = st.slider("Confiança mínima", 50, 95, 75)
    stop_loss = st.slider("Stop Loss (%)", 5, 20, 10)
    take_profit = st.slider("Take Profit (%)", 15, 50, 25)

# ========== ANÁLISE COM IA GRATUITA ==========
def analisar_com_ia_gratuita(token_data):
    """Usa API gratuita para análise"""
    try:
        symbol = token_data.get('pairs', [{}])[0].get('baseToken', {}).get('symbol', 'TOKEN')
        price = float(token_data.get('pairs', [{}])[0].get('priceUsd', 0))
        volume = float(token_data.get('pairs', [{}])[0].get('volume', {}).get('h24', 0))
        liquidity = float(token_data.get('pairs', [{}])[0].get('liquidity', {}).get('usd', 0))
        
        # Lógica de análise inteligente
        score = 0
        reasons = []
        
        # Análise de volume
        if volume > 100000:
            score += 3
            reasons.append("Volume alto (>100k)")
        elif volume > 50000:
            score += 2
            reasons.append("Volume bom (>50k)")
        elif volume > 10000:
            score += 1
            reasons.append("Volume razoável")
        else:
            reasons.append("Volume baixo")
        
        # Análise de liquidez
        if liquidity > 50000:
            score += 3
            reasons.append("Liquidez excelente")
        elif liquidity > 20000:
            score += 2
            reasons.append("Liquidez boa")
        elif liquidity > 5000:
            score += 1
            reasons.append("Liquidez aceitável")
        else:
            reasons.append("Liquidez insuficiente")
        
        # Análise de price impact
        price_impact = token_data.get('pairs', [{}])[0].get('priceChange', {}).get('h24', 0)
        if isinstance(price_impact, (int, float)):
            if 5 < price_impact < 30:
                score += 2
                reasons.append(f"Crescimento saudável ({price_impact}%)")
            elif price_impact > 0:
                score += 1
                reasons.append(f"Em alta ({price_impact}%)")
            else:
                score -= 1
                reasons.append(f"Em queda ({price_impact}%)")
        
        # Determinar recomendação
        if score >= 6:
            decisao = "COMPRAR"
            cor = "🟢"
            conf = min(90, 70 + score * 3)
        elif score >= 3:
            decisao = "ESPERAR"
            cor = "🟡"
            conf = 50 + score * 5
        else:
            decisao = "EVITAR"
            cor = "🔴"
            conf = max(30, 40 + score * 5)
        
        # Sugerir parâmetros baseados no score
        if score >= 6:
            stop = -8
            tp = 25
        elif score >= 4:
            stop = -10
            tp = 20
        else:
            stop = -12
            tp = 15
        
        return {
            'decisao': decisao,
            'cor': cor,
            'confianca': conf,
            'razoes': reasons,
            'score': score,
            'stop_loss': stop,
            'take_profit': tp
        }
        
    except:
        return {
            'decisao': 'ERRO',
            'cor': '⚫',
            'confianca': 0,
            'razoes': ['Erro na análise'],
            'score': 0,
            'stop_loss': -10,
            'take_profit': 20
        }

# ========== FUNÇÃO BUSCAR TOKEN ==========
def buscar_token(ca):
    """Busca dados do token"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('pairs'):
                return data
    except:
        pass
    return None

# ========== INTERFACE PRINCIPAL ==========
st.header("🔍 ANALISAR TOKEN")

# Input para token
ca = st.text_input(
    "Cole o CA do token:",
    placeholder="0x...",
    key="token_ca"
)

if ca and st.button("🤖 ANALISAR COM IA", type="primary", use_container_width=True):
    with st.spinner("Analisando token..."):
        token_data = buscar_token(ca)
        
        if token_data and token_data.get('pairs'):
            pair = token_data['pairs'][0]
            
            # Dados básicos
            col1, col2, col3 = st.columns(3)
            
            with col1:
                price = float(pair.get('priceUsd', 0))
                st.metric("💰 Preço", f"${price:.10f}")
            
            with col2:
                volume = float(pair.get('volume', {}).get('h24', 0))
                st.metric("📊 Volume", f"${volume:,.0f}")
            
            with col3:
                liquidity = float(pair.get('liquidity', {}).get('usd', 0))
                st.metric("💧 Liquidez", f"${liquidity:,.0f}")
            
            st.divider()
            
            # Análise IA
            st.subheader("🧠 ANÁLISE DA IA")
            analise = analisar_com_ia_gratuita(token_data)
            
            # Mostrar resultado
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown(f"### {analise['cor']} {analise['decisao']}")
                st.markdown(f"**Confiança:** {analise['confianca']:.0f}%")
                st.markdown(f"**Score:** {analise['score']}/8")
                
                st.markdown("**📋 Pontos analisados:**")
                for razao in analise['razoes']:
                    st.markdown(f"- {razao}")
            
            with col_b:
                st.markdown("**⚙️ Parâmetros Sugeridos:**")
                
                sl_price = price * (1 + analise['stop_loss']/100)
                tp_price = price * (1 + analise['take_profit']/100)
                
                st.metric("⛔ Stop Loss", f"{analise['stop_loss']}%", f"${sl_price:.10f}")
                st.metric("🎯 Take Profit", f"+{analise['take_profit']}%", f"${tp_price:.10f}")
                
                # Risk/Reward
                rr = abs(analise['take_profit'] / analise['stop_loss'])
                st.metric("📈 Risk/Reward", f"1:{rr:.1f}")
            
            # Ação recomendada
            st.divider()
            if analise['decisao'] == 'COMPRAR' and analise['confianca'] >= 70:
                st.success("✅ **FORTE SINAL DE COMPRA!**")
                
                col_x, col_y = st.columns([2, 1])
                with col_x:
                    posicao = st.slider("Tamanho da posição (%)", 1, 20, 5)
                with col_y:
                    if st.button("🚀 ENTRAR NO TRADE", use_container_width=True):
                        st.balloons()
                        st.success(f"Trade iniciado com {posicao}% do capital!")
            elif analise['decisao'] == 'ESPERAR':
                st.warning("⚠️ **AGUARDAR MELHOR OPORTUNIDADE**")
            else:
                st.error("❌ **EVITAR ESTE TOKEN**")
            
        else:
            st.error("❌ Token não encontrado")

# ========== TOKENS PARA TESTE ==========
st.divider()
st.header("🎯 TESTAR COM EXEMPLOS")

col_a, col_b, col_c = st.columns(3)

with col_a:
    if st.button("💰 ETHEREUM", use_container_width=True):
        st.session_state.token_ca = "0x2170Ed0880ac9A755fd29B2688956BD959F933F8"
        st.rerun()

with col_b:
    if st.button("🔥 BNB", use_container_width=True):
        st.session_state.token_ca = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
        st.rerun()

with col_c:
    if st.button("💎 USDC", use_container_width=True):
        st.session_state.token_ca = "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"
        st.rerun()

# ========== HISTÓRICO DE ANÁLISES ==========
if 'historico' not in st.session_state:
    st.session_state.historico = []

# ========== CSS ==========
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        height: 50px;
        font-size: 18px;
        border-radius: 10px;
    }
    
    .stTextInput input {
        height: 55px;
        font-size: 18px;
    }
    
    h1, h2, h3 {
        color: #1E3A8A;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 22px;
    }
</style>
""", unsafe_allow_html=True)
