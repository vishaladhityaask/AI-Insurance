"""
server.py — GigShield Phase 2
Used by Render for deployment.
Serves gigshield_p2.html as the main page.
"""
from app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
