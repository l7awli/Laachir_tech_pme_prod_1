# Create README.md
cat > README.md << 'EOF'
# ❄️ LAACHIR-TECH PME

Application de gestion d'interventions techniques pour les PME (Climatisation, Plomberie, Électricité)

## 🚀 Fonctionnalités

### Pour le Gérant
- 📊 Tableau de bord avec KPI en temps réel
- 📋 Gestion des interventions (Kanban)
- 🏢 CRM clients avec historique
- 💰 Validation des acomptes (70%)
- 👥 Gestion des utilisateurs (techniciens/gérants)
- 🗺️ Suivi GPS des techniciens
- 📄 Génération de devis PDF

### Pour le Technicien
- 📱 Interface mobile PWA
- 📸 Prise de photos avant/après intervention
- 🔩 Gestion des pièces consommées
- ✍️ Signature client digitale
- 📍 Localisation GPS temps réel
- 📝 Rapports d'intervention

## 🛠️ Technologies

- Backend: Python 3.11, Flask
- Base de données: SQLite (dev) / PostgreSQL (prod)
- Frontend: HTML5, CSS3, JavaScript
- Authentification: Flask-Login
- Conteneurisation: Docker

## 📦 Installation

### Prérequis
- Python 3.11 ou supérieur
- pip (gestionnaire de paquets Python)

### Installation locale

```bash
# Cloner le dépôt
git clone https://github.com/votre-username/laachir-tech-pme.git
cd laachir-tech-pme

# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement virtuel
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
python app.py

