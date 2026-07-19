from app.workers.celery_app import celery_app

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=5
)
def process_gps_point(self, point_id: int):
    try:
        print(f"Processing GPS point: {point_id}")
        return {"status": "processed", "point_id": point_id}
    except Exception as exc:
        raise self.retry(exc=exc)