import pandas as pd
import random
import logging
from collections import defaultdict 

# Configuração de Log
logging.basicConfig(level=logging.INFO, format="🔄 %(message)s")

# Colunas esperadas no CSV para as dezenas sorteadas
DEZENAS_COLS = [f"Bola{i}" for i in range(1, 16)] 

def carregar_dados(file_path):
    """Carrega os dados de concursos da Lotofácil a partir de um arquivo CSV."""
    logging.info("Iniciando leitura do arquivo...")

    try:
        # CORREÇÃO CRÍTICA: Alterado sep=";" para sep=","
        df = pd.read_csv(file_path, sep=",", engine="python", encoding="latin1") 

        # Remove linhas completamente vazias 
        df = df.dropna(how="all")

        # Verifica se as colunas de dezenas necessárias existem
        if not all(col in df.columns for col in DEZENAS_COLS):
            # Este log agora será desnecessário se o CSV for lido corretamente
            logging.error(f"❌ O arquivo CSV não contém as colunas de dezenas esperadas ({DEZENAS_COLS[0]} a {DEZENAS_COLS[-1]}).")
            logging.error(f"   Colunas encontradas no arquivo: {list(df.columns)}")
            return None
        
        logging.info(f"✅ Arquivo carregado com sucesso! Total de concursos: {len(df)}")
        return df

    except FileNotFoundError:
        logging.error(f"❌ Arquivo '{file_path}' não encontrado no diretório do projeto.")
        return None
    except pd.errors.ParserError as pe:
         logging.error(f"❌ Erro de parseamento do CSV. Tente verificar o delimitador e a codificação. Erro: {pe}")
         return None
    except Exception as e:
        logging.error(f"❌ Erro geral ao processar o arquivo: {e}")
        return None

def calcular_frequencia(df, ultimos):
    """Calcula a frequência de todas as dezenas nos últimos 'ultimos' concursos."""
    if df is None or df.empty:
        return pd.Series(dtype=int)

    df_ultimos = df.tail(ultimos).copy()
    
    # Empilha as colunas de dezenas em uma única série para contagem de frequência
    todas_dezenas = df_ultimos[DEZENAS_COLS].stack()
    
    # Conta a frequência, garantindo que o índice é int e ordenando por mais frequente
    frequencia = todas_dezenas.value_counts().sort_values(ascending=False).astype(int)
    
    return frequencia

def selecionar_dezenas(df, qtd=18, ultimos=50):
    """Retorna a lista das 'qtd' dezenas mais frequentes e o ranking completo."""
    frequencia = calcular_frequencia(df, ultimos)
    
    # Lista dos números mais frequentes
    dezenas_sugeridas = frequencia.head(qtd).index.tolist()
    
    return dezenas_sugeridas, frequencia

def gerar_jogos(numeros_sugeridos, qtd_15=0, qtd_16=0, qtd_17=0, qtd_18=0, jogos_fixos=None):
    """Gera jogos aleatórios com base nos números sugeridos, com jogos fixos (15 dezenas) como base."""
    jogos = []
    
    # Adiciona jogos fixos primeiro
    if jogos_fixos:
        for jogo in jogos_fixos:
            # Verifica se o jogo fixo tem entre 15 e 18 dezenas
            if 15 <= len(jogo) <= 18:
                jogos.append(sorted(jogo))

    contadores = {15: qtd_15, 16: qtd_16, 17: qtd_17, 18: qtd_18}
    
    # Gera os jogos aleatórios
    for tamanho in sorted(contadores.keys(), reverse=True):
        for _ in range(contadores[tamanho]):
            if len(numeros_sugeridos) >= tamanho:
                # Gera um jogo de 'tamanho' dezenas a partir das 'numeros_sugeridos'
                jogos.append(sorted(random.sample(numeros_sugeridos, tamanho)))
            else:
                logging.warning(f"⚠️ Não há dezenas suficientes ({len(numeros_sugeridos)}) para gerar um jogo de {tamanho}.")

    return jogos

def avaliar_jogos(jogos, df_concursos):
    """Avalia os jogos gerados contra o histórico de concursos, contando as ocorrências de acertos."""
    logging.info("🔄 Avaliando jogos contra concursos anteriores...")
    
    resultados_finais = []
    
    # Prepara o histórico de resultados em um formato de lista de conjuntos
    historico_sets = [set(row) for row in df_concursos[DEZENAS_COLS].values.astype(int)]
    
    for idx, jogo in enumerate(jogos, 1):
        jogo_set = set(jogo)
        contagens = defaultdict(int) 
        
        for concurso_set in historico_sets:
            acertos = len(jogo_set.intersection(concurso_set))
            
            # Só contamos 11 acertos ou mais (os prêmios)
            if acertos >= 11:
                contagens[acertos] += 1
                
        # Converte o defaultdict para um dicionário normal para exibição
        resultados_finais.append((idx, jogo, dict(contagens)))
        
    logging.info("✅ Avaliação concluída.")
    return resultados_finais

