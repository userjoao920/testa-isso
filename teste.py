import ccxt
import pandas as pd
import numpy as np
import time

# Inicializar ccxt para pegar dados da MEXC
exchange = ccxt.mexc()

# Configurações
symbol = 'PEPE/USDC'
timeframe = '15m'
limit = 8000  # Máximo de candles

print("Baixando dados...")
ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
print("Dados baixados com sucesso!")

# Organizar os dados em DataFrame
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)

# Função para executar o backtest
def backtest(ma_rapida, ma_lenta):
    saldo = 100  # saldo inicial em USDC
    posicao = None  # 'buy' ou 'sell'
    preco_entrada = 0

    df['ma_rapida'] = df['close'].rolling(ma_rapida).mean()
    df['ma_lenta'] = df['close'].rolling(ma_lenta).mean()

    for i in range(max(ma_rapida, ma_lenta), len(df)):

        preco_atual = df['close'].iloc[i]
        ma_r = df['ma_rapida'].iloc[i]
        ma_l = df['ma_lenta'].iloc[i]

        if np.isnan(ma_r) or np.isnan(ma_l):
            continue

        if ma_r > ma_l:
            # Sinal de compra
            if posicao == 'sell':
                # Fecha venda
                percentual = (preco_entrada - preco_atual) / preco_entrada
                saldo = saldo * (1 + percentual)
                posicao = None
            if posicao is None:
                # Abre compra
                preco_entrada = preco_atual
                posicao = 'buy'

        elif ma_r < ma_l:
            # Sinal de venda
            if posicao == 'buy':
                # Fecha compra
                percentual = (preco_atual - preco_entrada) / preco_entrada
                saldo = saldo * (1 + percentual)
                posicao = None
            if posicao is None:
                # Abre venda
                preco_entrada = preco_atual
                posicao = 'sell'

    # Fecha a última operação se ainda aberta
    if posicao == 'buy':
        percentual = (df['close'].iloc[-1] - preco_entrada) / preco_entrada
        saldo = saldo * (1 + percentual)
    elif posicao == 'sell':
        percentual = (preco_entrada - df['close'].iloc[-1]) / preco_entrada
        saldo = saldo * (1 + percentual)

    return saldo

# Testar todas combinações
resultados = []
total_testes = (200 - 5 + 1) ** 2
testes_concluidos = 0
progresso_aviso = 0

inicio_tempo = time.time()

for ma_rapida in range(5, 201):
    for ma_lenta in range(5, 201):
        if ma_rapida >= ma_lenta:
            continue  # Só interessa se a rápida for menor que a lenta

        saldo_final = backtest(ma_rapida, ma_lenta)
        resultados.append({
            'ma_rapida': ma_rapida,
            'ma_lenta': ma_lenta,
            'saldo_final': saldo_final
        })

        testes_concluidos += 1
        progresso_atual = int((testes_concluidos / total_testes) * 100)

        if progresso_atual >= progresso_aviso + 10:
            progresso_aviso = progresso_atual
            tempo_passado = (time.time() - inicio_tempo) / 60  # minutos
            print(f"Progresso: {progresso_atual}% - Tempo decorrido: {tempo_passado:.2f} min")

# Ordenar resultados
resultados_ordenados = sorted(resultados, key=lambda x: x['saldo_final'], reverse=True)

# Mostrar top 10
print("\nTop 10 melhores combinações:")
for idx, r in enumerate(resultados_ordenados[:10]):
    print(f"{idx+1}: Rápida {r['ma_rapida']} | Lenta {r['ma_lenta']} | Saldo final: {r['saldo_final']:.2f} USDC")
