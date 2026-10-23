"""Fila Redis com confirmação após execução e recuperação pelo Beat."""
import os
from celery import Celery

app = Celery('consultas', broker=os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0'),
             include=['src.tasks'])
app.conf.update(
    task_serializer='json', accept_content=['json'], task_ignore_result=True,
    task_acks_late=True, task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1, broker_connection_retry_on_startup=True,
    broker_transport_options={'visibility_timeout': 3900, 'socket_connect_timeout': 2, 'socket_timeout': 2},
    task_soft_time_limit=3500, task_time_limit=3600,
    beat_schedule={'recuperar-consultas': {'task': 'src.tasks.despachar_pendentes', 'schedule': 30.0}},
)
