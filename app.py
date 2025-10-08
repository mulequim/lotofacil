import streamlit as st
import pandas as pd
from lotofacil import (
    carregar_dados,
    calcular_frequencia,
    calcular_atrasos,
    gerar_jogos,
    avaliar_jogos,
    obter_concurso_atual_api,
)

st.set_page_config(page_title="Analisador Lotofácil", layout="wide")

st.title("🎯 Sistema de Análise e Geração de Jogos - Lotofácil")

df = carregar_dados("Lotofacil.csv")

aba = st.sidebar.radio("Menu", ["Análises", "Gerar Jogos"])

# ---------------------------
# ABA 1 - ANÁLISES
# ---------------------------
if aba == "Análises":
    st.header("📊 Análises Estatísticas")
    ultimos = st.slider("Quantidade de concursos recentes", 50, len(df), 300)

    freq = calcular_frequencia(df, ultimos)
    atrasos = calcular_atrasos(df)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔢 Frequência das dezenas")
        st.dataframe(freq)
    with col2:
        st.subheader("⏱️ Atrasos atuais")
        st.dataframe(atrasos)

# ---------------------------
# ABA 2 - GERAR JOGOS
# ---------------------------
if aba == "Gerar Jogos":
    st.header("🎲 Gerador de Jogos Inteligente")

    dezenas_base = st.multiselect("Escolha as dezenas base (1–25)", list(range(1, 26)))
    qtd_jogos = st.number_input("Quantos jogos deseja gerar?", min_value=1, max_value=20, value=4)
    tamanho_jogo = st.slider("Tamanho do jogo", 15, 20, 15)

    if st.button("Gerar Jogos"):
        jogos = gerar_jogos(dezenas_base or list(range(1, 26)), qtd_jogos, tamanho_jogo)
        resultados = avaliar_jogos(jogos, df)

        for idx, jogo, contagem in resultados:
            st.markdown(f"**🎯 Jogo {idx} ({len(jogo)} dezenas)**")
            st.write(jogo)
            st.text(
                f"11 acertos: {contagem[11]} | "
                f"12 acertos: {contagem[12]} | "
                f"13 acertos: {contagem[13]} | "
                f"14 acertos: {contagem[14]} | "
                f"15 acertos: {contagem[15]}"
            )
            st.markdown("---")

st.markdown("🟢 Sistema desenvolvido para análise estatística e geração de jogos balanceados.")
