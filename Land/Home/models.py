from django.db import models
from django.contrib.auth.models import User, Group
from django.utils import timezone
from decimal import Decimal


# ---------------------------
#   ROLE HELPERS
# ---------------------------
def assign_group(user: User, group_name: str):
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


# ---------------------------
#   RESIDENT / CUSTOMER
# ---------------------------
class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customer")

    adhar_no = models.CharField(max_length=12, unique=True)
    phone_no = models.CharField(max_length=15, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)

    pan_number = models.CharField(max_length=10, unique=True, null=True, blank=True)

    address = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    pincode = models.CharField(max_length=6, null=True, blank=True)
    email = models.EmailField(max_length=254, unique=True, null=True, blank=True)

    office = models.ForeignKey(
        "Home.SubRegistrarOffice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # --- NEW: wallet address for blockchain transactions ---
    eth_address = models.CharField(
        max_length=42,
        null=True,
        blank=True,
        help_text="Resident's Ethereum wallet (0x...)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    @property
    def group(self):
        return "Resident"

    def get_office(self):
        return self.office


# ---------------------------
#   OFFICES & REGISTRARS
# ---------------------------
class SubRegistrarOffice(models.Model):
    name = models.CharField(max_length=255)
    district = models.CharField(max_length=64)
    locality = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.district}, {self.locality} - {self.name}"


class SubRegistrar(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subregistrar_profile")
    office = models.ForeignKey(SubRegistrarOffice, on_delete=models.CASCADE, related_name="registrars")

    contact_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    status = models.CharField(max_length=50, default="active")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sub Registrar"
        verbose_name_plural = "Sub Registrars"
        ordering = ["office_id", "user_id"]

    def __str__(self):
        return f"{self.user.username} - {self.office.district}, {self.office.locality}"


# ---------------------------
#   LAND + BLOCKCHAIN TRANSACTION
# ---------------------------
class Transaction(models.Model):

    DEED_TYPE_CHOICES = [
        ("sale", "Sale Deed"),
        ("will", "Will"),
        ("inheritance", "Inheritance / Succession"),
        ("gift", "Gift Deed"),
        ("mortgage", "Mortgage"),
        ("poa", "Power of Attorney"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("draft", "Draft"),
    ]

    # NEW — direction allows ETH flow clarity
    DIRECTION_CHOICES = [
        ("outbound", "Resident Sends ETH"),
        ("inbound", "Resident Receives ETH"),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    office = models.ForeignKey(
        SubRegistrarOffice,
        on_delete=models.CASCADE,
        related_name="transactions",
        null=True,
        blank=True,
    )

    deed_type = models.CharField(max_length=20, choices=DEED_TYPE_CHOICES)
    survey_number = models.CharField(max_length=100)
    location = models.CharField(max_length=255)

    valuation = models.DecimalField(max_digits=18, decimal_places=2)

    party_name = models.CharField(max_length=255)
    party_contact = models.CharField(max_length=15)
    party_id = models.CharField(max_length=100)

    submission_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    rejection_reason = models.TextField(blank=True, null=True)
    certificate_file = models.FileField(upload_to="certificates/", null=True, blank=True)

    documents = models.JSONField(default=list, blank=True)

    verified_by = models.ForeignKey(
        SubRegistrar,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_transactions",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    # -------- Blockchain Transfer Fields --------

    direction = models.CharField(
        max_length=10,
        choices=DIRECTION_CHOICES,
        default="outbound",
        help_text="Whether the resident is sending or receiving ETH",
    )

    # addresses actually used during transfer
    sender_address = models.CharField(max_length=42, null=True, blank=True)
    receiver_address = models.CharField(max_length=42, null=True, blank=True)

    # ETH value (optional — depends on policy)
    amount_eth = models.DecimalField(
        max_digits=30,
        decimal_places=18,
        default=Decimal("0"),
    )

    # blockchain result
    blockchain_hash = models.CharField(max_length=100, blank=True, null=True)
    blockchain_anchored_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submission_date"]
        db_table = "transactions"
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    def __str__(self):
        return f"Transaction #{self.id} - {self.deed_type} ({self.status})"
