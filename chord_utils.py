"""Small, shared helpers for a 32-position Chord ring."""

import hashlib


RING_SIZE = 32


def _check_id(value, name="ring ID"):
    if type(value) is not int or not 0 <= value < RING_SIZE:
        raise ValueError("%s must be an integer in [0, 31]" % name)


def in_open_closed(key, start, end):
    """Return whether key is in clockwise interval (start, end].

    Equal endpoints represent the whole ring, which is how a single peer
    owns every key.
    """
    _check_id(key, "key")
    _check_id(start, "start")
    _check_id(end, "end")
    if start == end:
        return True
    if start < end:
        return start < key <= end
    return key > start or key <= end


def in_open_open(key, start, end):
    """Return whether key is in clockwise interval (start, end)."""
    _check_id(key, "key")
    _check_id(start, "start")
    _check_id(end, "end")
    if start == end:
        return key != start
    if start < end:
        return start < key < end
    return key > start or key < end


def clockwise_distance(start, end):
    """Return the number of ring steps clockwise from start to end."""
    _check_id(start, "start")
    _check_id(end, "end")
    return (end - start) % RING_SIZE


def finger_start(peer_id, index):
    """Return the start position for zero-based finger-table entry index."""
    _check_id(peer_id, "peer_id")
    if type(index) is not int or index < 0:
        raise ValueError("finger index must be a non-negative integer")
    return (peer_id + (1 << index)) % RING_SIZE


def closest_preceding_finger(peer_id, key, fingers):
    """Choose the closest known finger strictly between peer_id and key.

    ``fingers`` may contain peer references directly (``{"id", "url"}``) or
    finger entries holding one in their ``node`` field. Ties and duplicate
    references are harmless; malformed entries are ignored.
    """
    _check_id(peer_id, "peer_id")
    _check_id(key, "key")
    if peer_id == key:
        return None
    best = None
    best_distance = -1
    for entry in fingers:
        node = entry.get("node") if isinstance(entry, dict) and "node" in entry else entry
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        if type(node_id) is not int or not 0 <= node_id < RING_SIZE:
            continue
        if node_id == peer_id or not in_open_open(node_id, peer_id, key):
            continue
        distance = clockwise_distance(peer_id, node_id)
        if distance > best_distance:
            best = node
            best_distance = distance
    return best


def post_routing_key(post_id):
    """Hash a positive decimal post ID to a ring position."""
    if type(post_id) is not int or post_id <= 0:
        raise ValueError("post_id must be a positive integer")
    digest = hashlib.sha256(str(post_id).encode("ascii")).digest()
    return int.from_bytes(digest, "big") % RING_SIZE
