"""SM Configuration API Explorer — PySide6 GUI.

Launch:  python -m gui.main
"""

from __future__ import annotations

import logging
import pprint
import sys
import time
from datetime import datetime
from functools import partial
from typing import Any, Callable, Sequence

from PySide6.QtCore import Qt, QTimer, QThread, Signal, QObject, Slot
from PySide6.QtGui import QColor, QFont, QIcon, QTextCharFormat
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QSpinBox,
)

from gui.connection_manager import ConnectionStore, SMConnection
from gui.topology import TopologyDiagram
from gui.workers import fetch_server_cert, run_in_thread

logger = logging.getLogger(__name__)

# ── Colours ───────────────────────────────────────────────────────────────
ACCENT = "#D4572A"
SUCCESS = "#107c10"
ERROR = "#d13438"
WARN = "#ff8c00"
MUTED = "#8a8886"
BG_DARK = "#1e1e1e"


# ── Status polling worker ────────────────────────────────────────────────
class StatusPoller(QObject):
    """Polls all connections for status in a background thread."""
    updated = Signal()

    def __init__(self, store: ConnectionStore):
        super().__init__()
        self._store = store
        self._running = True

    def stop(self):
        self._running = False

    @Slot()
    def run(self):
        while self._running:
            for conn in self._store.connections:
                if conn.connected and conn.client:
                    conn.poll_status()
            self.updated.emit()
            QThread.msleep(2000)


