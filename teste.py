import ccxt
import pandas as pd
import numpy as np
from flask import Flask
import threading
import os
import logging
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm

# Configuração de log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

bot_status = "Iniciando o backtest..."  # Status inicial

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

    balance = 1000  # saldo inicial
    position = 0  # quantidade de tokens (positivo = comprado, negativo = vendido)
    entry_price = 0
    fee = 0.0006  # 0.06% taxa da Binance Futuros normal, pode mudar se quiser

    for i in range(max(short_window, long_window), len(df)):
        price = df['close'].iloc[i]

        # Sinal de cruzamento
        if short_sma.iloc[i] > long_sma.iloc[i]:
            # Cruzou para cima (sinal de compra)
            if position <= 0:  # Se não estiver comprado
                if position < 0:
                    # Fechar short
                    balance += abs(position) * (entry_price - price) * (1 - fee)
                    position = 0

                # Abrir long
                size = (balance * (1 - fee)) / price
                position = size
                entry_price = price

        elif short_sma.iloc[i] < long_sma.iloc[i]:
            # Cruzou para baixo (sinal de venda)
            if position >= 0:  # Se não estiver vendido
                if position > 0:
                    # Fechar long
                    balance += position * (price - entry_price) * (1 - fee)
                    position = 0

                # Abrir short
                size = (balance * (1 - fee)) / price
                position = -size
                entry_price = price

    # Fechar posição aberta no final
    final_price = df['close'].iloc[-1]
    if position > 0:
        balance += position * (final_price - entry_price) * (1 - fee)
    elif position < 0:
        balance += abs(position) * (entry_price - final_price) * (1 - fee)

    return {
        'short_window': short_window,
        'long_window': long_window,
        'balance': balance
    }

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

# Iniciar o backtest em thread separada
threading.Thread(target=backtest, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
