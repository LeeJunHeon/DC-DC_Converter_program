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
#  - Maxwell에서 읽어온 값 반환 형식: (power_W, voltage_V, current_A)
SampleProvider = Callable[[], Optional[Tuple[float, float, float]]]


class PowerGraphWidget(QWidget):
    """
    파워 / 전압 / 전류를 각각 별도 그래프로 그리는 위젯.

    - 그래프 3개를 세로로 배치:
        [Power(W)]   (상단)
        [Voltage(V)] (중앙)
        [Current(A)] (하단)

    - X축은 모두 실시간 시간(HH:mm:ss), 최근 window_sec 초만 표시
    - 출력 ON 구간마다 새로운 QLineSeries 세그먼트를 만들어
      OFF 구간은 선이 끊겨 보이도록 구현
    - start_recording() / stop_recording() 으로 CSV 녹화 기능 지원
    - output ON 상태일 때, 1초마다 등록된 sample_provider()를 호출해서
      실제 장비에서 읽어온 값으로 그래프를 그림
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

        # --- UI 쪽 출력용 위젯 (우측 상단 숫자 표시용) ---
        self.output_power_edit = output_power_edit
        self.output_voltage_edit = output_voltage_edit
        self.output_current_edit = output_current_edit

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 공통 설정
        self.window_sec = 10
        self.window_sec_int = int(self.window_sec)
        bg = QColor(245, 245, 245)

        # ==========================================================
        # 1) Power Chart (상단)
        # ==========================================================
        self.chart_power = QChart()
        self.chart_power.setTitle("Power (W)")
        self.chart_power.setBackgroundBrush(bg)
        self.chart_power.setPlotAreaBackgroundBrush(bg)
        self.chart_power.setPlotAreaBackgroundVisible(True)
        self.chart_power.setMargins(QMargins(10, 10, 10, 10))
        if self.chart_power.layout() is not None:
            self.chart_power.layout().setContentsMargins(0, 0, 0, 0)

        self.axis_x_power = QDateTimeAxis()
        self.axis_x_power.setTitleText("Time")
        self.axis_x_power.setFormat("HH:mm:ss")
        self.axis_x_power.setTickCount(self.window_sec_int + 1)
        now = QDateTime.currentDateTime()
        self.axis_x_power.setRange(now.addSecs(-self.window_sec_int), now)

        self.axis_y_power = QValueAxis()
        self.axis_y_power.setTitleText("Power (W)")
        self.axis_y_power.setRange(0, 20000)
        self.axis_y_power.setLabelFormat("%.0f")
        self.axis_y_power.setTickCount(11)

        self.chart_power.addAxis(self.axis_x_power, Qt.AlignBottom)
        self.chart_power.addAxis(self.axis_y_power, Qt.AlignLeft)

        self.chart_power.legend().setVisible(True)
        self.chart_power.legend().setAlignment(Qt.AlignTop)

        # 실제 데이터 시리즈(ON 구간별 세그먼트)
        self.power_series_segments: list[QLineSeries] = []
        self._active_power_series: QLineSeries | None = None

        self.view_power = QChartView(self.chart_power)
        self.view_power.setRenderHint(QPainter.Antialiasing)
        self.view_power.setStyleSheet("border: 1px solid black;")
        main_layout.addWidget(self.view_power)

        # ==========================================================
        # 2) Voltage Chart (중앙)
        # ==========================================================
        self.chart_voltage = QChart()
        self.chart_voltage.setTitle("Voltage (V)")
        self.chart_voltage.setBackgroundBrush(bg)
        self.chart_voltage.setPlotAreaBackgroundBrush(bg)
        self.chart_voltage.setPlotAreaBackgroundVisible(True)
        self.chart_voltage.setMargins(QMargins(10, 10, 10, 10))
        if self.chart_voltage.layout() is not None:
            self.chart_voltage.layout().setContentsMargins(0, 0, 0, 0)

        self.axis_x_voltage = QDateTimeAxis()
        self.axis_x_voltage.setTitleText("Time")
        self.axis_x_voltage.setFormat("HH:mm:ss")
        self.axis_x_voltage.setTickCount(self.window_sec_int + 1)
        self.axis_x_voltage.setRange(now.addSecs(-self.window_sec_int), now)

        self.axis_y_voltage = QValueAxis()
        self.axis_y_voltage.setTitleText("Voltage (V)")
        # 장비 사양: 0~60V
        self.axis_y_voltage.setRange(0, 60)
        self.axis_y_voltage.setLabelFormat("%.1f")
        self.axis_y_voltage.setTickCount(13)  # 5V 단위 눈금 정도

        self.chart_voltage.addAxis(self.axis_x_voltage, Qt.AlignBottom)
        self.chart_voltage.addAxis(self.axis_y_voltage, Qt.AlignLeft)

        self.chart_voltage.legend().setVisible(True)
        self.chart_voltage.legend().setAlignment(Qt.AlignTop)

        self.voltage_series_segments: list[QLineSeries] = []
        self._active_voltage_series: QLineSeries | None = None

        self.view_voltage = QChartView(self.chart_voltage)
        self.view_voltage.setRenderHint(QPainter.Antialiasing)
        self.view_voltage.setStyleSheet("border: 1px solid black;")
        main_layout.addWidget(self.view_voltage)

        # ==========================================================
        # 3) Current Chart (하단)
        # ==========================================================
        self.chart_current = QChart()
        self.chart_current.setTitle("Current (A)")
        self.chart_current.setBackgroundBrush(bg)
        self.chart_current.setPlotAreaBackgroundBrush(bg)
        self.chart_current.setPlotAreaBackgroundVisible(True)
        self.chart_current.setMargins(QMargins(10, 10, 10, 10))
        if self.chart_current.layout() is not None:
            self.chart_current.layout().setContentsMargins(0, 0, 0, 0)

        self.axis_x_current = QDateTimeAxis()
        self.axis_x_current.setTitleText("Time")
        self.axis_x_current.setFormat("HH:mm:ss")
        self.axis_x_current.setTickCount(self.window_sec_int + 1)
        self.axis_x_current.setRange(now.addSecs(-self.window_sec_int), now)

        self.axis_y_current = QValueAxis()
        self.axis_y_current.setTitleText("Current (A)")
        # 장비 사양: 0~500A
        self.axis_y_current.setRange(0, 500)
        self.axis_y_current.setLabelFormat("%.0f")
        self.axis_y_current.setTickCount(11)  # 50A 단위 눈금

        self.chart_current.addAxis(self.axis_x_current, Qt.AlignBottom)
        self.chart_current.addAxis(self.axis_y_current, Qt.AlignLeft)

        self.chart_current.legend().setVisible(True)
        self.chart_current.legend().setAlignment(Qt.AlignTop)

        self.current_series_segments: list[QLineSeries] = []
        self._active_current_series: QLineSeries | None = None

        self.view_current = QChartView(self.chart_current)
        self.view_current.setRenderHint(QPainter.Antialiasing)
        self.view_current.setStyleSheet("border: 1px solid black;")
        main_layout.addWidget(self.view_current)

        # ==========================================================
        # 공통 상태
        # ==========================================================
        self.max_points_per_series = 500

        # 목표값(그래프에는 직접 쓰지 않고 참조용으로만 보관)
        self._target_voltage = 0.0
        self._target_current = 0.0
        self._target_power = 0.0

        self._power_on = False

        # 타이머 (1초마다 샘플링 & 축 업데이트)
        self._update_interval_ms = 1000
        self.timer = QTimer(self)
        self.timer.setInterval(self._update_interval_ms)
        self.timer.timeout.connect(self._on_timer)
        self.timer.start()

        # 장비 샘플 콜백
        self._sample_provider: Optional[SampleProvider] = None

        # 녹화 상태
        self._recording: bool = False
        self._record_file = None
        self._record_writer: csv.writer | None = None
        self._record_file_path: Path | None = None

    # ------------------------------------------------------------------
    # 외부 API (출력 제어)
    # ------------------------------------------------------------------
    def set_target(self, voltage: float, current: float) -> None:
        """
        출력 목표값 설정 (그래프에는 사용하지 않고 내부 저장만 함).
        """
        v = float(voltage)
        c = float(current)
        p = v * c
        self._target_voltage = v
        self._target_current = c
        self._target_power = p

    def start_output(self) -> None:
        """
        출력 ON:
        - 3개의 그래프 각각에 대해 새로운 시리즈 세그먼트를 생성.
        """
        if self._power_on:
            return

        self._power_on = True
        self._start_new_segment()

    def stop_output(self) -> None:
        """
        출력 OFF:
        - 이후에는 포인트를 추가하지 않도록 active 시리즈만 끊는다.
        """
        self._power_on = False
        self._active_power_series = None
        self._active_voltage_series = None
        self._active_current_series = None

    def is_output_on(self) -> bool:
        """현재 출력 ON 상태인지 여부 리턴."""
        return self._power_on
    
    # ------------------------------------------------------------------
    # ★ 외부 API (측정 간격 변경)
    # ------------------------------------------------------------------
    def set_update_interval_sec(self, seconds: float) -> None:
        """
        그래프 갱신 / 장비 폴링 간격을 초 단위로 설정.
        - 0 또는 음수 → 0.1초로 보정
        - 너무 큰 값은 60초로 제한
        """
        try:
            s = float(seconds)
        except (TypeError, ValueError):
            s = 1.0

        if s <= 0:
            s = 0.1
        if s > 60.0:
            s = 60.0

        ms = int(s * 1000)
        if ms < 50:   # 안전장치
            ms = 50

        self._update_interval_ms = ms
        self.timer.setInterval(self._update_interval_ms)

    # ------------------------------------------------------------------
    # 외부 API (장비 샘플 공급자)
    # ------------------------------------------------------------------
    def set_sample_provider(self, provider: Optional[SampleProvider]) -> None:
        """
        장비에서 (Power, Voltage, Current)를 읽어오는 콜백을 등록.
        - provider() 가 None 을 반환하면 이번 주기는 스킵.
        """
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

        return path_str

    def is_recording(self) -> bool:
        """현재 CSV 녹화 중인지 여부."""
        return self._recording

    # ------------------------------------------------------------------
    # 내부: ON 구간(세그먼트) 시작
    # ------------------------------------------------------------------
    def _start_new_segment(self) -> None:
        """
        출력 ON 상태로 전환될 때마다 각 그래프에 새 QLineSeries를 만들어 연결.
        """
        # Power
        power_series = QLineSeries()
        power_series.setName("Power (W)")
        power_series.setPen(QPen(QColor(255, 0, 0), 2))
        self.chart_power.addSeries(power_series)
        power_series.attachAxis(self.axis_x_power)
        power_series.attachAxis(self.axis_y_power)
        self.power_series_segments.append(power_series)
        self._active_power_series = power_series

        # Voltage
        voltage_series = QLineSeries()
        voltage_series.setName("Voltage (V)")
        voltage_series.setPen(QPen(QColor(0, 120, 255), 2))
        self.chart_voltage.addSeries(voltage_series)
        voltage_series.attachAxis(self.axis_x_voltage)
        voltage_series.attachAxis(self.axis_y_voltage)
        self.voltage_series_segments.append(voltage_series)
        self._active_voltage_series = voltage_series

        # Current
        current_series = QLineSeries()
        current_series.setName("Current (A)")
        current_series.setPen(QPen(QColor(0, 180, 0), 2))
        self.chart_current.addSeries(current_series)
        current_series.attachAxis(self.axis_x_current)
        current_series.attachAxis(self.axis_y_current)
        self.current_series_segments.append(current_series)
        self._active_current_series = current_series

    # ------------------------------------------------------------------
    # 타이머 콜백 (측정 주기마다)
    # ------------------------------------------------------------------
    def _on_timer(self) -> None:
        """
        설정된 측정 주기마다 호출.
        - 3개의 그래프 X축을 모두 현재 시간 기준으로 슬라이딩.
        - 출력 ON 상태이면 sample_provider()에서 (P,V,I)를 읽어 각 그래프에 추가.
        """
        now = QDateTime.currentDateTime()
        start_dt = now.addSecs(-self.window_sec_int)

        # 세 그래프 X축을 동일하게 업데이트
        self.axis_x_power.setRange(start_dt, now)
        self.axis_x_voltage.setRange(start_dt, now)
        self.axis_x_current.setRange(start_dt, now)

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

        # 장비에서 샘플 읽기
        try:
            result = self._sample_provider()
        except Exception:
            # 통신 에러 등은 조용히 무시 (그래프만 잠시 멈춤)
            return

        if not result:
            # 읽기 실패 (None) -> 이번 주기는 스킵
            return

        power, voltage, current = result
        self._append_point(now, power, voltage, current)

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

        # 출력 위젯 업데이트 (우측 상단 숫자)
        self._set_numeric_widget(self.output_power_edit, power)
        self._set_numeric_widget(self.output_voltage_edit, voltage)
        self._set_numeric_widget(self.output_current_edit, current)

        # ★ 녹화 중이면 CSV에 "이 시점의 값" 기록
        if self._recording and self._record_writer is not None:
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

        # 포인트 수 제한 (각 그래프의 모든 세그먼트에 대해)
        for series in (
            self.power_series_segments
            + self.voltage_series_segments
            + self.current_series_segments
        ):
            cnt = series.count()
            if cnt > self.max_points_per_series:
                series.removePoints(0, cnt - self.max_points_per_series)
