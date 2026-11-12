"""Offline checks for diagnostic monitor timing and terminal output."""

import contextlib
import io
import unittest
from unittest.mock import patch

import can

from tools import motor_diag


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, duration):
        self.now += max(duration, 1e-8)


class FakeBus:
    def __init__(self, clock, *, provide_feedback):
        self.clock = clock
        self.provide_feedback = provide_feedback
        self.pending = []
        self.commands = []
        self.shutdown_called = False

    def send(self, message):
        data = bytes(message.data)
        if len(data) != 8 or data.startswith(b"\xff" * 7):
            return
        self.commands.append((self.clock.now, message.arbitration_id))
        if not self.provide_feedback:
            return
        if message.arbitration_id == 1:
            first_byte = 0x20
        else:
            first_byte = 0x14
        self.pending.append(can.Message(
            arbitration_id=message.arbitration_id,
            data=bytes([first_byte, 0x80, 0, 0x80, 0x08, 0, 50, 50]),
            is_extended_id=False,
        ))

    def recv(self, timeout):
        if self.clock.now >= 1.0:
            raise KeyboardInterrupt
        if self.pending:
            return self.pending.pop(0)
        self.clock.sleep(timeout)
        return None

    def shutdown(self):
        self.shutdown_called = True


class TtyOutput(io.StringIO):
    def isatty(self):
        return True


class MonitorTest(unittest.TestCase):
    def run_fake_monitor(self, *, provide_feedback, interval=None, tty=False):
        clock = FakeClock()
        bus = FakeBus(clock, provide_feedback=provide_feedback)
        output = TtyOutput() if tty else io.StringIO()
        with patch.object(motor_diag, "time", clock), contextlib.redirect_stdout(output):
            if interval is None:
                motor_diag.run_monitor(bus, [0, 3])
            else:
                motor_diag.run_monitor(bus, [0, 3], interval=interval)
        return bus, output.getvalue()

    def test_display_refreshes_while_command_cadence_stays_unchanged(self):
        bus, output = self.run_fake_monitor(provide_feedback=True)
        self.assertGreaterEqual(output.count("A1Z 电机监控"), 8)
        self.assertNotIn("LOST", output)
        self.assertNotIn("\033", output)
        command_times = [t for t, motor_id in bus.commands if motor_id == 1]
        self.assertGreaterEqual(len(command_times), 8)
        for previous, current in zip(command_times, command_times[1:]):
            self.assertAlmostEqual(current - previous, 0.1, delta=1e-5)

    def test_display_interval_is_elapsed_time_not_loop_count(self):
        bus, output = self.run_fake_monitor(provide_feedback=True, interval=0.3)
        self.assertEqual(output.count("A1Z 电机监控"), 4)
        self.assertGreaterEqual(len(bus.commands), 16)

    def test_missing_feedback_still_shows_lost(self):
        _, output = self.run_fake_monitor(provide_feedback=False)
        self.assertIn("LOST", output)
        self.assertIn("N/A", output)

    def test_terminal_refresh_reuses_screen_without_clearing_it_before_each_row(self):
        _, output = self.run_fake_monitor(provide_feedback=True, tty=True)
        self.assertGreaterEqual(output.count("\033[H"), 8)
        self.assertNotIn("\033[2J", output)

    def test_cli_monitor_uses_the_default_refresh_interval(self):
        bus = FakeBus(FakeClock(), provide_feedback=True)
        with patch.object(motor_diag.sys, "argv", ["motor_diag.py", "--monitor", "--yes"]):
            with patch.object(motor_diag, "load_config", return_value={}):
                with patch.object(motor_diag, "check_can_interface", return_value=(True, "")):
                    with patch.object(motor_diag, "confirm_active_motor_operation"):
                        with patch.object(motor_diag, "open_can_bus", return_value=bus):
                            with patch.object(motor_diag, "run_monitor") as monitor:
                                with patch.object(motor_diag, "_disable_joints_and_flush", return_value=True):
                                    with contextlib.redirect_stdout(io.StringIO()):
                                        motor_diag.main()
        monitor.assert_called_once_with(bus, list(range(6)))
        self.assertTrue(bus.shutdown_called)


if __name__ == "__main__":
    unittest.main()
