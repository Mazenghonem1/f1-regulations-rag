"""Environment check: venv is Python 3.11 and every dependency imports.

Run inside the venv: python src/check_env.py
"""
import sys

assert sys.version_info[:2] == (3, 11), f"expected Python 3.11, got {sys.version}"

import requests  # noqa: F401
import bs4  # noqa: F401
import pdfminer  # noqa: F401
import sentence_transformers  # noqa: F401
import rank_bm25  # noqa: F401
import numpy  # noqa: F401

if __name__ == "__main__":
    print(f"OK — Python {sys.version.split()[0]}, all dependencies import cleanly.")
