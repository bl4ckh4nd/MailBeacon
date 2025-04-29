from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.config import settings

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": f"Welcome to {settings.app_name}. Visit /docs for documentation."}

def test_find_email_invalid_input():
    response = client.post("/api/v1/find-single", json={
        "first_name": "",  # Invalid - empty string
        "last_name": "Doe",
        "domain": "example.com"
    })
    assert response.status_code == 422  # Validation error

def test_find_email_invalid_domain():
    response = client.post("/api/v1/find-single", json={
        "first_name": "John",
        "last_name": "Doe",
        "domain": "thisisaninvaliddomain12345.com"
    })
    assert response.status_code == 404  # Domain not found

def test_find_emails_batch_empty():
    response = client.post("/api/v1/find-batch", json={
        "contacts": []
    })
    assert response.status_code == 200
    assert response.json() == []

