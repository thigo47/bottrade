import streamlit as st
import google.generativeai as genai

st.title("Teste Gemini")

api_key = st.text_input("Cole sua chave:")

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Olá")
        st.success(f"Funciona! Resposta: {response.text}")
    except Exception as e:
        st.error(f"Erro: {e}")
