import streamlit as st
import pandas as pd
from lotofacil import carregar_dados, calcular_frequencia, calcular_atrasos, calcular_pares_impares, calcular_sequencias

st.set_page_config(page_title="Lotofácil Inteligente", page_icon="🎲", layout="wide")

st.title("🎲 Lotofácil Inteligente - Painel Estatístico")

# Carregar concursos
df = carregar_dados("Lotofacil.csv")
if df is None:
    st.error("❌ Erro ao carregar os concursos!")
    st.stop()
else:
    st.success(f"✅ Concursos carregados: {len(df)}")

# Quantos concursos usar na análise
ultimos = st.slider("📅 Concursos considerados", min_value=50, max_value=len(df), value=100, step=10)

# Criar abas
tab1, tab2, tab3, tab4 = st.tabs(["📊 Frequência", "⏳ Atrasadas", "⚖️ Pares/Ímpares", "🔗 Sequências"])

with tab1:
    st.subheader("📊 Dezenas mais frequentes")
    ranking = calcular_frequencia(df, ultimos)
    st.dataframe(ranking, use_container_width=True)

with tab2:
    st.subheader("⏳ Dezenas atrasadas")
    atrasos = calcular_atrasos(df)
    st.dataframe(atrasos, use_container_width=True)

with tab3:
    st.subheader("⚖️ Pares e Ímpares")
    pares_impares = calcular_pares_impares(df, ultimos)
    st.dataframe(pares_impares, use_container_width=True)

with tab4:
    st.subheader("🔗 Sequências")
    sequencias = calcular_sequencias(df, ultimos)
    st.dataframe(sequencias, use_container_width=True)
