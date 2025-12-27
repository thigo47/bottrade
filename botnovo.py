import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import google.generativeai as genai # pip install google-generativeai
from datetime import datetime
import plotly.graph_objects as go
from typing import Dict, List, Tuple, Optional

# ==========================================================
# CONFIGURAÇÃO DO CÉREBRO GEMINI
# ==========================================================
def gemini_trading_analyst(token_info: Dict, context: str = "entrada"):
    """
    IA Gemini analisa os dados brutos e decide a ação.
    context: 'entrada' para novos trades, 'monitoramento' para trades ativos.
    """
    try:
        # Puxa a chave da sessão para segurança
        api_key = st.session_state.get('gemini_api_key', '')
        if not api_key: return None
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Você é um Trader Especialista em Memecoins na rede Solana. 
        Analise os dados abaixo para uma decisão de {context}.
        
        DADOS DO TOKEN:
        {token_info}
        
        REGRAS:
        1. Se context='entrada', decida se é um 'BUY' seguro.
        2. Se context='monitoramento', decida se devemos 'HOLD' ou 'SELL' imediatamente.
        3. Considere liquidez baixa como risco alto.
        
        Responda ESTRITAMENTE em formato JSON:
        {{"decisao": "BUY/SELL/HOLD/WAIT", "confianca": 0-100, "analise": "breve justificativa"}}
        """
        
        response = model.generate_content(prompt)
        # Limpeza para garantir que o JSON seja lido corretamente
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        return {"decisao": "WAIT", "confianca": 0, "analise": f"Erro IA: {str(e)}"}

# ==========================================================
# SEU CÓDIGO ESTÁVEL COM ADIÇÕES DA IA
# ==========================================================

# ... (Manter as classes AutoTradeMonitor e AutoDecisionEngine do seu arquivo original)

# UPGRADE NA LOGICA DE DECISÃO PARA USAR O GEMINI
def smart_ai_analysis(token_data: Dict):
    pair = token_data.get('pairs', [{}])[0]
    
    # Prepara o 'dossiê' para o Gemini
    dossie = {
        "ticker": token_data.get('symbol'),
        "price": pair.get('priceUsd'),
        "liq": pair.get('liquidity', {}).get('usd'),
        "vol_24h": pair.get('volume', {}).get('h24'),
        "buys": pair.get('txns', {}).get('h1', {}).get('buys'),
        "sells": pair.get('txns', {}).get('h1', {}).get('sells'),
        "mkt_cap": pair.get('fdv')
    }
    
    return gemini_trading_analyst(dossie, context="entrada")

# ==========================================================
# INTERFACE COM PAINEL GEMINI
# ==========================================================
st.title("🤖 SNIPER PRO AI + GEMINI")

with st.sidebar:
    st.header("🔑 CHAVE DA INTELIGÊNCIA")
    api_key_input = st.text_input("Google Gemini API Key:", type="password", help="Pegue sua chave no Google AI Studio")
    if api_key_input:
        st.session_state.gemini_api_key = api_key_input
        st.success("IA Pronta para Analisar")
    
    st.divider()
    # Controles de Saldo (Mantendo seu sistema original)
    st.metric("💰 SALDO", f"${st.session_state.get('balance', 1000.0):,.2f}")

# ... (Seção de Monitorar Tokens - Mantendo sua Watchlist)

# NOVO: ÁREA DE ANÁLISE EM TEMPO REAL COM O CHAT IA
if 'selected_token_ca' in st.session_state:
    st.header("🧠 ANÁLISE PREDITIVA GEMINI")
    
    with st.status("Gemini processando padrões de ordens...", expanded=True) as status:
        t_data = fetch_token_data(st.session_state.selected_token_ca)
        if t_data and api_key_input:
            resultado_ia = smart_ai_analysis(t_data)
            
            col_ia1, col_ia2 = st.columns([1, 2])
            with col_ia1:
                st.metric("AÇÃO SUGERIDA", resultado_ia['decisao'])
                st.write(f"Confiança: **{resultado_ia['confianca']}%**")
            
            with col_ia2:
                st.info(f"**Análise da IA:** {resultado_ia['analise']}")
            
            status.update(label="Análise Concluída!", state="complete")
            
            # Botão de Execução Baseado na IA
            if resultado_ia['decisao'] == "BUY" and resultado_ia['confianca'] > 75:
                if st.button("🚀 EXECUTAR COMPRA VIA IA", use_container_width=True):
                    # Chama o seu método de criar trade original
                    st.success("Ordem enviada com base na análise do Gemini!")

# ... (Restante do seu código de Trades Ativos e Gráficos permanece IGUAL)
