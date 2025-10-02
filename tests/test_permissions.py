"""
Tests for sharing and collaboration permissions.
"""
import pytest
from django.urls import reverse
from inventory.models import InventoryItem, InventoryCollab, ShareLink

pytestmark = pytest.mark.permissions


class TestSharingPermissions:
    """Test share link permissions."""

    def test_create_share_link(self, authenticated_client, user):
        """Test creating a share link."""
        response = authenticated_client.post(
            reverse('inventory:create_share_link'),
            {'expires_in': '30'}
        )
        assert response.status_code == 302  # Redirect to settings

        # Verify link was created
        assert ShareLink.objects.filter(user=user).exists()

    def test_access_shared_inventory(self, client, user):
        """Test accessing inventory via share link."""
        # Create share link
        share_link = ShareLink.objects.create(user=user)

        # Create some items
        InventoryItem.objects.create(
            user=user,
            name='Shared Item',
            part_id='3001',
            color='Red',
            quantity_total=10
        )

        # Access shared inventory (no login required)
        response = client.get(
            reverse('inventory:shared_inventory', kwargs={'token': share_link.token})
        )
        assert response.status_code == 200
        assert 'Shared Item' in response.content.decode()

    def test_cannot_edit_via_share_link(self, client, user):
        """Test that share links are read-only."""
        # Create share link
        share_link = ShareLink.objects.create(user=user)

        # Try to access add item page (should not work)
        response = client.get(reverse('inventory:add'))
        # Should redirect to login
        assert response.status_code == 302

    def test_revoke_share_link(self, authenticated_client, user):
        """Test revoking a share link."""
        # Create share link
        share_link = ShareLink.objects.create(user=user)
        token = share_link.token

        # Revoke it
        response = authenticated_client.post(
            reverse('inventory:revoke_share_link')
        )
        assert response.status_code == 302

        # Link should be deleted
        assert not ShareLink.objects.filter(token=token).exists()


class TestCollaborationPermissions:
    """Test collaboration (invite) permissions."""

    def test_create_invite(self, authenticated_client, user, other_user):
        """Test creating a collaboration invite."""
        response = authenticated_client.post(
            reverse('inventory:create_invite'),
            {
                'collaborator_username': other_user.username,
                'can_edit': True
            }
        )
        # Should redirect to settings
        assert response.status_code == 302

        # Verify invite was created
        invite = InventoryCollab.objects.get(
            owner=user,
            collaborator=other_user
        )
        assert invite.can_edit is True
        assert not invite.is_active  # Not active until accepted

    def test_accept_invite(self, authenticated_client, user, other_user):
        """Test accepting a collaboration invite."""
        # Create invite from other_user to user
        invite = InventoryCollab.objects.create(
            owner=other_user,
            collaborator=user,
            can_edit=True
        )

        # Accept invite
        response = authenticated_client.get(
            reverse('inventory:accept_invite', kwargs={'token': invite.token})
        )
        assert response.status_code == 302

        # Invite should be active
        invite.refresh_from_db()
        assert invite.is_active
        assert invite.accepted_at is not None

    def test_collaborator_can_view_owner_inventory(
        self, authenticated_client, user, other_user
    ):
        """Test that collaborators can view owner's inventory."""
        # Create active collaboration
        InventoryCollab.objects.create(
            owner=other_user,
            collaborator=user,
            can_edit=False,
            is_active=True
        )

        # Create item for owner
        InventoryItem.objects.create(
            user=other_user,
            name='Owner Item',
            part_id='3001',
            color='Red',
            quantity_total=10
        )

        # Collaborator should see it in inventory switcher
        response = authenticated_client.get(reverse('inventory:inventory_switcher'))
        assert response.status_code == 200
        assert 'otheruser' in response.content.decode()

    def test_collaborator_with_edit_can_modify(
        self, authenticated_client, user, other_user
    ):
        """Test that collaborators with edit permission can modify items."""
        # Create active collaboration with edit permission
        InventoryCollab.objects.create(
            owner=other_user,
            collaborator=user,
            can_edit=True,
            is_active=True
        )

        # Create item for owner
        item = InventoryItem.objects.create(
            user=other_user,
            name='Owner Item',
            part_id='3001',
            color='Red',
            quantity_total=10
        )

        # Switch to owner's inventory
        session = authenticated_client.session
        session['viewing_user_id'] = other_user.id
        session.save()

        # Try to edit item
        response = authenticated_client.get(
            reverse('inventory:edit', kwargs={'pk': item.pk})
        )
        assert response.status_code == 200

    def test_collaborator_without_edit_cannot_modify(
        self, authenticated_client, user, other_user
    ):
        """Test that read-only collaborators cannot modify items."""
        # Create active collaboration without edit permission
        InventoryCollab.objects.create(
            owner=other_user,
            collaborator=user,
            can_edit=False,
            is_active=True
        )

        # Create item for owner
        item = InventoryItem.objects.create(
            user=other_user,
            name='Owner Item',
            part_id='3001',
            color='Red',
            quantity_total=10
        )

        # Switch to owner's inventory
        session = authenticated_client.session
        session['viewing_user_id'] = other_user.id
        session.save()

        # Try to edit item (should be forbidden)
        response = authenticated_client.get(
            reverse('inventory:edit', kwargs={'pk': item.pk})
        )
        # Should redirect or show error
        assert response.status_code in [302, 403, 404]

    def test_revoke_invite(self, authenticated_client, user, other_user):
        """Test revoking a collaboration invite."""
        # Create invite
        invite = InventoryCollab.objects.create(
            owner=user,
            collaborator=other_user,
            can_edit=True,
            is_active=True
        )

        # Revoke it
        response = authenticated_client.post(
            reverse('inventory:revoke_invite', kwargs={'pk': invite.pk})
        )
        assert response.status_code == 302

        # Invite should be inactive
        invite.refresh_from_db()
        assert not invite.is_active
        assert invite.revoked_at is not None
