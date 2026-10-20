import secrets
import time
from functools import wraps

from flask import Flask, jsonify, request

app = Flask(__name__)

students = [
    {
        "ID_S": 1,
        "FN": "Haythem",
        "LN": "Ftirich",
        "Major": "Information Technology",
        "dmajor": False,
        "level": "Senior"
    }
]

reports = [
    {
        "ID_R": 1,
        "Title": "Web Services",
        "Type": "Technical",
        "k1": "Flask",
        "k2": "REST API",
        "k3": "Python",
        "releaseDate": "2026-03-20"
    }
]


ACCESS_TOKEN_LIFETIME = 30     # seconds
REFRESH_TOKEN_LIFETIME = 120   # seconds

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
def next_id(items, key):
    """Return the next free ID: the biggest existing ID + 1."""
    return max((item[key] for item in items), default=0) + 1
 
 
def find(items, key, value):
    """Return the item whose `key` equals `value`, or None if not found."""
    for item in items:
        if item[key] == value:
            return item
    return None
 
 
def missing_fields(data, required):
    """Return the list of required fields that are absent or empty."""
    return [f for f in required if f not in data or data[f] in (None, "")]









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
# Students
# ----------------------------------------------------------------------







@app.route("/students", methods=["GET"])
@token_required
def get_students():
    return jsonify(students), 200




 
 
@app.route("/students/<int:student_id>", methods=["GET"])
@token_required
def get_student(student_id):
    student = find(students, "ID_S", student_id)
    if student is None:
        return jsonify(error=f"Student {student_id} not found"), 404
    return jsonify(student), 200




 
 
@app.route("/students", methods=["POST"])
def create_student():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Request body must be a JSON object"), 400
 
    missing = missing_fields(data, ["FN", "LN", "Major", "level"])
    if missing:
        return jsonify(error=f"Missing field(s): {', '.join(missing)}"), 400
 
    dmajor = data.get("dmajor", False)
    if not isinstance(dmajor, bool):
        return jsonify(error="dmajor must be true or false"), 400
 
    student = {
        "ID_S": next_id(students, "ID_S"),
        "FN": data["FN"],
        "LN": data["LN"],
        "Major": data["Major"],
        "dmajor": dmajor,
        "level": data["level"],
    }
    students.append(student)
    return jsonify(student), 201




 
 
@app.route("/students/<int:student_id>", methods=["PUT"])
def update_student(student_id):
    student = find(students, "ID_S", student_id)
    if student is None:
        return jsonify(error=f"Student {student_id} not found"), 404
 
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Request body must be a JSON object"), 400
    if "dmajor" in data and not isinstance(data["dmajor"], bool):
        return jsonify(error="dmajor must be true or false"), 400
 
    for field in ["FN", "LN", "Major", "dmajor", "level"]:
        if field in data:
            student[field] = data[field]
    return jsonify(student), 200





 
 
@app.route("/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    student = find(students, "ID_S", student_id)
    if student is None:
        return jsonify(error=f"Student {student_id} not found"), 404
    students.remove(student)
    return jsonify(message=f"Student {student_id} deleted"), 200








 
 
# ----------------------------------------------------------------------
# Reports
# ----------------------------------------------------------------------






@app.route("/reports", methods=["GET"])
def get_reports():
    return jsonify(reports), 200
 
 
@app.route("/reports/<int:report_id>", methods=["GET"])
def get_report(report_id):
    report = find(reports, "ID_R", report_id)
    if report is None:
        return jsonify(error=f"Report {report_id} not found"), 404
    return jsonify(report), 200
 
 
@app.route("/reports", methods=["POST"])
def create_report():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Request body must be a JSON object"), 400
 
    missing = missing_fields(data, ["Title", "Type", "releaseDate"])
    if missing:
        return jsonify(error=f"Missing field(s): {', '.join(missing)}"), 400
 
    report = {
        "ID_R": next_id(reports, "ID_R"),
        "Title": data["Title"],
        "Type": data["Type"],
        "k1": data.get("k1"),
        "k2": data.get("k2"),
        "k3": data.get("k3"),
        "releaseDate": data["releaseDate"],
    }
    reports.append(report)
    return jsonify(report), 201
 
 
@app.route("/reports/<int:report_id>", methods=["PUT"])
def update_report(report_id):
    report = find(reports, "ID_R", report_id)
    if report is None:
        return jsonify(error=f"Report {report_id} not found"), 404
 
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Request body must be a JSON object"), 400
 
    for field in ["Title", "Type", "k1", "k2", "k3", "releaseDate"]:
        if field in data:
            report[field] = data[field]
    return jsonify(report), 200
 
 
@app.route("/reports/<int:report_id>", methods=["DELETE"])
def delete_report(report_id):
    report = find(reports, "ID_R", report_id)
    if report is None:
        return jsonify(error=f"Report {report_id} not found"), 404
    reports.remove(report)
    return jsonify(message=f"Report {report_id} deleted"), 200
 
 
if __name__ == "__main__":
    app.run(debug=True)