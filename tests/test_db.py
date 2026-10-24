import sqlite3

import db.db as db


def test_migration_keeps_old_subscriptions(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    conn = sqlite3.connect("izhGet.db")
    conn.execute("""CREATE TABLE subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, fav_id INTEGER,
        notify_time TEXT, is_active INTEGER DEFAULT 1)""")
    conn.execute("INSERT INTO subscriptions (user_id, fav_id, notify_time) VALUES (5, 7, '07:30')")
    conn.commit()
    conn.close()

    db.create_tables()
    db.create_tables()  # повторный запуск не падает

    assert db.get_due_schedule_subscriptions("07:30") == [(1, 5, 7, "all")]
    assert db.get_subscription(5, 7) == (1, 5, 7, "07:30", 1, "schedule", "all", None)
    assert db.get_remind_subscriptions() == []


def test_add_and_update_subscription(tmp_db):
    sub_id = db.add_subscription(5, 7, "08:00", mode="remind", days="weekdays", lead_min=10)
    assert db.get_subscription(5, 7) == (sub_id, 5, 7, "08:00", 1, "remind", "weekdays", 10)
    assert db.get_remind_subscriptions() == [(sub_id, 5, 7, "08:00", "weekdays", 10)]
    assert db.get_due_schedule_subscriptions("08:00") == []

    assert db.add_subscription(5, 7, "07:30") == sub_id
    assert db.get_subscription(5, 7) == (sub_id, 5, 7, "07:30", 1, "schedule", "all", None)


def test_add_run_is_unique_per_day(tmp_db):
    assert db.add_run(1, 5, "2026-10-26", "07:57", "08:07", "1", "08:17", "planned") is True
    assert db.add_run(1, 5, "2026-10-26", "07:50", None, None, None, "planned") is False
    assert db.get_run(1, "2026-10-26")[1] == "planned"
    assert db.get_run(1, "2026-10-27") is None


def test_get_due_runs_and_claim(tmp_db):
    sub_id = db.add_subscription(5, 7, "08:00", mode="remind", days="all", lead_min=10)
    db.add_run(sub_id, 5, "2026-10-26", "07:57", "08:07", "1", "08:17", "planned")

    assert db.get_due_runs("2026-10-26", "07:56") == []
    due = db.get_due_runs("2026-10-26", "07:57")
    assert len(due) == 1
    run_id, user_id, fire_at, dep_time, route, next_dep, fav_id, notify_time = due[0]
    assert (user_id, fire_at, dep_time, route, next_dep, fav_id, notify_time) == \
        (5, "07:57", "08:07", "1", "08:17", 7, "08:00")
    assert db.get_due_runs("2026-10-27", "07:57") == []

    assert db.claim_run(run_id, "sent") is True
    assert db.claim_run(run_id, "sent") is False
    assert db.get_due_runs("2026-10-26", "08:30") == []


def test_changing_subscription_resets_planned_run_only(tmp_db):
    sub_id = db.add_subscription(5, 7, "08:00", mode="remind", days="all", lead_min=10)
    db.add_run(sub_id, 5, "2026-10-25", "07:57", "08:07", "1", None, "sent")
    db.add_run(sub_id, 5, "2026-10-26", "07:57", "08:07", "1", None, "planned")

    db.add_subscription(5, 7, "08:00", mode="remind", days="all", lead_min=5)

    assert db.get_run(sub_id, "2026-10-26") is None
    assert db.get_run(sub_id, "2026-10-25")[1] == "sent"


def test_delete_subscription_removes_runs(tmp_db):
    sub_id = db.add_subscription(5, 7, "08:00", mode="remind", days="all", lead_min=10)
    db.add_run(sub_id, 5, "2026-10-26", "07:57", "08:07", "1", None, "planned")
    assert db.delete_subscription(sub_id, 6) is False
    assert db.get_run(sub_id, "2026-10-26") is not None
    assert db.delete_subscription(sub_id, 5) is True
    assert db.get_run(sub_id, "2026-10-26") is None


def test_delete_favorite_removes_subscription_and_runs(tmp_db):
    fav_id = db.add_favorite_route(5, "1", "1900", "900", "30", "Дом")
    sub_id = db.add_subscription(5, fav_id, "08:00", mode="remind", days="all", lead_min=10)
    db.add_run(sub_id, 5, "2026-10-26", "07:57", "08:07", "1", None, "planned")
    assert db.delete_favorite_route(fav_id, 5) is True
    assert db.get_subscription(5, fav_id) is None
    assert db.get_run(sub_id, "2026-10-26") is None


def test_cleanup_runs(tmp_db):
    db.add_run(1, 5, "2026-10-23", "07:57", None, None, None, "sent")
    db.add_run(1, 5, "2026-10-24", "07:57", None, None, None, "sent")
    db.cleanup_runs("2026-10-24")
    assert db.get_run(1, "2026-10-23") is None
    assert db.get_run(1, "2026-10-24") is not None
