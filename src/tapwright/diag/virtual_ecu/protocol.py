# SPDX-License-Identifier: Apache-2.0

"""The virtual ECU's UDS (ISO 14229) protocol state machine.

Deliberately has no socket, thread, or bus code in it — `handle_request` maps
request bytes to a `ProtocolResult` given the current session/security state,
nothing more. That separation is what makes this module testable at T1 (see
`tests/unit/test_virtual_ecu_protocol.py`) on any platform, including this
project's own CI matrix legs and a contributor's Windows laptop, without a
`vcan` interface anywhere in the loop. `transport.py` is the only module that
turns a `ProtocolResult` into bus traffic.

Service set implemented (see the scope note in
`tests/differential/test_virtual_ecu_uds.py`'s module docstring for what's
deliberately deferred): DiagnosticSessionControl (0x10), ReadDataByIdentifier
(0x22), WriteDataByIdentifier (0x2E), ReadDTCInformation (0x19), and
SecurityAccess (0x27) — request-seed/send-key mechanics only, never key
derivation (C-10).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .scenario import DIDConfig, FailureInjection, Scenario

# NRCs used here, verified against udsoncan.ResponseCode.ResponseCode
# (see docs/inf-05-simulator-reuse-evaluation.md's oracle discussion — this is
# the same independently-authored reference the differential tests hold the
# responder to).
NRC_GENERAL_REJECT = 0x10
NRC_SERVICE_NOT_SUPPORTED = 0x11
NRC_SUB_FUNCTION_NOT_SUPPORTED = 0x12
NRC_CONDITIONS_NOT_CORRECT = 0x22
NRC_REQUEST_SEQUENCE_ERROR = 0x24
NRC_REQUEST_OUT_OF_RANGE = 0x31
NRC_INVALID_KEY = 0x35

SID_DIAGNOSTIC_SESSION_CONTROL = 0x10
SID_READ_DTC_INFORMATION = 0x19
SID_READ_DATA_BY_IDENTIFIER = 0x22
SID_SECURITY_ACCESS = 0x27
SID_WRITE_DATA_BY_IDENTIFIER = 0x2E

POSITIVE_RESPONSE_OFFSET = 0x40
NEGATIVE_RESPONSE_SID = 0x7F

SESSION_DEFAULT = 0x01
SESSION_EXTENDED = 0x03
KNOWN_SESSIONS = frozenset({SESSION_DEFAULT, SESSION_EXTENDED, 0x02, 0x04})
# 0x02 (programmingSession) and 0x04 (safetySystemDiagnosticSession) are
# accepted as valid subfunctions per ISO 14229 even though this virtual ECU
# has no special behaviour for them yet — an unrecognised subfunction and a
# recognised-but-unimplemented one are different failure modes, and only the
# former is subFunctionNotSupported.

READ_DTC_REPORT_BY_STATUS_MASK = 0x02


@dataclass
class ProtocolResult:
    """What the protocol layer decided to do with one request.

    `transport.py` maps each kind to bus behaviour: "response" is sent
    through the ISO-TP stack normally, "silence" means nothing is sent at all
    (the timeout-injection case), and "malformed" means a deliberately broken
    raw frame is sent instead — see that module for why a raw frame is needed
    for that one case specifically.
    """

    kind: Literal["response", "silence", "malformed"]
    data: bytes = b""
    declared_length: int = 0


def _negative(sid: int, nrc: int) -> ProtocolResult:
    return ProtocolResult(kind="response", data=bytes([NEGATIVE_RESPONSE_SID, sid, nrc]))


def _positive(sid: int, payload: bytes = b"") -> ProtocolResult:
    return ProtocolResult(kind="response", data=bytes([sid + POSITIVE_RESPONSE_OFFSET]) + payload)


def _selector_for(sid: int, data: bytes) -> int | None:
    """The value a FailureInjection is matched against for this request: the
    DID for RDBI/WDBI, the sub-function for everything else.
    """
    if sid in (SID_READ_DATA_BY_IDENTIFIER, SID_WRITE_DATA_BY_IDENTIFIER):
        if len(data) >= 3:
            return (data[1] << 8) | data[2]
        return None
    if len(data) >= 2:
        return data[1]
    return None


@dataclass
class ProtocolState:
    """One virtual ECU's session/security state plus its `Scenario`.

    A fresh instance starts in `scenario.initial_session` with every security
    level locked — matching `test_scenario_config_selects_initial_session_and_did_values`.
    """

    scenario: Scenario
    session: int = field(init=False)
    unlocked_levels: set[int] = field(default_factory=set)
    _pending_seed_level: int | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.session = self.scenario.initial_session

    def handle_request(self, data: bytes) -> ProtocolResult:
        if not data:
            # No SID to echo back — ISO 14229 has no clean answer for a
            # zero-length request. Silence is the least-wrong option: it
            # matches how a well-formed frame with no payload byte can't even
            # be constructed by a real client, so a real ECU never has to
            # decide this either.
            return ProtocolResult(kind="silence")

        sid = data[0]
        injection = self.scenario.matching_injection(sid, _selector_for(sid, data))
        if injection is not None:
            if injection.kind == "timeout":
                return ProtocolResult(kind="silence")
            if injection.kind == "nrc":
                return _negative(sid, injection.nrc)
            if injection.kind == "truncated":
                return ProtocolResult(kind="malformed", declared_length=injection.declared_length)
            # "oversized" falls through to the normal handler below, which
            # consults the same injection to pad its response.

        if sid == SID_DIAGNOSTIC_SESSION_CONTROL:
            return self._session_control(data)
        if sid == SID_READ_DATA_BY_IDENTIFIER:
            return self._read_did(data, injection)
        if sid == SID_WRITE_DATA_BY_IDENTIFIER:
            return self._write_did(data)
        if sid == SID_READ_DTC_INFORMATION:
            return self._read_dtc_information(data)
        if sid == SID_SECURITY_ACCESS:
            return self._security_access(data)
        return _negative(sid, NRC_SERVICE_NOT_SUPPORTED)

    # -- DiagnosticSessionControl (0x10) ----------------------------------

    def _session_control(self, data: bytes) -> ProtocolResult:
        if len(data) < 2:
            return _negative(SID_DIAGNOSTIC_SESSION_CONTROL, 0x13)
        subfunction = data[1] & 0x7F  # top bit is suppressPosRspMsgIndicationBit
        if subfunction not in KNOWN_SESSIONS:
            return _negative(SID_DIAGNOSTIC_SESSION_CONTROL, NRC_SUB_FUNCTION_NOT_SUPPORTED)
        self.session = subfunction
        # P2/P2* timing parameters (ISO 14229-1 §9.2.2.3): 50ms / 5000ms,
        # fixed values — this virtual ECU makes no timing promises beyond
        # "fast enough not to be the bottleneck in a CI run".
        return _positive(
            SID_DIAGNOSTIC_SESSION_CONTROL, bytes([subfunction, 0x00, 0x32, 0x01, 0xF4])
        )

    # -- ReadDataByIdentifier (0x22) --------------------------------------

    def _read_did(self, data: bytes, injection: FailureInjection | None) -> ProtocolResult:
        if len(data) < 3:
            return _negative(SID_READ_DATA_BY_IDENTIFIER, 0x13)
        did = (data[1] << 8) | data[2]
        config = self.scenario.dids.get(did)
        if config is None:
            return _negative(SID_READ_DATA_BY_IDENTIFIER, NRC_REQUEST_OUT_OF_RANGE)
        if config.session_gate is not None and self.session != config.session_gate:
            return _negative(SID_READ_DATA_BY_IDENTIFIER, NRC_CONDITIONS_NOT_CORRECT)

        value = config.value
        if injection is not None and injection.kind == "oversized":
            value = value + bytes(injection.extra_bytes)

        return _positive(SID_READ_DATA_BY_IDENTIFIER, bytes([data[1], data[2]]) + value)

    # -- WriteDataByIdentifier (0x2E) --------------------------------------

    def _write_did(self, data: bytes) -> ProtocolResult:
        if len(data) < 3:
            return _negative(SID_WRITE_DATA_BY_IDENTIFIER, 0x13)
        did = (data[1] << 8) | data[2]
        config = self.scenario.dids.get(did)
        if config is None or config.read_only:
            return _negative(SID_WRITE_DATA_BY_IDENTIFIER, NRC_REQUEST_OUT_OF_RANGE)

        new_value = data[3:]
        self.scenario.dids[did] = DIDConfig(
            value=new_value, session_gate=config.session_gate, read_only=config.read_only
        )
        return _positive(SID_WRITE_DATA_BY_IDENTIFIER, bytes([data[1], data[2]]))

    # -- ReadDTCInformation (0x19) ------------------------------------------

    def _read_dtc_information(self, data: bytes) -> ProtocolResult:
        if len(data) < 2:
            return _negative(SID_READ_DTC_INFORMATION, 0x13)
        subfunction = data[1]
        if subfunction != READ_DTC_REPORT_BY_STATUS_MASK:
            return _negative(SID_READ_DTC_INFORMATION, NRC_SUB_FUNCTION_NOT_SUPPORTED)

        payload = bytes([subfunction, 0xFF])  # DTCStatusAvailabilityMask: all bits supported
        for dtc in self.scenario.dtcs:
            payload += dtc.code + bytes([dtc.status])
        return _positive(SID_READ_DTC_INFORMATION, payload)

    # -- SecurityAccess (0x27) — mechanics only, never derivation (C-10) ----

    def _security_access(self, data: bytes) -> ProtocolResult:
        if len(data) < 2:
            return _negative(SID_SECURITY_ACCESS, 0x13)
        subfunction = data[1]
        if subfunction == 0 or subfunction == 0x7F:
            # 0x00 and 0x7F are ISOSAEReserved (ISO 14229-1 Table 51) —
            # rejected before even considering whether a level is configured,
            # unlike an unconfigured-but-otherwise-valid subfunction below.
            return _negative(SID_SECURITY_ACCESS, NRC_SUB_FUNCTION_NOT_SUPPORTED)

        is_request_seed = subfunction % 2 == 1
        level = (subfunction + 1) // 2 if is_request_seed else subfunction // 2

        level_config = self.scenario.security_levels.get(level)
        if level_config is None:
            return _negative(SID_SECURITY_ACCESS, NRC_SUB_FUNCTION_NOT_SUPPORTED)

        if is_request_seed:
            self._pending_seed_level = level
            return _positive(SID_SECURITY_ACCESS, bytes([subfunction]) + level_config.seed)

        # send-key
        if self._pending_seed_level != level:
            return _negative(SID_SECURITY_ACCESS, NRC_REQUEST_SEQUENCE_ERROR)
        self._pending_seed_level = None

        key = data[2:]
        if key != level_config.key:
            return _negative(SID_SECURITY_ACCESS, NRC_INVALID_KEY)

        self.unlocked_levels.add(level)
        return _positive(SID_SECURITY_ACCESS, bytes([subfunction]))
