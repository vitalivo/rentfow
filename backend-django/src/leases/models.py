    # leases/models.py
from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator

class Property(models.Model):
    address = models.CharField("Адрес", max_length=255)
    city = models.CharField("Город", max_length=100)
    country = models.CharField("Страна", max_length=100, default="Россия")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Объект недвижимости"
        verbose_name_plural = "Объекты недвижимости"

    def __str__(self):
        return self.address


class Tenant(models.Model):
    first_name = models.CharField("Имя", max_length=100)
    last_name = models.CharField("Фамилия", max_length=100)
    email = models.EmailField("Email", unique=True)
    phone = models.CharField("Телефон", max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Арендатор"
        verbose_name_plural = "Арендаторы"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Lease(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='leases',
        verbose_name="Объект"
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='leases',
        verbose_name="Арендатор"
    )
    start_date = models.DateField("Дата начала")
    end_date = models.DateField("Дата окончания")
    monthly_rent = models.DecimalField(
        "Ежемесячная арендная плата",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_day = models.PositiveSmallIntegerField(
        "День оплаты",
        help_text="Число месяца (1-31), когда арендатор должен платить"
    )
    notes = models.TextField("Примечания", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Договор аренды"
        verbose_name_plural = "Договоры аренды"

    def __str__(self):
        return f"{self.property} → {self.tenant}"