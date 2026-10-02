import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.database import SessionLocal
from app.services.notifications import run_alerts

log = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Europe/Paris")


async def daily_alerts_job():
    async with SessionLocal() as db:
        result = await run_alerts(db)
        log.info("Job alertes : %s", result)


def start_scheduler():
    if not settings.scheduler_enabled or scheduler.running:
        return
    scheduler.add_job(daily_alerts_job, "cron", hour=settings.alert_hour, minute=0, id="daily_alerts", replace_existing=True)
    scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
