# Azure Cloud Deployment: Grid Trading + Interactive Brokers

**Date**: 2026-06-07  
**Question**: Can grid trading with Interactive Brokers be deployed on Azure VMs?  
**Answer**: **YES ✅ FULLY SUPPORTED** with proper architecture  

---

## Executive Summary

### Can You Run Grid Trading + IB on Azure?

**YES ✅ 100% Possible**

You can deploy:
1. ✅ Grid backtesting engine (100% cloud)
2. ✅ Interactive Brokers live trading (with TWS/Gateway)
3. ✅ Full SaaS application (REST API, WebSocket)
4. ✅ Monitoring & alerting
5. ✅ CI/CD pipeline

**Cost Estimate**: $50–200/month (depending on scale)

### Can You Install TWS on Azure VM?

**YES ✅ BUT with caveats**

- ✅ TWS Gateway (headless) — **YES, perfect for cloud**
- ⚠️ TWS Desktop (GUI) — **Can run but unnecessary**
- ✅ IB API Server — **YES, easiest option**

**Recommendation**: Use **IB Gateway** (lightweight, designed for automation)

---

## Part 1: Azure VM Architecture

### Reference Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Azure Subscription                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Azure Container Registry (ACR)               │  │
│  │  - grid-backtest-core Docker image                   │  │
│  │  - grid-backtest-ib Docker image                     │  │
│  │  - grid-backtest-saas Docker image                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ▼                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │     Azure App Service / Kubernetes (AKS)             │  │
│  │  - grid-backtest-saas REST API (FastAPI)             │  │
│  │  - WebSocket for live trading monitoring             │  │
│  │  - Celery workers for backtests                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                   │
│     ┌─────────────────────┼──────────────────────┐           │
│     ▼                     ▼                      ▼            │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ VM Instance │  │ VM Instance  │  │  VM Instance      │   │
│  │  (Ubuntu)   │  │  (Ubuntu)    │  │  (Ubuntu)         │   │
│  │             │  │              │  │                   │   │
│  │ IB Gateway  │  │ Grid Engine  │  │ Monitoring Agent  │   │
│  │ Python 3.12 │  │ Python 3.12  │  │ (Datadog, New Rel)|   │
│  │ ib-insync   │  │ grid-backtest│  │                   │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
│       │ TWS Connection     │ DataFrame      │                │
│       │ (API port 7497)    │ Processing     │ Metrics         │
│       └──────┬─────────────┴────────────────┴────────────┐  │
│              ▼                                              │  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │     Azure Database (PostgreSQL)                       │  │
│  │  - Backtest results                                   │  │
│  │  - Live trades & positions                            │  │
│  │  - Account state snapshots                            │  │
│  │  - Metrics & analytics                                │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                   │
│  ┌────────────────────────┴─────────────────────────────┐  │
│  │     Azure Storage (Blob)                              │  │
│  │  - Backtest CSVs / Parquet files                      │  │
│  │  - Market data (cached)                               │  │
│  │  - Configuration backups                              │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                   │
│  ┌────────────────────────┴─────────────────────────────┐  │
│  │     Azure Key Vault                                   │  │
│  │  - IB Account credentials                             │  │
│  │  - API keys (Binance, Alpha Vantage, etc.)            │  │
│  │  - Database passwords                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘

External:
  Interactive Brokers API ← → IB Gateway (port 7497)
  Client Apps ← → Azure App Service (HTTPS, port 443)
```

---

## Part 2: Detailed VM Setup

### 2.1 Azure VM Configuration

#### Compute Requirements

```
Workload                    | vCPU | Memory | Disk    | Type
──────────────────────────────────────────────────────────────
Backtesting (CPU-bound)     | 4–8  | 16 GB  | 256 GB  | D4s_v3
Grid Engine + IB Gateway    | 2–4  | 8 GB   | 128 GB  | D2s_v3
SaaS API + WebSocket        | 2–4  | 8 GB   | 128 GB  | D2s_v3
Monitoring/Logging          | 1–2  | 4 GB   | 64 GB   | B2s
──────────────────────────────────────────────────────────────

