import pandas as pd
import vectorbt as vbt
import os
import time
import logging
from flask import Flask
import threading

# Configuração de log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

app = Flask(__name__)
bot_status = "Bot ainda não iniciou o backtest."

def baixar_dados_lentamente():
    logging.info("Iniciando download dos dados em partes mensais...")
    datas = pd.date_range(start='2024-05-01', end='2025-04-28', freq='M')
    datas = list(datas.insert(0, pd.Timestamp('2024-05-01')))  # inclui início

    partes = []
    for i in range(len(datas) - 1):
        logging.info(f"Baixando: {datas[i].date()} até {datas[i+1].date()}")
        parte = vbt.CCXTData.download(
            symbols='PEPE/USDT',
            exchange='mexc',
            timeframe='15m',
            start=datas[i],
            end=datas[i+1],
            show_progress=False
        )
        partes.append(parte.get('Close'))
        time.sleep(2)  # pausa leve após cada mês para não forçar o sistema

    close = pd.concat(partes).sort_index().drop_duplicates()
    logging.info("Download completo.")
    return close

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
    return portfolio.final_value

def rodar_backtest():
    global bot_status
    close = baixar_dados_lentamente()
    fast_range = range(1, 251)  # Ajustado para 1 até 250
    slow_range = range(2, 251)  # Ajustado para 2 até 250

    total = sum(1 for f in fast_range for s in slow_range if f < s)
    results = []
    testados = 0
    progresso_logado = set()

    bot_status = "Executando combinações..."

    for i, fast in enumerate(fast_range, start=1):
        for slow in slow_range:
            if fast >= slow:
                continue

            saldo = Testar_ma(fast, slow, close)
            if saldo is not None:
                results.append({'fast': fast, 'slow': slow, 'saldo_final': saldo})
                testados += 1

                progresso = int((testados / total) * 100)
                if progresso % 10 == 0 and progresso not in progresso_logado:
                    logging.info(f"Progresso: {progresso}% ({testados}/{total} combinações testadas)")
                    progresso_logado.add(progresso)

                time.sleep(0.2)  # Pausa de 0.2 segundos após cada backtest

    df = pd.DataFrame(results)
    df.to_csv("results.csv", index=False)
    top = df.sort_values(by="saldo_final", ascending=False).head(30)

    bot_status = "Top 30 combinações:<br>"
    for _, row in top.iterrows():
        bot_status += f"Fast: {row['fast']}, Slow: {row['slow']}, Saldo: {row['saldo_final']:.2f}<br>"

    logging.info("Backtest completo. Resultados salvos em results.csv.")

@app.route("/")
def home():
    return f"<h1>Trading bot está rodando!</h1><p>{bot_status}</p>"

@app.route("/start")
def start():
    threading.Thread(target=rodar_backtest, daemon=True).start()
    return "Backtest iniciado em segundo plano!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
