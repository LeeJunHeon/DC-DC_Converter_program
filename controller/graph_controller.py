# graph_controller.py

import csv
from pathlib import Path
from datetime import datetime

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


class PowerGraphWidget(QWidget):
    """
    전압/전류/파워 그래프 위젯

    - X축: 실제 현재 시간(HH:mm:ss), 최근 window_sec 초만 표시
    - Y축(왼쪽): Voltage(V) / Current(A)
    - Y축(오른쪽): Power(W)
    - start_output() / stop_output() 호출 시 선이 끊겨 보이도록
      ON 구간마다 새로운 QLineSeries 세그먼트를 사용
    - start_recording() / stop_recording() 으로 CSV 녹화 기능 지원
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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # ---------- Chart ----------
        self.chart = QChart()
        self.chart.setTitle("")

        bg = QColor(245, 245, 245)
        self.chart.setBackgroundBrush(bg)
        self.chart.setPlotAreaBackgroundBrush(bg)
        self.chart.setPlotAreaBackgroundVisible(True)

        # 그래프 영역 크게
        self.chart.setMargins(QMargins(10, 10, 10, 10))
        if self.chart.layout() is not None:
            self.chart.layout().setContentsMargins(0, 0, 0, 0)

        # ---------- 축 ----------
        self.window_sec = 10
        self.window_sec_int = int(self.window_sec)

        # X축: 실제 현재 시간
        self.axis_x = QDateTimeAxis()
        self.axis_x.setTitleText("Time")
        self.axis_x.setFormat("HH:mm:ss")
        self.axis_x.setTickCount(self.window_sec_int + 1)  # 1초 간격 눈금

        now = QDateTime.currentDateTime()
        self.axis_x.setRange(now.addSecs(-self.window_sec_int), now)

        # 왼쪽 Y축: V / A
        self.axis_y_left = QValueAxis()
        self.axis_y_left.setTitleText("Voltage (V) / Current (A)")
        self.axis_y_left.setRange(0, 500)
        self.axis_y_left.setLabelFormat("%.0f")
        self.axis_y_left.setTickCount(11)

        # 오른쪽 Y축: W
        self.axis_y_right = QValueAxis()
        self.axis_y_right.setTitleText("Power (W)")
        self.axis_y_right.setRange(0, 20000)
        self.axis_y_right.setLabelFormat("%.0f")
        self.axis_y_right.setTickCount(11)

        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y_left, Qt.AlignLeft)
        self.chart.addAxis(self.axis_y_right, Qt.AlignRight)

        # ---------- 범례용 시리즈 3개 (이건 이름/색상만 담당, 데이터는 안 넣음) ----------
        legend_power = QLineSeries()
        legend_power.setName("Power (W)")
        legend_power.setPen(QPen(QColor(255, 0, 0), 2))
        self.chart.addSeries(legend_power)
        legend_power.attachAxis(self.axis_x)
        legend_power.attachAxis(self.axis_y_right)

        legend_voltage = QLineSeries()
        legend_voltage.setName("Voltage (V)")
        legend_voltage.setPen(QPen(QColor(0, 120, 255), 2))
        self.chart.addSeries(legend_voltage)
        legend_voltage.attachAxis(self.axis_x)
        legend_voltage.attachAxis(self.axis_y_left)

        legend_current = QLineSeries()
        legend_current.setName("Current (A)")
        legend_current.setPen(QPen(QColor(0, 180, 0), 2))
        self.chart.addSeries(legend_current)
        legend_current.attachAxis(self.axis_x)
        legend_current.attachAxis(self.axis_y_left)

        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignTop)

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

        self._update_interval_ms = 1000  # 1초
        self.timer = QTimer(self)
        self.timer.setInterval(self._update_interval_ms)
        self.timer.timeout.connect(self._on_timer)
        self.timer.start()

        # ---------- 녹화 상태 ----------
        self._recording: bool = False
        self._record_file = None
        self._record_writer: csv.writer | None = None
        self._record_file_path: Path | None = None

        # ---------- ChartView ----------
        self.view = QChartView(self.chart)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setStyleSheet("border: 1px solid black;")
        layout.addWidget(self.view)

    # ------------------------------------------------------------------
    # 외부 API (출력 제어)
    # ------------------------------------------------------------------
    def set_target(self, voltage: float, current: float) -> None:
        """출력 목표값 설정 (입력값 그대로 사용)."""
        v = float(voltage)
        c = float(current)
        p = v * c
        self._target_voltage = v
        self._target_current = c
        self._target_power = p

    def start_output(self) -> None:
        """
        출력 ON:
        - 새로운 시리즈 세그먼트를 생성.
        - 이후 데이터는 그 세그먼트에만 추가되므로
          OFF 기간은 선이 끊어져 보인다.
        """
        if self._power_on:
            return

        self._power_on = True
        self._start_new_segment()

    def stop_output(self) -> None:
        """출력 OFF: 이후에는 포인트를 추가하지 않는다."""
        self._power_on = False
        self._active_power_series = None
        self._active_voltage_series = None
        self._active_current_series = None

    def is_output_on(self) -> bool:
        """현재 출력 ON 상태인지 여부 리턴."""
        return self._power_on

    # ------------------------------------------------------------------
    # 외부 API (녹화 제어)
    # ------------------------------------------------------------------
    def start_recording(
        self,
        input_power: float,
        input_voltage: float,
        input_current: float,
    ) -> str:
        """
        CSV 녹화 시작.
        - input_* : 녹화 시작 시점의 입력 파워/전압/전류 값 (파일 상단에 기록)
        - 반환값 : 생성된 CSV 파일 경로 (string)
        """
        # 기존 녹화 중이면 먼저 정리
        self.stop_recording()

        logs_dir = Path.cwd() / "logs"
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
        # 컬럼 헤더
        writer.writerow(["Time", "Power(W)", "Voltage(V)", "Current(A)"])
        f.flush()

        self._record_file = f
        self._record_writer = writer
        self._record_file_path = file_path
        self._recording = True

        return str(file_path)

    def stop_recording(self) -> str | None:
        """
        CSV 녹화 중지.
        - 반환값 : 마지막으로 기록한 파일 경로 (또는 None)
        """
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
        # 파일 경로는 마지막 파일 안내용으로 그대로 둔다.

        return path_str

    def is_recording(self) -> bool:
        """현재 CSV 녹화 중인지 여부."""
        return self._recording

    # ------------------------------------------------------------------
    # 내부: 새로운 구간(세그먼트) 시작
    # ------------------------------------------------------------------
    def _start_new_segment(self) -> None:
        """ON 상태로 전환될 때마다 새 QLineSeries를 만들어 연결한다."""
        # Power 세그먼트
        power_series = QLineSeries()
        power_series.setPen(QPen(QColor(255, 0, 0), 2))
        self.chart.addSeries(power_series)
        power_series.attachAxis(self.axis_x)
        power_series.attachAxis(self.axis_y_right)
        self.power_series_segments.append(power_series)
        self._active_power_series = power_series

        # Voltage 세그먼트
        voltage_series = QLineSeries()
        voltage_series.setPen(QPen(QColor(0, 120, 255), 2))
        self.chart.addSeries(voltage_series)
        voltage_series.attachAxis(self.axis_x)
        voltage_series.attachAxis(self.axis_y_left)
        self.voltage_series_segments.append(voltage_series)
        self._active_voltage_series = voltage_series

        # Current 세그먼트
        current_series = QLineSeries()
        current_series.setPen(QPen(QColor(0, 180, 0), 2))
        self.chart.addSeries(current_series)
        current_series.attachAxis(self.axis_x)
        current_series.attachAxis(self.axis_y_left)
        self.current_series_segments.append(current_series)
        self._active_current_series = current_series

        # ★ 새 세그먼트는 범례 마커를 전부 숨긴다 (위에 네모 안 생기게)
        for series in (power_series, voltage_series, current_series):
            for marker in self.chart.legend().markers(series):
                marker.setVisible(False)

    # ------------------------------------------------------------------
    # 타이머 콜백
    # ------------------------------------------------------------------
    def _on_timer(self) -> None:
        """
        1초마다 호출.
        - 항상 X축을 현재 시간 기준으로 슬라이딩.
        - 출력 ON 상태이면서 active 시리즈가 있을 때만 포인트 추가.
        """
        # ★★ 여기서 매번 "현재 시각"을 새로 구한다
        now = QDateTime.currentDateTime()

        # X축: 현재시간 기준 window_sec 초 윈도우
        start_dt = now.addSecs(-self.window_sec_int)
        self.axis_x.setRange(start_dt, now)

        if not self._power_on:
            return

        if (
            self._active_power_series is None
            or self._active_voltage_series is None
            or self._active_current_series is None
        ):
            return

        # 이 now 가 그대로 append_point(dt=...) 로 넘어감
        self._append_point(now, self._target_power, self._target_voltage, self._target_current)

    # ------------------------------------------------------------------
    # 숫자 표시 헬퍼 (QLCDNumber / QPlainTextEdit / QLineEdit 지원)
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
        """
        dt: 이 샘플의 실제 시간 (타이머에서 QDateTime.currentDateTime()으로 받은 값)
        """
        x = dt.toMSecsSinceEpoch()

        # 그래프 시리즈에 포인트 추가
        self._active_power_series.append(x, power)
        self._active_voltage_series.append(x, voltage)
        self._active_current_series.append(x, current)

        # 출력 위젯 업데이트
        self._set_numeric_widget(self.output_power_edit, power)
        self._set_numeric_widget(self.output_voltage_edit, voltage)
        self._set_numeric_widget(self.output_current_edit, current)

        # ★ 녹화 중이면 CSV에 "이 시점의 값" 기록
        if self._recording and self._record_writer is not None:
            # 이전: time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            raw_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 엑셀이 날짜로 인식하지 않도록 앞에 ' 를 붙여 텍스트로 저장
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
