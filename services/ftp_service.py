# ============= FTP HONEYPOT SERVICE (ALL COMMANDS WORKING) =============
import socket
import threading
import time
import logging
import os
import sys
from datetime import datetime

logger = logging.getLogger(__name__)

class FTPService:
    """FTP honeypot with valid credentials and full monitoring"""
    
    def __init__(self, ftp_root, db_manager, keylogger, geo_handler):
        self.ftp_root = ftp_root
        self.db_manager = db_manager
        self.keylogger = keylogger
        self.geo_handler = geo_handler
        self.active = False
        self.sock = None
        self.threads = []
        
        # Valid credentials
        self.VALID_CREDENTIALS = {
            "admin": "password123!",
            "user": "password",
            "root": "toor",
            "test": "test123",
            "anonymous": "",
            "ftp": "",
        }
        
        self.USER_PERMS = {
            "admin": "full",
            "root": "full",
            "user": "read",
            "test": "read",
            "anonymous": "read",
            "ftp": "read"
        }
    
    def get_user_permissions(self, username):
        return self.USER_PERMS.get(username, "read")
    
    def log_activity(self, client_ip, username, action, details, country="Unknown", city="Unknown"):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"  FTP: {action} - {username} ({client_ip}) - {details}")
        
        log_file = "logs/ftp_logs.txt"
        os.makedirs("logs", exist_ok=True)
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {action} - {username} ({client_ip}) - {details}\n")
                f.flush()
        except:
            pass
        
        if self.keylogger:
            try:
                self.keylogger.log_activity("FTP", client_ip, action, f"{username}: {details}")
            except:
                pass
        
        if self.db_manager:
            try:
                self.db_manager.log_connection(
                    client_ip, 21, 'FTP', action,
                    username, "", None, country, city, details
                )
            except:
                pass
    
    def log_credentials(self, client_ip, username, password, country="Unknown", city="Unknown"):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n{'='*70}")
        print(f"[!] FTP LOGIN ATTEMPT CAPTURED!")
        print(f"{'='*70}")
        print(f"Time: {timestamp}")
        print(f"IP Address: {client_ip}")
        print(f"Location: {country}, {city}")
        print(f"{'-'*50}")
        print(f"📝 USERNAME: {username}")
        print(f"🔑 PASSWORD: {password}")
        print(f"{'='*70}\n")
        
        cred_file = "captured_credentials.txt"
        try:
            with open(cred_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*70}\n")
                f.write(f"[{timestamp}] FTP - {client_ip}\n")
                f.write(f"Location: {country}, {city}\n")
                f.write(f"Username: {username}\n")
                f.write(f"Password: {password}\n")
                f.write(f"{'='*70}\n")
                f.flush()
        except:
            pass
        
        if self.keylogger:
            try:
                additional_info = {
                    'Country': country,
                    'City': city,
                    'Service': 'FTP'
                }
                self.keylogger.log_credentials(
                    "FTP", client_ip, username, password, additional_info
                )
            except:
                pass
        
        if self.db_manager:
            try:
                self.db_manager.log_connection(
                    client_ip, 21, 'FTP', 'LOGIN_ATTEMPT',
                    username, password, None, country, city
                )
            except:
                pass
    
    def get_complete_listing(self, username):
        """Generate COMPLETE directory listing with ALL files at once"""
        perms = self.get_user_permissions(username)
        
        listing = ""
        listing += "drwxr-xr-x 2 ftp ftp 4096 Jan 1 2020 pub\n"
        listing += "-rw-r--r-- 1 ftp ftp 1024 Jan 1 2020 README.txt\n"
        listing += "-rw-r--r-- 1 ftp ftp 2048 Jan 1 2020 passwords.txt\n"
        listing += "-rw-r--r-- 1 ftp ftp 512 Jan 1 2020 config.ini\n"
        listing += "-rw-r--r-- 1 ftp ftp 128 Jan 1 2020 notice.txt\n"
        
        if perms == "full":
            listing += "-rw-r--r-- 1 ftp ftp 256 Jan 1 2020 secret.txt\n"
            listing += "drwxr-xr-x 2 ftp ftp 4096 Jan 1 2020 admin_only\n"
        
        return listing
    
    def get_file_content(self, filename):
        """Get fake file content"""
        files = {
            "README.txt": "Welcome to the FTP Server!\n\nThis is a honeypot system.\nAll activities are logged and monitored.\n\nUnauthorized access is prohibited.\n",
            "passwords.txt": "admin:password123!\nuser:password\nroot:toor\ntest:test123\nbackup:backup123\n",
            "config.ini": "[database]\nhost=localhost\nport=3306\nuser=root\npassword=secret123\n\n[app]\ndebug=true\nsecret_key=supersecretkey123\n",
            "notice.txt": "WARNING: This system is monitored.\nAll access attempts are logged.\n\nBy continuing, you consent to monitoring.\n",
            "secret.txt": "SECRET FILE - ADMIN ONLY\n\nThis file contains sensitive information.\nContact admin@company.com for access.\n\nFlag: HONEYPOT{ftp_honeypot_success}\n",
        }
        return files.get(filename, "File not found.\n")
    
    def start(self, interface='0.0.0.0', port=21):
        """Start FTP service"""
        
        def handle_client(conn, addr):
            client_ip = addr[0]
            client_port = addr[1]
            username = ""
            password = ""
            authenticated = False
            current_dir = "/"
            data_port = None
            data_ip = None
            pasv_sock = None
            data_conn = None
            pasv_port = None
            
            # Get geo location
            country = "Unknown"
            city = "Unknown"
            if self.geo_handler:
                try:
                    location = self.geo_handler.get_location(client_ip)
                    country = location.get('country', 'Unknown')
                    city = location.get('city', 'Unknown')
                except:
                    pass
            
            try:
                conn.settimeout(60)
                conn.sendall(b"220 (vsFTPd 3.0.3) FTP server ready\r\n")
                
                while True:
                    try:
                        data = conn.recv(4096).decode('utf-8', errors='ignore').strip()
                        if not data:
                            break
                        
                        # Log every command
                        if self.keylogger:
                            self.keylogger.log_keystroke("FTP", client_ip, command=data)
                        
                        print(f"  FTP: {data} from {client_ip}")
                        
                        # Parse command
                        parts = data.split(' ', 1)
                        cmd = parts[0].upper()
                        arg = parts[1] if len(parts) > 1 else ""
                        
                        # USER command
                        if cmd == "USER":
                            username = arg
                            conn.sendall(b"331 Please specify the password.\r\n")
                            self.log_activity(client_ip, username, "USER", f"Username: {username}", country, city)
                            
                            if self.keylogger:
                                self.keylogger.log_keystroke("FTP", client_ip, username=username)
                            
                        # PASS command
                        elif cmd == "PASS":
                            password = arg
                            self.log_credentials(client_ip, username, password, country, city)
                            
                            if self.keylogger:
                                self.keylogger.log_keystroke("FTP", client_ip, password=password)
                            
                            if username in self.VALID_CREDENTIALS and self.VALID_CREDENTIALS[username] == password:
                                authenticated = True
                                conn.sendall(b"230 Login successful.\r\n")
                                print(f"  ✅ FTP: Login SUCCESS for {username}")
                                self.log_activity(client_ip, username, "LOGIN", "Successful login", country, city)
                            else:
                                conn.sendall(b"530 Login incorrect.\r\n")
                                self.log_activity(client_ip, username, "LOGIN_FAILED", "Incorrect credentials", country, city)
                            
                        # QUIT command
                        elif cmd == "QUIT":
                            conn.sendall(b"221 Goodbye.\r\n")
                            self.log_activity(client_ip, username, "QUIT", "User disconnected", country, city)
                            break
                            
                        # If not authenticated
                        elif not authenticated:
                            conn.sendall(b"530 Please login with USER and PASS.\r\n")
                            
                        # SYST command
                        elif cmd == "SYST":
                            conn.sendall(b"215 UNIX Type: L8\r\n")
                            self.log_activity(client_ip, username, "SYST", "System info requested", country, city)
                            
                        # FEAT command
                        elif cmd == "FEAT":
                            features = "211-Features:\n"
                            features += " PASV\n"
                            features += " REST STREAM\n"
                            features += " SIZE\n"
                            features += "211 End\r\n"
                            conn.sendall(features.encode())
                            self.log_activity(client_ip, username, "FEAT", "Features requested", country, city)
                            
                        # EPSV - reject
                        elif cmd == "EPSV":
                            conn.sendall(b"500 EPSV not supported. Use PASV.\r\n")
                            self.log_activity(client_ip, username, "EPSV", "EPSV rejected", country, city)
                            
                        # PWD / XPWD
                        elif cmd == "PWD" or cmd == "XPWD":
                            conn.sendall(f'257 "{current_dir}" is current directory\r\n'.encode())
                            self.log_activity(client_ip, username, "PWD", f"Current: {current_dir}", country, city)
                            
                        # CWD
                        elif cmd == "CWD":
                            if arg == "/":
                                current_dir = "/"
                            elif arg == "..":
                                if current_dir != "/":
                                    current_dir = "/".join(current_dir.split('/')[:-1])
                                    if not current_dir:
                                        current_dir = "/"
                            else:
                                if current_dir == "/":
                                    current_dir = f"/{arg}"
                                else:
                                    current_dir = f"{current_dir}/{arg}"
                            conn.sendall(b'250 Directory successfully changed.\r\n')
                            self.log_activity(client_ip, username, "CWD", f"Changed to: {current_dir}", country, city)
                            
                        # LIST / NLST - SEND COMPLETE LISTING
                        elif cmd == "LIST" or cmd == "NLST":
                            # Check if we have a data connection
                            if pasv_sock:
                                # Passive mode
                                try:
                                    data_conn, data_addr = pasv_sock.accept()
                                    print(f"  FTP: Data connection from {data_addr[0]}:{data_addr[1]}")
                                    
                                    conn.sendall(b'150 Here comes the directory listing.\r\n')
                                    listing = self.get_complete_listing(username)
                                    data_conn.sendall(listing.encode())
                                    data_conn.close()
                                    conn.sendall(b'226 Directory send OK.\r\n')
                                    self.log_activity(client_ip, username, "LIST", "Directory listing sent (PASV)", country, city)
                                except Exception as e:
                                    conn.sendall(b'425 Data connection failed.\r\n')
                            elif data_port and data_ip:
                                # Active mode
                                try:
                                    data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                    data_sock.settimeout(10)
                                    data_sock.connect((data_ip, data_port))
                                    
                                    conn.sendall(b'150 Here comes the directory listing.\r\n')
                                    listing = self.get_complete_listing(username)
                                    data_sock.sendall(listing.encode())
                                    data_sock.close()
                                    conn.sendall(b'226 Directory send OK.\r\n')
                                    self.log_activity(client_ip, username, "LIST", "Directory listing sent (PORT)", country, city)
                                except Exception as e:
                                    conn.sendall(b'425 Data connection failed.\r\n')
                            else:
                                # No data connection - send directly
                                listing = self.get_complete_listing(username)
                                conn.sendall(b'150 Here comes the directory listing.\r\n')
                                conn.sendall(listing.encode())
                                conn.sendall(b'226 Directory send OK.\r\n')
                                self.log_activity(client_ip, username, "LIST", "Directory listing sent (direct)", country, city)
                            
                            # Reset data connection
                            data_port = None
                            data_ip = None
                            pasv_sock = None
                            
                        # PASV (Passive Mode)
                        elif cmd == "PASV":
                            try:
                                # Close any existing passive socket
                                if pasv_sock:
                                    try:
                                        pasv_sock.close()
                                    except:
                                        pass
                                
                                # Create passive socket
                                pasv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                pasv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                                pasv_sock.bind(('0.0.0.0', 0))
                                pasv_sock.listen(1)
                                pasv_sock.settimeout(30)
                                
                                pasv_port = pasv_sock.getsockname()[1]
                                ip_parts = client_ip.split('.')
                                ip_str = ','.join(ip_parts)
                                port_str = f"{pasv_port // 256},{pasv_port % 256}"
                                
                                response = f"227 Entering Passive Mode ({ip_str},{port_str})\r\n"
                                conn.sendall(response.encode())
                                self.log_activity(client_ip, username, "PASV", f"Passive port: {pasv_port}", country, city)
                                
                            except Exception as e:
                                print(f"  FTP PASV error: {e}")
                                conn.sendall(b'425 Can\'t open data connection.\r\n')
                                pasv_sock = None
                            
                        # PORT (Active Mode)
                        elif cmd == "PORT":
                            try:
                                nums = arg.split(',')
                                if len(nums) == 6:
                                    data_ip = f"{nums[0]}.{nums[1]}.{nums[2]}.{nums[3]}"
                                    data_port = int(nums[4]) * 256 + int(nums[5])
                                    conn.sendall(b'200 PORT command successful.\r\n')
                                    self.log_activity(client_ip, username, "PORT", f"Active mode: {data_ip}:{data_port}", country, city)
                                else:
                                    conn.sendall(b'501 Syntax error in parameters.\r\n')
                                    data_port = None
                                    data_ip = None
                            except:
                                conn.sendall(b'501 Syntax error in parameters.\r\n')
                                data_port = None
                                data_ip = None
                            
                        # RETR (Download file)
                        elif cmd == "RETR":
                            perms = self.get_user_permissions(username)
                            if perms == "read" or perms == "full":
                                self.log_activity(client_ip, username, "RETR", f"Download: {arg}", country, city)
                                
                                # Check if we have a data connection
                                if pasv_sock:
                                    # Passive mode
                                    try:
                                        data_conn, data_addr = pasv_sock.accept()
                                        print(f"  FTP: Data connection from {data_addr[0]}:{data_addr[1]}")
                                        
                                        conn.sendall(b'150 Opening BINARY mode data connection.\r\n')
                                        content = self.get_file_content(arg)
                                        data_conn.sendall(content.encode())
                                        data_conn.close()
                                        conn.sendall(b'226 Transfer complete.\r\n')
                                        self.log_activity(client_ip, username, "RETR", f"Downloaded: {arg}", country, city)
                                        
                                        pasv_sock = None
                                    except Exception as e:
                                        conn.sendall(b'425 Data connection failed.\r\n')
                                elif data_port and data_ip:
                                    # Active mode
                                    try:
                                        data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                        data_sock.settimeout(10)
                                        data_sock.connect((data_ip, data_port))
                                        
                                        conn.sendall(b'150 Opening BINARY mode data connection.\r\n')
                                        content = self.get_file_content(arg)
                                        data_sock.sendall(content.encode())
                                        data_sock.close()
                                        conn.sendall(b'226 Transfer complete.\r\n')
                                        self.log_activity(client_ip, username, "RETR", f"Downloaded: {arg}", country, city)
                                        
                                        data_port = None
                                        data_ip = None
                                    except Exception as e:
                                        conn.sendall(b'425 Data connection failed.\r\n')
                                else:
                                    # No data connection - send on control
                                    conn.sendall(b'150 Opening BINARY mode data connection.\r\n')
                                    content = self.get_file_content(arg)
                                    conn.sendall(content.encode())
                                    conn.sendall(b'226 Transfer complete.\r\n')
                                    self.log_activity(client_ip, username, "RETR", f"Downloaded: {arg}", country, city)
                            else:
                                conn.sendall(b'550 Permission denied.\r\n')
                                
                        # STOR (Upload file)
                        elif cmd == "STOR":
                            perms = self.get_user_permissions(username)
                            if perms == "full":
                                self.log_activity(client_ip, username, "STOR", f"Upload: {arg}", country, city)
                                
                                # Check if we have a data connection
                                if pasv_sock:
                                    try:
                                        data_conn, data_addr = pasv_sock.accept()
                                        print(f"  FTP: Data connection from {data_addr[0]}:{data_addr[1]}")
                                        
                                        conn.sendall(b'150 Ok to send data.\r\n')
                                        data = data_conn.recv(1024)
                                        data_conn.close()
                                        conn.sendall(b'226 Transfer complete.\r\n')
                                        self.log_activity(client_ip, username, "STOR", f"Uploaded: {arg}", country, city)
                                        
                                        pasv_sock = None
                                    except Exception as e:
                                        conn.sendall(b'425 Data connection failed.\r\n')
                                elif data_port and data_ip:
                                    try:
                                        data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                        data_sock.settimeout(10)
                                        data_sock.connect((data_ip, data_port))
                                        
                                        conn.sendall(b'150 Ok to send data.\r\n')
                                        data = data_sock.recv(1024)
                                        data_sock.close()
                                        conn.sendall(b'226 Transfer complete.\r\n')
                                        self.log_activity(client_ip, username, "STOR", f"Uploaded: {arg}", country, city)
                                    except Exception as e:
                                        conn.sendall(b'425 Data connection failed.\r\n')
                                else:
                                    # No data connection - simulate upload
                                    conn.sendall(b'150 Ok to send data.\r\n')
                                    time.sleep(0.5)
                                    conn.sendall(b'226 Transfer complete.\r\n')
                                    self.log_activity(client_ip, username, "STOR", f"Uploaded: {arg}", country, city)
                            else:
                                conn.sendall(b'550 Permission denied.\r\n')
                                
                        # SIZE
                        elif cmd == "SIZE":
                            if arg in ["README.txt", "passwords.txt", "config.ini", "notice.txt", "secret.txt"]:
                                conn.sendall(b'213 1024\r\n')
                            else:
                                conn.sendall(b'550 File not found.\r\n')
                            self.log_activity(client_ip, username, "SIZE", f"Size request: {arg}", country, city)
                            
                        # TYPE
                        elif cmd == "TYPE":
                            if arg == "I" or arg == "L8":
                                conn.sendall(b'200 Switching to Binary mode.\r\n')
                            else:
                                conn.sendall(b'200 Switching to ASCII mode.\r\n')
                            self.log_activity(client_ip, username, "TYPE", f"Type: {arg}", country, city)
                            
                        # DELE (Delete)
                        elif cmd == "DELE":
                            perms = self.get_user_permissions(username)
                            if perms == "full":
                                self.log_activity(client_ip, username, "DELE", f"Delete: {arg}", country, city)
                                conn.sendall(b'250 Deleted successfully.\r\n')
                            else:
                                conn.sendall(b'550 Permission denied.\r\n')
                                
                        # MKD (Make Directory)
                        elif cmd == "MKD" or cmd == "XMDK":
                            perms = self.get_user_permissions(username)
                            if perms == "full":
                                self.log_activity(client_ip, username, "MKD", f"Create dir: {arg}", country, city)
                                conn.sendall(b'257 Directory created.\r\n')
                            else:
                                conn.sendall(b'550 Permission denied.\r\n')
                                
                        # RMD (Remove Directory)
                        elif cmd == "RMD" or cmd == "XRMD":
                            perms = self.get_user_permissions(username)
                            if perms == "full":
                                self.log_activity(client_ip, username, "RMD", f"Remove dir: {arg}", country, city)
                                conn.sendall(b'250 Directory removed.\r\n')
                            else:
                                conn.sendall(b'550 Permission denied.\r\n')
                                
                        # RNFR / RNTO (Rename)
                        elif cmd == "RNFR":
                            self.log_activity(client_ip, username, "RNFR", f"Rename from: {arg}", country, city)
                            conn.sendall(b'350 Ready for RNTO.\r\n')
                            
                        elif cmd == "RNTO":
                            self.log_activity(client_ip, username, "RNTO", f"Rename to: {arg}", country, city)
                            conn.sendall(b'550 Permission denied.\r\n')
                            
                        # NOOP
                        elif cmd == "NOOP":
                            conn.sendall(b'200 NOOP ok.\r\n')
                            
                        # HELP
                        elif cmd == "HELP":
                            help_text = "214-The following commands are recognized:\n"
                            help_text += " USER PASS QUIT SYST FEAT PWD CWD LIST NLST\n"
                            help_text += " RETR STOR DELE MKD RMD RNFR RNTO TYPE\n"
                            help_text += " PASV PORT SIZE HELP NOOP\n"
                            help_text += "214 Help OK.\r\n"
                            conn.sendall(help_text.encode())
                            self.log_activity(client_ip, username, "HELP", "Help requested", country, city)
                            
                        # STAT
                        elif cmd == "STAT":
                            conn.sendall(b'211-FTP server status:\n')
                            conn.sendall(b' Connected to '.encode() + client_ip.encode() + b'\n')
                            conn.sendall(b' Logged in as: '.encode() + username.encode() + b'\n')
                            conn.sendall(b' Type: Binary\n')
                            conn.sendall(b'211 End of status\r\n')
                            self.log_activity(client_ip, username, "STAT", "Status requested", country, city)
                            
                        # Unknown commands
                        else:
                            conn.sendall(b'502 Command not implemented.\r\n')
                            self.log_activity(client_ip, username, "UNKNOWN", f"Unknown: {cmd}", country, city)
                            
                    except socket.timeout:
                        break
                    except Exception as e:
                        print(f"  FTP handler error: {e}")
                        break
                        
            except Exception as e:
                print(f"  FTP client handler error: {e}")
            finally:
                try:
                    if pasv_sock:
                        pasv_sock.close()
                    if data_conn:
                        data_conn.close()
                    conn.close()
                except:
                    pass
        
        def server_loop():
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.sock.bind((interface, port))
                self.sock.listen(10)
                self.sock.settimeout(1)
                
                print(f"  ✅ FTP Server RUNNING on port {port}")
                print(f"     Serving: {self.ftp_root}")
                print(f"     Test: ftp {interface if interface != '0.0.0.0' else 'localhost'} {port}")
                print(f"\n     Valid Credentials:")
                for user, pwd in self.VALID_CREDENTIALS.items():
                    perm = self.USER_PERMS.get(user, "read")
                    print(f"       • {user} / {pwd if pwd else '(empty)'} [{perm}]")
                
                self.create_fake_files()
                print(f"\n     FTP Server is ready!")
                print(f"     ✓ All files shown in one listing")
                print(f"     ✓ Supports: ls, dir, get, put, more, cd, pwd, delete")
                print(f"     ✓ To download: get <filename>")
                print(f"     ✓ To upload: put <filename>")
                
                while self.active:
                    try:
                        conn, addr = self.sock.accept()
                        print(f"  FTP: New connection from {addr[0]}:{addr[1]}")
                        client_thread = threading.Thread(target=handle_client, args=(conn, addr))
                        client_thread.daemon = True
                        client_thread.start()
                        self.threads.append(client_thread)
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if self.active:
                            print(f"  FTP Server error: {e}")
                        break
                        
            except OSError as e:
                if e.errno == 98:
                    print(f"  ❌ Port {port} is already in use!")
                    print(f"     Solution: sudo fuser -k {port}/tcp")
                else:
                    print(f"  ❌ FTP Server error: {e}")
            except Exception as e:
                print(f"  ❌ FTP Server error: {e}")
            finally:
                if self.sock:
                    try:
                        self.sock.close()
                    except:
                        pass
        
        # Check if port is available
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.settimeout(1)
            result = test_sock.connect_ex((interface, port))
            test_sock.close()
            
            if result == 0:
                print(f"  ❌ Port {port} is already in use!")
                print(f"     Solution: sudo fuser -k {port}/tcp")
                return None
        except:
            pass
        
        self.active = True
        thread = threading.Thread(target=server_loop, daemon=True)
        thread.start()
        time.sleep(2)
        return thread
    
    def create_fake_files(self):
        """Create fake files in FTP root"""
        os.makedirs(self.ftp_root, exist_ok=True)
        
        fake_files = {
            "README.txt": "Welcome to FTP Server\nThis is a honeypot system.\nAll activities are logged and monitored.\n",
            "passwords.txt": "admin:password123!\nuser:password\nroot:toor\ntest:test123\n",
            "config.ini": "[database]\nhost=localhost\nuser=root\npassword=secret123\n",
            "notice.txt": "All access attempts are logged.\n",
            "secret.txt": "Only admin users can see this file.\nThis is a decoy file.\n",
        }
        
        for filename, content in fake_files.items():
            filepath = os.path.join(self.ftp_root, filename)
            if not os.path.exists(filepath):
                try:
                    with open(filepath, 'w') as f:
                        f.write(content)
                except:
                    pass
    
    def stop(self):
        self.active = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        
        for thread in self.threads:
            try:
                thread.join(timeout=1)
            except:
                pass
