#!/bin/bash

# Script de déploiement pour Odyssai
set -e

echo "🚀 Déploiement d'Odyssai en cours..."

# Variables
COMPOSE_FILE="docker-compose.prod.yml"
IMAGE_NAME="ghcr.io/jyok1m/odyssai-core:latest"

# Vérifications préalables
echo "🔍 Vérification des prérequis..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé"
    exit 1
fi

# Création du réseau Traefik si nécessaire
echo "🌐 Création du réseau Traefik..."
docker network create traefik-public 2>/dev/null || echo "Réseau traefik-public existe déjà"

# Pull de la dernière image
echo "📥 Téléchargement de la dernière image..."
docker pull $IMAGE_NAME

# Arrêt des anciens conteneurs
echo "🛑 Arrêt des anciens conteneurs..."
docker compose -f $COMPOSE_FILE down --remove-orphans

# Démarrage des nouveaux conteneurs
echo "▶️ Démarrage des nouveaux conteneurs..."
docker compose -f $COMPOSE_FILE up -d

# Nettoyage des anciennes images
echo "🧹 Nettoyage des anciennes images..."
docker image prune -f

# Vérification du déploiement
echo "✅ Vérification du déploiement..."
sleep 10

if docker compose -f $COMPOSE_FILE ps | grep -q "Up"; then
    echo "✅ Déploiement réussi !"
    echo "🌐 Application accessible sur: https://odyssai.yourdomain.com"
    echo "📊 Dashboard Traefik: https://odyssai.yourdomain.com:8080"
else
    echo "❌ Échec du déploiement"
    docker compose -f $COMPOSE_FILE logs
    exit 1
fi
