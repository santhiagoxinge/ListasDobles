# AquaRuta — Doubly Linked List Workshop (Real-Life Case Study)

> University workshop: **doubly linked lists applied to a real-life case**.
> Source code, identifiers and comments are in **English**. The user interface is in **Spanish**.

## 1. Real-Life Case

**AquaRuta — municipal water trunk main (red de acueducto).**

Every valve chamber along the pipeline is a node of a doubly linked list:

```text
head  ◀── prev ◀── [Compuerta de Admisión] ⇄ [Cámara Norte] ⇄ [Cámara Central] ⇄ ... ⇄ [Válvula de Descarga]  ──▶ tail
                                                  next ──▶
```

Why a doubly linked list is the right structure here:

| Real need in a water trunk main | Doubly linked list support |
| --- | --- |
| The operator walks the pipe **upstream and downstream** | `prev` / `next` moves one chamber in **O(1)** |
| New chambers at the intake or at the reservoir | `add_first` / `add_last` in **O(1)** |
| A chamber is decommissioned at **either end** | `remove_first` / `remove_last` in **O(1)** — a singly linked list can only do this at the head |
| Reviewing the line from the reservoir back to the intake | `to_list_backward()` traversal |
| Reading a chamber and both of its neighbours | neighbour access in **O(1)** |

This case was chosen because it is uncommon in data-structure workshops and the bidirectional pointer has a physical meaning: `prev` is **upstream**, `next` is **downstream**.

## 2. Project Structure

```text
ListasDobles/
├── README.md                      # this file (English)
├── backend/
│   ├── app.py                     # DoublyLinkedList + TrunkMain + REST API (stdlib only)
│   ├── test_doubly_linked_list.py # 19 assertions covering the whole list
│   └── requirements.txt           # empty — no external dependencies
└── frontend/
    ├── index.html                 # semantic UI in Spanish
    ├── app.js                     # API client, local fallback, spatial engine
    └── styles/
        ├── tokens.css             # design tokens (Apple palette + spacing/motion scales)
        ├── base.css               # reset, typography, layout, atmosphere
        ├── components.css         # glass bar, buttons, segmented control, scene, corridor
        └── animations.css         # scroll-driven reveals, state feedback, reduced motion
```

## 3. Backend (Python)

`backend/app.py` contains three layers:

- `ValveNode` — `valve_id`, `name`, `elevation`, `status` (Abierta / Cerrada), `prev`, `next`.
- `DoublyLinkedList` — `add_first`, `add_last`, `insert_at`, `insert_after`, `remove_first`,
  `remove_last`, `remove_by_id`, `remove_at`, `clear`, `find_by_id`, `find_by_name`,
  `count_by_status`, `to_list_forward`, `to_list_backward`, plus `_node_at` which walks from
  the **nearest end** (O(n/2)).
- `TrunkMain` — wraps the list and the operator cursor: `move("downstream" | "upstream")`,
  `remove()` (keeps the cursor on a valid neighbour), `seed_demo()`.

