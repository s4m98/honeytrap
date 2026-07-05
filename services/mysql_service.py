# ============= MYSQL HONEYPOT SERVICE (FULLY WORKING) =============
import socket
import threading
import time
import logging
import os
import sys
import struct
import random
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


class MySQLPacketReader:
    """Reads MySQL protocol packets off a raw socket with proper framing."""

    def __init__(self, conn):
        self.conn = conn
        self.buffer = bytearray()

    def read_packet(self):
        """Return the next complete MySQL packet (header + payload), or None on EOF."""
        while True:
            if len(self.buffer) >= 4:
                payload_len = self.buffer[0] | (self.buffer[1] << 8) | (self.buffer[2] << 16)
                total_len = 4 + payload_len
                if len(self.buffer) >= total_len:
                    packet = bytes(self.buffer[:total_len])
                    del self.buffer[:total_len]
                    return packet
            chunk = self.conn.recv(4096)
            if not chunk:
                return None
            self.buffer.extend(chunk)


class MySQLService:
    """MySQL honeypot - fully working with correct packet framing"""

    def __init__(self, db_manager, keylogger, geo_handler):
        self.db_manager = db_manager
        self.keylogger = keylogger
        self.geo_handler = geo_handler
        self.active = False
        self.sock = None
        self.threads = []

        self.server_version = "8.0.25-0ubuntu0.20.04.1"
        self.connection_id = 0

        self.VALID_CREDENTIALS = {
            "admin": "admin@123",
            "root": "myr00t",
        }

        self.DATABASES = ["information_schema", "mysql", "wordpress"]

        self.TABLES = {
            "information_schema": ["SCHEMATA", "TABLES", "COLUMNS", "STATISTICS"],
            "mysql": ["user", "db", "tables_priv", "columns_priv"],
            "wordpress": ["wp_users", "wp_posts", "wp_options", "wp_postmeta", "wp_comments", "wp_terms"],
        }

        self.TABLE_STRUCTURES = {
            "wp_users": [
                ("ID", "int(11)", "NO", "PRI"),
                ("user_login", "varchar(60)", "NO", ""),
                ("user_pass", "varchar(255)", "NO", ""),
                ("user_email", "varchar(100)", "NO", ""),
                ("user_registered", "datetime", "NO", ""),
                ("user_status", "int(11)", "NO", ""),
                ("display_name", "varchar(250)", "NO", "")
            ],
            "user": [
                ("Host", "char(60)", "NO", "PRI"),
                ("User", "char(32)", "NO", "PRI"),
                ("Password", "char(41)", "NO", ""),
                ("Select_priv", "enum('N','Y')", "NO", ""),
                ("Insert_priv", "enum('N','Y')", "NO", ""),
            ]
        }

        self.DATA = {
            "wp_users": [
                ("1", "admin", "$2y$10$abcdefghijklmnopqrstuvwxyz1234567890", "admin@wordpress.com", "2024-01-01 00:00:00", "0", "Administrator"),
                ("2", "editor", "$2y$10$zyxwvutsrqponmlkjihgfedcba0987654321", "editor@wordpress.com", "2024-01-02 00:00:00", "0", "Editor"),
                ("3", "subscriber", "$2y$10$qwertyuiopasdfghjklzxcvbnm1234567890", "user@wordpress.com", "2024-01-03 00:00:00", "0", "Subscriber"),
            ],
            "user": [
                ("localhost", "root", "*81F5E21E35407D884A6CD4A731AEBFB6AF209E1B", "Y", "Y"),
                ("%", "admin", "*81F5E21E35407D884A6CD4A731AEBFB6AF209E1B", "Y", "Y"),
            ]
        }

    # ---------------- logging ----------------

    def log_activity(self, client_ip, username, action, details, country="Unknown", city="Unknown"):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"  MySQL: {action} - {username} ({client_ip}) - {details}")

        log_file = "logs/mysql_logs.txt"
        os.makedirs("logs", exist_ok=True)
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {action} - {username} ({client_ip}) - {details}\n")
                f.flush()
        except Exception:
            pass

        if self.keylogger:
            try:
                self.keylogger.log_activity("MySQL", client_ip, action, f"{username}: {details}")
            except Exception:
                pass

        if self.db_manager:
            try:
                self.db_manager.log_connection(
                    client_ip, 3306, 'MySQL', action,
                    username, "", None, country, city, details
                )
            except Exception:
                pass

    def log_credentials(self, client_ip, username, password, country="Unknown", city="Unknown", success=False):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        status = "SUCCESS" if success else "FAILED"
        print(f"\n{'='*70}")
        print(f"[!] MYSQL LOGIN {status}!")
        print(f"{'='*70}")
        print(f"Time: {timestamp}")
        print(f"IP Address: {client_ip}")
        print(f"Location: {country}, {city}")
        print(f"{'-'*50}")
        print(f"USERNAME: {username}")
        print(f"PASSWORD HASH: {password[:50]}..." if len(password) > 50 else f"PASSWORD: {password}")
        print(f"{'='*70}\n")

        cred_file = "captured_credentials.txt"
        try:
            with open(cred_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*70}\n")
                f.write(f"[{timestamp}] MySQL {status} - {client_ip}\n")
                f.write(f"Location: {country}, {city}\n")
                f.write(f"Username: {username}\n")
                f.write(f"Password: {password}\n")
                f.write(f"{'='*70}\n")
                f.flush()
        except Exception:
            pass

        if self.keylogger:
            try:
                additional_info = {
                    'Country': country,
                    'City': city,
                    'Service': 'MySQL',
                    'Status': status
                }
                self.keylogger.log_credentials(
                    "MySQL", client_ip, username, password, additional_info
                )
            except Exception:
                pass

        if self.db_manager:
            try:
                self.db_manager.log_connection(
                    client_ip, 3306, 'MySQL', f'LOGIN_{status}',
                    username, password, None, country, city
                )
            except Exception:
                pass

    # ---------------- server lifecycle ----------------

    def start(self, interface='0.0.0.0', port=3306):
        def handle_client(conn, addr):
            client_ip = addr[0]
            client_port = addr[1]

            session = {
                "authenticated": False,
                "current_user": None,
                "current_db": None,
                "sequence_id": 0,
            }

            country = "Unknown"
            city = "Unknown"
            if self.geo_handler:
                try:
                    location = self.geo_handler.get_location(client_ip)
                    country = location.get('country', 'Unknown')
                    city = location.get('city', 'Unknown')
                except Exception:
                    pass

            try:
                conn.settimeout(60)
                connection_id = random.randint(1, 9999)
                reader = MySQLPacketReader(conn)

                self.send_handshake(conn, client_ip, country, city, connection_id, session)

                data = reader.read_packet()
                if not data:
                    return

                if not self.handle_login(conn, data, client_ip, client_port, country, city, session):
                    conn.close()
                    return

                while session["authenticated"]:
                    try:
                        data = reader.read_packet()
                        if not data:
                            break
                        self.handle_query(conn, data, client_ip, country, city, session)
                    except socket.timeout:
                        break
                    except Exception as e:
                        print(f"  MySQL query error: {e}")
                        break

                time.sleep(0.5)

            except socket.timeout:
                pass
            except Exception as e:
                print(f"  MySQL handler error: {e}")
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

        def server_loop():
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.sock.bind((interface, port))
                self.sock.listen(10)
                self.sock.settimeout(1)

                print(f"  MySQL Server RUNNING on port {port}")
                print(f"     Test: mysql -h {interface if interface != '0.0.0.0' else 'localhost'} -P {port} -u root -p")
                print(f"\n     VALID CREDENTIALS:")
                for user, pwd in self.VALID_CREDENTIALS.items():
                    print(f"       - {user} : {pwd}")

                while self.active:
                    try:
                        conn, addr = self.sock.accept()
                        print(f"  MySQL: New connection from {addr[0]}:{addr[1]}")
                        client_thread = threading.Thread(target=handle_client, args=(conn, addr))
                        client_thread.daemon = True
                        client_thread.start()
                        self.threads.append(client_thread)
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if self.active:
                            print(f"  MySQL Server error: {e}")
                        break

            except OSError as e:
                if e.errno == 98:
                    print(f"  Port {port} is already in use!")
                    print(f"     Solution: sudo fuser -k {port}/tcp")
                else:
                    print(f"  MySQL Server error: {e}")
            except Exception as e:
                print(f"  MySQL Server error: {e}")
            finally:
                if self.sock:
                    try:
                        self.sock.close()
                    except Exception:
                        pass

        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.settimeout(1)
            result = test_sock.connect_ex((interface, port))
            test_sock.close()

            if result == 0:
                print(f"  Port {port} is already in use!")
                print(f"     Solution: sudo fuser -k {port}/tcp")
                return None
        except Exception:
            pass

        self.active = True
        thread = threading.Thread(target=server_loop, daemon=True)
        thread.start()
        time.sleep(1)
        return thread

    # ---------------- handshake / auth ----------------

    def send_handshake(self, conn, client_ip, country, city, connection_id, session):
        try:
            session["sequence_id"] = 0

            protocol_version = 10
            server_version = self.server_version

            auth_plugin_data_part1 = os.urandom(8)
            auth_plugin_data_part2 = os.urandom(12)

            session["scramble"] = auth_plugin_data_part1 + auth_plugin_data_part2[:12]

            capability_flags = 0xffffffff
            character_set = 255
            status_flags = 0x0002
            auth_plugin_data_len = 21

            packet = bytearray()
            packet.append(protocol_version)
            packet.extend(server_version.encode('utf-8'))
            packet.append(0)
            packet.extend(struct.pack('<I', connection_id))
            packet.extend(auth_plugin_data_part1)
            packet.append(0)
            packet.extend(struct.pack('<H', capability_flags & 0xFFFF))
            packet.append(character_set)
            packet.extend(struct.pack('<H', status_flags))
            packet.extend(struct.pack('<H', (capability_flags >> 16) & 0xFFFF))
            packet.append(auth_plugin_data_len)
            packet.extend(b'\x00' * 10)
            packet.extend(auth_plugin_data_part2)
            packet.append(0)
            auth_plugin_name = b"mysql_native_password"
            packet.extend(auth_plugin_name)
            packet.append(0)

            self.send_packet(conn, packet, session)
            self.log_activity(client_ip, "unknown", "HANDSHAKE", "Handshake sent", country, city)

        except Exception as e:
            print(f"  MySQL handshake error: {e}")
            raise

    def compute_mysql_native_password(self, password, scramble):
        if not password:
            return b""
        stage1 = hashlib.sha1(password.encode('utf-8')).digest()
        stage2 = hashlib.sha1(stage1).digest()
        stage3 = hashlib.sha1(scramble + stage2).digest()
        return bytes(a ^ b for a, b in zip(stage1, stage3))

    def handle_login(self, conn, data, client_ip, client_port, country, city, session):
        try:
            if len(data) < 5:
                return False

            client_seq = data[3]
            session["sequence_id"] = (client_seq + 1) & 0xFF

            pos = 4
            pos += 4
            pos += 4
            pos += 1
            pos += 23

            username = ""
            while pos < len(data) and data[pos] != 0:
                username += chr(data[pos])
                pos += 1
            pos += 1

            auth_response = b""
            if pos < len(data):
                auth_response_len = data[pos]
                pos += 1
                if auth_response_len > 0 and pos + auth_response_len <= len(data):
                    auth_response = data[pos:pos + auth_response_len]

            password_hash = auth_response.hex() if auth_response else "(empty)"

            expected_password = self.VALID_CREDENTIALS.get(username)
            success = False
            if expected_password is not None:
                expected_response = self.compute_mysql_native_password(
                    expected_password, session.get("scramble", b"")
                )
                success = auth_response == expected_response

            self.log_credentials(client_ip, username, password_hash, country, city, success)

            if success:
                session["authenticated"] = True
                session["current_user"] = username
                self.send_ok_packet(conn, session)
                self.log_activity(client_ip, username, "LOGIN_SUCCESS", "Login successful", country, city)
                return True
            else:
                self.send_error_packet(conn, 1045, f"Access denied for user '{username}'", session)
                self.log_activity(client_ip, username, "LOGIN_FAILED", "Login failed", country, city)
                return False

        except Exception as e:
            print(f"  MySQL login handler error: {e}")
            self.send_error_packet(conn, 1045, "Access denied", session)
            return False

    # ---------------- query handling ----------------

    def handle_query(self, conn, data, client_ip, country, city, session):
        try:
            client_seq = data[3] if len(data) > 3 else 0
            session["sequence_id"] = (client_seq + 1) & 0xFF

            pos = 4
            if pos >= len(data):
                return

            cmd = data[pos]
            pos += 1

            if cmd == 0x03:  # COM_QUERY
                query = data[pos:].decode('utf-8', errors='ignore').strip()
                query_lower = query.lower()

                print(f"  MySQL: Query: {query}")
                self.log_activity(client_ip, session.get("current_user") or "unknown", "QUERY", query, country, city)

                if query_lower.startswith("select"):
                    self.handle_select_query(conn, query, session)
                elif query_lower.startswith("show"):
                    self.handle_show_query(conn, query, session)
                elif query_lower.startswith("describe") or query_lower.startswith("desc"):
                    self.handle_describe_query(conn, query, session)
                elif query_lower.startswith("use"):
                    self.handle_use_query(conn, query, session)
                elif query_lower.startswith("exit") or query_lower.startswith("quit"):
                    conn.close()
                else:
                    self.send_ok_packet(conn, session)

            elif cmd == 0x01:  # COM_QUIT
                conn.close()

            elif cmd == 0x02:  # COM_INIT_DB
                db_name = data[pos:].decode('utf-8', errors='ignore').strip('\x00').strip()
                if db_name in self.DATABASES:
                    session["current_db"] = db_name
                    self.log_activity(client_ip, session.get("current_user") or "unknown", "USE_DB", db_name, country, city)
                    self.send_ok_packet(conn, session)
                else:
                    self.send_error_packet(conn, 1049, f"Unknown database '{db_name}'", session)

            elif cmd == 0x04:  # COM_FIELD_LIST
                eof_packet = bytearray([0xFE]) + struct.pack('<H', 0) + struct.pack('<H', 0)
                self.send_packet(conn, eof_packet, session)

            elif cmd == 0x0e:  # COM_PING
                self.send_ok_packet(conn, session)

            else:
                self.send_ok_packet(conn, session)

        except Exception as e:
            print(f"  MySQL query error: {e}")
            self.send_error_packet(conn, 1064, "You have an error in your SQL syntax", session)

    def handle_use_query(self, conn, query, session):
        db_name = query.strip().split()[-1].strip('`;').strip()
        if db_name in self.DATABASES:
            session["current_db"] = db_name
            self.send_ok_packet(conn, session)
        else:
            self.send_error_packet(conn, 1049, f"Unknown database '{db_name}'", session)

    def handle_select_query(self, conn, query, session):
        query_lower = query.lower()

        if "from wp_users" in query_lower:
            self.send_resultset(conn, "wp_users", session)
        elif "from user" in query_lower and "mysql" in query_lower:
            self.send_resultset(conn, "user", session)
        else:
            self.send_empty_resultset(conn, session)

    def handle_show_query(self, conn, query, session):
        query_lower = query.lower()

        if "show databases" in query_lower:
            self.send_database_list(conn, session)
        elif "show tables" in query_lower:
            db = session.get("current_db") or "wordpress"
            if "from" in query_lower:
                db = query_lower.split("from")[-1].strip().strip('`;')
            self.send_table_list(conn, db, session)
        else:
            self.send_ok_packet(conn, session)

    def handle_describe_query(self, conn, query, session):
        query_lower = query.lower()
        table = query_lower.replace("describe", "").replace("desc", "").strip().strip(';').strip()

        if table in self.TABLE_STRUCTURES:
            self.send_table_structure(conn, table, session)
        else:
            self.send_empty_resultset(conn, session)

    # ---------------- resultset senders ----------------

    def send_database_list(self, conn, session):
        rows = [[db] for db in self.DATABASES]
        self.send_resultset_with_columns(conn, ["Database"], rows, session)

    def send_table_list(self, conn, database, session):
        if database in self.TABLES:
            rows = [[table] for table in self.TABLES[database]]
            self.send_resultset_with_columns(conn, [f"Tables_in_{database}"], rows, session)
        else:
            self.send_empty_resultset(conn, session)

    def send_table_structure(self, conn, table, session):
        if table in self.TABLE_STRUCTURES:
            structure = self.TABLE_STRUCTURES[table]
            rows = [list(field) for field in structure]
            self.send_resultset_with_columns(conn, ["Field", "Type", "Null", "Key"], rows, session)
        else:
            self.send_empty_resultset(conn, session)

    def send_resultset(self, conn, table, session):
        if table in self.DATA:
            data = self.DATA[table]
            if table == "wp_users":
                columns = ["ID", "user_login", "user_pass", "user_email", "user_registered", "user_status", "display_name"]
            elif table == "user":
                columns = ["Host", "User", "Password", "Select_priv", "Insert_priv"]
            else:
                columns = [f"col{i+1}" for i in range(len(data[0]))]
            self.send_resultset_with_columns(conn, columns, data, session)
        else:
            self.send_empty_resultset(conn, session)

    def send_resultset_with_columns(self, conn, columns, rows, session):
        """Send a full resultset: column count, column defs, EOF, rows, EOF.

        Column definition packet layout (protocol 41), exact field order:
          lenenc-str catalog ("def")
          lenenc-str schema
          lenenc-str table
          lenenc-str org_table
          lenenc-str name        <- no extra null terminator, the lenenc
                                     length prefix IS the terminator
          lenenc-str org_name
          lenenc-int  0x0c (length of the fixed-size fields below)
          2 bytes  character set
          4 bytes  column length
          1 byte   column type
          2 bytes  flags
          1 byte   decimals
          2 bytes  filler (0x00 0x00)

        The previous version appended a stray extra 0x00 after the column
        name on top of its length prefix, and dropped the 2-byte trailing
        filler entirely. Every byte after that point lands one position off,
        which is exactly why the client would print blank/misaligned headers
        and occasionally throw "malformed packet" depending on how the
        desync happened to land on a given connection.
        """
        try:
            # 1. Column count
            packet = bytearray()
            packet.extend(self.len_encode_int(len(columns)))
            self.send_packet(conn, packet, session)

            # 2. Column definitions
            for col in columns:
                col_def = bytearray()

                col_def.extend(self.len_encode_int(3))
                col_def.extend(b'def')            # catalog

                col_def.extend(self.len_encode_int(0))  # schema (empty)
                col_def.extend(self.len_encode_int(0))  # table (empty)
                col_def.extend(self.len_encode_int(0))  # org_table (empty)

                name_bytes = col.encode('utf-8')
                col_def.extend(self.len_encode_int(len(name_bytes)))
                col_def.extend(name_bytes)         # name - lenenc prefix only, no extra null

                col_def.extend(self.len_encode_int(len(name_bytes)))
                col_def.extend(name_bytes)         # org_name

                col_def.append(0x0c)               # length of fixed fields below
                col_def.extend(struct.pack('<H', 33))    # character set (utf8_general_ci)
                col_def.extend(struct.pack('<I', 255))   # column length

                col_type = 0x03 if ('id' in col.lower() or 'int' in col.lower()) else 0x0f
                col_def.append(col_type)           # type
                col_def.extend(struct.pack('<H', 0))     # flags
                col_def.append(0)                   # decimals
                col_def.extend(b'\x00\x00')         # filler - required, was missing before

                self.send_packet(conn, col_def, session)

            # 3. EOF after column definitions
            eof_packet = bytearray([0xFE]) + struct.pack('<H', 0) + struct.pack('<H', 0)
            self.send_packet(conn, eof_packet, session)

            # 4. Rows
            for row in rows:
                row_packet = bytearray()
                for value in row:
                    val_bytes = str(value).encode('utf-8')
                    row_packet.extend(self.len_encode_int(len(val_bytes)))
                    row_packet.extend(val_bytes)
                self.send_packet(conn, row_packet, session)

            # 5. Final EOF
            self.send_packet(conn, eof_packet, session)

        except Exception as e:
            print(f"  MySQL resultset error: {e}")
            self.send_error_packet(conn, 1064, f"Error: {e}", session)

    def send_empty_resultset(self, conn, session):
        """Protocol-correct empty resultset - reuses the real column-def path
        with zero rows instead of a bare 0x00 byte, which collides with the
        OK-packet header and desyncs the client's parser for the next command."""
        self.send_resultset_with_columns(conn, ["Info"], [], session)

    # ---------------- encoding helpers ----------------

    def len_encode_int(self, value):
        if value < 251:
            return bytes([value])
        elif value < 65536:
            return b'\xfc' + struct.pack('<H', value)
        elif value < 16777216:
            return b'\xfd' + struct.pack('<I', value)[:3]
        else:
            return b'\xfe' + struct.pack('<Q', value)

    # ---------------- ok / error packets ----------------

    def send_ok_packet(self, conn, session):
        try:
            packet = bytearray()
            packet.append(0x00)
            packet.append(0x00)
            packet.append(0x00)
            packet.extend(struct.pack('<H', 0))
            packet.extend(struct.pack('<H', 0))
            self.send_packet(conn, packet, session)

        except Exception as e:
            print(f"  MySQL OK packet error: {e}")

    def send_error_packet(self, conn, errno, message, session):
        try:
            packet = bytearray()
            packet.append(0xFF)
            packet.extend(struct.pack('<H', errno))
            packet.extend(b'#HY000')
            packet.extend(message.encode('utf-8'))
            self.send_packet(conn, packet, session)

        except Exception as e:
            print(f"  MySQL error packet error: {e}")

    def send_packet(self, conn, data, session):
        try:
            packet_len = len(data)
            header = struct.pack('<I', packet_len)[:3] + bytes([session["sequence_id"] & 0xFF])
            session["sequence_id"] = (session["sequence_id"] + 1) & 0xFF
            conn.sendall(header + data)

        except Exception as e:
            print(f"  MySQL send packet error: {e}")

    # ---------------- shutdown ----------------

    def stop(self):
        self.active = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass

        for thread in self.threads:
            try:
                thread.join(timeout=1)
            except Exception:
                pass
