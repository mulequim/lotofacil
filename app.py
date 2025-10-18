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
# ⚙️ Configuração geral
# ---------------------------
st.set_page_config(page_title="Lotofácil Inteligente", page_icon="🎲", layout="wide")
st.title("🎲 Painel Lotofácil Inteligente")

# ---------------------------
# 📂 Carregar base
# ---------------------------
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

# ---------------------------
# 📍 Menu lateral
# ---------------------------
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
# 🎯 Aba 2 – Geração de Jogos Inteligente
# ==========================================================
if aba == "🎯 Geração de Jogos":
    st.header("🧠 Geração de Jogos Inteligente")

    ranking = calcular_frequencia(df)
    atrasos = calcular_atrasos(df)

    top_atrasadas = atrasos.sort_values("Atraso Atual", ascending=False).head(3)
    top_frequentes = ranking.sort_values("Frequência", ascending=False).head(10)

    # 🔹 Painel resumo
    st.subheader("📊 Resumo Estatístico Atual")
    col1, col2, col3 = st.columns(3)
    col1.metric("Mais Atrasada", f"{int(top_atrasadas.iloc[0]['Dezena']):02d}", f"{int(top_atrasadas.iloc[0]['Atraso Atual'])} concursos")
    col2.metric("Mais Frequente", f"{int(top_frequentes.iloc[0]['Dezena']):02d}", f"{int(top_frequentes.iloc[0]['Frequência'])} vezes")
    col3.metric("Dezenas Analisadas", "1 a 25", "✅ completo")

    st.markdown("---")

    # 🔹 Sugestão de jogo automático
    st.subheader("🎯 Sugestão Automática de Jogo Ideal (15 dezenas)")
    jogo_ideal = sorted(
        list(
            set(top_frequentes.head(10)["Dezena"]).union(set(top_atrasadas["Dezena"]))
        )
    )
    if len(jogo_ideal) < 15:
        faltam = 15 - len(jogo_ideal)
        adicionais = [d for d in range(1, 26) if d not in jogo_ideal][:faltam]
        jogo_ideal.extend(adicionais)

    jogo_ideal = sorted(jogo_ideal[:15])
    st.success(f"🎲 Jogo sugerido: {' '.join(f'{int(d):02d}' for d in jogo_ideal)}")

    st.markdown("💡 Este jogo combina as dezenas mais frequentes e as mais atrasadas, equilibrando probabilidade e oportunidade.")

    st.markdown("---")
    st.subheader("🧩 Gerar seus próprios jogos")

    qtd_15 = st.number_input("🎯 Jogos de 15 dezenas", 0, 50, 0)
    qtd_16 = st.number_input("🎯 Jogos de 16 dezenas", 0, 50, 0)
    qtd_17 = st.number_input("🎯 Jogos de 17 dezenas", 0, 50, 0)
    qtd_18 = st.number_input("🎯 Jogos de 18 dezenas", 0, 50, 0)
    qtd_19 = st.number_input("🎯 Jogos de 19 dezenas", 0, 50, 0)
    qtd_20 = st.number_input("🎯 Jogos de 20 dezenas", 0, 50, 0)

    total_jogos = sum([qtd_15, qtd_16, qtd_17, qtd_18, qtd_19, qtd_20])

    if total_jogos == 0:
        st.info("Escolha pelo menos 1 jogo para gerar.")
    else:
        if st.button("🎲 Gerar Jogos Balanceados"):
            tamanhos_qtd = {15: qtd_15, 16: qtd_16, 17: qtd_17, 18: qtd_18, 19: qtd_19, 20: qtd_20}
            jogos_gerados = []
            for tam, qtd in tamanhos_qtd.items():
                if qtd > 0:
                    lista_temp = gerar_jogos_balanceados(df, qtd_jogos=qtd, tamanho=tam)
                    jogos_gerados.extend(lista_temp)

            st.session_state["jogos_gerados"] = jogos_gerados
            st.success(f"✅ {len(jogos_gerados)} jogos gerados!")

            try:
                file_path = os.path.join(os.getcwd(), "jogos_gerados.csv")
                criar_cabecalho = not os.path.exists(file_path)
                linhas = [{
                    "ID": i,
                    "DataHora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Tamanho": len(jogo),
                    "Dezenas": ",".join(str(d) for d in sorted(jogo))
                } for i, (jogo, _) in enumerate(jogos_gerados, start=1)]
                pd.DataFrame(linhas).to_csv(file_path, mode="a", index=False, header=criar_cabecalho, encoding="utf-8")
            except Exception as e:
                st.error(f"❌ Erro ao salvar jogos: {e}")

            st.markdown("---")
            st.subheader("📊 Avaliação Histórica dos Jogos")
            avaliacao = avaliar_jogos_historico(df, jogos_gerados)
            st.dataframe(avaliacao, use_container_width=True)

    # Exibição dos jogos gerados
    if "jogos_gerados" in st.session_state:
        jogos = st.session_state["jogos_gerados"]
        st.markdown("---")
        st.subheader("🎯 Jogos Gerados")
        with st.expander("🎨 Legenda das Cores", expanded=True):
            st.markdown("""
            - 🔴 **Vermelho:** dezenas mais **atrasadas**  
            - ⚪ **Branco:** dezenas **neutras**  
            - 🔵 **Azul:** dezenas mais **frequentes**
            """)

        for idx, (jogo, origem) in enumerate(jogos, start=1):
            display = [f"{ {'frequente':'🔵','atrasada':'🔴','aleatoria':'⚪'}.get(origem.get(d,'aleatoria'),'⚪') } {d:02d}" for d in jogo]
            st.markdown(f"🎯 **Jogo {idx} ({len(jogo)} dezenas):** {' '.join(display)}")

        st.markdown("---")
        st.subheader("💬 Dados do Bolão")
        participantes_input = st.text_input("👥 Participantes", value="Participante 01, Participante 02, Participante 03")
        pix_input = st.text_input("💸 Chave PIX", value="marcosmigueloliveira@yahoo.com.br")

        participantes_lista = [p.strip() for p in participantes_input.split(",") if p.strip()]
        valor_total = sum(calcular_valor_aposta(len(jogo)) for jogo, _ in jogos)
        valor_por_pessoa = (valor_total / len(participantes_lista)) if participantes_lista else valor_total

        st.metric("💰 Valor total", f"R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        if participantes_lista:
            st.dataframe(pd.DataFrame({"Participante": participantes_lista, "Valor (R$)": [round(valor_por_pessoa, 2)] * len(participantes_lista)}), use_container_width=True)

        if st.button("📄 Gerar PDF do Bolão"):
            arquivo_pdf = gerar_pdf_jogos(jogos, nome="Bolão Inteligente", participantes=participantes_input, pix=pix_input)
            st.success(f"📄 PDF gerado com sucesso!")
            with open(arquivo_pdf, "rb") as f:
                st.download_button("⬇️ Baixar PDF", f, file_name=arquivo_pdf)

