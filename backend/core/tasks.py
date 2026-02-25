from core.celery_app import celery_app


@celery_app.task(name="visionqa.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="visionqa.add")
def add(x: int, y: int) -> int:
    return x + y

