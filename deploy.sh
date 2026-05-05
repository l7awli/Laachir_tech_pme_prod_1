#!/bin/bash
# deploy.sh - One-click deployment script

echo "========================================"
echo "  LAACHIR-TECH PME - DEPLOYMENT"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Running as root - this will install system-wide"
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p instance logs static/uploads

# Set permissions
chmod 755 instance logs static/uploads

# Initialize database
echo "🗄️  Initializing database..."
python3 -c "from app import app, init_db; app.app_context().push(); init_db()"

# Create systemd service (for Linux servers)
if [ ! -f /etc/systemd/system/laachir-tech.service ]; then
    echo "🔧 Creating systemd service..."
    sudo tee /etc/systemd/system/laachir-tech.service > /dev/null <<EOF
[Unit]
Description=Laachir-Tech PME Application
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PWD
Environment="PATH=$PWD/venv/bin"
ExecStart=$PWD/venv/bin/gunicorn -c gunicorn_config.py wsgi:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
fi

echo ""
echo "========================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "========================================"
echo ""
echo "To start the application:"
echo "  Option 1 (Development): python app.py"
echo "  Option 2 (Production): gunicorn -c gunicorn_config.py wsgi:app"
echo "  Option 3 (System service): sudo systemctl start laachir-tech"
echo "  Option 4 (Docker): docker-compose up -d"
echo ""
echo "📍 Access the app at: http://localhost:8000"
echo "👔 Login: manager / admin123"
echo "========================================"