### REST API

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/health` | Service check |
| GET | `/api/valves?direction=forward\|backward` | Chambers in order (upstream / downstream) |
| GET | `/api/valves?search=query` | Search by name |
| GET | `/api/valves/<id>` | One chamber |
| POST | `/api/valves` | `{name, elevation, status, mode: last\|first\|at\|after, position, after_id}` |
| PUT | `/api/valves/<id>` | Update `name`, `elevation` or `status` |
| DELETE | `/api/valves/<id>` | Remove by id |
| DELETE | `/api/valves?mode=first\|last` | Remove at the intake or the reservoir (O(1)) |
| DELETE | `/api/valves?position=N` | Remove by position |
| POST | `/api/operator/move` | `{direction: upstream\|downstream}` |
| GET | `/api/operator` | Current operator chamber |
| GET | `/api/stats` | Size, head, tail, open, closed, elevation drop |
| POST | `/api/reset` | Restore the demo trunk main |
| POST | `/api/clear` | Empty the trunk main |

### Run

```bash
cd backend
python app.py
```

Open <http://127.0.0.1:8000> — the Python server also serves the static frontend.

Run the tests:

```bash
cd backend
python test_doubly_linked_list.py
```

## 4. Frontend — two skills combined

The interface merges the **Interactive 3D & Spatial Frontend** skill with the
**Apple Frontend** skill. Where the two disagree, the Apple skill wins on restraint and
the spatial skill wins on depth, because depth here communicates structure, not decoration.

### From the spatial skill

- **Floating 3D cards** — upstream / operator / downstream cards with independent
  `data-float` speed, `data-amp` amplitude, `data-depth` (`translateZ`) and phase offsets, using
  `y = baseY + sin(time * speed + phase) * amplitude`.
- **Spatial UI with meaning** — the operator card sits in front (66px), the pointer cards behind
  (26px), the pipe rail is pushed to `translateZ(-140px)`.
- **Depth in the corridor** — each chamber is offset in Z along the list, so the linked list is
  read as a pipeline receding into the distance.
- **Pointer interaction** — cards tilt toward the cursor and spring back on leave.
- **Parallax** — atmosphere washes move slower than the foreground.
- **Fallback** — the demo keeps working (read-only, local list) if Python is not running.
- **Performance** — one `requestAnimationFrame` loop, only `transform`/`opacity` writes, the loop is
  cancelled when the tab is hidden.

### From the Apple skill

- **Typography** — `-apple-system` / SF Pro stack, few weights, tight tracking, 4pt spacing scale.
- **Palette** — neutral `#f5f5f7` surfaces with a single water accent (`#0071e3`) plus semantic
  green / orange / red. No neon, no saturated gradients.
- **Liquid Glass** — used only where it is functional: the sticky navigation bar and the metric
  tiles, with a `@supports` fallback when `backdrop-filter` is unavailable.
- **Components** — segmented control, pill buttons, real labels on every input, toast, hover /
  pressed / selected states.
- **Motion** — CSS-first, `transform` and `opacity` only, 140 ms micro-interactions,
  scroll-driven reveals via `@supports (animation-timeline: view())` with an
  `IntersectionObserver` fallback.
- **Accessibility** — semantic HTML, skip link, visible focus rings, keyboard-operable controls,
  `prefers-reduced-motion` fully respected, safe-area insets, `viewport-fit=cover`.

### Where to customize

| What | Where |
| --- | --- |
| Colors, spacing, radii, durations | `frontend/styles/tokens.css` |
| Layout and atmosphere | `frontend/styles/base.css` |
| Card layout, corridor, buttons | `frontend/styles/components.css` |
| Float speed, amplitude, depth, parallax | `data-float`, `data-amp`, `data-depth` in `frontend/index.html` |
| Scroll and state animations | `frontend/styles/animations.css` |
| Demo data and elevations | `TrunkMain.seed_demo()` in `backend/app.py` |

## 5. Five-minute classroom script

1. Run `python backend/app.py`, open the page, show the corridor: each card is a node, `prev` and
   `next` are printed on it.
2. Press **Aguas arriba / Aguas abajo** — the list is traversed in both directions, which is only
   possible with a doubly linked list.
3. Move the operator with **▲ / ▼** — one `prev` / `next` jump, O(1).
4. Add a chamber at the intake and at the reservoir — both insertions are O(1).
5. Remove the **cámara de descarga** (tail) — O(1) here, but O(n) in a singly linked list.
6. Toggle a valve open/closed and search a chamber by name.

## 6. Requirements Checklist

| Requirement | Status |
| --- | --- |
| Real-life case, not a music player | Water trunk main |
| Doubly linked list in Python | `DoublyLinkedList` + `ValveNode` |
| Frontend included | Spatial + Apple inspired, Spanish UI |
| Code in English, interface in Spanish | Implemented |
| README in English | This file |
| No dependencies | Standard library + plain HTML/CSS/JS |
