import os
import secrets
import time
from functools import wraps

from flask import Flask, jsonify, request

from database import Database

app = Flask(__name__)

# ----------------------------------------------------------------------
# Database connection object (creates data/school.db on first run)
# ----------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db = Database(os.path.join(BASE_DIR, "data", "school.db"))

MAJORS = ["Finance", "Business Analytics", "Information Technology",
          "Marketing", "Accounting"]
LEVELS = ["Freshman", "Sophomore", "Junior", "Senior"]
STUDENT_FIELDS = ["FN", "LN", "Major", "dmajor", "level"]
REPORT_FIELDS = ["Title", "Type", "k1", "k2", "k3", "releaseDate"]

# ----------------------------------------------------------------------
# Authentication
# ----------------------------------------------------------------------
ACCESS_TOKEN_LIFETIME = 30     # seconds (use 5 * 60 for the final version)
REFRESH_TOKEN_LIFETIME = 120   # seconds (use 60 * 60 for the final version)

USERS = {"admin": "1234"}      # demo user: username -> password

access_tokens = {}    # token -> {"user": ..., "exp": ...}
refresh_tokens = {}   # token -> {"user": ..., "exp": ...}


def issue_tokens(username):
    access = secrets.token_urlsafe(32)
    refresh = secrets.token_urlsafe(32)
    now = time.time()
    access_tokens[access] = {"user": username, "exp": now + ACCESS_TOKEN_LIFETIME}
    refresh_tokens[refresh] = {"user": username, "exp": now + REFRESH_TOKEN_LIFETIME}
    return {"access_token": access, "refresh_token": refresh,
            "token_type": "Bearer", "expires_in": ACCESS_TOKEN_LIFETIME}


def token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify(error="Missing or malformed Authorization header"), 401

        token = header.split(" ", 1)[1].strip()
        info = access_tokens.get(token)
        if info is None:
            return jsonify(error="Invalid token"), 401
        if info["exp"] < time.time():
            access_tokens.pop(token, None)
            return jsonify(error="Token expired, please refresh it"), 401

        return f(*args, **kwargs)
    return wrapper


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def missing_fields(data, required):
    """Return the list of required fields that are absent or empty."""
    return [f for f in required if f not in data or data[f] in (None, "")]


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def max_reports(dmajor):
    """Double major -> 2 reports, otherwise 1 report."""
    return 2 if dmajor else 1


def count_reports(student_id):
    return db.query("SELECT COUNT(*) AS c FROM report WHERE ID_S = ?",
                    (student_id,), one=True)["c"]


def get_student_row(student_id):
    return db.query("SELECT * FROM student WHERE ID_S = ?", (student_id,), one=True)


def student_to_dict(row):
    """Turn a student row into a dict with its reports nested inside."""
    student = dict(row)
    student["dmajor"] = bool(student["dmajor"])     # 0/1 in the DB -> true/false
    student["reports"] = [dict(r) for r in db.query(
        "SELECT * FROM report WHERE ID_S = ? ORDER BY ID_R", (student["ID_S"],))]
    return student


def validate_student(data):
    """Check the student fields that are present. Return an error text or None."""
    for field in ("FN", "LN"):
        if field in data and (not isinstance(data[field], str) or not data[field].strip()):
            return f"{field} must be a non-empty text"
    if "Major" in data and data["Major"] not in MAJORS:
        return f"Major must be one of: {', '.join(MAJORS)}"
    if "level" in data and data["level"] not in LEVELS:
        return f"level must be one of: {', '.join(LEVELS)}"
    if "dmajor" in data and not isinstance(data["dmajor"], bool):
        return "dmajor must be true or false"
    return None


def check_reports(report_list, dmajor):
    """Check reports sent inside a student. Return an error text or None."""
    if not isinstance(report_list, list):
        return "reports must be a list"
    limit = max_reports(dmajor)
    if len(report_list) > limit:
        return f"This student can have at most {limit} report(s)"
    for r in report_list:
        if not isinstance(r, dict) or missing_fields(r, ["Title", "Type"]):
            return "Each report needs a Title and a Type"
    return None


