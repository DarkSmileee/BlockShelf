"""
Tests for data integrity and validation constraints.
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta
from inventory.models import InventoryItem, InventoryShare, InventoryCollab


class TestQuantityValidation:
    """Test quantity validation constraints."""

    def test_quantity_used_cannot_exceed_total(self, user):
        """Test that quantity_used cannot be greater than quantity_total."""
        with pytest.raises(ValidationError) as exc_info:
            item = InventoryItem(
                user=user,
                name='Test Brick',
                part_id='3001',
                color='Red',
                quantity_total=10,
                quantity_used=15  # Invalid: exceeds total
            )
            item.save()

        assert 'quantity_used' in exc_info.value.message_dict
        assert 'cannot exceed' in str(exc_info.value)

    def test_valid_quantities(self, user):
        """Test that valid quantities are accepted."""
        item = InventoryItem.objects.create(
            user=user,
            name='Test Brick',
            part_id='3001',
            color='Red',
            quantity_total=10,
            quantity_used=5  # Valid: less than total
        )
        assert item.quantity_used == 5
        assert item.quantity_total == 10

    def test_quantity_used_equals_total(self, user):
        """Test that quantity_used can equal quantity_total."""
        item = InventoryItem.objects.create(
            user=user,
            name='Test Brick',
            part_id='3001',
            color='Red',
            quantity_total=10,
            quantity_used=10  # Valid: equals total
        )
        assert item.quantity_used == 10
        assert item.quantity_total == 10

    def test_negative_quantities_rejected(self, user):
        """Test that negative quantities are rejected."""
        with pytest.raises(ValidationError):
            item = InventoryItem(
                user=user,
                name='Test Brick',
                part_id='3001',
                color='Red',
                quantity_total=-5,  # Invalid: negative
                quantity_used=0
            )
            item.save()

        with pytest.raises(ValidationError):
            item = InventoryItem(
                user=user,
                name='Test Brick',
                part_id='3002',
                color='Red',
                quantity_total=10,
                quantity_used=-2  # Invalid: negative
            )
            item.save()

    def test_update_quantity_validation(self, inventory_item):
        """Test validation when updating quantities."""
        # Try to set quantity_used > quantity_total
        inventory_item.quantity_used = inventory_item.quantity_total + 10

        with pytest.raises(ValidationError):
            inventory_item.save()

    def test_quantity_available_property(self, user):
        """Test quantity_available calculated property."""
        item = InventoryItem.objects.create(
            user=user,
            name='Test Brick',
            part_id='3001',
            color='Red',
            quantity_total=100,
            quantity_used=30
        )
        assert item.quantity_available == 70


class TestDuplicatePrevention:
    """Test duplicate prevention constraints."""

    def test_duplicate_user_part_color_rejected(self, user):
        """Test that duplicate (user, part_id, color) is rejected."""
        # Create first item
        InventoryItem.objects.create(
            user=user,
            name='Original Item',
            part_id='3001',
            color='Red',
            quantity_total=10
        )

        # Try to create duplicate
        with pytest.raises(IntegrityError) as exc_info:
            InventoryItem.objects.create(
                user=user,
                name='Duplicate Item',
                part_id='3001',  # Same part_id
                color='Red',     # Same color
                quantity_total=20
            )

        assert 'unique_user_part_color' in str(exc_info.value)

    def test_same_part_different_color_allowed(self, user):
        """Test that same part_id with different color is allowed."""
        item1 = InventoryItem.objects.create(
            user=user,
            name='Red Brick',
            part_id='3001',
            color='Red',
            quantity_total=10
        )

        item2 = InventoryItem.objects.create(
            user=user,
            name='Blue Brick',
            part_id='3001',  # Same part_id
            color='Blue',    # Different color
            quantity_total=20
        )

        assert item1.id != item2.id
        assert InventoryItem.objects.filter(user=user).count() == 2

    def test_same_part_different_user_allowed(self, user, other_user):
        """Test that same part_id and color for different users is allowed."""
        item1 = InventoryItem.objects.create(
            user=user,
            name='User 1 Brick',
            part_id='3001',
            color='Red',
            quantity_total=10
        )

        item2 = InventoryItem.objects.create(
            user=other_user,  # Different user
            name='User 2 Brick',
            part_id='3001',   # Same part_id
            color='Red',      # Same color
            quantity_total=20
        )

        assert item1.id != item2.id
        assert InventoryItem.objects.count() == 2


class TestDataRetention:
    """Test data retention and revocation tracking."""

    def test_share_revocation_tracked(self, user):
        """Test that share revocation is properly tracked."""
        share = InventoryShare.objects.create(
            user=user,
            token='test-token-123'
        )

        # Revoke the share
        share.revoke()

        # Verify tracking
        share.refresh_from_db()
        assert share.is_active is False
        assert share.revoked_at is not None
        assert share.revoked_at <= timezone.now()

    def test_collab_revocation_tracked(self, user, other_user):
        """Test that collaboration revocation is properly tracked."""
        collab = InventoryCollab.objects.create(
            owner=user,
            collaborator=other_user,
            can_edit=True
        )

        # Revoke the collaboration
        collab.revoke()

        # Verify tracking
        collab.refresh_from_db()
        assert collab.is_active is False
        assert collab.revoked_at is not None
        assert collab.revoked_at <= timezone.now()

    def test_old_revoked_shares_can_be_purged(self, user):
        """Test that old revoked shares can be identified for purging."""
        # Create old revoked share
        old_share = InventoryShare.objects.create(
            user=user,
            token='old-token'
        )
        old_share.revoke()

        # Manually set old revoked_at date (simulate old record)
        InventoryShare.objects.filter(id=old_share.id).update(
            revoked_at=timezone.now() - timedelta(days=100)
        )

        # Create recent revoked share
        recent_share = InventoryShare.objects.create(
            user=user,
            token='recent-token'
        )
        recent_share.revoke()

        # Query old revoked shares (>90 days)
        cutoff = timezone.now() - timedelta(days=90)
        old_shares = InventoryShare.objects.filter(
            is_active=False,
            revoked_at__isnull=False,
            revoked_at__lt=cutoff
        )

        assert old_shares.count() == 1
        assert old_shares.first().id == old_share.id

    def test_old_revoked_collabs_can_be_purged(self, user, other_user):
        """Test that old revoked collaborations can be identified for purging."""
        # Create old revoked collaboration
        old_collab = InventoryCollab.objects.create(
            owner=user,
            collaborator=other_user,
            can_edit=True
        )
        old_collab.revoke()

        # Manually set old revoked_at date
        InventoryCollab.objects.filter(id=old_collab.id).update(
            revoked_at=timezone.now() - timedelta(days=200)
        )

        # Create recent revoked collaboration
        recent_collab = InventoryCollab.objects.create(
            owner=user,
            collaborator=other_user,
            can_edit=False
        )
        recent_collab.revoke()

        # Query old revoked collaborations (>90 days)
        cutoff = timezone.now() - timedelta(days=90)
        old_collabs = InventoryCollab.objects.filter(
            is_active=False,
            revoked_at__isnull=False,
            revoked_at__lt=cutoff
        )

        assert old_collabs.count() == 1
        assert old_collabs.first().id == old_collab.id
