# pyright: reportMissingImports=false
import unittest

from parameterized import parameterized
from utils.channel_access import ChannelAccess
from utils.ioc_launcher import get_default_ioc_dir
from utils.test_modes import TestModes
from utils.testing import get_running_lewis_and_ioc, parameterized_list, skip_if_recsim

DEVICE_PREFIX = "G3HALLPR_01"

SCALES = [
    1,
    -1,
    1,
]


IOCS = [
    {
        "name": DEVICE_PREFIX,
        "directory": get_default_ioc_dir("G3HALLPR"),
        "macros": {
            "FIELD_SCAN_RATE": ".1 second",
            "TEMP_SCAN_RATE": ".1 second",
            "SCALE0": SCALES[0],
            "SCALE1": SCALES[1],
            "SCALE2": SCALES[2],
        },
        "emulator": "group3hallprobe",
    },
]


TEST_MODES = [TestModes.DEVSIM]

PROBE_IDS = [0, 1, 2]


class Group3HallprobeTests(unittest.TestCase):
    """
    Tests for the Group 3 hall probe IOC.
    """

    def setUp(self):
        self._lewis, self._ioc = get_running_lewis_and_ioc("group3hallprobe", DEVICE_PREFIX)
        self.ca = ChannelAccess(
            device_prefix=DEVICE_PREFIX, default_wait_time=0.0, default_timeout=10.0
        )
        self._lewis.backdoor_run_function_on_device("reset")
        for probe_id in PROBE_IDS:
            self.ca.assert_that_pv_alarm_is(f"{probe_id}:TEMPERATURE", self.ca.Alarms.NONE)
            self.ca.assert_that_pv_alarm_is(f"{probe_id}:FIELD:_RAW", self.ca.Alarms.NONE)

    def _set_temperature(self, probe_id: int, temperature: float):
        self._lewis.backdoor_run_function_on_device(
            "backdoor_set_temperature", [probe_id, temperature]
        )

    def _set_field(self, probe_id: int, field: float):
        self._lewis.backdoor_run_function_on_device("backdoor_set_field", [probe_id, field])

    def _set_initialized(self, probe_id: int, init: bool):
        self._lewis.backdoor_run_function_on_device("backdoor_set_initialized", [probe_id, init])

    @parameterized.expand(parameterized_list(PROBE_IDS))
    @skip_if_recsim("Uses emulator backdoor")
    def test_GIVEN_connected_inrange_device_THEN_can_read_raw_field(self, _: str, probe_id: int):
        self._set_field(probe_id, 123.456)
        self.ca.assert_that_pv_is(f"{probe_id}:FIELD:_RAWSTR", "123.456")
        self.ca.assert_that_pv_is_number(f"{probe_id}:FIELD:_RAW", 123.456, tolerance=0.0001)
        self.ca.assert_that_pv_alarm_is(f"{probe_id}:FIELD:_RAW", self.ca.Alarms.NONE)

    @parameterized.expand(parameterized_list(PROBE_IDS))
    @skip_if_recsim("Uses emulator backdoor")
    def test_GIVEN_connected_device_THEN_can_read_temperature(self, _: str, probe_id: int):
        self._set_temperature(probe_id, 456.321)
        self.ca.assert_that_pv_is_number(f"{probe_id}:TEMPERATURE", 456.321, tolerance=0.0001)

    @parameterized.expand(parameterized_list(PROBE_IDS))
    @skip_if_recsim("Uses emulator backdoor")
    def test_GIVEN_overrange_device_THEN_field_invalid(self, _: str, probe_id: int):
        self._set_field(probe_id, 999_999_999_999)
        self.ca.assert_that_pv_is(f"{probe_id}:FIELD:_RAWSTR", "OVER RANGE")
        self.ca.assert_that_pv_alarm_is(f"{probe_id}:FIELD:_RAWSTR", self.ca.Alarms.NONE)
        self.ca.assert_that_pv_alarm_is(f"{probe_id}:FIELD:_RAW", self.ca.Alarms.INVALID)

    @parameterized.expand(parameterized_list(PROBE_IDS))
    @skip_if_recsim("Uses emulator backdoor")
    def test_GIVEN_disconnected_device_THEN_field_invalid(self, _: str, probe_id: int):
        with self._lewis.backdoor_simulate_disconnected_device():
            self.ca.assert_that_pv_alarm_is(f"{probe_id}:FIELD:_RAWSTR", self.ca.Alarms.INVALID)
            self.ca.assert_that_pv_alarm_is(f"{probe_id}:FIELD:_RAW", self.ca.Alarms.INVALID)
            self.ca.assert_that_pv_alarm_is(f"{probe_id}:FIELD", self.ca.Alarms.INVALID)
            self.ca.assert_that_pv_alarm_is(f"{probe_id}:TEMPERATURE", self.ca.Alarms.INVALID)

    @parameterized.expand(parameterized_list(PROBE_IDS))
    @skip_if_recsim("Uses emulator backdoor")
    def test_GIVEN_conencted_device_THEN_can_change_ranges(self, _: str, probe_id: int):
        self._set_field(probe_id, 1)  # Should change down to r0 for this low field
        self.ca.assert_that_pv_is(f"{probe_id}:RANGE:SP", "0.3 Tesla")
        self.ca.assert_that_pv_is(f"{probe_id}:STATEMACHINE:STATE", "r0")
        self.ca.assert_that_pv_is_number(f"{probe_id}:FIELD:_RAW", 1, tolerance=0.0001)

        self._set_field(probe_id, 2901)  # Just above r0 move up point
        self.ca.assert_that_pv_is(f"{probe_id}:RANGE:SP", "0.6 Tesla")
        self.ca.assert_that_pv_is(f"{probe_id}:STATEMACHINE:STATE", "r1")
        self.ca.assert_that_pv_is_number(f"{probe_id}:FIELD:_RAW", 2901, tolerance=0.0001)

        self._set_field(probe_id, 2499)  # Just below r1 move down point
        self.ca.assert_that_pv_is(f"{probe_id}:RANGE:SP", "0.3 Tesla")
        self.ca.assert_that_pv_is(f"{probe_id}:STATEMACHINE:STATE", "r0")
        self.ca.assert_that_pv_is_number(f"{probe_id}:FIELD:_RAW", 2499, tolerance=0.0001)

        self._set_field(probe_id, 15_000)  # Only measurable in r3
        self.ca.assert_that_pv_is(f"{probe_id}:RANGE:SP", "3.0 Tesla")
        self.ca.assert_that_pv_is(f"{probe_id}:STATEMACHINE:STATE", "r3")
        self.ca.assert_that_pv_is_number(f"{probe_id}:FIELD:_RAW", 15000, tolerance=0.0001)

        self._set_field(probe_id, 0)  # Back to zero, should go back all the way to r0
        self.ca.assert_that_pv_is(f"{probe_id}:RANGE:SP", "0.3 Tesla")
        self.ca.assert_that_pv_is(f"{probe_id}:STATEMACHINE:STATE", "r0")
        self.ca.assert_that_pv_is_number(f"{probe_id}:FIELD:_RAW", 0.0, tolerance=0.0001)

    @parameterized.expand(parameterized_list(PROBE_IDS))
    @skip_if_recsim("Uses emulator backdoor")
    def test_GIVEN_device_disconnects_THEN_reinit_on_reconnect(self, _: str, probe_id: int):
        self._set_field(probe_id, 1)
        self.ca.assert_that_pv_is(f"{probe_id}:STATEMACHINE:STATE", "r0")
        self.ca.assert_that_pv_is_number(f"{probe_id}:FIELD:_RAW", 1, tolerance=0.0001)

        with self._lewis.backdoor_simulate_disconnected_device():
            self.ca.assert_that_pv_is(f"{probe_id}:STATEMACHINE:STATE", "disconnected")
            self.ca.assert_that_pv_alarm_is(f"{probe_id}:FIELD:_RAW", self.ca.Alarms.INVALID)
            self._set_initialized(probe_id, False)

        # On recovery, state machine should reinitialize device and make it back to range 0.
        self.ca.assert_that_pv_is(f"{probe_id}:STATEMACHINE:STATE", "r0")
        self.ca.assert_that_pv_alarm_is(f"{probe_id}:FIELD:_RAW", self.ca.Alarms.NONE)
        self.ca.assert_that_pv_is_number(f"{probe_id}:FIELD:_RAW", 1, tolerance=0.0001)

    @parameterized.expand(parameterized_list(PROBE_IDS))
    @skip_if_recsim("Uses emulator backdoor")
    def test_GIVEN_reading_device_THEN_field_scaled_correctly(self, _: str, probe_id: int):
        self._set_field(probe_id, 5)
        self.ca.assert_that_pv_is(f"{probe_id}:STATEMACHINE:STATE", "r0")

        self.ca.assert_that_pv_is_number(f"{probe_id}:FIELD:_RAW", 5, tolerance=0.0001)
        self.ca.assert_that_pv_is_number(
            f"{probe_id}:FIELD", 5 * SCALES[probe_id], tolerance=0.0001
        )
