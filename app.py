"""
app.py (Streamlit) - versão reorganizada que usa as funções corridas do lotofacil.py
"""

import streamlit as st
import os
from datetime import datetime
from lf_core import (
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

st.set_page_config(page_title="Lotofácil Inteligente", page_icon="🎲", layout="wide")
st.title("🎲 Painel Lotofácil Inteligente (Atualizado)")

# carregar base
file_path = "Lotofacil_Concursos.csv"
df = carregar_dados(file_path)
if df is None:
    st.error("❌ Erro ao carregar os concursos! Verifique o arquivo 'Lotofacil_Concursos.csv'.")
    st.stop()
else:
    st.success(f"✅ Concursos carregados: {len(df)}")

# tenta obter dados API (silencioso se falhar)
try:
    dados_api = obter_concurso_atual_api()
    if dados_api:
        st.info(f"📅 Último concurso oficial: **{dados_api['numero']}** ({dados_api['dataApuracao']})")
except Exception:
    pass

aba = st.sidebar.radio("📍 Menu Principal", ["📊 Painéis Estatísticos", "🎯 Geração de Jogos"])

# ---------------------------
# Painéis Estatísticos
# ---------------------------
if aba == "📊 Painéis Estatísticos":
    st.header("📊 Painéis Estatísticos da Lotofácil")
    ultimos = st.slider("Selecione quantos concursos deseja analisar:", 50, len(df), len(df))
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📈 Frequência","⏳ Atrasos","⚖️ Pares/Ímpares","🔗 Combinações","➕ Soma","📊 Sequências"])

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
        st.subheader("⚖️ Pares e Ímpares")
        pares_impares = calcular_pares_impares(df)
        st.dataframe(pares_impares, use_container_width=True)

    with tab4:
        st.subheader("🔗 Combinações Repetidas (2..5 dezenas)")
        combos = analisar_combinacoes_repetidas(df)
        for tamanho, tabela in combos.items():
            st.markdown(f"**Top {len(tabela)} combinações ({tamanho} dezenas):**")
            st.dataframe(tabela, use_container_width=True)

    with tab5:
        st.subheader("➕ Soma das Dezenas")
        df_soma, resumo = calcular_soma_total(df)
        col_min, col_med, col_max = st.columns(3)
        col_min.metric("Soma Mínima", f"{resumo['Soma Mínima']}")
        col_med.metric("Soma Média", f"{resumo['Soma Média']:.2f}")
        col_max.metric("Soma Máxima", f"{resumo['Soma Máxima']}")
        st.dataframe(df_soma.tail(), use_container_width=True)
        st.line_chart(df_soma.set_index("Concurso")["Soma"])

    with tab6:
        st.subheader("📊 Sequências detectadas")
        sequencias = calcular_sequencias(df)
        st.bar_chart(sequencias.set_index("Tamanho Sequência")["Ocorrências"])
        st.dataframe(sequencias, use_container_width=True)

# ---------------------------
# Geração de Jogos
# ---------------------------
if aba == "🎯 Geração de Jogos":
    st.header("🎯 Geração de Jogos")
    modo = st.radio("Selecione o tipo de geração:", ["🧠 Geração Inteligente", "📈 Por Desempenho Histórico"])

    if modo == "🧠 Geração Inteligente":
        st.subheader("🧠 Geração Inteligente (balanceada)")
        ranking = calcular_frequencia(df)
        atrasos = calcular_atrasos(df)
        top_atrasadas = atrasos.sort_values("Atraso Atual", ascending=False).head(3)
        top_frequentes = ranking.sort_values("Frequência", ascending=False).head(10)
        col1, col2, col3 = st.columns(3)
        col1.metric("Mais Atrasada", f"{int(top_atrasadas.iloc[0]['Dezena']):02d}", f"{int(top_atrasadas.iloc[0]['Atraso Atual'])} concursos")
        col2.metric("Mais Frequente", f"{int(top_frequentes.iloc[0]['Dezena']):02d}", f"{int(top_frequentes.iloc[0]['Frequência'])} vezes")
        col3.metric("Dezenas Analisadas", "1 a 25", "✅ completo")

        st.markdown("---")
        st.subheader("🎯 Sugestão automática (15 dezenas)")
        jogo_ideal = sorted(set(top_frequentes.head(10)["Dezena"]).union(set(top_atrasadas["Dezena"])))
        if len(jogo_ideal) < 15:
            faltam = 15 - len(jogo_ideal)
            adicionais = [d for d in range(1,26) if d not in jogo_ideal][:faltam]
            jogo_ideal.extend(adicionais)
        st.success("🎲 Jogo sugerido: " + " ".join(f"{int(d):02d}" for d in sorted(jogo_ideal[:15])))

        st.markdown("---")
        st.subheader("🧩 Monte seus próprios jogos")
        qtd_jogos = {tam: st.number_input(f"🎯 Jogos de {tam} dezenas", 0, 50, 0) for tam in range(15,21)}
        total = sum(qtd_jogos.values())
        if total > 0 and st.button("🎲 Gerar Jogos Balanceados"):
            jogos_gerados = []
            for tam,qtd in qtd_jogos.items():
                if qtd>0:
                    jogos_gerados.extend(gerar_jogos_balanceados(df, qtd_jogos=qtd, tamanho=tam))
            st.session_state['jogos_gerados'] = jogos_gerados
            st.success(f"✅ {len(jogos_gerados)} jogos gerados!")
            st.markdown("---")
            st.subheader("📊 Avaliação Histórica dos Jogos")
            avaliacao = avaliar_jogos_historico(df, jogos_gerados)
            st.dataframe(avaliacao, use_container_width=True)

        if 'jogos_gerados' in st.session_state:
            jogos = st.session_state['jogos_gerados']
            st.subheader("🎯 Jogos Gerados")
            legenda = {"quente":"🔵 Quente","fria":"🔴 Atrasada","neutra":"⚪ Neutra"}
            for idx,(jogo, origem) in enumerate(jogos, start=1):
                display = [ f"{'🔵' if origem.get(d)=='quente' else ('🔴' if origem.get(d)=='fria' else '⚪')} {d:02d}" for d in jogo ]
                st.markdown(f"**Jogo {idx} ({len(jogo)} dezenas):** {' '.join(display)}")
                pares = len([d for d in jogo if d%2==0]); impares = len(jogo)-pares; soma = sum(jogo)
                col1,col2,col3 = st.columns(3)
                col1.metric("Pares/Ímpares", f"{pares}/{impares}")
                col2.metric("Soma", soma)
                col3.metric("Tamanho", len(jogo))
            with st.expander("🎨 Legenda das cores", expanded=True):
                for k,v in legenda.items():
                    st.markdown(f"- {v}")

    elif modo == "📈 Por Desempenho Histórico":
        st.subheader("📈 Geração por Desempenho Histórico")
        tamanho = st.selectbox("Tamanho do jogo", [15,16,17,18,19,20])
        faixa = st.selectbox("Faixa de acertos desejada", [11,12,13,14,15])
        qtd = st.number_input("Quantidade de jogos a exibir", 1, 20, 5)
        if st.button("🚀 Buscar Melhores Combinações"):
            with st.spinner("Analisando histórico (amostragem)..."):
                df_mel = gerar_jogos_por_desempenho(df, tamanho_jogo=tamanho, faixa_desejada=faixa, top_n=qtd, sample_candidates=3000)
                if df_mel is None or df_mel.empty:
                    st.info("Nenhuma combinação encontrada na amostragem atual. Aumente sample_candidates ou ajuste parâmetros.")
                else:
                    st.dataframe(df_mel, use_container_width=True)
