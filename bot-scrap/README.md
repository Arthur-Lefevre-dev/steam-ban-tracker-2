# Steam Profile Scraper Bot

Un système de scraping de profils Steam avec architecture multi-bots et système d'oracle pour la synchronisation.

## 🚀 Fonctionnalités

- **Scraping multi-profils** : Collecte automatiquement les données de profils Steam et de leurs amis
- **Système d'Oracle** : Synchronise plusieurs bots pour éviter les doublons
- **Architecture modulaire** : Code organisé en modules réutilisables
- **Base de données MySQL** : Stockage persistant des données scrapées
- **Interface en ligne de commande** : Facile à utiliser avec de multiples options
- **Gestion des erreurs** : Système robuste de gestion des erreurs et retry
- **Rate limiting** : Respecte les limites de l'API Steam

## 📊 Données collectées

Pour chaque profil Steam :

1. **SteamID64** : Identifiant unique Steam
2. **URL du profil** : URL complète du profil
3. **Informations de ban** : Statut, type et date du ban
4. **Avatar** : URL de l'image de profil
5. **Niveau Steam** : Niveau actuel du compte
6. **Liste d'amis** : Pour la navigation récursive

## 🏗️ Architecture

```
Steam Scraper Bot
├── config.py          # Configuration centralisée
├── database.py        # Gestion base de données MySQL
├── steam_api.py       # Interface API Steam
├── oracle.py          # Système de synchronisation
├── bot_scraper.py     # Logique principale des bots
├── main.py            # Point d'entrée application
└── requirements.txt   # Dépendances Python
```

## 🛠️ Installation

### Prérequis

- Python 3.7+
- MySQL 5.7+
- Clé API Steam

### Installation des dépendances

```bash
pip install -r requirements.txt
```

### Configuration

1. **Copiez le fichier de configuration exemple :**

```bash
cp config.example .env
```

2. **Éditez le fichier `.env` avec vos informations :**

```env
# Configuration base de données
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=steam_scraper

# Clé API Steam (OBLIGATOIRE)
STEAM_API_KEY=your_steam_api_key_here

# Configuration des bots (optionnel)
MAX_CONCURRENT_BOTS=5
BOT_DELAY_MIN=2
BOT_DELAY_MAX=5
```

### Obtenir une clé API Steam

1. Visitez [Steam Web API Key](https://steamcommunity.com/dev/apikey)
2. Connectez-vous avec votre compte Steam
3. Entrez un nom de domaine (peut être fictif)
4. Copiez la clé générée dans votre fichier `.env`

## 🚀 Utilisation

### Mode interactif avec plusieurs bots

```bash
python main.py --seed 76561198000000000 --bots 3 --interactive
```

### Mode simple avec un bot

```bash
python main.py --seed https://steamcommunity.com/profiles/76561198000000000 --bots 1
```

### Scraping d'un profil unique

```bash
python main.py --single 76561198000000000
```

### Avec URL personnalisée

```bash
python main.py --seed customurl --bots 2
```

### Options disponibles

- `--bots N` : Nombre de bots à créer (défaut: 1)
- `--seed PROFILE [PROFILE...]` : Profils de départ (SteamID64, URLs ou URLs personnalisées)
- `--single PROFILE` : Mode scraping d'un seul profil
- `--interactive` : Mode interactif avec mises à jour de statut

## 📋 Formats de profils supportés

Le système accepte plusieurs formats :

- **SteamID64** : `76561198000000000`
- **URL complète** : `https://steamcommunity.com/profiles/76561198000000000`
- **URL personnalisée** : `https://steamcommunity.com/id/customurl`
- **Nom personnalisé** : `customurl`

## 🎯 Système d'Oracle

L'Oracle synchronise automatiquement les bots pour :

- Éviter les doublons de scraping
- Distribuer les tâches équitablement
- Gérer les tâches échouées
- Nettoyer les tâches bloquées

### Fonctionnement

1. Les bots demandent des tâches à l'Oracle
2. L'Oracle assigne des profils uniques à chaque bot
3. Les bots soumettent leurs résultats à l'Oracle
4. L'Oracle valide et sauvegarde les données

## 🗄️ Structure de la base de données

### Tables principales

- `steam_profiles` : Données des profils scrapés
- `steam_friends` : Relations d'amitié
- `scraping_queue` : Queue des tâches de scraping
- `bot_activities` : Activités des bots pour synchronisation

## 📈 Monitoring et statistiques

En mode interactif, vous pouvez voir :

- Nombre de profils scrapés
- Taux de réussite
- Statut de chaque bot
- Taille de la queue de scraping
- Statistiques en temps réel

## ⚙️ Configuration avancée

### Variables d'environnement

```env
# Délais entre requêtes
BOT_DELAY_MIN=2
BOT_DELAY_MAX=5

# Limite de requêtes par minute
REQUESTS_PER_MINUTE=60

# Nombre maximum d'amis par profil
MAX_FRIENDS_PER_PROFILE=100

# Timeout pour les tâches orphelines
ORACLE_TIMEOUT=30

# Niveau de logging
LOG_LEVEL=INFO
```

## 🔧 Dépannage

### Problèmes courants

**Erreur de connexion à la base de données**

```bash
# Vérifiez que MySQL est démarré
sudo systemctl start mysql

# Vérifiez les paramètres de connexion dans .env
```

**Erreur de clé API Steam**

```bash
# Vérifiez que votre clé API est correcte
# Respectez les limites de taux de l'API Steam
```

**Bots qui ne trouvent pas de tâches**

```bash
# Ajoutez plus de profils de départ
python main.py --seed profile1 profile2 profile3 --bots 3
```

## 🚨 Considérations importantes

1. **Respectez les ToS de Steam** : N'abusez pas de l'API
2. **Rate limiting** : Le système respecte automatiquement les limites
3. **Données sensibles** : Ne partagez jamais votre clé API
4. **Performance** : Ajustez le nombre de bots selon votre infrastructure

## 🤝 Contribution

Le code suit les principes DRY et maintient une architecture modulaire pour faciliter la maintenance et les contributions.

## 📄 Licence

Ce projet est fourni à des fins éducatives. Respectez les conditions d'utilisation de Steam.

---

**Note** : Ce système est conçu pour des fins de recherche et d'éducation. Utilisez-le de manière responsable et respectez les conditions d'utilisation de Steam.
