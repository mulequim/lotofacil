import streamlit as st
import pandas as pd
import requests
import json
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
    st.experimental_rerun()  # ✅ recarrega automaticamente após atualização

file_path = "Lotofacil.csv"
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

    # ✅ Agora o padrão é analisar TODOS os concursos
    ultimos = st.slider("Selecione quantos concursos deseja analisar:", 50, len(df), len(df))

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔢 Frequência das dezenas")
        freq = calcular_frequencia(df, ultimos)
        st.dataframe(freq, use_container_width=True)

    with col2:
        st.subheader("⏱️ Atrasos")
        atrasos = calcular_atrasos(df)
        st.dataframe(atrasos, use_container_width=True)

    st.markdown("---")

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("⚖️ Pares e Ímpares")
        pares_impares = calcular_pares_impares(df)
        st.dataframe(pares_impares, use_container_width=True)

    with col4:
        st.subheader("🔗 Sequências")
        sequencias = calcular_sequencias(df)
        st.dataframe(sequencias, use_container_width=True)

    st.markdown("---")

    st.subheader("🔁 Combinações Repetidas (pares, trios, quartetos)")
    combinacoes = analisar_combinacoes_repetidas(df)
    st.dataframe(combinacoes, use_container_width=True)

# --------------------------
# 🎯 Aba 2 – Geração de Jogos Inteligente
# --------------------------
if aba == "🎯 Geração de Jogos":
    st.header("🃏 Geração de Jogos Inteligente")

    ranking = calcular_frequencia(df, ultimos=len(df))
    atrasos = calcular_atrasos(df)

    dezenas_atrasadas = atrasos.sort_values("Atraso Atual", ascending=False).head(3)["Dezena"].tolist()
    st.info(f"🔴 Dezenas mais atrasadas sugeridas: {dezenas_atrasadas}")

    tamanhos = st.multiselect(
        "🎯 Escolha os tamanhos dos jogos (pode misturar):",
        [15, 16, 17, 18, 19, 20],
        default=[15]
    )
    qtd_jogos = st.number_input("🎲 Quantos jogos deseja gerar no total?", min_value=1, max_value=20, value=5)

    if st.button("🎲 Gerar Jogos Balanceados"):
        jogos = gerar_jogos_balanceados(df, qtd_jogos, tamanhos)
        st.session_state["jogos_gerados"] = jogos

        # ✅ Salva automaticamente os jogos gerados
        pd.DataFrame(
            [{"Jogo": idx, "Dezenas": jogo, "Tamanho": len(jogo)} for idx, (jogo, _) in enumerate(jogos, 1)]
        ).to_csv("jogos_gerados.csv", index=False, encoding="utf-8")

        st.success(f"✅ {qtd_jogos} jogos gerados com sucesso e salvos no arquivo jogos_gerados.csv!")

        # 🔍 Mostrar estatísticas relacionadas aos jogos gerados
        st.markdown("---")
        st.subheader("📊 Estatísticas dos Jogos Gerados")
        avaliacao = avaliar_jogos_historico(df, jogos)
        st.dataframe(avaliacao, use_container_width=True)

    if "jogos_gerados" in st.session_state:
        jogos = st.session_state["jogos_gerados"]
        st.markdown("---")
        st.subheader("🎯 Jogos Gerados")
        for idx, (jogo, origem) in enumerate(jogos, 1):
            display = " ".join(f"{d:02d}" for d in sorted(jogo))
            st.write(f"🎯 **Jogo {idx} ({len(jogo)} dezenas):** {display}")

        # Dados para o bolão
        st.markdown("---")
        st.subheader("💬 Dados do Bolão")

        participantes_input = st.text_input("👥 Participantes (separe por vírgulas)", "Marcos, João, Arthur")
        pix_input = st.text_input("💸 Chave PIX para rateio", "marcosoliveira@pix.com")

        participantes_lista = [p.strip() for p in participantes_input.split(",") if p.strip()]
        valor_total = sum(calcular_valor_aposta(len(jogo)) for jogo, _ in jogos)
        valor_por_pessoa = valor_total / len(participantes_lista) if participantes_lista else valor_total

        st.subheader("📊 Rateio do Bolão")
        df_rateio = pd.DataFrame({
            "Participantes": participantes_lista,
            "Valor (R$)": [round(valor_por_pessoa, 2)] * len(participantes_lista)
        })
        st.dataframe(df_rateio, use_container_width=True)

        st.markdown(f"**💰 Valor total:** R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        if st.button("📄 Gerar PDF do Bolão"):
            arquivo_pdf = gerar_pdf_jogos(jogos, nome="Bolão Inteligente", participantes=participantes_input, pix=pix_input)
            codigo_bolao = salvar_bolao_csv(
                jogos, participantes_input, pix_input, valor_total, valor_por_pessoa, numero_api
            )
            if codigo_bolao:
                st.success(f"📄 PDF gerado e bolão salvo! Código: {codigo_bolao}")
            with open(arquivo_pdf, "rb") as f:
                st.download_button("⬇️ Baixar PDF", f, file_name=arquivo_pdf)

# --------------------------
# 📋 Conferir Bolão e 🧮 Jogos Manuais
# (mantidos iguais ao seu original)
# --------------------------
# [essa parte permanece sem alterações]
