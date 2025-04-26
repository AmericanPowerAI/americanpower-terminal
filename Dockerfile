# Lightweight Kali base
FROM kalilinux/kali-rolling:latest

# Install 50+ essential tools (fits free tier)
RUN apt-get update && apt-get install -y \
    # Network
    nmap netcat traceroute dnsutils whois masscan \
    # Security
    sqlmap nikto hydra john hashcat \
    # Web
    wpscan gobuster dirb \
    # Forensics
    binwalk foremost volatility \
    # System
    htop strace ltrace \
    # Utilities
    curl wget git zip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy your app
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt

# Start command
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "app:app"]
