import streamlit as st
import pandas as pd
from lotofacil import carregar_dados, selecionar_dezenas, gerar_jogos, avaliar_jogos

st.set_page_config(page_title="Lotofácil Inteligente", page_icon="🎲", layout="wide")

st.title("🎲 Gerador Lotofácil Inteligente")

# Carregar concursos
df = carregar_dados("Lotofacil.csv")
if df is None:
    st.error("Erro ao carregar os concursos!")
    st.stop()
else:
    st.success(f"✅ Concursos carregados: {len(df)}")

# Mostrar ranking
dezenas = selecionar_dezenas(df, qtd=18, ultimos=50)
st.subheader("📊 Top 18 dezenas mais frequentes nos últimos 50 concursos")
st.write(dezenas)

# Definir jogo fixo
jogo_fixo = st.text_input("👉 Digite dezenas fixas (ex: 1,2,3,4,5) ou deixe vazio para automático")
if jogo_fixo:
    jogo_fixo = [int(x.strip()) for x in jogo_fixo.split(",") if x.strip().isdigit()]
    jogos_fixos = [jogo_fixo]
else:
    jogos_fixos = []

# Escolher quantidade
qtd_15 = st.number_input("Quantos jogos de 15 dezenas?", min_value=0, max_value=20, value=2)
qtd_16 = st.number_input("Quantos jogos de 16 dezenas?", min_value=0, max_value=10, value=0)
qtd_17 = st.number_input("Quantos jogos de 17 dezenas?", min_value=0, max_value=5, value=0)
qtd_18 = st.number_input("Quantos jogos de 18 dezenas?", min_value=0, max_value=2, value=0)

if st.button("🎲 Gerar Jogos"):
    jogos = gerar_jogos(dezenas, qtd_15, qtd_16, qtd_17, qtd_18, jogos_fixos)
    st.success(f"✅ {len(jogos)} jogos gerados!")

    df_jogos = pd.DataFrame(jogos)
    st.dataframe(df_jogos)

    # Avaliação (contra histórico)
    resultados = avaliar_jogos(jogos, df)
    st.subheader("📊 Avaliação dos jogos contra concursos anteriores")
    for idx, jogo, contagens in resultados:
        st.write(f"**Jogo {idx}** {jogo} → {contagens}")

    # Download em CSV
    csv = df_jogos.to_csv(index=False)
    st.download_button("⬇️ Baixar jogos em CSV", csv, "jogos.csv", "text/csv")