Recommended Setup for Solo Trader:
  - 1 VM (Standard_D4s_v3): 4 vCPU, 16 GB RAM, 256 GB SSD
  - Runs: IB Gateway + Grid Engine + API server + monitoring
  - Cost: ~$150–180/month
```

#### Recommended Operating System

✅ **Ubuntu 22.04 LTS** (or 24.04 LTS)
- Native Python 3.12 support
- Easy package management (apt)
- Lightweight for cloud
- Long-term support (5 years)

#### Network Configuration

```
Security Group / Firewall Rules:

Inbound:
  Port 7497  → IB API (localhost only, encrypted)
  Port 8000  → FastAPI (HTTPS, public)
  Port 9090  → Prometheus (private/VPN only)
  Port 22    → SSH (your IP only)

Outbound:
  Port 443   → HTTPS (Interactive Brokers, cloud APIs)
  Port 80    → HTTP (if needed)
  Port 5432  → PostgreSQL (Azure DB)
```

---

### 2.2 Step-by-Step Installation

#### Step 1: Create Azure VM

```bash
# Using Azure CLI

az group create --name grid-trading-rg --location eastus

az vm create \
  --resource-group grid-trading-rg \
  --name grid-trading-vm-01 \
  --image UbuntuLTS \
  --size Standard_D4s_v3 \
  --admin-username azureuser \
  --generate-ssh-keys \
  --public-ip-sku Standard
```

#### Step 2: Connect to VM

```bash
# Get public IP
az vm show -d --resource-group grid-trading-rg \
  --name grid-trading-vm-01 --query publicIps -o tsv

# SSH in
ssh azureuser@<public-ip>
```

#### Step 3: Install Python & Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12
sudo apt install -y python3.12 python3.12-venv python3.12-dev

# Install system dependencies
sudo apt install -y \
  git curl wget \
  libssl-dev libffi-dev \
  build-essential \
  postgresql-client-15

# Verify Python
python3.12 --version  # Should be 3.12.x
```

#### Step 4: Install IB Gateway

**Option A: Download from IB Website**

```bash
# Download from Interactive Brokers
# https://www.interactivebrokers.com/en/index.php?f=16042

cd ~/ib-gateway
# Unzip the distribution

# Make it executable
chmod +x ~/ib-gateway/bin/gatewayapp
```

**Option B: Docker (Recommended)**

```bash
# Use community Docker image for IB Gateway
docker pull waytrade/ib-gateway:latest

# Run gateway
docker run -d \
  --name ib-gateway \
  -p 7497:7497 \
  -e TWS_USERID=<your-ib-username> \
  -e TWS_PASSWORD=<your-ib-password> \
  -e TRADING_MODE=paper \
  waytrade/ib-gateway:latest
```

#### Step 5: Install grid-backtest Applications

```bash
# Create app directory
mkdir -p ~/apps && cd ~/apps

# Clone or download grid-backtest-core
git clone https://github.com/yourusername/grid-backtest-core.git
git clone https://github.com/yourusername/grid-backtest-saas.git
git clone https://github.com/yourusername/grid-backtest-ib.git

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e grid-backtest-core/
pip install -e grid-backtest-saas/
pip install -e grid-backtest-ib/

# Verify installations
python -c "import grid_backtest; print(grid_backtest.__version__)"
python -c "import ib_insync; print(ib_insync.__version__)"
```

#### Step 6: Configure Environment Variables

```bash
# Create .env file
cat > ~/.env << 'EOF'
# Interactive Brokers
IB_GATEWAY_HOST=localhost
IB_GATEWAY_PORT=7497
IB_CLIENT_ID=1

# Database
DATABASE_URL=postgresql://user:pass@<azure-postgres>.postgres.database.azure.com:5432/grid_db
REDIS_URL=redis://<azure-redis>.redis.cache.windows.net:6379

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_SECRET_KEY=$(openssl rand -hex 32)

# Grid Engine
STRATEGY_TYPE=DynamicGrid
BACKTEST_DATA_DIR=/data/market-data
RESULTS_DIR=/data/results

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/grid-trading.log

# Monitoring
DATADOG_API_KEY=<your-datadog-key>
SENTRY_DSN=<your-sentry-dsn>
EOF

# Load environment
source ~/.env
```

