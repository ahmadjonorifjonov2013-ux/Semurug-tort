from django.core.management.base import BaseCommand

from core.models import Banner, FAQ, SiteSettings


class Command(BaseCommand):
    help = "Sayt sozlamalari va kontent uchun namuna ma'lumot kiritadi"

    def handle(self, *args, **options):
        SiteSettings.objects.get_or_create(
            pk=1,
            defaults={
                'site_name': "Semurg' TORT Markazi",
                'phone': '+998 90 123 45 67',
                'telegram': '@semurog_tort',
                'instagram': 'https://instagram.com/semurog_tort',
                'address': "Toshkent sh., Amir Temur ko'chasi, 15",
                'work_hours': 'Har kuni 09:00 - 22:00',
                'delivery_price': 20000,
                'free_delivery_from': 800000,
                'about_text': (
                    "Biz 2015-yildan boshlab, har bir tortni mijoz "
                    "xohishiga qarab yakka tartibda tayyorlaymiz. "
                    "Tug'ilgan kun, to'y, yubiley — har qanday "
                    "voqeani nishonlash uchun."
                ),
            },
        )

        faqs = [
            ("Buyurtma qachon yetkaziladi?",
             "Toshkent ichida 24 soat ichida, viloyatga 48 soat ichida "
             "yetkazib beramiz."),
            ("Oldindan buyurtma kerakmi?",
             "Maxsus tortlar uchun kamida 3-7 kun oldin buyurtma berish "
             "tavsiya etiladi."),
            ("Yetkazib berish qancha turadi?",
             "Toshkent bo'ylab 20 000 so'm. 800 000 so'mdan katta "
             "buyurtmalar bepul yetkaziladi."),
            ("Maxsus dizayn mumkinmi?",
             "Ha. Rasmingiz yoki ilhom g'oyangizni yuboring — biz undan "
             "tort yasaymiz."),
        ]
        for order, (question, answer) in enumerate(faqs):
            FAQ.objects.get_or_create(
                question=question, defaults={'answer': answer, 'order': order}
            )

        if not Banner.objects.exists():
            self.stdout.write(self.style.WARNING(
                "Banner uchun rasm yuklang (admin → Banner), "
                "aks holda slayder bo'sh qoladi."
            ))

        self.stdout.write(self.style.SUCCESS("Sayt sozlamalari kiritildi"))
        self.stdout.write(f"  FAQ: {FAQ.objects.count()}")