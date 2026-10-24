import asyncio
import tempfile
import unittest
from pathlib import Path
from file_changes import FileChanges


class FileChangeTests(unittest.IsolatedAsyncioTestCase):
    async def test_modification_and_atomic_replacement_wake_monitor(self):
        watcher = FileChanges()
        try:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'race.csv'
                path.write_text('initial')
                await watcher.wait(path, timeout=3)
                async def change():
                    await asyncio.sleep(.15)
                    path.write_text('updated')
                task = asyncio.create_task(change())
                await asyncio.wait_for(watcher.wait(path, timeout=5), 2)
                await task
                await asyncio.sleep(.1)
                # Drain notifications from the first write.
                for _, signal in watcher._subscriptions.values():
                    signal.clear()
                async def replace():
                    await asyncio.sleep(.15)
                    replacement = Path(folder) / 'temp.csv'
                    replacement.write_text('replacement')
                    replacement.replace(path)
                task = asyncio.create_task(replace())
                await asyncio.wait_for(watcher.wait(path, timeout=5), 2)
                await task
        finally:
            watcher.close()

    async def test_timeout_and_cancellation(self):
        watcher = FileChanges()
        try:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'missing.csv'
                await watcher.wait(path, timeout=.02)
                await watcher.wait(path, timeout=.02)
                task = asyncio.create_task(watcher.wait(path, timeout=10))
                await asyncio.sleep(.02)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
        finally:
            watcher.close()
