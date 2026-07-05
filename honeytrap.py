#!/usr/bin/env python3
# ============= MAIN HONEYPOT ORCHESTRATOR =============
import sys
import os
import threading
import time
import logging
import socket
import errno

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import configuration
from config import *
from core.utils import check_port_available, ensure_directories
from core.database import DatabaseManager
from core.geoip import GeoLocationHandler
from core.keylogger import ServiceKeylogger
from services import FTPService, HTTPService, MySQLService

# Setup logging
logging.getLogger().handlers.clear()
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8', mode='a')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

class HoneyTrap:
    def __init__(self, interface='0.0.0.0'):
        self.interface = interface
        self.services = dict(DEFAULT_SERVICES)
        self.active = False
        self.threads = []
        self.service_instances = []
        
        # Ensure directories exist
        ensure_directories()
        
        # Initialize core components
        self.db_manager = DatabaseManager(DATABASE_FILE)
        self.geo_handler = GeoLocationHandler(GEOIP_DB_PATH, ENABLE_GEOIP)
        self.keylogger = ServiceKeylogger(SERVICE_LOGS, CREDENTIALS_FILE)
        
        # Store paths as instance variables
        self.web_root = DEFAULT_WEB_ROOT
        self.ftp_root = DEFAULT_FTP_ROOT
        
        # Create default web files
        self.create_default_web_pages()
        self.create_ftp_files()
    
    def create_default_web_pages(self):
        """Create default web pages in web_root if they don't exist"""
        # Create web_root directory if it doesn't exist
        os.makedirs(self.web_root, exist_ok=True)
        
        index_file = os.path.join(self.web_root, "index.html")
        if not os.path.exists(index_file):
            with open(index_file, 'w', encoding='utf-8') as f:
                f.write("""<!DOCTYPE html>
<html>
<head><title>Welcome</title>
<meta http-equiv="refresh" content="0; url=/login">
</head>
<body><p>Redirecting...</p></body>
</html>""")
        
        login_file = os.path.join(self.web_root, "login.html")
        if not os.path.exists(login_file):
            with open(login_file, 'w', encoding='utf-8') as f:
                f.write("""<!DOCTYPE html>
<html>
<head><title>Login</title>
<style>
body { font-family: Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; padding: 0; }
.login-container { background: white; padding: 40px; width: 350px; margin: 100px auto; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.2); }
h2 { text-align: center; color: #333; }
input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
button { background: #4CAF50; color: white; padding: 10px; width: 100%; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
button:hover { background: #45a049; }
.hint { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
</style>
</head>
<body>
<div class="login-container">
<h2>🔐 Secure Login</h2>
<form method="POST" action="/login">
<input type="text" name="username" placeholder="Username" required><br>
<input type="password" name="password" placeholder="Password" required><br>
<button type="submit">Login</button>
</form>
<div class="hint">Demo: admin / password123!</div>
</div>
</body>
</html>""")
        
        # Create CSS directory and file
        css_dir = os.path.join(self.web_root, "css")
        os.makedirs(css_dir, exist_ok=True)
        css_file = os.path.join(css_dir, "style.css")
        if not os.path.exists(css_file):
            with open(css_file, 'w', encoding='utf-8') as f:
                f.write("""body { font-family: Arial, sans-serif; }
.login-container { max-width: 400px; margin: 50px auto; }
""")
    
    def create_ftp_files(self):
        """Create fake FTP files in ftp_root"""
        # Create ftp_root directory if it doesn't exist
        os.makedirs(self.ftp_root, exist_ok=True)
        
        fake_files = {
            "readme.txt": "Welcome to FTP server\nThis is a honeypot system.\n",
            "passwords.txt": "admin:admin123\nuser:password\nroot:toor\n",
            "config.ini": "[database]\nhost=localhost\nuser=root\npass=secret123\n",
            "notice.txt": "All activities are monitored and logged.\n"
        }
        
        for filename, content in fake_files.items():
            filepath = os.path.join(self.ftp_root, filename)
            if not os.path.exists(filepath):
                try:
                    with open(filepath, 'w') as f:
                        f.write(content)
                except:
                    pass
    
    def start_service(self, port, service_name, service_version):
        """Start a generic service"""
        def service_loop():
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.settimeout(1)
                sock.bind((self.interface, port))
                sock.listen(5)
                
                print(f"  ✅ {service_name} on port {port}")
                
                while self.active:
                    try:
                        conn, addr = sock.accept()
                        client_ip = addr[0]
                        # Log connection
                        self.keylogger.log_connection(service_name, client_ip, port)
                        # Send banner and close
                        conn.sendall(f"220 {service_version}\r\n".encode())
                        time.sleep(0.5)
                        conn.close()
                    except socket.timeout:
                        continue
                    except:
                        break
            except Exception as e:
                print(f"  ❌ Failed to start {service_name} on port {port}: {e}")
            finally:
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
        
        # Check if port is available
        if not check_port_available(port, self.interface):
            print(f"  ⚠️  Port {port} is in use, skipping {service_name}")
            return None
            
        thread = threading.Thread(target=service_loop, daemon=True)
        thread.start()
        self.threads.append(thread)
        return thread
    
    def start_honeypot(self):
        if self.active:
            print("HoneyTrap is already running!")
            return
        
        self.active = True
        self.threads = []
        self.service_instances = []
        
        print("\n" + "="*60)
        print("🚀 Starting HoneyTrap Honeypot...")
        print("="*60)
        
        services_started = 0
        print("\n📡 Starting services:")
        print("-"*40)
        
        for port, (name, version) in self.services.items():
            # Check if port is available
            if not check_port_available(port, self.interface):
                print(f"  ⚠️  Port {port} is in use, skipping {name}")
                continue
                
            if port == 80:
                # Start HTTP service with web_root support
                try:
                    http_service = HTTPService(self.web_root, self.db_manager, self.keylogger, self.geo_handler)
                    self.service_instances.append(http_service)
                    http_service.start(self.interface, port)
                    services_started += 1
                except Exception as e:
                    print(f"  ❌ Failed to start HTTP service: {e}")
                
            elif port == 21:
                # Start FTP service (standalone version - no pyftpdlib needed)
                try:
                    # Check if port is free
                    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    test_sock.settimeout(1)
                    result = test_sock.connect_ex((self.interface, port))
                    test_sock.close()
                    
                    if result == 0:
                        print(f"  ⚠️  Port {port} is in use")
                        print(f"     Run: sudo fuser -k {port}/tcp")
                        continue
                    
                    ftp_service = FTPService(self.ftp_root, self.db_manager, self.keylogger, self.geo_handler)
                    self.service_instances.append(ftp_service)
                    ftp_service.start(self.interface, port)
                    services_started += 1
                except Exception as e:
                    print(f"  ❌ Failed to start FTP service: {e}")
            
            elif port == 3306:
                # Start MySQL service
                try:
                    # Check if port is free
                    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    test_sock.settimeout(1)
                    result = test_sock.connect_ex((self.interface, port))
                    test_sock.close()
                    
                    if result == 0:
                        print(f"  ⚠️  Port {port} is in use")
                        print(f"     Run: sudo fuser -k {port}/tcp")
                        continue
                    
                    mysql_service = MySQLService(self.db_manager, self.keylogger, self.geo_handler)
                    self.service_instances.append(mysql_service)
                    mysql_service.start(self.interface, port)
                    services_started += 1
                except Exception as e:
                    print(f"  ❌ Failed to start MySQL service: {e}")
                
            else:
                self.start_service(port, name, version)
                services_started += 1
        
        if services_started > 0:
            print("-"*40)
            print(f"\n🎯 HoneyTrap is ACTIVE with {services_started} services")
            print("="*60)
            print(f"\n📁 HTTP Web Root: {self.web_root}")
            print(f"📁 FTP Root: {self.ftp_root}")
            print(f"📁 Credentials: {CREDENTIALS_FILE}")
            print(f"📁 Logs Directory: logs/")
            
            print("\n🎣 TEST CREDENTIALS:")
            for user, pwd in DEFAULT_CREDENTIALS.items():
                print(f"  • {user} / {pwd}")
            
            print("\n🔧 TEST COMMANDS:")
            print("  HTTP:    curl -X POST http://localhost/login -d 'username=admin&password=password123!'")
            print("  HTTP:    Open browser and visit http://localhost")
            print("  FTP:     ftp localhost")
            print("  FTP:     Username: anonymous, Password: anything")
            print("  MySQL:   mysql -h localhost -P 3306 -u root -p")
            print("  MySQL:   Enter any password")
            print("  SSH:     ssh localhost -p 22")
            print("  Telnet:  telnet localhost 23")
            
            print("\n📝 Available Commands after login:")
            print("  FTP:")
            print("    • ls, dir - List files")
            print("    • get <file> - Download file")
            print("    • cd <dir> - Change directory")
            print("  MySQL:")
            print("    • Connection attempts captured")
            print("    • Username and password hash logged")
            
            print("\n" + "="*60)
            print("📝 Type 'stop' to shutdown")
            print("📝 Type 'logs' to see log files")
            print("📝 Type 'creds' to see captured credentials")
            print("="*60 + "\n")
        else:
            print("❌ No services could be started")
            self.active = False
    
    def stop_honeypot(self):
        if not self.active:
            print("HoneyTrap is not running!")
            return
        
        print("\n🛑 Stopping HoneyTrap...")
        self.active = False
        
        # Stop all service instances
        for service in self.service_instances:
            try:
                service.stop()
            except:
                pass
        
        time.sleep(1)
        self.db_manager.close()
        
        print("\n✅ HoneyTrap stopped")
        print("\n📁 Captured data saved to:")
        print(f"  • Credentials: {CREDENTIALS_FILE}")
        print(f"  • Database: {DATABASE_FILE}")
        print(f"  • Logs: logs/ directory")

