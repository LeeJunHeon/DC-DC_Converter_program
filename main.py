# main.py
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QMessageBox,
)
from PySide6.QtCore import QTimer

from ui.main_window import Ui_Form
from controller.graph_controller import PowerGraphWidget
from controller.DCconverter_controller import (
    SerialConfig,
    Rs485Driver,
    list_serial_ports,
    ALARM_BITS,
)

# 메뉴얼 스펙 범위 (MXR6020B 기준)
MAX_VOLTAGE = 60.0   # V
MAX_CURRENT = 500.0  # A
MIN_VOLTAGE = 0.0
MIN_CURRENT = 0.0

# 치명적인(팝업을 띄울) 알람 비트 목록
CRITICAL_ALARM_BITS = {
    0,   # Power failure
    1,   # Power protection
    5,   # Input overvoltage
    6,   # Input phase loss
    10,  # Serious uneven flow
    12,  # Address duplication
    17,  # Output overvoltage
    19,  # Output short
    20,  # Over temperature
}

class MainWindow(QWidget, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # 측정 주기 기본값 1.0초
        self.inputTime_edit.setText("1.0")

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

        # Maxwell RS-485 드라이버 핸들
        self._rs485: Rs485Driver | None = None
        self._last_alarm_mask = None  # 최근 알람 값 저장(옵션)
        self._last_alarm_popup_mask = 0  # 마지막으로 팝업을 띄운 알람 마스크

        # 출력 / 설정 / 녹화 버튼 시그널
        self.powerOn_button.clicked.connect(self.on_power_on_clicked)
        self.powerOff_button.clicked.connect(self.on_power_off_clicked)
        self.setValue_button.clicked.connect(self.on_set_value_clicked)
        self.recodeStart_button.clicked.connect(self.on_record_start_clicked)
        self.recodeStop_button.clicked.connect(self.on_record_stop_clicked)
        
        # 측정 주기 적용 버튼
        self.intputTime_button.clicked.connect(self.on_measure_interval_apply_clicked)

        # 통신 설정 UI 초기화
        self.slaveID_spinBox.setRange(0, 62)
        self.slaveID_spinBox.setValue(0)
        self.connect_button.clicked.connect(self.on_connect_button_clicked)

        # COM 포트 목록 한번 채우기
        self._refresh_com_ports()

        # 출력 버튼 초기 상태
        self._update_output_state_ui(False)

        # 녹화 버튼 깜빡임 설정
        self._record_start_default_text = self.recodeStart_button.text()
        self._record_start_default_style = self.recodeStart_button.styleSheet()
        self._record_blink_state = False

        self._record_blink_timer = QTimer(self)
        self._record_blink_timer.setInterval(500)  # 0.5초
        self._record_blink_timer.timeout.connect(self._on_record_blink)

    # ---------------------------------------------------------------
    # 창 닫힐 때 장비 포트 정리
    # ---------------------------------------------------------------
    def closeEvent(self, event):
        try:
            if self._rs485 is not None:
                self._rs485.close()
        except Exception:
            pass
        event.accept()

    # ---------------------------------------------------------------
    # 공통 유틸
    # ---------------------------------------------------------------
    def _read_input_voltage_current(self):
        """입력 전압/전류를 float 로 변환 (숫자 에러는 메시지 표시)."""
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
        범위를 벗어나면 경고창을 띄우고 False 리턴.
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
        """
        if on:
            # 출력 ON 상태
            self.powerOn_button.setText("출력 ON (운전중)")
            self.powerOn_button.setStyleSheet(
                "QPushButton {"
                "  background-color: rgb(0, 180, 0);"
                "  color: white;"
                "  font-weight: bold;"
                "}"
            )

            self.powerOff_button.setText("출력 OFF (누르면 정지)")
            self.powerOff_button.setStyleSheet("")
        else:
            # 출력 OFF 상태
            self.powerOn_button.setText("출력 ON (정지)")
            self.powerOn_button.setStyleSheet("")

            self.powerOff_button.setText("출력 OFF (정지)")
            self.powerOff_button.setStyleSheet(
                "QPushButton {"
                "  background-color: rgb(200, 0, 0);"
                "  color: white;"
                "  font-weight: bold;"
                "}"
            )

    # ---------------------------------------------------------------
    # COM 포트 / RS-485 연결 관리
    # ---------------------------------------------------------------
    def _refresh_com_ports(self) -> None:
        ports = list_serial_ports()  # 예: ["COM3", "COM4"]
        self.comPort_comboBox.clear()

        # 안내용 첫 줄 (원하면 빼도 됨)
        self.comPort_comboBox.addItem("COM 포트 선택")

        if ports:
            # ★ 리스트를 한 번에 추가할 때는 addItems 사용
            self.comPort_comboBox.addItems(ports)
        else:
            # 실제 포트가 하나도 없으면 안내만 남겨두기
            pass

    def _ensure_rs485_connected(self) -> bool:
        """
        UI에 선택된 COM 포트 / Slave ID 기준으로
        Rs485Driver 가 준비되어 있는지 확인.
        - 같은 설정으로 이미 열려 있으면 그대로 사용
        - 포트/주소가 바뀌었거나 포트가 죽었으면 다시 연다
        """
        port = (self.comPort_comboBox.currentText() or "").strip()
        slave = int(self.slaveID_spinBox.value())

        if not port:
            self._show_error("COM 포트를 선택해 주세요.")
            return False

        # 이미 같은 설정으로 열려 있으면 그대로 사용
        if self._rs485 is not None:
            try:
                if (
                    self._rs485.ser is not None
                    and self._rs485.ser.is_open
                    and self._rs485.cfg.port == port
                    and self._rs485.addr == slave
                ):
                    return True
            except Exception:
                pass

            # 설정이 바뀌었거나 포트가 죽었으면 닫고 다시
            try:
                self._rs485.close()
            except Exception:
                pass
            self._rs485 = None

        cfg = SerialConfig(port=port)
        try:
            drv = Rs485Driver(cfg, slave_addr=slave)
            drv.open()
        except Exception as ex:
            self._show_error(f"RS-485 포트 오픈 실패:\n{ex}")
            return False

        self._rs485 = drv

        def sample_provider():
            """
            장비에서 (P, V, I) + 알람 마스크를 읽어 옴.
            - VI 읽기 실패 시 None 반환 (그래프 추가 안 함)
            - 알람 읽기 실패는 그래프에 영향 주지 않음
            """
            if self._rs485 is None:
                return None

            # 1) VI 읽기
            try:
                vi = self._rs485.read_vi(timeout=0.5)
            except Exception:
                return None

            if vi is None:
                return None

            voltage, current = vi
            power = voltage * current

            # 2) 알람 마스크도 같은 주기로 읽어 둠
            try:
                alarm_mask = self._rs485.read_alarm_mask(timeout=0.5)
                # 최근 알람 값 저장
                self._last_alarm_mask = alarm_mask

                # 알람이 있고(마스크 != 0), 이전에 같은 마스크로 팝업을 띄운 적이 없으면 팝업
                if (
                    isinstance(alarm_mask, int)
                    and alarm_mask != 0
                    and alarm_mask != self._last_alarm_popup_mask
                ):
                    self._handle_alarm_mask(alarm_mask)
            except Exception:
                # 알람 읽기 실패는 일단 무시 (통신 상태만 로그 등으로 처리 가능)
                pass

            return power, voltage, current

        # ★ 그래프에서 Maxwell 실측값을 사용하도록 샘플 공급자 연결
        self.graph.set_sample_provider(sample_provider)

        return True

    def on_connect_button_clicked(self) -> None:
        """
        [연결] 버튼:
        - 현재 선택된 COM / Slave 로 드라이버를 열어 본다.
        """
        if self._ensure_rs485_connected():
            QMessageBox.information(
                self,
                "연결 성공",
                f"Maxwell 통신이 설정되었습니다.\n"
                f"포트: {self.comPort_comboBox.currentText()}, "
                f"Slave ID: {self.slaveID_spinBox.value()}",
            )

    # ---------------------------------------------------------------
    # 설정 값 적용
    # ---------------------------------------------------------------
    def on_set_value_clicked(self) -> None:
        """
        [설정 값 적용] 버튼:
        - 전압/전류 입력칸이 비어 있으면 경고
        - 스펙 범위 체크
        - 장비가 연결 + 출력 ON 상태일 때만
          그래프 / 입력 파워 / Maxwell 설정을 변경
        """
        v_text = (self.inputVoltage_edit.text() or "").strip()
        i_text = (self.inputCurrent_edit.text() or "").strip()
        if not v_text or not i_text:
            QMessageBox.warning(
                self,
                "입력 필요",
                "전압과 전류를 먼저 입력해 주세요.",
            )
            return

        # 숫자 변환 + 범위 체크 (기존 그대로)
        voltage, current = self._read_input_voltage_current()
        if not self._validate_range(voltage, current):
            return

        # ---- [추가] 장비 연결 / 출력 상태 확인 ----
        rs485_connected = False
        if self._rs485 is not None:
            try:
                if (
                    getattr(self._rs485, "ser", None) is not None
                    and self._rs485.ser.is_open
                ):
                    rs485_connected = True
            except Exception:
                rs485_connected = False

        # ▶ 장비가 연결 안 되었거나, 출력이 OFF면: 알림만 띄우고 아무것도 안 함
        if (not rs485_connected) or (not self.graph.is_output_on()):
            QMessageBox.information(
                self,
                "출력 OFF 또는 미연결",
                "장비 출력이 OFF 상태이거나 Maxwell 장비와 RS-485 통신이 연결되어 있지 않습니다.\n"
                "이번 설정 값은 적용되지 않았습니다.\n\n"
                "[연결] 버튼으로 통신을 먼저 연결하고, [출력 ON] 후에 다시 시도해 주세요.",
            )
            return

        # ---- 여기부터는 '장비 연결 + 출력 ON'인 경우에만 실행 ----
        # 그래프 target / 입력 파워 갱신 (왼쪽 UI)
        self.graph.set_target(voltage, current)
        self._update_input_power(voltage, current)

        # Maxwell 장비에도 실제 V/I 적용 (기존 코드 그대로)
        if self._rs485 is not None:
            try:
                ok = self._rs485.set_vi_and_start(voltage, current, timeout=1.0)
            except Exception as ex:
                self._show_error(
                    "장비에 새로운 V/I 설정을 보내는 중 오류가 발생했습니다:\n"
                    f"{ex}"
                )
                return

            if not ok:
                self._show_error(
                    "장비에 새로운 V/I 설정을 보내지 못했습니다.\n"
                    "배선, 슬레이브 주소, 통신 속도 등을 확인해 주세요."
                )

    # ---------------------------------------------------------------
    # 출력 ON / OFF
    # ---------------------------------------------------------------
    def on_power_on_clicked(self) -> None:
        """
        [출력 ON] 버튼:
        - 이미 ON이면 안내만 표시
        - OFF -> ON 전환 시 입력값/범위 체크 후
          1) RS-485 연결 확보
          2) Maxwell 모듈에 V/I 설정 + 출력 ON 명령
          3) 그래프 출력 시작 (이후 1초마다 장비에서 읽어 그래프)
        """
        if self.graph.is_output_on():
            QMessageBox.information(
                self,
                "출력 이미 ON",
                "이미 출력 ON 상태입니다.\n"
                "출력 중에 설정값을 변경하려면 [설정 값 적용] 버튼을 사용하세요.",
            )
            return

        v_text = (self.inputVoltage_edit.text() or "").strip()
        i_text = (self.inputCurrent_edit.text() or "").strip()
        if not v_text or not i_text:
            QMessageBox.warning(
                self,
                "입력 필요",
                "전압과 전류를 먼저 입력해 주세요.",
            )
            return

        voltage, current = self._read_input_voltage_current()
        if not self._validate_range(voltage, current):
            return

        # RS-485 연결 준비
        if not self._ensure_rs485_connected():
            return

        # Maxwell 모듈에 V/I 설정 + 출력 ON
        try:
            ok = self._rs485.set_vi_and_start(voltage, current, timeout=1.0)
        except Exception as ex:
            self._show_error(
                "장비에 V/I 설정 및 기동(출력 ON) 명령을 보내는 중 오류가 발생했습니다:\n"
                f"{ex}"
            )
            return

        if not ok:
            self._show_error(
                "장비에 V/I 설정 또는 기동(출력 ON) 명령이 실패했습니다.\n"
                "배선 / 슬레이브 주소 / 통신 속도 등을 다시 확인해 주세요."
            )
            return

        # 그래프 쪽 상태 갱신
        self.graph.set_target(voltage, current)
        self._update_input_power(voltage, current)
        self.graph.start_output()
        self._update_output_state_ui(True)

    def on_power_off_clicked(self) -> None:
        """
        [출력 OFF] 버튼:
        - 이미 OFF면 안내만 표시
        - ON -> OFF 전환 시
          1) 장비에 출력 OFF 명령
          2) 그래프 출력 중단
        """
        if not self.graph.is_output_on():
            QMessageBox.information(
                self,
                "출력 이미 OFF",
                "이미 출력 OFF 상태입니다.",
            )
            return

        # Maxwell 모듈 출력 OFF
        if self._rs485 is not None:
            try:
                ok = self._rs485.stop_output(timeout=1.0)
            except Exception as ex:
                self._show_error(
                    "장비에 출력 OFF 명령을 보내는 중 오류가 발생했습니다:\n"
                    f"{ex}"
                )
                ok = False

            if not ok:
                QMessageBox.warning(
                    self,
                    "장비 출력 OFF 실패",
                    "장비에 출력 OFF 명령을 보내지 못했습니다.\n"
                    "하지만 프로그램 내 그래프 출력은 중지합니다.",
                )

        self.graph.stop_output()
        self._update_output_state_ui(False)

    # ---------------------------------------------------------------
    # 장비 알림/오류 버튼
    # ---------------------------------------------------------------
    def on_device_error_clicked(self) -> None:
        """
        [장비 알림/오류] 버튼:
        1) 장비 알람 레지스터(306~307) 읽어서 디코딩
        2) 최근 로그 파일(dcconverter_*.txt)의 마지막 몇 줄을 함께 표시
        """
        alarm_text = self._get_alarm_summary()
        log_text = self._get_recent_log_summary()

        full_text = (
            "[장비 알람 상태]\n"
            f"{alarm_text}\n\n"
            "[최근 로그]\n"
            f"{log_text}"
        )

        QMessageBox.information(self, "장비 알림 / 오류", full_text)

    def _get_alarm_summary(self) -> str:
        """현재 장비 알람 상태를 텍스트로 정리."""
        if self._rs485 is None or self._rs485.ser is None or not self._rs485.ser.is_open:
            return "장비와 연결되어 있지 않습니다.\n(먼저 COM 포트와 Slave ID를 설정하고 [연결] 버튼을 눌러 주세요.)"

        try:
            mask = self._rs485.read_alarm_mask(timeout=1.0)
        except Exception as ex:
            return f"알람 레지스터 읽기 실패: {ex}"

        if mask is None:
            return "알람 상태를 읽지 못했습니다. (응답 없음 또는 CRC 오류)"

        lines = [f"Alarm Mask: 0x{mask:08X}"]

        active_bits = [b for b in ALARM_BITS.keys() if (mask & (1 << b))]
        if not active_bits:
            lines.append("→ 활성화된 알람이 없습니다.")
        else:
            lines.append("→ 활성 알람 목록:")
            for b in sorted(active_bits):
                desc = ALARM_BITS.get(b, "?")
                lines.append(f"  - bit{b}: {desc}")

        return "\n".join(lines)

    def _get_recent_log_summary(self, max_lines: int = 50) -> str:
        """
        logs/ 폴더에서 가장 최근 dcconverter_*.txt 파일을 찾아
        마지막 max_lines 줄만 문자열로 반환.
        """
        logs_dir = Path.cwd() / "logs"
        if not logs_dir.exists():
            return "로그 폴더(logs)가 없습니다."

        # dcconverter_*.txt 파일이 있으면 그 중 최신, 없으면 .txt 전체 중 최신
        txt_files = sorted(logs_dir.glob("dcconverter_*.txt"))
        if not txt_files:
            txt_files = sorted(logs_dir.glob("*.txt"))
        if not txt_files:
            return "로그 파일이 없습니다."

        latest = max(txt_files, key=lambda p: p.stat().st_mtime)

        try:
            lines = latest.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception as ex:
            return f"로그 파일({latest.name})을 읽는 중 오류: {ex}"

        tail = lines[-max_lines:] if len(lines) > max_lines else lines
        # 너무 길어지지 않도록 앞에 파일 이름 한 줄 붙이고 보여주기
        header = f"파일: {latest.name} (마지막 {len(tail)}/{len(lines)} 줄)\n"
        return header + "\n".join(tail)
    
    # ---------------------------------------------------------------
    # 치명 알람 판별 + 자동 팝업
    # ---------------------------------------------------------------
    def _has_critical_alarm(self, mask: int | None) -> bool:
        """알람 마스크 안에 치명 알람 비트가 하나라도 있는지 검사."""
        if mask is None:
            return False

        for bit in CRITICAL_ALARM_BITS:
            if mask & (1 << bit):
                return True
        return False

    def _handle_alarm_mask(self, mask: int) -> None:
        """
        치명 알람만 골라서 팝업을 띄운다.
        - CRITICAL_ALARM_BITS 에 정의된 비트 중 켜진 것만 메시지에 포함
        - 치명 알람이 없으면 아무 것도 하지 않음
        """
        if not self._has_critical_alarm(mask):
            # 치명 알람이 없으면 팝업 띄우지 않음
            return

        # 켜져 있는 치명 알람 비트만 추출
        active_bits = [b for b in sorted(CRITICAL_ALARM_BITS) if (mask & (1 << b))]
        if not active_bits:
            return

        lines = [f"Alarm Mask: 0x{mask:08X}", "→ 치명 알람 목록:"]
        for b in active_bits:
            desc = ALARM_BITS.get(b, "?")
            lines.append(f"  - bit{b}: {desc}")

        msg = (
            "장비에서 치명적인 알람이 감지되었습니다.\n\n"
            + "\n".join(lines)
            + "\n\n이 알람 상태가 유지되는 동안은 장비 및 배선을 반드시 점검해 주세요."
        )

        QMessageBox.warning(self, "장비 치명 알람", msg)

        # 이 마스크 값으로 팝업을 띄웠다고 기록
        self._last_alarm_popup_mask = mask

    # ---------------------------------------------------------------
    # 녹화 시작 / 중지
    # ---------------------------------------------------------------
    def on_record_start_clicked(self) -> None:
        """
        [녹화 시작] 버튼:

        - 반드시 출력 ON 상태에서만 녹화 가능
        - 이미 녹화 중이면 안내만 표시
        - 전압/전류 입력칸 비어 있으면 경고
        - 범위 체크 후 graph.start_recording() 호출
        - 버튼을 비활성화 + 텍스트 "녹화 중" 으로 변경
        - 버튼 배경을 빨간색으로 깜빡이게 함
        - 알림창(확인 버튼) 없이 바로 녹화 시작
        """
        # 이미 녹화 중이면
        if self.graph.is_recording():
            QMessageBox.information(
                self,
                "이미 녹화 중",
                "이미 녹화가 진행 중입니다.\n"
                "녹화를 다시 시작하려면 먼저 [녹화 중지] 버튼을 눌러 주세요.",
            )
            return

        # 출력 ON 상태에서만 녹화 허용
        if not self.graph.is_output_on():
            QMessageBox.warning(
                self,
                "출력 OFF",
                "출력이 ON 상태일 때만 녹화를 시작할 수 있습니다.",
            )
            return

        v_text = (self.inputVoltage_edit.text() or "").strip()
        i_text = (self.inputCurrent_edit.text() or "").strip()
        if not v_text or not i_text:
            QMessageBox.warning(
                self,
                "입력 필요",
                "녹화를 시작하려면 전압과 전류를 먼저 입력해 주세요.",
            )
            return

        voltage, current = self._read_input_voltage_current()
        if not self._validate_range(voltage, current):
            return

        input_power = self._update_input_power(voltage, current)

        file_path  = self.graph.start_recording(
            input_power=input_power,
            input_voltage=voltage,
            input_current=current,
        )

        # 추가: 녹화 파일 경로 안내
        QMessageBox.information(
            self,
            "녹화 시작",
            f"데이터 녹화를 시작했습니다.\n\n"
            f"저장 파일:\n{file_path}",
        )

        self.recodeStart_button.setEnabled(False)
        self.recodeStart_button.setText("녹화 중")

        # 깜빡임 시작
        self._record_blink_state = False
        self._record_blink_timer.start()
        self._apply_record_blink_style()

    def on_record_stop_clicked(self) -> None:
        """
        [녹화 중지] 버튼:
        - 녹화 중이 아니면 안내만 표시
        - 녹화 중이면 CSV 파일 닫고 경로는 내부적으로만 보관
        - 녹화 버튼을 다시 '녹화 시작' 으로 되돌리고 깜빡임 중단
        - 알림창 없이 바로 종료
        """
        if not self.graph.is_recording():
            QMessageBox.information(
                self,
                "녹화 중 아님",
                "현재 진행 중인 녹화가 없습니다.",
            )
            return

        file_path = self.graph.stop_recording()

        if file_path:
            QMessageBox.information(
                self,
                "녹화 중지",
                f"녹화를 종료했습니다.\n\n"
                f"저장 파일:\n{file_path}",
            )

        # 깜빡임 중단 + 버튼 원상복구
        self._record_blink_timer.stop()
        self.recodeStart_button.setEnabled(True)
        self.recodeStart_button.setText(self._record_start_default_text)
        self.recodeStart_button.setStyleSheet(self._record_start_default_style)

    # ---------------------------------------------------------------
    # 녹화 버튼 깜빡임 처리
    # ---------------------------------------------------------------
    def _on_record_blink(self) -> None:
        """0.5초마다 호출되어 녹화 버튼 색을 토글."""
        if not self.graph.is_recording():
            # 안전장치: 그래프 쪽 상태가 바뀌었으면 타이머 정지
            self._record_blink_timer.stop()
            self.recodeStart_button.setEnabled(True)
            self.recodeStart_button.setText(self._record_start_default_text)
            self.recodeStart_button.setStyleSheet(self._record_start_default_style)
            return

        self._record_blink_state = not self._record_blink_state
        self._apply_record_blink_style()

    def _apply_record_blink_style(self) -> None:
        """_record_blink_state 값에 따라 버튼 스타일을 변경."""
        if self._record_blink_state:
            # 빨간색 배경
            self.recodeStart_button.setStyleSheet(
                "QPushButton {"
                "  background-color: rgb(220, 0, 0);"
                "  color: white;"
                "  font-weight: bold;"
                "}"
            )
        else:
            # 옅은 배경 + 빨간 테두리
            self.recodeStart_button.setStyleSheet(
                "QPushButton {"
                "  background-color: rgb(255, 255, 255);"
                "  color: rgb(220, 0, 0);"
                "  font-weight: bold;"
                "  border: 2px solid rgb(220, 0, 0);"
                "}"
            )

    # ---------------------------------------------------------------
    # 측정 주기 적용 (상단 inputTime_edit + intputTime_button)
    # ---------------------------------------------------------------
    def on_measure_interval_apply_clicked(self) -> None:
        """
        상단 [측정 주기(초)] 입력값을 읽어서
        - 0.5초 미만 입력 시: 경고창 띄우고, 주기는 변경하지 않음
        - 0.5초 이상이면: 그래프/샘플 갱신 간격을 해당 초로 변경
        """
        text = (self.inputTime_edit.text() or "").strip()
        if not text:
            QMessageBox.warning(
                self,
                "입력 필요",
                "측정 주기를 초 단위로 입력해 주세요.\n예) 1.0",
            )
            return

        try:
            sec = float(text)
        except ValueError:
            QMessageBox.warning(
                self,
                "입력 오류",
                "측정 주기는 숫자로 입력해 주세요.\n예) 1.0",
            )
            return

        # 0.5초 미만은 허용하지 않음 (0.5 이상부터 허용)
        if sec < 0.5:
            QMessageBox.warning(
                self,
                "측정 주기 제한",
                "측정 주기는 0.5초 이상으로만 설정할 수 있습니다.\n"
                "(장비 보호를 위해 0.5초 미만은 사용할 수 없습니다.)",
            )
            # 사용자가 다시 입력하도록, 기본값으로 돌려놓고 끝냄
            self.inputTime_edit.setText("1.0")
            return

        # 그래프/샘플 갱신 주기 변경
        self.graph.set_update_interval(sec)

        QMessageBox.information(
            self,
            "측정 주기 변경",
            f"전압/전류/파워 및 알람 측정 주기를 {sec:.2f}초로 설정했습니다.",
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
