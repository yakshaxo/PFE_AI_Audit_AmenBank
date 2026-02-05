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