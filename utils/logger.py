"""
Merkezi loglama sistemi.
Hem dosyaya hem de streamlit console'a log yazar.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings import LOG_FILE, LOG_LEVEL


class LoggerFactory:
    """Singleton logger fabrikası."""

    _instance: Optional[logging.Logger] = None

    @classmethod
    def get_logger(cls, name: str = "ExamAnalyzer") -> logging.Logger:
        if cls._instance is not None:
            return cls._instance

        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

        # Format
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(module)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Dosya handler
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

        # Konsol handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

        cls._instance = logger
        return logger


def get_logger(name: str = "ExamAnalyzer") -> logging.Logger:
    return LoggerFactory.get_logger(name)
