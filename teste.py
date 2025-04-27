import logging
from flask import Flask, jsonify
import ccxt
import pandas as pd
import numpy as np
import time
import threading

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

# Classe de Negócio (Backtester)
class Backtester:
    def __init__(self):
        self.symbol = 'PEPE/USDC'
        self.timeframe = '15m'
        self.limit = 8000
        self.resultados = []
        self.exchange = ccxt.mexc()
        self.df = None

    def baixar_dados(self):
        logging.info("Baixando dados do MEXC...")
        ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=self.limit)
        self.df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], unit='ms')
        self.df.set_index('timestamp', inplace=True)
        logging.info("Dados baixados com sucesso!")

    def backtest(self, ma_rapida, ma_lenta):
        saldo = 100
        posicao = None
        preco_entrada = 0

        df = self.df.copy()
        df['ma_rapida'] = df['close'].rolling(ma_rapida).mean()
        df['ma_lenta'] = df['close'].rolling(ma_lenta).mean()

        for i in range(max(ma_rapida, ma_lenta), len(df)):

            preco_atual = df['close'].iloc[i]
            ma_r = df['ma_rapida'].iloc[i]
            ma_l = df['ma_lenta'].iloc[i]

            if np.isnan(ma_r) or np.isnan(ma_l):
                continue

            if ma_r > ma_l:
                if posicao == 'sell':
                    percentual = (preco_entrada - preco_atual) / preco_entrada
                    saldo = saldo * (1 + percentual)
                    posicao = None
                if posicao is None:
                    preco_entrada = preco_atual
                    posicao = 'buy'

            elif ma_r < ma_l:
                if posicao == 'buy':
                    percentual = (preco_atual - preco_entrada) / preco_entrada
                    saldo = saldo * (1 + percentual)
                    posicao = None
                if posicao is None:
                    preco_entrada = preco_atual
                    posicao = 'sell'

        if posicao == 'buy':
            percentual = (df['close'].iloc[-1] - preco_entrada) / preco_entrada
            saldo = saldo * (1 + percentual)
        elif posicao == 'sell':
            percentual = (preco_entrada - df['close'].iloc[-1]) / preco_entrada
            saldo = saldo * (1 + percentual)

        return saldo

    def executar_backtest(self):
        self.baixar_dados()

        total_testes = (200 - 5 + 1) ** 2
        testes_concluidos = 0
        progresso_aviso = 0
        inicio_tempo = time.time()

        for ma_rapida in range(5, 201):
            for ma_lenta in range(5, 201):
                if ma_rapida >= ma_lenta:
                    continue

                saldo_final = self.backtest(ma_rapida, ma_lenta)
                self.resultados.append({
                    'ma_rapida': ma_rapida,
                    'ma_lenta': ma_lenta,
                    'saldo_final': saldo_final
                })

                testes_concluidos += 1
                progresso_atual = int((testes_concluidos / total_testes) * 100)

                if progresso_atual >= progresso_aviso + 10:
                    progresso_aviso = progresso_atual
                    tempo_passado = (time.time() - inicio_tempo) / 60
                    logging.info(f"Progresso: {progresso_atual}% concluído - Tempo decorrido: {tempo_passado:.2f} minutos")

        self.resultados = sorted(self.resultados, key=lambda x: x['saldo_final'], reverse=True)
        logging.info("Backtest concluído!")

    def pegar_top_resultados(self, top=10):
        return self.resultados[:top]

# Instanciar o backtester
backtester = Backtester()

# Criar uma função para rodar em paralelo com Flask
def rodar_backtest():
    backtester.executar_backtest()

@app.route('/start-backtest', methods=['GET'])
def start_backtest():
    threading.Thread(target=rodar_backtest).start()
    return jsonify({"mensagem": "Backtest iniciado!"})

@app.route('/top-resultados', methods=['GET'])
def top_resultados():
    resultados = backtester.pegar_top_resultados()
    return jsonify(resultados)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
