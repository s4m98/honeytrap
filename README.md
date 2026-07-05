# HoneyTrap 🐝 - Advanced Multi-Service Honeypot System

A powerful, modular honeypot system for Linux that captures attacker credentials, tracks geolocation, and logs activities across multiple services including HTTP, FTP, SSH, Telnet, and MySQL.

## 📋 Table of Contents
- [Features](#-features)
- [Architecture](#-architecture)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Services](#-services)
- [Configuration](#-configuration)
- [Logging & Data Capture](#-logging--data-capture)
- [Security Considerations](#-security-considerations)
- [Project Structure](#-project-structure)
- [License](#-license)

## 🌟 Features

### Core Features
- ✅ **Multi-Service Support**: HTTP, FTP, SSH, Telnet, MySQL
- ✅ **Complete Credential Capture**: Captures full usernames and passwords
- ✅ **GeoLocation Tracking**: Tracks attacker locations using IP-API.com
- ✅ **Device Fingerprinting**: Extracts OS, browser, and device type
- ✅ **Modular Architecture**: Easy to add/modify services
- ✅ **Real-time Monitoring**: Live statistics and log viewing
- ✅ **Custom Web Pages**: Create realistic fake login pages
- ✅ **Fake File System**: Decoy files to attract attackers

### Security Features
- 🔒 **Complete Logging**: All activities logged to separate files
- 🌍 **Location Intelligence**: Country, city, ISP, coordinates
- 📁 **File Access Tracking**: Monitors file downloads/uploads
- 🕵️ **Session Tracking**: Tracks user sessions and activities
- 💾 **Database Storage**: SQLite database for all captured data
- 📊 **Statistics**: Connection counts, unique IPs, etc.


<figure><img src="/ss/1.png" alt=""><figcaption></figcaption></figure>
<figure><img src="/ss/2.png" alt=""><figcaption></figcaption></figure>
<figure><img src="/ss/3.png" alt=""><figcaption></figcaption></figure>
<figure><img src="/ss/4.png" alt=""><figcaption></figcaption></figure>


## 🏗️ Architecture

```
honeytrap/
├── honeytrap.py              # Main orchestrator
├── config.py                # Configuration settings
├── services/
│   ├── __init__.py
│   ├── ftp_service.py       # FTP honeypot with folder support
│   ├── http_service.py      # HTTP honeypot with web_root support
│   ├── ssh_service.py       # SSH honeypot
│   ├── telnet_service.py    # Telnet honeypot
│   ├── mysql_service.py     # MySQL honeypot
│   └── postgresql_service.py # PostgreSQL honeypot
├── core/
│   ├── __init__.py
│   ├── keylogger.py         # Keylogging functionality
│   ├── database.py          # Database manager
│   ├── geoip.py             # GeoLocation handler
│   └── utils.py             # Utility functions
├── web_root/                # HTTP web files directory
│   ├── index.html
│   ├── login.html
│   └── css/
│       └── style.css
├── ftp_root/                # FTP files directory
│   ├── readme.txt
│   ├── passwords.txt
│   └── config.ini
├── logs/                    # Service logs
├── captured_credentials.txt
└── honeypot.db
```

### System Requirements

- **Python 3.7+**
- **Linux OS** (Ubuntu/Debian recommended)
- **Root/sudo privileges** (for ports below 1024)

### Python Dependencies

```txt
pynput>=1.7.6        # For keylogging
pyftpdlib>=1.5.6     # For FTP service
requests>=2.28.0     # For GeoIP API calls
geoip2>=4.6.0        # Optional for MaxMind GeoIP
```

## 🚀 Installation

### 1. Clone or Download
```bash
git clone https://github.com/s4m98/honeytrap.git
cd honeytrap
mkdir -p web_root ftp_root logs
chmod +x honeytrap.py
```

## Install Dependencies

## Install required packages
```
pip3 install -r requirements.txt --break-system-packages
```

## Or manually:
```
pip3 install pynput pyftpdlib requests --break-system-packages
```

## 🎯 Quick Start

Run with sudo command
```
sudo python3 honeytrap.py
```


## Then type 'stop' to shutdown


## Default Users:

```txt
FTP:
     Valid Credentials:
       • admin / password123! [full]
       • user / password [read]
       • root / toor [full]
       • test / test123 [read]
       • anonymous / (empty) [read]
       • ftp / (empty) [read]

HTTP:
     Valid Credentials:
     • admin / password123!

MYSQL:
      Valid Credentials:
      • admin : admin@123
      • root : myr00t
```

## 📊 Logging & Data Capture
Log Files Structure

```text
logs/
├── http_logs.txt      # HTTP login attempts & requests
├── ftp_logs.txt       # FTP commands & login attempts
├── ssh_logs.txt       # SSH connection attempts
├── telnet_logs.txt    # Telnet login attempts
├── mysql_logs.txt     # MySQL connection attempts
└── honeypot.log       # Application events and errors
```

## 📝 License
This project is for educational and security research purposes only.

DISCLAIMER:

* Users are responsible for complying with all applicable laws and regulations.

* The authors are not responsible for any misuse or damage caused by this tool.

* Only deploy on systems you own or have explicit permission to test.

