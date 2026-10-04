"""API (DRF) testlari."""

from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework.test import APIClient

from testutils import ModelTestCase, image_file
from cakes.models import Cake, Category, Option
from clients.models import Client
from core.models import FAQ, SiteSettings
from orders.models import Order, OrderItem
from reviews.models import Review


class BaseAPITest(ModelTestCase):
    def setUp(self):
        super().setUp()
        self.api = APIClient()
        self.cake = self.make_cake(name='Klassik tort', description='Mazali',
                                   price=Decimal('450000'), weight_gram=1200)
        self.option = Option.objects.create(name='12 inch', group="O'lcham",
                                            price_delta=Decimal('350000'))


class CakeAPITests(BaseAPITest):
    def test_list(self):
        response = self.api.get('/api/cakes/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'Klassik tort')

    def test_retrieve_by_slug(self):
        response = self.api.get(f'/api/cakes/{self.cake.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['category']['name'], "Tug'ilgan kun")

    def test_filter_by_price(self):
        self.make_cake(name='Qimmat', description='a',
                       price=Decimal('5000000'), weight_gram=3000)
        response = self.api.get('/api/cakes/', {'price_max': 1000000})
        self.assertEqual(response.data['count'], 1)

    def test_create_requires_admin(self):
        response = self.api.post('/api/cakes/', {
            'category': self.category.pk, 'name': 'Yangi tort',
            'description': 'a', 'price': '100000',
        })
        self.assertIn(response.status_code, (401, 403))

    def _login_admin(self):
        User.objects.create_user(username='admin', password='YangiParol!2026',
                                 is_staff=True)
        self.api.login(username='admin', password='YangiParol!2026')

    def test_create_as_admin(self):
        self._login_admin()
        response = self.api.post('/api/cakes/', {
            'category': self.category.pk, 'name': 'Yangi tort',
            'description': 'a', 'price': '100000', 'weight_gram': 500,
            'main_image': image_file(),
        }, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Cake.objects.filter(name='Yangi tort').count(), 1)

    def test_old_price_cannot_be_lower(self):
        self._login_admin()
        response = self.api.post('/api/cakes/', {
            'category': self.category.pk, 'name': 'Xarato tort',
            'description': 'a', 'price': '900000',
            'old_price': '100000', 'weight_gram': 500,
            'main_image': image_file(),
        }, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertIn('old_price', response.data)


class CategoryAPITests(BaseAPITest):
    def test_list(self):
        response = self.api.get('/api/categories/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['cakes_count'], 1)


class CartAPITests(BaseAPITest):
    def test_add_to_cart(self):
        response = self.api.post('/api/cart/', {
            'cake': self.cake.pk, 'quantity': 2,
        })
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['total'], '900000.00')

    def test_options_change_price(self):
        self.api.post('/api/cart/', {
            'cake': self.cake.pk, 'quantity': 1,
            'options': [self.option.pk],
        })
        response = self.api.get('/api/cart/')
        self.assertEqual(response.data['total'], '800000.00')

    def test_get_empty_cart(self):
        response = self.api.get('/api/cart/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

    def test_patch_quantity(self):
        self.api.post('/api/cart/', {'cake': self.cake.pk, 'quantity': 2})
        response = self.api.patch(f'/api/cart/{self.cake.pk}/',
                                  {'quantity': 5}, format='json')
        self.assertEqual(response.data['count'], 5)

    def test_delete_item(self):
        self.api.post('/api/cart/', {'cake': self.cake.pk, 'quantity': 2})
        response = self.api.delete(f'/api/cart/{self.cake.pk}/')
        self.assertEqual(response.data['count'], 0)

    def test_checkout_empty_cart(self):
        response = self.api.post('/api/checkout/', {
            'phone': '+998901234567', 'name': 'Ali',
            'delivery_address': 'Toshkent, Amir Temur 15',
            'delivery_date': '2030-01-01',
        })
        self.assertEqual(response.status_code, 400)

    def test_checkout(self):
        self.api.post('/api/cart/', {'cake': self.cake.pk, 'quantity': 2})
        response = self.api.post('/api/checkout/', {
            'phone': '+998 90 123 45 67', 'name': 'Ali',
            'delivery_address': 'Toshkent, Amir Temur 15',
            'delivery_date': '2030-01-01',
            'payment_method': 'cash',
        })
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Order.objects.count(), 1)

        order = Order.objects.get()
        self.assertEqual(order.client.phone, '+998901234567')
        self.assertEqual(order.items_count, 2)
        self.assertEqual(self.api.get('/api/cart/').data['count'], 0)


class AuthAPITests(BaseAPITest):
    def test_register(self):
        response = self.api.post('/api/auth/register/', {
            'username': 'sardor', 'password': 'YangiParol!2026',
            'full_name': 'Sardor Karimov', 'phone': '+998901234567',
        })
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn('token', response.data)
        self.assertTrue(Client.objects.filter(phone='+998901234567').exists())

    def test_register_duplicate_username(self):
        User.objects.create_user(username='sardor', password='x')
        response = self.api.post('/api/auth/register/', {
            'username': 'sardor', 'password': 'YangiParol!2026',
            'full_name': 'Sardor', 'phone': '+998901234567',
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.data)

    def test_login(self):
        User.objects.create_user(username='ali', password='YangiParol!2026')
        response = self.api.post('/api/auth/login/', {
            'username': 'ali', 'password': 'YangiParol!2026',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data)

    def test_login_wrong(self):
        User.objects.create_user(username='ali', password='YangiParol!2026')
        response = self.api.post('/api/auth/login/', {
            'username': 'ali', 'password': 'nope',
        })
        self.assertEqual(response.status_code, 400)

    def test_clients_requires_auth(self):
        response = self.api.get('/api/clients/')
        self.assertIn(response.status_code, (401, 403))


class OrderAPITests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='ali',
                                             password='YangiParol!2026')
        self.client_obj = Client.objects.create(user=self.user,
                                                full_name='Ali',
                                                phone='+998901234567')
        self.order = Order.objects.create(
            client=self.client_obj, delivery_address='Toshkent',
            delivery_date='2030-01-01',
        )
        OrderItem.objects.create(order=self.order, cake=self.cake,
                                 quantity=1, price=Decimal('450000'))

    def test_my_orders(self):
        self.api.force_authenticate(self.user)
        response = self.api.get('/api/orders/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_other_users_order_hidden(self):
        other = User.objects.create_user(username='sardor',
                                         password='YangiParol!2026')
        self.api.force_authenticate(other)
        response = self.api.get('/api/orders/')
        self.assertEqual(response.data['count'], 0)

    def test_cancel(self):
        self.api.force_authenticate(self.user)
        response = self.api.post(f'/api/orders/{self.order.pk}/cancel/')
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)

    def test_cancel_delivered_rejected(self):
        self.order.status = Order.Status.DELIVERED
        self.order.save()
        self.api.force_authenticate(self.user)
        response = self.api.post(f'/api/orders/{self.order.pk}/cancel/')
        self.assertEqual(response.status_code, 400)


class ReviewAPITests(BaseAPITest):
    def test_create_is_unpublished(self):
        response = self.api.post('/api/reviews/', {
            'cake': self.cake.pk, 'rating': 5,
            'text': 'Juda mazali tort, tavsiya qilaman!',
        })
        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(Review.objects.get().is_published)

    def test_short_text_rejected(self):
        response = self.api.post('/api/reviews/', {
            'cake': self.cake.pk, 'rating': 5, 'text': 'zo\'r',
        })
        self.assertEqual(response.status_code, 400)

    def test_only_published_listed(self):
        Review.objects.create(cake=self.cake, author_name='A', rating=5,
                              text='Yashirin sharh matni', is_published=False)
        response = self.api.get('/api/reviews/')
        self.assertEqual(response.data['count'], 0)


class CoreAPITests(BaseAPITest):
    def test_site_settings(self):
        SiteSettings.objects.create(site_name='Semurog Tort',
                                    phone='+998901234567',
                                    address='Toshkent')
        response = self.api.get('/api/settings/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['site_name'], 'Semurog Tort')

    def test_faqs(self):
        FAQ.objects.create(question='Q?', answer='A.')
        response = self.api.get('/api/faqs/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)