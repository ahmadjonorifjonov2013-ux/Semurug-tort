from decimal import Decimal

from django.urls import reverse
from django.test import TestCase

from testutils import ModelTestCase, ViewTestCase
from clients.models import Client
from core.models import SiteSettings

from .models import Order, OrderItem, PromoCode


class OrderTotalTests(ModelTestCase):
    """Jami summa to'g'ri hisoblanayotganini tekshirish."""

    def setUp(self):
        super().setUp()
        SiteSettings.objects.create(
            site_name='T', phone='+998901234567',
            address='Toshkent', delivery_price=20000,
        )
        self.client_obj = Client.objects.create(full_name='Ali',
                                                phone='+998901234567')
        self.cake = self.make_cake(name='Tort', price=Decimal('300000'),
                                   weight_gram=1000, min_order_days=0)
        self.order = Order.objects.create(
            client=self.client_obj, delivery_address='Toshkent',
            delivery_date='2030-01-01', total_price=0,
        )
        OrderItem.objects.create(order=self.order, cake=self.cake,
                                 quantity=2, price=Decimal('300000'))

    def test_total_is_correct(self):
        self.order.recalc_total()
        self.order.refresh_from_db()
        # 2 × 300 000 + 20 000 yetkazish
        self.assertEqual(self.order.total_price, Decimal('620000'))

    def test_item_subtotal(self):
        item = self.order.items.first()
        self.assertEqual(item.subtotal, Decimal('600000'))

    def test_free_delivery(self):
        SiteSettings.objects.update(free_delivery_from=500000)
        self.order.recalc_total()
        self.order.refresh_from_db()
        self.assertEqual(self.order.total_price, Decimal('600000'))

    def test_promo_discount(self):
        promo = PromoCode.objects.create(code='YANVAR10',
                                         discount_percent=10)
        self.order.promo_code = promo
        self.order.save()
        self.order.recalc_total()
        self.order.refresh_from_db()
        # 600 000 - 10% = 540 000, + 20 000 yetkazish
        self.assertEqual(self.order.discount, Decimal('60000.00'))
        self.assertEqual(self.order.total_price, Decimal('560000.00'))


class PromoCodeTests(TestCase):
    def test_is_valid_checks_min_sum(self):
        promo = PromoCode.objects.create(code='A', discount_percent=10,
                                         min_order_sum=100000)
        self.assertFalse(promo.is_valid(50000))
        self.assertTrue(promo.is_valid(150000))

    def test_is_valid_checks_active(self):
        promo = PromoCode.objects.create(code='B', discount_percent=10,
                                         is_active=False)
        self.assertFalse(promo.is_valid(1000))

    def test_discount_of(self):
        promo = PromoCode.objects.create(code='C', discount_percent=25)
        self.assertEqual(promo.discount_of(Decimal('1000')), Decimal('250.00'))


class OrderStatusTests(ModelTestCase):
    def setUp(self):
        super().setUp()
        self.client_obj = Client.objects.create(full_name='Ali',
                                                phone='+998901234567')
        self.order = Order.objects.create(
            client=self.client_obj, delivery_address='Toshkent',
            delivery_date='2030-01-01',
        )

    def test_default_status_is_new(self):
        self.assertEqual(self.order.status, Order.Status.NEW)

    def test_is_active(self):
        self.assertTrue(self.order.is_active)
        self.order.status = Order.Status.CANCELLED
        self.assertFalse(self.order.is_active)


