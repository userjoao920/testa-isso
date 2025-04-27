import ccxt
import pandas as pd
import numpy as np
from flask import Flask
import threading
import time
import os
import logging
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm

# Configuração de log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

bot_status = "Iniciando o backtest..."

# Setup da Exchange
exchange = ccxt.mexc({
    'enableRateLimit': True,
})

symbol = 'PEPE/USDC'
timeframe = '15m'
limit = 8000

def fetch_data():
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

df = fetch_data()

def simulate(cross):
    short_window, long_window = cross
    if short_window >= long_window:
        return {'short_window': short_window, 'long_window': long_window, 'balance': -np.inf}
    
    short_sma = df['close'].rolling(window=short_window).mean()
    long_sma = df['close'].rolling(window=long_window).mean()

    closes = df['close'].values
    short_sma_values = short_sma.values
    long_sma_values = long_sma.values

    in_position = False
    position_type = None  # None, 'long', 'short'
    balance = 1000  # saldo em USDC
    token_amount = 0  # quantidade de token comprado
    fee = 0.003  # 0.3% por operação

    for i in range(1, len(df)):
        if np.isnan(short_sma_values[i-1]) or np.isnan(long_sma_values[i-1]):
            continue

        # Cruzamento para cima: abrir LONG
        if short_sma_values[i-1] <= long_sma_values[i-1] and short_sma_values[i] > long_sma_values[i]:
            if position_type == 'short':
                # Fechar short
                balance += token_amount * closes[i] * (1 - fee)
                token_amount = 0
                position_type = None

            if not in_position:
                # Abrir long
                token_amount = (balance * (1 - fee)) / closes[i]
                balance = 0
                in_position = True
                position_type = 'long'

        # Cruzamento para baixo: abrir SHORT
        elif short_sma_values[i-1] >= long_sma_values[i-1] and short_sma_values[i] < long_sma_values[i]:
            if position_type == 'long':
                # Fechar long
                balance += token_amount * closes[i] * (1 - fee)
                token_amount = 0
                position_type = None

            if not in_position:
                # Abrir short
                token_amount = (balance * (1 - fee)) / closes[i]
                balance = 0
                in_position = True
                position_type = 'short'

    # Se terminar ainda posicionado, fechar posição
    if in_position:
        if position_type == 'long':
            balance += token_amount * closes[-1] * (1 - fee)
        elif position_type == 'short':
            balance += token_amount * closes[-1] * (1 - fee)

    return {'short_window': short_window, 'long_window': long_window, 'balance': balance}

results = []
done = False

def backtest():
    global results, bot_status, done
    bot_status = "Baixando candles e preparando o backtest..."
    logger.info(bot_status)

    combinations = [(short, long) for short in range(5, 201) for long in range(5, 201)]

    bot_status = "Executando simulações..."
    logger.info(bot_status)

    with ProcessPoolExecutor() as executor:
        for result in tqdm(executor.map(simulate, combinations), total=len(combinations)):
            results.append(result)

    results.sort(key=lambda x: x['balance'], reverse=True)

    logger.info("TOP 5 melhores combinações:")
    for res in results[:5]:
        logger.info(res)

    bot_status = "Backtest finalizado!"
    done = True

# Iniciar Flask
app = Flask(__name__)

@app.route("/")
def home():
    if not done:
        return f"<h1>Rodando backtest...</h1><p>{bot_status}</p>"
    else:
        melhores = "<br>".join([f"Short: {r['short_window']} / Long: {r['long_window']} - Resultado: {r['balance']:.2f} USDC" for r in results[:5]])
        return f"<h1>Backtest Concluído!</h1><p>{melhores}</p>"

threading.Thread(target=backtest, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
