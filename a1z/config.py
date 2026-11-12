"""Configuration-file support for the A1Z SDK.

A central YAML config lets you set default robot parameters (CAN channel,
URDF, gripper, gains, ...) once and share them across examples and tools.

Example ``config.yaml`` (set ``with_gripper: true`` when G1Z is attached)::

    can_channel: can0
    control_freq_hz: 250
    gravity_comp_factor: 1.0
    zero_gravity_mode: true
    with_gripper: false
    gripper_max_torque: 2.0
    # urdf_path: a1z/robot_models/a1z/A1Z_G1Z.urdf
    # motor_a_use_new_enable_protocol: false
    # bustype: null

Usage in a script::

    from a1z.config import load_config, config_to_robot_kwargs

    config = load_config()
    kwargs = config_to_robot_kwargs(config)
    robot = get_a1z_robot(**kwargs)

Command-line arguments override config-file values.
"""

import sys
from pathlib import Path
from typing import Any, Dict

import numpy as np
import yaml


_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


# Mapping from config-file key -> get_a1z_robot keyword argument.
# Lists under ``default_kp`` / ``default_kd`` are converted to numpy arrays.
_ROBOT_KWARGS = {
    "can_channel",
    "gravity_comp_factor",
    "zero_gravity_mode",
    "control_freq_hz",
    "min_freq_hz",
    "urdf_path",
    "default_kp",
    "default_kd",
    "with_gripper",
    "gripper_max_torque",
    "motor_a_use_new_enable_protocol",
    "bustype",
}


def load_config() -> Dict[str, Any]:
    """Read the required config.yaml from the repository root."""
    # Checkout scripts also work with a non-editable SDK installation.
    script_dir = Path(sys.argv[0]).resolve().parent
    path = (
        script_dir.parent / "config.yaml"
        if script_dir.name in {"examples", "tools"}
        else _DEFAULT_CONFIG_PATH
    )
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return data


def config_to_robot_kwargs(config: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a loaded config dict into kwargs for :func:`get_a1z_robot`.

    Only recognized keys are forwarded. ``default_kp`` / ``default_kd`` are
    converted from lists to ``np.ndarray``.
    """
    kwargs: Dict[str, Any] = {}
    for key in _ROBOT_KWARGS:
        if key not in config:
            continue
        value = config[key]
        if key in ("default_kp", "default_kd") and isinstance(value, list):
            value = np.array(value, dtype=np.float64)
        kwargs[key] = value
    return kwargs
