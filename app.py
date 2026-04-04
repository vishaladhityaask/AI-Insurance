"""
app.py  —  GigShield Phase 2
==============================
Full REST API backend with:
  - Dynamic ML premium calculation
  - Policy management
  - Zero-touch claims engine
  - 5 automated disruption triggers
  - Claims history
"""

import os
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error

from insurance_model import (
    calculate_dynamic_premium,
    simulate_disruptions,
    process_auto_claim,
    get_policy_details,
    get_coverage_details,
)

# ─────────────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=".")
CORS(app)
app.secret_key = "gigshield_phase2_secret"


# ─────────────────────────────────────────────────────────────────────────────
# DB CONNECTION
# ─────────────────────────────────────────────────────────────────────────────
def get_db():
    try:
        return mysql.connector.connect(
            host     = os.environ.get("MYSQLHOST",     "localhost"),
            port     = int(os.environ.get("MYSQLPORT", 3306)),
            user     = os.environ.get("MYSQLUSER",     "root"),
            password = "Mysql@1234",
            database = os.environ.get("MYSQLDATABASE", "gig_insurance"),
        )
    except Error as e:
        print(f"[DB] {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# SERVE FRONTEND
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_file("gigshield_p2.html")


# ─────────────────────────────────────────────────────────────────────────────
# API — REGISTER WORKER (with dynamic premium)
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/register", methods=["POST"])
def api_register():
    data         = request.get_json()
    name         = (data.get("name") or "").strip()
    city         = (data.get("city") or "").strip()
    platform     = (data.get("platform") or "").strip()
    daily_income = data.get("daily_income")
    hours_per_day = float(data.get("hours_per_day", 8))

    if not all([name, city, platform, daily_income]):
        return jsonify({"success": False, "error": "All fields are required."}), 400

    try:
        daily_income = int(daily_income)
        if daily_income <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Daily income must be a positive number."}), 400

    # Dynamic ML premium
    pricing = calculate_dynamic_premium(daily_income, city, platform, hours_per_day)
    premium = pricing["premium"]

    conn = get_db()
    if not conn:
        return jsonify({"success": False, "error": "Database connection failed."}), 500

    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO workers (name, city, platform, daily_income, premium, hours_per_day)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, city, platform, daily_income, premium, hours_per_day))
        conn.commit()
        worker_id = cur.lastrowid
    except Error as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close(); conn.close()

    return jsonify({
        "success": True,
        "worker": {
            "id": worker_id, "name": name, "city": city,
            "platform": platform, "daily_income": daily_income,
            "hours_per_day": hours_per_day, "premium": premium,
            "plan": pricing["plan"], "coverage": pricing["coverage"],
        },
        "pricing": pricing,
    }), 201


# ─────────────────────────────────────────────────────────────────────────────
# API — DYNAMIC PREMIUM PREVIEW (before registration)
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/premium-preview", methods=["POST"])
def api_premium_preview():
    data         = request.get_json()
    daily_income = int(data.get("daily_income", 0))
    city         = data.get("city", "Mumbai")
    platform     = data.get("platform", "Other")
    hours        = float(data.get("hours_per_day", 8))

    if daily_income <= 0:
        return jsonify({"success": False, "error": "Invalid income"}), 400

    pricing = calculate_dynamic_premium(daily_income, city, platform, hours)
    return jsonify({"success": True, "pricing": pricing})


# ─────────────────────────────────────────────────────────────────────────────
# API — GET ALL WORKERS
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/workers", methods=["GET"])
def api_get_workers():
    conn = get_db()
    if not conn:
        return jsonify({"success": False, "error": "DB failed"}), 500
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM workers ORDER BY id DESC")
        workers = cur.fetchall()
    finally:
        cur.close(); conn.close()

    for w in workers:
        cov = get_coverage_details(w["premium"])
        w["plan"]     = cov["description"].split("–")[0].strip()
        w["coverage"] = cov["weekly_coverage"]
        if w.get("registered_at"):
            w["registered_at"] = str(w["registered_at"])

    total         = len(workers)
    total_premium = sum(w["premium"] for w in workers)
    return jsonify({
        "success": True, "workers": workers,
        "total": total, "total_premium": total_premium,
        "avg_premium": round(total_premium / total) if total else 0,
    })


# ─────────────────────────────────────────────────────────────────────────────
# API — GET SINGLE WORKER + POLICY
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/worker/<int:worker_id>", methods=["GET"])
def api_get_worker(worker_id):
    conn = get_db()
    if not conn:
        return jsonify({"success": False, "error": "DB failed"}), 500
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM workers WHERE id = %s", (worker_id,))
        worker = cur.fetchone()
    finally:
        cur.close(); conn.close()

    if not worker:
        return jsonify({"success": False, "error": "Worker not found"}), 404

    cov = get_coverage_details(worker["premium"])
    worker["plan"]     = cov["description"].split("–")[0].strip()
    worker["coverage"] = cov["weekly_coverage"]
    if worker.get("registered_at"):
        worker["registered_at"] = str(worker["registered_at"])

    policy = get_policy_details(worker)
    return jsonify({"success": True, "worker": worker, "policy": policy})


