import unittest

from chord_utils import (
    RING_SIZE,
    closest_preceding_finger,
    finger_start,
    in_open_closed,
    in_open_open,
    post_routing_key,
)


class ChordUtilsTests(unittest.TestCase):
    def test_interval_boundaries_and_wraparound(self):
        self.assertFalse(in_open_closed(4, 4, 12))
        self.assertTrue(in_open_closed(12, 4, 12))
        self.assertTrue(in_open_closed(0, 28, 4))
        self.assertFalse(in_open_closed(28, 28, 4))
        self.assertTrue(in_open_closed(17, 12, 20))
        self.assertTrue(in_open_closed(17, 12, 18))
        self.assertTrue(in_open_closed(31, 7, 7))  # one peer owns all keys
        self.assertFalse(in_open_open(4, 4, 12))
        self.assertFalse(in_open_open(12, 4, 12))
        self.assertTrue(in_open_open(0, 28, 4))

    def test_finger_starts_wrap(self):
        self.assertEqual([finger_start(4, i) for i in range(5)],
                         [5, 6, 8, 12, 20])
        self.assertEqual(finger_start(28, 2), 0)

    def test_closest_preceding_finger_and_wraparound(self):
        fingers = [
            {"start": 5, "node": {"id": 12, "url": "http://peer12"}},
            {"start": 8, "node": {"id": 20, "url": "http://peer20"}},
            {"start": 12, "node": {"id": 28, "url": "http://peer28"}},
        ]
        self.assertEqual(closest_preceding_finger(4, 17, fingers)["id"], 12)
        self.assertIsNone(closest_preceding_finger(4, 4, fingers))
        wrapped = [{"id": 31}, {"id": 2}, {"id": 6}]
        self.assertEqual(closest_preceding_finger(28, 5, wrapped)["id"], 2)

    def test_post_routing_key_and_collision_identity(self):
        self.assertTrue(0 <= post_routing_key(17) < RING_SIZE)
        self.assertEqual(post_routing_key(17), 3)
        self.assertEqual(post_routing_key(17), post_routing_key(17))
        seen = {}
        collision = None
        for post_id in range(1, RING_SIZE + 2):
            key = post_routing_key(post_id)
            if key in seen:
                collision = (seen[key], post_id, key)
                break
            seen[key] = post_id
        self.assertIsNotNone(collision)
        first_id, second_id, key = collision
        self.assertNotEqual(first_id, second_id)
        self.assertEqual(post_routing_key(first_id), key)
        self.assertEqual(post_routing_key(second_id), key)

    def test_invalid_inputs_are_rejected(self):
        for invalid in (-1, 32, True, "4"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    in_open_closed(invalid, 0, 1)
        with self.assertRaises(ValueError):
            finger_start(4, -1)
        with self.assertRaises(ValueError):
            post_routing_key(0)


if __name__ == "__main__":
    unittest.main()
