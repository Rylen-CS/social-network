import sqlite3
import os
import json
from datetime import datetime, timezone

class PeerStorage:
    def __init__(self, peer_id: int, db_dir: str = "database"):
        """Initializes isolated SQLite storage for a specific Chord peer ID."""
        self.peer_id = int(peer_id)
        os.makedirs(db_dir, exist_ok=True)
        self.db_path = os.path.join(db_dir, f"peer_{self.peer_id}.db")
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Creates table separating post ID, routing key, payload, and role (primary/backup)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS peer_posts (
                post_id INTEGER PRIMARY KEY,
                routing_key INTEGER NOT NULL,
                author INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                content TEXT NOT NULL,
                caption TEXT DEFAULT '',
                likes_json TEXT DEFAULT '[]',
                comments_json TEXT DEFAULT '[]',
                role TEXT CHECK(role IN ('primary', 'backup')) NOT NULL DEFAULT 'primary',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_routing_key ON peer_posts(routing_key);')
        conn.commit()
        conn.close()

    def put_post(self, post_data: dict, routing_key: int, role: str = 'primary'):
        """Inserts or updates a post record with its routing key and storage role."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        post_id = int(post_data['id'])
        author = int(post_data['author'])
        timestamp = post_data.get('timestamp', datetime.now(timezone.utc).isoformat())
        content = post_data.get('content', '')
        caption = post_data.get('caption', '')
        likes_json = json.dumps(post_data.get('likes', []))
        comments_json = json.dumps(post_data.get('comments', []))

        cursor.execute('''
            INSERT INTO peer_posts 
            (post_id, routing_key, author, timestamp, content, caption, likes_json, comments_json, role)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(post_id) DO UPDATE SET
                routing_key = excluded.routing_key,
                author = excluded.author,
                timestamp = excluded.timestamp,
                content = excluded.content,
                caption = excluded.caption,
                likes_json = excluded.likes_json,
                comments_json = excluded.comments_json,
                role = CASE WHEN peer_posts.role = 'primary' THEN 'primary' ELSE excluded.role END,
                updated_at = CURRENT_TIMESTAMP
        ''', (post_id, int(routing_key), author, timestamp, content, caption, likes_json, comments_json, role))
        
        conn.commit()
        conn.close()

    def get_post(self, post_id: int) -> dict:
        """Retrieves a specific post by its full integer ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM peer_posts WHERE post_id = ?", (int(post_id),))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return self._row_to_dict(row)

    def delete_post(self, post_id: int):
        """Deletes a post record locally."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM peer_posts WHERE post_id = ?", (int(post_id),))
        row = cursor.fetchone()
        if row:
            cursor.execute("DELETE FROM peer_posts WHERE post_id = ?", (int(post_id),))
            conn.commit()
        conn.close()

    def get_posts_in_interval(self, start: int, end: int) -> list:
        """
        Returns all records whose routing key falls clockwise in the interval (start, end].
        Handles 32-position ring wrap-around (e.g., start=28, end=4).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM peer_posts")
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            rk = row['routing_key']
            if self._in_interval(rk, start, end):
                results.append(self._row_to_dict(row))
        return results

    def _in_interval(self, key: int, start: int, end: int) -> int:
        """Checks if key is within (start, end] on a 32-position ring (0 to 31)."""
        if start < end:
            return start < key <= end
        else: # Wrap-around case (e.g., start=28, end=4)
            return key > start or key <= end

    def promote_backups_to_primary(self):
        """Promotes all backup records to primary (used during peer failure takeover)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE peer_posts SET role = 'primary' WHERE role = 'backup'")
        conn.commit()
        conn.close()

    def set_role_for_interval(self, start: int, end: int, role: str):
        """Updates role ('primary' or 'backup') for posts within a given routing interval."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM peer_posts")
        rows = cursor.fetchall()
        
        for row in rows:
            if self._in_interval(row['routing_key'], start, end):
                cursor.execute("UPDATE peer_posts SET role = ? WHERE post_id = ?", (role, row['post_id']))
        conn.commit()
        conn.close()

    def _row_to_dict(self, row) -> dict:
        return {
            "id": row['post_id'],
            "routing_key": row['routing_key'],
            "author": row['author'],
            "timestamp": row['timestamp'],
            "content": row['content'],
            "caption": row['caption'],
            "likes": json.loads(row['likes_json']),
            "comments": json.loads(row['comments_json']),
            "role": row['role']
        }

if __name__ == "__main__":
    storage = PeerStorage(peer_id=20)
    sample_post = {
        "id": 101,
        "author": 7,
        "timestamp": "2026-10-13T02:00:00+00:00",
        "content": "photo17.jpg",
        "caption": "Testing Chord storage",
        "likes": [],
        "comments": []
    }
    storage.put_post(sample_post, routing_key=17, role='primary')
    posts_in_range = storage.get_posts_in_interval(start=12, end=20)
    print(f"Posts found in interval (12, 20]: {len(posts_in_range)}")
    print(posts_in_range[0])