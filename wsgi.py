# wsgi.py - Production server entry point
from app import app

if __name__ == "__main__":
    app.run()

