"""Optional filesystem notifications with periodic reconciliation."""
import asyncio
import atexit
import logging
import os
import threading

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    FileSystemEventHandler = object
    Observer = None


class FileChanges:
    def __init__(self):
        self._observer = None
        self._directories = set()
        self._subscriptions = {}
        self._lock = threading.Lock()
        atexit.register(self.close)

    @staticmethod
    def _key(path):
        return os.path.normcase(os.path.abspath(os.fspath(path)))

    def _notify(self, event):
        if event.is_directory:
            return
        paths = {self._key(event.src_path)}
        if getattr(event, 'dest_path', None):
            paths.add(self._key(event.dest_path))
        with self._lock:
            targets = [value for key, value in self._subscriptions.items() if key[1] in paths]
        for loop, signal in targets:
            if not loop.is_closed():
                try:
                    loop.call_soon_threadsafe(signal.set)
                except RuntimeError:
                    pass

    async def wait(self, path, timeout=7):
        if Observer is None or not path:
            await asyncio.sleep(timeout)
            return
        loop = asyncio.get_running_loop()
        path = self._key(path)
        key = (loop, path)
        with self._lock:
            # Retire subscriptions when settings change or a bot loop is replaced.
            for old in list(self._subscriptions):
                if old[0].is_closed():
                    del self._subscriptions[old]
            subscription = self._subscriptions.get(key)
            if subscription is None:
                signal = asyncio.Event()
                self._subscriptions[key] = (loop, signal)
            else:
                signal = subscription[1]
        try:
            if self._observer is None:
                self._observer = Observer()
                self._observer.start()
            directory = os.path.dirname(path)
            if directory not in self._directories:
                handler = FileSystemEventHandler()
                # Read/open/close notifications must not trigger processing loops.
                handler.on_modified = self._notify
                handler.on_created = self._notify
                handler.on_moved = self._notify
                handler.on_deleted = self._notify
                self._observer.schedule(handler, directory, recursive=False)
                self._directories.add(directory)
        except Exception:
            logging.getLogger('mystats').warning('File notifications unavailable; using periodic checks', exc_info=True)
            await asyncio.sleep(timeout)
            return
        if subscription is None:
            return  # Establish the initial modification-time baseline immediately.
        try:
            await asyncio.wait_for(signal.wait(), timeout)
        except asyncio.TimeoutError:
            pass
        finally:
            signal.clear()

    def close(self):
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None


file_changes = FileChanges()
