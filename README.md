# Azure File Vault

A production-style Flask application that lets users upload files via a web UI or REST API. Files are stored in **Azure Blob Storage** and metadata (filename, size, upload time) is persisted in **Azure SQL Database**. The app runs in Docker and is ready to deploy to an Azure Linux VM.

---

## Project Structure

```
app/
├── app.py           # Flask routes & startup
├── config.py        # Environment variable loading
├── storage.py       # Azure Blob Storage helpers
├── database.py      # Azure SQL helpers (pyodbc)
├── requirements.txt
├── Dockerfile
└── .env.example
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.12+ |
| ODBC Driver 18 for SQL Server | latest |
| Docker | 24+ |
| Azure Storage Account | — |
| Azure SQL Database | — |

---

## Azure Setup (one-time)

### 1. Azure Blob Storage
```bash
# Create a storage account
az storage account create \
  --name <storageaccount> \
  --resource-group <rg> \
  --location eastus \
  --sku Standard_LRS

# Get the connection string
az storage account show-connection-string \
  --name <storageaccount> \
  --resource-group <rg>
```

### 2. Azure SQL Database
```bash
az sql server create \
  --name <sqlserver> \
  --resource-group <rg> \
  --location eastus \
  --admin-user <adminuser> \
  --admin-password <adminpassword>

az sql db create \
  --resource-group <rg> \
  --server <sqlserver> \
  --name filedb \
  --service-objective S0

# Allow your IP (or VM IP) through the SQL firewall
az sql server firewall-rule create \
  --resource-group <rg> \
  --server <sqlserver> \
  --name AllowMyIP \
  --start-ip-address <your-ip> \
  --end-ip-address <your-ip>
```

---

## Running Locally (Python)

### 1. Install ODBC Driver 18 (Ubuntu/Debian)
```bash
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list \
  | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev
```

### 2. Set up environment
```bash
cd app
cp .env.example .env
# Edit .env and fill in your Azure credentials
```

### 3. Install dependencies & run
```bash
pip install -r requirements.txt

# Load .env automatically
export $(grep -v '^#' .env | xargs)
python app.py
```

App is available at **http://localhost:5000**

---

## Running with Docker

### 1. Build the image
```bash
cd app
docker build -t azure-file-vault .
```

### 2. Run with environment variables
```bash
docker run -d \
  --name file-vault \
  -p 5000:5000 \
  --env-file .env \
  azure-file-vault
```

App is available at **http://localhost:5000**

### Useful Docker commands
```bash
# View logs (stdout — same as Azure Monitor)
docker logs -f file-vault

# Stop & remove
docker stop file-vault && docker rm file-vault

# Rebuild after code changes
docker build -t azure-file-vault . && docker run -d --name file-vault -p 5000:5000 --env-file .env azure-file-vault
```

---

## Deploying to an Azure Linux VM

```bash
# 1. Push your image to Azure Container Registry
az acr create --resource-group <rg> --name <registryname> --sku Basic
az acr login --name <registryname>
docker tag azure-file-vault <registryname>.azurecr.io/azure-file-vault:latest
docker push <registryname>.azurecr.io/azure-file-vault:latest

# 2. SSH into your VM and pull
ssh azureuser@<vm-ip>
sudo docker pull <registryname>.azurecr.io/azure-file-vault:latest
sudo docker run -d --name file-vault -p 5000:5000 --env-file .env \
  <registryname>.azurecr.io/azure-file-vault:latest

# 3. Open port 5000 in the VM's Network Security Group
az vm open-port --port 5000 --resource-group <rg> --name <vm-name>
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Web UI |
| `GET` | `/health` | Health check → `{"status":"ok"}` |
| `POST` | `/api/upload` | Upload a file (multipart/form-data, field `file`) |
| `GET` | `/api/files` | List all uploaded files |
| `DELETE` | `/api/files/<id>` | Delete a file by ID |

### Example: Upload via curl
```bash
curl -X POST http://localhost:5000/api/upload \
  -F "file=@/path/to/document.pdf"
```

---

## Upgrading to Managed Identity (passwordless)

When running on Azure (VM, ACI, App Service), replace the connection-string approach in `storage.py` with:

```python
from azure.identity import DefaultAzureCredential

def get_blob_service_client():
    account_url = f"https://{os.environ['AZURE_STORAGE_ACCOUNT_NAME']}.blob.core.windows.net"
    return BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())
```

And assign the **Storage Blob Data Contributor** role to your VM's system-assigned managed identity in the Azure portal. No secrets needed.
