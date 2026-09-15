"""Ponto de entrada do módulo lumi.ingestion quando executado com python -m lumi.ingestion."""

import asyncio
import sys

from lumi.ingestion.pipeline import main

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
