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
        atrasos = calcular_atrasos(df, debug=True)  # ativa prints
        st.dataframe(atrasos)


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

    # padrão: usar TODOS os concursos para estatísticas
    ranking = calcular_frequencia(df, ultimos=None)
    atrasos = calcular_atrasos(df)
    # --------------------------
    # 🔍 Destaques de dezenas
    # --------------------------
    
    # Top 3 atrasadas (com atraso atual)
    top_atrasadas = atrasos.sort_values("Atraso Atual", ascending=False).head(3)[["Dezena", "Atraso Atual"]]
    top_frequentes = ranking.sort_values("Frequência", ascending=False).head(10)[["Dezena", "Frequência"]]
    
    # Cria DataFrame para exibição lado a lado
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🔴 Top 3 Dezenas Mais Atrasadas")
        st.table(pd.DataFrame({
            "Dezena": [f"{int(row['Dezena']):02d}" for _, row in top_atrasadas.iterrows()],
            "Concursos em Atraso": [int(row["Atraso Atual"]) for _, row in top_atrasadas.iterrows()]
        }))
    
    with col2:
        st.markdown("### 🔵 Top 10 Dezenas Mais Frequentes")
        st.table(pd.DataFrame({
            "Dezena": [f"{int(row['Dezena']):02d}" for _, row in top_frequentes.iterrows()],
            "Qtd Sorteios": [int(row["Frequência"]) for _, row in top_frequentes.iterrows()]
        }))


    st.markdown("### 🧩 Escolha quantos jogos de cada tipo deseja gerar")
    qtd_15 = st.number_input("🎯 Jogos de 15 dezenas", 0, 50, 0)
    qtd_16 = st.number_input("🎯 Jogos de 16 dezenas", 0, 50, 0)
    qtd_17 = st.number_input("🎯 Jogos de 17 dezenas", 0, 50, 0)
    qtd_18 = st.number_input("🎯 Jogos de 18 dezenas", 0, 50, 0)
    qtd_19 = st.number_input("🎯 Jogos de 19 dezenas", 0, 50, 0)
    qtd_20 = st.number_input("🎯 Jogos de 20 dezenas", 0, 50, 0)

    total_jogos = sum([qtd_15, qtd_16, qtd_17, qtd_18, qtd_19, qtd_20])
    if total_jogos == 0:
        st.info("Informe pelo menos 1 jogo para gerar (escolha quantidades acima).")
    else:
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
                    jogos_gerados.extend(lista_temp)

            # guarda no session_state
            st.session_state["jogos_gerados"] = jogos_gerados

            # salva em CSV no diretório atual (append)
            try:
                import os
                from datetime import datetime
                file_path = os.path.join(os.getcwd(), "jogos_gerados.csv")
                criar_cabecalho = not os.path.exists(file_path)
                linhas = []
                for i, (jogo, _) in enumerate(jogos_gerados, start=1):
                    linhas.append({
                        "ID": i,
                        "DataHora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Tamanho": len(jogo),
                        "Dezenas": ",".join(str(d) for d in sorted(jogo))
                    })
                df_save = pd.DataFrame(linhas)
                df_save.to_csv(file_path, mode="a", index=False, header=criar_cabecalho, encoding="utf-8")
                st.success(f"✅ {len(jogos_gerados)} jogos gerados e salvos em {file_path}!")
            except Exception as e:
                st.error(f"❌ Erro ao salvar jogos: {e}")

            # Avaliação histórica (11..15)
            st.markdown("---")
            st.subheader("📊 Avaliação Histórica dos Jogos")
            try:
                avaliacao = avaliar_jogos_historico(df, jogos_gerados)
                st.dataframe(avaliacao, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao avaliar historicamente: {e}")

    # exibe jogos gerados (se houver)
    if "jogos_gerados" in st.session_state:
        jogos = st.session_state["jogos_gerados"]
        st.markdown("---")
        st.subheader("🎯 Jogos Gerados")
        # --------------------------
        # 🎯 Legenda de cores
        # --------------------------
        with st.expander("🎨 Legenda das Cores", expanded=True):
            st.markdown("""
            - 🔴 **Vermelho:** dezenas mais **atrasadas** (não saem há muitos concursos).  
            - ⚪ **Branco:** dezenas **neutras**, dentro da média de sorteios.  
            - 🔵 **Azul:** dezenas mais **frequentes** nos concursos recentes.
            """)

        for idx, (jogo, origem) in enumerate(jogos, start=1):
            # mostra origem por dezena se quiser (agora apenas emoji)
            display = []
            for d in jogo:
                tag = {"frequente": "🔵", "atrasada": "🔴", "aleatoria": "⚪", "aleatoria": "⚪"}.get(origem.get(d, "aleatoria"), "⚪")
                display.append(f"{tag} {d:02d}")
            st.markdown(f"🎯 **Jogo {idx} ({len(jogo)} dezenas):** {' '.join(display)}")

        # dados do bolão e geração de PDF/salvamento final
        st.markdown("---")
        st.subheader("💬 Dados do Bolão")
        participantes_input = st.text_input("👥 Participantes (separe por vírgulas)", value=st.session_state.get("participantes", "Participante 01, Participante 02, Participante 03"))
        st.session_state["participantes"] = participantes_input
        pix_input = st.text_input("💸 Chave PIX para rateio", value=st.session_state.get("pix", "marcosmigueloliveira@yahoo.com.br"))
        st.session_state["pix"] = pix_input

        participantes_lista = [p.strip() for p in participantes_input.split(",") if p.strip()]
        valor_total = sum(calcular_valor_aposta(len(jogo)) for jogo, _ in jogos)
        valor_por_pessoa = (valor_total / len(participantes_lista)) if participantes_lista else valor_total

        st.subheader("📊 Rateio do Bolão")
        if participantes_lista:
            df_rateio = pd.DataFrame({"Participantes": participantes_lista, "Valor (R$)": [round(valor_por_pessoa, 2)] * len(participantes_lista)})
            st.dataframe(df_rateio, use_container_width=True)
        st.markdown(f"**💰 Valor total:** R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        if st.button("📄 Gerar PDF do Bolão"):
            arquivo_pdf = gerar_pdf_jogos(jogos, nome="Bolão Inteligente", participantes=participantes_input, pix=pix_input)
            codigo_bolao = salvar_bolao_csv(jogos, participantes_input, pix_input, valor_total, valor_por_pessoa, concurso_base=numero_api)
            if codigo_bolao:
                st.success(f"📄 PDF gerado e bolão salvo! Código: {codigo_bolao}")
            with open(arquivo_pdf, "rb") as f:
                st.download_button("⬇️ Baixar PDF", f, file_name=arquivo_pdf)

