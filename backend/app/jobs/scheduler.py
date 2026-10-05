import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.database import SessionLocal
from app.services.notifications import run_alerts

log = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="UTC")
JOB_ID = "daily_alerts"


async def daily_alerts_job():
    async with SessionLocal() as db:
        result = await run_alerts(db)
        log.info("Job alertes : %s", result)


def _trigger(tz: str) -> CronTrigger:
    return CronTrigger(hour=settings.alert_hour, minute=0, timezone=tz)


def start_scheduler(tz: str = "UTC"):
    if not settings.scheduler_enabled or scheduler.running:
        return
    scheduler.add_job(daily_alerts_job, _trigger(tz), id=JOB_ID, replace_existing=True)
    scheduler.start()


def reschedule(tz: str):
    """Replanifie le contrôle quotidien après un changement de fuseau horaire."""
    if scheduler.running and scheduler.get_job(JOB_ID):
        scheduler.reschedule_job(JOB_ID, trigger=_trigger(tz))


def next_run():
    job = scheduler.get_job(JOB_ID) if scheduler.running else None
    return job.next_run_time if job else None


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
