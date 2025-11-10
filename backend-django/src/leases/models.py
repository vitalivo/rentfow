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
    fastapi_id = models.CharField(
        "FastAPI ID отслеживания", 
        max_length=100, 
        unique=True, 
        null=True, 
        blank=True
    )
    status = models.CharField(
        "Статус аренды (Kafka)", 
        max_length=50, 
        default='INITIATED'
    )
    last_event_type = models.CharField(
        "Последнее событие Kafka", 
        max_length=50, 
        default='LEASE_CREATED'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Договор аренды"
        verbose_name_plural = "Договоры аренды"

    def __str__(self):
        return f"{self.property} → {self.tenant}"
    
class Payment(models.Model):
    django_id = models.BigIntegerField("ID Django", null=True, blank=True)
    event_type = models.CharField("Тип события", max_length=64)
    ts = models.DateTimeField("Время события")
    tenant_id = models.BigIntegerField("ID арендатора", null=True, blank=True)
    lease_id = models.BigIntegerField("ID договора", null=True, blank=True)
    amount = models.DecimalField(
        "Сумма платежа",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    currency = models.CharField("Валюта", max_length=8, null=True, blank=True)
    payload = models.JSONField("Полные данные события", null=True, blank=True)
    created_at = models.DateTimeField("Дата создания записи", auto_now_add=True)

    class Meta:
        managed = False   # таблица создана вручную
        db_table = "payments"
        unique_together = (('django_id', 'event_type'),)
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"

    def __str__(self):
        return f"{self.event_type} {self.amount} {self.currency}"

    