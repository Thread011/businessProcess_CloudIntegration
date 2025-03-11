# Système de Traitement de Prêts Immobiliers

Un système distribué de traitement de prêts immobiliers construit avec une architecture microservices, utilisant FastAPI, Celery, RabbitMQ et Redis.

## Table des matières

- [Aperçu du projet](#aperçu-du-projet)
- [Architecture du système](#architecture-du-système)
- [Prérequis](#prérequis)
- [Configuration de l'environnement](#configuration-de-lenvironnement)
- [Exécution du système (Docker Compose)](#exécution-du-système-docker-compose)
- [Flux de traitement des demandes de prêt](#flux-de-traitement-des-demandes-de-prêt)
- [Services et fonctionnalités](#services-et-fonctionnalités)
- [Exemple d'utilisation](#exemple-dutilisation)
- [Surveillance et monitoring](#surveillance-et-monitoring)
- [Dépannage](#dépannage)

## Aperçu du projet

Ce projet est un système de traitement de prêts immobiliers qui permet d'automatiser l'évaluation et la décision d'octroi de prêts. Le système est conçu avec une architecture microservices pour assurer la scalabilité, la résilience et la maintenance facilitée.

Principales fonctionnalités :
- Soumission de demandes de prêt
- Vérification automatique de solvabilité
- Évaluation des biens immobiliers
- Prise de décision automatisée
- Notifications en temps réel
- Tableau de bord pour le suivi des demandes

## Architecture du système

Le système est composé des microservices suivants :

1. **Service de Demande de Prêt** : Point d'entrée pour les nouvelles demandes
2. **Service de Vérification de Crédit** : Évalue la solvabilité du demandeur
3. **Service d'Évaluation Immobilière** : Évalue la valeur et les risques liés au bien
4. **Service de Décision** : Détermine l'approbation ou le rejet du prêt
5. **Service de Notification** : Envoie des notifications aux clients

Technologies utilisées :
- **FastAPI** : Framework API REST haute performance
- **Celery** : Système de files d'attente et de tâches distribuées
- **RabbitMQ** : Broker de messages pour la communication entre services
- **Redis** : Cache et backend pour les résultats Celery
- **Docker & Docker Compose** : Conteneurisation et orchestration locale
- **Prometheus & Grafana** : Surveillance et visualisation des métriques

## Prérequis

- Docker et Docker Compose
- Git
- Make (optionnel, pour l'utilisation du Makefile)

## Configuration de l'environnement

1. Cloner le dépôt :

```bash
git clone <url-du-dépôt>
cd projectCloudMetier
```

2. Créer un fichier `.env` à la racine du projet :

```bash
cp .env.example .env
```

3. Configurer les variables d'environnement selon vos besoins

## Exécution du système (Docker Compose)

1. Démarrer tous les services :

```bash
docker-compose up -d
```

2. Vérifier l'état des services :

```bash
docker-compose ps
```

3. Accéder aux points d'entrée des services :
   - Service de Demande de Prêt : http://localhost:18010
   - Service de Vérification de Crédit : http://localhost:18011
   - Service d'Évaluation Immobilière : http://localhost:18012
   - Service de Décision : http://localhost:18013
   - Service de Notification : http://localhost:18014
   - Tableau de bord Grafana : http://localhost:3001 (admin/admin)
   - Interface RabbitMQ : http://localhost:15673 (guest/guest)

4. Exécuter le client de test pour simuler des demandes de prêt :

```bash
python main.py
```

## Flux de traitement des demandes de prêt

Le processus de traitement d'une demande de prêt suit les étapes suivantes :

1. **Soumission de la demande** : Le client soumet une demande via le Service de Demande de Prêt
2. **Vérification de crédit** : Le Service de Vérification de Crédit évalue la solvabilité du demandeur
3. **Évaluation du bien** : Le Service d'Évaluation Immobilière estime la valeur du bien et les risques associés
4. **Prise de décision** : Le Service de Décision analyse toutes les informations et détermine si le prêt est approuvé
5. **Notification** : Le Service de Notification informe le client du résultat

Chaque étape du processus est exécutée de manière asynchrone grâce à Celery et RabbitMQ, permettant un traitement efficace et scalable des demandes.

## Services et fonctionnalités

### Service de Demande de Prêt
- Accepte les nouvelles demandes de prêt
- Valide les données d'entrée
- Initie le flux de traitement

### Service de Vérification de Crédit
- Calcule le score de crédit du demandeur
- Évalue le ratio dette/revenu (DTI)
- Détermine l'éligibilité financière

### Service d'Évaluation Immobilière
- Estime la valeur du bien immobilier
- Calcule le ratio prêt/valeur (LTV)
- Évalue les risques liés à la propriété

### Service de Décision
- Analyse toutes les données collectées
- Applique les règles métier pour la décision
- Calcule le taux d'intérêt proposé
- Détermine l'approbation, le rejet ou la nécessité d'une révision manuelle

### Service de Notification
- Envoie des notifications par email
- Fournit des mises à jour en temps réel via WebSocket
- Offre un tableau de bord pour suivre l'état des demandes

## Exemple d'utilisation

Le système permet de traiter différents profils financiers pour les demandes de prêt. Voici un exemple d'utilisation avec le script `main.py` qui simule trois profils financiers différents : pauvre, moyen et riche.

### Données d'entrée (Exemple pour un profil moyen)

```python
# Extrait de main.py - Création d'une demande de prêt pour un profil moyen
loan_request_data = {
    "client_name": "John Doe (Medium)",
    "email": "john.doe.medium@example.com",
    "phone": "+33123456789",
    "birth_date": "1995-03-11T00:00:00",  # 30 ans
    "nationality": "French",
    "current_address": {
        "street": "123 Rue de Paris",
        "city": "Paris",
        "postal_code": "75001",
        "country": "France"
    },
    "monthly_income": "6250",
    "monthly_expenses": "2000",
    "loan_amount": "250000",
    "loan_purpose": "PURCHASE",
    "loan_duration_years": 20,
    "employment_info": {
        "employer_name": "Tech Corp",
        "position": "Engineer",
        "contract_type": "CDI",
        "years_employed": 5,
        "annual_income": "75000"
    },
    "property_info": {
        "type": "APARTMENT",
        "address": {
            "street": "456 Avenue des Champs-Élysées",
            "city": "Paris",
            "postal_code": "75008",
            "country": "France"
        },
        "surface_area": 85,
        "rooms": 3,
        "construction_year": 2010,
        "description": "Modern apartment in prime location",
        "condition": "EXCELLENT",
        "estimated_value": "450000"
    }
}
```

### Résultat dans le terminal

Lorsque vous exécutez `python main.py`, le système traite les demandes de prêt et affiche les résultats dans le terminal. Voici un exemple de sortie pour un profil moyen :

```
================================================================================
                     Loan Processing for MEDIUM Profile                      
================================================================================

[1] Submitting Loan Request
------------------------------------------------------------
[+] Request submitted successfully
[>] Request ID: 8f7d3a2e-1b5c-4c6a-9d8f-0e7a6b5c4d3a

[*] Dashboard Access
------------------------------------------------------------
[>] View your application status in real-time:
    http://localhost:18014/dashboard?clientId=8f7d3a2e-1b5c-4c6a-9d8f-0e7a6b5c4d3a

[*] Processing request (5 seconds)...

[2] Credit Evaluation
------------------------------------------------------------
[>] Credit Score: 720
[>] DTI Ratio: 0.32
[>] Eligibility: Approved

[3] Property Evaluation
------------------------------------------------------------
[>] Estimated Value: €450,000.00
[>] Risk Level: LOW
[>] LTV Ratio: 55.56%

[4] Loan Decision
------------------------------------------------------------
[+] Decision request submitted successfully
[>] Initial Status: PENDING
[*] Waiting for decision processing (5 seconds)...
[>] Decision: APPROVED
[>] Interest Rate: 2.85%
[>] Notes:
    - Application meets all criteria
    - Good credit history and stable income

[5] Notification System
------------------------------------------------------------
[+] Notification sent successfully

[*] Waiting for notifications...

[!] New Notification:
  > Subject: Loan Application Update
  > Message: Your loan application is being processed
  > Details:
    - client_name: John Doe (Medium)
    - loan_amount: 250000
  > Time: 10:15:23

============================================================
           Process Complete for MEDIUM Profile            
============================================================
```

Le système traite également des profils financiers "pauvre" et "riche" avec des résultats différents en fonction des critères d'évaluation.

## Surveillance et monitoring

Le système inclut une pile de surveillance complète :

- **Prometheus** : Collecte des métriques de performance
- **Grafana** : Visualisation des métriques avec des tableaux de bord préconfigurés

Métriques surveillées :
- Temps de réponse des services
- Taux d'erreur
- Utilisation des ressources
- Nombre de demandes traitées
- Temps de traitement par étape

## Dépannage

### Problèmes courants et solutions

1. **Les services ne démarrent pas**
   - Vérifier les logs avec `docker-compose logs <service-name>`
   - S'assurer que RabbitMQ et Redis sont en cours d'exécution

2. **Erreurs de communication entre services**
   - Vérifier que les variables d'environnement sont correctement configurées
   - S'assurer que RabbitMQ est accessible

3. **Performances lentes**
   - Augmenter le nombre de workers Celery
   - Vérifier l'utilisation des ressources avec Grafana

### Commandes utiles

```bash
# Voir les logs d'un service
docker-compose logs -f loan-request-service

# Redémarrer un service
docker-compose restart credit-check-service
