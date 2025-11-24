# -*- coding: utf-8 -*-
"""
DCconverter.py

Maxwell MXR6020B DC-DC Converter 모듈을 RS-485(MODBUS RTU)로 제어하기 위한 라이브러리.

구성:
- RS-485 / MODBUS RTU 저수준 드라이버: Rs485Driver
- 장비 상태/알람 비트 정의
- 고수준 제어용 래퍼 클래스: DCConverter
- 유틸: list_serial_ports()

참고:
- 기존 1:1 테스트 프로그램(1to1_test_program.py)의 프레임 구성 / CRC / 레지스터 맵
- "MXR6020B RS485 Communication Protocol" 매뉴얼 (V1.01.01, 2024/11/28)
"""

from __future__ import annotations

import os
import time
import serial
import datetime
import struct
from dataclasses import dataclass
from typing import Optional, Tuple, List
from serial.tools import list_ports


# ---------- 로그 유틸 ----------
def ts() -> str:
    """현재 시간을 'YYYY-mm-dd HH:MM:SS.mmm' 형식으로 반환."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def ensure_log():
    """./logs 폴더에 세션 로그 파일을 하나 생성."""
    os.makedirs("logs", exist_ok=True)
    path = os.path.join(
        "logs",
        f"dcconverter_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
    )
    return open(path, "a", encoding="utf-8")


LOGF = ensure_log()


def log_line(line: str) -> None:
    """
    콘솔 + 로그 파일에 동시에 한 줄 출력.
    - 통신 프레임 디버깅용 (원하지 않으면 나중에 print 부분만 막아도 됨)
    """
    print(line)
    try:
        LOGF.write(line + "\n")
        LOGF.flush()
    except Exception:
        pass


def hex_bytes(b: bytes) -> str:
    """바이트열을 '01 03 00 65 ...' 형식의 헥사 문자열로 변환."""
    return " ".join(f"{x:02X}" for x in b)


def parse_hex_bytes(s: str) -> bytes:
    """
    '01 03 00 65', '0x01,0x03...' 등 다양한 헥사 문자열을 순수 바이트열로 변환.
    (원한다면 Raw 테스트용으로 사용할 수 있음)
    """
    s = (
        s.strip()
        .replace(" ", "")
        .replace(",", "")
        .replace("0x", "")
        .replace("0X", "")
    )
    if len(s) % 2 != 0:
        raise ValueError("짝수 길이의 헥사 문자열이어야 합니다.")
    return bytes.fromhex(s)


# ---------- CRC / 32비트 분해/결합 ----------
def crc16_modbus(data: bytes) -> int:
    """
    Modbus-RTU CRC16 (poly = 0xA001).
    반환값: 0x0000~0xFFFF (Low-Byte 먼저 전송).
    """
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def split_u32_to_words_be(u32: int) -> Tuple[int, int]:
    """
    32-bit 값을 상위워드/하위워드(빅엔디언 기준) 16-bit로 분리.
    예) 0x00061A80 -> (0x0006, 0x1A80)
    """
    if not (0 <= u32 <= 0xFFFFFFFF):
        raise ValueError("u32 범위 오류 (0~0xFFFFFFFF)")
    return (u32 >> 16) & 0xFFFF, u32 & 0xFFFF


def combine_words_to_u32_be(hi: int, lo: int) -> int:
    """
    상위워드/하위워드(16-bit) 두 개를 하나의 32-bit 값으로 결합.
    """
    return ((hi & 0xFFFF) << 16) | (lo & 0xFFFF)


# ---------- RS-485 / MODBUS RTU 기본 설정 ----------
RS485_BAUD = 9600     # 8N1, no parity
RS485_BYTESIZE = 8
RS485_PARITY = "N"
RS485_STOPBITS = 1

# 매뉴얼 기준 레지스터 주소들
REG_CTL = 101
REG_SET_V_H = 102
REG_SET_V_L = 103
REG_SET_I_H = 104
REG_SET_I_L = 105

REG_RO_PWR_ON = 301
REG_RO_V_H = 302
REG_RO_V_L = 303
REG_RO_I_H = 304
REG_RO_I_L = 305
REG_RO_ALM_H = 306
REG_RO_ALM_L = 307


@dataclass
class SerialConfig:
    port: str
    baud: int = RS485_BAUD
    bytesize: int = RS485_BYTESIZE
    parity: str = RS485_PARITY
    stopbits: int = RS485_STOPBITS
    timeout: float = 1.0


class Rs485Driver:
    """
    MXR6020B 모듈과 1:1로 통신하는 Modbus RTU 드라이버 (저수준).
    - 레지스터 단위 읽기/쓰기 (0x03 / 0x06 / 0x10)
    - V/I 읽기, V/I 설정+기동, 출력 정지 등의 편의 함수 제공
    """

    def __init__(self, cfg: SerialConfig, slave_addr: int):
        if serial is None:
            raise RuntimeError(
                "pyserial이 설치되어 있지 않습니다. "
                "pip install pyserial 로 설치 후 사용하세요."
            )
        if not (0 <= slave_addr <= 62):
            raise ValueError("RS-485 슬레이브 주소는 0~62 범위여야 합니다.")
        self.cfg = cfg
        self.addr = slave_addr
        self.ser: Optional[serial.Serial] = None

    # ----- 포트 열기 / 닫기 -----
    def open(self) -> None:
        log_line(
            f"[{ts()}] RS485 open: port={self.cfg.port}, baud={self.cfg.baud}, "
            f"{self.cfg.bytesize}{self.cfg.parity}{self.cfg.stopbits}"
        )
        self.ser = serial.Serial(
            port=self.cfg.port,
            baudrate=self.cfg.baud,
            bytesize=self.cfg.bytesize,
            parity=self.cfg.parity,
            stopbits=self.cfg.stopbits,
            timeout=self.cfg.timeout,
        )

    def close(self) -> None:
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass

    # ----- 저수준 송수신 -----
    def _write_frame(self, payload_wo_crc: bytes) -> None:
        crc = crc16_modbus(payload_wo_crc)
        frame = payload_wo_crc + bytes([crc & 0xFF, (crc >> 8) & 0xFF])  # Low, High
        log_line(f"[{ts()}] >> RS485  {hex_bytes(frame)}")
        self.ser.reset_input_buffer()
        self.ser.write(frame)
        self.ser.flush()

    def _read_exact(self, n: int, timeout: float) -> bytes:
        """
        n바이트 '정확히' 읽기.
        - 예전 방식은 in_waiting 만큼 한 번에 읽어버려서,
          헤더(3바이트)만 읽으려 할 때 응답 전체를 다 먹는 문제가 있었음.
        - 여기서는 pyserial의 read(n)에 timeout만 설정해서
          최대 n바이트까지만 읽도록 수정.
        """
        if n <= 0:
            return b""

        # 기존 타임아웃을 잠시 바꿨다가 다시 원복
        old_timeout = self.ser.timeout
        try:
            self.ser.timeout = timeout
            data = self.ser.read(n)  # 최대 n바이트까지만 읽음
            return data
        finally:
            self.ser.timeout = old_timeout

    # ----- 기능 코드 구현: 0x03 / 0x06 / 0x10 -----
    def read_holding_registers(
        self,
        start_reg: int,
        qty: int,
        timeout: float = 1.0,
    ) -> List[int]:
        """
        홀딩 레지스터 읽기 (0x03).
        - start_reg: 시작 주소
        - qty: 읽을 레지스터 개수 (1~30)
        반환: [UINT16, UINT16, ...]
        """
        if not (1 <= qty <= 30):
            raise ValueError("0x03 읽기 개수는 1~30 범위로 제한됩니다.")
        p = bytes([self.addr, 0x03]) + struct.pack(">HH", start_reg, qty)
        self._write_frame(p)

        # 응답: [addr][0x03][byte_count=N*2][data...][crc_lo][crc_hi]
        # 먼저 3바이트 읽고, byte_count를 보고 나머지(+2 CRC) 읽는다
        head = self._read_exact(3, timeout)
        if len(head) < 3:
            log_line(f"[{ts()}] << RS485  (no data)")
            return []
        addr, fn, bc = head[0], head[1], head[2]
        rest = self._read_exact(bc + 2, timeout)
        frame = head + rest
        log_line(f"[{ts()}] << RS485  {hex_bytes(frame)}")

        if len(rest) < bc + 2:
            raise RuntimeError("응답 길이 부족")

        # CRC 확인
        data = head + rest[:-2]
        rx_crc = rest[-2] | (rest[-1] << 8)
        if crc16_modbus(data) != rx_crc:
            raise RuntimeError("CRC 불일치")

        if addr != self.addr or fn != 0x03 or bc != qty * 2:
            raise RuntimeError("응답 포맷 오류")

        regs: List[int] = []
        for i in range(qty):
            w = (rest[i * 2] << 8) | rest[i * 2 + 1]
            regs.append(w)
        return regs

    def write_single_register(
        self,
        reg: int,
        value: int,
        timeout: float = 1.0,
    ) -> bool:
        """
        단일 레지스터 쓰기 (0x06).
        - reg: 레지스터 주소
        - value: UINT16
        성공 여부를 True/False로 반환.
        """
        p = bytes([self.addr, 0x06]) + struct.pack(">HH", reg, value & 0xFFFF)
        self._write_frame(p)
        resp = self._read_exact(8, timeout)  # 1+1+2+2+2
        log_line(f"[{ts()}] << RS485  {hex_bytes(resp) if resp else '(no data)'}")
        if len(resp) < 8:
            return False
        if crc16_modbus(resp[:-2]) != (resp[-2] | (resp[-1] << 8)):
            return False
        return resp[0] == self.addr and resp[1] == 0x06

    def write_multiple_registers(
        self,
        start_reg: int,
        values: List[int],
        timeout: float = 1.0,
    ) -> bool:
        """
        다중 레지스터 쓰기 (0x10).
        - start_reg: 시작 주소
        - values: UINT16 리스트 (1~30개)
        """
        qty = len(values)
        if not (1 <= qty <= 30):
            raise ValueError("0x10 쓰기 개수는 1~30 범위로 제한됩니다.")
        data = b"".join(struct.pack(">H", v & 0xFFFF) for v in values)
        p = (
            bytes([self.addr, 0x10])
            + struct.pack(">HHB", start_reg, qty, qty * 2)
            + data
        )
        self._write_frame(p)
        resp = self._read_exact(8, timeout)  # [addr][0x10][start][qty][crc]
        log_line(f"[{ts()}] << RS485  {hex_bytes(resp) if resp else '(no data)'}")
        if len(resp) < 8:
            return False
        if crc16_modbus(resp[:-2]) != (resp[-2] | (resp[-1] << 8)):
            return False
        return resp[0] == self.addr and resp[1] == 0x10

    # ----- 고수준 편의 기능 -----
    def read_vi(self, timeout: float = 1.0) -> Optional[Tuple[float, float]]:
        """
        출력 전압/전류 읽기.
        - 매뉴얼 기준 302~305: V(INT32), I(INT32) => 4 regs.
        반환: (전압[V], 전류[A]) 또는 실패 시 None
        """
        regs = self.read_holding_registers(REG_RO_V_H, 4, timeout=timeout)
        if len(regs) != 4:
            return None
        v_raw = combine_words_to_u32_be(regs[0], regs[1])
        i_raw = combine_words_to_u32_be(regs[2], regs[3])
        return (v_raw / 1000.0, i_raw / 1000.0)

    def read_alarm_mask(self, timeout: float = 1.0) -> Optional[int]:
        """
        알람 마스크(32bit) 읽기.
        - 306~307: UINT32
        """
        regs = self.read_holding_registers(REG_RO_ALM_H, 2, timeout=timeout)
        if len(regs) != 2:
            return None
        return combine_words_to_u32_be(regs[0], regs[1])

    def read_power_on_flag(self, timeout: float = 1.0) -> Optional[bool]:
        """
        전원(출력) 상태 플래그 읽기.
        - 301: 0=Shutdown, 1=Power on
        """
        regs = self.read_holding_registers(REG_RO_PWR_ON, 1, timeout=timeout)
        if len(regs) != 1:
            return None
        return bool(regs[0])

    def set_vi_and_start(
        self,
        volt_v: float,
        curr_a: float,
        timeout: float = 1.0,
    ) -> bool:
        """
        V/I 설정 + 출력 기동 (0x10, 101~105).
        - VOLT, CURR 는 단위 V/A, 내부적으로 *1000 후 INT32로 전송
        """
        v_mill = int(round(volt_v * 1000))
        i_mill = int(round(curr_a * 1000))
        v_hi, v_lo = split_u32_to_words_be(v_mill)
        i_hi, i_lo = split_u32_to_words_be(i_mill)
        # 101~105: [컨트롤(1=ON), V_hi, V_lo, I_hi, I_lo]
        vals = [1, v_hi, v_lo, i_hi, i_lo]
        return self.write_multiple_registers(REG_CTL, vals, timeout=timeout)

    def stop_output(self, timeout: float = 1.0) -> bool:
        """
        출력 정지 (0x06, 101=0).
        """
        return self.write_single_register(REG_CTL, 0, timeout=timeout)

    # (선택) RS-485 Raw 바이트 송수신 (디버깅용)
    def send_and_read_raw(
        self,
        data: bytes,
        read_len: Optional[int] = None,
        read_timeout: float = 1.0,
    ) -> bytes:
        """
        이미 CRC 등이 붙은 Raw 프레임을 그대로 송수신할 때 사용.
        - 일반적인 사용에서는 필요 없음 (디버깅용).
        """
        log_line(f"[{ts()}] >> RS485-RAW  {hex_bytes(data)}")
        self.ser.reset_input_buffer()
        self.ser.write(data)
        self.ser.flush()
        end = time.time() + read_timeout
        rx = bytearray()
        while time.time() < end:
            n = self.ser.in_waiting
            if n:
                rx += self.ser.read(n)
                if read_len is not None and len(rx) >= read_len:
                    break
            else:
                time.sleep(0.01)
        log_line(
            f"[{ts()}] << RS485-RAW  "
            f"{hex_bytes(bytes(rx)) if rx else '(no data)'}"
        )
        return bytes(rx)


# ---------- Alarm bit names ----------
ALARM_BITS = {
    0: "Power failure",
    1: "Power protection",
    4: "Input undervoltage",
    5: "Input overvoltage",
    6: "Input phase loss",
    10: "Serious uneven flow",
    12: "Address duplication",
    13: "Output status (0:on,1:off)",
    14: "Power derating",
    15: "Temperature derating",
    16: "AC derating",
    17: "Output overvoltage",
    18: "Output undervoltage",
    19: "Output short",
    20: "Over temperature",
    21: "Low temperature",
}


def list_serial_ports() -> List[str]:
    """
    현재 PC에 연결된 시리얼 포트 목록을 ['COM3', 'COM5', ...] 형식으로 반환.
    (GUI에서 콤보박스 채울 때 사용)
    """
    if list_ports is None:
        return []
    try:
        return [p.device for p in list_ports.comports()]
    except Exception:
        return []


# ---------- 고수준 래퍼: DCConverter ----------
class DCConverterError(Exception):
    """DCConverter 고수준 래퍼에서 사용하는 예외 형식."""


@dataclass
class DCStatus:
    power_on: bool
    voltage_v: float
    current_a: float
    alarm_mask: int
    active_alarms: List[str]


class DCConverter:
    """
    GUI / 상위 어플리케이션에서 쓰기 좋은 고수준 인터페이스.

    예시 사용:
        dc = DCConverter(timeout=0.5)
        dc.connect("COM3", slave_addr=1)
        dc.start_output(400.0, 20.0)
        status = dc.read_status()
        dc.stop_output()
        dc.close()
    """

    def __init__(self, timeout: float = 1.0):
        self._timeout = timeout
        self._drv: Optional[Rs485Driver] = None
        self._port: Optional[str] = None
        self._slave_addr: Optional[int] = None

    # ----- 내부 헬퍼 -----
    def _require_drv(self) -> Rs485Driver:
        if self._drv is None or self._drv.ser is None or not self._drv.ser.is_open:
            raise DCConverterError("RS-485 포트가 열려 있지 않습니다. connect()를 먼저 호출하세요.")
        return self._drv

    # ----- 연결 관리 -----
    def connect(self, port: str, slave_addr: int) -> None:
        """
        RS-485 포트를 열고 Maxwell 모듈과 연결.
        - port: 예) 'COM3'
        - slave_addr: 0~62
        """
        # 기존 연결 정리
        self.close()

        cfg = SerialConfig(port=port, timeout=self._timeout)
        drv = Rs485Driver(cfg, slave_addr=slave_addr)
        try:
            drv.open()
        except Exception as ex:
            raise DCConverterError(f"RS-485 포트 오픈 실패: {ex}") from ex

        self._drv = drv
        self._port = port
        self._slave_addr = slave_addr

    def close(self) -> None:
        """열려 있는 RS-485 포트를 닫는다."""
        if self._drv is not None:
            try:
                self._drv.close()
            except Exception:
                pass
        self._drv = None

    @property
    def is_connected(self) -> bool:
        """현재 포트가 열려 있는지 여부."""
        try:
            return (
                self._drv is not None
                and self._drv.ser is not None
                and self._drv.ser.is_open
            )
        except Exception:
            return False

    # ----- 장비 제어 -----
    def start_output(self, voltage_v: float, current_a: float) -> bool:
        """
        V/I 설정 + 출력 ON.
        - GUI의 [출력 ON] 버튼에 대응
        """
        drv = self._require_drv()
        try:
            ok = drv.set_vi_and_start(voltage_v, current_a, timeout=self._timeout)
        except Exception as ex:
            raise DCConverterError(
                f"장비에 V/I 설정 및 출력 ON 명령을 보내는 중 오류 발생: {ex}"
            ) from ex
        return ok

    def stop_output(self) -> bool:
        """
        출력 OFF.
        - GUI의 [출력 OFF] 버튼에 대응
        """
        drv = self._require_drv()
        try:
            ok = drv.stop_output(timeout=self._timeout)
        except Exception as ex:
            raise DCConverterError(
                f"장비에 출력 OFF 명령을 보내는 중 오류 발생: {ex}"
            ) from ex
        return ok

    def update_vi_while_running(self, voltage_v: float, current_a: float) -> bool:
        """
        출력 ON 상태에서 V/I 설정만 다시 보내고 싶을 때 사용.
        - Maxwell 프로토콜 상 set_vi_and_start()를 다시 보내면,
          컨트롤 레지스터 101=1(ON)을 유지한 채 V/I 값만 업데이트하는 효과.
        """
        return self.start_output(voltage_v, current_a)

    # ----- 상태 읽기 -----
    def read_vi(self) -> Tuple[float, float]:
        """
        현재 출력 전압/전류 읽기.
        반환: (전압[V], 전류[A])
        """
        drv = self._require_drv()
        try:
            vi = drv.read_vi(timeout=self._timeout)
        except Exception as ex:
            raise DCConverterError(
                f"장비에서 V/I 데이터를 읽는 중 오류 발생: {ex}"
            ) from ex

        if vi is None:
            raise DCConverterError("V/I 데이터를 읽지 못했습니다 (응답 없음 또는 CRC 오류).")
        return vi

    def read_alarm_mask(self) -> int:
        """
        알람 마스크 32bit 값만 읽기.
        """
        drv = self._require_drv()
        try:
            mask = drv.read_alarm_mask(timeout=self._timeout)
        except Exception as ex:
            raise DCConverterError(
                f"장비에서 알람 상태를 읽는 중 오류 발생: {ex}"
            ) from ex

        if mask is None:
            raise DCConverterError("알람 상태를 읽지 못했습니다 (응답 없음 또는 CRC 오류).")
        return mask

    def decode_alarms(self, alarm_mask: int) -> List[str]:
        """
        알람 마스크 값에서 활성 알람 문자열 리스트를 추출.
        """
        active = [
            f"bit{b}: {ALARM_BITS.get(b, '?')}"
            for b in ALARM_BITS
            if (alarm_mask & (1 << b))
        ]
        return active

    def read_status(self) -> DCStatus:
        """
        모듈의 현재 상태를 한 번에 읽어오는 편의 함수.
        - power_on: 레지스터 301 기준
        - voltage/current: 302~305 기준
        - alarm_mask + active_alarms: 306~307 + ALARM_BITS 기준
        """
        drv = self._require_drv()

        # 전원 ON/OFF 상태
        try:
            power_flag = drv.read_power_on_flag(timeout=self._timeout)
        except Exception as ex:
            raise DCConverterError(
                f"전원 상태(레지스터 301) 읽기 실패: {ex}"
            ) from ex

        power_on = bool(power_flag) if power_flag is not None else False

        # V/I
        try:
            vi = drv.read_vi(timeout=self._timeout)
        except Exception as ex:
            raise DCConverterError(
                f"V/I(302~305) 읽기 실패: {ex}"
            ) from ex

        if vi is None:
            voltage_v = 0.0
            current_a = 0.0
        else:
            voltage_v, current_a = vi

        # 알람
        try:
            mask = drv.read_alarm_mask(timeout=self._timeout)
        except Exception as ex:
            raise DCConverterError(
                f"알람 상태(306~307) 읽기 실패: {ex}"
            ) from ex

        alarm_mask = mask if mask is not None else 0
        active_alarms = self.decode_alarms(alarm_mask)

        return DCStatus(
            power_on=power_on,
            voltage_v=voltage_v,
            current_a=current_a,
            alarm_mask=alarm_mask,
            active_alarms=active_alarms,
        )
