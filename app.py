import streamlit as st
import pandas as pd
# Importa apenas as funções necessárias do seu módulo de lógica
from lotofacil import carregar_dados, selecionar_dezenas, gerar_jogos, avaliar_jogos

st.set_page_config(page_title="Lotofácil Inteligente", page_icon="🎲", layout="wide")

st.title("🎲 Gerador Lotofácil Inteligente")

# --- Configurações Iniciais ---
# Cache para evitar recarregar o arquivo a cada interação
@st.cache_data
def load_data(file_path):
    return carregar_dados(file_path)

df = load_data("Lotofacil.csv")

if df is None:
    st.error("❌ Erro ao carregar os concursos! Verifique se 'Lotofacil.csv' está na pasta raiz e se o formato das colunas está correto (Bola1 a Bola15).")
    st.stop()
else:
    st.success(f"✅ Concursos carregados: {len(df)}")
    # Colunas de dezenas para avaliação
    DEZENAS_COLS = [f"Bola{i}" for i in range(1, 16)]
    df_concursos = df[DEZENAS_COLS]

# --- Sidebar para Configurações ---
st.sidebar.header("⚙️ Configurações de Análise")
ultimos_concursos = st.sidebar.slider(
    "Base de Análise (Últimos Concursos)",
    min_value=50, max_value=len(df), value=100, step=10
)
qtd_dezenas_base = st.sidebar.slider(
    "Dezenas Base Sugeridas",
    min_value=15, max_value=25, value=18, step=1
)

# --- Processamento Central (Base de Sugestão) ---
# 'selecionar_dezenas' retorna a lista de dezenas_base e o ranking completo
dezenas_base, ranking_frequencia = selecionar_dezenas(df, qtd=qtd_dezenas_base, ultimos=ultimos_concursos)

# --- Explicação do Critério ---
st.subheader("💡 Base de Sugestão e Critérios")

# 1. Tabela do Ranking
col_ranking, col_fixas = st.columns([1, 2])

with col_ranking:
    st.markdown(f"**Top {qtd_dezenas_base} Dezenas Mais Frequentes** (Últimos {ultimos_concursos} Concursos)")
    
    # Cria um DataFrame de ranking para exibição
    df_ranking = ranking_frequencia.reset_index()
    df_ranking.columns = ['Dezena', 'Frequência']
    st.dataframe(df_ranking.head(qtd_dezenas_base), use_container_width=True, hide_index=True)

with col_fixas:
    st.markdown("---")
    st.markdown(
        f"""
        O gerador usará essas **{qtd_dezenas_base}** dezenas (listadas ao lado) como o **universo principal** para construir seus jogos. 
        
        Isso garante que todos os jogos gerados focarão nos números 
        que têm a maior probabilidade estatística de serem sorteados, baseados na frequência recente.
        """
    )

# --- Entrada de Dezenas Fixas ---
st.subheader("🎯 Dezenas Fixas Personalizadas")
jogo_fixo_input = st.text_input(
    f"👉 Digite dezenas que **DEVEM** estar em seus jogos (Ex: 1, 3, 25). Use até 15 dezenas.", 
    key="jogo_fixo_input"
)
jogos_fixos_lista = []
if jogo_fixo_input:
    try:
        jogo_fixo = [int(x.strip()) for x in jogo_fixo_input.split(",") if x.strip().isdigit() and 1 <= int(x.strip()) <= 25]
        if 15 < len(jogo_fixo):
             st.warning("Dezenas fixas devem ter no máximo 15 números.")
        elif len(jogo_fixo) > 0:
            jogos_fixos_lista = [jogo_fixo]
            st.info(f"🔒 Jogo Fixo Selecionado: {sorted(jogo_fixo)}")
    except:
        st.error("Formato de dezenas fixas inválido.")

# --- Escolha da Quantidade de Jogos ---
st.subheader("🔢 Quantidade de Jogos a Gerar")
col1, col2, col3, col4 = st.columns(4)

with col1:
    qtd_15 = st.number_input("Jogos de 15 dezenas", min_value=0, max_value=20, value=2)
with col2:
    qtd_16 = st.number_input("Jogos de 16 dezenas", min_value=0, max_value=10, value=0)
with col3:
    qtd_17 = st.number_input("Jogos de 17 dezenas", min_value=0, max_value=5, value=0)
with col4:
    qtd_18 = st.number_input("Jogos de 18 dezenas", min_value=0, max_value=2, value=0)


if st.button("🎲 Gerar e Avaliar Jogos"):
    if qtd_15 + qtd_16 + qtd_17 + qtd_18 == 0 and not jogos_fixos_lista:
        st.warning("Selecione a quantidade de jogos ou defina um jogo fixo.")
    else:
        with st.spinner('Gerando e avaliando...'):
            jogos = gerar_jogos(dezenas_base, qtd_15, qtd_16, qtd_17, qtd_18, jogos_fixos_lista)
            st.success(f"✅ {len(jogos)} jogos gerados!")
            
            # --- Exibição Detalhada dos Jogos ---
            st.markdown("---")
            st.subheader("🎲 Jogos Gerados")
            
            df_jogos = pd.DataFrame(jogos).T.rename(columns=lambda x: f'Jogo {x+1}')
            
            # Formatação para melhor visualização (Transposta e sem índice)
            st.dataframe(df_jogos.T, use_container_width=True, hide_index=False)
            
            st.markdown(
                f"""
                <div style='background-color: #e0f7fa; padding: 15px; border-radius: 10px;'>
                    <p style='font-weight: bold;'>Critério de Geração:</p>
                    <p>Todos os jogos foram gerados a partir do universo de 
                    <span style='font-weight: bold;'>{len(dezenas_base)} dezenas mais frequentes</span> 
                    calculadas nos últimos {ultimos_concursos} concursos. 
                    Isso aumenta a probabilidade de acerto ao usar apenas os números 
                    mais 'quentes' do histórico recente.</p>
                </div>
                """, unsafe_allow_html=True
            )

            # --- Avaliação (contra histórico) ---
            st.markdown("---")
            resultados = avaliar_jogos(jogos, df_concursos)
            st.subheader("📊 Avaliação Histórica (Acertos em Concursos Anteriores)")
            
            for idx, jogo, contagens in resultados:
                
                contagens_formatadas = []
                # Ordena as chaves do dicionário (11, 12, 13, ...)
                for acerto in sorted(contagens.keys()):
                    contagens_formatadas.append(f"**{acerto} acertos**: {contagens[acerto]} vezes")

                # Exibe o resultado de forma clara
                st.markdown(
                    f"""
                    **Jogo {idx}** ({len(jogo)} dezenas): {sorted(jogo)}
                    <br>
                    {' | '.join(contagens_formatadas)}
                    <br>
                    """, unsafe_allow_html=True
                )

            # --- Download em CSV ---
            st.markdown("---")
            csv = df_jogos.T.to_csv(index=False)
            st.download_button("⬇️ Baixar jogos em CSV", csv, "jogos_lotofacil.csv", "text/csv")

