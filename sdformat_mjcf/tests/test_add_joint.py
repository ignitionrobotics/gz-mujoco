# Copyright (C) 2022 Open Source Robotics Foundation

# Licensed under the Apache License, version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#       http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from numpy.testing import assert_allclose
from math import pi

import sdformat as sdf
from ignition.math import Pose3d, Vector3d
from dm_control import mjcf

from sdformat_mjcf.converters.joint import JointType
from sdformat_mjcf.converters.joint import add_joint as add_joint_impl
import sdformat_mjcf.sdf_utils as su
import helpers


def add_joint(*args, **kwargs):
    """Call the add_joint implementation with pose_resolver and
    axis_xyz_resolver set to testing versions"""
    return add_joint_impl(
        *args,
        **kwargs,
        pose_resolver=helpers.nonthrowing_pose_resolver,
        axis_xyz_resolver=helpers.nonthrowing_axis_xyz_resolver
    )


class JointTest(unittest.TestCase):

    test_pose = Pose3d(1, 2, 3, pi / 2, pi / 3, pi / 4)
    expected_pos = [1.0, 2.0, 3.0]
    expected_euler = [90.0, 60.0, 45.0]

    def setUp(self):
        self.mujoco = mjcf.RootElement(model="test")
        self.body = self.mujoco.worldbody.add("body")

    def create_sdf_joint(self,
                         name,
                         j_type,
                         pose,
                         xyz=None,
                         limits=None,
                         dynamics=None):
        joint = sdf.Joint()
        joint.set_name(name)
        joint.set_type(j_type)
        joint.set_raw_pose(pose)
        joint_axis = sdf.JointAxis()
        if xyz:
            joint_axis.set_xyz(Vector3d(*xyz))
        if limits:
            joint_axis.set_lower(limits[0])
            joint_axis.set_upper(limits[1])

        if dynamics:
            for key, val in dynamics.items():
                setter = getattr(joint_axis, f"set_{key}")
                setter(val)

        joint.set_axis(0, joint_axis)
        return joint

    def test_free_joint(self):
        mj_joint = add_joint(self.body, None)
        self.assertIsNotNone(mj_joint)
        self.assertEqual("freejoint", mj_joint.name)
        self.assertEqual("freejoint", mj_joint.tag)

    def test_fixed_joint(self):
        joint = sdf.Joint()
        joint.set_type(JointType.FIXED)
        mj_joint = add_joint(self.body, joint)
        self.assertIsNone(mj_joint)

    def test_revolute_joint(self):
        joint = self.create_sdf_joint("joint1",
                                      JointType.REVOLUTE,
                                      self.test_pose,
                                      xyz=[1, 0, 0])

        mj_joint = add_joint(self.body, joint)
        self.assertIsNotNone(mj_joint)
        self.assertEqual("joint1", mj_joint.name)
        self.assertEqual("hinge", mj_joint.type)
        assert_allclose(self.expected_pos, mj_joint.pos)
        expected_axis = su.vec3d_to_list(
            self.test_pose.rot().rotate_vector(Vector3d(1, 0, 0))
        )
        assert_allclose(expected_axis, mj_joint.axis)
        self.assertFalse(mj_joint.limited)

    def test_revolute_joint_with_limits(self):
        joint = self.create_sdf_joint("joint1",
                                      JointType.REVOLUTE,
                                      self.test_pose,
                                      xyz=[1, 0, 0],
                                      limits=(-pi / 4, pi / 2))

        mj_joint = add_joint(self.body, joint)
        self.assertTrue(mj_joint.limited)
        assert_allclose([-45.0, 90.0], mj_joint.range)

    def test_revolute_joint_with_dynamics(self):
        joint_dynamics = {
            'damping': 0.1,
            'friction': 0.2,
            'spring_stiffness': 0.3,
            'spring_reference': pi / 6
        }
        joint = self.create_sdf_joint("joint1",
                                      JointType.REVOLUTE,
                                      self.test_pose,
                                      xyz=[1, 0, 0],
                                      dynamics=joint_dynamics)

        mj_joint = add_joint(self.body, joint)
        self.assertEqual("hinge", mj_joint.type)
        self.assertEqual(0.1, mj_joint.damping)
        self.assertEqual(0.2, mj_joint.frictionloss)
        self.assertEqual(0.3, mj_joint.stiffness)
        self.assertAlmostEqual(30, mj_joint.springref)

    def test_continuous_joint(self):
        joint = self.create_sdf_joint("joint1",
                                      JointType.CONTINUOUS,
                                      self.test_pose,
                                      xyz=[1, 0, 0],
                                      limits=(-pi / 4, pi / 2))

        mj_joint = add_joint(self.body, joint)
        self.assertIsNotNone(mj_joint)
        self.assertEqual("joint1", mj_joint.name)
        self.assertEqual("hinge", mj_joint.type)
        assert_allclose(self.expected_pos, mj_joint.pos)
        expected_axis = su.vec3d_to_list(
            self.test_pose.rot().rotate_vector(Vector3d(1, 0, 0))
        )
        assert_allclose(expected_axis, mj_joint.axis)
        # Limits should be ignored even if they're set in the SDFormat Joint
        self.assertFalse(mj_joint.limited)

    def test_continuous_joint_with_dynamics(self):
        joint_dynamics = {
            'damping': 0.1,
            'friction': 0.2,
            'spring_stiffness': 0.3,
            'spring_reference': pi / 6
        }
        joint = self.create_sdf_joint("joint1",
                                      JointType.CONTINUOUS,
                                      self.test_pose,
                                      xyz=[1, 0, 0],
                                      dynamics=joint_dynamics)

        mj_joint = add_joint(self.body, joint)
        self.assertEqual("hinge", mj_joint.type)
        self.assertEqual(0.1, mj_joint.damping)
        self.assertEqual(0.2, mj_joint.frictionloss)
        self.assertEqual(0.3, mj_joint.stiffness)
        self.assertAlmostEqual(30, mj_joint.springref)

    def test_prismatic_joint(self):
        joint = self.create_sdf_joint("joint1",
                                      JointType.PRISMATIC,
                                      self.test_pose,
                                      xyz=[1, 0, 0])

        mj_joint = add_joint(self.body, joint)
        self.assertIsNotNone(mj_joint)
        self.assertEqual("joint1", mj_joint.name)
        self.assertEqual("slide", mj_joint.type)
        assert_allclose(self.expected_pos, mj_joint.pos)
        expected_axis = su.vec3d_to_list(
            self.test_pose.rot().rotate_vector(Vector3d(1, 0, 0))
        )
        assert_allclose(expected_axis, mj_joint.axis)

    def test_prismatic_joint_with_limits(self):
        joint = self.create_sdf_joint("joint1",
                                      JointType.PRISMATIC,
                                      self.test_pose,
                                      xyz=[1, 0, 0],
                                      limits=(-5, 10))

        mj_joint = add_joint(self.body, joint)
        self.assertTrue(mj_joint.limited)
        assert_allclose([-5, 10], mj_joint.range)

    def test_prismatic_joint_with_dynamics(self):
        joint_dynamics = {
            'damping': 0.1,
            'friction': 0.2,
            'spring_stiffness': 0.3,
            'spring_reference': 0.4
        }
        joint = self.create_sdf_joint("joint1",
                                      JointType.PRISMATIC,
                                      self.test_pose,
                                      xyz=[1, 0, 0],
                                      dynamics=joint_dynamics)

        mj_joint = add_joint(self.body, joint)
        self.assertEqual(0.1, mj_joint.damping)
        self.assertEqual(0.2, mj_joint.frictionloss)
        self.assertEqual(0.3, mj_joint.stiffness)
        self.assertAlmostEqual(0.4, mj_joint.springref)

    def test_ball_joint(self):
        joint = self.create_sdf_joint("joint1",
                                      JointType.BALL,
                                      self.test_pose)

        mj_joint = add_joint(self.body, joint)
        self.assertIsNotNone(mj_joint)
        self.assertEqual("joint1", mj_joint.name)
        self.assertEqual("ball", mj_joint.type)
        assert_allclose(self.expected_pos, mj_joint.pos)


if __name__ == "__main__":
    unittest.main()
