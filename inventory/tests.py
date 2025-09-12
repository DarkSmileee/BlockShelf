from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from .models import InventoryItem

class InventoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='p')

    def test_login_required(self):
        resp = self.client.get(reverse('inventory:list'))
        self.assertEqual(resp.status_code, 302)  # redirect to login

    def test_create_item(self):
        self.client.login(username='u', password='p')
        resp = self.client.post(reverse('inventory:add'), {
            'name': '2x4 Brick',
            'part_id': '3001',
            'color': 'Red',
            'quantity_total': 10,
            'quantity_used': 2,
            'storage_location': 'Bin A1',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(InventoryItem.objects.filter(user=self.user).count(), 1)
