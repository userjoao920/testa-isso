import threading
import logging
import time
from flask import Flask
import vectorbt as vbt
import pandas as pd

# LOG
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Status do bot
bot_status = "Bot de Backtest ainda não iniciou..."

# Função de teste com médias móveis
def Testar_ma(fast_window, slow_window, close):
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
        slippage=0.00
    )

    return portfolio.value().iloc[-1]

# Função principal de backtest
def rodar_backtest():
    global bot_status
    bot_status = "Backtest em andamento..."

    logger.info("Baixando dados de candles...")
    data = vbt.CCXTData.download(
        symbols='PEPE/USDT',
        exchange='mexc',
        timeframe='15m',
        start='2024-05-01',
        end='2025-04-28'
    )

    close = data.get('Close')

    results = []
    for fast in range(1, 20):
        for slow in range(fast + 1, 20):
            saldo = Testar_ma(fast, slow, close)
            results.append(((fast, slow), saldo))

    results = sorted(results, key=lambda x: x[1], reverse=True)

    logger.info("\n--- TOP 30 COMBINAÇÕES ---")
    for combo, saldo in results[:30]:
        logger.info(f"Fast: {combo[0]}, Slow: {combo[1]}, Saldo Final: {saldo:.2f}")

    bot_status = "<h1>Backtest finalizado com sucesso!</h1> Veja os logs para as 30 melhores combinações."

# Flask para status
app = Flask(__name__)

@app.route("/")
def home():
    return bot_status

# Rodar backtest em segundo plano
threading.Thread(target=rodar_backtest, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
