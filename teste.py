import ccxt
import pandas as pd
import time
import itertools
import logging
from flask import Flask
import multiprocessing

# Configuração de log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Inicializar o Flask
app = Flask(__name__)

# Função para pegar dados da MEXC com mais de 1.000 candles
def pegar_dados_mexc(par='PEPE/USDC', timeframe='15m', candles=8000):
    exchange = ccxt.mexc()
    agora = exchange.milliseconds()
    desde = agora - candles * 15 * 60 * 1000  # Calcula o início do período com base no número de candles

    all_ohlcv = []
    limite = 1000  # Limite de 1.000 candles por requisição

    while len(all_ohlcv) < candles:
        ohlcv = exchange.fetch_ohlcv(par, timeframe=timeframe, since=desde, limit=limite)
        
        if not ohlcv:
            logger.error(f"Nenhum dado retornado. Verifique o par de moedas ou o intervalo de tempo.")
            break
        
        all_ohlcv += ohlcv
        desde = ohlcv[-1][0] + 1  # Avança para o próximo lote de candles
        time.sleep(0.5)  # Aguarda meio segundo entre as requisições para evitar limites da API

    if all_ohlcv:  # Verifica se há dados para converter
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    else:
        return None

# Função de backtest
def backtest(df, sma_curta, sma_longa, taxa=0.003, capital_inicial=1000.0):
    data = df.copy()
    data['sma_curta'] = data['close'].rolling(window=sma_curta).mean()
    data['sma_longa'] = data['close'].rolling(window=sma_longa).mean()

    capital = capital_inicial
    posicao = 0  # O valor que está sendo investido na moeda
    saldo_final = capital

    for i in range(1, len(data)):
        if pd.isna(data['sma_curta'].iloc[i]) or pd.isna(data['sma_longa'].iloc[i]):
            continue

        preco_atual = data['close'].iloc[i]
        sma_curta_atual = data['sma_curta'].iloc[i]
        sma_longa_atual = data['sma_longa'].iloc[i]
        sma_curta_ant = data['sma_curta'].iloc[i-1]
        sma_longa_ant = data['sma_longa'].iloc[i-1]

        # Compra quando a SMA curta cruza acima da SMA longa
        if sma_curta_ant < sma_longa_ant and sma_curta_atual > sma_longa_atual and posicao == 0:
            posicao = capital * (1 - taxa) / preco_atual  # Compra toda a quantidade de moeda disponível
            capital = 0  # O capital foi usado para a compra

        # Vende quando a SMA curta cruza abaixo da SMA longa
        elif sma_curta_ant > sma_longa_ant and sma_curta_atual < sma_longa_atual and posicao > 0:
            capital = posicao * preco_atual * (1 - taxa)  # Vende toda a posição
            posicao = 0  # Não há mais posição aberta

    # Se ainda houver uma posição aberta, vende no último preço disponível
    if posicao > 0:
        capital = posicao * data['close'].iloc[-1] * (1 - taxa)

    return (sma_curta, sma_longa, capital)

# Função para rodar os backtests
def rodar_backtests(df, params_list):
    results = []
    for params in params_list:
        results.append(backtest(df, *params))
    
    # Filtrar e ordenar resultados
    results = [r for r in results if r is not None]
    results.sort(key=lambda x: x[2], reverse=True)

    return results

# Função principal para executar o backtest
def rodar_backtest_em_segundo_plano():
    df = pegar_dados_mexc(par='PEPE/USDC', timeframe='15m', candles=8000)

    if df is None or len(df) == 0:
        logger.error("Falha ao obter dados suficientes da MEXC.")
        return

    logger.info(f"Dados recebidos: {len(df)} candles")

    # Gerar combinações de SMA curta e longa com intervalos de 5 até 200
    params_list = list(itertools.product(range(5, 201), repeat=2))

    logger.info("Rodando backtests, isso pode levar alguns minutos...")
    results = rodar_backtests(df, params_list)

    # Mostrar Top 5 melhores configurações
    logger.info("\nTop 5 melhores configurações encontradas:\n")
    melhores_resultados = []
    for sma_curta, sma_longa, saldo_final in results[:5]:
        melhores_resultados.append(f"SMA curta: {sma_curta}, SMA longa: {sma_longa}, Saldo final: {saldo_final:.2f} USDC")
        logger.info(f"SMA curta: {sma_curta}, SMA longa: {sma_longa}, Saldo final: {saldo_final:.2f} USDC")
    
    return melhores_resultados

# Variável global para armazenar os melhores resultados
melhores_resultados = []

@app.route("/")
def home():
    global melhores_resultados
    if melhores_resultados:
        melhores = "<br>".join(melhores_resultados)
        return f"<h1>Backtest Concluído!</h1><p>{melhores}</p>"
    else:
        return "<h1>Rodando backtest...</h1><p>Isso pode levar algum tempo, aguarde!</p>"

# Rodar o backtest em segundo plano como um processo separado
def iniciar_backtest():
    global melhores_resultados
    melhores_resultados = rodar_backtest_em_segundo_plano()

if __name__ == "__main__":
    # Rodar o backtest em processo separado
    p = multiprocessing.Process(target=iniciar_backtest)
    p.start()
    
    # Iniciar o servidor Flask
    app.run(host="0.0.0.0", port=10000)
