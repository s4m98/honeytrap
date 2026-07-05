# ============= HTTP HONEYPOT SERVICE =============
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import os
import json
import time
import random
import logging
import threading
from urllib.parse import parse_qs, unquote
import socket
import re
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DEFAULT_CREDENTIALS

logger = logging.getLogger(__name__)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads"""
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 100
    
    def server_bind(self):
        """Bind server with SO_REUSEADDR option"""
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()

class HoneypotHTTPHandler(BaseHTTPRequestHandler):
    server_version = "Apache/2.4.41"
    sys_version = ""
    
    def log_message(self, format, *args):
        pass
    
    def parse_user_agent(self, user_agent):
        """Parse User-Agent string to extract device info"""
        info = {
            'browser': 'Unknown',
            'os': 'Unknown',
            'device': 'Unknown',
            'is_mobile': False
        }
        
        # Detect browser
        if 'Chrome' in user_agent and 'Edg' not in user_agent:
            info['browser'] = 'Chrome'
        elif 'Firefox' in user_agent:
            info['browser'] = 'Firefox'
        elif 'Safari' in user_agent and 'Chrome' not in user_agent:
            info['browser'] = 'Safari'
        elif 'Edg' in user_agent:
            info['browser'] = 'Edge'
        elif 'Opera' in user_agent or 'OPR' in user_agent:
            info['browser'] = 'Opera'
        elif 'MSIE' in user_agent or 'Trident' in user_agent:
            info['browser'] = 'Internet Explorer'
        
        # Detect OS
        if 'Windows' in user_agent:
            info['os'] = 'Windows'
            if 'Windows NT 10.0' in user_agent:
                info['os'] = 'Windows 10'
            elif 'Windows NT 6.1' in user_agent:
                info['os'] = 'Windows 7'
            elif 'Windows NT 6.2' in user_agent:
                info['os'] = 'Windows 8'
            elif 'Windows NT 6.3' in user_agent:
                info['os'] = 'Windows 8.1'
        elif 'Mac OS X' in user_agent or 'macOS' in user_agent:
            info['os'] = 'macOS'
        elif 'Linux' in user_agent and 'Android' not in user_agent:
            info['os'] = 'Linux'
        elif 'Android' in user_agent:
            info['os'] = 'Android'
            info['is_mobile'] = True
        elif 'iOS' in user_agent or 'iPhone' in user_agent or 'iPad' in user_agent:
            info['os'] = 'iOS'
            info['is_mobile'] = True
        
        # Detect device type
        if 'Mobile' in user_agent or 'Android' in user_agent and 'Mobile' in user_agent:
            info['device'] = 'Mobile Phone'
            info['is_mobile'] = True
        elif 'iPad' in user_agent:
            info['device'] = 'Tablet'
            info['is_mobile'] = True
        elif 'Tablet' in user_agent:
            info['device'] = 'Tablet'
            info['is_mobile'] = True
        else:
            info['device'] = 'Desktop'
        
        return info
    
    def handle_one_request(self):
        """Handle a single HTTP request with better error handling"""
        try:
            self.raw_requestline = self.rfile.readline(65537)
            if len(self.raw_requestline) > 65536:
                self.requestline = ''
                self.request_version = ''
                self.command = ''
                self.send_error(414)
                return
            if not self.raw_requestline:
                self.close_connection = True
                return
            if not self.parse_request():
                return
            
            method = self.command
            if method == "GET":
                self.do_GET()
            elif method == "POST":
                self.do_POST()
            elif method == "HEAD":
                self.do_HEAD()
            elif method == "OPTIONS":
                self.send_options_response()
            else:
                self.send_error(501, "Unsupported method (%r)" % method)
                
            self.wfile.flush()
        except (socket.timeout, ConnectionResetError, BrokenPipeError):
            self.close_connection = True
            return
        except Exception as e:
            self.close_connection = True
            return
    
    def send_options_response(self):
        self.send_response(200)
        self.send_header('Allow', 'GET, POST, HEAD, OPTIONS')
        self.send_header('Content-Length', '0')
        self.end_headers()
    
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
    
    def do_GET(self):
        try:
            web_root = getattr(self.server, 'web_root', None)
            
            # Always create web_root if it doesn't exist
            if web_root and not os.path.exists(web_root):
                os.makedirs(web_root, exist_ok=True)
                self.create_default_pages(web_root)
            
            client_info = self.get_client_info()
            
            # Log the request
            if hasattr(self.server, 'keylogger'):
                self.server.keylogger.log_activity(
                    "HTTP", client_info['ip'], "GET_REQUEST", 
                    f"Path: {self.path}\nUser-Agent: {client_info['user_agent']}\nDevice: {client_info['device_info']['device']}\nOS: {client_info['device_info']['os']}"
                )
            
            # Serve the login page for root path
            if self.path == "/" or self.path == "" or self.path == "/login":
                self.send_login_page(web_root)
            else:
                self.send_404()
                
        except Exception as e:
            logger.error(f"Error in do_GET: {e}")
            self.send_404()
    
    def create_default_pages(self, web_root):
        """Create default HTML pages"""
        login_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Secure Login</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .login-container {
            background: white;
            border-radius: 10px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
            padding: 40px;
            animation: fadeIn 0.5s ease-in;
        }
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        h2 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
            font-weight: 600;
        }
        .input-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }
        input {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e1e1e1;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.3s ease;
            outline: none;
        }
        input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s ease;
        }
        button:hover {
            transform: translateY(-2px);
        }
        button:active {
            transform: translateY(0);
        }
        .hint {
            text-align: center;
            margin-top: 20px;
            color: #888;
            font-size: 12px;
        }
        .error {
            color: #e74c3c;
            text-align: center;
            margin-top: 10px;
            font-size: 12px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h2>🔐 Secure Access Portal</h2>
        <form method="POST" action="/login" onsubmit="return validateForm()">
            <div class="input-group">
                <label>Username</label>
                <input type="text" id="username" name="username" placeholder="Enter your username" required autocomplete="off">
            </div>
            <div class="input-group">
                <label>Password</label>
                <input type="password" id="password" name="password" placeholder="Enter your password" required>
            </div>
            <button type="submit">Sign In</button>
            <div class="hint">
                <p>Demo: admin / password123!</p>
            </div>
            <div id="errorMsg" class="error"></div>
        </form>
    </div>
    <script>
        function validateForm() {
            var username = document.getElementById('username').value;
            var password = document.getElementById('password').value;
            if (!username || !password) {
                document.getElementById('errorMsg').style.display = 'block';
                document.getElementById('errorMsg').innerHTML = 'Please enter both username and password';
                return false;
            }
            return true;
        }
    </script>
</body>
</html>"""
        
        # Create login page
        login_path = os.path.join(web_root, "login.html")
        with open(login_path, 'w', encoding='utf-8') as f:
            f.write(login_html)
        
        # Create index.html that redirects to login
        index_path = os.path.join(web_root, "index.html")
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0; url=/login">
    <title>Redirecting...</title>
