import pandas as pd
import vectorbt as vbt
import os
import time
from flask import Flask
import threading

app = Flask(__name__)
bot_status = "Bot ainda não iniciou o backtest."

def baixar_dados():
    data = vbt.CCXTData.download(
        symbols='PEPE/USDT',
        exchange='mexc',
        timeframe='15m',
        start='2024-05-01',
        end='2025-04-28',
    )
    return data.get('Close')

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
    return portfolio.get_final_value()

def rodar_backtest():
    global bot_status
    close = baixar_dados()
    fast_range = range(1, 1001)
    slow_range = range(1, 1001)
    total = len(fast_range) * len(slow_range)
    results = []

    start_time = time.time()
    last_save_time = start_time

    bot_status = "Executando combinações..."

    for fast in fast_range:
        for slow in slow_range:
            saldo = Testar_ma(fast, slow, close)
            if saldo is not None:
                results.append({'fast': fast, 'slow': slow, 'saldo_final': saldo})

            # Salvamento a cada 5 minutos
            now = time.time()
            if now - last_save_time >= 300:
                df = pd.DataFrame(results)
                df.to_csv("resultados_parciais.csv", index=False)
                last_save_time = now
                bot_status = f"Parcial salvo com {len(results)} combinações testadas..."

    df = pd.DataFrame(results)
    df.to_csv("results.csv", index=False)
    top = df.sort_values(by="saldo_final", ascending=False).head(30)

    bot_status = "Top 30 combinações:<br>"
    for _, row in top.iterrows():
        bot_status += f"Fast: {row['fast']}, Slow: {row['slow']}, Saldo: {row['saldo_final']:.2f}<br>"

@app.route("/")
def home():
    return f"<h1>Trading bot está rodando!</h1><p>{bot_status}</p>"

@app.route("/start")
def start():
    threading.Thread(target=rodar_backtest, daemon=True).start()
    return "Backtest iniciado em segundo plano!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
