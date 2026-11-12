"""Compatibility checks for the bundled A1Z URDFs."""

import unittest
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import can
import numpy as np
import pinocchio

from a1z.dynamics.gravity_model import GravityModel
from a1z.robots.get_robot import get_a1z_robot
from a1z.robots.kinematics import Kinematics


MODELS = Path(__file__).resolve().parents[1] / "a1z" / "robot_models" / "a1z"
ARM_JOINTS = [f"arm_joint{i}" for i in range(1, 7)]
FINGER_JOINTS = ("gripper_finger_left_joint", "gripper_finger_rIght_joint")


class UpstreamModelsTest(unittest.TestCase):
    def test_arm_models_match_full_urdf_dynamics(self):
        for variant in ("Flange", "G1Z"):
            with self.subTest(variant=variant):
                path = str(MODELS / f"A1Z_{variant}.urdf")
                full = pinocchio.buildModelFromUrdf(path)
                reduced = GravityModel(path)
                self.assertEqual((reduced.nq, reduced.nv), (6, 6))
                self.assertEqual(list(reduced.model.names)[1:], ARM_JOINTS)
                self.assertTrue(full.existFrame("arm_link6"))
                if variant == "G1Z":
                    for finger in FINGER_JOINTS:
                        self.assertTrue(full.existFrame(finger))
                        self.assertTrue(full.existFrame(finger.replace("_joint", "_link")))
                self.assertAlmostEqual(
                    sum(inertia.mass for inertia in full.inertias),
                    sum(inertia.mass for inertia in reduced.model.inertias),
                )

                rng = np.random.default_rng(42)
                for _ in range(5):
                    q = rng.uniform(-0.5, 0.5, 6)
                    velocity = rng.uniform(-0.3, 0.3, 6)
                    acceleration = rng.uniform(-0.2, 0.2, 6)
                    q_full = pinocchio.neutral(full)
                    velocity_full = np.zeros(full.nv)
                    acceleration_full = np.zeros(full.nv)
                    indices = []
                    for i, name in enumerate(ARM_JOINTS):
                        self.assertTrue(full.existJointName(name), name)
                        joint = full.joints[full.getJointId(name)]
                        self.assertEqual((joint.nq, joint.nv), (1, 1))
                        q_full[joint.idx_q] = q[i]
                        velocity_full[joint.idx_v] = velocity[i]
                        acceleration_full[joint.idx_v] = acceleration[i]
                        indices.append(joint.idx_v)

                    expected = pinocchio.rnea(
                        full, full.createData(), q_full, velocity_full, acceleration_full
                    )[indices]
                    actual = reduced.compute_inverse_dynamics(q, velocity, acceleration)
                    np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=1e-10)
                    self.assertTrue(np.isfinite(actual).all())

                    expected_gravity = pinocchio.computeGeneralizedGravity(
                        full, full.createData(), q_full
                    )[indices]
                    np.testing.assert_allclose(
                        reduced.compute_gravity_torque(q), expected_gravity, rtol=1e-10, atol=1e-10
                    )

    def test_kinematics_accepts_six_arm_joints(self):
        for variant in ("Flange", "G1Z"):
            with self.subTest(variant=variant):
                path = str(MODELS / f"A1Z_{variant}.urdf")
                kin = Kinematics(path, end_effector_frame="arm_link6")
                q = np.array([0.1, 0.5, -0.5, 0.2, -0.1, 0.3])
                transform = kin.fk(q)
                self.assertEqual(transform.shape, (4, 4))
                converged, result = kin.ik(transform, init_q=q)
                self.assertTrue(converged)
                np.testing.assert_allclose(result, q, atol=1e-10)

    def test_robot_factory_uses_six_axis_dynamics(self):
        for with_gripper in (False, True):
            with self.subTest(with_gripper=with_gripper):
                with can.Bus(interface="virtual", channel="a1z-model-test") as bus:
                    with patch("a1z.robots.get_robot.open_can_bus", return_value=bus):
                        robot = get_a1z_robot(with_gripper=with_gripper)
                        self.assertEqual(robot.num_dofs(), 6 + int(with_gripper))
                        self.assertEqual((robot._gravity_model.nq, robot._gravity_model.nv), (6, 6))

    def test_full_gripper_model_can_still_be_loaded(self):
        path = str(MODELS / "A1Z_G1Z.urdf")
        full = pinocchio.buildModelFromUrdf(path)
        model = GravityModel(path, lock_gripper_joints=False)
        kin = Kinematics(path, lock_gripper_joints=False)
        self.assertEqual((model.nq, model.nv), (full.nq, full.nv))
        self.assertEqual((kin._model.nq, kin._model.nv), (full.nq, full.nv))

    def test_fixed_finger_urdf_remains_six_axis(self):
        tree = ET.parse(MODELS / "A1Z_G1Z.urdf")
        for joint in tree.findall("joint"):
            if joint.get("name") in FINGER_JOINTS:
                joint.set("type", "fixed")
                for tag in ("axis", "limit", "mimic"):
                    element = joint.find(tag)
                    if element is not None:
                        joint.remove(element)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixed_gripper.urdf"
            tree.write(path)
            model = GravityModel(str(path))
            kin = Kinematics(str(path))
            self.assertEqual((model.nq, model.nv), (6, 6))
            self.assertEqual((kin._model.nq, kin._model.nv), (6, 6))
            self.assertTrue(np.isfinite(model.compute_gravity_torque(np.zeros(6))).all())

    def test_other_robot_description_keeps_its_joints(self):
        tree = ET.parse(MODELS / "A1Z_G1Z.urdf")
        joint = next(j for j in tree.findall("joint") if j.get("name") == "arm_joint6")
        joint.set("name", "other_joint6")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "other_robot.urdf"
            tree.write(path)
            full = pinocchio.buildModelFromUrdf(str(path))
            model = GravityModel(str(path))
            self.assertEqual((model.nq, model.nv), (full.nq, full.nv))


if __name__ == "__main__":
    unittest.main()