# ----------------------------------------------------------------------
# Database status (proof of connection)
# ----------------------------------------------------------------------
@app.route("/db-status", methods=["GET"])
def db_status():
    return jsonify(db.status()), 200


# ----------------------------------------------------------------------
# Auth endpoints
# ----------------------------------------------------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Request body must be a JSON object"), 400
    username = data.get("username")
    password = data.get("password")
    if username is None or USERS.get(username) != password:
        return jsonify(error="Invalid username or password"), 401
    return jsonify(issue_tokens(username)), 200


@app.route("/refresh", methods=["POST"])
def refresh():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Request body must be a JSON object"), 400
    old = data.get("refresh_token")
    info = refresh_tokens.get(old)
    if info is None:
        return jsonify(error="Invalid refresh token"), 401
    if info["exp"] < time.time():
        refresh_tokens.pop(old, None)
        return jsonify(error="Refresh token expired, please log in again"), 401
    refresh_tokens.pop(old)   # a refresh token can be used only once
    return jsonify(issue_tokens(info["user"])), 200


# ----------------------------------------------------------------------
# Students  (GET requires a token)
# ----------------------------------------------------------------------
@app.route("/students", methods=["GET"])
@token_required
def get_students():
    rows = db.query("SELECT * FROM student ORDER BY ID_S")
    return jsonify([student_to_dict(r) for r in rows]), 200


@app.route("/students/<int:student_id>", methods=["GET"])
@token_required
def get_student(student_id):
    row = get_student_row(student_id)
    if row is None:
        return jsonify(error=f"Student {student_id} not found"), 404
    return jsonify(student_to_dict(row)), 200


@app.route("/students", methods=["POST"])
def create_student():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Request body must be a JSON object"), 400

    missing = missing_fields(data, ["FN", "LN", "Major", "level"])
    if missing:
        return jsonify(error=f"Missing field(s): {', '.join(missing)}"), 400
    error = validate_student(data)
    if error:
        return jsonify(error=error), 400

    dmajor = data.get("dmajor", False)
    report_list = data.get("reports", [])
    error = check_reports(report_list, dmajor)
    if error:
        return jsonify(error=error), 400

    # one transaction: the student and its reports are saved together or not at all
    with db.transaction() as conn:
        cur = conn.execute(
            "INSERT INTO student (FN, LN, Major, dmajor, level) VALUES (?, ?, ?, ?, ?)",
            (data["FN"], data["LN"], data["Major"], int(dmajor), data["level"]))
        student_id = cur.lastrowid
        for r in report_list:
            conn.execute(
                "INSERT INTO report (ID_S, Title, Type, k1, k2, k3, releaseDate) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (student_id, r["Title"], r["Type"], r.get("k1"), r.get("k2"),
                 r.get("k3"), r.get("releaseDate")))

    return jsonify(student_to_dict(get_student_row(student_id))), 201


@app.route("/students/<int:student_id>", methods=["PUT"])
def update_student(student_id):
    if get_student_row(student_id) is None:
        return jsonify(error=f"Student {student_id} not found"), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Request body must be a JSON object"), 400
    error = validate_student(data)
    if error:
        return jsonify(error=error), 400
    if data.get("dmajor") is False and count_reports(student_id) > 1:
        return jsonify(error="Cannot remove double major: the student already "
                             "has 2 reports. Delete one report first."), 409

    fields = [f for f in STUDENT_FIELDS if f in data]
    if fields:
        values = [int(data[f]) if f == "dmajor" else data[f] for f in fields]
        sql = ("UPDATE student SET " + ", ".join(f"{f} = ?" for f in fields)
               + " WHERE ID_S = ?")
        db.execute(sql, (*values, student_id))
    return jsonify(student_to_dict(get_student_row(student_id))), 200


