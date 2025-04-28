import threading
import logging
import time
import os
from flask import Flask
import ccxt
import numpy as np

# Configuração de LOG
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Variáveis globais
bot_status = "Bot de Backtest ainda não iniciou..."

# Configurações iniciais
par = "PEPE/USDC"
exchange = ccxt.mexc()
taxa_operacao = 0.001  # 0,1%
capital_inicial = 100  # 100 dólares simulados
intervalo = "15m"
quantidade_candles = 8000

# Função para buscar os candles
def pegar_candles():
    try:
        dados = exchange.fetch_ohlcv(par, timeframe=intervalo, limit=quantidade_candles)
        fechar_precos = [item[4] for item in dados]  # preço de fechamento
        return fechar_precos
    except Exception as e:
        logger.error(f"Erro ao pegar candles: {e}")
        return []

# Função para fazer o backtest
def backtestar(precos, media_rapida, media_lenta):
    saldo = capital_inicial
    posicao = None  # Nenhuma posição no início

    fees = 0  # controle de taxas pagas
    historico_operacoes = []

    for i in range(media_lenta, len(precos)):
        fechamento = precos[i]

        media_f = np.mean(precos[i - media_rapida:i])
        media_l = np.mean(precos[i - media_lenta:i])

        # Cruzamento de médias
        if media_f > media_l:
            if posicao != "comprado":
                if posicao == "vendido":
                    saldo *= (2 - taxa_operacao)  # fechou venda
                    fees += saldo * taxa_operacao
                posicao = "comprado"
                saldo *= (1 - taxa_operacao)
                fees += saldo * taxa_operacao

        elif media_f < media_l:
            if posicao != "vendido":
                if posicao == "comprado":
                    saldo *= (2 - taxa_operacao)  # fechou compra
                    fees += saldo * taxa_operacao
                posicao = "vendido"
                saldo *= (1 - taxa_operacao)
                fees += saldo * taxa_operacao

    # Fecha posição no final
    if posicao is not None:
        saldo *= (2 - taxa_operacao)
        fees += saldo * taxa_operacao

    retorno = ((saldo - capital_inicial) / capital_inicial) * 100  # crescimento em %
    return saldo, retorno, fees

# Função principal para rodar backtest
def rodar_backtest():
    global bot_status

    logger.info("Iniciando backtest... Buscando candles...")
    precos = pegar_candles()

    if not precos:
        bot_status = "Erro ao buscar candles."
        return

    combinacoes_resultados = []
    total_testes = (200 - 5) * (200 - 5) / 2
    testes_realizados = 0

    inicio = time.time()

    for media_rapida in range(5, 200):
        for media_lenta in range(media_rapida + 1, 201):
            saldo_final, retorno_final, taxas = backtestar(precos, media_rapida, media_lenta)
            combinacoes_resultados.append({
                "media_rapida": media_rapida,
                "media_lenta": media_lenta,
                "saldo_final": saldo_final,
                "retorno": retorno_final,
                "taxas": taxas
            })
            testes_realizados += 1

            # Atualizar progresso a cada 5% ou 5 minutos
            if testes_realizados % int(total_testes * 0.05) == 0 or (time.time() - inicio) > 300:
                progresso = (testes_realizados / total_testes) * 100
                logger.info(f"Progresso: {progresso:.2f}% concluído ({testes_realizados}/{int(total_testes)} testes)")
                inicio = time.time()

    # Ordenar pelos melhores retornos
    combinacoes_resultados.sort(key=lambda x: x['retorno'], reverse=True)
    top_10 = combinacoes_resultados[:10]

    logger.info("\n--- TOP 10 COMBINAÇÕES ---")
    for idx, resultado in enumerate(top_10, 1):
        logger.info(f"{idx}) Rápida: {resultado['media_rapida']} | Lenta: {resultado['media_lenta']} | "
                    f"Saldo Final: {resultado['saldo_final']:.2f} | Retorno: {resultado['retorno']:.2f}% | "
                    f"Taxas Pagas: {resultado['taxas']:.2f}")

    texto_final = ""
    for idx, resultado in enumerate(top_10, 1):
        texto_final += (f"<p>{idx}) Média rápida: {resultado['media_rapida']}, "
                        f"lenta: {resultado['media_lenta']}, "
                        f"Saldo: ${resultado['saldo_final']:.2f}, "
                        f"Retorno: {resultado['retorno']:.2f}%, "
                        f"Taxas pagas: ${resultado['taxas']:.2f}</p>")

    bot_status = "<h1>Backtest concluído!</h1>" + texto_final

# Iniciar o Flask
app = Flask(__name__)

@app.route("/")
def home():
    return f"{bot_status}"

# Rodar o bot em thread separada
threading.Thread(target=rodar_backtest, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
