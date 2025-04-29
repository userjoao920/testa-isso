import pandas as pd
import vectorbt as vbt
import ccxt
import time
from tqdm import tqdm

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
    # Criar as médias móveis com vectorbt
    fast_ma = vbt.MA.run(close, window=fast_window).ma  # Média rápida
    slow_ma = vbt.MA.run(close, window=slow_window).ma  # Média lenta

    # Cruzamento das médias móveis para determinar os sinais
    cross_up = fast_ma.vbt.crossed_above(slow_ma)
    cross_down = fast_ma.vbt.crossed_below(slow_ma)

    # Sinal de compra (long entry)
    long_signal = cross_up

    # Sinal de venda (short entry)
    short_signal = cross_down

    # Criar o portfólio com base nas condições
    portfolio = vbt.Portfolio.from_signals(
        close,
        entries=long_signal,
        exits=short_signal,
        short_entries=cross_down,
        short_exits=cross_up,
        init_cash=100,
        fees=0.001,  # Taxa de 0.1%
        slippage=0.00  # Deslizamento de 0.1%
    )
    return portfolio.get_final_value()

# Função para dividir os testes em lotes e salvar progresso
def testar_combinacoes_em_lotes(fast_range, slow_range, close, batch_size=50, start_from=0):
    results = []
    batch_start = start_from
    total_combinations = len(fast_range) * len(slow_range)
    
    # Carregar resultados anteriores se existir
    try:
        results_df = pd.read_csv('results.csv')
        results = results_df.to_dict('records')
        print("Resultados anteriores carregados, retomando a partir de:", len(results))
        batch_start = len(results)
    except FileNotFoundError:
        print("Nenhum resultado anterior encontrado.")
    
    # Laço para testar combinações em lotes
    for i in tqdm(range(batch_start, total_combinations), total=total_combinations, desc="Testando combinações"):
        fast_idx = i // len(slow_range)
        slow_idx = i % len(slow_range)
        
        fast = fast_range[fast_idx]
        slow = slow_range[slow_idx]
        
        saldo = Testar_ma(fast, slow, close)
        if saldo is not None:
            results.append({'fast': fast, 'slow': slow, 'saldo_final': saldo})

        # Salvar progresso a cada lote
        if (i + 1) % batch_size == 0 or i == total_combinations - 1:
            results_df = pd.DataFrame(results)
            results_df.to_csv('results.csv', index=False)
            time.sleep(1)  # Pause para não sobrecarregar o sistema

    return results

# Função principal
def main():
    close = baixar_dados()
    fast_range = list(range(1, 1002))  # Variação rápida de 1 a 1001
    slow_range = list(range(1, 1002))  # Variação lenta de 1 a 1001

    # Chama a função para testar combinações em lotes
    results = testar_combinacoes_em_lotes(fast_range, slow_range, close, batch_size=50)

    # Ordenar os resultados por saldo final e mostrar os 30 melhores
    results_sorted = sorted(results, key=lambda x: x['saldo_final'], reverse=True)
    for combo in results_sorted[:30]:
        print(f"Fast: {combo['fast']}, Slow: {combo['slow']}, Saldo Final: {combo['saldo_final']}")

app = Flask(__name__) # Iniciar um site em flask

@app.route("/")

def home(): 
    
    return f"<h1>Trading bot está rodando!</h1><p>{bot_status}</p>"

    # Iniciar o bot em uma thread separada
threading.Thread(target=main, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
