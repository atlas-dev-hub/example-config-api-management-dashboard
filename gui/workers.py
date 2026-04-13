"""Background workers for gRPC calls — never block the UI thread.

Each worker runs in a QThread and emits signals when results arrive.
The ``CallbackBridge`` ensures callbacks execute on the **main** thread
(via ``Qt.QueuedConnection``) so that UI updates are safe.
"""

from __future__ import annotations

import logging
import ssl
import socket
import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot

logger = logging.getLogger(__name__)


class GrpcCallWorker(QObject):
    """Runs a single callable in a background thread.

    Signals:
        finished(result): Emitted with the call result on success.
        error(str): Emitted with an error message on failure.
    """

    finished = Signal(object)
    error = Signal(str)

    def __init__(self, func: Callable[..., Any], *args: Any, **kwargs: Any):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs

    @Slot()
    def run(self) -> None:
        try:
            result = self._func(*self._args, **self._kwargs)
            self.finished.emit(result)
        except Exception as exc:
            msg = f"{type(exc).__name__}: {exc}"
            logger.error("Worker error: %s", msg)
            self.error.emit(msg)


class CallbackBridge(QObject):
    """Lives on the main thread; receives signals via QueuedConnection."""

    sig_success = Signal(object)
    sig_error = Signal(str)

    def __init__(
        self,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        if on_success:
            self.sig_success.connect(on_success)
        if on_error:
            self.sig_error.connect(on_error)


def run_in_thread(
    func: Callable[..., Any],
    *args: Any,
    on_success: Callable[[Any], None] | None = None,
    on_error: Callable[[str], None] | None = None,
    parent: QObject | None = None,
    **kwargs: Any,
) -> tuple[QThread, GrpcCallWorker, CallbackBridge]:
    """Run *func* in a QThread with main-thread callbacks.

    Returns ``(thread, worker, bridge)`` — the caller **must** keep
    references alive until the work is done (store them in a list).
    """
    thread = QThread(parent)
    worker = GrpcCallWorker(func, *args, **kwargs)
    bridge = CallbackBridge(on_success, on_error, parent)

    worker.moveToThread(thread)

    # Wire: thread starts → worker.run()
    thread.started.connect(worker.run)

    # Wire: worker signals → bridge (QueuedConnection = main-thread delivery)
    worker.finished.connect(bridge.sig_success, Qt.QueuedConnection)
    worker.error.connect(bridge.sig_error, Qt.QueuedConnection)

    # Clean-up chain: worker done → quit thread → deleteLater
    worker.finished.connect(thread.quit)
    worker.error.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    thread.start()
    return thread, worker, bridge


def fetch_server_cert(host: str, port: int) -> bytes | None:
    """Probe a TLS server and return the certificate as PEM bytes.

    Returns ``None`` if the server doesn't speak TLS.
    """
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives.serialization import Encoding

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, port), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                der = ssock.getpeercert(binary_form=True)
        return x509.load_der_x509_certificate(der).public_bytes(Encoding.PEM)
    except Exception:
        return None