# ─────────────────────────────────────────────────────────────────────────────
# API — DELETE WORKER
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/worker/<int:worker_id>", methods=["DELETE"])
def api_delete_worker(worker_id):
    conn = get_db()
    if not conn:
        return jsonify({"success": False, "error": "DB failed"}), 500
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM workers WHERE id = %s", (worker_id,))
        conn.commit()
        affected = cur.rowcount
    finally:
        cur.close(); conn.close()

    if affected == 0:
        return jsonify({"success": False, "error": "Worker not found"}), 404
    return jsonify({"success": True})


# ─────────────────────────────────────────────────────────────────────────────
# API — DISRUPTION TRIGGERS (5 automated triggers)
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/disruptions/<city>", methods=["GET"])
def api_disruptions(city):
    disruption = simulate_disruptions(city)
    return jsonify({"success": True, "disruption": disruption})


# ─────────────────────────────────────────────────────────────────────────────
# API — ZERO-TOUCH CLAIM SUBMISSION
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/claim", methods=["POST"])
def api_submit_claim():
    data      = request.get_json()
    worker_id = data.get("worker_id")

    conn = get_db()
    if not conn:
        return jsonify({"success": False, "error": "DB failed"}), 500

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM workers WHERE id = %s", (worker_id,))
        worker = cur.fetchone()
    finally:
        cur.close(); conn.close()

    if not worker:
        return jsonify({"success": False, "error": "Worker not found"}), 404

    # Get live disruption for worker's city
    disruption = simulate_disruptions(worker["city"])

    if not disruption["claim_eligible"]:
        return jsonify({
            "success": False,
            "error":   "No active disruption trigger in your city right now.",
            "disruption": disruption,
        }), 400

    # Process zero-touch claim
    claim = process_auto_claim(worker, disruption)

    if not claim["success"]:
        return jsonify({"success": False, "error": claim["reason"]}), 400

    # Save claim to DB
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claims
              (worker_id, claim_id, trigger_type, trigger_label,
               payout_amount, coverage_pct, status, processed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            worker_id, claim["claim_id"], claim["trigger"],
            claim["trigger_label"], claim["payout_amount"],
            claim["coverage_pct"], claim["status"],
        ))
        conn.commit()
    except Error as e:
        print(f"[CLAIM DB] {e}")   # non-fatal — claim data still returned
    finally:
        cur.close(); conn.close()

    return jsonify({
        "success": True,
        "claim":   claim,
        "disruption": disruption,
    })


# ─────────────────────────────────────────────────────────────────────────────
# API — CLAIMS HISTORY FOR A WORKER
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/claims/<int:worker_id>", methods=["GET"])
def api_claims_history(worker_id):
    conn = get_db()
    if not conn:
        return jsonify({"success": False, "error": "DB failed"}), 500
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT * FROM claims
            WHERE worker_id = %s
            ORDER BY processed_at DESC
            LIMIT 20
        """, (worker_id,))
        claims = cur.fetchall()
    finally:
        cur.close(); conn.close()

    for c in claims:
        if c.get("processed_at"):
            c["processed_at"] = str(c["processed_at"])

    total_paid = sum(c["payout_amount"] for c in claims)
    return jsonify({
        "success": True,
        "claims":  claims,
        "total_claims": len(claims),
        "total_paid":   total_paid,
    })


# ─────────────────────────────────────────────────────────────────────────────
# API — ALL CLAIMS (admin view)
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/claims", methods=["GET"])
def api_all_claims():
    conn = get_db()
    if not conn:
        return jsonify({"success": False, "error": "DB failed"}), 500
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT c.*, w.name as worker_name, w.city
            FROM claims c
            JOIN workers w ON c.worker_id = w.id
            ORDER BY c.processed_at DESC
        """)
        claims = cur.fetchall()
        cur.execute("SELECT SUM(payout_amount) as total FROM claims")
        total  = cur.fetchone()["total"] or 0
    finally:
        cur.close(); conn.close()

    for c in claims:
        if c.get("processed_at"):
            c["processed_at"] = str(c["processed_at"])

    return jsonify({
        "success": True, "claims": claims,
        "total_claims": len(claims), "total_paid": total,
    })


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  GigShield Phase 2  —  AI Parametric Insurance")
    print("  http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)
