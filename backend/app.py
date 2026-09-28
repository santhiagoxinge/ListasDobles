"""
AquaRuta backend — Doubly Linked List applied to a real-life case.

Real-life case: a municipal water trunk main (red de acueducto).
Every valve chamber along the pipeline is a node of a doubly linked list:

    prev -> the chamber upstream   (aguas arriba)
    next -> the chamber downstream (aguas abajo)

Why a doubly linked list fits this problem:
  * the operator walks the trunk main in both directions in O(1) per chamber;
  * new chambers are added at the intake (head) or at the reservoir (tail) in O(1);
  * a closed chamber is removed from either end in O(1), which a singly linked
    list can only do at the head;
  * the line is traversable head -> tail and tail -> head.

Code, identifiers and comments are in English.
The frontend user interface is rendered in Spanish.

Standard library only — no external dependencies.

Run:
    python app.py
Open:
    http://127.0.0.1:8000
The same server exposes the JSON REST API under /api/* and serves the static
frontend located in ../frontend/.
"""

import json
import socket
import unicodedata
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

HOST = "0.0.0.0"
PORT = 8000

OPEN = "Abierta"
CLOSED = "Cerrada"


def _normalize(text: str) -> str:
    """Lowercase and strip accents, so the UI search tolerates missing accents."""
    decomposed = unicodedata.normalize("NFD", str(text).lower().strip())
    return "".join(char for char in decomposed if not unicodedata.combining(char))

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = (BASE_DIR / ".." / "frontend").resolve()


class ValveNode:
    """A node of the doubly linked list. Each node is a valve chamber."""

    def __init__(self, valve_id: int, name: str, elevation: int, status: str = OPEN):
        self.valve_id = valve_id
        self.name = name
        self.elevation = elevation
        self.status = status
        self.prev = None
        self.next = None

    def to_dict(self):
        return {
            "id": self.valve_id,
            "name": self.name,
            "elevation": self.elevation,
            "status": self.status,
        }