---

## Part 3: Running Interactive Brokers on Azure

### 3.1 IB Gateway vs. TWS Desktop

| Feature | IB Gateway | TWS Desktop | Rating |
|---|---|---|---|
| **Headless** | ✅ YES | ❌ Needs X11 | ✅ Gateway wins |
| **CPU Usage** | ~5–10% | ~15–25% | ✅ Gateway wins |
| **Memory** | ~100 MB | ~400–600 MB | ✅ Gateway wins |
| **Reliability** | Excellent | Excellent | TIE |
| **Setup** | Simple | Complex (X11) | ✅ Gateway wins |
| **Cloud Friendly** | ✅ Perfect | ⚠️ Possible | ✅ Gateway wins |

**Verdict**: Use **IB Gateway** (not TWS Desktop) on Azure

### 3.2 Running IB Gateway on Azure

#### Option 1: Docker (Recommended)

```yaml
# docker-compose.yml

version: '3.8'
services:
  ib-gateway:
    image: waytrade/ib-gateway:latest
    container_name: ib-gateway
    ports:
      - "7497:7497"
    environment:
      TWS_USERID: ${IB_USERNAME}
      TWS_PASSWORD: ${IB_PASSWORD}
      TRADING_MODE: paper  # or live
      IB_INSYNC_LOGFILE: /var/log/ib-gateway.log
    volumes:
      - ./ib-logs:/var/log
    restart: unless-stopped
    networks:
      - grid-network

  grid-engine:
    build: ./grid-backtest-ib
    container_name: grid-engine
    depends_on:
      - ib-gateway
    environment:
      IB_GATEWAY_HOST: ib-gateway
      IB_GATEWAY_PORT: 7497
      DATABASE_URL: ${DATABASE_URL}
    ports:
      - "8000:8000"
    volumes:
      - ./data:/data
      - ./logs:/var/log
    restart: unless-stopped
    networks:
      - grid-network

networks:
  grid-network:
    driver: bridge
```

**Deploy**:
```bash
docker-compose up -d
docker-compose logs -f  # Monitor
```

#### Option 2: Systemd Service (Manual)

```bash
# Create service file
sudo cat > /etc/systemd/system/ib-gateway.service << 'EOF'
[Unit]
Description=Interactive Brokers IB Gateway
After=network.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=/home/azureuser/ib-gateway
ExecStart=/home/azureuser/ib-gateway/bin/gatewayapp
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable ib-gateway
sudo systemctl start ib-gateway

# Check status
sudo systemctl status ib-gateway
```

---

## Part 4: Connectivity & Security

### 4.1 IB Gateway → Grid Engine Communication

```python
# grid_backtest_ib/connector.py

from ib_insync import IB
import os

class IBConnector:
    def __init__(self):
        self.ib = IB()
        
        # Connect to IB Gateway on same machine
        host = os.getenv('IB_GATEWAY_HOST', 'localhost')
        port = int(os.getenv('IB_GATEWAY_PORT', 7497))
        client_id = int(os.getenv('IB_CLIENT_ID', 1))
        
        try:
            self.ib.connect(host, port, clientId=client_id)
            print(f"✅ Connected to IB Gateway at {host}:{port}")
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            raise
    
    def is_connected(self) -> bool:
        return self.ib.isConnected()
```

### 4.2 Secrets Management (Azure Key Vault)

**NEVER store IB credentials in code or env files!**

```python
# Use Azure Key Vault for credentials

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def get_ib_credentials():
    vault_url = "https://grid-trading-vault.vault.azure.net/"
    client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())
    
    ib_username = client.get_secret("IB-USERNAME").value
    ib_password = client.get_secret("IB-PASSWORD").value
    
    return ib_username, ib_password

# Use in IB Gateway
ib_username, ib_password = get_ib_credentials()
```

