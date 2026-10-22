
import asyncio
import threading
from contextlib import suppress

from fastapi.testclient import TestClient

from app import main as main_module


def test_periodic_login_cleanup_executes(monkeypatch):
    calls = []

    def fake_cleanup():
        calls.append(True)
        return 2

    monkeypatch.setattr(
        main_module,
        "run_login_cleanup",
        fake_cleanup,
    )

    monkeypatch.setattr(
        main_module,
        "LOGIN_CLEANUP_INTERVAL_SECONDS",
        0.01,
    )

    async def check_execution():
        task = asyncio.create_task(
            main_module.periodic_login_cleanup()
        )

        try:
            async def wait_for_cleanup():
                while not calls:
                    await asyncio.sleep(0.005)

            await asyncio.wait_for(
                wait_for_cleanup(),
                timeout=3,
            )
        finally:
            task.cancel()

            with suppress(asyncio.CancelledError):
                await task

    asyncio.run(check_execution())

    assert calls


def test_lifespan_starts_and_stops_cleanup(monkeypatch):
    started = threading.Event()
    stopped = threading.Event()

    async def fake_periodic_cleanup():
        started.set()

        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    monkeypatch.setattr(
        main_module,
        "periodic_login_cleanup",
        fake_periodic_cleanup,
    )

    with TestClient(main_module.app):
        assert started.wait(timeout=3)

    assert stopped.wait(timeout=3)