class CartTests(ViewTestCase):
    def setUp(self):
        super().setUp()
        self.cake = self.make_cake(name='Tort', price=Decimal('450000'))

    def test_add_increases_quantity(self):
        self.client.post(reverse('orders:cart_add', args=[self.cake.pk]))
        self.client.post(reverse('orders:cart_add', args=[self.cake.pk]))
        self.assertEqual(self.client.session['cart'],
                         {str(self.cake.pk): {'qty': 2, 'options': [],
                                              'comment': ''}})

    def test_remove(self):
        self.client.post(reverse('orders:cart_add', args=[self.cake.pk]))
        self.client.post(reverse('orders:cart_remove', args=[self.cake.pk]))
        self.assertEqual(self.client.session['cart'], {})

    def test_clear(self):
        self.client.post(reverse('orders:cart_add', args=[self.cake.pk]))
        self.client.post(reverse('orders:cart_clear'))
        self.assertEqual(self.client.session['cart'], {})

    def test_cart_add_requires_post(self):
        response = self.client.get(
            reverse('orders:cart_add', args=[self.cake.pk])
        )
        self.assertEqual(response.status_code, 405)

    def test_cart_view_shows_total(self):
        self.client.post(reverse('orders:cart_add', args=[self.cake.pk]))
        response = self.client.get(reverse('orders:cart'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total'], Decimal('450000'))
        self.assertEqual(response.context['count'], 1)

    def test_checkout_redirects_when_cart_empty(self):
        response = self.client.get(reverse('orders:checkout'))
        self.assertRedirects(response, reverse('cakes:list'))


class CheckoutTests(ViewTestCase):
    def setUp(self):
        super().setUp()
        self.cake = self.make_cake(name='Tugilgan kun torti',
                                   price=Decimal('450000'))
        self.client.post(reverse('orders:cart_add', args=[self.cake.pk]),
                         {'quantity': 2})

    def test_anonymous_checkout_creates_client_and_order(self):
        response = self.client.post(reverse('orders:checkout'), {
            'phone': '+998 90 123 45 67',
            'name': 'Sardor',
            'delivery_address': "Toshkent, Amir Temur 15",
            'delivery_date': '2030-01-01',
            'delivery_time': '10:00',
            'payment_method': Order.PaymentMethod.CASH,
        })

        self.assertEqual(response.status_code, 302)
        client = Client.objects.get(phone='+998901234567')
        self.assertEqual(client.full_name, 'Sardor')

        order = Order.objects.get(client=client)
        self.assertEqual(order.items_count, 2)
        self.assertEqual(order.subtotal, Decimal('900000'))
        self.assertEqual(self.client.session['cart'], {})

    def test_promo_code_applied(self):
        PromoCode.objects.create(code='YANVAR10', discount_percent=10)
        self.client.post(reverse('orders:checkout'), {
            'phone': '+998901234567',
            'name': 'Sardor',
            'delivery_address': "Toshkent, Amir Temur 15",
            'delivery_date': '2030-01-01',
            'payment_method': Order.PaymentMethod.CASH,
            'promo_code': 'YANVAR10',
        })
        order = Order.objects.get()
        self.assertEqual(order.promo_code.code, 'YANVAR10')
        self.assertEqual(order.discount, Decimal('90000.00'))

    def test_past_date_rejected(self):
        response = self.client.post(reverse('orders:checkout'), {
            'phone': '+998901234567',
            'name': 'Sardor',
            'delivery_address': "Toshkent, Amir Temur 15",
            'delivery_date': '2020-01-01',
            'payment_method': Order.PaymentMethod.CASH,
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('delivery_date', response.context['form'].errors)
        self.assertEqual(Order.objects.count(), 0)


class RegisterAndOrderTests(ViewTestCase):
    """Mijoz ro'yxatdan o'tadi va tort buyurtma qiladi — butun yo'l."""

    def setUp(self):
        super().setUp()
        self.cake = self.make_cake(name='Feruza to\'y torti',
                                   price=Decimal('2500000'))

    def register(self):
        return self.client.post(reverse('clients:register'), {
            'username': 'alisher01',
            'full_name': 'Alisher Karimov',
            'phone': '+998 90 123 45 67',
            'email': 'alisher@example.uz',
            'telegram': '@alisher',
            'password1': 'YangiParol!2026',
            'password2': 'YangiParol!2026',
        })

    def test_register_logs_user_in(self):
        response = self.register()
        self.assertEqual(response.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertTrue(Client.objects.filter(phone='+998901234567').exists())

    def test_registered_user_can_order_cake(self):
        self.register()

        self.client.post(reverse('orders:cart_add', args=[self.cake.pk]),
                         {'quantity': 2})
        response = self.client.post(reverse('orders:checkout'), {
            'name': 'Alisher Karimov',
            'phone': '+998901234567',
            'telegram': '@alisher',
            'delivery_address': "Toshkent, Yunusobod tumani, Navoiy 15",
            'delivery_date': '2030-01-01',
            'delivery_time': '18:00',
            'payment_method': Order.PaymentMethod.CASH,
        })

        order = Order.objects.get()
        # Ro'yxatdan o'tgan mijoz — buyurtma sahifasiga olib boriladi.
        self.assertRedirects(response, reverse('orders:detail', args=[order.pk]))
        self.assertEqual(order.client.phone, '+998901234567')
        self.assertEqual(order.items_count, 2)
        self.assertEqual(order.subtotal, Decimal('5000000'))

    def test_order_appears_in_history(self):
        self.register()
        self.client.post(reverse('orders:cart_add', args=[self.cake.pk]),
                         {'quantity': 1})
        self.client.post(reverse('orders:checkout'), {
            'name': 'Alisher Karimov',
            'phone': '+998901234567',
            'delivery_address': "Toshkent, Yunusobod tumani, Navoiy 15",
            'delivery_date': '2030-01-01',
            'payment_method': Order.PaymentMethod.CASH,
        })

        for url in (reverse('orders:my'),
                    reverse('clients:profile_orders')):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['orders'].count(), 1)

    def test_guest_cart_is_kept_after_register(self):
        """Ro'yxatdan o'tishdan oldin solingan savat yo'qolmasin."""
        self.client.post(reverse('orders:cart_add', args=[self.cake.pk]),
                         {'quantity': 3})
        expected = {str(self.cake.pk): {'qty': 3, 'options': [], 'comment': ''}}
        self.assertEqual(self.client.session['cart'], expected)

        self.register()

        self.assertEqual(self.client.session['cart'], expected)