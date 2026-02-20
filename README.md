# 🏦 PFE: Système d'Audit et Monitoring AI pour Amen Bank

## 📋 Description
Système dockerisé de monitoring et d'audit intelligent utilisant Zabbix, Grafana et Intelligence Artificielle (RAG + LLM).

## 🎯 Objectifs
- Monitoring automatisé des serveurs Windows et Linux
- Visualisation des données avec Grafana
- Chatbot IA pour requêtes en langage naturel
- Système d'authentification sécurisé
- Génération automatique de rapports

## 🛠️ Stack Technologique
- **Monitoring:** Zabbix Server + Agent
- **Visualisation:** Grafana
- **Base de données:** PostgreSQL
- **Vector DB:** Milvus
- **IA:** Mistral 7B / LLaMA
- **Backend:** FastAPI
- **Authentification:** JWT + PostgreSQL
- **Containerisation:** Docker + Docker Compose

## 🚀 Installation Rapide

### Prérequis
- Docker Desktop installé
- 8GB RAM minimum
- 25GB espace disque
- Python 3.10+

### Configuration

1. **Cloner le repository:**
```bash
git clone <votre-repo-url>
cd PFE_AI_Audit_AmenBank
```

2. **Créer le fichier .env:**
```bash
cp .env.example .env
```

3. **Éditer .env avec vos configurations:**
```bash
# Changez les mots de passe!
POSTGRES_PASSWORD=votre_mot_de_passe_securise
GRAFANA_ADMIN_PASSWORD=votre_mot_de_passe_admin
```

4. **Démarrer les services:**
```bash
docker-compose up -d
```

5. **Vérifier que tout fonctionne:**
```bash
docker-compose ps
```

## 🌐 Accès aux Services

| Service | URL | Identifiants par défaut |
|---------|-----|------------------------|
| Zabbix Web | http://localhost:8080 | Admin / zabbix |
| Grafana | http://localhost:3000 | admin / (voir .env) |
| AI Chatbot | http://localhost:5000 | (Semaine 6) |
| Auth API | http://localhost:8000 | (Semaine 8) |

## 📅 Planning

### Mois 1: Infrastructure Docker & Monitoring
- **Semaine 1:** Configuration environnement Docker
- **Semaine 2:** Déploiement Zabbix Server
- **Semaine 3:** Intégration Grafana
- **Semaine 4:** Tests avec serveurs de la banque

### Mois 2: Couche Intelligence Artificielle
- **Semaine 5:** Base de données vectorielle (Milvus)
- **Semaine 6:** LLM local (Mistral 7B)
- **Semaine 7:** Interface Chatbot
- **Semaine 8:** Authentification & Sécurité

### Mois 3: Finalisation & Déploiement
- **Semaine 9:** Module de rapports
- **Semaine 10:** Tests & Optimisation
- **Semaine 11:** Revue sécurité & Documentation
- **Semaine 12:** Présentation finale & Déploiement

## 📂 Structure du Projet
```
PFE_AI_Audit_AmenBank/
├── docker-compose.yml          # Configuration des conteneurs
├── .env.example                # Template configuration
├── .gitignore                  # Fichiers à ignorer
├── README.md                   # Ce fichier
├── zabbix/                     # Configuration Zabbix
├── grafana/                    # Dashboards Grafana
├── postgres/                   # Scripts DB
├── ai-chatbot/                 # Application IA
├── auth-service/               # Service d'authentification
└── docs/                       # Documentation
```

## 🔧 Commandes Utiles

### Démarrer tous les services:
```bash
docker-compose up -d
```

### Arrêter tous les services:
```bash
docker-compose down
```

### Voir les logs:
```bash
docker-compose logs -f [service-name]
```

### Redémarrer un service:
```bash
docker-compose restart [service-name]
```

### Nettoyer Docker (libérer espace):
```bash
docker system prune -a
```

## 👥 Équipe
- Étudiant 1: Louay
- Étudiant 2: [hakim]
- Encadrant Banque: Karim Rayachi

## 📧 Contact
Email: karim.rayachi@amenbank.com.tn

## 📝 Notes Importantes
- Ne jamais commit le fichier .env (contient des mots de passe)
- Les modèles IA (4GB+) doivent être téléchargés séparément
- Nettoyer Docker régulièrement pour économiser l'espace disque

## 🎓 PFE - ESPRIT 2024-2025



# 🏦 PFE: Système d'Audit et Monitoring AI pour Amen Bank

## 📋 Description
Système dockerisé de monitoring et d'audit intelligent combinant **Zabbix** pour la collecte de métriques et une couche d'**Intelligence Artificielle (FastAPI)** pour l'analyse d'anomalies en temps réel.

## 🎯 Objectifs Réalisés (Phase Infrastructure)
- [x] **Pipeline de Données Opérationnel :** Liaison temps réel entre Zabbix et le moteur AI.
- [x] **Moteur d'Analyse (Backend) :** API REST avec FastAPI pour le traitement des alertes.
- [x] **Webhooks Avancés :** Scripting JavaScript personnalisé pour l'envoi de JSON structuré.
- [x] **Visualisation Dynamique :** Injection des prédictions AI directement dans le dashboard Zabbix via des "Tags".

## 🛠️ Stack Technologique
- **Monitoring:** Zabbix Server 6.0 + Zabbix Agent (Active/Passive)
- **Backend AI:** FastAPI (Python 3.10)
- **Containerisation:** Docker & Docker Compose
- **Visualisation:** Zabbix Dashboard + Grafana
- **Base de données:** PostgreSQL (Zabbix DB)

## 🚀 Architecture du Pipeline AI
Le flux de données actuel suit ce parcours :
1. **Zabbix Agent** (LOUAY-PC) ➔ Envoi des métriques CPU/Système.
2. **Zabbix Server** ➔ Détection de dépassement de seuil.
3. **Webhook JS** ➔ Transformation des données en JSON et envoi POST.
4. **FastAPI Engine** ➔ Analyse de l'alerte et calcul du score d'anomalie.
5. **Tags Zabbix** ➔ Retour de la prédiction (`AI_Prediction`) sur le Dashboard.

## 📂 Structure du Projet Actuelle

PFE_AI_Audit_AmenBank/
├── docker-compose.yml # Orchestration des services
├── .env # Variables d'environnement (Passwords/IPs)
├── README.md # Documentation projet
├── ai-engine/ # Moteur d'IA (FastAPI)
│ ├── main.py # Point d'entrée API
│ ├── analyzer.py # Logique ML (Hakim - En cours)
│ └── recommender.py # Système expert (Hakim - En cours)
└── requirements.txt # Dépendances Python (FastAPI, Uvicorn, Scikit-learn)
## 🌐 Accès Rapide

| Service | URL | Usage |
|---------|-----|-------|
| **Zabbix UI** | http://localhost:8080 | Monitoring & Configuration Alertes |
| **API Docs** | http://localhost:5000/docs | Documentation Swagger de l'IA |
| **AI Health** | http://localhost:5000/health | Vérification d'état du moteur AI |

## 📅 État d'avancement
- **Semaine 3-4 :** Infrastructure Docker & Pipeline Zabbix-AI [TERMINÉ ✅]
- **Semaine 5-6 :** Développement de la couche Machine Learning (Analyzer) [EN COURS ⏳]
