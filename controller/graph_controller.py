# graph_controller.py

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
    - 출력 위젯 3개(QLCDNumber / QPlainTextEdit / QLineEdit)에 마지막 포인트 값 표시
    - MainWindow 에서 set_target(), start_output(), stop_output() 으로 제어
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

        # UI에서 넘겨주는 출력용 위젯 (타입은 QLCDNumber / QPlainTextEdit 등 섞여 있음)
        self.output_power_edit = output_power_edit
        self.output_voltage_edit = output_voltage_edit
        self.output_current_edit = output_current_edit

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # ---------- Chart & Series ----------
        self.chart = QChart()
        self.chart.setTitle("")

        bg = QColor(245, 245, 245)
        self.chart.setBackgroundBrush(bg)
        self.chart.setPlotAreaBackgroundBrush(bg)
        self.chart.setPlotAreaBackgroundVisible(True)

        # 그래프 영역 크게 보이도록 margin 최소화
        self.chart.setMargins(QMargins(10, 10, 10, 10))
        if self.chart.layout() is not None:
            self.chart.layout().setContentsMargins(0, 0, 0, 0)

        # 선 3개
        self.series_power = QLineSeries()
        self.series_power.setName("Power (W)")
        self.series_power.setPen(QPen(QColor(255, 0, 0), 2))

        self.series_voltage = QLineSeries()
        self.series_voltage.setName("Voltage (V)")
        self.series_voltage.setPen(QPen(QColor(0, 120, 255), 2))

        self.series_current = QLineSeries()
        self.series_current.setName("Current (A)")
        self.series_current.setPen(QPen(QColor(0, 180, 0), 2))

        self.chart.addSeries(self.series_power)
        self.chart.addSeries(self.series_voltage)
        self.chart.addSeries(self.series_current)

        # ---------- 축 설정 ----------
        self.window_sec = 10
        self.window_sec_int = int(self.window_sec)

        # X축: 실제 현재 시간
        self.axis_x = QDateTimeAxis()
        self.axis_x.setTitleText("Time")
        self.axis_x.setFormat("HH:mm:ss")
        self.axis_x.setTickCount(self.window_sec_int + 1)  # 1초 간격 눈금

        now = QDateTime.currentDateTime()
        self.axis_x.setRange(
            now.addSecs(-self.window_sec_int),
            now,
        )

        # 왼쪽 Y축: V / A  (0~500까지만 보이게)
        self.axis_y_left = QValueAxis()
        self.axis_y_left.setTitleText("Voltage (V) / Current (A)")
        self.axis_y_left.setRange(0, 500)
        self.axis_y_left.setLabelFormat("%.0f")
        self.axis_y_left.setTickCount(11)  # 0,50,...,500

        # 오른쪽 Y축: W (0~20 kW)
        self.axis_y_right = QValueAxis()
        self.axis_y_right.setTitleText("Power (W)")
        self.axis_y_right.setRange(0, 20000)
        self.axis_y_right.setLabelFormat("%.0f")
        self.axis_y_right.setTickCount(11)  # 0,2000,...,20000

        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y_left, Qt.AlignLeft)
        self.chart.addAxis(self.axis_y_right, Qt.AlignRight)

        # 축 연결
        for s in (self.series_power, self.series_voltage, self.series_current):
            s.attachAxis(self.axis_x)

        self.series_voltage.attachAxis(self.axis_y_left)
        self.series_current.attachAxis(self.axis_y_left)
        self.series_power.attachAxis(self.axis_y_right)

        # 범례
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignTop)

        # ---------- ChartView ----------
        self.view = QChartView(self.chart)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setStyleSheet("border: 1px solid black;")

        layout.addWidget(self.view)

        # ---------- 상태 / 타이머 ----------
        self.max_points = 500

        # 현재 목표값 (설정 값 적용 / 출력 ON 에서 설정)
        self._target_voltage = 0.0
        self._target_current = 0.0
        self._target_power = 0.0

        # 출력 ON 여부
        self._power_on = False

        # 타이머는 항상 돈다 (그래프 그릴 때만 포인트 추가)
        self._update_interval_ms = 1000  # 1초
        self.timer = QTimer(self)
        self.timer.setInterval(self._update_interval_ms)
        self.timer.timeout.connect(self._on_timer)
        self.timer.start()

    # ------------------------------------------------------------------
    # 외부에서 호출하는 API  (★ 클램프 없음: 입력 그대로 사용)
    # ------------------------------------------------------------------
    def set_target(self, voltage: float, current: float) -> None:
        """
        목표 전압/전류 설정.
        - 여기서는 사용자가 입력한 값을 그대로 사용한다.
        """
        v = float(voltage)
        c = float(current)
        p = v * c

        self._target_voltage = v
        self._target_current = c
        self._target_power = p

    def start_output(self) -> None:
        """출력 ON: 그래프 포인트 추가 시작"""
        self._power_on = True

    def stop_output(self) -> None:
        """출력 OFF: 그래프 포인트 추가 중단 (축 시간은 계속 진행)"""
        self._power_on = False

    # ------------------------------------------------------------------
    # 타이머 콜백
    # ------------------------------------------------------------------
    def _on_timer(self) -> None:
        """
        1초마다 호출.
        - 항상 X축을 현재 시간 기준으로 슬라이딩
        - 출력 ON 상태일 때만 포인트 추가
        """
        now = QDateTime.currentDateTime()

        # X축: 현재시간 기준 window_sec 초 윈도우
        start_dt = now.addSecs(-self.window_sec_int)
        self.axis_x.setRange(start_dt, now)

        # 출력 OFF면 선 없이 시간만 흐름
        if not self._power_on:
            return

        voltage = self._target_voltage
        current = self._target_current
        power = self._target_power

        self.append_point(now, power, voltage, current)

    # ------------------------------------------------------------------
    # 숫자 표시용 헬퍼 (QLCDNumber / QPlainTextEdit / QLineEdit 모두 지원)
    # ------------------------------------------------------------------
    def _set_numeric_widget(self, widget, value: float) -> None:
        if widget is None:
            return
        text = f"{value:.1f}"

        # QLCDNumber
        if hasattr(widget, "display"):
            widget.display(text)
        # QPlainTextEdit
        elif hasattr(widget, "setPlainText"):
            widget.setPlainText(text)
        # QLineEdit 등 setText 있는 경우
        elif hasattr(widget, "setText"):
            widget.setText(text)

    # ------------------------------------------------------------------
    # 실제 데이터 추가용 내부 API
    # ------------------------------------------------------------------
    def append_point(
        self,
        dt: QDateTime,
        power: float,
        voltage: float,
        current: float,
    ) -> None:
        """
        dt: QDateTime (측정 시각)
        power: 전력 [W]
        voltage: 전압 [V]
        current: 전류 [A]
        """
        x = dt.toMSecsSinceEpoch()

        # 그래프 데이터 추가
        self.series_power.append(x, power)
        self.series_voltage.append(x, voltage)
        self.series_current.append(x, current)

        # 출력 위젯에 그래프와 동일한 값 표시
        self._set_numeric_widget(self.output_power_edit, power)
        self._set_numeric_widget(self.output_voltage_edit, voltage)
        self._set_numeric_widget(self.output_current_edit, current)

        # 포인트 수 제한
        for series in (self.series_power, self.series_voltage, self.series_current):
            cnt = series.count()
            if cnt > self.max_points:
                series.removePoints(0, cnt - self.max_points)
