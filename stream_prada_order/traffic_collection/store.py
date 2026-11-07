"""Single-writer, logically append-only SQLite event journal and private blobs.

SQLite pages/journals are not WORM storage. Events cannot be updated/deleted via
the application; a hash chain detects ordinary corruption, not a malicious admin.
"""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import threading
import time
from datetime import datetime, timezone
import uuid

from .schema import IntegrityError, canonical, digest, require, strict_json
from .state import replay


def _check_ignored_paths(root, names):
    root = Path(root).resolve()
    require(not str(root).startswith(("\\\\", "//")), "local_disk_required")
    parent = root
    while not parent.exists():
        parent = parent.parent
    repository = next((p for p in [parent, *parent.parents] if (p / ".git").exists()), None)
    if repository:
        for name in names:
            relative = (root / name).relative_to(repository).as_posix()
            ignored = subprocess.run(["git", "-C", str(repository), "check-ignore", "--quiet", "--", relative], capture_output=True)
            tracked = subprocess.run(["git", "-C", str(repository), "ls-files", "--", relative], capture_output=True)
            require(ignored.returncode == 0 and tracked.returncode == 0 and not tracked.stdout, "private_path_not_git_ignored")
    return root


def check_private_root(root):
    return _check_ignored_paths(root, ["events.sqlite3", "events.sqlite3-journal", "writer.lock", "blobs/privacy-probe.private"])


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"), time.monotonic_ns()


def read_events(root):
    path = Path(root).resolve() / "events.sqlite3"
    require(path.is_file() and not path.is_symlink(), "store_missing")
    conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        require(conn.execute("PRAGMA user_version").fetchone()[0] == 1, "unsupported_store_version")
        rows = conn.execute("SELECT sequence, body, previous_sha256, event_sha256 FROM events ORDER BY sequence").fetchall()
        events, previous = [], "0" * 64
        for seq, body, old_hash, event_hash in rows:
            require(all(type(x) is str for x in [body, old_hash, event_hash]), "journal_corrupt")
            event = strict_json(body)
            require(type(event) is dict, "journal_corrupt")
            require(canonical(event) == body and old_hash == previous and event["event_sequence"] == seq, "journal_corrupt")
            require(digest(previous + "\n" + body) == event_hash, "journal_corrupt")
            previous = event_hash
            events.append(event)
        replay(events)
        return events
    except (sqlite3.DatabaseError, json.JSONDecodeError, KeyError):
        raise IntegrityError("journal_corrupt") from None
    finally:
        conn.close()


