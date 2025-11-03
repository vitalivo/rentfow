import json
import logging
import os
import time
from datetime import datetime # Ошибка исправлена: импорт datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from leases.models import Lease, Property, Tenant # Включая все модели
from kafka import KafkaConsumer
from kafka.errors import KafkaError

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Command(BaseCommand):
    help = 'Запускает Kafka Consumer для обработки событий аренды'

    def handle(self, *args, **options):
        # Получаем параметры подключения из переменных окружения
        kafka_broker = os.environ.get('KAFKA_BROKER', 'kafka:29092')
        kafka_topic = os.environ.get('KAFKA_TOPIC', 'lease_events')
        group_id = 'django-lease-processor' # Уникальный ID группы консьюмеров

        self.stdout.write(self.style.SUCCESS(f'Starting Kafka Consumer for topic: {kafka_topic}...'))

        try:
            consumer = KafkaConsumer(
                kafka_topic,
                bootstrap_servers=[kafka_broker],
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id=group_id,
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            self.stdout.write(self.style.SUCCESS(
                f'Kafka Consumer успешно подключен к {kafka_broker}. Партиций: {len(consumer.partitions_for_topic(kafka_topic) or [])}'
            ))
            logger.info("Запуск основного цикла чтения сообщений...")

        except KafkaError as e:
            self.stderr.write(self.style.ERROR(f"Ошибка подключения к Kafka: {e}"))
            return

        # Основной цикл обработки сообщений
        for message in consumer:
            self.process_message(message)

    def process_message(self, message):
        """Обрабатывает одно сообщение из Kafka."""
        try:
            data = message.value
            event_type = data.get('event_type')
            django_id = data.get('django_id')
            fastapi_id = data.get('fastapi_id')
            details = data.get('details', {})
            
            print(f"!!! KAFKA SUCCESS CHECK !!! Offset: {message.offset} | Event: {event_type} | Django ID: {django_id}")

            if not django_id:
                logger.error("Сообщение проигнорировано: отсутствует поле 'django_id'.")
                return

            logger.info(f"Найдено событие '{event_type}' для Django ID: {django_id}")

            with transaction.atomic():
                # Получаем существующую запись аренды
                lease_instance = Lease.objects.select_for_update().get(id=django_id)

                # --- МАРШРУТИЗАЦИЯ СОБЫТИЙ ---
                if event_type == 'LeaseCreated':
                    self._handle_lease_created(lease_instance, fastapi_id, details)
                
                elif event_type == 'LeaseUpdated':
                    self._handle_lease_updated(lease_instance, fastapi_id, details)
                
                elif event_type == 'LeaseTerminated':
                    self._handle_lease_terminated(lease_instance, fastapi_id, details)
                
                else:
                    logger.warning(f"Неизвестный тип события: {event_type}. Пропуск.")

            # Успешный коммит
            self.stdout.write(self.style.SUCCESS(f"Lease {django_id}: успешно обработано событие {event_type}."))

        except ObjectDoesNotExist:
            logger.error(f"Ошибка: запись Lease с ID {django_id} не найдена в Django DB.")
        except json.JSONDecodeError:
            logger.error("Ошибка декодирования JSON в сообщении.")
        except Exception as e:
            logger.error(f"Ошибка при обработке события {event_type} для ID {django_id}: {e}", exc_info=True)

    # ====================================================================
    #           МЕТОДЫ ОБРАБОТКИ КОНКРЕТНЫХ ТИПОВ СОБЫТИЙ
    # ====================================================================

    def _handle_lease_created(self, lease_instance, fastapi_id, details):
        """Обрабатывает событие LeaseCreated."""
        
        # Обновляем поля, которые устанавливаются FastAPI/Business Logic
        lease_instance.fastapi_id = fastapi_id
        lease_instance.status = 'ACTIVE' 
        
        # Обновляем данные, которые могли быть уточнены (например, окончательная рента)
        if 'monthly_rent' in details:
            lease_instance.monthly_rent = details['monthly_rent']
        
        # Обновляем дату начала (если она пришла)
        if 'start_date' in details:
            lease_instance.start_date = datetime.strptime(details['start_date'], '%Y-%m-%d').date()

        lease_instance.save()
        logger.info(f"Lease {lease_instance.id}: успешно обновлен. Status: {lease_instance.status}, FastAPI ID: {lease_instance.fastapi_id}")
        
    def _handle_lease_updated(self, lease_instance, fastapi_id, details):
        """Обрабатывает событие LeaseUpdated."""
        # Убедимся, что ID соответствует (хотя это не строго необходимо, но хорошо для валидации)
        if lease_instance.fastapi_id != fastapi_id:
            logger.warning(f"ID Lease (Django: {lease_instance.fastapi_id}, Event: {fastapi_id}) не совпадают. Игнорируем или используем ID события.")
        
        # Обновление основных полей
        if 'monthly_rent' in details:
            lease_instance.monthly_rent = details['monthly_rent']
        
        if 'end_date' in details:
            lease_instance.end_date = datetime.strptime(details['end_date'], '%Y-%m-%d').date()

        if 'status' in details:
            # Например, статус может быть обновлен до 'PENDING_TERMINATION'
            lease_instance.status = details['status'] 

        lease_instance.save()
        logger.info(f"Lease {lease_instance.id}: обновлено. Новая рента: {lease_instance.monthly_rent}, Status: {lease_instance.status}")

    def _handle_lease_terminated(self, lease_instance, fastapi_id, details):
        """Обрабатывает событие LeaseTerminated."""
        
        # Устанавливаем окончательный статус
        lease_instance.status = 'TERMINATED'
        
        # Возможно, обновляем фактическую дату окончания
        if 'actual_end_date' in details:
            lease_instance.end_date = datetime.strptime(details['actual_end_date'], '%Y-%m-%d').date()

        lease_instance.save()
        logger.info(f"Lease {lease_instance.id}: успешно завершен. Status: TERMINATED.")