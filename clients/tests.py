from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from testutils import ViewTestCase

from .forms import clean_phone_value
from .models import Client


class PhoneValidatorTests(TestCase):
    def test_already_normalised(self):
        self.assertEqual(clean_phone_value('+998901234567'), '+998901234567')

    def test_with_spaces_and_plus(self):
        self.assertEqual(clean_phone_value('+998 90 123 45 67'),
                         '+998901234567')

    def test_nine_digits_gets_prefix(self):
        self.assertEqual(clean_phone_value('901234567'), '+998901234567')

    def test_invalid(self):
        with self.assertRaises(Exception):
            clean_phone_value('12345')


class RegistrationTests(ViewTestCase):
    def test_register_creates_user_and_client(self):
        response = self.client.post(reverse('clients:register'), {
            'username': 'sardor',
            'email': 'sardor@example.com',
            'full_name': 'Sardor Karimov',
            'phone': '+998 90 123 45 67',
            'telegram': '@sardor',
            'password1': 'YangiParol!2026',
            'password2': 'YangiParol!2026',
        })
        self.assertEqual(response.status_code, 302)

        user = User.objects.get(username='sardor')
        self.assertEqual(user.first_name, 'Sardor')

        client = Client.objects.get(user=user)
        self.assertEqual(client.full_name, 'Sardor Karimov')
        self.assertEqual(client.phone, '+998901234567')

        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_duplicate_phone_rejected(self):
        Client.objects.create(full_name='Ali', phone='+998901234567')
        response = self.client.post(reverse('clients:register'), {
            'username': 'ali2',
            'full_name': 'Ali',
            'phone': '+998901234567',
            'password1': 'YangiParol!2026',
            'password2': 'YangiParol!2026',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('phone', response.context['form'].errors)


class AuthTests(ViewTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ali',
                                             password='YangiParol!2026')
        Client.objects.create(user=self.user, full_name='Ali',
                              phone='+998901234567')

    def test_login(self):
        response = self.client.post(reverse('clients:login'), {
            'username': 'ali', 'password': 'YangiParol!2026',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']),
                         self.user.pk)

    def test_login_wrong_password(self):
        response = self.client.post(reverse('clients:login'), {
            'username': 'ali', 'password': 'xaroparol',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('clients:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_profile_requires_login(self):
        response = self.client.get(reverse('clients:profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/clients/login/', response.url)


class ProfileTests(ViewTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ali',
                                             password='YangiParol!2026')
        self.client_obj = Client.objects.create(user=self.user,
                                                full_name='Ali',
                                                phone='+998901234567')
        self.client.force_login(self.user)

    def test_profile_update(self):
        response = self.client.post(reverse('clients:profile'), {
            'full_name': 'Alisher',
            'phone': '+998 90 765 43 21',
            'telegram': '@alisher',
            'email': 'ali@example.com',
            'address': 'Toshkent',
        })
        self.assertEqual(response.status_code, 302)
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.full_name, 'Alisher')
        self.assertEqual(self.client_obj.phone, '+998907654321')


class ClientModelTests(TestCase):
    def test_str(self):
        client = Client.objects.create(full_name='Ali',
                                       phone='+998901234567')
        self.assertEqual(str(client), 'Ali (+998901234567)')

    def test_orders_count(self):
        client = Client.objects.create(full_name='Ali',
                                       phone='+998901234567')
        self.assertEqual(client.orders_count, 0)

    def test_telegram_username(self):
        client = Client.objects.create(full_name='Ali', phone='+998901234567',
                                       telegram='@ali_tort')
        self.assertEqual(client.telegram_username, 'ali_tort')