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

# Função para fazer o backtest corretamente
def backtestar(precos, media_rapida, media_lenta):
    saldo = capital_inicial
    posicao = None  # comprado ou vendido
    preco_entrada = None
    fees = 0

    for i in range(media_lenta, len(precos)):
        fechamento = precos[i]
        media_f = np.mean(precos[i - media_rapida:i])
        media_l = np.mean(precos[i - media_lenta:i])

        if media_f > media_l:
            if posicao != "comprado":
                if posicao == "vendido":
                    # Fecha vendido
                    retorno_pct = (preco_entrada - fechamento) / preco_entrada
                    saldo *= (1 + retorno_pct)
                    saldo *= (1 - taxa_operacao)
                    fees += saldo * taxa_operacao
                # Abre comprado
                preco_entrada = fechamento
                saldo *= (1 - taxa_operacao)
                fees += saldo * taxa_operacao
                posicao = "comprado"

        elif media_f < media_l:
            if posicao != "vendido":
                if posicao == "comprado":
                    # Fecha comprado
                    retorno_pct = (fechamento - preco_entrada) / preco_entrada
                    saldo *= (1 + retorno_pct)
                    saldo *= (1 - taxa_operacao)
                    fees += saldo * taxa_operacao
                # Abre vendido
                preco_entrada = fechamento
                saldo *= (1 - taxa_operacao)
                fees += saldo * taxa_operacao
                posicao = "vendido"

    # Fecha última operação
    if posicao == "comprado":
        retorno_pct = (fechamento - preco_entrada) / preco_entrada
        saldo *= (1 + retorno_pct)
        saldo *= (1 - taxa_operacao)
        fees += saldo * taxa_operacao
    elif posicao == "vendido":
        retorno_pct = (preco_entrada - fechamento) / preco_entrada
        saldo *= (1 + retorno_pct)
        saldo *= (1 - taxa_operacao)
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
        for media_lenta in range(media_rapida + 1, 201):  # Garantir que média lenta > média rápida
            saldo_final, retorno_final, taxas = backtestar(precos, media_rapida, media_lenta)
            combinacoes_resultados.append({
                "media_rapida": media_rapida,
                "media_lenta": media_lenta,
                "saldo_final": saldo_final,
                "retorno": retorno_final,
                "taxas": taxas
            })
            testes_realizados += 1

            # Notificação do progresso
            if testes_realizados % int(total_testes * 0.05) == 0 or (time.time() - inicio) > 300:
                progresso = (testes_realizados / total_testes) * 100
                logger.info(f"Progresso: {progresso:.2f}% concluído ({testes_realizados}/{int(total_testes)} testes)")
                inicio = time.time()

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
