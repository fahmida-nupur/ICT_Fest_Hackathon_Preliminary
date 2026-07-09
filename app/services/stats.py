"""Live per-room booking statistics.

Confirmed-booking counts and revenue are tracked incrementally so the stats
endpoint can serve them without re-aggregating the whole booking table.
"""
import threading
import time
from sqlalchemy.orm import Session

_stats: dict[int, dict] = {}
_stats_lock = threading.Lock()


def _aggregate_pause() -> None:
    time.sleep(0.1)


def _ensure_initialized(room_id: int, db: Session) -> None:
    if room_id not in _stats:
        from ..models import Booking
        bookings = db.query(Booking).filter(
            Booking.room_id == room_id,
            Booking.status == "confirmed"
        ).all()
        count = len(bookings)
        revenue = sum(b.price_cents for b in bookings)
        _stats[room_id] = {"count": count, "revenue": revenue}


def record_create(room_id: int, price_cents: int, db: Session) -> None:
    with _stats_lock:
        if room_id not in _stats:
            _ensure_initialized(room_id, db)
            _aggregate_pause()
        else:
            current = _stats[room_id]
            count, revenue = current["count"], current["revenue"]
            _aggregate_pause()
            _stats[room_id] = {"count": count + 1, "revenue": revenue + price_cents}


def record_cancel(room_id: int, price_cents: int, db: Session) -> None:
    with _stats_lock:
        if room_id not in _stats:
            _ensure_initialized(room_id, db)
            _aggregate_pause()
        else:
            current = _stats[room_id]
            count, revenue = current["count"], current["revenue"]
            _aggregate_pause()
            _stats[room_id] = {"count": max(0, count - 1), "revenue": revenue - price_cents}


def get(room_id: int, db: Session) -> dict:
    with _stats_lock:
        _ensure_initialized(room_id, db)
        return _stats[room_id]
