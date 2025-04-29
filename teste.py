import os
import time
import threading
import pandas as pd
import vectorbt as vbt
from tqdm import tqdm
from flask import Flask

# Função para baixar os dados
def baixar_dados():
    data = vbt.CCXTData.download(
        symbols='PEPE/USDT',
        exchange='mexc',
        timeframe='15m',
        start='2024-05-01',
        end='2025-04-28',
    )
    return data.get('Close')

# Função de teste das médias móveis
def Testar_ma(fast_window, slow_window, close):
    if fast_window >= slow_window:
        return None
    try:
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
        return portfolio.get_final_value()
    except:
        return None

# Função para testar as combinações em lotes
def testar_combinacoes_em_lotes(fast_range, slow_range, close, batch_size=50):
    global bot_status
    results = []
    total_combinations = len(fast_range) * len(slow_range)
    try:
        results_df = pd.read_csv('results.csv')
        results = results_df.to_dict('records')
        print("Resultados anteriores carregados.")
        start_index = len(results)
    except FileNotFoundError:
        print("Nenhum resultado anterior encontrado.")
        start_index = 0

    for i in tqdm(range(start_index, total_combinations), total=total_combinations, desc="Testando combinações"):
        fast_idx = i // len(slow_range)
        slow_idx = i % len(slow_range)

        fast = fast_range[fast_idx]
        slow = slow_range[slow_idx]

        saldo = Testar_ma(fast, slow, close)
        if saldo is not None:
            results.append({'fast': fast, 'slow': slow, 'saldo_final': saldo})

        if (i + 1) % batch_size == 0 or i == total_combinations - 1:
            pd.DataFrame(results).to_csv('results.csv', index=False)
            time.sleep(0.5)

    # Ordenar resultados finais e guardar
    sorted_results = sorted(results, key=lambda x: x['saldo_final'], reverse=True)[:30]
    bot_status = "\n".join([f"Fast: {r['fast']}, Slow: {r['slow']}, Saldo: {r['saldo_final']:.2f}" for r in sorted_results])
    pd.DataFrame(results).to_csv('results.csv', index=False)

# Executa o backtest em uma thread
def main():
    global bot_status
    bot_status = "Inicializando..."
    close = baixar_dados()
    fast_range = list(range(1, 1002))
    slow_range = list(range(1, 1002))
    testar_combinacoes_em_lotes(fast_range, slow_range, close)

# Flask app
app = Flask(__name__)
bot_status = "Aguardando início..."

@app.route("/")
def home():
    return f"<h1>Bot está rodando!</h1><pre>{bot_status}</pre>"

# Iniciar o bot
threading.Thread(target=main, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
