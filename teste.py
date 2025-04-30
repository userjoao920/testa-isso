import pandas as pd
import vectorbt as vbt
import os
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

def baixar_dados():
    logging.info("Iniciando download dos dados...")
    data = vbt.CCXTData.download(
        symbols='PEPE/USDT',
        exchange='mexc',
        timeframe='15m',
        start='2024-05-01',
        end='2025-04-28',
        show_progress=True  # Exibe barra de progresso durante o download
    )
    logging.info("Download concluído.")
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
    return portfolio.final_value

def rodar_backtest():
    global bot_status
    close = baixar_dados()
    fast_range = range(1, 251)  # Alterei para 1 a 250
    slow_range = range(1, 251)
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

                # Armazenar apenas as 30 melhores combinações
                if len(results) > 30:
                    results = sorted(results, key=lambda x: x['saldo_final'], reverse=True)[:30]

        # Limpar os dados do backtest após cada iteração
        del close
        import gc
        gc.collect()

    # Convertendo resultados para DataFrame e retornando as melhores combinações
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
