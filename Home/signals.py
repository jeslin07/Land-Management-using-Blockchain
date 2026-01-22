from pathlib import Path

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from .models import Transaction
from .services.fill_certificate import generate_certificate


@receiver(post_save, sender=Transaction)
def auto_generate_certificate(sender, instance: Transaction, created, **kwargs):
    """
    Automatically generate a certificate when a transaction is approved
    and does not already have one.
    """

    # only run when APPROVED and no certificate exists
    if instance.status != "approved":
        return

    if instance.certificate_file:
        return   # already generated — do nothing

    # ---- generate the PDF ----
    pdf_path = generate_certificate(instance)

    # convert OS path -> relative MEDIA path (portable)
    relative_path = Path(pdf_path).relative_to(settings.MEDIA_ROOT)

    # save ONLY the file field (avoid re-triggering signal logic)
    instance.certificate_file = str(relative_path)
    instance.save(update_fields=["certificate_file"])
