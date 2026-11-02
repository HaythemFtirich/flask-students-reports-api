"""Loads the starting data straight into data/school.db (no Postman needed).

Usage:
    python seed.py            add the students/reports from seed_data.json
                              (students that already exist are skipped)
    python seed.py --reset    delete the database file first, then seed
"""
import json
import os
import sys

from database import Database

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "school.db")
SEED_FILE = os.path.join(BASE_DIR, "seed_data.json")


def main():
    if "--reset" in sys.argv and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Old database deleted.")

    db = Database(DB_PATH)      # creates the file and both tables if missing

    with open(SEED_FILE, encoding="utf-8") as f:
        students = json.load(f)

    added_students = added_reports = skipped = 0

    # one transaction: everything is saved together, or nothing is
    with db.transaction() as conn:
        for s in students:
            exists = conn.execute(
                "SELECT 1 FROM student WHERE FN = ? AND LN = ?",
                (s["FN"], s["LN"])).fetchone()
            if exists:
                skipped += 1
                continue

            reports = s.get("reports", [])
            limit = 2 if s["dmajor"] else 1
            if len(reports) > limit:
                raise ValueError(f"{s['FN']} {s['LN']}: {len(reports)} reports "
                                 f"but the limit is {limit}")

            cur = conn.execute(
                "INSERT INTO student (FN, LN, Major, dmajor, level) "
                "VALUES (?, ?, ?, ?, ?)",
                (s["FN"], s["LN"], s["Major"], int(s["dmajor"]), s["level"]))
            student_id = cur.lastrowid
            added_students += 1

            for r in reports:
                conn.execute(
                    "INSERT INTO report (ID_S, Title, Type, k1, k2, k3, releaseDate) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (student_id, r["Title"], r["Type"], r.get("k1"), r.get("k2"),
                     r.get("k3"), r.get("releaseDate")))
                added_reports += 1

    status = db.status()
    print(f"Added {added_students} student(s) and {added_reports} report(s); "
          f"skipped {skipped} already present.")
    print(f"Database file: {DB_PATH}")
    print(f"Rows now: {status['tables']}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(f"Seed cancelled, nothing was saved: {e}")
        sys.exit(1)