def view_credentials():
    """View captured credentials"""
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    print("\n📋 Captured Credentials:")
                    print("="*60)
                    print(content)
                else:
                    print("\n📋 No credentials captured yet")
        except Exception as e:
            print(f"Error reading file: {e}")
    else:
        print("\n📋 No credentials captured yet")

def view_logs():
    """View all log files"""
    print("\n📊 Log Files:")
    print("-"*40)
    
    # Check service logs
    for service, filename in SERVICE_LOGS.items():
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"  • {service}: {filename} ({size:,} bytes)")
        else:
            print(f"  • {service}: No logs yet")
    
    # Check main log
    if os.path.exists(LOG_FILE):
        size = os.path.getsize(LOG_FILE)
        print(f"  • Main: {LOG_FILE} ({size:,} bytes)")
    
    # Check credentials file
    if os.path.exists(CREDENTIALS_FILE):
        size = os.path.getsize(CREDENTIALS_FILE)
        print(f"  • Credentials: {CREDENTIALS_FILE} ({size:,} bytes)")
    
    print("\n📁 To view specific log, check the logs/ directory")

def main():
    print(HONEYTRAP_BANNER)
    
    honeytrap = HoneyTrap()
    
    while True:
        print("\n" + "="*60)
        print("🐝 HONEYTRAP CONTROL PANEL")
        print("="*60)
        print("1. 🚀 Start HoneyTrap")
        print("2. 📋 View Captured Credentials")
        print("3. 📊 View Logs")
        print("4. 📁 List Available Files")
        print("5. ❌ Exit")
        print("="*60)
        
        try:
            choice = input("\nSelect option [1-5]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Exiting...")
            if honeytrap.active:
                honeytrap.stop_honeypot()
            break
        
        if choice == "1":
            try:
                honeytrap.start_honeypot()
                
                if honeytrap.active:
                    print("\n🐝 HoneyTrap is monitoring...")
                    print("Commands: stop, logs, creds, help\n")
                    
                    while honeytrap.active:
                        try:
                            cmd = input().strip().lower()
                            if cmd in ['stop', 'exit', 'quit']:
                                honeytrap.stop_honeypot()
                                break
                            elif cmd == 'logs':
                                view_logs()
                            elif cmd == 'creds':
                                view_credentials()
                            elif cmd == 'help':
                                print("\nAvailable commands:")
                                print("  • stop  - Stop the honeypot")
                                print("  • logs  - Show log files")
                                print("  • creds - Show captured credentials")
                                print("  • help  - Show this help")
                            elif cmd:
                                print(f"Unknown command: {cmd}. Try: stop, logs, creds, help")
                        except (KeyboardInterrupt, EOFError):
                            honeytrap.stop_honeypot()
                            break
            except KeyboardInterrupt:
                honeytrap.stop_honeypot()
            except Exception as e:
                print(f"Error: {e}")
        
        elif choice == "2":
            view_credentials()
        
        elif choice == "3":
            view_logs()
        
        elif choice == "4":
            print("\n📁 Available Directories and Files:")
            print("-"*40)
            
            # Show web_root contents
            if os.path.exists(DEFAULT_WEB_ROOT):
                print(f"\n📂 HTTP Web Root ({DEFAULT_WEB_ROOT}):")
                for file in os.listdir(DEFAULT_WEB_ROOT):
                    filepath = os.path.join(DEFAULT_WEB_ROOT, file)
                    if os.path.isfile(filepath):
                        size = os.path.getsize(filepath)
                        print(f"  📄 {file} ({size} bytes)")
                    elif os.path.isdir(filepath):
                        print(f"  📁 {file}/")
            
            # Show ftp_root contents
            if os.path.exists(DEFAULT_FTP_ROOT):
                print(f"\n📂 FTP Root ({DEFAULT_FTP_ROOT}):")
                for file in os.listdir(DEFAULT_FTP_ROOT):
                    filepath = os.path.join(DEFAULT_FTP_ROOT, file)
                    if os.path.isfile(filepath):
                        size = os.path.getsize(filepath)
                        print(f"  📄 {file} ({size} bytes)")
                    elif os.path.isdir(filepath):
                        print(f"  📁 {file}/")
        
        elif choice == "5":
            print("\n👋 Goodbye!")
            if honeytrap.active:
                honeytrap.stop_honeypot()
            break
        
        else:
            print("Invalid option! Please select 1-5")

if __name__ == "__main__":
    if os.name != 'nt' and os.geteuid() != 0:
        print("⚠️  Note: Run with 'sudo' for ports below 1024 (80, 21, etc.)")
        print()
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Terminated")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
