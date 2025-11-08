import json
import logging
import os
from django.core.management.base import BaseCommand
from kafka import KafkaConsumer
from leases.models import Tenant

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Запускает Kafka Consumer для обработки событий арендаторов"

    def handle(self, *args, **options):
        kafka_broker = os.environ.get("KAFKA_BROKER", "kafka:29092")
        kafka_topic = "tenant_events"

        consumer = KafkaConsumer(
            kafka_topic,
            bootstrap_servers=[kafka_broker],
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id="django-tenant-processor",
            value_deserializer=lambda x: json.loads(x.decode("utf-8"))
        )

        self.stdout.write(self.style.SUCCESS(f"TenantConsumer listening on {kafka_topic}..."))

        for message in consumer:
            self.process_message(message.value)

    def process_message(self, data):
        event_type = data.get("event_type")
        django_id = data.get("django_id")
        details = data.get("details", {})

        logger.info(f"Tenant Event: {event_type} | Django ID: {django_id}")

        try:
            tenant = Tenant.objects.get(id=django_id)
            if event_type == "TenantCreated":
                logger.info(f"Tenant {tenant.id} created: {tenant.first_name} {tenant.last_name}")
            elif event_type == "TenantUpdated":
                tenant.email = details.get("email", tenant.email)
                tenant.phone = details.get("phone", tenant.phone)
                tenant.save()
                logger.info(f"Tenant {tenant.id} updated")
            elif event_type == "TenantDeleted":
                tenant.delete()
                logger.info(f"Tenant {django_id} deleted")
        except Tenant.DoesNotExist:
            logger.error(f"Tenant with ID {django_id} not found")