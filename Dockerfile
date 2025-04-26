FROM kalilinux/kali-rolling:latest

# Install 30 most critical tools (fits free tier)
RUN apt-get update && apt-get install -y \
    # Network scanning
    nmap masscan dnsutils netcat \
    # Web security
    sqlmap nikto wpscan \
    # Password attacks
    hydra john \
    # Forensics
    binwalk foremost \
    # System
    htop curl wget \
    # Cleanup to save space
    && apt-get remove -y kali-linux-large \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && find /usr/share/doc -depth -type f ! -name copyright -delete

# Special permissions
RUN setcap cap_net_raw+ep /usr/bin/ping && \
    chmod 4755 /usr/bin/nmap

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:$PORT", "app:app"]
