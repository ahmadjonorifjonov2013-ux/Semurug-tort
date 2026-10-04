from decimal import Decimal

from django.core.management.base import BaseCommand

from cakes.models import Allergen, Cake, Category, Option


class Command(BaseCommand):
    help = "Katalog uchun namuna ma'lumot kiritadi"

    def handle(self, *args, **options):
        cats = {}
        for order, name in enumerate(["Tug'ilgan kun", "To'y torti",
                                      "Shirinliklar", "Maxsus tort"]):
            cat, _ = Category.objects.get_or_create(
                name=name, defaults={'order': order}
            )
            cats[name] = cat

        opts = [
            Option.objects.get_or_create(
                name=n, group=g, defaults={'price_delta': Decimal(p)}
            )[0]
            for n, g, p in [
                ('8 inch', "O'lcham", '0'),
                ('10 inch', "O'lcham", '150000'),
                ('12 inch', "O'lcham", '350000'),
                ('Vanilli krem', "Ta'm", '0'),
                ('Shokolad', "Ta'm", '20000'),
                ('Karamel', "Ta'm", '20000'),
                ('3 qavat', 'Dekor', '300000'),
            ]
        ]

        allergens = [
            Allergen.objects.get_or_create(name=a)[0]
            for a in ["Yong'oq", 'Tuxum', 'Sut', 'Gluten']
        ]

        cakes = [
            ("Tug'ilgan kun", "Tug'ilgan kun torti", '450000', 1000, 2),
            ("To'y torti", "To'y torti 3 qavat", '1200000', 1800, 5),
            ('Shirinliklar', 'Truffel quyoshlar', '380000', 400, 0),
            ('Maxsus tort', "Feruza to'y torti", '2500000', 2500, 7),
        ]

        for cat_name, name, price, weight, min_days in cakes:
            cake, created = Cake.objects.get_or_create(
                name=name,
                defaults={
                    'category': cats[cat_name],
                    'description': f"{name} — Semurg' TORT Markazining "
                                   "eng mashhur mahsuloti.",
                    'price': Decimal(price),
                    'weight_gram': weight,
                    'min_order_days': min_days,
                    'is_preorder': min_days > 0,
                },
            )
            if created:
                cake.options.set(opts[:3])
                cake.allergens.set(allergens[:2])

        self.stdout.write(self.style.SUCCESS("Namuna ma'lumot kiritildi"))
        self.stdout.write(f"  Kategoriyalar: {Category.objects.count()}")
        self.stdout.write(f"  Tortlar:        {Cake.objects.count()}")
        self.stdout.write(f"  Variantlar:     {Option.objects.count()}")
        self.stdout.write(f"  Allergenlar:    {Allergen.objects.count()}")