class DoublyLinkedList:
    """Classic doubly linked list of ValveNode objects."""

    def __init__(self):
        self.head = None
        self.tail = None
        self._size = 0
        self._next_id = 1

    # -- basic helpers -------------------------------------------------
    def is_empty(self) -> bool:
        return self.head is None

    def __len__(self) -> int:
        return self._size

    def _create_node(self, name: str, elevation: int, status: str) -> ValveNode:
        node = ValveNode(self._next_id, name.strip(), int(elevation), status)
        self._next_id += 1
        return node

    # -- insertion -----------------------------------------------------
    def add_first(self, name: str, elevation: int, status: str = OPEN) -> ValveNode:
        """Insert a chamber at the intake end of the trunk main. O(1)."""
        node = self._create_node(name, elevation, status)
        if self.is_empty():
            self.head = self.tail = node
        else:
            node.next = self.head
            self.head.prev = node
            self.head = node
        self._size += 1
        return node

    def add_last(self, name: str, elevation: int, status: str = OPEN) -> ValveNode:
        """Insert a chamber at the reservoir end of the trunk main. O(1)."""
        node = self._create_node(name, elevation, status)
        if self.is_empty():
            self.head = self.tail = node
        else:
            node.prev = self.tail
            self.tail.next = node
            self.tail = node
        self._size += 1
        return node

    def insert_at(self, position: int, name: str, elevation: int, status: str = OPEN) -> ValveNode:
        """Insert a chamber at a 0-based position."""
        if position <= 0:
            return self.add_first(name, elevation, status)
        if position >= self._size:
            return self.add_last(name, elevation, status)
        node = self._create_node(name, elevation, status)
        current = self._node_at(position)
        previous = current.prev
        previous.next = node
        node.prev = previous
        node.next = current
        current.prev = node
        self._size += 1
        return node

    def insert_after(self, target_id: int, name: str, elevation: int, status: str = OPEN):
        """Insert a chamber right after the chamber with target_id."""
        target = self.find_by_id(target_id)
        if target is None:
            return None
        if target is self.tail:
            return self.add_last(name, elevation, status)
        node = self._create_node(name, elevation, status)
        node.prev = target
        node.next = target.next
        target.next.prev = node
        target.next = node
        self._size += 1
        return node

    # -- removal -------------------------------------------------------
    def remove_first(self):
        """Remove the chamber at the intake end. O(1)."""
        if self.is_empty():
            return None
        removed = self.head
        if self.head is self.tail:
            self.head = self.tail = None
        else:
            self.head = self.head.next
            self.head.prev = None
        self._size -= 1
        removed.next = removed.prev = None
        return removed

    def remove_last(self):
        """Remove the chamber at the reservoir end. O(1)."""
        if self.is_empty():
            return None
        removed = self.tail
        if self.head is self.tail:
            self.head = self.tail = None
        else:
            self.tail = self.tail.prev
            self.tail.next = None
        self._size -= 1
        removed.next = removed.prev = None
        return removed

    def remove_by_id(self, valve_id: int):
        node = self.find_by_id(valve_id)
        if node is None:
            return None
        if node is self.head:
            return self.remove_first()
        if node is self.tail:
            return self.remove_last()
        node.prev.next = node.next
        node.next.prev = node.prev
        self._size -= 1
        node.next = node.prev = None
        return node

    def remove_at(self, position: int):
        node = self._node_at(position)
        if node is None:
            return None
        return self.remove_by_id(node.valve_id)

    def clear(self):
        self.head = self.tail = None
        self._size = 0

    # -- traversal / search -------------------------------------------
    def _node_at(self, position: int):
        """Bidirectional traversal: start from the nearest end. O(n/2)."""
        if position < 0 or position >= self._size:
            return None
        if position < self._size // 2:
            current = self.head
            for _ in range(position):
                current = current.next
        else:
            current = self.tail
            for _ in range(self._size - 1, position, -1):
                current = current.prev
        return current

    def find_by_id(self, valve_id: int):
        current = self.head
        while current:
            if current.valve_id == valve_id:
                return current
            current = current.next
        return None

    def find_by_name(self, query: str):
        """Substring search, accent insensitive (so "camara" finds "Camara")."""
        needle = _normalize(query)
        results = []
        current = self.head
        index = 0
        while current:
            if needle in _normalize(current.name):
                item = current.to_dict()
                item["position"] = index
                results.append(item)
            current = current.next
            index += 1
        return results

    def to_list_forward(self):
        """Head -> tail traversal (upstream to downstream)."""
        items = []
        current = self.head
        while current:
            items.append(current.to_dict())
            current = current.next
        return items

    def to_list_backward(self):
        """Tail -> head traversal (downstream to upstream), only possible with prev."""
        items = []
        current = self.tail
        while current:
            items.append(current.to_dict())
            current = current.prev
        return items

    def count_by_status(self, status: str) -> int:
        counter = 0
        current = self.head
        while current:
            if current.status == status:
                counter += 1
            current = current.next
        return counter


class TrunkMain:
    """Wraps the list plus the operator position (a cursor over the list)."""

    def __init__(self):
        self.valves = DoublyLinkedList()
        self.current_id = None
        self.seed_demo()

    # -- demo data -----------------------------------------------------
    def seed_demo(self):
        self.valves.clear()
        demo = [
            ("Compuerta de Admisión", 3240, OPEN),
            ("Cámara de Reposo Norte", 3210, OPEN),
            ("Estación de Bombeo PB-1", 3185, OPEN),
            ("Cruce de Calle 45", 3160, CLOSED),
            ("Cámara Central", 3130, OPEN),
            ("Purga de Sedimentos", 3105, CLOSED),
            ("Cámara de Reposo Sur", 3080, OPEN),
            ("Válvula de Descarga", 3055, OPEN),
        ]
        for name, elevation, status in demo:
            self.valves.add_last(name, elevation, status)
        if self.valves.head:
            self.current_id = self.valves.head.valve_id

    # -- operator cursor -----------------------------------------------
    def current(self):
        if self.current_id is None:
            return None
        return self.valves.find_by_id(self.current_id)

    def move(self, direction: str):
        """direction: 'downstream' (next) or 'upstream' (prev)."""
        current = self.current()
        if current is None:
            return None, "empty"
        if direction == "downstream":
            if current.next is None:
                return current, "end_of_line"
            self.current_id = current.next.valve_id
            return current.next, "moved"
        if direction == "upstream":
            if current.prev is None:
                return current, "start_of_line"
            self.current_id = current.prev.valve_id
            return current.prev, "moved"
        return current, "invalid_direction"

    # -- operations -----------------------------------------------------
    def remove(self, valve_id: int):
        """Remove any chamber and keep the operator on a valid neighbour."""
        node = self.valves.find_by_id(valve_id)
        if node is None:
            return None
        successor_id = node.next.valve_id if node.next else None
        predecessor_id = node.prev.valve_id if node.prev else None
        removed = self.valves.remove_by_id(valve_id)
        if removed is None:
            return None
        if self.current_id == removed.valve_id:
            # fall back to the closest remaining neighbour: downstream first,
            # otherwise the chamber just upstream
            fallback = successor_id if successor_id is not None else predecessor_id
            if fallback is None and self.valves.head is not None:
                fallback = self.valves.head.valve_id
            self.current_id = fallback
        return removed

    def remove_first(self):
        if self.valves.head is None:
            return None
        return self.remove(self.valves.head.valve_id)

    def remove_last(self):
        if self.valves.tail is None:
            return None
        return self.remove(self.valves.tail.valve_id)

    def ensure_cursor(self):
        if self.current_id is None and self.valves.head is not None:
            self.current_id = self.valves.head.valve_id