# ── Add Connection Dialog ────────────────────────────────────────────────
class AddConnectionDialog(QDialog):
    def __init__(self, parent=None, *, name="My SM", address="localhost:7000", insecure=False):
        super().__init__(parent)
        self.setWindowTitle("Edit Connection" if name != "My SM" else "Add Connection")
        self.setMinimumWidth(400)

        layout = QFormLayout(self)
        self.name_edit = QLineEdit(name)
        self.address_edit = QLineEdit(address)
        self.insecure_check = QCheckBox("Insecure (no TLS)")
        self.insecure_check.setChecked(insecure)

        layout.addRow("Name:", self.name_edit)
        layout.addRow("Address (host:port):", self.address_edit)
        layout.addRow("", self.insecure_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_connection(self) -> SMConnection:
        return SMConnection(
            name=self.name_edit.text().strip() or "Unnamed",
            address=self.address_edit.text().strip() or "localhost:7000",
            insecure=self.insecure_check.isChecked(),
        )


# ══════════════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SM Configuration API Explorer")
        self.resize(1400, 900)
        self.setMinimumSize(1000, 700)

        self._store = ConnectionStore()
        self._store.load()
        self._threads: list[Any] = []  # prevent GC of (thread, worker, bridge)
        self._app_combos: list[QComboBox] = []  # all App ID combo boxes to refresh

        # Status poller
        self._poller_thread = QThread()
        self._poller = StatusPoller(self._store)
        self._poller.moveToThread(self._poller_thread)
        self._poller_thread.started.connect(self._poller.run)
        self._poller.updated.connect(self._refresh_connection_list, Qt.QueuedConnection)

        self._build_ui()
        self._poller.updated.connect(self._topology.refresh, Qt.QueuedConnection)
        self._topology.card_action.connect(self._on_card_action, Qt.QueuedConnection)
        self._poller_thread.start()

    # ── UI construction ──────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet(f"background-color: {ACCENT}; color: white;")
        header.setFixedHeight(56)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 0, 20, 0)
        title = QLabel("System Monitor Configuration API")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: white;")
        h_lay.addWidget(title)
        h_lay.addStretch()

        # Theme toggle button
        self._dark_mode = False
        self._theme_btn = QPushButton("🌙 Dark")
        self._theme_btn.setFixedWidth(90)
        self._theme_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.15); color: white; "
            "border: 1px solid rgba(255,255,255,0.3); border-radius: 4px; "
            "padding: 4px 12px; font-weight: bold; }"
            "QPushButton:hover { background: rgba(255,255,255,0.25); }"
        )
        self._theme_btn.clicked.connect(self._toggle_theme)
        h_lay.addWidget(self._theme_btn)

        root_layout.addWidget(header)

        # Main splitter: left (connections) | right (tabs + output)
        main_splitter = QSplitter(Qt.Horizontal)

        # ── Left panel: Connection manager ──
        left = QWidget()
        left.setMinimumWidth(260)
        left.setMaximumWidth(380)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(8, 8, 4, 8)

        lbl = QLabel("Connections")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        left_lay.addWidget(lbl)

        self._conn_list = QListWidget()
        self._conn_list.currentRowChanged.connect(self._on_connection_selected)
        self._conn_list.doubleClicked.connect(self._edit_selected)
        left_lay.addWidget(self._conn_list)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("+ Add")
        btn_add.clicked.connect(self._add_connection)
        btn_edit = QPushButton("✏ Edit")
        btn_edit.clicked.connect(self._edit_selected)
        btn_connect = QPushButton("Connect")
        btn_connect.clicked.connect(self._connect_selected)
        btn_disconnect = QPushButton("Disconnect")
        btn_disconnect.clicked.connect(self._disconnect_selected)
        btn_remove = QPushButton("Remove")
        btn_remove.clicked.connect(self._remove_selected)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_connect)
        btn_row.addWidget(btn_disconnect)
        btn_row.addWidget(btn_remove)
        left_lay.addLayout(btn_row)

        # Status indicators
        status_group = QGroupBox("Selected Connection Status")
        sg_lay = QVBoxLayout(status_group)
        self._lbl_link = QLabel("Link: —")
        self._lbl_online = QLabel("Online: —")
        self._lbl_update = QLabel("Live Update: —")
        self._lbl_error = QLabel("")
        self._lbl_error.setWordWrap(True)
        self._lbl_error.setStyleSheet(f"color: {ERROR};")
        for w in (self._lbl_link, self._lbl_online, self._lbl_update, self._lbl_error):
            w.setFont(QFont("Segoe UI", 10))
            sg_lay.addWidget(w)
        left_lay.addWidget(status_group)
        main_splitter.addWidget(left)

        # ── Right panel: Tabs + Output ──
        right_splitter = QSplitter(Qt.Vertical)

        self._tabs = QTabWidget()
        self._topology = TopologyDiagram(self._store)
        self._tabs.addTab(self._topology, "🗺 Server Connections")
        self._build_tab_system()
        self._build_tab_project()
        self._build_tab_parameters()
        self._build_tab_logging()
        self._build_tab_virtual()
        right_splitter.addWidget(self._tabs)

        # Output log
        out_widget = QWidget()
        out_lay = QVBoxLayout(out_widget)
        out_lay.setContentsMargins(4, 4, 4, 4)
        out_bar = QHBoxLayout()
        out_bar.addWidget(QLabel("Output Log"))
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(lambda: self._output.clear())
        out_bar.addStretch()
        out_bar.addWidget(btn_clear)
        out_lay.addLayout(out_bar)

        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(QFont("Cascadia Mono", 9))
        self._output.setStyleSheet(
            f"background-color: {BG_DARK}; color: #d4d4d4; border: none;"
        )
        out_lay.addWidget(self._output)
        right_splitter.addWidget(out_widget)

        right_splitter.setSizes([600, 200])
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([280, 1120])
        root_layout.addWidget(main_splitter)

        # Status bar
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("Ready")

        # Populate connection list
        self._refresh_connection_list()

    # ── Tab builders ─────────────────────────────────────────────────

    def _build_tab_system(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)

        g = self._group(layout, "Status & Connectivity")
        self._action_btn(g, "Get Status", self._call, "system", "get_status")
        self._action_btn(g, "Set Online (True)", self._call, "system", "set_online", True)
        self._action_btn(g, "Set Online (False)", self._call, "system", "set_online", False)
        self._action_btn(g, "Set Live Update (True)", self._call, "system", "set_live_update", True)
        self._action_btn(g, "Set Live Update (False)", self._call, "system", "set_live_update", False)

        g = self._group(layout, "Unit Management")
        self._action_btn(g, "Get Unit List", self._call, "system", "get_unit_list")
        self._action_btn(g, "Get Unit Name", self._call, "system", "get_unit_name")

        g = self._group(layout, "Information")
        self._action_btn(g, "Get Licence Details", self._call, "system", "get_licence_details")
        self._action_btn(g, "Get Device Properties", self._call, "system", "get_device_properties")
        self._action_btn(g, "Get Log Folder", self._call, "system", "get_log_folder")
        self._action_btn(g, "Get PPO File Name", self._call, "system", "get_ppo_file_name")

        layout.addStretch()
        self._tabs.addTab(scroll, "🔌 System")

    def _build_tab_project(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)

        g = self._group(layout, "Version & Build")
        self._action_btn(g, "Get Version Number", self._call, "project", "get_version_number")
        self._action_btn(g, "Get Build Number", self._call, "project", "get_build_number")

        g = self._group(layout, "Application Management")
        self._action_btn(g, "Get App Details", self._call_and_refresh_apps)
        self._action_btn(g, "Get Active Apps", self._call, "project", "get_active_apps")

        g = self._group(layout, "Data Version (DTV)")
        self._action_btn_with_app_combo(g, "Get DTV Version",
                                         self._call_hex_arg, "project", "get_dtv_version")
        self._action_btn_with_app_combo(g, "Get DTV Comment",
                                         self._call_hex_arg, "project", "get_dtv_comment")
        self._action_btn_with_app_combo(g, "Get DTV Notes",
                                         self._call_hex_arg, "project", "get_dtv_notes")
        self._action_btn_with_app_combo(g, "Get PGV Version",
                                         self._call_hex_arg, "project", "get_pgv_version")

        g = self._group(layout, "Events & Errors")
        self._action_btn(g, "Get Errors", self._call, "project", "get_errors")
        self._action_btn(g, "Get Events", self._call, "project", "get_events")

        layout.addStretch()
        self._tabs.addTab(scroll, "📁 Project")

    def _build_tab_parameters(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)

        g = self._group(layout, "Parameter Listing")
        self._action_btn_with_app_combo(g, "Get Parameters",
                                         self._call_hex_arg, "parameter", "get_parameters", 0)
        self._action_btn_with_app_combo(g, "Get Parameter Properties",
                                         self._call_hex_arg, "parameter", "get_parameter_properties", 0)
        self._action_btn_with_app_combo(g, "Get Modified Parameters",
                                         self._call_hex_arg, "parameter", "get_modified_parameters")
        self._action_btn_with_app_combo(g, "Get Parameter Groups",
                                         self._call_hex_arg, "parameter", "get_parameter_and_groups")

        g = self._group(layout, "Conversions")
        self._action_btn_with_app_combo(g, "Get Conversions",
                                         self._call_hex_arg, "parameter", "get_conversions")

        g = self._group(layout, "Values")
        self._action_btn_with_app_combo_and_input(
            g, "Get Value Scalar",
            "Param IDs (comma-sep):", "vCar",
            self._call_value_read, "parameter", "get_value_scalar",
        )
        self._action_btn_with_app_combo_and_input(
            g, "Get Value Measurement",
            "Param IDs (comma-sep):", "vCar",
            self._call_value_read, "parameter", "get_value_measurement",
        )

        g = self._group(layout, "Utility")
        self._action_btn(g, "Delete Min/Max", self._call, "parameter", "delete_min_max")

        layout.addStretch()
        self._tabs.addTab(scroll, "📊 Parameters")

    def _build_tab_logging(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)

        g = self._group(layout, "Logging Configuration")
        self._action_btn(g, "Get Channel Properties", self._call, "logging", "get_logging_channel_properties")
        self._action_btn(g, "Get Triggers", self._call, "logging", "get_logging_triggers")
        self._action_btn(g, "Get Wrap", self._call, "logging", "get_logging_wrap")
        self._action_btn(g, "Get Offset", self._call, "logging", "get_logging_offset")
        self._action_btn(g, "Get Slots Used", self._call, "logging", "get_logging_slots_used")
        self._action_btn(g, "Get ECU Config", self._call, "logging", "get_ecu_logging_config")
        self._action_btn(g, "Get Parameter Details", self._call, "logging", "get_logging_parameter_details")

        g = self._group(layout, "Config Transfer")
        self._action_btn(g, "Download In Progress?", self._call, "logging", "logging_config_download_in_progress")
        self._action_btn(g, "Upload Config", self._call, "logging", "logging_config_upload")

        layout.addStretch()
        self._tabs.addTab(scroll, "📝 Logging")

    def _build_tab_virtual(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)

        g = self._group(layout, "Virtual Parameters")
        self._action_btn(g, "Get Groups", self._call, "virtual", "get_virtual_parameter_groups")
        self._action_btn(g, "Remove All Virtual Params", self._call, "virtual", "remove_all_virtual_parameters")
        self._action_btn(g, "Remove All Virtual Conversions", self._call, "virtual", "remove_all_virtual_conversions")

        layout.addStretch()
        self._tabs.addTab(scroll, "🔧 Virtual")

    # ── UI helpers ───────────────────────────────────────────────────

    def _group(self, parent_layout: QVBoxLayout, title: str) -> QVBoxLayout:
        group = QGroupBox(title)
        group.setFont(QFont("Segoe UI", 10, QFont.Bold))
        lay = QVBoxLayout(group)
        parent_layout.addWidget(group)
        return lay

    def _action_btn(self, layout: QVBoxLayout, label: str,
                    callback: Callable, *args: Any):
        row = QHBoxLayout()
        btn = QPushButton(label)
        btn.setFixedWidth(250)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {ACCENT}; color: white; "
            f"padding: 6px 12px; border: none; border-radius: 3px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: #B84A24; }}"
        )
        btn.clicked.connect(partial(callback, *args))
        row.addWidget(btn)
        row.addStretch()
        layout.addLayout(row)

    def _action_btn_with_input(self, layout: QVBoxLayout, label: str,
                                input_label: str, default: str,
                                callback: Callable, *args: Any):
        row = QHBoxLayout()
        btn = QPushButton(label)
        btn.setFixedWidth(250)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {ACCENT}; color: white; "
            f"padding: 6px 12px; border: none; border-radius: 3px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: #B84A24; }}"
        )
        row.addWidget(btn)
        row.addWidget(QLabel(input_label))
        edit = QLineEdit(default)
        edit.setFixedWidth(120)
        row.addWidget(edit)
        row.addStretch()
        btn.clicked.connect(partial(callback, edit, *args))
        layout.addLayout(row)

    def _action_btn_with_two_inputs(self, layout: QVBoxLayout, label: str,
                                     lbl1: str, default1: str,
                                     lbl2: str, default2: str,
                                     callback: Callable, *args: Any):
        row = QHBoxLayout()
        btn = QPushButton(label)
        btn.setFixedWidth(250)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {ACCENT}; color: white; "
            f"padding: 6px 12px; border: none; border-radius: 3px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: #B84A24; }}"
        )
        row.addWidget(btn)
        row.addWidget(QLabel(lbl1))
        edit1 = QLineEdit(default1)
        edit1.setFixedWidth(100)
        row.addWidget(edit1)
        row.addWidget(QLabel(lbl2))
        edit2 = QLineEdit(default2)
        edit2.setFixedWidth(200)
        row.addWidget(edit2)
        row.addStretch()
        btn.clicked.connect(partial(callback, edit1, edit2, *args))
        layout.addLayout(row)

    def _make_app_combo(self) -> QComboBox:
        """Create an App ID combo box (editable fallback) and register for refresh."""
        combo = QComboBox()
        combo.setEditable(True)
        combo.setFixedWidth(200)
        combo.setInsertPolicy(QComboBox.NoInsert)
        combo.lineEdit().setPlaceholderText("Select or type App ID")
        self._app_combos.append(combo)
        return combo

    def _action_btn_with_app_combo(self, layout: QVBoxLayout, label: str,
                                    callback: Callable, *args: Any):
        """Button + App-ID combo box row."""
        row = QHBoxLayout()
        btn = QPushButton(label)
        btn.setFixedWidth(250)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {ACCENT}; color: white; "
            f"padding: 6px 12px; border: none; border-radius: 3px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: #B84A24; }}"
        )
        row.addWidget(btn)
        row.addWidget(QLabel("App:"))
        combo = self._make_app_combo()
        row.addWidget(combo)
        row.addStretch()
        btn.clicked.connect(partial(callback, combo, *args))
        layout.addLayout(row)

    def _action_btn_with_app_combo_and_input(self, layout: QVBoxLayout, label: str,
                                              lbl2: str, default2: str,
                                              callback: Callable, *args: Any):
        """Button + App-ID combo + a second text input row."""
        row = QHBoxLayout()
        btn = QPushButton(label)
        btn.setFixedWidth(250)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {ACCENT}; color: white; "
            f"padding: 6px 12px; border: none; border-radius: 3px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: #B84A24; }}"
        )
        row.addWidget(btn)
        row.addWidget(QLabel("App:"))
        combo = self._make_app_combo()
        row.addWidget(combo)
        row.addWidget(QLabel(lbl2))
        edit2 = QLineEdit(default2)
        edit2.setFixedWidth(200)
        row.addWidget(edit2)
        row.addStretch()
        btn.clicked.connect(partial(callback, combo, edit2, *args))
        layout.addLayout(row)

    def _refresh_app_combos(self):
        """Rebuild all App-ID combo boxes from the selected connection's app_info."""
        idx = self._conn_list.currentRow()
        if idx < 0 or idx >= len(self._store.connections):
            return
        conn = self._store.connections[idx]
        items: list[tuple[str, int]] = []  # (display_text, app_id)
        if conn.connected and conn.app_info:
            for info in conn.app_info:
                name = info.get("app_name", "?")
                aid = info.get("app_id", 0)
                items.append((f"{name}  (ID:{aid})", aid))

        new_ids = [aid for _, aid in items]

        for combo in self._app_combos:
            # Skip rebuild if the item list is unchanged
            existing_ids = [combo.itemData(i) for i in range(combo.count())]
            if existing_ids == new_ids:
                continue

            prev = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            for display, aid in items:
                combo.addItem(display, aid)
            # Restore previous selection if still valid
            if prev is not None:
                ix = combo.findData(prev)
                if ix >= 0:
                    combo.setCurrentIndex(ix)
            combo.blockSignals(False)

    # ── Connection management ────────────────────────────────────────

    def _add_connection(self):
        dlg = AddConnectionDialog(self)
        if dlg.exec() == QDialog.Accepted:
            conn = dlg.get_connection()
            self._store.add(conn)
            self._store.save()
            self._refresh_connection_list()
            self._log_info(f"Added connection: {conn.name} ({conn.address})")

    def _edit_selected(self):
        idx = self._conn_list.currentRow()
        if idx < 0 or idx >= len(self._store.connections):
            return
        conn = self._store.connections[idx]
        if conn.connected:
            QMessageBox.warning(self, "Edit Connection",
                                "Disconnect before editing.")
            return
        dlg = AddConnectionDialog(self, name=conn.name, address=conn.address,
                                  insecure=conn.insecure)
        if dlg.exec() == QDialog.Accepted:
            old_name = conn.name
            conn.name = dlg.name_edit.text().strip() or "Unnamed"
            conn.address = dlg.address_edit.text().strip() or "localhost:7000"
            conn.insecure = dlg.insecure_check.isChecked()
            conn.ca_cert = None  # reset cert in case address changed
            self._store.save()
            self._refresh_connection_list()
            self._log_info(f"Updated connection: {old_name} → {conn.name} ({conn.address})")

    def _connect_selected(self):
        idx = self._conn_list.currentRow()
        if idx < 0 or idx >= len(self._store.connections):
            return
        conn = self._store.connections[idx]
        self._log_call(f"Connecting to {conn.name} ({conn.address})...")

        def do_connect():
            # Auto-probe TLS cert
            host = conn.address.split(":")[0] if ":" in conn.address else conn.address
            port = int(conn.address.split(":")[1]) if ":" in conn.address else 7000
            if not conn.insecure and not conn.ca_cert:
                ca_pem = fetch_server_cert(host, port)
                if ca_pem:
                    conn.ca_cert = ca_pem
            conn.connect()
            return conn.connected

        def on_done(result):
            if result:
                self._log_success(f"Connected to {conn.name}")
                self._refresh_app_combos()
            else:
                self._log_error(f"Failed: {conn.error_message}")
            self._refresh_connection_list()

        t, w, b = run_in_thread(do_connect, on_success=on_done,
                             on_error=lambda e: self._log_error(e), parent=self)
        self._threads.append((t, w, b))

    def _disconnect_selected(self):
        idx = self._conn_list.currentRow()
        if idx < 0 or idx >= len(self._store.connections):
            return
        conn = self._store.connections[idx]
        conn.disconnect()
        self._log_info(f"Disconnected from {conn.name}")
        self._refresh_connection_list()

    def _remove_selected(self):
        idx = self._conn_list.currentRow()
        if idx < 0 or idx >= len(self._store.connections):
            return
        name = self._store.connections[idx].name
        self._store.remove(idx)
        self._store.save()
        self._refresh_connection_list()
        self._log_info(f"Removed connection: {name}")

    def _on_connection_selected(self, idx: int):
        if idx < 0 or idx >= len(self._store.connections):
            self._lbl_link.setText("Link: —")
            self._lbl_online.setText("Online: —")
            self._lbl_update.setText("Live Update: —")
            self._lbl_error.setText("")
            return
        self._update_status_labels(self._store.connections[idx])
        self._refresh_app_combos()

    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        self._topology.set_theme(self._dark_mode)
        self._theme_btn.setText("☀ Light" if self._dark_mode else "🌙 Dark")

    def _on_card_action(self, conn_name: str, action: str):
        """Handle interactive card actions from the topology diagram."""
        conn = next((c for c in self._store.connections if c.name == conn_name), None)
        if conn is None:
            return

        if action == "toggle_connect":
            if conn.connected:
                conn.disconnect()
                self._log_info(f"Disconnected from {conn.name}")
                self._refresh_connection_list()
            else:
                # Select this connection in the list and trigger connect
                idx = self._store.connections.index(conn)
                self._conn_list.setCurrentRow(idx)
                self._connect_selected()
            return

        if not conn.connected or not conn.client:
            return

        if action == "toggle_online":
            new_val = not conn.online

            def do_toggle():
                conn.client.system.set_online(new_val)
                conn.poll_status()
                return new_val

            def on_done(val):
                self._log_success(f"{conn.name}: Online → {'ON' if val else 'OFF'}")
                self._refresh_connection_list()

            t, w, b = run_in_thread(do_toggle, on_success=on_done,
                                    on_error=lambda e: self._log_error(e), parent=self)
            self._threads.append((t, w, b))

        elif action == "toggle_live":
            new_val = not conn.live_update

            def do_toggle():
                conn.client.system.set_live_update(new_val)
                conn.poll_status()
                return new_val

            def on_done(val):
                self._log_success(f"{conn.name}: Live Update → {'ON' if val else 'OFF'}")
                self._refresh_connection_list()

            t, w, b = run_in_thread(do_toggle, on_success=on_done,
                                    on_error=lambda e: self._log_error(e), parent=self)
            self._threads.append((t, w, b))

        elif action == "refresh_apps":
            self._log_call(f"Refreshing app info for {conn.name}...")

            def do_refresh():
                conn.fetch_app_info()
                return len(conn.app_info)

            def on_done(count):
                self._log_success(f"{conn.name}: {count} apps refreshed")
                self._refresh_app_combos()

            t, w, b = run_in_thread(do_refresh, on_success=on_done,
                                    on_error=lambda e: self._log_error(e), parent=self)
            self._threads.append((t, w, b))

    def _refresh_connection_list(self):
        current = self._conn_list.currentRow()
        self._conn_list.blockSignals(True)
        self._conn_list.clear()
        for conn in self._store.connections:
            if conn.connected:
                icon = "🟢" if conn.link_status == "LINK_OK" else "🟡"
            elif conn.failed:
                icon = "🔴"
            else:
                icon = "⚫"
            item = QListWidgetItem(f"{icon} {conn.name} — {conn.address}")
            self._conn_list.addItem(item)
        if 0 <= current < self._conn_list.count():
            self._conn_list.setCurrentRow(current)
            self._update_status_labels(self._store.connections[current])
        self._conn_list.blockSignals(False)
        self._statusbar.showMessage(
            f"{len(self._store.connections)} connection(s) | "
            f"{sum(1 for c in self._store.connections if c.connected)} connected"
        )
        self._topology.refresh()

    def _update_status_labels(self, conn: SMConnection):
        link_color = SUCCESS if conn.link_status == "LINK_OK" else ERROR
        online_color = SUCCESS if conn.online else ERROR
        update_color = SUCCESS if conn.live_update else ERROR

        self._lbl_link.setText(f"Link: {conn.link_status}")
        self._lbl_link.setStyleSheet(
            f"color: white; background-color: {link_color}; padding: 4px; border-radius: 3px;"
        )
        self._lbl_online.setText(f"Online: {'Yes' if conn.online else 'No'}")
        self._lbl_online.setStyleSheet(
            f"color: white; background-color: {online_color}; padding: 4px; border-radius: 3px;"
        )
        self._lbl_update.setText(f"Live Update: {'Yes' if conn.live_update else 'No'}")
        self._lbl_update.setStyleSheet(
            f"color: white; background-color: {update_color}; padding: 4px; border-radius: 3px;"
        )
        self._lbl_error.setText(conn.error_message)

    # ── gRPC call dispatchers ────────────────────────────────────────

    def _get_client(self):
        idx = self._conn_list.currentRow()
        if idx < 0 or idx >= len(self._store.connections):
            self._log_error("No connection selected")
            return None
        conn = self._store.connections[idx]
        if not conn.connected or not conn.client:
            self._log_error(f"{conn.name} is not connected")
            return None
        return conn.client

    def _call(self, service_name: str, method_name: str, *args: Any):
        client = self._get_client()
        if not client:
            return
        svc = getattr(client, service_name, None)
        if not svc:
            self._log_error(f"Unknown service: {service_name}")
            return
        method = getattr(svc, method_name, None)
        if not method:
            self._log_error(f"Unknown method: {service_name}.{method_name}")
            return

        self._log_call(f"{service_name}.{method_name}({', '.join(str(a) for a in args)})")

        def do_call():
            t0 = time.perf_counter()
            result = method(*args)
            elapsed = (time.perf_counter() - t0) * 1000
            return result, elapsed

        def on_done(data):
            result, elapsed = data
            self._log_success(f"Completed in {elapsed:.1f}ms")
            self._log_result(result)

        t, w, b = run_in_thread(do_call, on_success=on_done,
                             on_error=lambda e: self._log_error(e), parent=self)
        self._threads.append((t, w, b))

    def _call_and_refresh_apps(self):
        """Call get_app_details, log the result, and refresh the app combos."""
        client = self._get_client()
        if not client:
            return
        self._log_call("project.get_app_details()")

        def do_call():
            import time as _t
            t0 = _t.perf_counter()
            result = client.project.get_app_details()
            elapsed = (_t.perf_counter() - t0) * 1000
            return result, elapsed

        def on_done(data):
            result, elapsed = data
            self._log_success(f"Completed in {elapsed:.1f}ms")
            self._log_result(result)
            # Re-fetch app_info on the selected connection and refresh combos
            idx = self._conn_list.currentRow()
            if 0 <= idx < len(self._store.connections):
                conn = self._store.connections[idx]
                conn.fetch_app_info()
                self._refresh_app_combos()

        t, w, b = run_in_thread(do_call, on_success=on_done,
                             on_error=lambda e: self._log_error(e), parent=self)
        self._threads.append((t, w, b))

    def _parse_app_id(self, widget) -> int | None:
        """Extract app ID from a QComboBox (itemData) or QLineEdit (text parse)."""
        if isinstance(widget, QComboBox):
            data = widget.currentData()
            if data is not None:
                return int(data)
            # Fallback: user typed a value in the editable combo
            text = widget.currentText().strip()
        else:
            text = widget.text().strip()
        if not text:
            self._log_error("No App ID selected")
            return None
        try:
            return int(text, 16) if text.lower().startswith("0x") else int(text)
        except ValueError:
            self._log_error(f"Invalid App ID: {text}  (use decimal e.g. 3840 or hex e.g. 0xF00)")
            return None

    def _call_hex_arg(self, widget, service_name: str,
                       method_name: str, *extra_args: Any):
        """Parse app ID from combo or text input, then call the gRPC method."""
        val = self._parse_app_id(widget)
        if val is None:
            return
        all_args = (val,) + extra_args
        self._call(service_name, method_name, *all_args)

    def _call_value_read(self, widget_app, edit_params: QLineEdit,
                          service_name: str, method_name: str):
        app_id = self._parse_app_id(widget_app)
        if app_id is None:
            return
        param_ids = [p.strip() for p in edit_params.text().split(",") if p.strip()]
        if not param_ids:
            self._log_error("No parameter IDs specified")
            return
        self._call(service_name, method_name, app_id, param_ids)

    # ── Output log ───────────────────────────────────────────────────

    def _log(self, text: str, color: str):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self._output.append(
            f'<span style="color:{MUTED}">[{ts}]</span> '
            f'<span style="color:{color}">{text}</span>'
        )
        self._output.verticalScrollBar().setValue(
            self._output.verticalScrollBar().maximum()
        )

    def _log_call(self, text: str):
        self._log(f"→ {text}", "#569cd6")

    def _log_success(self, text: str):
        self._log(f"✓ {text}", SUCCESS)

    def _log_error(self, text: str):
        self._log(f"✗ {text}", ERROR)

    def _log_info(self, text: str):
        self._log(text, "#d4d4d4")

    def _log_result(self, result: Any):
        """Format and log a gRPC result."""
        if result is None:
            self._log("  (void)", MUTED)
            return
        text = str(result)
        if hasattr(result, "__len__") and not isinstance(result, str):
            count = len(result)
            if count > 20:
                # Truncate long lists
                items = []
                for item in list(result)[:20]:
                    items.append(str(item).replace("\n", " ")[:120])
                text = f"[{count} items]\n" + "\n".join(f"  {i}" for i in items) + "\n  ..."
            else:
                items = []
                for item in result:
                    items.append(str(item).replace("\n", " ")[:120])
                text = f"[{count} items]\n" + "\n".join(f"  {i}" for i in items)
        else:
            text = str(result).replace("\n", " | ")[:500]
        # Escape HTML
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace("\n", "<br>")
        self._log(f"  {text}", "#d4d4d4")

    # ── Cleanup ──────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._poller.stop()
        self._poller_thread.quit()
        self._poller_thread.wait(2000)
        self._store.disconnect_all()
        self._store.save()
        super().closeEvent(event)


# ── Entry point ──────────────────────────────────────────────────────────
def main():
    logging.basicConfig(level=logging.WARNING)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
