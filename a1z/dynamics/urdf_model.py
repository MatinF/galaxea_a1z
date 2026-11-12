"""Build a Pinocchio model for the six-axis A1Z arm."""

import pinocchio


_ARM_JOINTS = tuple(f"arm_joint{i}" for i in range(1, 7))
_GRIPPER_JOINTS = (
    "gripper_finger_left_joint",
    "gripper_finger_rIght_joint",
)


def build_arm_model(urdf_path: str, lock_gripper_joints: bool = True):
    """Load a URDF, optionally locking A1Z gripper joints at their zero positions.

    The finger links remain in the model so their inertia contributes to the
    arm's dynamics. Other robot descriptions are loaded without modification.
    """
    model = pinocchio.buildModelFromUrdf(urdf_path)
    if lock_gripper_joints and all(model.existJointName(name) for name in _ARM_JOINTS):
        joint_ids = [
            model.getJointId(name)
            for name in _GRIPPER_JOINTS
            if model.existJointName(name)
        ]
        if joint_ids:
            model = pinocchio.buildReducedModel(model, joint_ids, pinocchio.neutral(model))
    return model
