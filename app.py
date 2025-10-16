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
        # Necessita da biblioteca 'github' e da variável de ambiente GH_TOKEN configuradas no Streamlit
        resultado = atualizar_csv_github() 
    st.success(resultado)
    st.rerun()  # ✅ recarrega automaticamente após atualização

file_path = "Lotofacil.csv"
# Tenta carregar o arquivo CSV (este arquivo deve estar no seu repositório/Streamlit Cloud)
df = carregar_dados(file_path)

if df is None:
    st.error("❌ Erro ao carregar os concursos! Verifique se 'Lotofacil.csv' está presente.")
    st.stop()
else:
    st.success(f"✅ Concursos carregados: {len(df)}")

# Obter o último concurso da API para exibir
dados_api = obter_concurso_atual_api()
numero_api = dados_api.get("numero", "N/A") if dados_api else "N/A"
dezenas_api = dados_api.get("dezenas", []) if dados_api else []

st.markdown(f"**Último Concurso (API Caixa):** **{numero_api}** | Data: {dados_api.get('dataApuracao', 'N/A') if dados_api else 'N/A'}")
if dezenas_api:
    st.markdown(f"**Dezenas sorteadas:** {' '.join(str(d).zfill(2) for d in sorted(dezenas_api))}")
st.markdown("---")


# ---------------------------
# Geração de Jogos
# ---------------------------
st.header("🔮 Gerar Jogos Inteligentes")

