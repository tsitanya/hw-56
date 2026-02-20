from flask import Flask, request, jsonify
import psycopg2
import redis
import json
import os

app = Flask(__name__)

def get_db():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "postgres"),
        database=os.environ.get("DB_NAME", "mydb"),
        user=os.environ.get("DB_USER", "myuser"),
        password=os.environ.get("DB_PASS", "mypassword")
    )

def get_redis():
    return redis.Redis(host=os.environ.get("REDIS_HOST", "redis"), port=6379, db=0)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL
        )
    """)
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO users (name, email) VALUES (%s, %s), (%s, %s)",
                    ("Alice", "alice@example.com", "Bob", "bob@example.com"))
    conn.commit()
    cur.close()
    conn.close()

@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id, name, email",
                (data["name"], data["email"]))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    r = get_redis()
    r.delete("users_all")
    return jsonify({"id": row[0], "name": row[1], "email": row[2]}), 201

@app.route("/users", methods=["GET"])
def get_users():
    r = get_redis()
    cached = r.get("users_all")
    if cached:
        return jsonify({"source": "redis_cache", "data": json.loads(cached)})
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email FROM users")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    data = [{"id": r[0], "name": r[1], "email": r[2]} for r in rows]
    get_redis().setex("users_all", 60, json.dumps(data))
    return jsonify({"source": "database", "data": data})

@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    r = get_redis()
    cache_key = f"user_{user_id}"
    cached = r.get(cache_key)
    if cached:
        return jsonify({"source": "redis_cache", "data": json.loads(cached)})
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if not row:
        return jsonify({"error": "User not found"}), 404
    
    data = {"id": row[0], "name": row[1], "email": row[2]}
    get_redis().setex(cache_key, 60, json.dumps(data))
    return jsonify({"source": "database", "data": data})

@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET name=%s, email=%s WHERE id=%s RETURNING id, name, email",
                (data["name"], data["email"], user_id))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    if not row:
        return jsonify({"error": "User not found"}), 404
    
    r = get_redis()
    r.delete("users_all")
    r.delete(f"user_{user_id}")
    return jsonify({"id": row[0], "name": row[1], "email": row[2]})

@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=%s RETURNING id", (user_id,))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    if not row:
        return jsonify({"error": "User not found"}), 404
    
    r = get_redis()
    r.delete("users_all")
    r.delete(f"user_{user_id}")
    return jsonify({"message": f"User {user_id} deleted"})

if __name__ == "__main__":
    init_db()
    app.run()