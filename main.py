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

        # 버튼 시그널 연결
        self.powerOn_button.clicked.connect(self.on_power_on_clicked)
        self.powerOff_button.clicked.connect(self.on_power_off_clicked)
        self.setValue_button.clicked.connect(self.on_set_value_clicked)

        # 시작 상태: 출력 OFF 스타일
        self._update_output_state_ui(False)

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

    def _update_output_state_ui(self, on: bool) -> None:
        """
        출력 상태에 따라 ON/OFF 버튼 모양을 바꿔 준다.

        - OFF 상태:
            ON 버튼  : 기본 스타일, "출력 ON"
            OFF 버튼 : 빨간색 배경 + 흰 글씨 + 볼드, "출력 OFF (정지)"
        - ON 상태:
            ON 버튼  : 초록색 배경 + 흰 글씨 + 볼드, "출력 ON (동작중)"
            OFF 버튼 : 기본 스타일, "출력 OFF"
        """
        if on:
            # 출력 ON 상태
            self.powerOn_button.setText("출력 ON (동작중)")
            self.powerOn_button.setStyleSheet(
                "QPushButton {"
                "  background-color: rgb(0, 180, 0);"
                "  color: white;"
                "  font-weight: bold;"
                "}"
            )

            self.powerOff_button.setText("출력 OFF")
            self.powerOff_button.setStyleSheet("")
        else:
            # 출력 OFF 상태
            self.powerOn_button.setText("출력 ON")
            self.powerOn_button.setStyleSheet("")

            self.powerOff_button.setText("출력 OFF (정지)")
            self.powerOff_button.setStyleSheet(
                "QPushButton {"
                "  background-color: rgb(200, 0, 0);"
                "  color: white;"
                "  font-weight: bold;"
                "}"
            )

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

        ★ 출력 ON 상태에서도 이 버튼으로만 설정값 변경이 가능하게 두고,
          출력 ON 버튼은 단순히 "출력 시작" 역할만 한다.
        """
        voltage, current = self._read_input_voltage_current()

        if not self._validate_range(voltage, current):
            return

        self.graph.set_target(voltage, current)
        self._update_input_power(voltage, current)

    def on_power_on_clicked(self) -> None:
        """
        [출력 ON] 버튼:
        - 이미 출력 ON 상태라면:
            → 아무 설정도 바꾸지 않고
            → 안내 메시지만 띄움
        - 출력 OFF 상태라면:
            → 현재 입력값을 읽어서 스펙 범위 체크
            → 범위를 벗어나면 경고창 띄우고 출력 시작 안 함
            → 범위 안이면 target 설정 + 입력 파워 계산 + 그래프 출력 시작
        """
        # 이미 출력 ON이면 설정은 건드리지 않고 안내만
        if self.graph.is_output_on():
            QMessageBox.information(
                self,
                "출력 이미 ON",
                "이미 출력 ON 상태입니다.\n"
                "출력 중에 설정값을 변경하려면 [설정 값 적용] 버튼을 사용하세요.",
            )
            return

        # 아직 OFF 상태 → 출력 시작 절차
        voltage, current = self._read_input_voltage_current()

        if not self._validate_range(voltage, current):
            return

        self.graph.set_target(voltage, current)
        self._update_input_power(voltage, current)
        self.graph.start_output()
        self._update_output_state_ui(True)

    def on_power_off_clicked(self) -> None:
        """
        [출력 OFF] 버튼:
        - 이미 OFF면 안내만 띄움
        - ON이면 그래프 포인트 추가 중단 + 버튼 모양 OFF 상태로 변경
        """
        if not self.graph.is_output_on():
            QMessageBox.information(
                self,
                "출력 이미 OFF",
                "이미 출력 OFF 상태입니다.",
            )
            return

        self.graph.stop_output()
        self._update_output_state_ui(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
