# ============= CONFIGURATION =============
import os

# Get the base directory (where config.py is located)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Service configurations (removed PostgreSQL)
DEFAULT_SERVICES = {
    21: ("FTP", "vsFTPd 3.0.3"),
    22: ("SSH", "OpenSSH_8.2p1"),
    23: ("Telnet", "Linux telnetd"),
    80: ("HTTP", "Apache/2.4.41"),
    3306: ("MySQL", "MySQL 8.0.25"),
}

# File paths
LOG_FILE = os.path.join(BASE_DIR, "honeypot.log")
DATABASE_FILE = os.path.join(BASE_DIR, "honeypot.db")

# Separate log files for each service
SERVICE_LOGS = {
    "HTTP": os.path.join(BASE_DIR, "logs/http_logs.txt"),
    "SSH": os.path.join(BASE_DIR, "logs/ssh_logs.txt"),
    "FTP": os.path.join(BASE_DIR, "logs/ftp_logs.txt"),
    "Telnet": os.path.join(BASE_DIR, "logs/telnet_logs.txt"),
    "MySQL": os.path.join(BASE_DIR, "logs/mysql_logs.txt"),
    "GENERIC": os.path.join(BASE_DIR, "logs/generic_logs.txt"),
}

# Credentials log file
CREDENTIALS_FILE = os.path.join(BASE_DIR, "captured_credentials.txt")

# Directory paths
DEFAULT_WEB_ROOT = os.path.join(BASE_DIR, "web_root")
DEFAULT_FTP_ROOT = os.path.join(BASE_DIR, "ftp_root")

# Login credentials
DEFAULT_CREDENTIALS = {
    "admin": "password123!",
    "root": "toor",
    "guest": "guest123",
    "user": "password",
    "anonymous": "anonymous",
}

# GeoLite2 City database path (optional)
GEOIP_DB_PATH = os.path.join(BASE_DIR, "GeoLite2-City.mmdb")
ENABLE_GEOIP = False  # Set to True if you have GeoIP database

# ASCII Banner
HONEYTRAP_BANNER = r"""

   __ __                  ______            
  / // /__  ___  ___ __ _/_  __/______ ____ 
 / _  / _ \/ _ \/ -_) // // / / __/ _ `/ _ \
/_//_/\___/_//_/\__/\_, //_/ /_/  \_,_/ .__/
                   /___/             /_/    

══════════════════════════════════════════════
   Author: Mohit Sambharwal
   Version: 1.0

  Advanced Honeypot System - Capture Everything
══════════════════════════════════════════════
"""
