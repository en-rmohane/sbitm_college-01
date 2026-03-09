import sys
import os

# Add the project root to the path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Vercel needs the application object to be named 'app' or 'application'
# In our app.py, it's already named 'app'
