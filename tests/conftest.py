"""
Pytest configuration and fixtures for BlockShelf tests.
"""
import pytest
from django.contrib.auth import get_user_model
from inventory.models import InventoryItem, UserPreference

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


@pytest.fixture
def other_user(db):
    """Create another test user for permission tests."""
    return User.objects.create_user(
        username='otheruser',
        email='other@example.com',
        password='otherpass123'
    )


@pytest.fixture
def user_preferences(user):
    """Create user preferences."""
    return UserPreference.objects.create(
        user=user,
        theme='light',
        rebrickable_api_key='test_api_key_123'
    )


@pytest.fixture
def inventory_item(user):
    """Create a test inventory item."""
    return InventoryItem.objects.create(
        user=user,
        name='Test Brick 2x4',
        part_id='3001',
        color='Red',
        quantity_total=100,
        quantity_used=10,
        storage_location='Box A1',
        notes='Test item for unit tests'
    )


@pytest.fixture
def inventory_items(user):
    """Create multiple test inventory items."""
    items = []
    for i in range(5):
        items.append(InventoryItem.objects.create(
            user=user,
            name=f'Test Part {i}',
            part_id=f'300{i}',
            color='Blue' if i % 2 == 0 else 'Red',
            quantity_total=10 * (i + 1),
            quantity_used=i,
            storage_location=f'Box B{i + 1}'
        ))
    return items


@pytest.fixture
def authenticated_client(client, user):
    """Return a Django test client with authenticated user."""
    client.force_login(user)
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Return a Django test client with authenticated admin."""
    client.force_login(admin_user)
    return client
