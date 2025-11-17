# main.py
import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QMessageBox

from ui.main_window import Ui_Form
from controller.graph_controller import PowerGraphWidget


class MainWindow(QWidget, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # 그래프 위젯 생성해서 Graph_widget 안에 넣기
        layout = QVBoxLayout(self.Graph_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.graph = PowerGraphWidget(
            parent=self.Graph_widget,
            output_power_edit=self.outputPower_edit,
            output_voltage_edit=self.outputVoltage_edit,
            output_current_edit=self.outputCurrent_edit,
        )
        layout.addWidget(self.graph)

        # 버튼 연결
        self.powerOn_button.clicked.connect(self.on_power_on_clicked)
        self.powerOff_button.clicked.connect(self.on_power_off_clicked)
        self.setValue_button.clicked.connect(self.on_set_value_clicked)

    # ------------------------------------------------------------------
    # 입력값 읽기 + 스펙 범위로 클램프
    # ------------------------------------------------------------------
    def _read_and_clamp_input_voltage_current(self) -> tuple[float, float]:
        """
        입력 박스에서 전압/전류 읽어서 float 로 변환 후
        스펙 범위 (V:0~60, A:0~500) 안으로 제한.
        제한된 값은 입력칸에도 다시 써 넣어 UI와 그래프가 항상 일치하게 만든다.
        """
        v_text = (self.inputVoltage_edit.text() or "").strip()
        i_text = (self.inputCurrent_edit.text() or "").strip()

        # 숫자 파싱
        try:
            v_raw = float(v_text) if v_text else 0.0
        except ValueError:
            self._show_error("전압 값이 숫자가 아닙니다.")
            v_raw = 0.0

        try:
            i_raw = float(i_text) if i_text else 0.0
        except ValueError:
            self._show_error("전류 값이 숫자가 아닙니다.")
            i_raw = 0.0

        # 스펙 범위로 제한
        v = max(0.0, min(60.0, v_raw))
        i = max(0.0, min(500.0, i_raw))

        # 만약 제한되었다면 입력 칸 텍스트도 실제 사용 값으로 맞춰준다
        if v != v_raw:
            self.inputVoltage_edit.setText(f"{v:.1f}")
        if i != i_raw:
            self.inputCurrent_edit.setText(f"{i:.1f}")

        return v, i

    def _update_input_power(self, voltage: float, current: float) -> float:
        """
        P = V * I 계산해서 입력 파워 칸에 표시하고 값을 리턴.
        (전달받은 voltage/current 는 이미 스펙 범위 안이라고 가정)
        """
        power = voltage * current
        self.inputPower_edit.setText(f"{power:.1f}")
        return power

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, "입력 오류", message)

    # ------------------------------------------------------------------
    # 버튼 핸들러
    # ------------------------------------------------------------------
    def on_set_value_clicked(self) -> None:
        """
        [설정 값 적용] 버튼:
        - 입력 전압/전류 읽어서 (스펙 범위로 제한)
        - graph.set_target() 으로 목표값 설정
        - 입력 파워 칸에 V*I 표시
        """
        voltage, current = self._read_and_clamp_input_voltage_current()
        self.graph.set_target(voltage, current)
        self._update_input_power(voltage, current)

    def on_power_on_clicked(self) -> None:
        """
        [출력 ON] 버튼:
        - 현재 입력값을 다시 읽어서 (스펙 범위로 제한)
        - graph.set_target() 으로 목표값 설정
        - 입력 파워 계산
        - 그래프 출력 시작
        """
        voltage, current = self._read_and_clamp_input_voltage_current()
        self.graph.set_target(voltage, current)
        self._update_input_power(voltage, current)
        self.graph.start_output()

    def on_power_off_clicked(self) -> None:
        """
        [출력 OFF] 버튼:
        - 그래프 포인트 추가만 중단
        - X축 시간은 계속 흐름
        """
        self.graph.stop_output()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
