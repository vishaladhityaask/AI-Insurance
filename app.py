"""
app.py  –  AI Insurance Phase 1
Main Flask server: routes, DB queries, API endpoints
"""

from flask import (
    Flask, render_template, request,
    jsonify, redirect, url_for, session, flash
)
import mysql.connector
from mysql.connector import Error
from insurance_model import calculate_premium, simulate_weather, recalculate_all_premiums
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ai-insurance-dev-secret-2024")

# ─── DB Config ────────────────────────────────────────────────────────────────

DB_CONFIG = {
    "host":     os.environ.get("DB_HOST", "localhost"),
    "user":     os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "Prithvi@2006"),
    "database": os.environ.get("DB_NAME", "ai_insurance"),
}


def get_db():
    """Return a fresh DB connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"[DB ERROR] {e}")
        return None


def query(sql, params=(), fetchone=False, commit=False):
    """Utility: run a query, return results or last row id."""
    conn = get_db()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        if commit:
            conn.commit()
            return cur.lastrowid
        return cur.fetchone() if fetchone else cur.fetchall()
    except Error as e:
        print(f"[QUERY ERROR] {e}")
        return None
    finally:
        conn.close()


# ─── Public Routes ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    stats = {
        "total_workers": (query("SELECT COUNT(*) AS c FROM workers", fetchone=True) or {}).get("c", 0),
        "active_workers": (query("SELECT COUNT(*) AS c FROM workers WHERE status='active'", fetchone=True) or {}).get("c", 0),
        "avg_premium": (query("SELECT ROUND(AVG(final_premium),2) AS c FROM workers", fetchone=True) or {}).get("c", 0),
        "total_claims": (query("SELECT COUNT(*) AS c FROM claims", fetchone=True) or {}).get("c", 0),
    }
    weather_all = [simulate_weather(r) for r in
                   ["North Zone", "South Zone", "East Zone", "West Zone", "Central Zone"]]
    return render_template("index.html", stats=stats, weather_all=weather_all)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.form
        occupation = data.get("occupation", "").strip()
        age        = int(data.get("age", 30))
        region     = data.get("region", "Central Zone")

        # Run AI premium calculation
        result = calculate_premium(occupation, age, region)

        worker_id = query(
            """INSERT INTO workers
               (full_name, email, phone, occupation, age, region,
                risk_level, base_premium, final_premium, weather_factor, status)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')""",
            (
                data.get("full_name"), data.get("email"), data.get("phone"),
                occupation, age, region,
                result["risk_level"],
                result["base_premium"],
                result["final_premium"],
                result["weather_factor"],
            ),
            commit=True
        )

        session["last_registration"] = {
            "id":            worker_id,
            "name":          data.get("full_name"),
            "premium":       result["final_premium"],
            "risk_level":    result["risk_level"],
            "weather":       result["weather"]["condition"],
            "breakdown":     result["breakdown"],
        }
        return redirect(url_for("dashboard", worker_id=worker_id))

    return render_template("register.html")


@app.route("/dashboard")
@app.route("/dashboard/<int:worker_id>")
def dashboard(worker_id=None):
    worker = None
    if worker_id:
        worker = query("SELECT * FROM workers WHERE id=%s", (worker_id,), fetchone=True)
    reg_info = session.pop("last_registration", None)
    claims   = []
    if worker:
        claims = query("SELECT * FROM claims WHERE worker_id=%s ORDER BY filed_at DESC", (worker["id"],))
    return render_template("dashboard.html", worker=worker, reg_info=reg_info, claims=claims or [])


# ─── Admin Routes ─────────────────────────────────────────────────────────────

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST" and not session.get("admin"):
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
        else:
            flash("Invalid password", "error")
            return redirect(url_for("admin"))

    if not session.get("admin"):
        return render_template("admin.html", locked=True)

    workers  = query("SELECT * FROM workers ORDER BY registered_at DESC") or []
    claims   = query("""
        SELECT c.*, w.full_name, w.occupation
        FROM claims c JOIN workers w ON c.worker_id=w.id
        ORDER BY c.filed_at DESC LIMIT 50
    """) or []
    stats = {
        "total":     len(workers),
        "active":    sum(1 for w in workers if w["status"] == "active"),
        "pending":   sum(1 for w in workers if w["status"] == "pending"),
        "high_risk": sum(1 for w in workers if w["risk_level"] == "high"),
        "avg_prem":  round(sum(w["final_premium"] for w in workers) / len(workers), 2) if workers else 0,
    }
    return render_template("admin.html", locked=False, workers=workers, claims=claims, stats=stats)


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin"))


@app.route("/admin/update-status", methods=["POST"])
def update_status():
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    wid    = request.json.get("id")
    status = request.json.get("status")
    query("UPDATE workers SET status=%s WHERE id=%s", (status, wid), commit=True)
    return jsonify({"success": True})


@app.route("/admin/recalculate", methods=["POST"])
def recalculate():
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    workers = query("SELECT id, occupation, age, region FROM workers") or []
    updates = recalculate_all_premiums(workers)
    for u in updates:
        query(
            "UPDATE workers SET final_premium=%s, weather_factor=%s, risk_level=%s WHERE id=%s",
            (u["final_premium"], u["weather_factor"], u["risk_level"], u["id"]),
            commit=True
        )
    return jsonify({"success": True, "updated": len(updates)})


# ─── JSON API ─────────────────────────────────────────────────────────────────

@app.route("/api/calculate-premium", methods=["POST"])
def api_calculate():
    d = request.json or {}
    try:
        result = calculate_premium(
            d.get("occupation", "office worker"),
            int(d.get("age", 30)),
            d.get("region", "Central Zone"),
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/weather/<region>")
def api_weather(region):
    return jsonify(simulate_weather(region))


@app.route("/api/workers")
def api_workers():
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    workers = query("SELECT * FROM workers ORDER BY registered_at DESC") or []
    return jsonify(workers)


@app.route("/api/claim", methods=["POST"])
def file_claim():
    d = request.json or {}
    claim_id = query(
        "INSERT INTO claims (worker_id, claim_type, amount, description) VALUES (%s,%s,%s,%s)",
        (d.get("worker_id"), d.get("claim_type"), d.get("amount"), d.get("description")),
        commit=True
    )
    return jsonify({"success": True, "claim_id": claim_id})


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
