import streamlit as st
import pandas as pd
from lotofacil import (
    carregar_dados,
    calcular_frequencia,
    calcular_atrasos,
    calcular_pares_impares,
    calcular_sequencias,
    gerar_jogos,
)

st.set_page_config(page_title="Lotofácil Inteligente", page_icon="🎲", layout="wide")

st.title("🎲 Painel Lotofácil Inteligente")

# ---------------------------
# Carregar dados
# ---------------------------
df = carregar_dados("Lotofacil.csv")
if df is None:
    st.error("Erro ao carregar os concursos!")
    st.stop()
else:
    st.success(f"✅ Concursos carregados: {len(df)}")

# ---------------------------
# Parâmetro base
# ---------------------------
ultimos = st.sidebar.slider("Analisar últimos concursos:", 50, len(df), 100, step=10)

# ---------------------------
# Abas principais
# ---------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 Frequência", "⏳ Atrasos", "⚖️ Pares e Ímpares", "🔗 Sequências", "🃏 Geração de Jogos"]
)

# ---------------------------------------
# 📊 Aba 1 — Frequência
# ---------------------------------------
with tab1:
    st.subheader("📊 Dezenas mais frequentes")
    ranking = calcular_frequencia(df, ultimos)
    st.dataframe(ranking, use_container_width=True)

# ---------------------------------------
# ⏳ Aba 2 — Atrasos
# ---------------------------------------
with tab2:
    st.subheader("⏳ Dezenas atrasadas")
    atrasos = calcular_atrasos(df)
    st.dataframe(atrasos, use_container_width=True)

# ---------------------------------------
# ⚖️ Aba 3 — Pares e Ímpares
# ---------------------------------------
with tab3:
    st.subheader("⚖️ Distribuição de Pares e Ímpares")
    from lotofacil import calcular_pares_impares
    pares_impares = calcular_pares_impares(df, ultimos)
    st.dataframe(pares_impares, use_container_width=True)

# ---------------------------------------
# 🔗 Aba 4 — Sequências
# ---------------------------------------
with tab4:
    st.subheader("🔗 Sequências de dezenas consecutivas")
    from lotofacil import calcular_sequencias
    sequencias = calcular_sequencias(df, ultimos)
    st.dataframe(sequencias, use_container_width=True)

# ---------------------------------------
# 🃏 Aba 5 — Geração de Jogos Inteligente
# ---------------------------------------
with tab5:
    st.header("🃏 Geração de Jogos Inteligente")

    ranking = calcular_frequencia(df, ultimos=100)
    dezenas_base = ranking["Dezena"].tolist()

    # Fixas (usuário)
    jogo_fixo_input = st.text_input("👉 Digite dezenas fixas (máx 10)", "")
    dezenas_fixas = []
    if jogo_fixo_input:
        dezenas_fixas = [int(x.strip()) for x in jogo_fixo_input.split(",") if x.strip().isdigit()]

    # Atrasadas automáticas
    atrasos = calcular_atrasos(df)
    dezenas_atrasadas = atrasos.sort_values("Atraso Atual", ascending=False).head(3)["Dezena"].tolist()
    st.info(f"🔴 Usando dezenas atrasadas sugeridas: {dezenas_atrasadas}")

    # Quantidade de jogos
    qtd_15 = st.number_input("Jogos de 15 dezenas", min_value=0, max_value=10, value=2)

    if st.button("🎲 Gerar Jogos"):
        jogos = gerar_jogos(
            dezenas_base,
            qtd_15=qtd_15,
            dezenas_fixas=dezenas_fixas,
            atrasadas=dezenas_atrasadas,
        )

        for idx, (jogo, origem) in enumerate(jogos, start=1):
            st.markdown(f"### 🎯 Jogo {idx} ({len(jogo)} dezenas)")
            display = []
            for d in jogo:
                if origem[d] == "fixa_usuario":
                    display.append(f"<span style='color:black; font-weight:bold;'>⚫ {d}</span>")
                elif origem[d] == "fixa_auto":
                    display.append(f"<span style='color:blue;'>🔵 {d}</span>")
                elif origem[d] == "atrasada":
                    display.append(f"<span style='color:red;'>🔴 {d}</span>")
                else:
                    display.append(f"<span style='color:gray;'>⚪ {d}</span>")
            st.markdown(" ".join(display), unsafe_allow_html=True)

            st.write("📘 **Explicação da composição:**")
            st.markdown("""
            - **⚫ Preto:** Dezenas fixas escolhidas pelo usuário  
            - **🔵 Azul:** Dezenas fixas automáticas (mais frequentes)  
            - **🔴 Vermelho:** Dezenas atrasadas (em alta probabilidade)  
            - **⚪ Cinza:** Dezenas adicionadas para equilibrar pares/ímpares  
            """)
