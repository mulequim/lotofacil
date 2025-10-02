import streamlit as st
import pandas as pd
from lotofacil import (
    carregar_dados, calcular_frequencia, calcular_atrasos,
    calcular_pares_impares, calcular_sequencias,
    gerar_jogos, avaliar_jogos
)

st.set_page_config(page_title="Lotofácil Inteligente", page_icon="🎲", layout="wide")

st.title("🎲 Lotofácil Inteligente - Painel Estatístico")

# Carregar concursos
df = carregar_dados("Lotofacil.csv")
if df is None:
    st.error("❌ Erro ao carregar os concursos!")
    st.stop()
else:
    st.success(f"✅ Concursos carregados: {len(df)}")

ultimos = st.slider("📅 Concursos considerados", min_value=50, max_value=len(df), value=100, step=10)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 Frequência", "⏳ Atrasadas", "⚖️ Pares/Ímpares", "🔗 Sequências", "🎲 Geração de Jogos"]
)

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

# ---------------------------
# Nova aba: Geração de Jogos
# ---------------------------
with tab5:
    st.subheader("🎲 Geração de Jogos")

    dezenas_base = calcular_frequencia(df, ultimos)["Dezena"].tolist()

    st.markdown("👉 Digite suas **dezenas fixas** (máx. 11):")
    dezenas_fixas_input = st.text_input("Exemplo: 1, 3, 5, 10")
    dezenas_fixas = []
    if dezenas_fixas_input:
        dezenas_fixas = [int(x.strip()) for x in dezenas_fixas_input.split(",") if x.strip().isdigit()]

    if len(dezenas_fixas) > 11:
        st.error("❌ Máximo permitido: 11 dezenas fixas.")

    col1, col2, col3, col4 = st.columns(4)
    qtd_15 = col1.number_input("Jogos de 15", min_value=0, max_value=20, value=2)
    qtd_16 = col2.number_input("Jogos de 16", min_value=0, max_value=10, value=0)
    qtd_17 = col3.number_input("Jogos de 17", min_value=0, max_value=5, value=0)
    qtd_18 = col4.number_input("Jogos de 18", min_value=0, max_value=2, value=0)

    if st.button("🚀 Gerar Jogos", key="gerar"):
        if qtd_15 + qtd_16 + qtd_17 + qtd_18 == 0:
            st.warning("Selecione pelo menos 1 jogo para gerar.")
        else:
            jogos = gerar_jogos(dezenas_base, qtd_15, qtd_16, qtd_17, qtd_18, dezenas_fixas)
            st.success(f"✅ {len(jogos)} jogos gerados!")

            df_jogos = pd.DataFrame(jogos)
            st.dataframe(df_jogos)

            # Avaliação
            resultados = avaliar_jogos(jogos, df)
            st.subheader("📊 Avaliação Histórica")
            for idx, jogo, contagens in resultados:
                st.write(f"**Jogo {idx}** {jogo} → {contagens}")

            # Download CSV
            csv = df_jogos.to_csv(index=False)
            st.download_button("⬇️ Baixar jogos em CSV", csv, "jogos.csv", "text/csv")
