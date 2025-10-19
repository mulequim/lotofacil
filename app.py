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
    gerar_jogos_por_desempenho,
    calcular_valor_aposta,
    gerar_pdf_jogos,
    obter_concurso_atual_api,
    atualizar_csv_github,
    salvar_bolao_csv,
    calcular_soma_total,
    avaliar_jogos_historico  # 🔹 nova função adicionada
)

# ==========================================================
# ⚙️ Configuração geral
# ==========================================================
st.set_page_config(page_title="Lotofácil Inteligente", page_icon="🎲", layout="wide")
st.title("🎲 Painel Lotofácil Inteligente")

# ==========================================================
# 📂 Carregar base
# ==========================================================
if st.button("🔄 Atualizar base com último concurso"):
    with st.spinner("Verificando novo concurso..."):
        resultado = atualizar_csv_github()
    st.success(resultado)
    st.rerun()

file_path = "Lotofacil_Concursos.csv"
df = carregar_dados(file_path)

if df is None:
    st.error("❌ Erro ao carregar os concursos!")
    st.stop()
else:
    st.success(f"✅ Concursos carregados: {len(df)}")

dados_api = obter_concurso_atual_api()
if dados_api:
    st.info(f"📅 Último concurso oficial: **{dados_api['numero']}** ({dados_api['dataApuracao']})")

# ==========================================================
# 📍 Menu lateral
# ==========================================================
aba = st.sidebar.radio(
    "📍 Menu Principal",
    ["📊 Painéis Estatísticos", "🎯 Geração de Jogos"]
)

# ==========================================================
# 📊 Aba 1 – Painéis Estatísticos
# ==========================================================
if aba == "📊 Painéis Estatísticos":
    st.header("📊 Painéis Estatísticos da Lotofácil")

    ultimos = st.slider("Selecione quantos concursos deseja analisar:", 50, len(df), len(df))

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Frequência",
        "⏳ Atrasos",
        "⚖️ Pares/Ímpares",
        "🔗 Combinações",
        "➕ Soma",
        "📊 Sequências"
    ])

    with tab1:
        st.subheader("📈 Frequência das Dezenas")
        freq = calcular_frequencia(df, ultimos)
        st.bar_chart(freq.set_index("Dezena")["Frequência"])
        st.dataframe(freq, use_container_width=True)

    with tab2:
        st.subheader("⏳ Atrasos das Dezenas")
        atrasos = calcular_atrasos(df)
        st.bar_chart(atrasos.set_index("Dezena")["Atraso Atual"])
        st.dataframe(atrasos, use_container_width=True)

    with tab3:
        st.subheader("⚖️ Distribuição de Pares e Ímpares")
        pares_impares = calcular_pares_impares(df)
        st.dataframe(pares_impares, use_container_width=True)
        st.markdown("💡 O equilíbrio ideal costuma ficar entre **6x9 e 9x6** (pares/ímpares).")

    with tab4:
        st.subheader("🔗 Combinações Mais Frequentes")
        combinacoes = analisar_combinacoes_repetidas(df)
        for tamanho, tabela in combinacoes.items():
            st.markdown(f"**Top 5 combinações de {tamanho} dezenas:**")
            st.dataframe(tabela, use_container_width=True)

    with tab5:
        st.subheader("➕ Análise da Soma Total das Dezenas")
        df_soma, resumo = calcular_soma_total(df)
        col_min, col_med, col_max = st.columns(3)
        col_min.metric("🔻 Soma Mínima", f"{resumo['Soma Mínima']}")
        col_med.metric("⚖️ Soma Média", f"{resumo['Soma Média']:.2f}")
        col_max.metric("🔺 Soma Máxima", f"{resumo['Soma Máxima']}")
        st.dataframe(df_soma.tail(), use_container_width=True)
        st.line_chart(df_soma.set_index("Concurso")["Soma"], height=250)
        st.info("💡 Soma típica entre **170 e 210** é considerada estatisticamente equilibrada.")

    with tab6:
        st.subheader("📊 Tamanho das Sequências")
        sequencias = calcular_sequencias(df)
        st.bar_chart(sequencias.set_index("Tamanho Sequência")["Ocorrências"])
        st.dataframe(sequencias, use_container_width=True)
        st.markdown("💡 Sequências de 2 ou 3 números consecutivos são as mais comuns.")