# Sidebar para configurações
with st.sidebar:
    st.header("⚙️ Configurações do Jogo")
    qtd_jogos = st.number_input("Total de Jogos a Gerar:", min_value=1, max_value=20, value=4)
    
    # Opções de tamanho: 15 (aposta mínima) até 20
    tamanho_jogo = st.select_slider(
        "Tamanho da Aposta (Qtd. de Dezenas):",
        options=list(range(15, 21)),
        value=15
    )
    
    valor_aposta = calcular_valor_aposta(tamanho_jogo)
    st.markdown(f"**Valor por Jogo:** R$ {valor_aposta:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    # Se o valor total do bolão for muito alto, emite um aviso
    valor_total_estimado = qtd_jogos * valor_aposta
    if valor_total_estimado > 500:
        st.warning(f"⚠️ O valor total dos jogos é R$ {valor_total_estimado:,.2f}.".replace(",", "X").replace(".", ",").replace("X", "."))
        
    st.markdown("---")

if st.button(f"✨ Gerar {qtd_jogos} Jogos de {tamanho_jogo} Dezenas"):
    with st.spinner("Gerando jogos..."):
        # A função gerar_jogos_balanceados agora recebe o DF (histórico) e faz o cálculo interno
        jogos_gerados = gerar_jogos_balanceados(df, qtd_jogos=qtd_jogos, tamanho=tamanho_jogo)
    
    st.session_state["jogos_gerados"] = jogos_gerados
    st.session_state["tamanho_jogo"] = tamanho_jogo
    st.session_state["mostrar_jogos"] = True

if st.session_state.get("mostrar_jogos", False) and st.session_state.get("jogos_gerados"):
    jogos = st.session_state["jogos_gerados"]
    tamanho_jogo = st.session_state["tamanho_jogo"]
    
    st.subheader(f"🔢 Seus Jogos Gerados ({tamanho_jogo} Dezenas)")
    
    # Exibir jogos
    df_jogos = pd.DataFrame({
        "Jogo": range(1, len(jogos) + 1),
        "Dezenas": [" ".join(str(d).zfill(2) for d in jogo) for jogo, _ in jogos],
        "Origem": [str(origem) for _, origem in jogos],
        "Tamanho": [len(jogo) for jogo, _ in jogos]
    })
    st.dataframe(df_jogos[["Jogo", "Dezenas", "Tamanho"]].to_markdown(index=False), use_container_width=True)

    # ---------------------------
    # Avaliação Histórica
    # ---------------------------
    st.header("📜 Avaliação no Histórico")
    with st.spinner("Avaliando jogos contra o histórico..."):
        # A função avalia os jogos (lista de listas de dezenas) contra o DF de concursos
        df_avaliacao = avaliar_jogos_historico(df, jogos)
    
    st.markdown(f"**Acertos que seus jogos teriam feito em {len(df)} concursos:**")
    st.dataframe(df_avaliacao.to_markdown(index=False), use_container_width=True)
    
    st.markdown("---")
    
    # ---------------------------
    # Bolão e PDF
    # ---------------------------
    st.header("🤝 Bolão (PIX e PDF)")
    
    # Inicializa variáveis de sessão para manter os valores
    if "participantes" not in st.session_state:
        st.session_state["participantes"] = "Participante 01, Participante 02, Participante 03"
    if "pix" not in st.session_state:
        st.session_state["pix"] = ""

    with st.form("form_bolao"):
        participantes_input = st.text_input("👥 Nomes dos Participantes (separados por vírgula)", 
                                           value=st.session_state.get("participantes", "Participante 01, Participante 02, Participante 03"))
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

        if st.form_submit_button("📄 Gerar PDF e Salvar Bolão"):
            # 1. Gerar PDF localmente (no Streamlit Cloud, ele não persiste, mas pode ser baixado)
            arquivo_pdf = gerar_pdf_jogos(jogos, nome="Bolão Inteligente", participantes=participantes_input, pix=pix_input)
            
            # 2. Tentar salvar o bolão no CSV do GitHub
            codigo_bolao = salvar_bolao_csv(jogos, participantes_input, pix_input, valor_total, valor_por_pessoa, concurso_base=numero_api)
            
            # 3. Exibir resultados
            if codigo_bolao.startswith("❌"):
                 st.error(f"Erro ao salvar bolão no GitHub. Verifique GH_TOKEN. {codigo_bolao}")
            else:
                 st.success(f"✅ Bolão salvo! Código: {codigo_bolao}")

            # 4. Oferecer o download do PDF
            with open(arquivo_pdf, "rb") as file:
                st.download_button(
                    label="Baixar PDF",
                    data=file,
                    file_name=arquivo_pdf,
                    mime="application/pdf"
                )

# ---------------------------
# Estatísticas
# ---------------------------
st.header("📈 Estatísticas do Histórico")
tab_freq, tab_atraso, tab_pares, tab_comb = st.tabs(["Frequência", "Atrasos", "Pares/Ímpares", "Combinações"])

# --- Frequência
with tab_freq:
    st.subheader("Frequência de Saída das Dezenas")
    
    # Calcular Frequência
    df_frequencia = calcular_frequencia(df)
    
    # Normalizar Frequência
    max_freq = df_frequencia["Frequência"].max()
    df_frequencia["%"] = (df_frequencia["Frequência"] / max_freq * 100).round(2).astype(str) + "%"
    
    st.dataframe(df_frequencia.to_markdown(index=False), use_container_width=True)
    
    # Exibir Dezenas que nunca saíram (se houver - improvável na Lotofácil)
    dezenas_presentes = set(df_frequencia["Dezena"].tolist())
    dezenas_faltantes = sorted(list(set(range(1, 26)) - dezenas_presentes))
    if dezenas_faltantes:
        st.warning(f"⚠️ Dezenas que nunca saíram no histórico: {dezenas_faltantes}")

# --- Atrasos
with tab_atraso:
    st.subheader("Atraso Atual e Máximo")
    
    # Calcular Atrasos
    # Certifique-se que o df está ordenado por concurso ANTES de calcular o atraso, 
    # se a função calcular_atrasos não o fizer internamente de forma robusta.
    df_atrasos = calcular_atrasos(df)
    st.dataframe(df_atrasos.to_markdown(index=False), use_container_width=True)
    
    # Análise de tendência (Opcional - exemplo)
    max_atual = df_atrasos["Atraso Atual"].max()
    dezena_max = df_atrasos.iloc[0]["Dezena"]
    st.info(f"A dezena mais atrasada é a **{dezena_max}** com **{max_atual}** concursos sem sair.")

# --- Pares/Ímpares
with tab_pares:
    st.subheader("Pares vs. Ímpares Mais Comuns")
    # Calcular Pares/Ímpares
    df_pares_impares = calcular_pares_impares(df)
    st.dataframe(df_pares_impares.to_markdown(index=False), use_container_width=True)

# --- Combinações
with tab_comb:
    st.subheader("Sequências (Números Consecutivos)")
    df_sequencias = calcular_sequencias(df)
    st.dataframe(df_sequencias.to_markdown(index=False), use_container_width=True)

    st.subheader("Combinações de 2 Dezenas Mais Repetidas")
    df_combinacoes = analisar_combinacoes_repetidas(df)
    st.dataframe(df_combinacoes.to_markdown(index=False), use_container_width=True)
