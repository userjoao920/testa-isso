import pandas as pd
import vectorbt as vbt
import os
import logging
from flask import Flask
import threading
import time
import gc

# Configuração de log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

app = Flask(__name__)
backtest_rodando = False

def testar_ma(fast, slow, close):
    if fast >= slow:
        return None
    try:
        fast_ma = vbt.MA.run(close, window=fast).ma
        slow_ma = vbt.MA.run(close, window=slow).ma

        cross_up = fast_ma.vbt.crossed_above(slow_ma)
        cross_down = fast_ma.vbt.crossed_below(slow_ma)

        portfolio = vbt.Portfolio.from_signals(
            close,
            entries=cross_up,
            exits=cross_down,
            short_entries=cross_down,
            short_exits=cross_up,
            init_cash=100,
            fees=0.001,
            slippage=0.0
        )
        saldo = portfolio.value().iloc[-1]

        # Limpeza de memória
        del fast_ma, slow_ma, cross_up, cross_down, portfolio
        gc.collect()

        return saldo
    except Exception as e:
        logging.warning(f"Erro em fast={fast}, slow={slow}: {e}")
        return None

def rodar_backtest():
    logging.info("Baixando dados...")
    data = vbt.CCXTData.download(
        symbols='PEPE/USDT',
        exchange='mexc',
        timeframe='15m',
        start='2024-11-01',
        end='2025-04-29',
        show_progress=True
    )
    close = data.get('Close')
    logging.info("Download finalizado.")

    fast_range = range(1, 201)
    slow_range = range(2, 202)
    total = sum(1 for f in fast_range for s in slow_range if f < s)
    testados = 0
    resultados = []

    inicio = time.time()
    logging.info("Iniciando backtest...")

    for fast in fast_range:
        for slow in slow_range:
            if fast >= slow:
                continue

            saldo = testar_ma(fast, slow, close)
            testados += 1

            if saldo is not None:
                resultados.append({'fast': fast, 'slow': slow, 'saldo': saldo})

                if len(resultados) > 30:
                    resultados = sorted(resultados, key=lambda x: x['saldo'], reverse=True)[:30]

            if testados % 100 == 0:
                tempo = int((time.time() - inicio) // 60)
                restantes = total - testados
                logging.info(f"Testados: {testados}/{total} - Restantes: {restantes} - Tempo: {tempo} min")

            gc.collect()

    df = pd.DataFrame(resultados)
    df.to_csv("top30.csv", index=False)

    logging.info("Backtest concluído! Top 30 combinações:")
    for r in resultados:
        logging.info(f"Fast: {r['fast']}, Slow: {r['slow']}, Saldo: {r['saldo']:.2f}")

@app.route("/")
def home():
    global backtest_rodando
    if not backtest_rodando:
        threading.Thread(target=rodar_backtest, daemon=True).start()
        backtest_rodando = True
        logging.info("Backtest iniciado em segundo plano.")
    return "<h1>Bot de backtest em execução...</h1>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
