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
bot_status = "Bot ainda não iniciou o backtest."

def Testar_ma(fast_window, slow_window, close):
    if fast_window >= slow_window:
        return None

    fast_ma = vbt.MA.run(close, window=fast_window).ma
    slow_ma = vbt.MA.run(close, window=slow_window).ma

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

    return portfolio.final_value()

def Rodar_backtest():
    global bot_status
    logging.info("Iniciando download dos dados...")
    data = vbt.CCXTData.download(
        symbols='PEPE/USDT',
        exchange='mexc',
        timeframe='15m',
        start='2024-11-01',
        end='2025-04-29',
        show_progress=True
    )
    logging.info("Download concluído.")
    close = data.get('Close')
    
    fast_range = range(1, 1001)
    slow_range = range(1, 1001)
    results = []
    testados = 0
    total_combinacoes = sum(1 for f in fast_range for s in slow_range if f < s)
    inicio = time.time()

    bot_status = "Executando combinações..."

    for i, fast in enumerate(fast_range, start=1):
        for slow in slow_range:
            if fast >= slow:
                continue

            saldo = Testar_ma(fast, slow, close)
            if saldo is not None:
                results.append({'fast': fast, 'slow': slow, 'saldo_final': saldo})
                testados += 1

                # Mantém apenas top 30
                if len(results) > 30:
                    results = sorted(results, key=lambda x: x['saldo_final'], reverse=True)[:30]

            if testados % 500 == 0:
                tempo_decorrido = int((time.time() - inicio) // 60)
                restantes = total_combinacoes - testados
                logging.info(f"Testados: {testados}, Restantes: {restantes}, Tempo: {tempo_decorrido} min")

            time.sleep(0.01)
        gc.collect()

    df = pd.DataFrame(results)
    df.to_csv("results.csv", index=False)
    top = df.sort_values(by="saldo_final", ascending=False).head(30)

    bot_status = "Top 30 combinações:<br>"
    for _, row in top.iterrows():
        bot_status += f"Fast: {row['fast']}, Slow: {row['slow']}, Saldo: {row['saldo_final']:.2f}<br>"

    logging.info("Backtest completo. Resultados salvos em results.csv.")

@app.route("/")
def home():
    threading.Thread(target=Rodar_backtest, daemon=True).start()
    logging.info("Backtest iniciado em segundo plano!")
    return f"<h1>Trading bot está ativo</h1><p>{bot_status}</p>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
