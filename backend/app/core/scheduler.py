"""Planificateur de tâches de fond (APScheduler, 1 seul process uvicorn)."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.database import SessionLocal
from app.services.relance_auto import run_relances_auto

log = logging.getLogger("uvicorn.error")

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone="Europe/Paris")
    _scheduler.add_job(
        _tick_relances,
        IntervalTrigger(minutes=30, start_date=None),
        id="relances_auto",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    log.info("Scheduler démarré (relances auto toutes les 30 min)")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("Scheduler arrêté")


def _tick_relances() -> None:
    db = SessionLocal()
    try:
        stats = run_relances_auto(db)
        if stats["copros"] > 0 or stats["envoyes"] > 0:
            log.info("Relances auto : %s", stats)
    except Exception:
        log.exception("Erreur pendant les relances automatiques")
    finally:
        db.close()
