import streamlit as st
import pandas as pd
import requests
import json
import os
import uuid
from datetime import datetime
from lotofacil import (
    carregar_dados,
    calcular_frequencia,
    calcular_atrasos,
    calcular_pares_impares,
    calcular_sequencias,
    analisar_combinacoes_repetidas,
    gerar_jogos_balanceados,
    calcular_valor_aposta,
    gerar_pdf_jogos,
    obter_concurso_atual_api,
    atualizar_csv_github,
    salvar_bolao_csv,
    calcular_soma_total,
    avaliar_jogos_historico  # 🔹 nova função adicionada
)

# ---------------------------
# Configuração geral
# ---------------------------
st.set_page_config(page_title="Lotofácil Inteligente", page_icon="🎲", layout="wide")
st.title("🎲 Painel Lotofácil Inteligente")

# ---------------------------
# Carregar base
# ---------------------------
if st.button("🔄 Atualizar base com último concurso"):
    with st.spinner("Verificando novo concurso..."):
        resultado = atualizar_csv_github()
    st.success(resultado)
    st.rerun()  # ✅ recarrega automaticamente após atualização

file_path = "Lotofacil_Concursos.csv"
df = carregar_dados(file_path)

if df is None:
    st.error("❌ Erro ao carregar os concursos!")
    st.stop()
else:
    st.success(f"✅ Concursos carregados: {len(df)}")

dados_api = obter_concurso_atual_api()
if dados_api:
    numero_api = dados_api["numero"]
    st.info(f"📅 Último concurso oficial: **{numero_api}** ({dados_api['dataApuracao']})")

# ---------------------------
# Abas principais
# ---------------------------
aba = st.sidebar.radio(
    "📍 Menu Principal",
    ["📊 Painéis Estatísticos", "🎯 Geração de Jogos", "📋 Conferir Bolão", "🧮 Conferir Jogos Manuais"]
)

# ---------------------------
# 📊 Aba 1 – Painéis Estatísticos
# ---------------------------
if aba == "📊 Painéis Estatísticos":
    st.header("📊 Painéis Estatísticos da Lotofácil")

    # Slider para quantidade de concursos analisados
    ultimos = st.slider("Selecione quantos concursos deseja analisar:", 50, len(df), len(df))

    # 🔹 Agrupando tudo em abas (tabs)
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Frequência",
        "⏳ Atrasos",
        "⚖️ Pares/Ímpares",
        "🔗 Combinações",
        "➕ Soma",
        "📊 Sequências"
    ])

    # --- 📈 Frequência ---
    with tab1:
        st.subheader("📈 Frequência das Dezenas")
        freq = calcular_frequencia(df, ultimos)
        st.bar_chart(freq.set_index("Dezena")["Frequência"])  # gráfico rápido
        st.dataframe(freq, use_container_width=True)

    # --- ⏳ Atrasos ---
    with tab2:
        st.subheader("⏳ Atrasos das Dezenas")
        atrasos = calcular_atrasos(df)
        st.bar_chart(atrasos.set_index("Dezena")["Atraso Atual"])
        st.dataframe(atrasos, use_container_width=True)

    # --- ⚖️ Pares e Ímpares ---
    with tab3:
        st.subheader("⚖️ Distribuição de Pares e Ímpares")
        pares_impares = calcular_pares_impares(df)
        st.dataframe(pares_impares, use_container_width=True)
        st.markdown("💡 **Dica:** o equilíbrio ideal costuma ficar entre 6x9 e 9x6 (pares/ímpares).")

    # --- 🔗 Combinações Repetidas ---
    with tab4:
        st.subheader("🔗 Combinações Mais Frequentes")
        combinacoes = analisar_combinacoes_repetidas(df)

        for tamanho, tabela in combinacoes.items():
            st.markdown(f"**Top 5 combinações de {tamanho} dezenas:**")
            st.dataframe(tabela, use_container_width=True)

        st.info("💡 Essas combinações indicam duplas, trios e grupos que mais aparecem juntas nos sorteios.")

    # --- ➕ Soma das Dezenas ---
    with tab5:
        st.subheader("➕ Análise da Soma Total das Dezenas")
        df_soma, resumo = calcular_soma_total(df)

        # --- Painel de métricas ---
        col_min, col_med, col_max = st.columns(3)
        col_min.metric("🔻 Soma Mínima", f"{resumo['Soma Mínima']}")
        col_med.metric("⚖️ Soma Média", f"{resumo['Soma Média']:.2f}")
        col_max.metric("🔺 Soma Máxima", f"{resumo['Soma Máxima']}")

        # --- Últimos concursos ---
        st.markdown("**Últimos concursos (soma total):**")
        st.dataframe(df_soma.tail(), use_container_width=True)
        st.line_chart(df_soma.set_index("Concurso")["Soma"], height=250)

        st.info("💡 A soma total costuma variar entre **170 e 210**. "
                "Evite jogos muito fora dessa faixa para manter o padrão estatístico.")

    # --- 📊 Sequências ---
    with tab6:
        st.subheader("📊 Tamanho de Sequências Consecutivas")
        sequencias = calcular_sequencias(df)
        st.bar_chart(sequencias.set_index("Tamanho Sequência")["Ocorrências"])
        st.dataframe(sequencias, use_container_width=True)
        st.markdown("💡 Em geral, sequências de 2 ou 3 números consecutivos são mais comuns.")

