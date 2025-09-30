import pandas as pd
import random
import logging
from collections import defaultdict # Útil para contagem

# Configuração do log (o Streamlit usará isso)
logging.basicConfig(level=logging.INFO, format="🔄 %(message)s")

# Colunas esperadas no CSV para as dezenas sorteadas
DEZENAS_COLS = [f"Bola{i}" for i in range(1, 16)] 

def carregar_dados(file_path):
    """Carrega os dados de concursos da Lotofácil a partir de um arquivo CSV."""
    logging.info("Iniciando leitura do arquivo...")

    try:
        # Tenta carregar o arquivo CSV com detecção automática de separador
        # Assume-se que o arquivo Lotofacil.csv está no diretório raiz do projeto
        df = pd.read_csv(file_path, sep=None, engine="python", encoding="latin1")

        # Verifica se as colunas de dezenas necessárias existem
        if not all(col in df.columns for col in DEZENAS_COLS):
            logging.error("❌ O arquivo CSV não contém as colunas de dezenas esperadas (ex: Bola1, Bola2...).")
            return None

        # Remove linhas vazias ou quebradas
        df = df.dropna(how="all")

        logging.info(f"✅ Arquivo carregado com sucesso! Total de concursos: {len(df)}")
        return df

    except Exception as e:
        logging.error(f"❌ Erro ao carregar o arquivo: {e}")
        return None

def selecionar_dezenas(df, qtd=18, ultimos=50):
    """Calcula as 'qtd' dezenas mais frequentes nos últimos 'ultimos' concursos."""
    if df is None or df.empty:
        return list(range(1, qtd + 1)) # Retorna um padrão se não houver dados

    logging.info(f"🔄 Calculando frequência nas últimas {ultimos} colunas...")
    
    # Seleciona apenas os últimos concursos e as colunas de dezenas
    df_ultimos = df.tail(ultimos)
    
    # Empilha as colunas de dezenas em uma única série para contagem de frequência
    todas_dezenas = df_ultimos[DEZENAS_COLS].stack()
    
    # Conta a frequência e seleciona as 'qtd' mais frequentes
    # O index são os números da dezena
    frequencia = todas_dezenas.value_counts().head(qtd)
    
    # Retorna apenas a lista dos números (índices) mais frequentes
    return frequencia.index.astype(int).tolist() # Garante que são inteiros

def gerar_jogos(numeros_sugeridos, qtd_15=0, qtd_16=0, qtd_17=0, qtd_18=0, jogos_fixos=None):
    """Gera jogos aleatórios com base nos números sugeridos."""
    jogos = []
    
    # Adiciona jogos fixos primeiro
    if jogos_fixos:
        for jogo in jogos_fixos:
            if len(jogo) == 15: # Apenas jogos de 15 dezenas são suportados como fixos para simplificação
                jogos.append(sorted(jogo))

    logging.info("🔄 Gerando jogos...")
    
    contadores = {15: qtd_15, 16: qtd_16, 17: qtd_17, 18: qtd_18}
    
    for tamanho in sorted(contadores.keys(), reverse=True):
        for _ in range(contadores[tamanho]):
            if len(numeros_sugeridos) >= tamanho:
                jogos.append(sorted(random.sample(numeros_sugeridos, tamanho)))
            else:
                logging.warning(f"⚠️ Não há dezenas suficientes ({len(numeros_sugeridos)}) para gerar um jogo de {tamanho}.")

    logging.info(f"✅ Total de jogos gerados: {len(jogos)}")
    return jogos

def avaliar_jogos(jogos, df_concursos):
    """Avalia os jogos gerados contra o histórico de concursos, contando as ocorrências de acertos."""
    logging.info("🔄 Avaliando jogos contra concursos anteriores...")
    
    resultados_finais = []
    
    # Prepara o histórico de resultados em um formato de lista de conjuntos
    # Usa a constante DEZENAS_COLS para garantir as colunas corretas
    historico_sets = [set(row) for row in df_concursos[DEZENAS_COLS].values.astype(int)]
    
    for idx, jogo in enumerate(jogos, 1):
        jogo_set = set(jogo)
        contagens = defaultdict(int) # Dicionário para contar 11, 12, 13, 14 e 15 acertos
        
        for concurso_set in historico_sets:
            # Calcula quantos números do jogo gerado estão no concurso
            acertos = len(jogo_set.intersection(concurso_set))
            
            # Só contamos 11 acertos ou mais (os prêmios)
            if acertos >= 11:
                contagens[acertos] += 1
                
        # Converte o defaultdict para um dicionário normal para exibição
        resultados_finais.append((idx, jogo, dict(contagens)))
        
    logging.info("✅ Avaliação concluída.")
    return resultados_finais

