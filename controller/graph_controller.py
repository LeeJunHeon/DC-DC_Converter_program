# graph_controller.py

import csv
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional, Tuple

from PySide6.QtCore import QTimer, Qt, QDateTime, QMargins
from PySide6.QtGui import QPen, QColor, QPainter
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCharts import (
    QChart,
    QChartView,
    QLineSeries,
    QValueAxis,
    QDateTimeAxis,
)

# SampleProvider:
#   - Maxwell에서 읽어온 값 반환 형식: (power_W, voltage_V, current_A)
SampleProvider = Callable[[], Optional[Tuple[float, float, float]]]


class PowerGraphWidget(QWidget):
    """
    파워 / 전압 / 전류를 각각 별도 그래프로 그리는 위젯.

    - 그래프 3개를 세로로 배치:
        [Power(W)]   (상단)
        [Voltage(V)] (중간)
        [Current(A)] (하단)
    - 각 그래프는 자기 X축을 가진다 (모두 HH:mm:ss, 최근 window_sec 초만 표시)
    - X축 제목은 표시하지 않는다.
    - Y축 tick 개수는 5개로 줄여서 레이블이 '...' 로 잘리지 않게 함.
    - start_output() / stop_output() 으로 ON 구간만 선이 이어지도록 세그먼트 관리
    - start_recording() / stop_recording() 으로 CSV 녹화 기능 지원
    - output ON 상태일 때, 1초마다 등록된 sample_provider()를 호출해서
      실제 장비에서 읽어온 값으로 그래프를 그림.
    """

    def __init__(
        self,
        parent=None,
        *,
        output_power_edit=None,
        output_voltage_edit=None,
        output_current_edit=None,
    ):
        super().__init__(parent)

        # UI에서 넘겨주는 출력용 위젯
        self.output_power_edit = output_power_edit
        self.output_voltage_edit = output_voltage_edit
        self.output_current_edit = output_current_edit

        # 메인 레이아웃 (세로로 3개 그래프)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 공통 설정
        self.window_sec = 10
        self.window_sec_int = int(self.window_sec)

        self._charts: list[QChart] = []
        self._x_axes: list[QDateTimeAxis] = []

        # --- 헬퍼: 차트 하나 생성 ---
        def create_chart(y_title: str, y_min: float, y_max: float) -> tuple[
            QChart, QDateTimeAxis, QValueAxis
        ]:
            chart = QChart()
            chart.setTitle("")  # ★ 그래프 제목 제거
            bg = QColor(245, 245, 245)
            chart.setBackgroundBrush(bg)
            chart.setPlotAreaBackgroundBrush(bg)
            chart.setPlotAreaBackgroundVisible(True)
            chart.setMargins(QMargins(4, 4, 4, 4))
            if chart.layout() is not None:
                chart.layout().setContentsMargins(0, 0, 0, 0)

            # X축: 실제 현재 시간 (HH:mm:ss), 제목은 표시하지 않음
            axis_x = QDateTimeAxis()
            axis_x.setTitleText("")  # ★ X축 제목 제거
            axis_x.setFormat("HH:mm:ss")
            axis_x.setTickCount(self.window_sec_int + 1)  # 1초 간격
            now = QDateTime.currentDateTime()
            axis_x.setRange(now.addSecs(-self.window_sec_int), now)

            # Y축: 각 그래프별 범위, tick 개수 5개
            axis_y = QValueAxis()
            axis_y.setTitleText(y_title)
            axis_y.setRange(y_min, y_max)
            axis_y.setLabelFormat("%.0f")
            axis_y.setTickCount(6)  # ★ Y축 tick 5개로 제한

            chart.addAxis(axis_x, Qt.AlignBottom)
            chart.addAxis(axis_y, Qt.AlignLeft)

            chart.legend().setVisible(False)  # ★ 범례 숨겨서 세로 공간 확보

            view = QChartView(chart)
            view.setRenderHint(QPainter.Antialiasing)
            view.setStyleSheet("border: 1px solid black;")
            layout.addWidget(view)

            self._charts.append(chart)
            self._x_axes.append(axis_x)

            return chart, axis_x, axis_y

        # --- 상단: Power(W) 그래프 ---
        (
            self.chart_power,
            self.axis_x_power,
            self.axis_y_power,
        ) = create_chart("Power (W)", 0, 20000)

        # --- 중간: Voltage(V) 그래프 ---
        (
            self.chart_voltage,
            self.axis_x_voltage,
            self.axis_y_voltage,
        ) = create_chart("Voltage (V)", 0, 60)

        # --- 하단: Current(A) 그래프 ---
        (
            self.chart_current,
            self.axis_x_current,
            self.axis_y_current,
        ) = create_chart("Current (A)", 0, 500)

        # ---------- 실제 데이터 시리즈 세그먼트 관리 ----------
        self.power_series_segments: list[QLineSeries] = []
        self.voltage_series_segments: list[QLineSeries] = []
        self.current_series_segments: list[QLineSeries] = []

        self._active_power_series: QLineSeries | None = None
        self._active_voltage_series: QLineSeries | None = None
        self._active_current_series: QLineSeries | None = None

        # ---------- 상태 & 타이머 ----------
        self.max_points_per_series = 500

        self._target_voltage = 0.0
        self._target_current = 0.0
        self._target_power = 0.0

        self._power_on = False

        # ---------- 타이머 설정 ----------
        self._update_interval_ms = 1000  # 기본 1초
        self.timer = QTimer(self)
        self.timer.setInterval(self._update_interval_ms)
        self.timer.timeout.connect(self._on_timer)
        self.timer.start()

        # ---------- 장비 샘플 콜백 ----------
        self._sample_provider: Optional[SampleProvider] = None

        # ---------- 녹화 상태 ----------
        self._recording: bool = False
        self._record_file = None
        self._record_writer: csv.writer | None = None
        self._record_file_path: Path | None = None

    # ------------------------------------------------------------------
    # 외부 API (측정 주기 변경)
    # ------------------------------------------------------------------
    def set_update_interval(self, sec: float) -> None:
        """
        그래프 업데이트 / 장비 폴링 주기를 변경한다.
        - sec: 초 단위 (예: 0.5, 1.0, 2.0, 5.0 ...)
        """
        # 0 이하로 들어오는 경우를 방지
        if sec <= 0:
            sec = 1.0

        # --- 타이머 간격 변경 (장비 읽기 + 그래프 업데이트 주기) ---
        self._update_interval_ms = int(sec * 1000)
        self.timer.setInterval(self._update_interval_ms)

        # --- X축 눈금 간격도 주기에 맞추기 ---
        # window_sec(가로로 보이는 시간 범위)를 sec 간격으로 나눈 개수 + 1
        # 예) window_sec=10, sec=5  -> 눈금 3개 (시작, +5초, 끝)
        if self.window_sec_int > 0:
            tick_count = int(self.window_sec_int / sec) + 1
        else:
            tick_count = 2

        # 최소 2개는 유지
        if tick_count < 2:
            tick_count = 2

        # ★ 3개 그래프(P/V/I) X축 모두에 tickCount 적용
        for axis in (self.axis_x_power, self.axis_x_voltage, self.axis_x_current):
            axis.setTickCount(tick_count)

    # ------------------------------------------------------------------
    # 외부 API (출력 제어)
    # ------------------------------------------------------------------
    def set_target(self, voltage: float, current: float) -> None:
        v = float(voltage)
        c = float(current)
        p = v * c
        self._target_voltage = v
        self._target_current = c
        self._target_power = p

    def start_output(self) -> None:
        if self._power_on:
            return
        self._power_on = True
        self._start_new_segment()

    def stop_output(self) -> None:
        self._power_on = False
        self._active_power_series = None
        self._active_voltage_series = None
        self._active_current_series = None

    def is_output_on(self) -> bool:
        return self._power_on

    # ------------------------------------------------------------------
    # 외부 API (장비 샘플 공급자)
    # ------------------------------------------------------------------
    def set_sample_provider(self, provider: Optional[SampleProvider]) -> None:
        self._sample_provider = provider

    # ------------------------------------------------------------------
    # 외부 API (녹화 제어)
    # ------------------------------------------------------------------
    def start_recording(
        self,
        input_power: float,
        input_voltage: float,
        input_current: float,
    ) -> str:
        # 기존 녹화 중이면 먼저 정리
        self.stop_recording()

        logs_dir = Path.cwd() / "data"
        logs_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = logs_dir / f"record_{ts}.csv"

        f = file_path.open("w", newline="", encoding="utf-8-sig")
        writer = csv.writer(f)

        # 상단에 입력값 기록
        writer.writerow(
            [
                "# InputPower(W)",
                f"{input_power:.3f}",
                "InputVoltage(V)",
                f"{input_voltage:.3f}",
                "InputCurrent(A)",
                f"{input_current:.3f}",
            ]
        )
        writer.writerow(["Time", "Power(W)", "Voltage(V)", "Current(A)"])
        f.flush()

        self._record_file = f
        self._record_writer = writer
        self._record_file_path = file_path
        self._recording = True

        return str(file_path)

    def stop_recording(self) -> str | None:
        path_str = str(self._record_file_path) if self._record_file_path else None

        if self._record_file is not None:
            try:
                self._record_file.flush()
                self._record_file.close()
            except Exception:
                pass

        self._record_file = None
        self._record_writer = None
        self._recording = False

        return path_str

    def is_recording(self) -> bool:
        return self._recording

    # ------------------------------------------------------------------
    # 내부: 새로운 구간(세그먼트) 시작
    # ------------------------------------------------------------------
    def _start_new_segment(self) -> None:
        # Power 세그먼트
        power_series = QLineSeries()
        power_series.setPen(QPen(QColor(255, 0, 0), 2))
        self.chart_power.addSeries(power_series)
        power_series.attachAxis(self.axis_x_power)
        power_series.attachAxis(self.axis_y_power)
        self.power_series_segments.append(power_series)
        self._active_power_series = power_series

        # Voltage 세그먼트
        voltage_series = QLineSeries()
        voltage_series.setPen(QPen(QColor(0, 120, 255), 2))
        self.chart_voltage.addSeries(voltage_series)
        voltage_series.attachAxis(self.axis_x_voltage)
        voltage_series.attachAxis(self.axis_y_voltage)
        self.voltage_series_segments.append(voltage_series)
        self._active_voltage_series = voltage_series

        # Current 세그먼트
        current_series = QLineSeries()
        current_series.setPen(QPen(QColor(0, 180, 0), 2))
        self.chart_current.addSeries(current_series)
        current_series.attachAxis(self.axis_x_current)
        current_series.attachAxis(self.axis_y_current)
        self.current_series_segments.append(current_series)
        self._active_current_series = current_series

    # ------------------------------------------------------------------
    # 타이머 콜백
    # ------------------------------------------------------------------
    def _on_timer(self) -> None:
        """
        1초마다 호출.
        - 모든 그래프의 X축을 현재 시간 기준으로 슬라이딩.
        - 출력 ON 상태일 때 sample_provider()로부터 (P,V,I)를 읽어 각 그래프에 추가.
        """
        now = QDateTime.currentDateTime()
        start_dt = now.addSecs(-self.window_sec_int)

        # ★ 3개 그래프 모두 X축 범위 갱신
        for axis in (self.axis_x_power, self.axis_x_voltage, self.axis_x_current):
            axis.setRange(start_dt, now)

        if not self._power_on:
            return

        if (
            self._active_power_series is None
            or self._active_voltage_series is None
            or self._active_current_series is None
        ):
            return

        if self._sample_provider is None:
            return

        try:
            result = self._sample_provider()
        except Exception:
            return

        if not result:
            return

        power, voltage, current = result
        self._append_point(now, power, voltage, current)

    # ------------------------------------------------------------------
    # 숫자 표시 헬퍼
    # ------------------------------------------------------------------
    def _set_numeric_widget(self, widget, value: float) -> None:
        if widget is None:
            return
        text = f"{value:.1f}"

        if hasattr(widget, "display"):          # QLCDNumber
            widget.display(text)
        elif hasattr(widget, "setPlainText"):   # QPlainTextEdit
            widget.setPlainText(text)
        elif hasattr(widget, "setText"):        # QLineEdit, QLabel 등
            widget.setText(text)

    # ------------------------------------------------------------------
    # 실제 데이터 추가
    # ------------------------------------------------------------------
    def _append_point(
        self,
        dt: QDateTime,
        power: float,
        voltage: float,
        current: float,
    ) -> None:
        x = dt.toMSecsSinceEpoch()

        # 각 그래프 시리즈에 포인트 추가
        self._active_power_series.append(x, power)
        self._active_voltage_series.append(x, voltage)
        self._active_current_series.append(x, current)

        # 출력 값 표시
        self._set_numeric_widget(self.output_power_edit, power)
        self._set_numeric_widget(self.output_voltage_edit, voltage)
        self._set_numeric_widget(self.output_current_edit, current)

        # 녹화 중이면 CSV에 기록
        if self._recording and self._record_writer is not None:
            raw_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            time_str = "'" + raw_time_str
            self._record_writer.writerow(
                [time_str, f"{power:.3f}", f"{voltage:.3f}", f"{current:.3f}"]
            )
            try:
                self._record_file.flush()
            except Exception:
                pass

        # 포인트 수 제한
        for series in (
            self.power_series_segments
            + self.voltage_series_segments
            + self.current_series_segments
        ):
            cnt = series.count()
            if cnt > self.max_points_per_series:
                series.removePoints(0, cnt - self.max_points_per_series)
