/* AquaRuta frontend logic.
   Identifiers, comments and API field names are in English.
   Every user-facing string is in Spanish.

   Responsibilities:
     1. state + REST client for the Python backend
     2. rendering (corridor, spatial cards, metrics, search)
     3. spatial engine (float motion, pointer tilt, parallax, reduced motion)
*/

const API_BASE = "http://127.0.0.1:8000/api";
const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
const supportsHover = window.matchMedia("(hover: hover) and (pointer: fine)");

/* =========================================================
   1. State
   ========================================================= */

const state = {
  valves: [],
  direction: "forward",
  currentId: null,
  insertMode: "last",
  backendOnline: false,
};

/* =========================================================
   2. REST client
   ========================================================= */

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Error del servidor");
  return data;
}

async function loadValves() {
  try {
    const data = await api(`/valves?direction=${state.direction}`);
    state.valves = data.valves || [];
    state.currentId = data.current_id ?? null;
    state.backendOnline = true;
  } catch {
    // Classroom fallback: the demo keeps working without the Python server.
    state.backendOnline = false;
    const forward = LocalTrunkMain.demoValves();
    state.valves = state.direction === "backward" ? [...forward].reverse() : forward;
    state.currentId = forward.length ? forward[0].id : null;
  }
  renderStatus();
}

/* Minimal in-memory trunk main used only when the backend is offline. */
class LocalTrunkMain {
  static demoValves() {
    return [
      { id: 1, name: "Compuerta de Admisión", elevation: 3240, status: "Abierta" },
      { id: 2, name: "Cámara de Reposo Norte", elevation: 3210, status: "Abierta" },
      { id: 3, name: "Estación de Bombeo PB-1", elevation: 3185, status: "Abierta" },
      { id: 4, name: "Cruce de Calle 45", elevation: 3160, status: "Cerrada" },
      { id: 5, name: "Cámara Central", elevation: 3130, status: "Abierta" },
      { id: 6, name: "Purga de Sedimentos", elevation: 3105, status: "Cerrada" },
      { id: 7, name: "Cámara de Reposo Sur", elevation: 3080, status: "Abierta" },
      { id: 8, name: "Válvula de Descarga", elevation: 3055, status: "Abierta" },
    ];
  }
}

/* =========================================================
   3. DOM helpers
   ========================================================= */

const $ = (id) => document.getElementById(id);
const corridorEl = $("corridor");
const toastEl = $("toast");
let toastTimer = null;

