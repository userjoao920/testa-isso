import ccxt
import numpy as np
import pandas as pd
import time
from datetime import datetime

# Definir o cliente ccxt para acessar dados de mercado da MEXC
exchange = ccxt.mexc()

# Configurações do backtest
symbol = 'PEPE/USDT'
timeframe = '15m'  # Intervalo de 15 minutos
max_candles = 8000  # Últimos 8000 candles
initial_capital = 1000  # Capital inicial
best_results = []

# Função para buscar os dados históricos de candles
def get_candles():
    # Recuperando os últimos 8000 candles (de acordo com a API da MEXC)
    candles = exchange.fetch_ohlcv(symbol, timeframe, limit=max_candles)
    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Função de cálculo das médias móveis
def moving_average(data, period):
    return data['close'].rolling(window=period).mean()

# Função para calcular o retorno e atualizar o capital com juros compostos
def calculate_return(initial_balance, trades):
    balance = initial_balance
    for trade in trades:
        balance *= (1 + trade)  # Calculando o capital com juros compostos
    return balance

# Função para executar o backtest e testar diferentes combinações de médias móveis
def backtest():
    df = get_candles()
    best_results.clear()
    total_combinations = (200 - 5 + 1) ** 2  # Testando médias de 5 a 200 para as duas médias
    completed = 0  # Contador de progresso

    for short_period in range(5, 201):  # Média rápida de 5 a 200
        for long_period in range(5, 201):  # Média devagar de 5 a 200
            if short_period >= long_period:
                continue  # Média rápida deve ser menor que a média devagar

            short_ma = moving_average(df, short_period)
            long_ma = moving_average(df, long_period)

            capital = initial_capital
            trades = []  # Lista de resultados de operações
            position = None  # A posição pode ser None, 'long' ou 'short'

            # Loop para simular as operações de compra e venda
            for i in range(max(short_period, long_period), len(df)):
                if short_ma[i] > long_ma[i] and position != 'long':  # Cruzamento de alta (compra)
                    if position == 'short':  # Fechar a posição vendida
                        profit = (df['close'][i] - entry_price) / entry_price
                        trades.append(profit)
                    position = 'long'
                    entry_price = df['close'][i]
                elif short_ma[i] < long_ma[i] and position != 'short':  # Cruzamento de baixa (venda)
                    if position == 'long':  # Fechar a posição comprada
                        profit = (entry_price - df['close'][i]) / entry_price
                        trades.append(profit)
                    position = 'short'
                    entry_price = df['close'][i]

            # Calculando o retorno total com juros compostos
            final_balance = calculate_return(initial_capital, trades)
            best_results.append((short_period, long_period, final_balance))

            # Atualizar o progresso
            completed += 1
            progress = (completed / total_combinations) * 100
            print(f"Progresso: {progress:.2f}%")

    # Ordenar os resultados e retornar os 5 melhores
    best_results.sort(key=lambda x: x[2], reverse=True)
    return best_results[:5]

# Função para exibir os melhores resultados
def display_best_results():
    print("\nTop 5 Melhores Resultados:")
    for idx, (short_period, long_period, final_balance) in enumerate(best_results, 1):
        print(f"{idx}. Média Rápida: {short_period}, Média Devagar: {long_period}, Saldo Final: {final_balance:.2f} USDT")

# Executar o backtest e exibir os melhores resultados
print("Iniciando o backtest...")
start_time = time.time()
top_results = backtest()
end_time = time.time()

print(f"\nBacktest concluído em {end_time - start_time:.2f} segundos")
display_best_results()