---

## Part 5: Monitoring & Logging

### 5.1 Azure Monitor + Application Insights

```python
# Enable monitoring in your grid engine

from opencensus.ext.azure.log_exporter import AzureLogHandler
import logging

# Set up Azure logging
logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(
    connection_string='InstrumentationKey=<your-key>'
))

# Log trades
logger.info(f"Trade placed: {symbol} {qty} @ {price}")
logger.warning(f"Position at risk: {symbol} drawdown={dd}%")
logger.error(f"Connection lost to IB Gateway, retrying...")
```

### 5.2 Prometheus + Grafana

```yaml
# prometheus.yml

global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'grid-engine'
    static_configs:
      - targets: ['localhost:9090']
  
  - job_name: 'ib-gateway'
    static_configs:
      - targets: ['localhost:7497']
```

**Dashboard Metrics**:
- Portfolio value
- Drawdown %
- Active positions
- Trades per hour
- API latency

---

## Part 6: Cost Analysis

### 6.1 Monthly Azure Costs

| Service | Size | Cost/Month |
|---|---|---|
| **Virtual Machine** | D4s_v3 (4vCPU, 16GB) | $150–180 |
| **Database** | PostgreSQL 14 (single server) | $30–50 |
| **Redis** | Basic (C1) | $15–20 |
| **Storage** | Blob (100 GB) | $2–5 |
| **Key Vault** | Standard | $0.30 |
| **Bandwidth** | Outbound | $5–10 |
| **Monitoring** | Application Insights | $5–10 |
| **Load Balancer** | *(optional)* | $15–20 |
| **Total** | | **$220–290** |

### 6.2 Cost Optimization

```
Cost Reduction Ideas:

1. Use Azure Spot VMs (-70% compute cost)
   - Trade execution can tolerate interruptions
   - Example: D4s_v3 → $50/month instead of $180

2. Use Database for MySQL (cheaper than PostgreSQL)
   - 10–20% savings
   - Fully compatible

3. Run during market hours only (US stocks 9:30–16:00)
   - Scale down VM outside trading hours
   - Saves 50% on compute

4. Combine resources:
   - Single D2s_v3 instead of multiple smaller VMs
   - Handle: API + Grid Engine + IB Gateway
   - Cost: $100/month + storage/DB

Realistic Total: $150–200/month (optimized)
```

---

## Part 7: Deployment Pipeline (CI/CD)

### 7.1 Azure Pipelines

```yaml
# azure-pipelines.yml

trigger:
  - main
  - develop

pool:
  vmImage: 'ubuntu-latest'

stages:
  - stage: Build
    jobs:
      - job: BuildAndTest
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.12'
          
          - script: |
              python -m pip install --upgrade pip
              pip install -r grid-backtest-core/requirements.txt
              pip install -r grid-backtest-ib/requirements.txt
            displayName: 'Install dependencies'
          
          - script: |
              pytest grid-backtest-core/tests
              pytest grid-backtest-ib/tests
            displayName: 'Run tests'
          
          - task: PublishCodeCoverageResults@1
            inputs:
              codeCoverageTool: 'Cobertura'
              summaryFileLocation: 'coverage.xml'
  
  - stage: Deploy
    dependsOn: Build
    condition: succeeded()
    jobs:
      - deployment: DeployToAzure
        displayName: Deploy to Azure VM
        environment: production
        strategy:
          runOnce:
            deploy:
              steps:
                - task: AzureWebApp@1
                  inputs:
                    azureSubscription: 'Azure Connection'
                    appType: 'webAppLinux'
                    appName: 'grid-trading-saas'
                    package: '$(Pipeline.Workspace)'
```

---

## Part 8: Security Best Practices

### 8.1 Checklist

