from fastapi.testclient import TestClient
from app.main import app

def test_health_and_validation():
    # Listener binding may be unavailable in a restricted CI sandbox; REST remains usable.
    with TestClient(app) as client:
        assert client.get('/api/health').status_code == 200
        assert client.post('/api/dns/query',json={'domain':'not valid','record_type':'A'}).status_code == 422
        assert client.get('/api/analytics/summary').status_code == 200
        assert client.delete('/api/cache').status_code == 200
