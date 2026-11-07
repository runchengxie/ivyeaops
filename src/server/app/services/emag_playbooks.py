"""Private immutable evidence revisions; never writes to a marketplace."""

import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from app.services import store_artifacts as artifacts, emag_operations


class Conflict(ValueError):
    """The current evidence or record identity no longer matches."""


class MissingWorkspace(ValueError):
    """No compatible snapshot exists for this workspace."""


@contextmanager
def _db():
    from app.core.config import settings

    path = settings.data_dir / "emag-playbooks.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    os.close(fd)
    path.chmod(0o600)
    conn = sqlite3.connect(path, timeout=20)
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS revisions (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT NOT NULL, revision INTEGER NOT NULL,
            store TEXT NOT NULL, body TEXT NOT NULL,
            UNIQUE(record_id, revision))""")
        with conn:
            yield conn
    finally:
        conn.close()


def _source(store_id):
    try:
        snapshot = artifacts.read_snapshot(store_id)
        emag_operations._issues(snapshot)
        return snapshot
    except (OSError, ValueError) as exc:
        raise MissingWorkspace(str(exc)) from exc


def view(store_id, before_sequence=None):
    from app.services import emag_playbook_rules as rules

    if before_sequence is not None and (type(before_sequence) is not int or before_sequence <= 0):
        raise ValueError("History cursor must be a positive integer")
    with artifacts.snapshot_guard():
        snapshot = _source(store_id)
        offers = snapshot["data"]["offers"]
        with _db() as conn:
            rows = conn.execute(
                "SELECT sequence, body FROM revisions WHERE store=? AND (? IS NULL OR sequence<?) "
                "ORDER BY sequence DESC LIMIT 501",
                (store_id, before_sequence, before_sequence),
            ).fetchall()
            latest = dict(
                conn.execute(
                    "SELECT record_id, MAX(revision) FROM revisions WHERE store=? GROUP BY record_id", (store_id,)
                )
            )
            records = [{**json.loads(body), "sequence": sequence} for sequence, body in rows]
        truncated = len(records) > 500
        records = records[:500]
        for record in records:
            record["stale"] = record["snapshot_id"] != snapshot["snapshot_id"]
            record["current"] = latest[record["record_id"]] == record["revision"] and not record["stale"]
            if record["stale"]:
                record["historical_assessment"] = record["assessment"]
                record["assessment"] = {
                    "checks": [{**check, "status": "unknown"} for check in record["assessment"]["checks"]],
                    "source_ids": record["assessment"]["source_ids"],
                    "metrics": {},
                }
        return {
            "store_id": store_id,
            "snapshot_id": snapshot["snapshot_id"],
            "captured_at": snapshot["captured_at"],
            "marketplace_writes": False,
            "products": [
                {
                    "product_id": str(o["id"]),
                    "name": o.get("name", ""),
                    "sku": o.get("part_number", ""),
                    "stock": o.get("general_stock"),
                }
                for o in offers
            ],
            "records_limit": 500,
            "records_truncated": truncated,
            "records_next_before": records[-1]["sequence"] if truncated else None,
            "repairs": rules.repair_guidance(snapshot),
            "sources": rules.sources(),
            "records": records,
        }


def save(store_id, snapshot_id, kind, product_id, payload, actor, record_id=None, revision=0):
    from app.services import emag_playbook_rules as rules

    if type(revision) is not int or revision < 0:
        raise ValueError("Revision must be a nonnegative integer")
    with artifacts.snapshot_guard():
        snapshot = _source(store_id)
        if snapshot["snapshot_id"] != snapshot_id:
            raise Conflict("Evidence is stale; reload first")
        offers = snapshot["data"]["offers"]
        selected = [o for o in offers if str(o["id"]) == product_id]
        if not selected:
            raise Conflict("Select a product from the current store snapshot")
        with _db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if record_id is not None:
                previous = conn.execute(
                    "SELECT body FROM revisions WHERE record_id=? ORDER BY revision DESC LIMIT 1", (record_id,)
                ).fetchone()
                if previous is None:
                    raise Conflict("Record not found in this store")
                previous = json.loads(previous[0])
                if (previous["store_id"], previous["kind"], previous["product_id"]) != (store_id, kind, product_id):
                    raise Conflict("Record store, kind and product identity cannot change")
                if previous["revision"] != revision:
                    raise Conflict("Revision conflict; reload first")
            elif revision != 0:
                raise Conflict("New records require revision zero")
            scope = selected if kind == "ads" else offers
            normalized = rules.validate_payload(kind, payload, scope)
            result = {
                "record_id": record_id or secrets.token_hex(16),
                "store_id": store_id,
                "kind": kind,
                "product_id": product_id,
                "snapshot_id": snapshot_id,
                "revision": revision + 1,
                "payload": normalized,
                "assessment": rules.assess(kind, normalized, scope),
                "actor": actor,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "stale": False,
                "current": True,
                "marketplace_writes": False,
            }
            conn.execute(
                "INSERT INTO revisions(record_id, revision, store, body) VALUES(?,?,?,?)",
                (result["record_id"], result["revision"], store_id, json.dumps(result, allow_nan=False)),
            )
            return result