```
Security Configuration:

☑️ Firewall Rules
   - Only open ports 7497 (IB), 8000 (API), 22 (SSH)
   - Restrict SSH to your IP only
   - Use VPN for management

☑️ Credentials Management
   - Store IB credentials in Azure Key Vault
   - Rotate quarterly
   - Never log credentials

☑️ HTTPS/TLS
   - Use self-signed cert or Let's Encrypt
   - Enable TLS 1.3 minimum

☑️ Network Isolation
   - Put database in private subnet
   - Use NAT for outbound only
   - No inbound to database

☑️ Encryption
   - Enable encryption at rest (database)
   - Enable encryption in transit
   - Enable disk encryption

☑️ Monitoring
   - Alert on failed login attempts
   - Alert on large transactions
   - Daily backup verification

☑️ Backup & Recovery
   - Nightly backups (Azure)
   - Test recovery monthly
   - 30-day retention

☑️ API Security
   - Use Bearer tokens (OAuth2)
   - Rate limiting (100 req/min)
   - Input validation

☑️ Logging
   - Log all trades
   - Log API calls
   - Centralized logging (Application Insights)
```

---

## Part 9: Step-by-Step Deployment Guide

### Quick Start (15 Minutes)

```bash
# 1. Create VM
az vm create --resource-group grid-rg --name grid-vm \
  --image UbuntuLTS --size Standard_D4s_v3 --admin-username azureuser

# 2. SSH in
ssh azureuser@<ip>

# 3. Install basics
sudo apt update && sudo apt install -y python3.12 python3.12-venv docker.io

# 4. Clone repo
git clone https://github.com/yourusername/grid-backtest.git
cd grid-backtest

# 5. Create .env
cat > .env << 'EOF'
IB_USERNAME=your_ib_user
IB_PASSWORD=your_ib_password
IB_ACCOUNT=your_account_id
DATABASE_URL=postgresql://...
EOF

# 6. Deploy with Docker Compose
docker-compose up -d

# 7. Check status
docker-compose ps
docker-compose logs -f
```

### Full Production Setup (1 Hour)

See Section 2.2 (Step-by-Step Installation) for complete details.

---

## Part 10: Troubleshooting

### IB Gateway Connection Issues

```bash
# Check if IB Gateway is running
netstat -an | grep 7497

# Check IB Gateway logs
docker logs ib-gateway

# Restart IB Gateway
docker restart ib-gateway

# Verify connectivity from grid engine
python3 -c "from ib_insync import IB; ib = IB(); ib.connect('localhost', 7497); print('✅ Connected')"
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
psql -h <host> -U <user> -d grid_db

# Check credentials in Key Vault
az keyvault secret show --vault-name grid-vault --name DATABASE-URL
```

### API Not Responding

```bash
# Check if FastAPI is running
curl http://localhost:8000/health

# Check API logs
docker logs grid-engine

# Restart API
docker restart grid-engine
```

---

## Conclusion

### Can You Run Grid Trading + IB on Azure?

**YES ✅ Fully supported and recommended**

### Implementation Summary

```
Timeline: 2–4 hours (including DNS setup)

1. Create Azure VM (~5 min)
2. Install Python + Docker (~10 min)
3. Configure IB Gateway (~15 min)
4. Deploy grid-backtest apps (~15 min)
5. Set up monitoring (~10 min)
6. Test live trading (~30 min)

Cost: $150–200/month (optimized)
```

### Why Azure is Good for Grid Trading

1. ✅ Easy VM creation (minutes)
2. ✅ Integrated monitoring (Application Insights)
3. ✅ Built-in secrets management (Key Vault)
4. ✅ PostgreSQL compatible
5. ✅ Good uptime SLA (99.9%)
6. ✅ Easy backups

### Next Steps

1. **This week**: Create Azure VM, install IB Gateway
2. **Next week**: Deploy grid engine, test paper trading
3. **Following week**: Configure monitoring, go live with small capital
4. **Month 2**: Add more strategies, scale infrastructure

Your grid-backtest engine + Interactive Brokers + Azure = **complete cloud-native automated trading platform** ✅
