# main.py
import sys
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QMessageBox,
)

from ui.main_window import Ui_Form
from controller.graph_controller import PowerGraphWidget


# 메뉴얼 스펙 범위
MAX_VOLTAGE = 60.0   # V
MAX_CURRENT = 500.0  # A
MIN_VOLTAGE = 0.0
MIN_CURRENT = 0.0


class MainWindow(QWidget, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # Qt Designer에서 만든 Graph_widget 안에 그래프 삽입
        layout = QVBoxLayout(self.Graph_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.graph = PowerGraphWidget(
            parent=self.Graph_widget,
            output_power_edit=self.outputPower_edit,
            output_voltage_edit=self.outputVoltage_edit,
            output_current_edit=self.outputCurrent_edit,
        )
        layout.addWidget(self.graph)

        # 버튼 시그널 연결
        self.powerOn_button.clicked.connect(self.on_power_on_clicked)
        self.powerOff_button.clicked.connect(self.on_power_off_clicked)
        self.setValue_button.clicked.connect(self.on_set_value_clicked)

    # ------------------------------------------------------------------
    # 입력값 읽기
    # ------------------------------------------------------------------
    def _read_input_voltage_current(self) -> tuple[float, float]:
        """입력 전압/전류를 그대로 float 로 읽어온다. (범위 제한은 _validate_range에서)"""
        v_text = (self.inputVoltage_edit.text() or "").strip()
        i_text = (self.inputCurrent_edit.text() or "").strip()

        try:
            v = float(v_text) if v_text else 0.0
        except ValueError:
            self._show_error("전압 값이 숫자가 아닙니다.")
            v = 0.0

        try:
            i = float(i_text) if i_text else 0.0
        except ValueError:
            self._show_error("전류 값이 숫자가 아닙니다.")
            i = 0.0

        return v, i

    def _update_input_power(self, voltage: float, current: float) -> float:
        """P = V * I 계산해서 입력 파워 칸에 표시."""
        power = voltage * current
        self.inputPower_edit.setText(f"{power:.1f}")
        return power

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, "입력 오류", message)

    def _validate_range(self, voltage: float, current: float) -> bool:
        """
        메뉴얼 스펙 범위(전압 0~60V, 전류 0~500A) 체크.
        범위를 벗어나면 경고창을 띄우고 False 를 리턴.
        """
        msgs = []

        if not (MIN_VOLTAGE <= voltage <= MAX_VOLTAGE):
            msgs.append(
                f"전압은 {MIN_VOLTAGE:.1f} ~ {MAX_VOLTAGE:.1f} V 범위로만 설정할 수 있습니다.\n"
                f"(현재 입력: {voltage:.1f} V)"
            )

        if not (MIN_CURRENT <= current <= MAX_CURRENT):
            msgs.append(
                f"전류는 {MIN_CURRENT:.1f} ~ {MAX_CURRENT:.1f} A 범위로만 설정할 수 있습니다.\n"
                f"(현재 입력: {current:.1f} A)"
            )

        if msgs:
            QMessageBox.warning(self, "설정 범위 초과", "\n\n".join(msgs))
            return False

        return True

    # ------------------------------------------------------------------
    # 버튼 핸들러
    # ------------------------------------------------------------------
    def on_set_value_clicked(self) -> None:
        """
        [설정 값 적용] 버튼:
        - 입력 전압/전류 읽기
        - 메뉴얼 스펙 범위(0~60V, 0~500A) 벗어나면 경고창만 띄우고 종료
        - 정상 범위면 graph.set_target() 으로 목표값 설정
        - 입력 파워 칸에 V*I 표시
        """
        voltage, current = self._read_input_voltage_current()

        if not self._validate_range(voltage, current):
            # 범위 초과 → target 설정/그래프 갱신 모두 막음
            return

        self.graph.set_target(voltage, current)
        self._update_input_power(voltage, current)

    def on_power_on_clicked(self) -> None:
        """
        [출력 ON] 버튼:
        - 현재 입력값을 읽어서 스펙 범위 체크
        - 범위를 벗어나면 경고창 띄우고 출력 시작 안 함
        - 범위 안이면 target 설정 + 입력 파워 계산 + 그래프 출력 시작
        """
        voltage, current = self._read_input_voltage_current()

        if not self._validate_range(voltage, current):
            return

        self.graph.set_target(voltage, current)
        self._update_input_power(voltage, current)
        self.graph.start_output()

    def on_power_off_clicked(self) -> None:
        """
        [출력 OFF] 버튼:
        - 그래프 포인트 추가 중단
        - X축 시간은 계속 흐름 (graph_controller 쪽에서 처리)
        """
        self.graph.stop_output()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
