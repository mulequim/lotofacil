import streamlit as st
import pandas as pd
from lotofacil import (
    carregar_dados,
    calcular_frequencia,
    calcular_atrasos,
    gerar_jogos,
    avaliar_jogos,
)

st.set_page_config(page_title="Lotofácil Inteligente", page_icon="🎲", layout="wide")

st.title("🎲 Gerador Lotofácil Inteligente")

# Carregar dados
df = carregar_dados("Lotofacil.csv")
if df is None:
    st.error("Erro ao carregar os concursos!")
    st.stop()
else:
    st.success(f"✅ Concursos carregados: {len(df)}")

# ---------------------------
# Aba de geração
# ---------------------------
st.header("🃏 Geração de Jogos")

# Ranking frequência
ranking = calcular_frequencia(df, ultimos=100)
dezenas_base = ranking["Dezena"].tolist()

# Input fixas
jogo_fixo_input = st.text_input("👉 Digite dezenas fixas (máx 11)", "")
dezenas_fixas = []
if jogo_fixo_input:
    dezenas_fixas = [int(x.strip()) for x in jogo_fixo_input.split(",") if x.strip().isdigit()]

# Escolher atrasadas
atrasos = calcular_atrasos(df)
dezenas_atrasadas = atrasos.sort_values("Atraso Atual", ascending=False).head(3)["Dezena"].tolist()

st.info(f"🔴 Usando dezenas atrasadas sugeridas: {dezenas_atrasadas}")

# Quantidade
qtd_15 = st.number_input("Jogos de 15 dezenas", min_value=0, max_value=10, value=2)

if st.button("🎲 Gerar Jogos"):
    jogos = gerar_jogos(dezenas_base, qtd_15=qtd_15, dezenas_fixas=dezenas_fixas, atrasadas=dezenas_atrasadas)

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
