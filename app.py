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
    avaliar_jogos,
    gerar_pdf_jogos,
    obter_concurso_atual_api,
    atualizar_csv_github,
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
aba = st.sidebar.radio("📍 Menu Principal", ["📊 Painéis Estatísticos", "🎯 Geração de Jogos"])

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

# ---------------------------
# 🎯 Aba 2 – Geração de Jogos
# ---------------------------
elif aba == "🎯 Geração de Jogos":
    st.header("🎯 Gerador de Jogos Inteligente")

    # Base para gerar
    ranking = calcular_frequencia(df, ultimos=len(df))
    dezenas_base = ranking["Dezena"].tolist()

    # Fixas digitadas
    dezenas_fixas_input = st.text_input("👉 Digite dezenas fixas (máx 10, separadas por vírgula)", "")
    dezenas_fixas = []
    if dezenas_fixas_input:
        dezenas_fixas = [int(x.strip()) for x in dezenas_fixas_input.split(",") if x.strip().isdigit()]

    # Atrasadas automáticas
    atrasos = calcular_atrasos(df)
    dezenas_atrasadas = atrasos.sort_values("Atraso Atual", ascending=False).head(3)["Dezena"].tolist()
    st.info(f"🔴 Dezenas atrasadas sugeridas: {dezenas_atrasadas}")

    # Configurações de jogo
    tamanho_jogo = st.slider("🎯 Tamanho do jogo", 15, 20, 15)
    qtd_jogos = st.number_input("🎲 Quantos jogos deseja gerar?", min_value=1, max_value=20, value=4)

    if st.button("🎲 Gerar Jogos Balanceados"):
        jogos = gerar_jogos_balanceados(df, qtd_jogos, tamanho_jogo)
        st.subheader("🎯 Jogos Gerados")

        for idx, (jogo, origem) in enumerate(jogos, start=1):
            st.markdown(f"### 🎯 Jogo {idx} ({len(jogo)} dezenas)")
            display = []
            for d in jogo:
                tipo = origem.get(d, "")
                if tipo == "frequente":
                    display.append(f"<span style='color:blue;'>🔵 {d}</span>")
                elif tipo == "atrasada":
                    display.append(f"<span style='color:red;'>🔴 {d}</span>")
                elif tipo == "repetida":
                    display.append(f"<span style='color:green;'>🟢 {d}</span>")
                else:
                    display.append(f"<span style='color:gray;'>⚪ {d}</span>")
            st.markdown(" ".join(display), unsafe_allow_html=True)

        st.markdown("""
        📘 **Legenda:**
        - 🔵 Mais frequentes  
        - 🔴 Atrasadas  
        - 🟢 De combinações recorrentes  
        - ⚪ Equilíbrio par/ímpar  
        """)

        # Avaliar os jogos
        st.subheader("📈 Avaliação dos Jogos")
        resultados = avaliar_jogos(jogos, df)
        for idx, jogo, contagens in resultados:
            st.markdown(f"**🎲 Jogo {idx}:** {', '.join(map(str, jogo))}")
            st.write(
                f"""
                • 🎯 11 acertos: {contagens[11]}  
                • 🎯 12 acertos: {contagens[12]}  
                • 🎯 13 acertos: {contagens[13]}  
                • 🎯 14 acertos: {contagens[14]}  
                • 🏆 15 acertos: {contagens[15]}  
                """
            )
            st.markdown("---")

        st.markdown("### 💬 Dados do Bolão")
        participantes_input = st.text_input("👥 Participantes (separe por vírgulas)", "Marcos, João, Arthur")
        pix_input = st.text_input("💸 Chave PIX para rateio", "marcosoliveira@pix.com")
        
        if st.button("📄 Gerar PDF do Bolão"):
            arquivo_pdf = gerar_pdf_jogos(
                jogos,
                nome="Bolão Inteligente",
                participantes=participantes_input,
                pix=pix_input
            )
        
            # Mostrar resumo financeiro
            participantes_lista = [p.strip() for p in participantes_input.split(",") if p.strip()]
            valor_total = sum(calcular_valor_aposta(len(jogo)) for jogo, _ in jogos)
            valor_por_pessoa = valor_total / len(participantes_lista) if participantes_lista else valor_total
        
            st.subheader("📊 Resumo do Rateio")
            df_resumo = pd.DataFrame({
                "Participantes": participantes_lista or ["(Nenhum)"],
                "Valor Individual (R$)": [round(valor_por_pessoa, 2)] * (len(participantes_lista) or 1)
            })
            st.dataframe(df_resumo, use_container_width=True)
        
            st.success(f"📄 PDF gerado com sucesso: {arquivo_pdf}")
            with open(arquivo_pdf, "rb") as file:
                st.download_button("⬇️ Baixar PDF", file, file_name=arquivo_pdf)


