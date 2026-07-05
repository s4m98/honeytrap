# ============= UTILITY FUNCTIONS =============
import socket
import errno
import os

# Import configuration
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DEFAULT_WEB_ROOT, DEFAULT_FTP_ROOT

def check_port_available(port, interface='0.0.0.0'):
    """Check if a port is available for binding"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind((interface, port))
        sock.close()
        return True
    except socket.error as e:
        if e.errno == errno.EADDRINUSE:
            return False
        return False
    except:
        return False

def ensure_directories():
    """Create necessary directories"""
    directories = ['logs', DEFAULT_WEB_ROOT, DEFAULT_FTP_ROOT]
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
        except:
            pass