@app.route("/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    if get_student_row(student_id) is None:
        return jsonify(error=f"Student {student_id} not found"), 404
    db.execute("DELETE FROM student WHERE ID_S = ?", (student_id,))  # reports cascade
    return jsonify(message=f"Student {student_id} and their reports deleted"), 200


# ----------------------------------------------------------------------
# Reports  (public)
# ----------------------------------------------------------------------
@app.route("/reports", methods=["GET"])
def get_reports():
    student_id = request.args.get("ID_S", type=int)     # optional: /reports?ID_S=1
    if student_id is not None:
        rows = db.query("SELECT * FROM report WHERE ID_S = ? ORDER BY ID_R", (student_id,))
    else:
        rows = db.query("SELECT * FROM report ORDER BY ID_R")
    return jsonify([dict(r) for r in rows]), 200


@app.route("/reports/<int:report_id>", methods=["GET"])
def get_report(report_id):
    row = db.query("SELECT * FROM report WHERE ID_R = ?", (report_id,), one=True)
    if row is None:
        return jsonify(error=f"Report {report_id} not found"), 404
    return jsonify(dict(row)), 200


@app.route("/reports", methods=["POST"])
def create_report():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Request body must be a JSON object"), 400

    missing = missing_fields(data, ["ID_S", "Title", "Type"])
    if missing:
        return jsonify(error=f"Missing field(s): {', '.join(missing)}"), 400
    if not is_int(data["ID_S"]):
        return jsonify(error="ID_S must be an integer"), 400

    student = get_student_row(data["ID_S"])
    if student is None:
        return jsonify(error=f"Student {data['ID_S']} not found"), 404
    if count_reports(student["ID_S"]) >= max_reports(student["dmajor"]):
        return jsonify(error=f"Student {student['ID_S']} has reached the maximum "
                             f"of {max_reports(student['dmajor'])} report(s)"), 409

    report_id, _ = db.execute(
        "INSERT INTO report (ID_S, Title, Type, k1, k2, k3, releaseDate) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (data["ID_S"], data["Title"], data["Type"], data.get("k1"),
         data.get("k2"), data.get("k3"), data.get("releaseDate")))
    row = db.query("SELECT * FROM report WHERE ID_R = ?", (report_id,), one=True)
    return jsonify(dict(row)), 201


@app.route("/reports/<int:report_id>", methods=["PUT"])
def update_report(report_id):
    current = db.query("SELECT * FROM report WHERE ID_R = ?", (report_id,), one=True)
    if current is None:
        return jsonify(error=f"Report {report_id} not found"), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Request body must be a JSON object"), 400
    for field in ("Title", "Type"):
        if field in data and (not isinstance(data[field], str) or not data[field].strip()):
            return jsonify(error=f"{field} must be a non-empty text"), 400

    fields = [f for f in REPORT_FIELDS if f in data]
    values = [data[f] for f in fields]

    # moving the report to another student: that student must exist and have room
    if "ID_S" in data and data["ID_S"] != current["ID_S"]:
        if not is_int(data["ID_S"]):
            return jsonify(error="ID_S must be an integer"), 400
        student = get_student_row(data["ID_S"])
        if student is None:
            return jsonify(error=f"Student {data['ID_S']} not found"), 404
        if count_reports(student["ID_S"]) >= max_reports(student["dmajor"]):
            return jsonify(error=f"Student {student['ID_S']} has reached the maximum "
                                 f"of {max_reports(student['dmajor'])} report(s)"), 409
        fields.append("ID_S")
        values.append(data["ID_S"])

    if fields:
        sql = ("UPDATE report SET " + ", ".join(f"{f} = ?" for f in fields)
               + " WHERE ID_R = ?")
        db.execute(sql, (*values, report_id))
    row = db.query("SELECT * FROM report WHERE ID_R = ?", (report_id,), one=True)
    return jsonify(dict(row)), 200


@app.route("/reports/<int:report_id>", methods=["DELETE"])
def delete_report(report_id):
    _, changed = db.execute("DELETE FROM report WHERE ID_R = ?", (report_id,))
    if changed == 0:
        return jsonify(error=f"Report {report_id} not found"), 404
    return jsonify(message=f"Report {report_id} deleted"), 200


if __name__ == "__main__":
    app.run(debug=True)