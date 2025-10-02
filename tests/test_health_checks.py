"""
Tests for health check endpoints.
"""
import pytest
from django.urls import reverse


class TestHealthChecks:
    """Test health check endpoints."""

    def test_liveness_check(self, client):
        """Test liveness check endpoint."""
        response = client.get(reverse('inventory:liveness'))
        assert response.status_code == 200

        data = response.json()
        assert data['status'] == 'alive'
        assert 'timestamp' in data

    def test_readiness_check_healthy(self, client, db):
        """Test readiness check when database is available."""
        response = client.get(reverse('inventory:readiness'))
        assert response.status_code == 200

        data = response.json()
        assert data['status'] == 'ready'
        assert 'timestamp' in data

    def test_health_check_comprehensive(self, client, db):
        """Test comprehensive health check."""
        response = client.get(reverse('inventory:health'))
        assert response.status_code == 200

        data = response.json()
        assert data['status'] == 'healthy'
        assert 'checks' in data
        assert 'database' in data['checks']
        assert 'cache' in data['checks']
        assert 'disk' in data['checks']

        # Database check should be OK
        assert data['checks']['database']['status'] == 'ok'
        assert 'latency_ms' in data['checks']['database']

    def test_health_check_no_auth_required(self, client):
        """Test that health checks don't require authentication."""
        # Liveness
        response = client.get(reverse('inventory:liveness'))
        assert response.status_code == 200

        # Readiness
        response = client.get(reverse('inventory:readiness'))
        assert response.status_code == 200

        # Health
        response = client.get(reverse('inventory:health'))
        assert response.status_code == 200

    def test_metrics_endpoint(self, client, db, user, inventory_items):
        """Test metrics endpoint."""
        response = client.get(reverse('inventory:metrics'))
        assert response.status_code == 200

        data = response.json()
        assert 'active_users' in data
        assert 'total_items' in data
        assert 'timestamp' in data

        # Should have at least 1 active user
        assert data['active_users'] >= 1

        # Should have inventory items
        assert data['total_items'] >= len(inventory_items)
