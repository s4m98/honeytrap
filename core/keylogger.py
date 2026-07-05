# ============= KEYLOGGER =============
import threading
from datetime import datetime
from collections import defaultdict
import os

class ServiceKeylogger:
    def __init__(self, service_logs, credentials_file):
        self.service_logs = service_logs
        self.credentials_file = credentials_file
        self.pending_credentials = defaultdict(dict)
        self.buffer_lock = threading.Lock()
        
        # Create logs directory
        os.makedirs("logs", exist_ok=True)
        
        # Initialize all log files
        for service, filename in self.service_logs.items():
            try:
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with open(filename, 'a', encoding='utf-8') as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"{service} Logger started at {datetime.now()}\n")
                    f.write(f"{'='*60}\n\n")
            except Exception as e:
                print(f"Error initializing log for {service}: {e}")
    
    def log_credentials(self, service, client_ip, username, password, additional_info=None):
        """Log captured credentials as complete entries"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file = self.service_logs.get(service, self.service_logs.get("GENERIC", "logs/generic_logs.txt"))
        
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            # Write to service-specific log
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"[{timestamp}] CREDENTIALS CAPTURED - {service}\n")
                f.write(f"IP Address: {client_ip}\n")
                f.write(f"Username: {username}\n")
                f.write(f"Password: {password}\n")
                if additional_info:
                    for key, value in additional_info.items():
                        f.write(f"{key}: {value}\n")
                f.write(f"{'='*50}\n")
                f.flush()
            
            # Write to combined credentials file
            with open(self.credentials_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"[{timestamp}] {service} - {client_ip}\n")
                f.write(f"Username: {username}\n")
                f.write(f"Password: {password}\n")
                if additional_info:
                    f.write(f"Additional Info:\n")
                    for key, value in additional_info.items():
                        f.write(f"  {key}: {value}\n")
                f.write(f"{'='*60}\n")
                f.flush()
                
        except Exception as e:
            print(f"Error logging credentials: {e}")
    
    def log_connection(self, service, client_ip, port, additional_info=None):
        """Log connection attempt"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file = self.service_logs.get(service, self.service_logs.get("GENERIC", "logs/generic_logs.txt"))
        
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n[CONNECTION] {timestamp}\n")
                f.write(f"Service: {service}\n")
                f.write(f"Source IP: {client_ip}:{port}\n")
                if additional_info:
                    for key, value in additional_info.items():
                        f.write(f"{key}: {value}\n")
                f.write("-" * 40 + "\n")
                f.flush()
        except:
            pass
    
    def log_activity(self, service, client_ip, activity_type, details):
        """Log general activity"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file = self.service_logs.get(service, self.service_logs.get("GENERIC", "logs/generic_logs.txt"))
        
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n[{timestamp}] {activity_type}\n")
                f.write(f"IP: {client_ip}\n")
                f.write(f"Details: {details}\n")
                f.write("-" * 40 + "\n")
                f.flush()
        except:
            pass
    
    def log_keystroke(self, service, client_ip, username=None, password=None, command=None):
        """Log individual keystrokes or commands"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file = self.service_logs.get(service, self.service_logs.get("GENERIC", "logs/generic_logs.txt"))
        
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] KEYSTROKE - {client_ip}\n")
                if username:
                    f.write(f"    Username: {username}\n")
                if password:
                    f.write(f"    Password: {password}\n")
                if command:
                    f.write(f"    Command: {command}\n")
                f.write("-" * 40 + "\n")
                f.flush()
        except:
            pass