function showToast(text) {
  toastEl.textContent = text;
  toastEl.classList.add("is-visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove("is-visible"), 2800);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[char]));
}

function requireBackend(action) {
  if (state.backendOnline) return true;
  showToast(`${action} necesita el backend de Python en ejecución.`);
  return false;
}

/* =========================================================
   4. Rendering
   ========================================================= */

function renderStatus() {
  const pill = $("statusPill");
  const text = $("statusText");
  if (state.backendOnline) {
    pill.dataset.state = "online";
    text.textContent = "Backend conectado";
  } else {
    pill.dataset.state = "offline";
    text.textContent = "Vista local";
  }
}

function renderMetrics() {
  const valves = state.valves;
  const open = valves.filter((v) => v.status === "Abierta").length;
  const closed = valves.length - open;
  $("statSize").textContent = valves.length;
  $("statOpen").textContent = open;
  $("statClosed").textContent = closed;

  const elevations = valves.map((v) => v.elevation);
  const drop = elevations.length ? Math.max(...elevations) - Math.min(...elevations) : 0;
  $("statDrop").textContent = drop ? `${drop} m` : "—";
}

function renderCorridor() {
  corridorEl.innerHTML = "";
  $("emptyNote").hidden = state.valves.length > 0;

  const total = state.valves.length;
  state.valves.forEach((valve, index) => {
    const chamber = document.createElement("article");
    chamber.className = "chamber" + (valve.id === state.currentId ? " is-current" : "");
    chamber.dataset.status = valve.status;
    chamber.dataset.id = valve.id;
    chamber.setAttribute("role", "listitem");

    // Depth follows the list order: front = near the operator, back = far away.
    const distance = index - (total - 1) / 2;
    chamber.style.setProperty("--z", `${(-distance * 16).toFixed(1)}px`);
    chamber.style.setProperty("--shift", `${(distance * 10).toFixed(1)}px`);

    chamber.innerHTML = `
      <div class="chamber-head">
        <span>#${valve.id} · posición ${index}</span>
        <span class="chip" data-status="${escapeHtml(valve.status)}">${escapeHtml(valve.status)}</span>
      </div>
      <h3 class="chamber-name">${escapeHtml(valve.name)}</h3>
      <p class="chamber-elev">Cota ${valve.elevation} m s. n. m.</p>
      <div class="chamber-pointers">
        <span>prev: ${index > 0 ? `#${state.valves[index - 1].id}` : "null"}</span>
        <span>next: ${index < total - 1 ? `#${state.valves[index + 1].id}` : "null"}</span>
      </div>
      <div class="chamber-actions">
        <button class="btn btn-compact press" data-action="toggle" type="button">
          ${valve.status === "Abierta" ? "Cerrar" : "Abrir"}
        </button>
        <button class="btn btn-compact press btn-danger" data-action="remove" type="button">Quitar</button>
      </div>
    `;
    corridorEl.appendChild(chamber);

    if (index < total - 1) {
      const arrow = document.createElement("span");
      arrow.className = "arrow";
      arrow.textContent = "⟷";
      arrow.setAttribute("aria-hidden", "true");
      corridorEl.appendChild(arrow);
    }
  });

  scrollCurrentIntoView();
}

function renderSceneCards() {
  const valves = state.valves;
  const index = valves.findIndex((v) => v.id === state.currentId);
  const current = index >= 0 ? valves[index] : null;
  const upstream = index > 0 ? valves[index - 1] : null;
  const downstream = index >= 0 && index < valves.length - 1 ? valves[index + 1] : null;

  $("fcCurrent").textContent = current ? current.name : "Sin operador";
  $("fcCurrentMeta").textContent = current
    ? `${current.elevation} m · ${current.status}`
    : "el conducto está vacío";
  $("fcPrev").textContent = upstream ? upstream.name : "head ·Compuerta";
  $("fcPrevMeta").textContent = upstream ? `prev → #${upstream.id} · O(1)` : "no hay nodo anterior";
  $("fcNext").textContent = downstream ? downstream.name : "tail · Descarga";
  $("fcNextMeta").textContent = downstream ? `next → #${downstream.id} · O(1)` : "no hay nodo siguiente";
}

function render() {
  renderCorridor();
  renderSceneCards();
  renderMetrics();
}

function scrollCurrentIntoView() {
  const current = corridorEl.querySelector(".chamber.is-current");
  if (current) {
    corridorEl.scrollTo({
      left: current.offsetLeft - corridorEl.clientWidth / 2 + current.clientWidth / 2,
      behavior: motionQuery.matches ? "auto" : "smooth",
    });
  }
}

/* =========================================================
   5. Operations
   ========================================================= */

async function addChamber(event) {
  event.preventDefault();
  const name = $("inputName").value.trim();
  if (!name) {
    showToast("Escribe el nombre de la cámara.");
    return;
  }
  if (!requireBackend("Añadir una cámara")) return;

  const payload = {
    name,
    elevation: Number($("inputElevation").value || 3000),
    status: $("inputStatus").value,
    mode: state.insertMode,
    position: Number($("inputPosition").value || 0),
    after_id: Number($("inputAfterId").value || 0),
  };

  try {
    await api("/valves", { method: "POST", body: JSON.stringify(payload) });
    $("inputName").value = "";
    const label = {
      last: "al final", first: "al inicio", at: "en la posición indicada", after: "después de la cámara de referencia",
    }[state.insertMode];
    showToast(`Cámara añadida ${label}.`);
    await loadValves();
    render();
  } catch (error) {
    showToast(`No se pudo añadir: ${error.message}`);
  }
}

async function moveOperator(direction) {
  if (!requireBackend("Mover al operador")) return;
  try {
    const data = await api("/operator/move", {
      method: "POST",
      body: JSON.stringify({ direction }),
    });
    if (data.status === "end_of_line") showToast("Fin del conducto: la válvula de descarga es el último nodo.");
    else if (data.status === "start_of_line") showToast("Inicio del conducto: la compuerta de admisión es el head.");
    else showToast(direction === "downstream" ? "El operador bajó aguas abajo." : "El operador subió aguas arriba.");
    await loadValves();
    render();
    pulseCurrent();
  } catch (error) {
    showToast(`No se pudo mover: ${error.message}`);
  }
}

async function setDirection(direction) {
  state.direction = direction;
  await loadValves();
  render();
}

async function removeChamber(valveId) {
  if (!requireBackend("Quitar una cámara")) return;
  try {
    await api(`/valves/${valveId}`, { method: "DELETE" });
    showToast(`Cámara #${valveId} fuera del conducto.`);
    await loadValves();
    render();
  } catch (error) {
    showToast(`No se pudo quitar: ${error.message}`);
  }
}

async function removeEdge(mode) {
  if (!requireBackend("Quitar una cámara")) return;
  try {
    await api(`/valves?mode=${mode}`, { method: "DELETE" });
    showToast(mode === "first" ? "Se quitó la cámara de admisión." : "Se quitó la cámara de descarga.");
    await loadValves();
    render();
  } catch (error) {
    showToast(`No se pudo quitar: ${error.message}`);
  }
}

async function toggleStatus(valveId, chamberEl) {
  if (!requireBackend("Cambiar el estado")) return;
  const valve = state.valves.find((v) => v.id === valveId);
  const nextStatus = valve.status === "Abierta" ? "Cerrada" : "Abierta";
  try {
    await api(`/valves/${valveId}`, {
      method: "PUT",
      body: JSON.stringify({ status: nextStatus }),
    });
    showToast(`${valve.name}: ${nextStatus === "Abierta" ? "válvula abierta" : "válvula cerrada"}.`);
    await loadValves();
    render();
    if (chamberEl) chamberEl.scrollIntoView({ block: "nearest", behavior: motionQuery.matches ? "auto" : "smooth" });
  } catch (error) {
    showToast(`No se pudo actualizar: ${error.message}`);
  }
}

async function searchValves() {
  const query = $("searchInput").value.trim();
  const listEl = $("searchResults");
  listEl.innerHTML = "";

  let results = [];
  if (state.backendOnline) {
    try {
      const data = await api(`/valves?search=${encodeURIComponent(query)}`);
      results = data.valves || [];
    } catch (error) {
      showToast(`Búsqueda fallida: ${error.message}`);
      return;
    }
  } else {
    const needle = query.toLowerCase();
    results = state.valves.filter((v) => v.name.toLowerCase().includes(needle));
  }

  if (!results.length) {
    listEl.innerHTML = '<li class="empty">Ninguna cámara coincide con la búsqueda.</li>';
    return;
  }

  results.forEach((valve) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <span><strong>#${valve.id}</strong> ${escapeHtml(valve.name)} · ${valve.elevation} m</span>
      <span class="chip" data-status="${escapeHtml(valve.status)}">${escapeHtml(valve.status)}</span>
    `;
    listEl.appendChild(item);
  });
}

async function resetTrunk() {
  if (!requireBackend("Cargar la demostración")) return;
  await api("/reset", { method: "POST" });
  await loadValves();
  render();
  showToast("Conducto de demostración cargado.");
}

async function clearTrunk() {
  if (!requireBackend("Vaciar el conducto")) return;
  await api("/clear", { method: "POST" });
  await loadValves();
  render();
  showToast("Conducto vacío.");
}

function pulseCurrent() {
  const current = corridorEl.querySelector(".chamber.is-current");
  if (!current) return;
  current.classList.remove("is-moved");
  void current.offsetWidth; // restart the animation
  current.classList.add("is-moved");
}

/* =========================================================
   6. Spatial engine
   float:  y = baseY + sin(time * speed + phase) * amplitude
   tilt:   pointer-driven rotation on the pointer card
   parallax: atmosphere layers move slower than the foreground
   ========================================================= */

function initSpatialEngine() {
  const cards = [...document.querySelectorAll(".float-card")];
  const layers = [...document.querySelectorAll("[data-depth]")].filter(
    (el) => !el.classList.contains("float-card")
  );
  const start = performance.now();
  const tilt = new Map(cards.map((card) => ({ card, x: 0, y: 0, tx: 0, ty: 0 })));

  cards.forEach((entry) => {
    entry.card.addEventListener("pointermove", (event) => {
      if (motionQuery.matches || !supportsHover.matches) return;
      const rect = entry.card.getBoundingClientRect();
      entry.tx = ((event.clientY - rect.top) / rect.height - 0.5) * -8;
      entry.ty = ((event.clientX - rect.left) / rect.width - 0.5) * 8;
    });
    entry.card.addEventListener("pointerleave", () => {
      entry.tx = 0;
      entry.ty = 0;
    });
  });

  let pointerX = 0;
  let pointerY = 0;
  let smoothX = 0;
  let smoothY = 0;
  let frame = 0;

  window.addEventListener("pointermove", (event) => {
    pointerX = (event.clientX / window.innerWidth - 0.5) * 2;
    pointerY = (event.clientY / window.innerHeight - 0.5) * 2;
  }, { passive: true });

  function frameStep(now) {
    const time = (now - start) / 1000;
    smoothX += (pointerX - smoothX) * 0.06;
    smoothY += (pointerY - smoothY) * 0.06;
    const still = motionQuery.matches;

    cards.forEach((entry, index) => {
      const speed = Number(entry.card.dataset.float || 1);
      const amplitude = Number(entry.card.dataset.amp || 10);
      const depth = Number(entry.card.dataset.depth || 30);
      const phase = index * 1.7;

      const floatY = still ? 0 : Math.sin(time * speed + phase) * amplitude;
      entry.x += (entry.tx - entry.x) * 0.12;
      entry.y += (entry.ty - entry.y) * 0.12;

      const driftX = still ? 0 : smoothX * depth * 0.12;
      const driftY = still ? 0 : smoothY * depth * 0.12;

      entry.card.style.transform =
        `translate3d(${driftX.toFixed(2)}px, ${(floatY + driftY).toFixed(2)}px, ${depth}px) ` +
        `rotateX(${entry.x.toFixed(2)}deg) rotateY(${entry.y.toFixed(2)}deg)`;
    });

    layers.forEach((layer) => {
      const factor = Number(layer.dataset.depth || 4) / 200;
      layer.style.transform = still
        ? "none"
        : `translate3d(${(-smoothX * factor * 40).toFixed(2)}px, ${(-smoothY * factor * 40).toFixed(2)}px, 0)`;
    });

    frame = requestAnimationFrame(frameStep);
  }

  frame = requestAnimationFrame(frameStep);

  // Stop the loop when the tab is hidden: saves CPU/GPU.
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      cancelAnimationFrame(frame);
    } else {
      frame = requestAnimationFrame(frameStep);
    }
  });
}

/* Reveal fallback when scroll-driven animations are not supported. */
function initRevealFallback() {
  if (CSS.supports("animation-timeline: view()")) return;
  const targets = document.querySelectorAll(".reveal");
  targets.forEach((el) => el.classList.add("js-reveal"));

  if (!("IntersectionObserver" in window)) {
    targets.forEach((el) => el.classList.add("is-in"));
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("is-in");
      observer.unobserve(entry.target);
    });
  }, { rootMargin: "0px 0px -12% 0px", threshold: 0.15 });

  targets.forEach((el) => observer.observe(el));
}

/* =========================================================
   7. Wiring
   ========================================================= */

function initControls() {
  $("addForm").addEventListener("submit", addChamber);

  document.querySelectorAll("[data-direction]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-direction]").forEach((other) => {
        const selected = other === button;
        other.classList.toggle("is-selected", selected);
        other.setAttribute("aria-pressed", String(selected));
      });
      setDirection(button.dataset.direction);
    });
  });

  document.querySelectorAll("[data-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-mode]").forEach((other) => {
        const selected = other === button;
        other.classList.toggle("is-selected", selected);
        other.setAttribute("aria-pressed", String(selected));
      });
      state.insertMode = button.dataset.mode;
      $("modeInputs").hidden = !(state.insertMode === "at" || state.insertMode === "after");
      $("positionField").hidden = state.insertMode !== "at";
      $("afterField").hidden = state.insertMode !== "after";
    });
  });

  $("btnUpstream").addEventListener("click", () => moveOperator("upstream"));
  $("btnDownstream").addEventListener("click", () => moveOperator("downstream"));
  $("btnSearch").addEventListener("click", searchValves);
  $("searchInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      searchValves();
    }
  });

  $("btnRemoveFirst").addEventListener("click", () => removeEdge("first"));
  $("btnRemoveLast").addEventListener("click", () => removeEdge("last"));
  $("btnRemoveById").addEventListener("click", () => {
    const id = Number($("removeIdInput").value || 0);
    if (!id) {
      showToast("Escribe el ID de la cámara que quieres quitar.");
      return;
    }
    removeChamber(id);
  });
  $("btnReset").addEventListener("click", resetTrunk);
  $("btnClear").addEventListener("click", clearTrunk);

  // Delegated actions from the corridor cards.
  corridorEl.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    const chamber = button.closest(".chamber");
    const id = Number(chamber.dataset.id);
    if (button.dataset.action === "toggle") toggleStatus(id, chamber);
    if (button.dataset.action === "remove") removeChamber(id);
  });

  // Hero actions.
  document.querySelectorAll("[data-scroll]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelector(button.dataset.scroll)?.scrollIntoView({
        behavior: motionQuery.matches ? "auto" : "smooth",
      });
    });
  });

  document.querySelector('[data-action="demo-upstream"]')?.addEventListener("click", () => {
    document.querySelector('[data-direction="backward"]').click();
    showToast("Recorriendo el conducto desde la válvula de descarga.");
  });

  motionQuery.addEventListener("change", () => render());
}

initControls();
initSpatialEngine();
initRevealFallback();
loadValves().then(render);
