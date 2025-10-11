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

    # 🧮 Campos separados para cada tipo de jogo
    st.markdown("### 🧩 Escolha quantos jogos de cada tipo deseja gerar")
    qtd_15 = st.number_input("🎯 Jogos de 15 dezenas", 0, 20, 3)
    qtd_16 = st.number_input("🎯 Jogos de 16 dezenas", 0, 20, 0)
    qtd_17 = st.number_input("🎯 Jogos de 17 dezenas", 0, 20, 0)
    qtd_18 = st.number_input("🎯 Jogos de 18 dezenas", 0, 20, 0)
    qtd_19 = st.number_input("🎯 Jogos de 19 dezenas", 0, 20, 0)
    qtd_20 = st.number_input("🎯 Jogos de 20 dezenas", 0, 20, 0)

    total_jogos = sum([qtd_15, qtd_16, qtd_17, qtd_18, qtd_19, qtd_20])

    if total_jogos == 0:
        st.warning("Informe pelo menos 1 jogo para gerar.")
        st.stop()

    if st.button("🎲 Gerar Jogos Balanceados"):
        tamanhos_qtd = {
            15: qtd_15,
            16: qtd_16,
            17: qtd_17,
            18: qtd_18,
            19: qtd_19,
            20: qtd_20
        }

        jogos_gerados = []

        for tam, qtd in tamanhos_qtd.items():
            if qtd > 0:
                lista_temp = gerar_jogos_balanceados(df, qtd_jogos=qtd, tamanho=tam)
                if lista_temp:
                    jogos_gerados += lista_temp
                else:
                    st.warning(f"⚠️ Nenhum jogo gerado para {tam} dezenas.")

        if not jogos_gerados:
            st.error("❌ Nenhum jogo foi gerado. Verifique os parâmetros.")
            st.stop()

        st.session_state["jogos_gerados"] = jogos_gerados

        # 💾 Salvar todos os jogos no CSV (anexa histórico)
        try:
            df_save = pd.DataFrame([
                {
                    "DataHora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "Jogo": i + 1,
                    "Dezenas": ",".join(map(str, jogo)),
                    "Tamanho": len(jogo)
                }
                for i, (jogo, _) in enumerate(jogos_gerados)
            ])

            if os.path.exists("jogos_gerados.csv"):
                df_existente = pd.read_csv("jogos_gerados.csv", encoding="utf-8")
                df_final = pd.concat([df_existente, df_save], ignore_index=True)
            else:
                df_final = df_save

            df_final.to_csv("jogos_gerados.csv", index=False, encoding="utf-8")
            st.success(f"✅ {len(jogos_gerados)} jogos gerados e salvos em jogos_gerados.csv!")
        except Exception as e:
            st.error(f"❌ Erro ao salvar jogos: {e}")

        # 📊 Avaliação histórica dos jogos
        st.markdown("---")
        st.subheader("📊 Avaliação Histórica dos Jogos")
        avaliacao = avaliar_jogos_historico(df, jogos_gerados)
        st.dataframe(avaliacao, use_container_width=True)

    # ---------------------------
    # Exibir jogos gerados
    # ---------------------------
    if "jogos_gerados" in st.session_state:
        jogos = st.session_state["jogos_gerados"]
        st.markdown("---")
        st.subheader("🎯 Jogos Gerados")

        for idx, (jogo, _) in enumerate(jogos, 1):
            st.write(f"🎯 **Jogo {idx} ({len(jogo)} dezenas):** {' '.join(f'{d:02d}' for d in sorted(jogo))}")

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
