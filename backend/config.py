"""
Central Configuration File for Backend
All database and environment configurations should be imported from here.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
# Try root directory first, then current directory
root_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(root_env):
    load_dotenv(root_env)
else:
    load_dotenv()

# Database Configuration
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", " name "),
    "user": os.getenv("DB_USER", " postgres"),
    "password": os.getenv("DB_PASSWORD", " sifre "),
    "host": os.getenv("DB_HOST", " localhost"),
    "port": os.getenv("DB_PORT", " port no ")
}

# External DB Config for translate.py bridge
EXT_DB_CONFIG = {
    "dbname": os.getenv("EXT_DB_NAME", "external_erp_db"),
    "user": os.getenv("EXT_DB_USER", "postgres"),
    "password": os.getenv("EXT_DB_PASSWORD", "your_password"),
    "host": os.getenv("EXT_DB_HOST", "localhost"),
    "port": os.getenv("EXT_DB_PORT", "5432")
}

# Service Configuration
try:
    # Güvenli parsing: Eğer "port no" gibi bir string gelirse varsayılan porta döner
    BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000").strip())
except ValueError:
    BACKEND_PORT = 8000

try:
    FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "5173").strip())
except ValueError:
    FRONTEND_PORT = 5173
