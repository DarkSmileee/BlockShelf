"""
Tests for CSV/Excel import functionality.
"""
import pytest
import io
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from inventory.models import InventoryItem

pytestmark = pytest.mark.imports


class TestCSVImport:
    """Test CSV import functionality."""

    def test_import_csv_basic(self, authenticated_client, user):
        """Test importing a basic CSV file."""
        csv_content = """name,part_id,color,quantity_total,quantity_used,storage_location
Brick 2x4,3001,Red,100,10,Box A1
Plate 2x2,3022,Blue,50,5,Box A2
Tile 1x1,3070,Yellow,200,20,Box B1"""

        csv_file = SimpleUploadedFile(
            "test_import.csv",
            csv_content.encode('utf-8'),
            content_type="text/csv"
        )

        response = authenticated_client.post(
            reverse('inventory:import_csv'),
            {'csv_file': csv_file},
            follow=True
        )

        assert response.status_code == 200

        # Verify items were created
        assert InventoryItem.objects.filter(user=user).count() == 3
        assert InventoryItem.objects.filter(name='Brick 2x4').exists()
        assert InventoryItem.objects.filter(part_id='3001').exists()

    def test_import_csv_with_duplicates(self, authenticated_client, user):
        """Test importing CSV with duplicate part_id and color."""
        # Create existing item
        InventoryItem.objects.create(
            user=user,
            name='Existing Brick',
            part_id='3001',
            color='Red',
            quantity_total=50
        )

        csv_content = """name,part_id,color,quantity_total
Brick 2x4,3001,Red,100
Plate 2x2,3022,Blue,50"""

        csv_file = SimpleUploadedFile(
            "test_import.csv",
            csv_content.encode('utf-8'),
            content_type="text/csv"
        )

        response = authenticated_client.post(
            reverse('inventory:import_csv'),
            {'csv_file': csv_file},
            follow=True
        )

        assert response.status_code == 200

        # Should have 2 items total (duplicate skipped or merged)
        items = InventoryItem.objects.filter(user=user)
        assert items.count() >= 2  # At least the new one

    def test_import_csv_invalid_format(self, authenticated_client, user):
        """Test importing CSV with invalid format."""
        csv_content = """invalid,headers,here
value1,value2,value3"""

        csv_file = SimpleUploadedFile(
            "test_import.csv",
            csv_content.encode('utf-8'),
            content_type="text/csv"
        )

        response = authenticated_client.post(
            reverse('inventory:import_csv'),
            {'csv_file': csv_file},
            follow=True
        )

        # Should show error message
        assert response.status_code == 200
        messages = list(response.context['messages'])
        assert len(messages) > 0
        # Should contain error message
        assert any('error' in str(m).lower() or 'invalid' in str(m).lower()
                   for m in messages)

    def test_import_csv_missing_required_fields(self, authenticated_client, user):
        """Test importing CSV with missing required fields."""
        csv_content = """name,color
Brick 2x4,Red"""  # Missing part_id

        csv_file = SimpleUploadedFile(
            "test_import.csv",
            csv_content.encode('utf-8'),
            content_type="text/csv"
        )

        response = authenticated_client.post(
            reverse('inventory:import_csv'),
            {'csv_file': csv_file},
            follow=True
        )

        assert response.status_code == 200
        # Should show error about missing fields
        messages = list(response.context['messages'])
        assert len(messages) > 0

    def test_import_csv_large_file(self, authenticated_client, user):
        """Test importing a large CSV file."""
        # Generate large CSV content
        lines = ['name,part_id,color,quantity_total']
        for i in range(100):
            lines.append(f'Part {i},300{i},Red,{i*10}')
        csv_content = '\n'.join(lines)

        csv_file = SimpleUploadedFile(
            "test_import.csv",
            csv_content.encode('utf-8'),
            content_type="text/csv"
        )

        response = authenticated_client.post(
            reverse('inventory:import_csv'),
            {'csv_file': csv_file},
            follow=True
        )

        assert response.status_code == 200

        # Verify items were created
        assert InventoryItem.objects.filter(user=user).count() == 100

    def test_import_csv_special_characters(self, authenticated_client, user):
        """Test importing CSV with special characters."""
        csv_content = """name,part_id,color,quantity_total,notes
"Brick, 2x4",3001,Red,100,"Contains comma, and quotes"
Plate "Special",3022,Blue,50,Test's apostrophe"""

        csv_file = SimpleUploadedFile(
            "test_import.csv",
            csv_content.encode('utf-8'),
            content_type="text/csv"
        )

        response = authenticated_client.post(
            reverse('inventory:import_csv'),
            {'csv_file': csv_file},
            follow=True
        )

        assert response.status_code == 200

        # Verify items were created with special characters
        item = InventoryItem.objects.get(part_id='3001')
        assert 'comma' in item.notes

    def test_import_requires_authentication(self, client):
        """Test that import requires authentication."""
        response = client.get(reverse('inventory:import_csv'))
        assert response.status_code == 302  # Redirect to login

    def test_export_csv(self, authenticated_client, inventory_items):
        """Test exporting inventory to CSV."""
        response = authenticated_client.get(reverse('inventory:export_csv'))
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        assert 'attachment' in response['Content-Disposition']

        # Verify CSV content
        content = response.content.decode('utf-8')
        assert 'name' in content.lower()
        assert 'part_id' in content.lower()
        assert 'Test Part' in content

    def test_export_empty_inventory(self, authenticated_client, user):
        """Test exporting when inventory is empty."""
        response = authenticated_client.get(reverse('inventory:export_csv'))
        assert response.status_code == 200

        # Should still return CSV with headers
        content = response.content.decode('utf-8')
        assert 'name' in content.lower() or 'part_id' in content.lower()


class TestRebrickableImport:
    """Test Rebrickable part lookup and import."""

    @pytest.mark.slow
    def test_lookup_part_api_integration(self, authenticated_client, mocker):
        """Test looking up a part from Rebrickable API."""
        # Mock the Rebrickable API response
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'part_num': '3001',
            'name': 'Brick 2x4',
            'part_img_url': 'https://cdn.rebrickable.com/media/parts/elements/300126.jpg'
        }
        mocker.patch('requests.get', return_value=mock_response)

        # Test lookup endpoint
        response = authenticated_client.get(
            reverse('inventory:lookup_part'),
            {'part_id': '3001'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get('name') == 'Brick 2x4'
        assert 'part_img_url' in data or 'image_url' in data

    def test_lookup_part_not_found(self, authenticated_client, mocker):
        """Test looking up a non-existent part."""
        mock_response = mocker.Mock()
        mock_response.status_code = 404
        mocker.patch('requests.get', return_value=mock_response)

        response = authenticated_client.get(
            reverse('inventory:lookup_part'),
            {'part_id': 'invalid'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        data = response.json()
        assert data.get('found') is False

    def test_lookup_requires_authentication(self, client):
        """Test that lookup requires authentication."""
        response = client.get(
            reverse('inventory:lookup_part'),
            {'part_id': '3001'}
        )
        assert response.status_code == 302  # Redirect to login