# ==========================================================
# 🎯 Aba 2 – Geração de Jogos
# ==========================================================
if aba == "🎯 Geração de Jogos":
    st.header("🎯 Geração de Jogos")

    modo = st.radio(
        "Selecione o tipo de geração:",
        ["🧠 Geração Inteligente", "📈 Geração por Desempenho Histórico"]
    )

    # --------------------------
    # 🧠 Geração Inteligente
    # --------------------------
    if modo == "🧠 Geração Inteligente":
        st.subheader("🧠 Geração de Jogos Inteligente")

        ranking = calcular_frequencia(df)
        atrasos = calcular_atrasos(df)

        top_atrasadas = atrasos.sort_values("Atraso Atual", ascending=False).head(3)
        top_frequentes = ranking.sort_values("Frequência", ascending=False).head(10)

        col1, col2, col3 = st.columns(3)
        col1.metric("Mais Atrasada", f"{int(top_atrasadas.iloc[0]['Dezena']):02d}", f"{int(top_atrasadas.iloc[0]['Atraso Atual'])} concursos")
        col2.metric("Mais Frequente", f"{int(top_frequentes.iloc[0]['Dezena']):02d}", f"{int(top_frequentes.iloc[0]['Frequência'])} vezes")
        col3.metric("Dezenas Analisadas", "1 a 25", "✅ completo")

        st.markdown("---")
        st.subheader("🎯 Sugestão Automática de Jogo Ideal (15 dezenas)")

        jogo_ideal = sorted(set(top_frequentes.head(10)["Dezena"]).union(set(top_atrasadas["Dezena"])))
        if len(jogo_ideal) < 15:
            faltam = 15 - len(jogo_ideal)
            adicionais = [d for d in range(1, 26) if d not in jogo_ideal][:faltam]
            jogo_ideal.extend(adicionais)
        jogo_ideal = sorted(jogo_ideal[:15])
        st.success(f"🎲 Jogo sugerido: {' '.join(f'{int(d):02d}' for d in jogo_ideal)}")

        st.markdown("💡 Combinação equilibrada entre dezenas quentes e atrasadas.")
        st.markdown("---")
        st.subheader("🧩 Monte seus próprios jogos")

        qtd_jogos = {tam: st.number_input(f"🎯 Jogos de {tam} dezenas", 0, 50, 0) for tam in range(15, 21)}
        total_jogos = sum(qtd_jogos.values())

        if total_jogos > 0 and st.button("🎲 Gerar Jogos Balanceados"):
            jogos_gerados = []
            for tam, qtd in qtd_jogos.items():
                if qtd > 0:
                    jogos_gerados.extend(gerar_jogos_balanceados(df, qtd_jogos=qtd, tamanho=tam))
            st.session_state["jogos_gerados"] = jogos_gerados
            st.success(f"✅ {len(jogos_gerados)} jogos gerados!")

            st.subheader("📊 Avaliação Histórica")
            avaliacao = avaliar_jogos_historico(df, jogos_gerados)
            st.dataframe(avaliacao, use_container_width=True)

    # --------------------------
    # 📈 Geração por Desempenho Histórico
    # --------------------------
    elif modo == "📈 Geração por Desempenho Histórico":
        st.subheader("📈 Geração Baseada em Desempenho Histórico")

        tamanho = st.selectbox("🎯 Tamanho do jogo", [15, 16, 17, 18, 19, 20])
        faixa = st.selectbox("🏆 Faixa de acertos desejada", [11, 12, 13, 14, 15])
        qtd = st.number_input("🔢 Quantidade de jogos a exibir", 1, 10, 5)

        st.markdown("💡 Busca combinações que **mais vezes atingiram** a faixa de acertos selecionada ao longo da história.")

        if st.button("🚀 Buscar Melhores Combinações"):
            with st.spinner("Analisando histórico..."):
                try:
                    df_melhores = gerar_jogos_por_desempenho(df, tamanho_jogo=tamanho, faixa_desejada=faixa, top_n=qtd)
                    st.success("✅ Melhores combinações encontradas!")
                    st.dataframe(df_melhores, use_container_width=True)

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Tamanho", tamanho)
                    col2.metric("Faixa de Acertos", faixa)
                    col3.metric("Top Jogos", qtd)

                except Exception as e:
                    st.error(f"❌ Erro ao gerar: {e}")

        st.markdown("---")
        st.subheader("📊 Gerar Jogo por Desempenho Histórico")
        
        tamanho = st.slider("Selecione o tamanho do jogo", 15, 20, 15)
        faixa = st.selectbox("Escolha a faixa de acertos", [11, 12, 13, 14, 15])
        
        if st.button("🎯 Gerar jogo mais recorrente"):
            with st.spinner("Analisando histórico..."):
                resultado = gerar_jogos_por_desempenho(df, tamanho=tamanho, faixa=faixa)
            st.dataframe(resultado, use_container_width=True)
