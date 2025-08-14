# Déploiement CI/CD

## Configuration GitHub Container Registry

### 1. Activation des packages GitHub

1. Allez dans votre repository GitHub
2. Settings → General → Features → Packages ✅

### 2. Permissions du token

Le pipeline utilise `GITHUB_TOKEN` automatiquement avec les permissions :

- `contents: read`
- `packages: write`

## Utilisation

### Développement local

```bash
# Construire et lancer en local
docker compose up --build

# Utiliser l'image du registry
docker compose -f docker-compose.prod.yml up
```

### Production

```bash
# Déploiement automatique via script
./deploy.sh

# Ou manuellement
docker compose -f docker-compose.prod.yml up -d
```

## Tags automatiques

La pipeline génère automatiquement ces tags :

- `latest` : Pour la branche main
- `main-<sha>` : SHA commit sur main
- `develop-<sha>` : SHA commit sur develop
- `pr-<number>` : Pour les Pull Requests

## Images générées

🐳 **Registry** : `ghcr.io/jyok1m/odyssai-core`

**Tags disponibles** :

- `latest` - Dernière version stable
- `main-abc1234` - Version spécifique
- `develop-def5678` - Version développement

## Configuration serveur de production

### Prérequis

1. Docker et Docker Compose installés
2. Réseau Traefik créé : `docker network create traefik-public`
3. Variables d'environnement dans `.env`
4. Certificats SSL configurés

### Variables d'environnement requises

```bash
# API Keys
HF_API_KEY=...
OPENAI_API_KEY=...
PINECONE_API_KEY=...
# ... autres variables
```

### Déploiement automatisé (optionnel)

Pour activer le déploiement automatique, configurez ces secrets GitHub :

- `DEPLOY_HOST` : IP/hostname du serveur
- `DEPLOY_USER` : Utilisateur SSH
- `DEPLOY_KEY` : Clé privée SSH

## Monitoring

### Logs

```bash
# Logs en temps réel
docker compose -f docker-compose.prod.yml logs -f

# Logs spécifiques
docker logs odyssai-backend
docker logs traefik
```

### Health checks

```bash
# API
curl https://odyssai.yourdomain.com/api/health

# Traefik dashboard
curl https://odyssai.yourdomain.com:8080/api/overview
```
