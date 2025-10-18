# utils.py
import os
from dotenv import load_dotenv

load_dotenv()

def get_env(key, default=None):
    val = os.getenv(key)
    return val if val is not None else default
