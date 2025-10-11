import streamlit as st
import pandas as pd
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

    ultimos = st.slider("Selecione quantos concursos deseja analisar:", 50, len(df), 300)

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
    st.caption("🔎 Mostra as combinações que mais se repetiram nos últimos concursos.")

# --------------------------
# 🎯 Aba 2 – Geração de Jogos Inteligente
# --------------------------
if aba == "🎯 Geração de Jogos":
    st.header("🃏 Geração de Jogos Inteligente")

    ranking = calcular_frequencia(df, ultimos=100)

    if "Dezena" not in ranking.columns:
        st.error("❌ A coluna 'Dezena' não foi encontrada no resultado de calcular_frequencia().")
        st.stop()

    # Forçar conversão segura e limpar valores inválidos
    ranking["Dezena"] = pd.to_numeric(ranking["Dezena"], errors="coerce")
    dezenas_base = ranking["Dezena"].dropna().astype(int).tolist()

    if not dezenas_base:
        st.error("❌ Nenhuma dezena válida encontrada. Verifique o arquivo Lotofacil.csv.")
        st.stop()

    jogo_fixo_input = st.text_input("👉 Digite dezenas fixas (máx 10)", "")
    dezenas_fixas = [int(x.strip()) for x in jogo_fixo_input.split(",") if x.strip().isdigit()]

    atrasos = calcular_atrasos(df)
    dezenas_atrasadas = atrasos.sort_values("Atraso Atual", ascending=False).head(3)["Dezena"].tolist()
    st.info(f"🔴 Usando dezenas atrasadas sugeridas: {dezenas_atrasadas}")

    tamanho_jogo = st.slider("🎯 Tamanho do jogo", 15, 20, 15)
    qtd_jogos = st.number_input("🎲 Quantos jogos deseja gerar?", min_value=1, max_value=10, value=4)
   

    # --------------------------
    # 🔘 Botão para gerar jogos
    # --------------------------
    if st.button("🎲 Gerar Jogos Balanceados"):
        st.session_state["jogos_gerados"] = gerar_jogos_balanceados(df, qtd_jogos, tamanho_jogo)
        st.success(f"✅ {qtd_jogos} jogos gerados com sucesso!")

    # --------------------------
    # 📋 Exibir jogos gerados
    # --------------------------
    if "jogos_gerados" in st.session_state:
        jogos = st.session_state["jogos_gerados"]

        st.subheader("🎯 Jogos Gerados")
        for idx, (jogo, origem) in enumerate(jogos, start=1):
            st.markdown(f"### 🎯 Jogo {idx} ({len(jogo)} dezenas)")
            display = []
            for d in jogo:
                cor = {
                    "frequente": "🔵",
                    "atrasada": "🔴",
                    "repetida": "🟢",
                    "equilibrio": "⚪"
                }.get(origem[d], "⚪")
                display.append(f"{cor} {d:02d}")
            st.markdown(" ".join(display))

        st.markdown("---")

        # --------------------------
        # 💬 Dados do bolão (persistentes)
        # --------------------------
        st.markdown("### 💬 Dados do Bolão")
        participantes_input = st.text_input(
            "👥 Participantes (separe por vírgulas)",
            value=st.session_state.get("participantes", "Marcos, João, Arthur")
        )
        st.session_state["participantes"] = participantes_input
        
        pix_input = st.text_input(
            "💸 Chave PIX para rateio",
            value=st.session_state.get("pix", "marcosoliveira@pix.com")
        )
        st.session_state["pix"] = pix_input


        # --------------------------
        # 📊 Cálculo financeiro
        # --------------------------
        participantes_lista = [p.strip() for p in participantes_input.split(",") if p.strip()]
        valor_total = sum(calcular_valor_aposta(len(jogo)) for jogo, _ in jogos)
        valor_por_pessoa = valor_total / len(participantes_lista) if participantes_lista else valor_total

        st.subheader("📊 Resumo do Rateio")
        df_resumo = pd.DataFrame({
            "Participantes": participantes_lista or ["(Nenhum)"],
            "Valor Individual (R$)": [round(valor_por_pessoa, 2)] * (len(participantes_lista) or 1)
        })
        st.dataframe(df_resumo, use_container_width=True)

        st.markdown(f"**💰 Valor total do bolão:** R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        # --------------------------
        # 📄 Gerar PDF (mantém dados)
        # --------------------------
        # 📄 Gerar PDF + Salvar bolão
        if st.button("📄 Gerar PDF do Bolão"):
            arquivo_pdf = gerar_pdf_jogos(
                jogos,
                nome="Bolão Inteligente",
                participantes=participantes_input,
                pix=pix_input
            )
        
            codigo_bolao = salvar_bolao_csv(
                jogos=jogos,
                participantes=participantes_input,
                pix=pix_input,
                valor_total=valor_total,
                valor_por_pessoa=valor_por_pessoa,
                concurso_base=numero_api  # último concurso conhecido
            )
        
            if codigo_bolao:
                st.success(f"📄 PDF gerado e bolão salvo com sucesso!")
                st.info(f"🧾 Código do bolão: **{codigo_bolao}** (guarde para conferência futura)")
            else:
                st.warning("⚠️ Bolão não pôde ser salvo no histórico.")
        
            with open(arquivo_pdf, "rb") as file:
                st.download_button("⬇️ Baixar PDF", file, file_name=arquivo_pdf)
# 📋 Conferência de bolão salvo
if aba == "📋 Conferir Bolão":
    st.header("📋 Conferência de Bolão")

    codigo_input = st.text_input("🧾 Digite o código do bolão (ex: B20251009ABC123)")
    concurso_input = st.number_input("🏆 Concurso para conferência", min_value=1, step=1)

    if st.button("🔍 Conferir"):
        try:
            df_boloes = pd.read_csv("jogos_gerados.csv")
            bolao = df_boloes[df_boloes["CodigoBolao"] == codigo_input]
            if bolao.empty:
                st.error("❌ Código de bolão não encontrado.")
            else:
                st.success("✅ Bolão encontrado!")

                jogos = json.loads(bolao.iloc[0]["Jogos"])
                participantes = bolao.iloc[0]["Participantes"]
                concurso = int(concurso_input)

                # Buscar resultado do concurso
                url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/{concurso}"
                r = requests.get(url, headers={"accept": "application/json"}, timeout=10)
                if r.status_code != 200:
                    st.error("❌ Não foi possível obter o resultado da Caixa.")
                else:
                    dados = r.json()
                    dezenas_sorteadas = [int(d) for d in dados["listaDezenas"]]
                    st.info(f"🎯 Resultado do concurso {concurso}: {dezenas_sorteadas}")

                    resultados = []
                    for idx, jogo in enumerate(jogos, start=1):
                        acertos = len(set(jogo) & set(dezenas_sorteadas))
                        resultados.append((idx, acertos))

                    df_result = pd.DataFrame(resultados, columns=["Jogo", "Acertos"])
                    st.dataframe(df_result)

                    total_acertos = df_result["Acertos"].value_counts().to_dict()
                    st.markdown("### 📊 Resumo dos acertos:")
                    for k in sorted(total_acertos.keys(), reverse=True):
                        st.write(f"🎯 **{k} acertos:** {total_acertos[k]} jogo(s)")

        except Exception as e:
            st.error(f"Erro ao conferir bolão: {e}")

# --------------------------
# 🧮 Aba 4 – Conferir Jogos Manuais
# --------------------------
if aba == "🧮 Conferir Jogos Manuais":
    st.header("🧮 Conferência de Jogos Manuais")

    dezenas_input = st.text_area(
        "Digite seus jogos (um por linha, dezenas separadas por vírgula):",
        "01,02,03,04,05,06,07,08,09,10,11,12,13,14,15\n01,03,05,07,09,11,13,15,17,19,21,23,25,02,04"
    )

    concurso_input = st.number_input("🏆 Concurso para conferir", min_value=1, step=1)
    if st.button("🔍 Conferir Jogos"):
        try:
            url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/{int(concurso_input)}"
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                st.error("❌ Não foi possível obter o resultado da Caixa.")
            else:
                dados = r.json()
                dezenas_sorteadas = [int(x) for x in dados["listaDezenas"]]
                st.success(f"🎯 Resultado: {dezenas_sorteadas}")

                linhas = [l.strip() for l in dezenas_input.splitlines() if l.strip()]
                resultados = []
                for i, linha in enumerate(linhas, start=1):
                    dezenas = [int(x.strip()) for x in linha.split(",") if x.strip().isdigit()]
                    acertos = len(set(dezenas) & set(dezenas_sorteadas))
                    resultados.append({"Jogo": i, "Dezenas": dezenas, "Acertos": acertos})

                df_result = pd.DataFrame(resultados)
                st.dataframe(df_result)
                st.markdown("### 📊 Resumo de acertos")
                contagem = df_result["Acertos"].value_counts().to_dict()
                for k in sorted(contagem.keys(), reverse=True):
                    st.write(f"🎯 {k} acertos: {contagem[k]} jogo(s)")
        except Exception as e:
            st.error(f"Erro ao conferir: {e}")
