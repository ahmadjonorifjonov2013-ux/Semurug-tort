from django.urls import reverse

from testutils import ModelTestCase, ViewTestCase
from clients.models import Client

from .models import Review


class ReviewModelTests(ModelTestCase):
    def setUp(self):
        super().setUp()
        self.cake = self.make_cake(name='Klassik tort')
        self.client_obj = Client.objects.create(full_name='Ali',
                                                phone='+998901234567')

    def test_default_not_published(self):
        review = Review.objects.create(cake=self.cake, author_name='Ali',
                                       rating=5, text='Juda mazali tort!')
        self.assertFalse(review.is_published)

    def test_short_text_rejected(self):
        from django.core.exceptions import ValidationError

        review = Review(cake=self.cake, author_name='Ali', rating=5, text='zo\'r')
        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_str(self):
        review = Review.objects.create(cake=self.cake, author_name='Ali',
                                       rating=4, text='Juda mazali tort!')
        self.assertEqual(str(review), 'Ali — 4 yulduz')


class AddReviewViewTests(ViewTestCase):
    def setUp(self):
        super().setUp()
        self.cake = self.make_cake(name='Klassik tort')

    def test_anonymous_can_add(self):
        response = self.client.post(
            reverse('reviews:add', args=[self.cake.slug]),
            {'rating': 5, 'text': 'Juda mazali tort, tavsiya qilaman!'},
        )
        self.assertEqual(response.status_code, 302)
        review = Review.objects.get()
        self.assertEqual(review.author_name, 'Mehmon')
        self.assertFalse(review.is_published)

    def test_authenticated_links_client(self):
        from django.contrib.auth.models import User

        user = User.objects.create_user(username='sardor',
                                        password='YangiParol!2026')
        client_obj = Client.objects.create(user=user, full_name='Sardor',
                                           phone='+998901234567')
        self.client.force_login(user)

        self.client.post(reverse('reviews:add', args=[self.cake.slug]), {
            'rating': 5, 'text': 'Juda mazali tort, tavsiya qilaman!',
        })

        review = Review.objects.get()
        self.assertEqual(review.client, client_obj)
        self.assertEqual(review.author_name, 'Sardor')

    def test_short_text_rejected(self):
        response = self.client.post(
            reverse('reviews:add', args=[self.cake.slug]),
            {'rating': 5, 'text': 'zo\'r'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Review.objects.count(), 0)

    def test_only_published_shown(self):
        hidden = Review.objects.create(cake=self.cake, author_name='Ali',
                                       rating=5,
                                       text='Yashirin sharh, ko\'rinmaydi',
                                       is_published=False)
        visible = Review.objects.create(cake=self.cake, author_name='Sardor',
                                        rating=4,
                                        text='Ko\'rinadigan sharh, yaxshi tort',
                                        is_published=True)

        response = self.client.get(reverse('reviews:list'))
        self.assertEqual(list(response.context['reviews']), [visible])
        self.assertNotIn(hidden, response.context['reviews'])

    def test_filter_by_cake(self):
        response = self.client.get(
            reverse('reviews:cake_list', args=[self.cake.slug])
        )
        self.assertEqual(response.context['cake'], self.cake)