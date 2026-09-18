# Deploying RiskLens to Azure

This is the deployment path the CI pipeline (`.github/workflows/ci.yml`) targets.
It's written as a concrete, followable guide rather than left vague, so you can
actually stand this up and speak to it in an interview.

## Target architecture

- **Azure Container Apps** — hosts the FastAPI backend as a container, scales to
  zero when idle (cheap for a portfolio project), supports revisions for
  zero-downtime deploys.
- **Azure Database for PostgreSQL — Flexible Server** — with the `pgvector`
  extension enabled (Azure supports this as an allow-listed extension).
- **Azure Cosmos DB for MongoDB API** — API-compatible with the `pymongo`
  client already used in `app/db/mongo.py`, no code changes needed.
- **Azure Static Web Apps** — hosts the built React frontend, with the API
  proxied to the Container App.
- **Azure Container Registry (ACR)** — stores the backend Docker image built
  by CI.

## One-time setup

```bash
# Resource group
az group create --name risklens-rg --location eastus

# Container registry
az acr create --name risklensacr --resource-group risklens-rg --sku Basic

# Postgres flexible server with pgvector
az postgres flexible-server create \
  --name risklens-pg --resource-group risklens-rg \
  --admin-user risklens --admin-password <secret> \
  --sku-name Standard_B1ms --tier Burstable
az postgres flexible-server parameter set \
  --resource-group risklens-rg --server-name risklens-pg \
  --name azure.extensions --value VECTOR

# Cosmos DB (Mongo API)
az cosmosdb create --name risklens-mongo --resource-group risklens-rg --kind MongoDB

# Container Apps environment
az containerapp env create --name risklens-env --resource-group risklens-rg --location eastus

# Container App (first deploy, subsequent ones come from CI)
az containerapp create \
  --name risklens-backend --resource-group risklens-rg \
  --environment risklens-env \
  --image risklensacr.azurecr.io/risklens-backend:latest \
  --target-port 8000 --ingress external \
  --secrets anthropic-key=<your-key> database-url=<pg-connection-string> mongo-url=<cosmos-connection-string> \
  --env-vars ANTHROPIC_API_KEY=secretref:anthropic-key DATABASE_URL=secretref:database-url MONGO_URL=secretref:mongo-url
```

## GitHub Actions secrets required

| Secret | Value |
|---|---|
| `ACR_LOGIN_SERVER` | `risklensacr.azurecr.io` |
| `ACR_USERNAME` / `ACR_PASSWORD` | from `az acr credential show` |
| `ACR_NAME` | `risklensacr` |
| `AZURE_RESOURCE_GROUP` | `risklens-rg` |

## Frontend

```bash
cd frontend
npm run build
az staticwebapp create --name risklens-frontend --resource-group risklens-rg \
  --source ./dist --location eastus2
```

Set the Static Web App's API proxy (`staticwebapp.config.json`) to route `/api/*`
to the Container App's FQDN.

## Honest note on scope

This guide describes the intended path; standing up the Postgres/Cosmos/Container
Apps trio costs real money to run continuously, so for a portfolio project the
practical move is: run it locally via `infra/docker-compose.yml` for demos, and
be ready to walk through this file and the CI YAML to show you know how it would
ship — most interviewers care more about whether you understand the deployment
shape than whether it's live 24/7 on your own Azure bill.
