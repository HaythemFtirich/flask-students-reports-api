# flask-students-reports-api

# Homework: Students & Reports Web Service

A Flask REST API with two resources (students and reports), token authentication
for student endpoints, token expiration and refreshing.

## Run it
    pip install -r requirements.txt
    python app.py

## Endpoints
- POST /login, POST /refresh
- /students: GET all, GET by id (token required), POST, PUT, DELETE
- /reports: GET all, GET by id (public), POST, PUT, DELETE

Demo credentials: admin / 1234
Test with the included Postman collection.
