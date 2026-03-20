"""
app.py
------
Flask REST API backend for GigShield – Phase 1.
Serves gigshield.html as the frontend and exposes
JSON API endpoints that the frontend calls via fetch().

API Endpoints:
  GET  /                      → serves gigshield.html
  POST /api/register          → save worker to MySQL, return worker JSON
  GET  /api/workers           → return all workers as JSON
  GET  /api/worker/<id>       → return single worker as JSON
  DELETE /api/worker/<id>     → delete a worker from MySQL
  GET  /api/weather/<city>    → return simulated weather JSON
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error

from insurance_model import calculate_premium, simulate_weather_risk, get_coverage_details

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__, static_folder=".")   # serve files from project root
CORS(app)                                  # allow frontend fetch() calls
app.secret_key = "gig_insurance_phase1_secret"


# ---------------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------------
def get_db_connection():
    """Return a fresh MySQL connection. Edit password if needed."""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="mysql1234",          # ← change if your MySQL root has a password
            database="gig_insurance",
        )
        return conn
    except Error as e:
        print(f"[DB ERROR] {e}")
        return None


# ---------------------------------------------------------------------------
# Serve the frontend
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve gigshield.html as the main frontend page."""
    return send_from_directory(".", "gigshield.html")


# ---------------------------------------------------------------------------
# API — Register a worker
# ---------------------------------------------------------------------------

@app.route("/api/register", methods=["POST"])
def api_register():
    """
    POST /api/register
    Body (JSON): { name, city, platform, daily_income }
    Returns: { success, worker } or { success, error }
    """
    data = request.get_json()

    # --- Validate input ---
    name         = (data.get("name") or "").strip()
    city         = (data.get("city") or "").strip()
    platform     = (data.get("platform") or "").strip()
    daily_income = data.get("daily_income")

    if not all([name, city, platform, daily_income]):
        return jsonify({"success": False, "error": "All fields are required."}), 400

    try:
        daily_income = int(daily_income)
        if daily_income <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Daily income must be a positive number."}), 400

    # --- Calculate premium using Python model ---
    premium  = calculate_premium(daily_income)
    coverage = get_coverage_details(premium)

    # --- Save to MySQL ---
    conn = get_db_connection()
    if conn is None:
        return jsonify({"success": False, "error": "Database connection failed."}), 500

    try:
        cursor = conn.cursor()
        sql = """
            INSERT INTO workers (name, city, platform, daily_income, premium)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (name, city, platform, daily_income, premium))
        conn.commit()
        worker_id = cursor.lastrowid
    except Error as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

    # --- Return worker data to frontend ---
    worker = {
        "id":           worker_id,
        "name":         name,
        "city":         city,
        "platform":     platform,
        "daily_income": daily_income,
        "premium":      premium,
        "plan":         coverage["description"].split("–")[0].strip(),
        "coverage":     coverage["weekly_coverage"],
    }
    return jsonify({"success": True, "worker": worker}), 201


# ---------------------------------------------------------------------------
# API — Get all workers (for admin page)
# ---------------------------------------------------------------------------

@app.route("/api/workers", methods=["GET"])
def api_get_workers():
    """
    GET /api/workers
    Returns: { success, workers: [...], total, total_premium, avg_premium }
    """
    conn = get_db_connection()
    if conn is None:
        return jsonify({"success": False, "error": "Database connection failed."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM workers ORDER BY id DESC")
        workers = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    # Enrich each worker with plan and coverage from Python model
    for w in workers:
        cov = get_coverage_details(w["premium"])
        w["plan"]     = cov["description"].split("–")[0].strip()
        w["coverage"] = cov["weekly_coverage"]
        # Convert datetime to string if present
        if "registered_at" in w and w["registered_at"]:
            w["registered_at"] = str(w["registered_at"])

    total         = len(workers)
    total_premium = sum(w["premium"] for w in workers)
    avg_premium   = round(total_premium / total) if total else 0

    return jsonify({
        "success":       True,
        "workers":       workers,
        "total":         total,
        "total_premium": total_premium,
        "avg_premium":   avg_premium,
    })


# ---------------------------------------------------------------------------
# API — Get single worker (for dashboard)
# ---------------------------------------------------------------------------

@app.route("/api/worker/<int:worker_id>", methods=["GET"])
def api_get_worker(worker_id):
    """
    GET /api/worker/<id>
    Returns: { success, worker } or { success, error }
    """
    conn = get_db_connection()
    if conn is None:
        return jsonify({"success": False, "error": "Database connection failed."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM workers WHERE id = %s", (worker_id,))
        worker = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not worker:
        return jsonify({"success": False, "error": "Worker not found."}), 404

    cov = get_coverage_details(worker["premium"])
    worker["plan"]     = cov["description"].split("–")[0].strip()
    worker["coverage"] = cov["weekly_coverage"]
    if "registered_at" in worker and worker["registered_at"]:
        worker["registered_at"] = str(worker["registered_at"])

    return jsonify({"success": True, "worker": worker})


# ---------------------------------------------------------------------------
# API — Delete a worker (admin action)
# ---------------------------------------------------------------------------

@app.route("/api/worker/<int:worker_id>", methods=["DELETE"])
def api_delete_worker(worker_id):
    """
    DELETE /api/worker/<id>
    Returns: { success } or { success, error }
    """
    conn = get_db_connection()
    if conn is None:
        return jsonify({"success": False, "error": "Database connection failed."}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM workers WHERE id = %s", (worker_id,))
        conn.commit()
        affected = cursor.rowcount
    finally:
        cursor.close()
        conn.close()

    if affected == 0:
        return jsonify({"success": False, "error": "Worker not found."}), 404

    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# API — Weather simulation (calls Python insurance_model.py)
# ---------------------------------------------------------------------------

@app.route("/api/weather/<city>", methods=["GET"])
def api_weather(city):
    """
    GET /api/weather/<city>
    Returns simulated weather risk from insurance_model.py
    """
    weather = simulate_weather_risk(city)
    return jsonify({"success": True, "weather": weather})


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  GigShield – AI Parametric Insurance Platform")
    print("  Frontend : http://127.0.0.1:5000")
    print("  API Base : http://127.0.0.1:5000/api")
    print("=" * 60)
    app.run(debug=True)
