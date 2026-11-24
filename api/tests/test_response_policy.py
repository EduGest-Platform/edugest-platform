"""Isolated HTTP response tests; no database or external calls."""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.core.error_handling import install_error_handling
from app.core.response_policy import SecurityResponseMiddleware


def application(environment="production"):
    app = FastAPI()
    install_error_handling(app)
    app.add_middleware(CORSMiddleware, allow_origins=["https://synthetic.example"], allow_methods=["GET"])
    app.add_middleware(SecurityResponseMiddleware, environment=environment)

    @app.get('/api/v1/example')
    def example(code: int = 200):
        if code == 500:
            raise RuntimeError('Synthetic private exception')
        if code != 200:
            raise HTTPException(code, 'Synthetic denial')
        return {'status': 'synthetic'}

    return app


@pytest.mark.parametrize('code', [200, 401, 403, 404, 422, 500])
def test_security_policy_covers_success_and_errors(code):
    with TestClient(application()) as client:
        response = client.get('/api/v1/example', params={'code': 'invalid' if code == 422 else code})
    assert response.status_code == code
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert response.headers['x-frame-options'] == 'DENY'
    assert response.headers['referrer-policy'] == 'no-referrer'
    if code != 200:
        assert 'request_id' in response.json()
    assert 'Synthetic private exception' not in response.text


@pytest.mark.parametrize(('environment', 'url', 'hsts'), [
    ('production', 'https://testserver', True), ('staging', 'https://testserver', True),
    ('local', 'https://testserver', False), ('production', 'http://testserver', False),
])
def test_hsts_only_for_nonlocal_https(environment, url, hsts):
    with TestClient(application(environment), base_url=url) as client:
        response = client.get('/api/v1/example', headers={'X-Forwarded-Proto': 'https'})
    assert ('strict-transport-security' in response.headers) is hsts


def test_cors_preflight_is_preserved_and_hardened():
    with TestClient(application()) as client:
        response = client.options('/api/v1/example', headers={'Origin': 'https://synthetic.example', 'Access-Control-Request-Method': 'GET'})
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'https://synthetic.example'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert response.headers['cache-control'] == 'no-store'


def test_swagger_documentation_is_not_given_a_breaking_content_security_policy():
    with TestClient(application()) as client:
        response = client.get('/docs')
    assert response.status_code == 200
    assert 'content-security-policy' not in response.headers
