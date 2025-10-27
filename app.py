

import streamlit as st
import pandas as pd
import os
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
    avaliar_jogos_historico
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
        "📈 Frequência", "⏳ Atrasos", "⚖️ Pares/Ímpares",
        "🔗 Combinações", "➕ Soma", "📊 Sequências"
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
        st.line_chart(df_soma.set_index("Concurso")["Soma"], height=250)
        st.info("💡 Soma típica entre **170 e 210** é considerada equilibrada.")

    with tab6:
        st.subheader("📊 Tamanho das Sequências")
        sequencias = calcular_sequencias(df)
        st.bar_chart(sequencias.set_index("Tamanho Sequência")["Ocorrências"])
        st.dataframe(sequencias, use_container_width=True)

# ==========================================================
# 🎯 Aba 2 – Geração de Jogos
# ==========================================================
if aba == "🎯 Geração de Jogos":
    st.header("🎯 Geração de Jogos")

    modo = st.radio("Selecione o tipo de geração:",
                    ["🧠 Geração Inteligente", "📈 Geração por Desempenho Histórico"])

    # --------------------------
    # 🧠 Geração Inteligente
    # --------------------------
    if modo == "🧠 Geração Inteligente":
        st.header("🧠 Geração de Jogos Inteligente com Explicações e Análises")

        ranking = calcular_frequencia(df)
        atrasos = calcular_atrasos(df)
        top_atrasadas = atrasos.sort_values("Atraso Atual", ascending=False).head(3)
        top_frequentes = ranking.sort_values("Frequência", ascending=False).head(10)

        col1, col2, col3 = st.columns(3)
        col1.metric("🔥 Mais Frequente", f"{int(top_frequentes.iloc[0]['Dezena']):02d}",
                    f"{int(top_frequentes.iloc[0]['Frequência'])}x")
        col2.metric("🧊 Mais Atrasada", f"{int(top_atrasadas.iloc[0]['Dezena']):02d}",
                    f"{int(top_atrasadas.iloc[0]['Atraso Atual'])} concursos")
        col3.metric("📅 Total de Concursos", len(df), "Histórico completo")

        st.markdown("---")
        st.subheader("🎯 Sugestão Automática (15 dezenas balanceadas)")

        jogo_ideal = sorted(set(top_frequentes.head(10)["Dezena"]).union(set(top_atrasadas["Dezena"])))
        faltam = 15 - len(jogo_ideal)
        if faltam > 0:
            adicionais = [d for d in range(1, 26) if d not in jogo_ideal][:faltam]
            jogo_ideal.extend(adicionais)
        jogo_ideal = sorted(jogo_ideal)

        st.success("🎲 **Jogo sugerido:** " + " ".join(f"{int(d):02d}" for d in jogo_ideal))
        st.caption("💡 Equilíbrio entre dezenas quentes e atrasadas, soma próxima de 190 ± 20.")

        st.markdown("---")
        st.subheader("🧩 Monte seus próprios jogos inteligentes")

        qtd_jogos = {tam: st.number_input(f"🎯 Jogos de {tam} dezenas", 0, 50, 0)
                     for tam in range(15, 21)}
        total_jogos = sum(qtd_jogos.values())

        if total_jogos > 0 and st.button("🤖 Gerar Jogos Inteligentes"):
            jogos_gerados = []
            for tam, qtd in qtd_jogos.items():
                if qtd > 0:
                    jogos_gerados.extend(gerar_jogos_balanceados(df, qtd_jogos=qtd, tamanho=tam))

            st.session_state["jogos_gerados"] = jogos_gerados
            st.success(f"✅ {len(jogos_gerados)} jogos gerados com análise estatística!")

            st.markdown("---")
            st.subheader("📊 Análise Visual dos Jogos Gerados")

            legenda = {
                "quente": "🔵 **Quente:** Alta frequência.",
                "fria": "🔴 **Fria:** Longo atraso.",
                "neutra": "⚪ **Neutra:** Média estável.",
                "recente": "🟢 **Recente:** Saiu nos últimos 3.",
                "sequencia": "🟠 **Sequência:** Consecutiva no jogo.",
                "alta_soma": "🟣 **Alta Soma:** >210, arriscado.",
                "baixa_soma": "🟤 **Baixa Soma:** <170, conservador."
            }

            jogos = st.session_state["jogos_gerados"]
            for idx, (jogo, origem) in enumerate(jogos, start=1):
                display = []
                for d in jogo:
                    tag = origem.get(d, "neutra")
                    emoji = {
                        "quente": "🔵", "fria": "🔴", "neutra": "⚪", "recente": "🟢",
                        "sequencia": "🟠", "alta_soma": "🟣", "baixa_soma": "🟤"
                    }.get(tag, "⚪")
                    display.append(f"{emoji} {d:02d}")

                st.markdown(f"🎯 **Jogo {idx} ({len(jogo)} dezenas):** {' '.join(display)}")

                pares = len([d for d in jogo if d % 2 == 0])
                impares = len(jogo) - pares
                soma = sum(jogo)
                qualidade = 100 - abs(190 - soma) / 2

                col1, col2, col3 = st.columns(3)
                col1.metric("⚖️ Pares/Ímpares", f"{pares}/{impares}")
                col2.metric("➕ Soma", soma)
                col3.metric("⭐ Qualidade", f"{qualidade:.1f}/100")
                st.progress(min(qualidade / 100, 1.0))

                with st.expander(f"🔍 Explicação do raciocínio do Jogo {idx}"):
                    for d in jogo:
                        tag = origem.get(d, "neutra")
                        explicacao = {
                            "quente": "Alta frequência recente.",
                            "fria": "Muito atrasada, chance de retorno.",
                            "recente": "Saiu há pouco tempo.",
                            "sequencia": "Consecutiva no jogo.",
                            "alta_soma": "Jogo de soma alta.",
                            "baixa_soma": "Jogo de soma baixa.",
                            "neutra": "Média estável."
                        }.get(tag, "Sem destaque.")
                        st.markdown(f"**{d:02d}** → {explicacao}")

                st.markdown("---")

            with st.expander("🎨 Legenda das Cores e Critérios", expanded=True):
                for _, desc in legenda.items():
                    st.markdown(desc)

            st.success("💡 Cada cor representa um critério estatístico para facilitar sua análise.")

    # --------------------------
    # 📈 Geração por Desempenho Histórico
    # --------------------------
    elif modo == "📈 Geração por Desempenho Histórico":
        st.subheader("📈 Geração Baseada em Desempenho Histórico")
        tamanho = st.selectbox("🎯 Tamanho do jogo", [15, 16, 17, 18, 19, 20])
        faixa = st.selectbox("🏆 Faixa de acertos desejada", [11, 12, 13, 14, 15])
        qtd = st.number_input("🔢 Quantidade de jogos a exibir", 1, 10, 5)

        st.markdown("💡 Busca combinações que **mais vezes atingiram** a faixa de acertos ao longo da história.")

        if st.button("🚀 Buscar Melhores Combinações"):
            with st.spinner("Analisando histórico..."):
                try:
                    df_melhores = gerar_jogos_por_desempenho(
                        df, tamanho_jogo=tamanho, faixa_desejada=faixa, top_n=qtd
                    )
                    st.success("✅ Melhores combinações encontradas!")
                    st.dataframe(df_melhores, use_container_width=True)

                except Exception as e:
                    st.error(f"❌ Erro ao gerar: {e}")