</head>
<body>
    <p>Redirecting to login page...</p>
</body>
</html>""")
    
    def send_login_page(self, web_root):
        """Send the login page"""
        try:
            # Check if custom login page exists
            login_file = os.path.join(web_root, "login.html")
            if os.path.exists(login_file):
                with open(login_file, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', len(content))
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                self.wfile.write(content)
            else:
                # Create default page on the fly
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                
                html = """<!DOCTYPE html>
<html>
<head><title>Login</title>
<style>
body { font-family: Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; padding: 0; }
.login-container { background: white; padding: 40px; width: 350px; margin: 100px auto; border-radius: 10px; }
h2 { text-align: center; }
input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
button { background: #4CAF50; color: white; padding: 10px; width: 100%; border: none; border-radius: 5px; cursor: pointer; }
</style>
</head>
<body>
<div class="login-container">
<h2>Login</h2>
<form method="POST" action="/login">
<input type="text" name="username" placeholder="Username"><br>
<input type="password" name="password" placeholder="Password"><br>
<button type="submit">Login</button>
</form>
</div>
</body>
</html>"""
                self.wfile.write(html.encode('utf-8'))
        except Exception as e:
            logger.error(f"Error sending login page: {e}")
            self.send_404()
    
    def do_POST(self):
        try:
            if self.path == "/login":
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0 and content_length < 10000:
                    post_data = self.rfile.read(content_length).decode('utf-8', errors='ignore')
                    self.handle_login(post_data)
                else:
                    self.send_error(400, "Bad Request")
            else:
                self.send_404()
        except Exception as e:
            logger.error(f"Error in do_POST: {e}")
            self.send_404()
    
    def get_client_info(self):
        """Get comprehensive client information including device details"""
        client_ip = self.client_address[0]
        user_agent = self.headers.get('User-Agent', 'Unknown')
        referer = self.headers.get('Referer', 'Unknown')
        accept_language = self.headers.get('Accept-Language', 'Unknown')
        accept_encoding = self.headers.get('Accept-Encoding', 'Unknown')
        
        # Parse device info from user agent
        device_info = self.parse_user_agent(user_agent)
        
        # Get geo location
        location = {'country': 'Unknown', 'city': 'Unknown', 'latitude': 0, 'longitude': 0, 'isp': 'Unknown'}
        if hasattr(self.server, 'geo_handler'):
            geo_info = self.server.geo_handler.get_location(client_ip)
            location = {
                'country': geo_info.get('country', 'Unknown'),
                'city': geo_info.get('city', 'Unknown'),
                'latitude': geo_info.get('latitude', 0),
                'longitude': geo_info.get('longitude', 0),
                'isp': geo_info.get('isp', 'Unknown')
            }
        
        return {
            'ip': client_ip,
            'user_agent': user_agent,
            'referer': referer,
            'accept_language': accept_language,
            'accept_encoding': accept_encoding,
            'device_info': device_info,
            'location': location
        }
    
    def handle_login(self, post_data):
        """Handle login POST request - captures complete credentials"""
        try:
            client_info = self.get_client_info()
            
            # Parse POST data - get complete credentials
            username = ""
            password = ""
            try:
                params = parse_qs(post_data)
                username = unquote(params.get('username', [''])[0])
                password = unquote(params.get('password', [''])[0])
            except:
                # Manual parsing fallback
                for param in post_data.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        if key == 'username':
                            username = value.replace('+', ' ')
                        elif key == 'password':
                            password = value
            
            # Log the complete credentials (not individual characters)
            print(f"\n{'='*60}")
            print(f"[!] HTTP Login Attempt Captured!")
            print(f"{'='*60}")
            print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"IP Address: {client_info['ip']}")
            print(f"Location: {client_info['location']['country']}, {client_info['location']['city']}")
            print(f"ISP: {client_info['location']['isp']}")
            print(f"{'-'*40}")
            print(f"📝 USERNAME: {username}")
            print(f"🔑 PASSWORD: {password}")
            print(f"{'-'*40}")
            print(f"Device Information:")
            print(f"  • Device Type: {client_info['device_info']['device']}")
            print(f"  • Operating System: {client_info['device_info']['os']}")
            print(f"  • Browser: {client_info['device_info']['browser']}")
            print(f"  • Mobile: {'Yes' if client_info['device_info']['is_mobile'] else 'No'}")
            print(f"{'-'*40}")
            print(f"User-Agent: {client_info['user_agent']}")
            print(f"Referer: {client_info['referer']}")
            print(f"Accept Language: {client_info['accept_language']}")
            print(f"{'='*60}\n")
            
            logger.info(f"HTTP Login attempt from {client_info['ip']} - Username: {username}, Password: {password}")
            
            # Prepare additional info with complete device details
            additional_info = {
                'User-Agent': client_info['user_agent'],
                'Referer': client_info['referer'],
                'Accept-Language': client_info['accept_language'],
                'Country': client_info['location']['country'],
                'City': client_info['location']['city'],
                'ISP': client_info['location']['isp'],
                'Latitude': str(client_info['location']['latitude']),
                'Longitude': str(client_info['location']['longitude']),
                'Device Type': client_info['device_info']['device'],
                'Operating System': client_info['device_info']['os'],
                'Browser': client_info['device_info']['browser'],
                'Is Mobile': str(client_info['device_info']['is_mobile'])
            }
            
            # Save to database
            if hasattr(self.server, 'db_manager'):
                self.server.db_manager.log_connection(
                    client_info['ip'], 80, 'HTTP', 'LOGIN_ATTEMPT',
                    username, password, client_info['user_agent'],
                    client_info['location']['country'], client_info['location']['city'],
                    f"Device: {client_info['device_info']['device']}, OS: {client_info['device_info']['os']}, Browser: {client_info['device_info']['browser']}"
                )
            
            # Save to keylogger (complete credentials at once)
            if hasattr(self.server, 'keylogger'):
                self.server.keylogger.log_credentials(
                    "HTTP", client_info['ip'], username, password, additional_info
                )
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            time.sleep(random.uniform(0.5, 1.5))
            
            # Return fake response with device info shown
            html = f"""<!DOCTYPE html>
<html>
<head><title>Access Granted</title>
<style>
body {{ font-family: Arial; text-align: center; padding: 50px; background: #f5f5f5; }}
.message {{ background: white; padding: 30px; border-radius: 10px; max-width: 600px; margin: 0 auto; box-shadow: 0 0 20px rgba(0,0,0,0.1); }}
h2 {{ color: #28a745; }}
.info {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: left; }}
.warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; text-align: left; }}
</style>
</head>
<body>
<div class="message">
<h2>✓ Access Granted</h2>
<div class="warning">
<strong>⚠️ Security Notice:</strong> This is a honeypot system. All activities are monitored and logged.
</div>
<div class="info">
<p><strong>Welcome, {username}!</strong></p>
<p><strong>Your Information:</strong></p>
<ul>
<li>IP Address: {client_info['ip']}</li>
<li>Location: {client_info['location']['country']}, {client_info['location']['city']}</li>
<li>Device: {client_info['device_info']['device']}</li>
<li>Operating System: {client_info['device_info']['os']}</li>
<li>Browser: {client_info['device_info']['browser']}</li>
<li>User-Agent: {client_info['user_agent'][:100]}...</li>
</ul>
</div>
<p><a href="/login">Logout</a></p>
</div>
</body>
</html>"""
            self.wfile.write(html.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error handling login: {e}")
            self.send_404()
    
    def send_404(self):
        try:
            self.send_response(404)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>404 - Page Not Found</h1></body></html>")
        except Exception:
            pass

class HTTPService:
    def __init__(self, web_root, db_manager, keylogger, geo_handler):
        self.web_root = web_root
        self.db_manager = db_manager
        self.keylogger = keylogger
        self.geo_handler = geo_handler
        self.active = False
        self.server = None
    
    def start(self, interface='0.0.0.0', port=80):
        """Start HTTP service"""
        def http_loop():
            try:
                # Create web_root directory
                os.makedirs(self.web_root, exist_ok=True)
                
                # Create server with proper socket options
                self.server = ThreadedHTTPServer((interface, port), HoneypotHTTPHandler)
                self.server.db_manager = self.db_manager
                self.server.keylogger = self.keylogger
                self.server.geo_handler = self.geo_handler
                self.server.web_root = self.web_root
                self.server.timeout = 30
                
                print(f"  ✅ HTTP Server on port {port}")
                print(f"     Serving: {self.web_root}")
                print(f"     URL: http://{interface if interface != '0.0.0.0' else 'localhost'}:{port}")
                
                while self.active:
                    try:
                        self.server.handle_request()
                    except KeyboardInterrupt:
                        break
                    except Exception as e:
                        if self.active:
                            time.sleep(0.1)
                
            except OSError as e:
                if e.errno == 98:  # Address already in use
                    print(f"  ❌ Port {port} is already in use")
                    print(f"     Try: sudo lsof -i :{port} to see what's using it")
                else:
                    print(f"  ❌ HTTP Server error: {e}")
            except Exception as e:
                print(f"  ❌ HTTP Server error: {e}")
            finally:
                if self.server:
                    try:
                        self.server.server_close()
                    except:
                        pass
        
        self.active = True
        thread = threading.Thread(target=http_loop, daemon=True)
        thread.start()
        time.sleep(0.5)  # Give time for server to start
        return thread
    
    def stop(self):
        """Stop HTTP service"""
        self.active = False
        if self.server:
            try:
                self.server.server_close()
            except:
                pass
