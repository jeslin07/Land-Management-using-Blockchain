from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from .models import Transaction
from .services.fill_certificate import generate_certificate


@receiver(post_save, sender=Transaction)
def auto_generate_certificate(sender, instance, created, **kwargs):
    """
    Automatically generate certificate once a transaction is approved.
    Runs only once.
    """

    # must be approved + no certificate yet
    if instance.status == "approved" and not instance.certificate_file:

        pdf_path = generate_certificate(instance)

        # store file path in DB (strip MEDIA_ROOT prefix)
        instance.certificate_file = pdf_path.replace(settings.MEDIA_ROOT + "/", "")
        instance.save(update_fields=["certificate_file"])
