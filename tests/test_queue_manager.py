# tests/test_queue_manager.py
"""Unit tests for the pure-Python queue state machine (no GUI, no network)."""
import unittest

from models import DownloadItem, DownloadStatus
from queue_manager import QueueManager


class FakeStore:
    """In-memory stand-in for persistence.QueueStore."""

    def __init__(self, queue=None):
        self.queue = list(queue or [])
        self.save_calls = 0

    def load_queue(self):
        return list(self.queue)

    def save_queue(self, queue):
        self.queue = list(queue)
        self.save_calls += 1


def make_manager(queue=None, history=None):
    store = FakeStore(queue)
    history = history or []
    return QueueManager(store, history_loader=lambda: list(history)), store


class LoadRehabTests(unittest.TestCase):
    def test_downloading_items_rehabilitated_to_pending(self):
        store = FakeStore([
            {"url": "a", "path": "/d", "status": "downloading", "title": "a"},
            {"url": "b", "path": "/d", "status": "pending", "title": "b"},
        ])
        manager = QueueManager(store)
        manager.load()
        statuses = [item.status for item in manager.snapshot()]
        self.assertEqual(statuses, [DownloadStatus.PENDING, DownloadStatus.PENDING])
        # The rehabilitation is persisted.
        self.assertEqual(store.queue[0]["status"], "pending")

    def test_unknown_status_defaults_to_pending(self):
        store = FakeStore([{"url": "a", "path": "/d", "status": "weird"}])
        manager = QueueManager(store)
        manager.load()
        self.assertEqual(manager.item_at(0).status, DownloadStatus.PENDING)

    def test_malformed_rows_are_skipped(self):
        store = FakeStore([{"url": "a", "path": "/d"}, "not-a-dict", 42])
        manager = QueueManager(store)
        manager.load()
        self.assertEqual(len(manager), 1)


class DuplicateTests(unittest.TestCase):
    def test_duplicate_in_queue(self):
        manager, _ = make_manager()
        manager.add(DownloadItem(url="u", path="/d", status=DownloadStatus.PENDING))
        kind, record = manager.find_duplicate("u")
        self.assertEqual(kind, "queue")
        self.assertEqual(record["url"], "u")

    def test_completed_item_is_not_a_queue_duplicate(self):
        manager, _ = make_manager()
        manager.add(DownloadItem(url="u", path="/d", status=DownloadStatus.COMPLETED))
        self.assertEqual(manager.find_duplicate("u"), (None, None))

    def test_duplicate_in_history(self):
        manager, _ = make_manager(history=[{"url": "h"}])
        kind, record = manager.find_duplicate("h")
        self.assertEqual(kind, "history")
        self.assertEqual(record["url"], "h")


class TransitionTests(unittest.TestCase):
    def test_pause_all_running_and_resume(self):
        manager, store = make_manager()
        manager.add(DownloadItem(url="a", path="/d"))
        manager.add(DownloadItem(url="b", path="/d"))
        manager.mark_running()
        self.assertEqual(manager.stats()["downloading"], 2)

        paused = manager.pause_all_running()
        self.assertEqual(paused, 2)
        self.assertEqual(manager.stats()["paused"], 2)

        self.assertTrue(manager.resume(0))
        self.assertEqual(manager.item_at(0).status, DownloadStatus.PENDING)
        self.assertTrue(manager.resume(1))
        # Resuming an already-pending item is a no-op.
        self.assertFalse(manager.resume(0))

    def test_mark_failed_does_not_clobber_pause(self):
        manager, _ = make_manager()
        item = manager.add(DownloadItem(url="a", path="/d", status=DownloadStatus.PAUSED))
        manager.mark_failed(item)
        self.assertEqual(item.status, DownloadStatus.PAUSED)

    def test_mark_running_skips_completed(self):
        manager, _ = make_manager()
        manager.add(DownloadItem(url="done", path="/d", status=DownloadStatus.COMPLETED))
        manager.add(DownloadItem(url="todo", path="/d"))
        manager.mark_running()
        self.assertEqual(manager.item_at(0).status, DownloadStatus.COMPLETED)
        self.assertEqual(manager.item_at(1).status, DownloadStatus.DOWNLOADING)

    def test_clear_completed(self):
        manager, _ = make_manager()
        manager.add(DownloadItem(url="a", path="/d", status=DownloadStatus.COMPLETED))
        manager.add(DownloadItem(url="b", path="/d"))
        manager.clear_completed()
        self.assertEqual(len(manager), 1)
        self.assertEqual(manager.item_at(0).url, "b")

    def test_remove_out_of_range_is_noop(self):
        manager, _ = make_manager()
        manager.add(DownloadItem(url="a", path="/d"))
        self.assertFalse(manager.remove(5))
        self.assertEqual(len(manager), 1)


class ReorderTests(unittest.TestCase):
    def _manager(self):
        manager, store = make_manager()
        first = manager.add(DownloadItem(url="a", path="/d", title="a"))
        second = manager.add(DownloadItem(url="b", path="/d", title="b"))
        third = manager.add(DownloadItem(url="c", path="/d", title="c"))
        return manager, store, (first, second, third)

    def test_move_swaps_and_persists(self):
        manager, store, (first, second, _) = self._manager()
        self.assertTrue(manager.move(second, -1))
        self.assertEqual([item.title for item in manager.snapshot()], ["b", "a", "c"])
        self.assertEqual([row["title"] for row in store.queue], ["b", "a", "c"])

    def test_move_clamps_at_both_ends(self):
        manager, store, (first, _, third) = self._manager()
        before = store.save_calls
        self.assertFalse(manager.move(first, -1))
        self.assertFalse(manager.move(third, 1))
        self.assertEqual(store.save_calls, before)   # nothing moved, nothing saved

    def test_completed_or_running_items_cannot_move(self):
        manager, _, (first, second, third) = self._manager()
        second.status = DownloadStatus.DOWNLOADING
        self.assertFalse(manager.move(second, -1))
        third.status = DownloadStatus.COMPLETED
        self.assertFalse(manager.move(third, -1))
        self.assertEqual([item.title for item in manager.snapshot()], ["a", "b", "c"])

    def test_move_skips_immovable_neighbours(self):
        manager, _, (_, second, third) = self._manager()
        second.status = DownloadStatus.COMPLETED
        self.assertTrue(manager.move(third, -1))
        # The completed row is stepped over: the two runnable items swap.
        self.assertEqual([item.title for item in manager.snapshot()], ["c", "b", "a"])


class PersistenceTests(unittest.TestCase):
    def test_mutations_persist(self):
        manager, store = make_manager()
        manager.add(DownloadItem(url="a", path="/d", title="clip"))
        self.assertEqual(store.queue[0]["title"], "clip")
        self.assertGreaterEqual(store.save_calls, 1)

    def test_stats_shape(self):
        manager, _ = make_manager()
        manager.add(DownloadItem(url="a", path="/d", status=DownloadStatus.FAILED))
        stats = manager.stats()
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["failed"], 1)
        self.assertEqual(stats["pending"], 0)


if __name__ == "__main__":
    unittest.main()
