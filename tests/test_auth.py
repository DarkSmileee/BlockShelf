"""
Tests for authentication and authorization.
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

pytestmark = pytest.mark.auth


class TestAuthentication:
    """Test user authentication."""

    def test_user_creation(self, db):
        """Test creating a new user."""
        user = User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='newpass123'
        )
        assert user.username == 'newuser'
        assert user.email == 'new@example.com'
        assert user.check_password('newpass123')
        assert not user.is_staff
        assert not user.is_superuser

    def test_superuser_creation(self, db):
        """Test creating a superuser."""
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        assert admin.is_staff
        assert admin.is_superuser

    def test_login_required(self, client):
        """Test that inventory views require authentication."""
        response = client.get(reverse('inventory:list'))
        assert response.status_code == 302  # Redirect to login
        assert '/accounts/login/' in response.url

    def test_authenticated_access(self, authenticated_client):
        """Test that authenticated users can access inventory."""
        response = authenticated_client.get(reverse('inventory:list'))
        assert response.status_code == 200

    def test_login_logout(self, client, user):
        """Test login and logout flow."""
        # Login
        logged_in = client.login(username='testuser', password='testpass123')
        assert logged_in

        # Access protected view
        response = client.get(reverse('inventory:list'))
        assert response.status_code == 200

        # Logout
        client.logout()

        # Should redirect after logout
        response = client.get(reverse('inventory:list'))
        assert response.status_code == 302


class TestUserPermissions:
    """Test user permissions and access control."""

    def test_user_can_only_see_own_inventory(self, authenticated_client, user, other_user):
        """Test that users can only see their own inventory items."""
        from inventory.models import InventoryItem

        # Create item for current user
        item1 = InventoryItem.objects.create(
            user=user,
            name='My Item',
            part_id='3001',
            color='Red',
            quantity_total=10
        )

        # Create item for other user
        item2 = InventoryItem.objects.create(
            user=other_user,
            name='Their Item',
            part_id='3002',
            color='Blue',
            quantity_total=20
        )

        # Access inventory list
        response = authenticated_client.get(reverse('inventory:list'))
        assert response.status_code == 200

        # Should see own item
        content = response.content.decode()
        assert 'My Item' in content

        # Should not see other user's item
        assert 'Their Item' not in content

    def test_user_cannot_edit_others_item(self, authenticated_client, user, other_user):
        """Test that users cannot edit other users' items."""
        from inventory.models import InventoryItem

        # Create item owned by other user
        item = InventoryItem.objects.create(
            user=other_user,
            name='Their Item',
            part_id='3001',
            color='Red',
            quantity_total=10
        )

        # Try to access edit page
        response = authenticated_client.get(
            reverse('inventory:edit', kwargs={'pk': item.pk})
        )
        # Should get 404 (item doesn't exist in user's queryset)
        assert response.status_code == 404

    def test_user_cannot_delete_others_item(self, authenticated_client, user, other_user):
        """Test that users cannot delete other users' items."""
        from inventory.models import InventoryItem

        # Create item owned by other user
        item = InventoryItem.objects.create(
            user=other_user,
            name='Their Item',
            part_id='3001',
            color='Red',
            quantity_total=10
        )

        # Try to delete
        response = authenticated_client.post(
            reverse('inventory:delete', kwargs={'pk': item.pk})
        )
        # Should get 404
        assert response.status_code == 404

        # Item should still exist
        assert InventoryItem.objects.filter(pk=item.pk).exists()

    def test_admin_can_access_admin_site(self, admin_client):
        """Test that admin users can access Django admin."""
        response = admin_client.get('/admin/')
        assert response.status_code == 200

    def test_regular_user_cannot_access_admin(self, authenticated_client):
        """Test that regular users cannot access Django admin."""
        response = authenticated_client.get('/admin/')
        # Should redirect to login
        assert response.status_code == 302
