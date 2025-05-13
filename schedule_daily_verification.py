#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para execuu00e7u00e3o diu00e1ria da verificau00e7u00e3o da estrutura OPIN utilizando o processo opin_verification.
Este script deve ser configurado para ser executado diariamente atravu00e9s de um agendador
como cron (Linux/Mac) ou Task Scheduler (Windows).

Exemplo de configurau00e7u00e3o para cron (executar todos os dias u00e0s 2:00 AM):
0 2 * * * /caminho/para/python /caminho/para/schedule_daily_verification.py >> /caminho/para/logs/opin_daily.log 2>&1

Alternativamente, pode ser configurado para executar em intervalo menor para APIs cru00edticas:
0 */6 * * * /caminho/para/python /caminho/para/schedule_daily_verification.py --critical-only
"""

import os
import sys
import logging
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Adiciona o diretu00f3rio pai ao path para poder importar app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurau00e7u00e3o de logging
log_dir = Path(os.path.dirname(os.path.abspath(__file__)), "logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f"opin_daily_{datetime.now().strftime('%Y%m%d')}.log", 
                            encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("opin_daily")


def parse_arguments():
    """
    Processa os argumentos de linha de comando.
    
    Returns:
        Objeto com os argumentos processados
    """
    parser = argparse.ArgumentParser(description="Executa a verificau00e7u00e3o diu00e1ria da estrutura OPIN usando opin_verification")
    parser.add_argument(
        "--critical-only", 
        action="store_true", 
        help="Verifica apenas APIs em estado cru00edtico"
    )
    parser.add_argument(
        "--email-notification", 
        action="store_true", 
        help="Envia notificau00e7u00e3o por email em caso de falhas cru00edticas"
    )
    
    return parser.parse_args()


def check_critical_apis() -> Dict[str, Any]:
    """
    Verifica apenas as APIs que estu00e3o em estado cru00edtico utilizando
    o processo opin_verification com filtro para APIs cru00edticas.
    
    Returns:
        Resultado da verificau00e7u00e3o
    """
    try:
        # Importa o mu00f3dulo de verificau00e7u00e3o opin_verification
        from app.services.opin_verification.main import verify_opin_structure
        
        # Executa a verificau00e7u00e3o apenas para APIs cru00edticas
        logger.info("Executando verificau00e7u00e3o apenas para APIs cru00edticas com opin_verification")
        results = verify_opin_structure(critical_only=True)
        
        return results
    except Exception as e:
        error_msg = f"Erro ao verificar APIs cru00edticas: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg
        }


def send_email_notification(report: Dict[str, Any]) -> None:
    """
    Envia notificau00e7u00e3o por email em caso de falhas cru00edticas.
    
    Args:
        report: Relatu00f3rio de sau00fade das APIs
    """
    # Por enquanto, apenas registra no log que esta funcionalidade deve ser implementada
    logger.info("A funcionalidade de envio de email de notificau00e7u00e3o deve ser implementada.")


def main() -> Dict[str, Any]:
    """
    Funu00e7u00e3o principal que executa a verificau00e7u00e3o diu00e1ria da estrutura OPIN
    utilizando o processo opin_verification.
    
    Returns:
        Resultado da verificau00e7u00e3o
    """
    try:
        # Processa argumentos da linha de comando
        args = parse_arguments()
        
        # Verifica se u00e9 para executar apenas para APIs cru00edticas
        if args.critical_only:
            logger.info("Iniciando verificau00e7u00e3o apenas de APIs cru00edticas")
            result = check_critical_apis()
        else:
            # Executa verificau00e7u00e3o completa utilizando opin_verification
            logger.info("Iniciando verificau00e7u00e3o diu00e1ria completa utilizando opin_verification")
            
            # Importa o mu00f3dulo de verificau00e7u00e3o opin_verification
            from app.services.opin_verification.main import verify_opin_structure
            
            # Executa a verificau00e7u00e3o
            result = verify_opin_structure()
        
        # Registra o resultado
        if isinstance(result, dict) and "status" in result:
            if result["status"] == "success":
                logger.info(f"Verificau00e7u00e3o concluu00edda com sucesso: {result.get('message', '')}")
            else:
                logger.error(f"Erro na verificau00e7u00e3o: {result.get('message', 'Erro desconhecido')}")
        else:
            logger.info("Verificau00e7u00e3o concluu00edda com sucesso!")
        
        # Envia notificau00e7u00e3o por email se solicitado
        if args.email_notification:
            send_email_notification(result)
        
        return result
    except Exception as e:
        error_msg = f"Erro ao executar verificau00e7u00e3o diu00e1ria: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg
        }


if __name__ == "__main__":
    main()