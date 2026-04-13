"""Live topology diagram — shows SM connections as draggable cards.

A central "SM Config API" hub connects via Bezier curves to each System
Monitor card. Cards show name, address, and colour-coded Link / Online /
Live Update status. Cards can be dragged to rearrange the layout.
Supports light and dark themes toggled at runtime.

Interactive card controls:
- Power button (top-right): connect / disconnect
- Online pill: toggle set_online
- Live pill: toggle set_live_update
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QWidget, QToolTip

if TYPE_CHECKING:
    from gui.connection_manager import ConnectionStore

# ── Theme dataclass ───────────────────────────────────────────────────────

@dataclass
class TopologyTheme:
    name: str
    bg: QColor
    hub_grad_start: QColor
    hub_grad_end: QColor
    hub_border: QColor
    card_bg: QColor
    card_border: QColor
    card_border_active: QColor
    card_shadow: QColor
    line_active: QColor
    line_inactive: QColor
    green: QColor
    red: QColor
    yellow: QColor
    grey: QColor
    text: QColor
    text_muted: QColor
    white: QColor


THEME_LIGHT = TopologyTheme(
    name="light",
    bg=QColor("#f7f8fa"),
    hub_grad_start=QColor("#D4572A"),
    hub_grad_end=QColor("#B84A24"),
    hub_border=QColor("#A3401F"),
    card_bg=QColor("#ffffff"),
    card_border=QColor("#d2d2d2"),
    card_border_active=QColor("#D4572A"),
    card_shadow=QColor(0, 0, 0, 30),
    line_active=QColor("#D4572A"),
    line_inactive=QColor("#cccccc"),
    green=QColor("#107c10"),
    red=QColor("#d13438"),
    yellow=QColor("#ff8c00"),
    grey=QColor("#8a8886"),
    text=QColor("#323130"),
    text_muted=QColor("#605e5c"),
    white=QColor("#ffffff"),
)

THEME_DARK = TopologyTheme(
    name="dark",
    bg=QColor("#1e1e1e"),
    hub_grad_start=QColor("#C0522A"),
    hub_grad_end=QColor("#8C3C1F"),
    hub_border=QColor("#D4572A"),
    card_bg=QColor("#2d2d2d"),
    card_border=QColor("#444444"),
    card_border_active=QColor("#D4572A"),
    card_shadow=QColor(0, 0, 0, 60),
    line_active=QColor("#D4572A"),
    line_inactive=QColor("#555555"),
    green=QColor("#2ea043"),
    red=QColor("#f85149"),
    yellow=QColor("#d29922"),
    grey=QColor("#6e6e6e"),
    text=QColor("#e0e0e0"),
    text_muted=QColor("#a0a0a0"),
    white=QColor("#ffffff"),
)


# ── Fonts ─────────────────────────────────────────────────────────────────
FONT_TITLE = QFont("Segoe UI", 11, QFont.Bold)
FONT_ADDR = QFont("Cascadia Mono", 9)
FONT_STATUS = QFont("Segoe UI", 9, QFont.Bold)
FONT_HUB = QFont("Segoe UI", 13, QFont.Bold)
FONT_HUB_SUB = QFont("Segoe UI", 9)

CARD_W = 230
CARD_H_BASE = 120       # base height without app info
CARD_H_APP_ROW = 16     # height per application row
CARD_H_APP_HDR = 22     # header gap before app section
HUB_W = 160
HUB_H = 80

# Clickable regions within a card (offsets from card top-left)
_POWER_BTN = QRectF(CARD_W - 30, 10, 20, 20)      # top-right power button
_REFRESH_BTN = QRectF(CARD_W - 54, 10, 20, 20)    # refresh button left of power
_ONLINE_PILL_Y = 82                                  # y offset for Online pill
_LIVE_PILL_Y = 82                                    # y offset for Live pill
_PILL_H = 18
DRAG_THRESHOLD = 5  # pixels — below this a release counts as a click
FONT_APP = QFont("Cascadia Mono", 7.5)


class TopologyDiagram(QWidget):
    """Custom-painted live topology diagram with draggable SM cards."""

    # Emitted when user clicks an action on a card: (connection_name, action)
    # Actions: "toggle_connect", "toggle_online", "toggle_live", "refresh_apps"
    card_action = Signal(str, str)

    def __init__(self, store: "ConnectionStore", parent=None):
        super().__init__(parent)
        self._store = store
        self._theme: TopologyTheme = THEME_LIGHT
        self.setMinimumSize(500, 300)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.setMouseTracking(True)

        # Drag state
        self._card_positions: dict[str, QPointF] = {}   # name → top-left
        self._hub_pos: QPointF | None = None             # hub top-left (draggable too)
        self._dragging: str | None = None                # name of card being dragged, or "__hub__"
        self._drag_offset = QPointF(0, 0)
        self._press_pos: QPointF | None = None           # mouse-down position for click detection
        self._press_card: str | None = None              # card name where press occurred

    # ── Public API ───────────────────────────────────────────────────

    def refresh(self):
        """Trigger a repaint (call from the status poller signal)."""
        self.update()

    def set_theme(self, dark: bool):
        """Switch between light and dark themes."""
        self._theme = THEME_DARK if dark else THEME_LIGHT
        self.update()

    def reset_layout(self):
        """Clear all manual positions and return to auto-layout."""
        self._card_positions.clear()
        self._hub_pos = None
        self.update()

    # ── Auto-layout helpers ──────────────────────────────────────────

    @staticmethod
    def _card_height(conn) -> float:
        """Compute card height: base + app rows when available."""
        if conn.connected and conn.app_info:
            return CARD_H_BASE + CARD_H_APP_HDR + len(conn.app_info) * CARD_H_APP_ROW
        return CARD_H_BASE

    def _default_hub_pos(self) -> QPointF:
        return QPointF(self.width() / 2 - HUB_W / 2, 20)

    def _default_card_positions(self, n: int) -> list[QPointF]:
        """Compute horizontal layout for n cards below the hub."""
        if n == 0:
            return []
        hub = self._hub_pos if self._hub_pos else self._default_hub_pos()
        card_y = hub.y() + HUB_H + 80  # vertical gap below hub
        gap = 24  # horizontal gap between cards
        total_w = n * CARD_W + (n - 1) * gap
        start_x = max(20, (self.width() - total_w) / 2)
        return [QPointF(start_x + i * (CARD_W + gap), card_y) for i in range(n)]

    def _get_card_pos(self, name: str, default: QPointF) -> QPointF:
        """Return stored position or the auto-layout default."""
        return self._card_positions.get(name, default)

    # ── Mouse events for drag-and-drop + click actions ─────────────

    def _find_card_at(self, pos: QPointF) -> tuple[str | None, QPointF | None]:
        """Return (name, card_top_left) of card under pos, or (None, None)."""
        conns = self._store.connections
        defaults = self._default_card_positions(len(conns))
        for i in range(len(conns) - 1, -1, -1):
            cp = self._get_card_pos(conns[i].name, defaults[i])
            ch = self._card_height(conns[i])
            if QRectF(cp.x(), cp.y(), CARD_W, ch).contains(pos):
                return conns[i].name, cp
        return None, None

    def _hit_test_action(self, pos: QPointF, card_pos: QPointF, conn_name: str) -> str | None:
        """Check if pos hits a clickable control inside a card. Returns action or None."""
        local = pos - card_pos  # position relative to card top-left

        # Power button (top-right corner)
        if _POWER_BTN.contains(local):
            return "toggle_connect"

        # Find the connection to get pill widths
        conn = next((c for c in self._store.connections if c.name == conn_name), None)
        if not conn or not conn.connected:
            return None

        # Refresh button (left of power button)
        if _REFRESH_BTN.contains(local):
            return "refresh_apps"

        # Online pill region
        online_text = " Online: ON " if conn.online else " Online: OFF "
        fm = QFontMetrics(FONT_STATUS)
        online_w = fm.horizontalAdvance(online_text) + 8
        online_rect = QRectF(12, _ONLINE_PILL_Y, online_w, _PILL_H)
        if online_rect.contains(local):
            return "toggle_online"

        # Live pill region
        live_text = " Live: ON " if conn.live_update else " Live: OFF "
        live_w = fm.horizontalAdvance(live_text) + 8
        live_rect = QRectF(120, _LIVE_PILL_Y, live_w, _PILL_H)
        if live_rect.contains(local):
            return "toggle_live"

        return None

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)

        pos = event.position()
        self._press_pos = pos

        # Check hub hit
        hub = self._hub_pos if self._hub_pos else self._default_hub_pos()
        hub_rect = QRectF(hub.x(), hub.y(), HUB_W, HUB_H)
        if hub_rect.contains(pos):
            self._dragging = "__hub__"
            self._press_card = None
            self._drag_offset = pos - hub
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            return

        # Check card hits
        name, cp = self._find_card_at(pos)
        if name is not None:
            self._dragging = name
            self._press_card = name
            self._drag_offset = pos - cp
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            return

        self._press_card = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging:
            new_pos = event.position() - self._drag_offset
            if self._dragging == "__hub__":
                self._hub_pos = new_pos
            else:
                self._card_positions[self._dragging] = new_pos
            self.update()
            QToolTip.hideText()
            return

        # Hover cursor + tooltip
        pos = event.position()
        hub = self._hub_pos if self._hub_pos else self._default_hub_pos()
        if QRectF(hub.x(), hub.y(), HUB_W, HUB_H).contains(pos):
            self.setCursor(QCursor(Qt.OpenHandCursor))
            QToolTip.hideText()
            return

        name, cp = self._find_card_at(pos)
        if name is not None:
            action = self._hit_test_action(pos, cp, name)
            if action:
                self.setCursor(QCursor(Qt.PointingHandCursor))
                QToolTip.hideText()
            else:
                self.setCursor(QCursor(Qt.OpenHandCursor))
                # Only show tooltip when hovering the app-info section of the card
                conn = next((c for c in self._store.connections if c.name == name), None)
                local_y = pos.y() - cp.y()
                if conn and conn.connected and conn.app_info and local_y >= CARD_H_BASE:
                    self._show_card_tooltip(conn, event.globalPosition().toPoint())
                elif conn and conn.failed and conn.error_message:
                    QToolTip.showText(event.globalPosition().toPoint(),
                                      f"<b>Error:</b> {conn.error_message}", self)
                else:
                    QToolTip.hideText()
            return

        self.setCursor(QCursor(Qt.ArrowCursor))
        QToolTip.hideText()

    def _show_card_tooltip(self, conn, global_pos):
        """Build and display a rich HTML tooltip for a connected card."""
        rows = []
        for info in conn.app_info:
            name = info.get("app_name", "?")
            pgv = info.get("pgv_id")
            dtv = info.get("dtv_version")
            pgv_str = str(pgv) if pgv is not None else "--"
            dtv_str = dtv if dtv else "--"
            rows.append(
                f"<tr>"
                f"<td style='padding:2px 10px 2px 0;white-space:nowrap;'><b>{name}</b></td>"
                f"<td style='padding:2px 10px;white-space:nowrap;color:#888;'>PGV: {pgv_str}</td>"
                f"<td style='padding:2px 10px;white-space:nowrap;color:#888;'>DTV: {dtv_str}</td>"
                f"</tr>"
            )
        html = (
            f"<div style='font-family:Segoe UI,sans-serif;font-size:9pt;white-space:nowrap;'>"
            f"<b>{conn.name}</b> &mdash; {conn.address}<br>"
            f"<table cellspacing='0' style='margin-top:4px;'>"
            f"<tr style='color:#555;'>"
            f"<td style='padding:2px 10px 2px 0;white-space:nowrap;'><u>Application</u></td>"
            f"<td style='padding:2px 10px;white-space:nowrap;'><u>PGV ID</u></td>"
            f"<td style='padding:2px 10px;white-space:nowrap;'><u>DTV Version</u></td>"
            f"</tr>"
            + "\n".join(rows) +
            f"</table></div>"
        )
        QToolTip.showText(global_pos, html, self)

    def mouseReleaseEvent(self, event):
        if self._dragging:
            was_dragging = self._dragging
            press_pos = self._press_pos
            release_pos = event.position()
            self._dragging = None
            self.setCursor(QCursor(Qt.ArrowCursor))

            # If mouse barely moved, treat as click and check for action hits
            if (press_pos is not None and was_dragging != "__hub__"
                    and (release_pos - press_pos).manhattanLength() < DRAG_THRESHOLD):
                # Undo the tiny drag
                name = was_dragging
                conns = self._store.connections
                defaults = self._default_card_positions(len(conns))
                idx = next((i for i, c in enumerate(conns) if c.name == name), None)
                if idx is not None:
                    # Restore to original position (remove from manual if was auto)
                    if name in self._card_positions:
                        # Undo the micro-move
                        self._card_positions[name] = press_pos - self._drag_offset
                    cp = self._get_card_pos(name, defaults[idx])
                    action = self._hit_test_action(release_pos, cp, name)
                    if action:
                        self.card_action.emit(name, action)
                        self.update()
                        return

            self._press_pos = None
            self._press_card = None
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Double-click on empty space resets layout."""
        pos = event.position()
        hub = self._hub_pos if self._hub_pos else self._default_hub_pos()
        if QRectF(hub.x(), hub.y(), HUB_W, HUB_H).contains(pos):
            return
        conns = self._store.connections
        defaults = self._default_card_positions(len(conns))
        for i, conn in enumerate(conns):
            cp = self._get_card_pos(conn.name, defaults[i])
            ch = self._card_height(conn)
            if QRectF(cp.x(), cp.y(), CARD_W, ch).contains(pos):
                return
        self.reset_layout()

    # ── Painting ─────────────────────────────────────────────────────

    def paintEvent(self, event):
        t = self._theme
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        # Background
        painter.fillRect(self.rect(), t.bg)

        connections = self._store.connections
        n = len(connections)

        # Hub position
        hub = self._hub_pos if self._hub_pos else self._default_hub_pos()
        hub_bottom_center = QPointF(hub.x() + HUB_W / 2, hub.y() + HUB_H)

        # Draw hub
        self._draw_hub(painter, hub.x(), hub.y(), n)

        if n == 0:
            painter.setFont(QFont("Segoe UI", 11))
            painter.setPen(t.text_muted)
            painter.drawText(
                QRectF(hub.x() - 70, hub.y() + HUB_H + 20, HUB_W + 140, 40),
                Qt.AlignHCenter | Qt.AlignVCenter,
                "Add a connection to see it here",
            )
            painter.end()
            return

        # Card positions
        defaults = self._default_card_positions(n)

        for i, conn in enumerate(connections):
            cp = self._get_card_pos(conn.name, defaults[i])
            card_top_center = QPointF(cp.x() + CARD_W / 2, cp.y())
            self._draw_line(painter, hub_bottom_center, card_top_center,
                            conn.connected, conn.failed)
            self._draw_card(painter, cp.x(), cp.y(), conn)

        painter.end()

    def _draw_hub(self, painter: QPainter, x: float, y: float, conn_count: int):
        t = self._theme
        rect = QRectF(x, y, HUB_W, HUB_H)

        # Shadow
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 25))
        painter.drawRoundedRect(rect.translated(2, 2), 12, 12)

        # Gradient fill
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0, t.hub_grad_start)
        grad.setColorAt(1, t.hub_grad_end)
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(t.hub_border, 1.5))
        painter.drawRoundedRect(rect, 12, 12)

        # Text
        painter.setPen(t.white)
        painter.setFont(FONT_HUB)
        painter.drawText(rect.adjusted(0, 8, 0, -16), Qt.AlignHCenter | Qt.AlignTop, "⚙ SM gRPC API")
        painter.setFont(FONT_HUB_SUB)
        painter.drawText(
            rect.adjusted(0, 16, 0, -4),
            Qt.AlignHCenter | Qt.AlignBottom,
            f"{conn_count} connection{'s' if conn_count != 1 else ''}",
        )

    def _draw_line(self, painter: QPainter, start: QPointF, end: QPointF,
                   active: bool, failed: bool = False):
        t = self._theme
        if active:
            color = t.line_active
        elif failed:
            color = t.red
        else:
            color = t.line_inactive
        pen = QPen(color, 2.5 if active else 1.5)
        pen.setStyle(Qt.SolidLine if (active or failed) else Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        # Vertical Bezier: hub bottom-centre → card top-centre
        path = QPainterPath(start)
        mid_y = (start.y() + end.y()) / 2
        path.cubicTo(QPointF(start.x(), mid_y), QPointF(end.x(), mid_y), end)
        painter.drawPath(path)

        if active:
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(end, 4, 4)

    def _draw_card(self, painter: QPainter, x: float, y: float, conn):
        t = self._theme
        ch = self._card_height(conn)
        rect = QRectF(x, y, CARD_W, ch)

        # Shadow
        painter.setPen(Qt.NoPen)
        painter.setBrush(t.card_shadow)
        painter.drawRoundedRect(rect.translated(2, 3), 8, 8)

        # Background
        painter.setBrush(t.card_bg)
        if conn.connected:
            border = t.card_border_active
        elif conn.failed:
            border = t.red
        else:
            border = t.card_border
        painter.setPen(QPen(border, 1.5))
        painter.drawRoundedRect(rect, 8, 8)

        # Top accent bar
        if conn.connected and conn.link_status == "LINK_OK":
            accent = t.green
        elif conn.connected:
            accent = t.yellow
        elif conn.failed:
            accent = t.red
        else:
            accent = t.grey
        painter.setPen(Qt.NoPen)
        painter.setBrush(accent)
        painter.drawRoundedRect(QRectF(x + 1, y + 1, CARD_W - 2, 4), 2, 2)

        # Power button (top-right)
        pw_rect = QRectF(x + _POWER_BTN.x(), y + _POWER_BTN.y(),
                         _POWER_BTN.width(), _POWER_BTN.height())
        pw_color = t.green if conn.connected else (t.red if conn.failed else t.grey)
        painter.setBrush(pw_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(pw_rect, 4, 4)
        painter.setPen(t.white)
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(pw_rect, Qt.AlignCenter, "\u23FB")  # power symbol ⏻

        # Refresh button (left of power, only when connected)
        if conn.connected:
            rf_rect = QRectF(x + _REFRESH_BTN.x(), y + _REFRESH_BTN.y(),
                             _REFRESH_BTN.width(), _REFRESH_BTN.height())
            painter.setBrush(t.hub_grad_start)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rf_rect, 4, 4)
            painter.setPen(t.white)
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(rf_rect, Qt.AlignCenter, "\u21BB")  # ↻

        # Name — leave room for buttons
        name_max_w = CARD_W - 72 if conn.connected else CARD_W - 48
        painter.setPen(t.text)
        painter.setFont(FONT_TITLE)
        fm = QFontMetrics(FONT_TITLE)
        elided = fm.elidedText(conn.name, Qt.ElideRight, int(name_max_w))
        painter.drawText(QRectF(x + 12, y + 12, name_max_w, 22),
                         Qt.AlignLeft | Qt.AlignVCenter, elided)

        # Address
        painter.setPen(t.text_muted)
        painter.setFont(FONT_ADDR)
        painter.drawText(QRectF(x + 12, y + 34, CARD_W - 24, 18),
                         Qt.AlignLeft | Qt.AlignVCenter, conn.address)

        # Status pills — Link is read-only, Online and Live are clickable
        py = y + 60
        self._draw_pill(painter, x + 12, py, "Link", conn.link_status,
                        conn.connected and conn.link_status == "LINK_OK")
        self._draw_pill(painter, x + 12, py + 22, "Online",
                        "ON" if conn.online else "OFF", conn.online,
                        clickable=conn.connected)
        self._draw_pill(painter, x + 120, py + 22, "Live",
                        "ON" if conn.live_update else "OFF", conn.live_update,
                        clickable=conn.connected)

        # ── Application info section ────────────────────────────────
        if conn.connected and conn.app_info:
            app_y = y + CARD_H_BASE + 6

            # Thin separator line
            painter.setPen(QPen(t.card_border, 0.5))
            painter.drawLine(QPointF(x + 12, app_y - 4), QPointF(x + CARD_W - 12, app_y - 4))

            # Section header
            painter.setPen(t.text_muted)
            painter.setFont(QFont("Segoe UI", 7.5, QFont.Bold))
            n_apps = len(conn.app_info)
            painter.drawText(QRectF(x + 12, app_y, CARD_W - 24, 14),
                             Qt.AlignLeft | Qt.AlignVCenter,
                             f"Applications ({n_apps})")
            app_y += 16

            # Per-app rows
            painter.setFont(FONT_APP)
            fm_app = QFontMetrics(FONT_APP)
            for info in conn.app_info:
                name = info.get("app_name", "?")
                pgv = info.get("pgv_id")
                dtv = info.get("dtv_version")
                pgv_str = str(pgv) if pgv is not None else "--"
                dtv_str = dtv if dtv else "--"

                # App name (bold accent)
                painter.setPen(t.text)
                label = fm_app.elidedText(name, Qt.ElideRight, 65)
                painter.drawText(QRectF(x + 14, app_y, 68, CARD_H_APP_ROW),
                                 Qt.AlignLeft | Qt.AlignVCenter, label)

                # PGV/DTV values
                painter.setPen(t.text_muted)
                detail = f"PGV:{pgv_str}  DTV:{dtv_str}"
                detail = fm_app.elidedText(detail, Qt.ElideRight, CARD_W - 98)
                painter.drawText(QRectF(x + 82, app_y, CARD_W - 96, CARD_H_APP_ROW),
                                 Qt.AlignLeft | Qt.AlignVCenter, detail)
                app_y += CARD_H_APP_ROW

    def _draw_pill(self, painter: QPainter, x: float, y: float,
                   label: str, value: str, is_ok: bool, clickable: bool = False):
        t = self._theme
        bg = t.green if is_ok else t.red
        display_val = value if len(value) <= 12 else value[:10] + "…"
        text = f" {label}: {display_val} "

        painter.setFont(FONT_STATUS)
        fm = QFontMetrics(FONT_STATUS)
        tw = fm.horizontalAdvance(text) + 8
        th = 18

        pill_rect = QRectF(x, y, tw, th)
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(pill_rect, 9, 9)

        # Clickable affordance — subtle dotted border
        if clickable:
            painter.setPen(QPen(t.white, 1.0, Qt.DotLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(pill_rect.adjusted(0.5, 0.5, -0.5, -0.5), 9, 9)

        painter.setPen(t.white)
        painter.setBrush(Qt.NoBrush)
        painter.drawText(pill_rect, Qt.AlignCenter, text)
