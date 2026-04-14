"""Minimal PDF report generation for dashboard analysis downloads."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from app.schemas import (
    AnalysisDashboardResponse,
    ChartDatum,
    MetricInsight,
    OeeLineInsight,
)

PAGE_WIDTH = 612
PAGE_HEIGHT = 792
MARGIN = 48
CONTENT_WIDTH = PAGE_WIDTH - (MARGIN * 2)

STATUS_COLORS = {
    "stable": "#3D7A58",
    "watch": "#C9A227",
    "alert": "#9F1D1D",
}


def build_report_filename(source_name: str | None) -> str:
    """Return a safe attachment filename for the generated report."""

    stem = Path(source_name or "manufacturing-analysis").stem
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("._-")
    if not safe_stem:
        safe_stem = "manufacturing-analysis"
    return f"{safe_stem}-report.pdf"


def _hex_to_rgb(color: str) -> tuple[float, float, float]:
    color = color.lstrip("#")
    return tuple(int(color[index : index + 2], 16) / 255 for index in (0, 2, 4))


def _escape_text(value: str) -> str:
    safe = value.encode("latin-1", "replace").decode("latin-1")
    return (
        safe.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def _wrap_text(text: str, max_chars: int) -> list[str]:
    words = " ".join(text.split()).split(" ")
    if not words or words == [""]:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _format_value(value: float) -> str:
    rounded = round(value, 2)
    if float(rounded).is_integer():
        return str(int(rounded))
    return f"{rounded:.2f}"


def _format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


@dataclass
class _PdfPage:
    commands: list[str] = field(default_factory=list)


class _PdfBuilder:
    def __init__(self) -> None:
        self.pages = [_PdfPage()]
        self.cursor_y = PAGE_HEIGHT - MARGIN

    @property
    def page(self) -> _PdfPage:
        return self.pages[-1]

    def new_page(self) -> None:
        self.pages.append(_PdfPage())
        self.cursor_y = PAGE_HEIGHT - MARGIN

    def ensure_space(self, height: float) -> None:
        if self.cursor_y - height < MARGIN:
            self.new_page()

    def emit(self, command: str) -> None:
        self.page.commands.append(command)

    def rect(self, x: float, y: float, width: float, height: float, color: str) -> None:
        red, green, blue = _hex_to_rgb(color)
        self.emit(
            f"{red:.3f} {green:.3f} {blue:.3f} rg "
            f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re f"
        )

    def stroke_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: str,
        line_width: float = 1.0,
    ) -> None:
        red, green, blue = _hex_to_rgb(color)
        self.emit(
            f"{line_width:.2f} w {red:.3f} {green:.3f} {blue:.3f} RG "
            f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re S"
        )

    def text(
        self,
        x: float,
        y: float,
        value: str,
        *,
        size: float = 12,
        font: str = "F1",
        color: str = "#0F172A",
    ) -> None:
        red, green, blue = _hex_to_rgb(color)
        self.emit(
            "BT "
            f"{red:.3f} {green:.3f} {blue:.3f} rg "
            f"/{font} {size:.2f} Tf "
            f"1 0 0 1 {x:.2f} {y:.2f} Tm "
            f"({_escape_text(value)}) Tj "
            "ET"
        )

    def wrapped_text(
        self,
        value: str,
        *,
        x: float = MARGIN,
        width: float = CONTENT_WIDTH,
        size: float = 12,
        font: str = "F1",
        color: str = "#0F172A",
        leading: float | None = None,
    ) -> None:
        line_height = leading or size * 1.35
        max_chars = max(18, int(width / max(size * 0.53, 1)))
        for line in _wrap_text(value, max_chars):
            self.ensure_space(line_height + 2)
            self.text(x, self.cursor_y, line, size=size, font=font, color=color)
            self.cursor_y -= line_height

    def section_header(self, title: str) -> None:
        self.ensure_space(34)
        self.text(MARGIN, self.cursor_y, title, size=15, font="F2", color="#11233D")
        self.cursor_y -= 10
        self.rect(MARGIN, self.cursor_y, CONTENT_WIDTH, 2, "#D7DEE7")
        self.cursor_y -= 18

    def summary_cards(self, items: list[tuple[str, str]]) -> None:
        card_gap = 12
        card_width = (CONTENT_WIDTH - (card_gap * (len(items) - 1))) / len(items)
        card_height = 62

        self.ensure_space(card_height + 20)
        base_y = self.cursor_y - card_height
        for index, (label, value) in enumerate(items):
            x = MARGIN + (index * (card_width + card_gap))
            self.rect(x, base_y, card_width, card_height, "#F4F0E8")
            self.stroke_rect(x, base_y, card_width, card_height, "#D5C7B7")
            self.text(x + 14, base_y + 40, label, size=10, color="#6B5E52")
            self.text(x + 14, base_y + 18, value, size=19, font="F2", color="#11233D")
        self.cursor_y = base_y - 22

    def metric_cards(self, cards: list[MetricInsight]) -> None:
        card_gap = 12
        card_width = (CONTENT_WIDTH - (card_gap * (len(cards) - 1))) / len(cards)
        card_height = 92

        self.ensure_space(card_height + 22)
        base_y = self.cursor_y - card_height
        for index, card in enumerate(cards):
            x = MARGIN + (index * (card_width + card_gap))
            accent = STATUS_COLORS[card.status]
            self.rect(x, base_y, card_width, card_height, "#FCFBF8")
            self.stroke_rect(x, base_y, card_width, card_height, "#D7DEE7")
            self.rect(x, base_y + card_height - 8, card_width, 8, accent)
            self.text(x + 12, base_y + 64, card.label, size=12, font="F2", color="#11233D")
            self.text(
                x + 12,
                base_y + 48,
                f"Peak {card.max_value} {card.unit}",
                size=10,
                color="#334155",
            )
            self.text(
                x + 12,
                base_y + 34,
                f"Threshold {card.threshold} {card.unit}",
                size=10,
                color="#334155",
            )
            self.text(
                x + 12,
                base_y + 20,
                f"Breaches {card.breach_count}",
                size=10,
                color="#334155",
            )
        self.cursor_y = base_y - 22

    def bar_chart(self, title: str, items: list[ChartDatum]) -> None:
        self.section_header(title)
        chart_items = items or [ChartDatum(label="No data", value=0, color="#CBD5E1")]
        max_value = max((item.value for item in chart_items), default=0) or 1
        bar_height = 10
        for item in chart_items:
            self.ensure_space(30)
            self.text(MARGIN, self.cursor_y, item.label, size=11, color="#334155")
            self.text(
                PAGE_WIDTH - MARGIN - 24,
                self.cursor_y,
                _format_value(item.value),
                size=11,
                font="F2",
                color="#11233D",
            )
            bar_y = self.cursor_y - 12
            self.rect(MARGIN, bar_y, CONTENT_WIDTH, bar_height, "#E5E7EB")
            fill_width = CONTENT_WIDTH * (item.value / max_value)
            self.rect(MARGIN, bar_y, fill_width, bar_height, item.color or "#1F6AA5")
            self.cursor_y -= 28
        self.cursor_y -= 8

    def bullet_list(self, items: list[str]) -> None:
        for item in items:
            self.ensure_space(18)
            self.text(MARGIN + 6, self.cursor_y, "-", size=11, font="F2", color="#C65D2E")
            self.wrapped_text(
                item,
                x=MARGIN + 20,
                width=CONTENT_WIDTH - 20,
                size=11,
                color="#334155",
            )
            self.cursor_y -= 6

    def build(self) -> bytes:
        objects: dict[int, bytes] = {
            1: b"<< /Type /Catalog /Pages 2 0 R >>",
            3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        }

        kids: list[str] = []
        for index, page in enumerate(self.pages):
            page_id = 5 + (index * 2)
            content_id = page_id + 1
            kids.append(f"{page_id} 0 R")
            stream = "\n".join(page.commands).encode("latin-1", "replace")
            objects[page_id] = (
                "<< /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                "/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            ).encode("latin-1")
            objects[content_id] = (
                f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
                + stream
                + b"\nendstream"
            )

        objects[2] = (
            f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(self.pages)} >>"
        ).encode("latin-1")

        max_object_id = max(objects)
        chunks: list[bytes] = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
        offsets = [0] * (max_object_id + 1)
        for object_id in range(1, max_object_id + 1):
            offsets[object_id] = sum(len(chunk) for chunk in chunks)
            chunks.append(f"{object_id} 0 obj\n".encode("latin-1"))
            chunks.append(objects[object_id])
            chunks.append(b"\nendobj\n")

        startxref = sum(len(chunk) for chunk in chunks)
        chunks.append(f"xref\n0 {max_object_id + 1}\n".encode("latin-1"))
        chunks.append(b"0000000000 65535 f \n")
        for object_id in range(1, max_object_id + 1):
            chunks.append(f"{offsets[object_id]:010d} 00000 n \n".encode("latin-1"))
        chunks.append(
            (
                f"trailer\n<< /Size {max_object_id + 1} /Root 1 0 R >>\n"
                f"startxref\n{startxref}\n%%EOF"
            ).encode("latin-1")
        )
        return b"".join(chunks)


def render_dashboard_pdf(dashboard: AnalysisDashboardResponse) -> bytes:
    """Render a downloadable PDF report from the UI dashboard payload."""

    builder = _PdfBuilder()
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    header_height = 92
    header_bottom = PAGE_HEIGHT - MARGIN - header_height
    builder.rect(MARGIN, header_bottom, CONTENT_WIDTH, header_height, "#11233D")
    builder.text(
        MARGIN + 18,
        header_bottom + 60,
        "Manufacturing Analysis Report",
        size=22,
        font="F2",
        color="#F8FAFC",
    )
    builder.text(
        MARGIN + 18,
        header_bottom + 38,
        f"Source: {dashboard.source_name or 'Uploaded dataset'}",
        size=11,
        color="#E2E8F0",
    )
    builder.text(
        MARGIN + 18,
        header_bottom + 22,
        f"Thread: {dashboard.thread_id}",
        size=10,
        color="#CBD5E1",
    )
    builder.text(
        MARGIN + 18,
        header_bottom + 8,
        f"Generated: {generated_at}",
        size=10,
        color="#CBD5E1",
    )
    builder.cursor_y = header_bottom - 24

    issue_count = len(dashboard.analysis_result.issues)
    builder.summary_cards(
        [
            ("Records", str(dashboard.plant_snapshot.record_count)),
            ("Machines", str(dashboard.plant_snapshot.machine_count)),
            ("Issues", str(issue_count)),
            ("Confidence", f"{round(dashboard.analysis_result.confidence_score * 100)}%"),
        ]
    )

    critical_count = next(
        (
            int(item.value)
            for item in dashboard.severity_breakdown
            if item.label.lower() == "critical"
        ),
        0,
    )

    builder.section_header("Threshold Overview")
    builder.metric_cards(dashboard.metric_cards)

    if dashboard.oee_summary and dashboard.oee_summary.available and dashboard.oee_summary.overall:
        overall_oee = dashboard.oee_summary.overall
        builder.section_header("OEE Snapshot")
        builder.summary_cards(
            [
                ("OEE", _format_percent(overall_oee.oee)),
                ("Availability", _format_percent(overall_oee.availability)),
                ("Performance", _format_percent(overall_oee.performance)),
                ("Quality", _format_percent(overall_oee.quality)),
            ]
        )
        builder.wrapped_text(
            dashboard.oee_summary.narrative,
            size=11,
            color="#334155",
            leading=15,
        )
        builder.cursor_y -= 8
        builder.section_header("Line OEE Ranking")
        if dashboard.oee_summary.line_breakdown:
            builder.bullet_list(
                [_format_oee_line(line) for line in dashboard.oee_summary.line_breakdown]
            )
        else:
            builder.wrapped_text(
                "No `line_id` values were supplied, so only plant-level OEE is shown.",
                size=11,
                color="#334155",
            )

    builder.bar_chart("Issue Mix", dashboard.issue_breakdown)
    builder.bar_chart("Severity Profile", dashboard.severity_breakdown)

    builder.section_header("Operational Analysis")
    builder.wrapped_text(
        dashboard.analysis_result.analysis,
        size=11.5,
        color="#334155",
        leading=15,
    )
    if critical_count:
        builder.cursor_y -= 4
        builder.wrapped_text(
            f"Critical issue buckets detected: {critical_count}.",
            size=10.5,
            font="F2",
            color="#9F1D1D",
        )
    builder.cursor_y -= 10

    builder.section_header("Recommended Actions")
    for solution in dashboard.analysis_result.solutions:
        title = str(solution.get("title") or solution.get("action") or "Recommended action")
        priority = str(solution.get("priority", "unspecified")).upper()
        rationale = str(
            solution.get("rationale")
            or solution.get("expected_impact")
            or "Action recommended by the workflow output."
        )
        actions = solution.get("actions")
        action_list = actions if isinstance(actions, list) else []
        if not action_list and solution.get("action"):
            action_list = [str(solution["action"])]

        builder.ensure_space(48)
        builder.text(MARGIN, builder.cursor_y, title, size=13, font="F2", color="#11233D")
        builder.text(
            PAGE_WIDTH - MARGIN - 86,
            builder.cursor_y,
            priority,
            size=10,
            font="F2",
            color="#C65D2E",
        )
        builder.cursor_y -= 16
        builder.wrapped_text(rationale, size=11, color="#334155")
        if action_list:
            builder.bullet_list([str(item) for item in action_list])
        builder.cursor_y -= 6

    builder.section_header("Machine Hotspots")
    hotspot_lines = [
        (
            f"{machine.machine_id}: {machine.issue_count} issue(s), "
            f"avg temp {machine.average_temperature} C, "
            f"avg error {machine.average_error_rate}, "
            f"downtime {machine.total_downtime_minutes} min."
        )
        for machine in dashboard.machine_breakdown
    ]
    if hotspot_lines:
        builder.bullet_list(hotspot_lines)
    else:
        builder.wrapped_text(
            "No machine hotspots were highlighted for this dataset.",
            size=11,
            color="#334155",
        )

    return builder.build()


def _format_oee_line(line: OeeLineInsight) -> str:
    return (
        f"{line.line_id}: OEE {_format_percent(line.oee)}, availability "
        f"{_format_percent(line.availability)}, performance {_format_percent(line.performance)}, "
        f"quality {_format_percent(line.quality)}, {line.machine_count} machines."
    )
