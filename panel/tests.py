"""Boshqaruv paneli va saytga kirish talabi testlari."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from cakes.models import Cake, CakeImage, Category
from clients.models import Client
from core.models import ContactMessage
from orders.models import Order, OrderItem
from panel.decorators import SESSION_KEY
from reviews.models import Review
from testutils import (SiteLoginRequiredTestCase, ViewTestCase, image_file)

User = get_user_model()


# ---------------------------------------------------------------------------
# Panelga kirish
# ---------------------------------------------------------------------------

class PanelLoginTests(ViewTestCase):
    def setUp(self):
        super().setUp()
        self.password = 'YangiParol!2026'
        self.customer = User.objects.create_user(
            username='ali', password=self.password, is_staff=False,
        )
        self.staff = User.objects.create_user(
            username='rahim', password=self.password, is_staff=True,
        )

    def assertRedirectsToPanelLogin(self, response):
        """Panelga kirishga qaytarilishi kerak (`next` bilan)."""
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(
            f"{reverse('panel:login')}?next="), response['Location'])

    def test_customer_login_does_not_open_panel(self):
        """Mijoz logini bilan panelga kirib bo'lmasligi kerak."""
        self.client.force_login(self.customer)
        self.assertRedirectsToPanelLogin(
            self.client.get(reverse('panel:dashboard')))

    def test_staff_login_opens_panel(self):
        response = self.client.post(reverse('panel:login'), {
            'username': 'rahim',
            'password': self.password,
        })
        self.assertRedirects(response, reverse('panel:dashboard'))
        self.assertEqual(self.client.session[SESSION_KEY], self.staff.pk)

    def test_staff_password_wrong(self):
        response = self.client.post(reverse('panel:login'), {
            'username': 'rahim',
            'password': 'noto\'g\'ri',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_staff_site_login_opens_panel_without_second_login(self):
        """Sayt loginidan kirgan administrator panelga qayta kirmaydi."""
        response = self.client.post(reverse('clients:login'), {
            'username': 'rahim',
            'password': self.password,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('panel:dashboard'))
        self.assertEqual(self.client.session[SESSION_KEY], self.staff.pk)
        self.assertEqual(
            self.client.get(reverse('panel:dashboard')).status_code, 200)

    def test_authenticated_staff_is_not_asked_password_again(self):
        """`/boshqaruv/kirish/` allaqachon kirgan administratorni qayta so'ramaydi."""
        self.client.force_login(self.staff)
        response = self.client.get(reverse('panel:login'))
        self.assertRedirects(response, reverse('panel:dashboard'))
        self.assertEqual(self.client.session[SESSION_KEY], self.staff.pk)

    def test_customer_account_rejected(self):
        response = self.client.post(reverse('panel:login'), {
            'username': 'ali',
            'password': self.password,
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_logout_clears_panel_session(self):
        self.client.force_login(self.staff)
        session = self.client.session
        session[SESSION_KEY] = self.staff.pk
        session.save()

        self.client.get(reverse('panel:logout'))
        self.assertNotIn(SESSION_KEY, self.client.session)
        # Chiqish — sessiyadagi kirish ham tozalanadi (qayta avtomatik kirish bo'lmasin)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_panel_pages_require_panel_login(self):
        names = ('panel:orders', 'panel:cakes', 'panel:catalog', 'panel:content',
                 'panel:clients', 'panel:messages', 'panel:reviews',
                 'panel:settings')
        for name in names:
            with self.subTest(name=name):
                self.client.force_login(self.staff)   # panel belgisisiz
                self.assertRedirectsToPanelLogin(
                    self.client.get(reverse(name)))
                self.client.logout()


# ---------------------------------------------------------------------------
# Tort qo'shish va boshqarish
# ---------------------------------------------------------------------------

class PanelCakeTests(ViewTestCase):
    def setUp(self):
        super().setUp()
        self.admin = self.login_staff()

    def cake_data(self, **overrides):
        data = {
            'category': self.category.pk,
            'name': 'Snikers torti',
            'description': 'Yangi tort tavsifi',
            'price': '550000',
            'weight_gram': '1500',
            'is_active': 'on',
            'is_available': 'on',
        }
        data.update(overrides)
        return data

    def test_admin_adds_cake(self):
        response = self.client.post(
            reverse('panel:cake_create'),
            data=self.cake_data(main_image=image_file('snikers.png')),
        )
        cake = Cake.objects.get(name='Snikers torti')
        self.assertRedirects(response, reverse('panel:cake_edit',
                                               args=[cake.pk]))
        self.assertEqual(cake.slug, 'snikers-torti')
        self.assertTrue(cake.is_active)

    def test_added_cake_visible_on_site(self):
        self.client.post(
            reverse('panel:cake_create'),
            data=self.cake_data(main_image=image_file('snikers.png')),
        )
        response = self.client.get(reverse('cakes:list'))
        self.assertContains(response, 'Snikers torti')

    def test_gallery_images_uploaded(self):
        self.client.post(
            reverse('panel:cake_create'),
            data=self.cake_data(
                main_image=image_file('snikers.png'),
                gallery_images=[image_file('1.png'), image_file('2.png')],
            ),
        )
        cake = Cake.objects.get(name='Snikers torti')
        self.assertEqual(cake.images.count(), 2)

    def test_edit_cake(self):
        cake = self.make_cake(name='Edam torti', price=450000)
        response = self.client.post(reverse('panel:cake_edit', args=[cake.pk]),
                                    data=self.cake_data(name='Yangi nom'))
        self.assertRedirects(response, reverse('panel:cake_edit',
                                               args=[cake.pk]))
        cake.refresh_from_db()
        self.assertEqual(cake.name, 'Yangi nom')

    def test_archive_and_restore(self):
        cake = self.make_cake(name='Arxivlanadigan tort')

        self.client.post(reverse('panel:cake_flag', args=[cake.pk]),
                         {'action': 'archive'})
        cake.refresh_from_db()
        self.assertFalse(cake.is_active)

        self.client.post(reverse('panel:cake_flag', args=[cake.pk]),
                         {'action': 'restore'})
        cake.refresh_from_db()
        self.assertTrue(cake.is_active)

    def test_archived_cake_hidden_from_site(self):
        cake = self.make_cake(name='Yashirin tort')
        cake.is_active = False
        cake.save(update_fields=['is_active'])
        response = self.client.get(reverse('cakes:list'))
        self.assertNotContains(response, 'Yashirin tort')

    def test_cake_used_in_order_cannot_be_deleted(self):
        cake = self.make_cake(name='Buyurtmadagi tort')
        client = Client.objects.create(full_name='Sardor', phone='+998901112233')
        order = Order.objects.create(client=client, delivery_address='Toshkent',
                                     delivery_date=timezone.localdate())
        OrderItem.objects.create(order=order, cake=cake, quantity=1,
                                 price=cake.price)

        self.client.post(reverse('panel:cake_delete', args=[cake.pk]))
        self.assertTrue(Cake.objects.filter(pk=cake.pk).exists())

    def test_gallery_image_deleted(self):
        cake = self.make_cake(name='Galereyali tort')
        image = CakeImage.objects.create(cake=cake, image=image_file('g.png'))
        self.client.post(reverse('panel:gallery_image_delete',
                                  args=[image.pk]))
        self.assertEqual(cake.images.count(), 0)

    def test_customer_cannot_add_cake(self):
        self.client.logout()
        self.login_user('ali')
        response = self.client.post(
            reverse('panel:cake_create'),
            data=self.cake_data(main_image=image_file('snikers.png')),
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(
            reverse('panel:login')))
        self.assertEqual(Cake.objects.count(), 0)


# ---------------------------------------------------------------------------
# Buyurtmalarni rasmiylash
# ---------------------------------------------------------------------------

class PanelOrderTests(ViewTestCase):
    def setUp(self):
        super().setUp()
        self.admin = self.login_staff()
        self.client_profile = Client.objects.create(
            full_name='Sardor', phone='+998901112233')
        self.cake = self.make_cake(name="Tog' torti")
        self.order = Order.objects.create(
            client=self.client_profile,
            delivery_address='Toshkent, Amir Temur 12',
            delivery_date=timezone.localdate() + timezone.timedelta(days=1),
            total_price=450000,
        )
        OrderItem.objects.create(order=self.order, cake=self.cake, quantity=1,
                                 price=450000)

    def test_orders_list_contains_order(self):
        response = self.client.get(reverse('panel:orders'))
        self.assertContains(response, f"#{self.order.pk}")

    def test_order_detail_shows_client_phone(self):
        response = self.client.get(
            reverse('panel:order_detail', args=[self.order.pk]))
        self.assertContains(response, '+998901112233')

    def test_status_change(self):
        response = self.client.post(
            reverse('panel:order_detail', args=[self.order.pk]), {
                'status': Order.Status.IN_PROGRESS,
                'payment_method': Order.PaymentMethod.CASH,
                'delivery_address': 'Toshkent, Amir Temur 12',
                'delivery_date': str(self.order.delivery_date),
            })
        self.assertRedirects(response, reverse('panel:order_detail',
                                               args=[self.order.pk]))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.IN_PROGRESS)

    def test_paid_toggle(self):
        self.client.post(reverse('panel:order_action', args=[self.order.pk]),
                         {'action': 'paid'})
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_paid)

        self.client.post(reverse('panel:order_action', args=[self.order.pk]),
                         {'action': 'paid'})
        self.order.refresh_from_db()
        self.assertFalse(self.order.is_paid)

    def test_phone_confirmed_note_added(self):
        self.client.post(reverse('panel:order_action', args=[self.order.pk]),
                         {'action': 'confirm_phone'})
        self.order.refresh_from_db()
        self.assertIn('Telefon tasdiqlandi', self.order.comment)

    def test_other_customers_order_is_admin_only(self):
        """Mijoz boshqasining buyurtmasini panel orqali ko'ra olmaydi."""
        self.client.logout()
        self.login_user('ali')
        response = self.client.get(
            reverse('panel:order_detail', args=[self.order.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(
            reverse('panel:login')))


# ---------------------------------------------------------------------------
# Mijozlar, xabarlar, sharhlar, katalog, sozlamalar
# ---------------------------------------------------------------------------

class PanelContentTests(ViewTestCase):
    def setUp(self):
        super().setUp()
        self.admin = self.login_staff()

    def test_client_vip_toggle(self):
        client = Client.objects.create(full_name='Nodira', phone='+998901234567')
        self.client.post(reverse('panel:client_vip', args=[client.pk]))
        client.refresh_from_db()
        self.assertTrue(client.is_vip)

    def test_client_notes_saved(self):
        client = Client.objects.create(full_name='Nodira', phone='+998901234567')
        response = self.client.post(
            reverse('panel:client_detail', args=[client.pk]), {
                'full_name': 'Nodira A.',
                'phone': '+998901234567',
                'notes': 'Doimiy mijoz',
                'is_vip': 'on',
            })
        self.assertRedirects(response, reverse('panel:client_detail',
                                               args=[client.pk]))
        client.refresh_from_db()
        self.assertEqual(client.notes, 'Doimiy mijoz')
        self.assertTrue(client.is_vip)

    def test_message_marked_handled(self):
        msg = ContactMessage.objects.create(name='Botir', phone='+998901112233',
                                            message='Savol bor')
        self.client.post(reverse('panel:message_handle', args=[msg.pk]))
        msg.refresh_from_db()
        self.assertTrue(msg.is_handled)

    def test_review_published(self):
        review = Review.objects.create(author_name='Ali', rating=5,
                                       text='Juda zo\'r tort', is_published=False)
        self.client.post(reverse('panel:review_publish', args=[review.pk]))
        review.refresh_from_db()
        self.assertTrue(review.is_published)

    def test_category_created(self):
        self.client.post(reverse('panel:category_save'),
                         {'name': 'To\'y tortlari', 'is_active': 'on'})
        self.assertTrue(Category.objects.filter(name="To'y tortlari").exists())

    def test_panel_pages_render(self):
        """Barcha panel sahifalari haqiqiy shablon bilan chiziladi.

        Model property'si bilan bir xil nomli `annotate()` ishlatish
        `property ... has no setter` xatosini beradi — shu sabab ham
        bu test kerak.
        """
        client = Client.objects.create(full_name='Nodira', phone='+998901234567')
        ContactMessage.objects.create(name='Botir', phone='+998901112233',
                                      message='Savol bor')
        urls = [
            reverse('panel:dashboard'),
            reverse('panel:orders'),
            reverse('panel:cakes'),
            reverse('panel:cake_create'),
            reverse('panel:catalog'),
            reverse('panel:content'),
            reverse('panel:clients'),
            reverse('panel:client_detail', args=[client.pk]),
            reverse('panel:messages'),
            reverse('panel:reviews'),
            reverse('panel:settings'),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_promo_code_created(self):
        self.client.post(reverse('panel:promo_save'), {
            'code': 'yangi10',
            'discount_percent': '10',
            'min_order_sum': '100000',
            'is_active': 'on',
        })
        self.assertTrue(self._promo_exists('YANGI10'))

    @staticmethod
    def _promo_exists(code):
        from orders.models import PromoCode

        return PromoCode.objects.filter(code=code).exists()

    def test_site_settings_saved(self):
        from core.models import SiteSettings

        SiteSettings.objects.create(site_name='Semurg', phone='+998901234567',
                                    address='Toshkent')
        response = self.client.post(reverse('panel:settings'), {
            'site_name': 'Semurg\' TORT Markazi',
            'phone': '+998901234567',
            'address': 'Toshkent, Amir Temur 12',
            'work_hours': 'Har kuni 09:00 - 22:00',
            'delivery_price': '50000',
            'about_text': 'Biz haqimizda',
        })
        self.assertRedirects(response, reverse('panel:settings'))
        self.assertEqual(SiteSettings.objects.get().delivery_price, 50000)


# ---------------------------------------------------------------------------
# Butun sayt faqat kiritilganlarga ochiq
# ---------------------------------------------------------------------------

class SiteLoginRequiredTests(SiteLoginRequiredTestCase):
    """`SITE_REQUIRE_LOGIN` yoqilganda sayt yopiq bo'lishi kerak."""

    def test_home_redirects_to_login(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('clients:login'), response['Location'])
        self.assertIn('next=', response['Location'])

    def test_public_pages_redirect(self):
        for name in ('cakes:list', 'core:contact', 'core:faq', 'orders:cart',
                     'clients:profile', 'orders:my', 'reviews:list'):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)

    def test_login_and_register_open(self):
        self.assertEqual(self.client.get(reverse('clients:login')).status_code,
                         200)
        self.assertEqual(self.client.get(reverse('clients:register')).status_code,
                         200)

    def test_panel_login_page_open(self):
        self.assertEqual(self.client.get(reverse('panel:login')).status_code,
                         200)

    def test_django_admin_login_open(self):
        response = self.client.get('/admin/login/')
        self.assertEqual(response.status_code, 200)

    def test_authenticated_user_can_see_site(self):
        user = User.objects.create_user(username='ali',
                                        password='YangiParol!2026')
        self.client.force_login(user)
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)

    def test_api_login_and_register_open(self):
        self.assertEqual(self.client.post('/api/auth/login/').status_code,
                         400)
        self.assertEqual(self.client.post('/api/auth/register/').status_code,
                         400)

    def test_api_cart_and_checkout_need_login(self):
        """API'da buyurtma qilish ham autentifikatsiyasiz mumkin emas."""
        response = self.client.get('/api/cart/')
        self.assertEqual(response.status_code, 401)
        response = self.client.post('/api/checkout/', data={},
                                    content_type='application/json')
        self.assertEqual(response.status_code, 401)
        response = self.client.get('/api/orders/')
        self.assertEqual(response.status_code, 401)

    def test_api_token_header_allowed(self):
        from rest_framework.authtoken.models import Token

        user = User.objects.create_user(username='ali',
                                        password='YangiParol!2026')
        token = Token.objects.create(user=user)
        response = self.client.get('/api/orders/',
                                   HTTP_AUTHORIZATION=f'Token {token.key}')
        self.assertEqual(response.status_code, 200)

    def test_api_authenticated_user_allowed(self):
        user = User.objects.create_user(username='ali',
                                        password='YangiParol!2026')
        self.client.force_login(user)
        self.assertEqual(self.client.get('/api/cakes/').status_code, 200)


# ---------------------------------------------------------------------------
# Ro'yxatdan o'tish -> saytga kirish -> buyurtma
# ---------------------------------------------------------------------------

class RegisterThenOrderTests(SiteLoginRequiredTestCase):
    """Foydalanuvchi ro'yxatdan o'tadi, kiritadi va buyurtma beradi."""

    def setUp(self):
        super().setUp()
        self.cake = self.make_cake(name='Krem tort')

    def test_register_login_then_order(self):
        # 1. Ro'yxatdan o'tish
        response = self.client.post(reverse('clients:register'), {
            'username': 'nodira',
            'password1': 'YangiParol!2026!',
            'password2': 'YangiParol!2026!',
            'full_name': 'Nodira Aliyeva',
            'phone': '+998901234567',
        })
        self.assertEqual(response.status_code, 302)

        # 2. Sayt endi ochiq
        self.assertEqual(self.client.get(reverse('core:home')).status_code, 200)

        # 3. Buyurtma berish
        self.client.post(reverse('orders:cart_add', args=[self.cake.pk]),
                         {'quantity': '1'})
        response = self.client.post(reverse('orders:checkout'), {
            'name': 'Nodira Aliyeva',
            'phone': '+998901234567',
            'delivery_address': 'Toshkent, Amir Temur 12',
            'delivery_date': str(timezone.localdate()),
            'payment_method': Order.PaymentMethod.CASH,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.first().client.full_name,
                         'Nodira Aliyeva')