class EventStore:
    def __init__(self, root, clock=now, max_logical_bytes=64 * 1024 * 1024):
        self.root = check_private_root(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        require(not (self.root / "blobs").is_symlink(), "symlink_storage_rejected")
        (self.root / "blobs").mkdir(exist_ok=True, mode=0o700)
        self.clock = clock
        self.clock_epoch = uuid.uuid4().hex
        self.max_logical_bytes = max_logical_bytes
        self.mutex = threading.RLock()
        self.conn = None
        self.lock = (self.root / "writer.lock").open("a+b")
        try:
            if self.lock.seek(0, os.SEEK_END) == 0:
                self.lock.write(b"0"); self.lock.flush()
            self.lock.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.lock.close()
            raise IntegrityError("writer_already_active") from None
        try:
            path = self.root / "events.sqlite3"
            require(not path.is_symlink(), "symlink_storage_rejected")
            existing = path.exists() and path.stat().st_size > 0
            self.conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
            if existing:
                version = self.conn.execute("PRAGMA user_version").fetchone()[0]
                tables = list(self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'"))
                if version == 0 and not tables:
                    existing = False  # Empty header left before an atomic schema commit.
                else:
                    require(version == 1, "unsupported_store_version")
            if existing:
                require(self.conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete", "unsupported_journal_mode")
            self.conn.execute("PRAGMA journal_mode=DELETE")
            self.conn.execute("PRAGMA synchronous=FULL")
            if not existing:
                self.conn.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE events(sequence INTEGER PRIMARY KEY, body TEXT NOT NULL,
                        previous_sha256 TEXT NOT NULL, event_sha256 TEXT NOT NULL UNIQUE);
                    CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN
                        SELECT RAISE(ABORT, 'append_only'); END;
                    CREATE TRIGGER events_no_delete BEFORE DELETE ON events BEGIN
                        SELECT RAISE(ABORT, 'append_only'); END;
                    PRAGMA user_version=1;
                    COMMIT;
                """)
            triggers = {r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
            require({"events_no_update", "events_no_delete"} <= triggers, "append_only_guards_missing")
            self.state = replay(read_events(self.root))
            for run in self.state.runs.values():
                if not run["closed"]:
                    self.max_logical_bytes = min(self.max_logical_bytes, run["manifest"]["budget"]["max_logical_storage_bytes"])
        except BaseException:
            self.close()
            raise

    def events(self):
        with self.mutex:
            return read_events(self.root)

    def logical_bytes(self):
        body = self.conn.execute("SELECT coalesce(sum(length(cast(body AS BLOB))),0) FROM events").fetchone()[0]
        return body + sum(p.stat().st_size for p in (self.root / "blobs").iterdir() if p.is_file())

    def write_blob(self, raw):
        require(isinstance(raw, bytes), "blob_bytes_required")
        sha = digest(raw); path = self.root / "blobs" / (sha + ".private")
        _check_ignored_paths(self.root, ["blobs/" + sha + ".private"])
        require(not path.is_symlink(), "symlink_storage_rejected")
        if path.exists():
            require(self.read_blob(sha) == raw, "blob_corrupt")
            return sha
        require(self.logical_bytes() + len(raw) <= self.max_logical_bytes, "storage_budget_exhausted")
        temporary = self.root / "blobs" / ("part-" + uuid.uuid4().hex)
        _check_ignored_paths(self.root, [temporary.relative_to(self.root).as_posix()])
        with temporary.open("xb") as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
        # Hard-link publish is atomic and cannot overwrite an existing content address.
        os.link(temporary, path)
        temporary.unlink()
        return sha

    def read_blob(self, sha):
        require(len(sha) == 64 and all(c in "0123456789abcdef" for c in sha), "invalid_blob_reference")
        path = self.root / "blobs" / (sha + ".private")
        require(path.is_file() and not path.is_symlink(), "blob_missing")
        raw = path.read_bytes()
        require(digest(raw) == sha, "blob_corrupt")
        return raw

    def append(self, kind, run_id, session_id=None, request_id=None, data=None):
        with self.mutex:
            _check_ignored_paths(self.root, ["events.sqlite3", "events.sqlite3-journal"])
            stamp, monotonic = self.clock()
            event = json.loads(canonical({"schema_version": "traffic-event-v1", "event_sequence": self.state.sequence + 1,
                "kind": kind, "run_id": run_id, "session_id": session_id, "request_id": request_id,
                "utc": stamp, "monotonic_ns": monotonic, "clock_epoch": self.clock_epoch,
                "utc_regressed": bool(self.state.last_utc and stamp < self.state.last_utc), "data": data}))
            body = canonical(event)
            require(self.logical_bytes() + len(body.encode()) <= self.max_logical_bytes, "storage_budget_exhausted")
            self.state.advance(event)
            try:
                self.conn.execute("BEGIN IMMEDIATE")
                last = self.conn.execute("SELECT event_sha256 FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
                previous = last[0] if last else "0" * 64
                self.conn.execute("INSERT INTO events VALUES (?,?,?,?)", (event["event_sequence"], body, previous, digest(previous + "\n" + body)))
                self.conn.execute("COMMIT")
            except BaseException:
                if self.conn.in_transaction:
                    self.conn.execute("ROLLBACK")
                self.state = replay(read_events(self.root))
                raise
            return event

    def close(self):
        if self.conn is not None:
            self.conn.close(); self.conn = None
        if getattr(self, "lock", None) and not self.lock.closed:
            self.lock.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock.fileno(), fcntl.LOCK_UN)
            self.lock.close()

    def __enter__(self): return self
    def __exit__(self, *_): self.close()