TRUNK = TrunkMain()

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # keep the console clean during the class demo

    # -- response helpers -----------------------------------------------
    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def _serve_static(self, url_path: str):
        if url_path in ("/", ""):
            url_path = "/index.html"
        target = (FRONTEND_DIR / url_path.lstrip("/")).resolve()
        if not str(target).startswith(str(FRONTEND_DIR)) or not target.is_file():
            return False
        data = target.read_bytes()
        mime = MIME_TYPES.get(target.suffix.lower(), "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        return True

    def do_OPTIONS(self):
        self._send_json({"ok": True})

    # -- routing ---------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/health":
            return self._send_json({"ok": True, "service": "aquaruta-backend"})

        if path == "/api/valves":
            search = (query.get("search", [""])[0] or "").strip()
            if search:
                return self._send_json({"valves": TRUNK.valves.find_by_name(search)})
            direction = (query.get("direction", ["forward"])[0] or "forward").lower()
            valves = TRUNK.valves.to_list_backward() if direction == "backward" else TRUNK.valves.to_list_forward()
            current = TRUNK.current()
            return self._send_json({
                "valves": valves,
                "direction": direction,
                "size": len(TRUNK.valves),
                "current_id": current.valve_id if current else None,
            })

        if path.startswith("/api/valves/"):
            try:
                valve_id = int(path.rsplit("/", 1)[-1])
            except ValueError:
                return self._send_json({"error": "invalid id"}, status=400)
            node = TRUNK.valves.find_by_id(valve_id)
            if node is None:
                return self._send_json({"error": "valve chamber not found"}, status=404)
            return self._send_json({"valve": node.to_dict()})

        if path == "/api/operator":
            current = TRUNK.current()
            return self._send_json({
                "current": current.to_dict() if current else None,
                "size": len(TRUNK.valves),
            })

        if path == "/api/stats":
            head = TRUNK.valves.head
            tail = TRUNK.valves.tail
            return self._send_json({
                "size": len(TRUNK.valves),
                "is_empty": TRUNK.valves.is_empty(),
                "head": head.to_dict() if head else None,
                "tail": tail.to_dict() if tail else None,
                "open": TRUNK.valves.count_by_status(OPEN),
                "closed": TRUNK.valves.count_by_status(CLOSED),
                "drop": (head.elevation - tail.elevation) if (head and tail) else 0,
            })

        if path.startswith("/api/"):
            return self._send_json({"error": "endpoint not found"}, status=404)

        if self._serve_static(path):
            return
        return self._send_json({"error": "frontend file not found"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_json()

        if path == "/api/valves":
            name = str(body.get("name", "")).strip()
            if not name:
                return self._send_json({"error": "name is required"}, status=400)
            try:
                elevation = int(body.get("elevation", 3000))
            except (TypeError, ValueError):
                return self._send_json({"error": "elevation must be an integer"}, status=400)
            status = OPEN if str(body.get("status", OPEN)) == OPEN else CLOSED
            mode = str(body.get("mode", "last")).lower()

            if mode == "first":
                node = TRUNK.valves.add_first(name, elevation, status)
            elif mode == "at":
                try:
                    position = int(body.get("position", len(TRUNK.valves)))
                except (TypeError, ValueError):
                    position = len(TRUNK.valves)
                node = TRUNK.valves.insert_at(position, name, elevation, status)
            elif mode == "after":
                try:
                    after_id = int(body.get("after_id", 0))
                except (TypeError, ValueError):
                    return self._send_json({"error": "after_id must be an integer"}, status=400)
                node = TRUNK.valves.insert_after(after_id, name, elevation, status)
                if node is None:
                    return self._send_json({"error": "reference chamber not found"}, status=404)
            else:
                node = TRUNK.valves.add_last(name, elevation, status)

            TRUNK.ensure_cursor()
            return self._send_json({"valve": node.to_dict(), "size": len(TRUNK.valves)}, status=201)

        if path == "/api/operator/move":
            direction = str(body.get("direction", "downstream")).lower()
            node, outcome = TRUNK.move(direction)
            if node is None:
                return self._send_json({"error": "the trunk main is empty"}, status=400)
            return self._send_json({"current": node.to_dict(), "status": outcome})

        if path == "/api/reset":
            TRUNK.seed_demo()
            return self._send_json({"valves": TRUNK.valves.to_list_forward(), "size": len(TRUNK.valves)})

        if path == "/api/clear":
            TRUNK.valves.clear()
            TRUNK.current_id = None
            return self._send_json({"valves": [], "size": 0})

        return self._send_json({"error": "endpoint not found"}, status=404)

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_json()

        if path.startswith("/api/valves/"):
            try:
                valve_id = int(path.rsplit("/", 1)[-1])
            except ValueError:
                return self._send_json({"error": "invalid id"}, status=400)
            node = TRUNK.valves.find_by_id(valve_id)
            if node is None:
                return self._send_json({"error": "valve chamber not found"}, status=404)
            if "name" in body and str(body["name"]).strip():
                node.name = str(body["name"]).strip()
            if "elevation" in body:
                try:
                    node.elevation = int(body["elevation"])
                except (TypeError, ValueError):
                    return self._send_json({"error": "elevation must be an integer"}, status=400)
            if "status" in body:
                node.status = OPEN if str(body["status"]) == OPEN else CLOSED
            return self._send_json({"valve": node.to_dict()})

        return self._send_json({"error": "endpoint not found"}, status=404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path.startswith("/api/valves/"):
            try:
                valve_id = int(path.rsplit("/", 1)[-1])
            except ValueError:
                return self._send_json({"error": "invalid id"}, status=400)
            removed = TRUNK.remove(valve_id)
            if removed is None:
                return self._send_json({"error": "valve chamber not found"}, status=404)
            return self._send_json({"removed": removed.to_dict(), "size": len(TRUNK.valves)})

        if path == "/api/valves":
            mode = (query.get("mode", [""])[0] or "").lower()
            if mode == "first":
                removed = TRUNK.remove_first()
            elif mode == "last":
                removed = TRUNK.remove_last()
            elif "position" in query:
                try:
                    position = int(query["position"][0])
                except (TypeError, ValueError):
                    return self._send_json({"error": "position must be an integer"}, status=400)
                removed = TRUNK.valves.remove_at(position)
            else:
                return self._send_json(
                    {"error": "use /<id>, ?mode=first|last or ?position=N"}, status=400
                )
            if removed is None:
                return self._send_json({"error": "nothing to remove"}, status=404)
            return self._send_json({"removed": removed.to_dict(), "size": len(TRUNK.valves)})

        return self._send_json({"error": "endpoint not found"}, status=404)


class DualStackServer(ThreadingHTTPServer):
    address_family = socket.AF_INET6

    def server_bind(self):
        try:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except (AttributeError, OSError):
            pass
        super().server_bind()


def run():
    try:
        server = DualStackServer(("", PORT), RequestHandler)
    except Exception:
        server = HTTPServer(("0.0.0.0", PORT), RequestHandler)

    print(f"AquaRuta backend running at http://localhost:{PORT} and http://127.0.0.1:{PORT}")
    print(f"Serving the frontend from: {FRONTEND_DIR}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    run()
