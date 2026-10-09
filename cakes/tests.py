from decimal import Decimal

from django.test import RequestFactory
from django.urls import reverse

from testutils import ModelTestCase

from .models import Category, Option
from .views import _filter_cakes


class CakeModelTests(ModelTestCase):
    def setUp(self):
        super().setUp()
        self.cake = self.make_cake(name='Klassik tort',
                                   price=Decimal('450000'),
                                   weight_gram=1200)

    def test_slug_generated_from_name(self):
        self.assertEqual(self.cake.slug, 'klassik-tort')

    def test_slug_not_overwritten(self):
        self.cake.slug = 'my-own-slug'
        self.cake.save()
        self.assertEqual(self.cake.slug, 'my-own-slug')

    def test_has_discount(self):
        self.assertFalse(self.cake.has_discount)
        self.cake.old_price = Decimal('600000')
        self.cake.save()
        self.assertTrue(self.cake.has_discount)
        self.assertEqual(self.cake.discount_percent, 25)

    def test_get_absolute_url(self):
        self.assertEqual(
            self.cake.get_absolute_url(),
            reverse('cakes:detail', args=[self.cake.slug]),
        )

    def test_price_with_options(self):
        option = Option.objects.create(name='12 inch', group="O'lcham",
                                       price_delta=Decimal('350000'))
        self.assertEqual(self.cake.price_with([option.pk]),
                         Decimal('800000'))


class CakeFilterTests(ModelTestCase):
    """Katalog filtrlari — _filter_cakes() mantiqi."""

    def setUp(self):
        super().setUp()
        self.cat1 = self.category
        self.cat2 = Category.objects.create(name="To'y torti")
        self.cheap = self.make_cake(name='Arzon tort', description='a',
                                    price=Decimal('200000'), weight_gram=500)
        self.expensive = self.make_cake(name='Qimmat tort', description='b',
                                        category=self.cat2,
                                        price=Decimal('2000000'),
                                        weight_gram=2000)
        self.hidden = self.make_cake(name='Yashirin tort', description='c',
                                     price=Decimal('100000'),
                                     weight_gram=300, is_active=False)

    def filter(self, **params):
        request = RequestFactory().get('/', params)
        return list(_filter_cakes(request))

    def test_inactive_cakes_hidden(self):
        self.assertNotIn(self.hidden, self.filter())

    def test_filter_by_category(self):
        names = [c.name for c in self.filter(category=self.cat2.slug)]
        self.assertEqual(names, ['Qimmat tort'])

    def test_filter_by_price(self):
        names = [c.name for c in self.filter(price_max=500000)]
        self.assertEqual(names, ['Arzon tort'])

    def test_filter_by_price_min(self):
        names = [c.name for c in self.filter(price_min=1000000)]
        self.assertEqual(names, ['Qimmat tort'])

    def test_search(self):
        names = [c.name for c in self.filter(search='qimmat')]
        self.assertEqual(names, ['Qimmat tort'])

    def test_sort_by_price_desc(self):
        names = [c.name for c in self.filter(sort='price_desc')]
        self.assertEqual(names[0], 'Qimmat tort')

    def test_sort_by_price_asc(self):
        names = [c.name for c in self.filter(sort='price_asc')]
        self.assertEqual(names[0], 'Arzon tort')

    def test_only_available(self):
        self.cheap.is_available = False
        self.cheap.save()
        self.assertNotIn(self.cheap, self.filter(available='1'))

    def test_only_preorder(self):
        self.cheap.is_preorder = True
        self.cheap.save()
        self.assertIn(self.cheap, self.filter(preorder='1'))
        self.assertNotIn(self.expensive, self.filter(preorder='1'))


class CakeDetailViewTests(ModelTestCase):
    def setUp(self):
        super().setUp()
        self.cake = self.make_cake(name='Klassik tort',
                                   price=Decimal('450000'),
                                   weight_gram=1200, min_order_days=3)

    def test_404_for_missing(self):
        response = self.client.get(reverse('cakes:detail', args=['yoq-yoq']))
        self.assertEqual(response.status_code, 404)

    def test_404_for_inactive(self):
        self.cake.is_active = False
        self.cake.save()
        response = self.client.get(
            reverse('cakes:detail', args=[self.cake.slug])
        )
        self.assertEqual(response.status_code, 404)