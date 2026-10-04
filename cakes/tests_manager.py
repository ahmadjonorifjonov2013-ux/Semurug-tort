from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from testutils import ModelTestCase, image_file

from .models import Cake, Option


def _inline_forms(counts=None):
    """Admin sahifasidagi inline formalar uchun management form ma'lumotlari.

    `counts` — inline bo'yicha formalar soni (topshirilmasa — 1 ta bo'sh qator).
    """
    counts = counts or {}
    data = {}
    for prefix in ('images', 'Cake_options'):
        total = counts.get(prefix, 1)
        data[f'{prefix}-TOTAL_FORMS'] = str(total)
        data[f'{prefix}-INITIAL_FORMS'] = '0'
        data[f'{prefix}-MIN_NUM_FORMS'] = '0'
        data[f'{prefix}-MAX_NUM_FORMS'] = '1000'
    return data


class CakeManagerAccountTests(ModelTestCase):
    """`create_cake_manager` hisobining ruxsatlarini tekshiradi."""

    def setUp(self):
        super().setUp()
        call_command('create_cake_manager', 'gulnora',
                     password='Test123456!', stdout=StringIO())
        self.user = get_user_model().objects.get(username='gulnora')
        self.client.force_login(self.user)

    def test_is_staff_but_not_superuser(self):
        self.assertTrue(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_can_open_admin_index(self):
        self.assertEqual(self.client.get('/admin/').status_code, 200)

    def test_sees_only_cakes_section(self):
        response = self.client.get('/admin/')
        visible = {app['app_label'] for app in response.context['available_apps']}
        self.assertEqual(visible, {'cakes'})

    def test_cannot_open_other_apps_admin(self):
        # Boshqa ilovalar panelda umuman ko'rinmaydi (404) va
        # to'g'ridan-to'g'ri URL kirsa 403 beriladi.
        hidden = ['/admin/orders/', '/admin/reviews/', '/admin/clients/',
                  '/admin/core/']
        denied = ['/admin/orders/order/', '/admin/clients/client/',
                  '/admin/auth/user/', '/admin/auth/group/']
        for url in hidden:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
        for url in denied:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_cannot_delete_cake(self):
        cake = self.make_cake(name="O'chirib bo'lmaydigan tort")
        self.assertEqual(self.client.get(f'/admin/cakes/cake/{cake.pk}/delete/')
                         .status_code, 403)

    def test_can_add_cake(self):
        option = Option.objects.create(name='10 inch', group="O'lcham")
        data = {
            'category': self.category.pk,
            'name': 'Yangi tort',
            'slug': 'yangi-tort',
            'description': "Yangi qo'shilgan tort",
            'price': Decimal('500000'),
            'weight_gram': 1200,
            'min_order_days': 0,
            'main_image': image_file('yangi.png'),
            'options': [option.pk],
            'images-0-image': image_file('gallery.png'),
            'images-0-order': '0',
            'Cake_options-0-option': option.pk,
        }
        data.update(_inline_forms())
        response = self.client.post(reverse('admin:cakes_cake_add'), data)
        self.assertEqual(response.status_code, 302)
        cake = Cake.objects.get(name='Yangi tort')
        self.assertEqual(list(cake.options.all()), [option])

    def test_can_change_cake_price(self):
        cake = self.make_cake(name="Narxi o'zgaradigan tort",
                              price=Decimal('450000'))
        data = {
            'category': self.category.pk,
            'name': cake.name,
            'slug': cake.slug,
            'description': cake.description,
            'price': Decimal('555000'),
            'weight_gram': cake.weight_gram,
            'min_order_days': 0,
        }
        data.update(_inline_forms(counts={'images': 0, 'Cake_options': 0}))
        response = self.client.post(
            reverse('admin:cakes_cake_change', args=[cake.pk]), data
        )
        self.assertEqual(response.status_code, 302)
        cake.refresh_from_db()
        self.assertEqual(cake.price, Decimal('555000'))