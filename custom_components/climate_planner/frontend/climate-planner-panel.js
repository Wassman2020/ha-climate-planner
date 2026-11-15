/* Climate Planner – side panel (vanilla web component, no build step). */

const SEASONS = [
  ["winter", "Invierno"],
  ["transition", "Entretiempo"],
  ["summer", "Verano"],
];
const SEASON_LABEL = Object.fromEntries(SEASONS);
const DAYS = ["L", "M", "X", "J", "V", "S", "D"];
const MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const MODE_LABEL = {
  off: "Apagar", heat: "Calor", cool: "Frío", heat_cool: "Auto", auto: "Auto",
  dry: "Deshumidificar", fan_only: "Ventilador",
};
const MODE_COLOR = {
  presence: "#4caf50",
  heat: "#e8743b", cool: "#3b8be8", heat_cool: "#8e5ee8", auto: "#8e5ee8",
  dry: "#2fa59a", fan_only: "#8a9099", off: "#666",
};
const DEFAULTS = {
  winter: { mode: "heat", temp: 21 },
  summer: { mode: "cool", temp: 25 },
  transition: { mode: "heat_cool", temp: 23 },
};

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const hm = (s) => {
  const [h, m] = String(s).split(":").map(Number);
  return h * 60 + m;
};
const clone = (o) => JSON.parse(JSON.stringify(o));
const modeLabel = (m) => MODE_LABEL[m] || m || "—";

function segments(slots) {
  const days = Array.from({ length: 7 }, () => []);
  for (const s of slots) {
    if (!s.start || !s.end) continue; // point actions are drawn separately
    const a = hm(s.start) % 1440;
    const b = hm(s.end) % 1440;
    if (a === b) continue;
    for (const d of s.days) {
      if (b > a) days[d].push({ from: a, to: b, s });
      else {
        days[d].push({ from: a, to: 1440, s });
        if (b > 0) days[(d + 1) % 7].push({ from: 0, to: b, s });
      }
    }
  }
  return days;
}

function points(slots) {
  const days = Array.from({ length: 7 }, () => []);
  for (const s of slots) if (s.start && !s.end) for (const d of s.days) days[d].push(s);
  return days;
}

function gridHTML(slots) {
  const segs = segments(slots);
  const pts = points(slots);
  const rows = DAYS.map((label, i) => {
    const blocks = segs[i]
      .map((g) => {
        const t = g.s.temperature != null && g.s.temperature !== "" ? `${g.s.temperature}°` : "";
        const title = `${g.s.start}–${g.s.end} · ${modeLabel(g.s.hvac_mode)} ${t}`;
        return `<div class="seg" title="${esc(title)}" style="left:${g.from / 14.4}%;width:${(g.to - g.from) / 14.4}%;background:${MODE_COLOR[g.s.hvac_mode] || "var(--primary-color)"}">${g.to - g.from >= 150 ? esc(t) : ""}</div>`;
      })
      .join("") + pts[i]
      .map((p) => `<div class="pt ${p.hvac_mode === "off" ? "off" : ""}" title="${esc(`${p.start} · ${modeLabel(p.hvac_mode)}`)}" style="left:${hm(p.start) / 14.4}%;${p.hvac_mode === "off" ? "" : `background:${MODE_COLOR[p.hvac_mode] || "var(--primary-color)"}`}"></div>`)
      .join("");
    return `<div class="grow"><span class="dl">${label}</span><div class="bar">${blocks}</div></div>`;
  }).join("");
  const ticks = [0, 6, 12, 18, 24].map((h) => `<span style="left:${(h / 24) * 100}%">${h}</span>`).join("");
  return `<div class="grid">${rows}<div class="grow"><span class="dl"></span><div class="ticks">${ticks}</div></div></div>`;
}

const CSS = `
:host{display:block;background:var(--primary-background-color);min-height:100vh;color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family, Roboto, sans-serif)}
.toolbar{display:flex;align-items:center;height:56px;padding:0 12px;background:var(--app-header-background-color);color:var(--app-header-text-color, #fff);font-size:20px;position:sticky;top:0;z-index:2}
.toolbar .title{margin-left:8px}
.content{max-width:900px;margin:0 auto;padding:12px}
.card{background:var(--card-background-color);border-radius:12px;padding:14px;margin-bottom:12px;box-shadow:var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,.2))}
.card.disabled{opacity:.55}
h3{margin:0 0 10px;font-weight:500}
.row{display:flex;align-items:center;gap:10px;margin:6px 0}
.wrap{flex-wrap:wrap}
.between{justify-content:space-between}
.end{justify-content:flex-end;flex-wrap:wrap}
.name{font-size:17px;font-weight:500}
.sub{color:var(--secondary-text-color);font-size:13px;margin-top:2px}
.lbl{margin:14px 0 6px;font-weight:500;color:var(--secondary-text-color);font-size:13px;text-transform:uppercase;letter-spacing:.04em}
label.sw{display:flex;align-items:center;gap:8px;margin:6px 0;cursor:pointer}
label.f{display:flex;flex-direction:column;font-size:12px;color:var(--secondary-text-color);gap:3px}
input,select{font:inherit;color:var(--primary-text-color);background:var(--secondary-background-color, #f3f3f3);border:1px solid var(--divider-color);border-radius:8px;padding:7px 8px}
input[type=checkbox]{width:20px;height:20px;accent-color:var(--primary-color)}
input[type=number]{width:80px}
input.wide{width:100%;box-sizing:border-box}
button{font:inherit;border:1px solid var(--divider-color);background:transparent;color:var(--primary-text-color);border-radius:8px;padding:7px 12px;cursor:pointer}
button.primary{background:var(--primary-color);color:var(--text-primary-color, #fff);border-color:var(--primary-color)}
button.danger{color:var(--error-color, #db4437);border-color:var(--error-color, #db4437)}
button.mini{padding:3px 8px;font-size:12px}
.tabs{display:flex;gap:6px;margin:4px 0 12px;overflow-x:auto}
.tab{flex:1;white-space:nowrap}
.tab.on{background:var(--primary-color);color:var(--text-primary-color, #fff);border-color:var(--primary-color)}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#4caf50;margin-left:6px;vertical-align:middle}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{border-radius:16px;padding:5px 12px}
.chip.on{background:var(--primary-color);color:var(--text-primary-color, #fff);border-color:var(--primary-color)}
.slot{border:1px solid var(--divider-color);border-radius:10px;padding:10px;margin-bottom:8px}
.days{display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.day{width:34px;height:34px;padding:0;border-radius:50%}
.day.on{background:var(--primary-color);color:var(--text-primary-color, #fff);border-color:var(--primary-color)}
.grid{margin-top:8px}
.grow{display:flex;align-items:center;gap:6px;margin:3px 0}
.dl{width:14px;font-size:12px;color:var(--secondary-text-color)}
.bar{position:relative;flex:1;height:20px;border-radius:5px;background:var(--secondary-background-color, #eee);overflow:hidden}
.seg{position:absolute;top:0;bottom:0;border-radius:4px;color:#fff;font-size:11px;display:flex;align-items:center;justify-content:center;overflow:hidden}
.pt{position:absolute;top:0;bottom:0;width:3px;margin-left:-1px;background:var(--primary-color)}
.pt.off{background:var(--primary-text-color);opacity:.7}
.badge{display:inline-block;font-size:11px;padding:1px 7px;border-radius:10px;border:1px solid var(--divider-color);margin-left:6px;vertical-align:middle;color:var(--secondary-text-color)}
.legend{font-size:11px;color:var(--secondary-text-color);margin-top:4px}
.ticks{position:relative;flex:1;height:14px;font-size:10px;color:var(--secondary-text-color)}
.ticks span{position:absolute;transform:translateX(-50%)}
.ticks span:first-child{transform:none}.ticks span:last-child{transform:translateX(-100%)}
.empty{color:var(--secondary-text-color);text-align:center;padding:20px}
.toast{position:fixed;left:50%;bottom:20px;transform:translateX(-50%);background:#323232;color:#fff;padding:10px 16px;border-radius:8px;opacity:0;transition:opacity .2s;pointer-events:none;max-width:90vw;z-index:5}
.toast.show{opacity:1}.toast.err{background:var(--error-color, #db4437)}
`;

class ClimatePlannerPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._data = null;
    this._tab = null;
    this._edit = null;
    this._dates = null;
    this._confirmDel = null;
    this._view = "schedules";
    this._pedit = null;
    this._pAll = false;
    this.shadowRoot.addEventListener("click", (e) => this._onClick(e));
    this.shadowRoot.addEventListener("change", (e) => this._onChange(e));
    this.shadowRoot.addEventListener("input", (e) => this._onInput(e));
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    const mb = this.shadowRoot.querySelector("ha-menu-button");
    if (mb) mb.hass = hass;
    if (first) {
      this._render();
      this._load();
    }
  }
  set narrow(n) {
    this._narrow = n;
    const mb = this.shadowRoot.querySelector("ha-menu-button");
    if (mb) mb.narrow = n;
  }
  set panel(_p) {}

  /* ------------------------------------------------------------ data */
  async _ws(type, extra = {}) {
    try {
      const res = await this._hass.callWS({ type, ...extra });
      this._data = res;
      return res;
    } catch (err) {
      this._toast(err?.message || String(err), true);
      throw err;
    }
  }
  async _load() {
    try {
      await this._ws("climate_planner/get");
      if (!this._tab) this._tab = this._data.season;
      this._render();
    } catch (_e) { /* toast shown */ }
  }
  _climates() {
    return Object.values(this._hass.states)
      .filter((s) => s.entity_id.startsWith("climate."))
      .map((s) => ({ id: s.entity_id, name: s.attributes.friendly_name || s.entity_id, attrs: s.attributes }))
      .sort((a, b) => a.name.localeCompare(b.name, "es"));
  }
  _entName(id) {
    return this._hass.states[id]?.attributes.friendly_name || id;
  }
  _schedule(id) {
    return this._data.schedules.find((s) => s.id === id);
  }

  /* ---------------------------------------------------------- render */
  _render() {
    if (!this._content) {
      this.shadowRoot.innerHTML = `<style>${CSS}</style>
        <div class="toolbar"><ha-menu-button></ha-menu-button><div class="title">Climatización</div></div>
        <div class="content"></div>
        <div id="toast" class="toast"></div>`;
      this._content = this.shadowRoot.querySelector(".content");
      const mb = this.shadowRoot.querySelector("ha-menu-button");
      if (mb) {
        mb.hass = this._hass;
        mb.narrow = this._narrow;
      }
    }
    this._content.innerHTML = this._data ? this._body() : '<div class="card">Cargando…</div>';
  }

  _body() {
    if (this._edit) return this._settingsCard() + this._editor();
    if (this._pedit) return this._presenceEditor();
    const views = [["schedules", "Horarios"], ["presence", "Presencia"]]
      .map(([k, l]) => `<button class="tab ${k === this._view ? "on" : ""}" data-action="view" data-view="${k}">${l}</button>`)
      .join("");
    if (this._view === "presence") return `${this._settingsCard()}<div class="tabs">${views}</div>${this._presenceList()}`;
    const list = this._data.schedules.filter((s) => s.seasons.includes(this._tab));
    const tabs = SEASONS.map(([k, l]) => {
      const n = this._data.schedules.filter((s) => s.seasons.includes(k)).length;
      return `<button class="tab ${k === this._tab ? "on" : ""}" data-action="tab" data-season="${k}">${l} (${n})${k === this._data.season ? '<span class="dot" title="Temporada activa"></span>' : ""}</button>`;
    }).join("");
    return `${this._settingsCard()}
      <div class="tabs">${views}</div>
      <div class="tabs">${tabs}</div>
      ${list.length ? list.map((s) => this._card(s)).join("") : `<div class="card empty">No hay horarios de ${SEASON_LABEL[this._tab].toLowerCase()}.</div>`}
      <div class="row end"><button class="primary" data-action="new">+ Nuevo horario</button></div>`;
  }

  _settingsCard() {
    const d = this._data;
    const opts = SEASONS.map(([k, l]) => `<option value="${k}" ${k === d.season ? "selected" : ""}>${l}</option>`).join("");
    return `<div class="card">
      <div class="row between">
        <label class="sw"><input type="checkbox" data-setting="enabled" ${d.enabled ? "checked" : ""}> Programación activa</label>
        <button data-action="resync">Aplicar ahora</button>
      </div>
      <div class="row"><span>Temporada activa</span><select data-setting="season">${opts}</select></div>
      <label class="sw"><input type="checkbox" data-setting="auto_season" ${d.auto_season ? "checked" : ""}> Cambiar de temporada por fechas</label>
      <label class="sw"><input type="checkbox" data-setting="resync_on_start" ${d.resync_on_start ? "checked" : ""}> Aplicar el estado del horario al arrancar HA</label>
      ${d.auto_season && !this._edit ? this._datesEditor() : ""}
    </div>`;
  }

  _datesEditor() {
    const dates = this._dates || this._data.season_dates;
    const rows = dates.map((e, i) => {
      const [m, day] = e.start.split("-").map(Number);
      const sOpts = SEASONS.map(([k, l]) => `<option value="${k}" ${k === e.season ? "selected" : ""}>${l}</option>`).join("");
      const dOpts = Array.from({ length: 31 }, (_, j) => `<option ${j + 1 === day ? "selected" : ""}>${j + 1}</option>`).join("");
      const mOpts = MONTHS.map((n, j) => `<option value="${j + 1}" ${j + 1 === m ? "selected" : ""}>${n}</option>`).join("");
      return `<div class="row wrap"><span>Desde el</span>
        <select data-date="day" data-i="${i}">${dOpts}</select>
        <select data-date="month" data-i="${i}">${mOpts}</select>
        <span>→</span><select data-date="season" data-i="${i}">${sOpts}</select>
        <button class="mini danger" data-action="date-del" data-i="${i}">✕</button></div>`;
    }).join("");
    return `<div class="lbl">Cambios de temporada</div>${rows}
      <div class="row end"><button class="mini" data-action="date-add">+ Añadir cambio</button>
      ${this._dates ? '<button class="mini" data-action="date-cancel">Descartar</button><button class="mini primary" data-action="date-save">Guardar fechas</button>' : ""}</div>`;
  }

  _card(s) {
    const ents = s.entities.map((e) => esc(this._entName(e))).join(", ");
    const last = Object.values(this._data.last_actions || {})
      .filter((a) => a.schedule === s.name)
      .sort((a, b) => (a.time < b.time ? 1 : -1))[0];
    const lastTxt = last
      ? ` · Último: ${new Date(last.time).toLocaleString("es-ES", { weekday: "short", hour: "2-digit", minute: "2-digit" })} ${modeLabel(last.hvac_mode)}${last.temperature != null ? " " + last.temperature + "°" : ""}`
      : "";
    const del = this._confirmDel === s.id ? "¿Seguro?" : "Eliminar";
    return `<div class="card ${s.enabled ? "" : "disabled"}">
      <div class="row between">
        <div><div class="name">${esc(s.name)}${s.seasons.length === 3 ? '<span class="badge">Siempre</span>' : s.seasons.length > 1 ? s.seasons.map((x) => `<span class="badge">${SEASON_LABEL[x]}</span>`).join("") : ""}</div><div class="sub">${ents}${lastTxt}</div></div>
        <label class="sw" title="Activo"><input type="checkbox" data-toggle="${s.id}" ${s.enabled ? "checked" : ""}></label>
      </div>
      ${gridHTML(s.slots)}<div class="legend">Las rayas finas son acciones puntuales (por ejemplo, apagados de seguridad).</div>
      <div class="row end">
        <button class="mini" data-action="apply" data-id="${s.id}">Aplicar</button>
        <button class="mini" data-action="dup" data-id="${s.id}">Duplicar</button>
        <button class="mini" data-action="edit" data-id="${s.id}">Editar</button>
        <button class="mini danger" data-action="del" data-id="${s.id}">${del}</button>
      </div></div>`;
  }

  _modesFor(entities) {
    const all = this._climates();
    const sel = all.filter((c) => entities.includes(c.id));
    const src = sel.length ? sel : all;
    const modes = new Set();
    src.forEach((c) => (c.attrs.hvac_modes || []).forEach((m) => m !== "off" && modes.add(m)));
    let fans = null;
    sel.forEach((c) => {
      const f = c.attrs.fan_modes || [];
      fans = fans === null ? [...f] : fans.filter((x) => f.includes(x));
    });
    const first = sel[0]?.attrs || {};
    return {
      modes: [...modes, "off"],
      fans: fans || [],
      min: first.min_temp ?? 7,
      max: first.max_temp ?? 35,
      step: first.target_temp_step ?? 0.5,
    };
  }

  _editor() {
    const e = this._edit;
    const info = this._modesFor(e.entities);
    const seasonChips = SEASONS.map(([k, l]) => `<button class="chip ${e.seasons.includes(k) ? "on" : ""}" data-action="season" data-season="${k}">${l}</button>`).join("");
    const chips = this._climates()
      .map((c) => `<button class="chip ${e.entities.includes(c.id) ? "on" : ""}" data-action="ent" data-ent="${c.id}">${esc(c.name)}</button>`)
      .join("");
    const slots = e.slots.map((s, i) => this._slotEditor(s, i, info)).join("");
    return `<div class="card">
      <h3>${e.id ? "Editar horario" : "Nuevo horario"}</h3>
      <div class="row wrap">
        <label class="f" style="flex:1;min-width:180px">Nombre<input class="wide" data-e="name" value="${esc(e.name)}" placeholder="Ej. Salón invierno"></label>
      </div>
      <div class="lbl">Temporadas</div><div class="chips">${seasonChips}</div>
      <label class="sw"><input type="checkbox" data-e="enabled" ${e.enabled ? "checked" : ""}> Activo</label>
      <label class="sw"><input type="checkbox" data-e="off_outside" ${e.off_outside ? "checked" : ""}> Apagar al terminar cada franja</label>
      <div class="lbl">Equipos</div><div class="chips">${chips}</div>
      <div class="lbl">Franjas</div>${slots || '<div class="sub">Añade al menos una franja.</div>'}
      <button data-action="slot-add">+ Añadir franja</button>
      <div class="lbl">Vista semanal</div><div id="preview">${gridHTML(e.slots)}</div>
      <div class="row end" style="margin-top:12px">
        <button data-action="cancel">Cancelar</button>
        <button class="primary" data-action="save">Guardar</button>
      </div></div>`;
  }

  _slotEditor(s, i, info) {
    const days = DAYS.map((d, j) => `<button class="day ${s.days.includes(j) ? "on" : ""}" data-action="day" data-i="${i}" data-day="${j}">${d}</button>`).join("");
    const modes = [...info.modes];
    if (s.hvac_mode && !modes.includes(s.hvac_mode)) modes.push(s.hvac_mode);
    const mOpts = modes.map((m) => `<option value="${m}" ${m === s.hvac_mode ? "selected" : ""}>${modeLabel(m)}</option>`).join("");
    const fan = info.fans.length && s.hvac_mode !== "off"
      ? `<label class="f">Ventilador<select data-slot="fan_mode" data-i="${i}"><option value="">—</option>${info.fans
          .map((f) => `<option ${f === s.fan_mode ? "selected" : ""}>${esc(f)}</option>`)
          .join("")}</select></label>`
      : "";
    return `<div class="slot">
      <div class="days">${days}
        <button class="mini" data-action="preset" data-i="${i}" data-p="wk">L‑V</button>
        <button class="mini" data-action="preset" data-i="${i}" data-p="we">S‑D</button>
        <button class="mini" data-action="preset" data-i="${i}" data-p="all">Todos</button>
      </div>
      <div class="row wrap">
        <label class="f">Desde<input type="time" data-slot="start" data-i="${i}" value="${esc(s.start)}"></label>
        ${s.end ? `<label class="f">Hasta<input type="time" data-slot="end" data-i="${i}" value="${esc(s.end)}"></label>` : ""}
        <label class="sw" style="font-size:13px"><input type="checkbox" data-point="${i}" ${s.end ? "" : "checked"}> Puntual</label>
        <label class="f">Modo<select data-slot="hvac_mode" data-i="${i}">${mOpts}</select></label>
        <label class="f" ${s.hvac_mode === "off" ? 'style="display:none"' : ""}>Consigna °C<input type="number" data-slot="temperature" data-i="${i}" min="${info.min}" max="${info.max}" step="${info.step}" value="${s.temperature ?? ""}"></label>
        ${fan}
        <button class="mini danger" data-action="slot-del" data-i="${i}" style="margin-left:auto">✕</button>
      </div></div>`;
  }

  /* -------------------------------------------------------- presence */
  _sensorLabel(id) {
    const st = this._hass.states[id];
    const name = esc(st?.attributes.friendly_name || id);
    if (!st) return `${name} (no existe)`;
    if (st.state === "on") return `${name} <b style="color:#4caf50">● presencia</b>`;
    if (st.state === "off") return `${name} ○ vacío`;
    return `${name} <i>(${esc(st.state)})</i>`;
  }

  _windowsText(ws) {
    return ws
      .map((w) => {
        const d = w.days.length === 7 ? "Todos" : w.days.map((x) => DAYS[x]).join("");
        return `${d} ${w.start}–${w.end}`;
      })
      .join(", ");
  }

  _presenceList() {
    const rules = this._data.presence_rules || [];
    const cards = rules
      .map((r) => {
        const mode = r.mode === "outside"
          ? "fuera de las programaciones"
          : r.mode === "windows" ? `en ${this._windowsText(r.windows)}` : "siempre";
        const del = this._confirmDel === "p:" + r.entity ? "¿Seguro?" : "Eliminar";
        const cst = this._hass.states[r.entity]?.state;
        return `<div class="card ${r.enabled ? "" : "disabled"}">
          <div class="row between">
            <div><div class="name">${esc(this._entName(r.entity))}<span class="badge">${esc(modeLabel(cst))}</span></div>
              <div class="sub">Se apaga tras ${r.delay} min sin nadie, ${esc(mode)}.</div>
              <div class="sub">${r.sensors.map((x) => this._sensorLabel(x)).join(" · ")}</div></div>
            <label class="sw"><input type="checkbox" data-ptoggle="${r.entity}" ${r.enabled ? "checked" : ""}></label>
          </div>
          ${r.mode === "windows" ? gridHTML(r.windows.map((w) => ({ ...w, hvac_mode: "presence" }))) : ""}
          <div class="row end">
            <button class="mini" data-action="pedit" data-ent="${r.entity}">Editar</button>
            <button class="mini danger" data-action="pdel" data-ent="${r.entity}">${del}</button>
          </div></div>`;
      })
      .join("");
    return `${cards || '<div class="card empty">No hay reglas de presencia. Añade una para apagar un equipo cuando no haya nadie.</div>'}
      <div class="row end"><button class="primary" data-action="pnew">+ Nueva regla</button></div>`;
  }

  _presenceEditor() {
    const r = this._pedit;
    const climates = this._climates();
    const used = new Set((this._data.presence_rules || []).map((x) => x.entity));
    const cOpts = climates
      .map((c) => `<option value="${c.id}" ${c.id === r.entity ? "selected" : ""}>${esc(c.name)}${used.has(c.id) && c.id !== r._orig ? " (ya tiene regla)" : ""}</option>`)
      .join("");
    const classes = ["occupancy", "presence", "motion"];
    const sensors = Object.values(this._hass.states)
      .filter((s) => s.entity_id.startsWith("binary_sensor.") &&
        (this._pAll || classes.includes(s.attributes.device_class) || r.sensors.includes(s.entity_id)))
      .sort((a, b) => (a.attributes.friendly_name || "").localeCompare(b.attributes.friendly_name || "", "es"));
    const chips = sensors
      .map((s) => `<button class="chip ${r.sensors.includes(s.entity_id) ? "on" : ""}" data-action="psensor" data-sensor="${s.entity_id}">${esc(s.attributes.friendly_name || s.entity_id)}${s.state === "on" ? " ●" : ""}</button>`)
      .join("");
    const radio = (v, l) => `<label class="sw"><input type="radio" name="pmode" data-p="mode" value="${v}" ${r.mode === v ? "checked" : ""}> ${l}</label>`;
    const wins = r.windows
      .map((w, i) => `<div class="slot"><div class="days">${DAYS.map((d, j) => `<button class="day ${w.days.includes(j) ? "on" : ""}" data-action="wday" data-i="${i}" data-day="${j}">${d}</button>`).join("")}
        <button class="mini" data-action="wpreset" data-i="${i}" data-p="wk">L‑V</button>
        <button class="mini" data-action="wpreset" data-i="${i}" data-p="we">S‑D</button>
        <button class="mini" data-action="wpreset" data-i="${i}" data-p="all">Todos</button></div>
        <div class="row wrap"><label class="f">Desde<input type="time" data-w="start" data-i="${i}" value="${esc(w.start)}"></label>
        <label class="f">Hasta<input type="time" data-w="end" data-i="${i}" value="${esc(w.end)}"></label>
        <button class="mini danger" data-action="wdel" data-i="${i}" style="margin-left:auto">✕</button></div></div>`)
      .join("");
    return `<div class="card">
      <h3>${r._orig ? "Editar regla de presencia" : "Nueva regla de presencia"}</h3>
      <div class="row wrap">
        <label class="f" style="flex:1;min-width:180px">Equipo<select data-p="entity">${cOpts}</select></label>
        <label class="f">Minutos sin nadie<input type="number" min="1" max="720" data-p="delay" value="${r.delay}"></label>
      </div>
      <label class="sw"><input type="checkbox" data-p="enabled" ${r.enabled ? "checked" : ""}> Activa</label>
      <div class="lbl">Sensores de presencia</div>
      <div class="sub" style="margin-bottom:6px">Se considera que no hay nadie cuando ninguno detecta presencia. Los sensores no disponibles se ignoran.</div>
      <div class="chips">${chips || '<span class="sub">No hay sensores de presencia o movimiento.</span>'}</div>
      <label class="sw" style="font-size:13px"><input type="checkbox" data-p="all" ${this._pAll ? "checked" : ""}> Mostrar todos los sensores binarios</label>
      <div class="lbl">Cuándo apagar</div>
      ${radio("always", "Siempre que esté encendido y no haya nadie")}
      ${radio("outside", "Solo fuera de las programaciones (si alguien lo enciende fuera de horario)")}
      ${radio("windows", "Solo en estas franjas horarias")}
      ${r.mode === "windows" ? `${wins}<button data-action="wadd">+ Añadir franja</button>` : ""}
      <div class="row end" style="margin-top:12px">
        <button data-action="pcancel">Cancelar</button>
        <button class="primary" data-action="psave">Guardar</button>
      </div></div>`;
  }

  async _savePresence() {
    const r = this._pedit;
    if (!r.entity) return this._toast("Elige un equipo", true), false;
    if (!r.sensors.length) return this._toast("Elige al menos un sensor", true), false;
    const delay = Number(r.delay);
    if (!(delay >= 1 && delay <= 720)) return this._toast("El retardo debe estar entre 1 y 720 minutos", true), false;
    if (r.mode === "windows") {
      if (!r.windows.length) return this._toast("Añade al menos una franja", true), false;
      for (const w of r.windows) {
        if (!w.days.length) return this._toast("Cada franja necesita al menos un día", true), false;
        if (!w.start || !w.end || hm(w.start) % 1440 === hm(w.end) % 1440)
          return this._toast("Revisa las horas de las franjas", true), false;
      }
    }
    const rule = { entity: r.entity, sensors: r.sensors, delay, mode: r.mode, windows: r.mode === "windows" ? r.windows : [], enabled: r.enabled };
    try {
      await this._ws("climate_planner/presence/save", { rule });
      if (r._orig && r._orig !== r.entity) await this._ws("climate_planner/presence/delete", { entity: r._orig });
    } catch (_e) {
      return false;
    }
    this._pedit = null;
    this._toast("Regla guardada");
    return true;
  }

  _refreshPreview() {
    const p = this.shadowRoot.getElementById("preview");
    if (p && this._edit) p.innerHTML = gridHTML(this._edit.slots);
  }

  _toast(msg, err = false) {
    const t = this.shadowRoot.getElementById("toast");
    if (!t) return;
    t.textContent = msg;
    t.className = `toast show ${err ? "err" : ""}`;
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => (t.className = "toast"), err ? 6000 : 2500);
  }

  /* ---------------------------------------------------------- events */
  async _onClick(ev) {
    const btn = ev.target.closest("[data-action]");
    if (!btn) return;
    const a = btn.dataset.action;
    const i = Number(btn.dataset.i);
    const e = this._edit;
    try {
      switch (a) {
        case "tab":
          this._tab = btn.dataset.season;
          this._confirmDel = null;
          break;
        case "resync":
          await this._ws("climate_planner/resync");
          this._toast("Estado aplicado a los equipos");
          return;
        case "apply":
          await this._ws("climate_planner/resync", { schedule_id: btn.dataset.id });
          this._toast(this._schedule(btn.dataset.id)?.seasons.includes(this._data.season)
            ? "Horario aplicado"
            : "Este horario no es de la temporada activa");
          return;
        case "new": {
          const def = DEFAULTS[this._tab];
          this._edit = {
            name: "", seasons: [this._tab], enabled: true, off_outside: true, entities: [],
            slots: [{ days: [0, 1, 2, 3, 4], start: "07:00", end: "09:00", hvac_mode: def.mode, temperature: def.temp, fan_mode: null }],
          };
          break;
        }
        case "edit":
          this._edit = clone(this._schedule(btn.dataset.id));
          break;
        case "dup": {
          const c = clone(this._schedule(btn.dataset.id));
          delete c.id;
          c.name += " (copia)";
          this._edit = c;
          break;
        }
        case "del":
          if (this._confirmDel !== btn.dataset.id) {
            this._confirmDel = btn.dataset.id;
            break;
          }
          this._confirmDel = null;
          await this._ws("climate_planner/schedule/delete", { schedule_id: btn.dataset.id });
          this._toast("Horario eliminado");
          break;
        case "cancel":
          this._edit = null;
          break;
        case "save":
          if (!(await this._save())) return;
          break;
        case "ent": {
          const id = btn.dataset.ent;
          e.entities = e.entities.includes(id) ? e.entities.filter((x) => x !== id) : [...e.entities, id];
          break;
        }
        case "slot-add": {
          const last = e.slots[e.slots.length - 1];
          const def = DEFAULTS[e.seasons[0] || "winter"];
          e.slots.push(last
            ? !last.end ? { ...clone(last), start: last.start } : { ...clone(last), start: last.end, end: last.end === "23:00" ? "23:59" : String((Math.floor(hm(last.end) / 60) + 2) % 24).padStart(2, "0") + ":00" }
            : { days: [0, 1, 2, 3, 4], start: "07:00", end: "09:00", hvac_mode: def.mode, temperature: def.temp, fan_mode: null });
          break;
        }
        case "season":
          e.seasons = e.seasons.includes(btn.dataset.season)
            ? e.seasons.filter((x) => x !== btn.dataset.season)
            : SEASONS.map(([k]) => k).filter((k) => k === btn.dataset.season || e.seasons.includes(k));
          break;
        case "view":
          this._view = btn.dataset.view;
          this._confirmDel = null;
          break;
        case "pnew": {
          const used = new Set((this._data.presence_rules || []).map((x) => x.entity));
          const free = this._climates().find((c) => !used.has(c.id));
          this._pedit = { entity: free?.id || "", sensors: [], delay: 15, mode: "outside", windows: [], enabled: true };
          break;
        }
        case "pedit": {
          const r = clone((this._data.presence_rules || []).find((x) => x.entity === btn.dataset.ent));
          r._orig = r.entity;
          this._pedit = r;
          break;
        }
        case "pdel":
          if (this._confirmDel !== "p:" + btn.dataset.ent) {
            this._confirmDel = "p:" + btn.dataset.ent;
            break;
          }
          this._confirmDel = null;
          await this._ws("climate_planner/presence/delete", { entity: btn.dataset.ent });
          this._toast("Regla eliminada");
          break;
        case "psensor": {
          const p = this._pedit;
          const id = btn.dataset.sensor;
          p.sensors = p.sensors.includes(id) ? p.sensors.filter((x) => x !== id) : [...p.sensors, id];
          break;
        }
        case "wadd":
          this._pedit.windows.push({ days: [0, 1, 2, 3, 4, 5, 6], start: "09:00", end: "14:00" });
          break;
        case "wdel":
          this._pedit.windows.splice(i, 1);
          break;
        case "wday": {
          const w = this._pedit.windows[i];
          const d = Number(btn.dataset.day);
          w.days = w.days.includes(d) ? w.days.filter((x) => x !== d) : [...w.days, d].sort();
          break;
        }
        case "wpreset":
          this._pedit.windows[i].days = { wk: [0, 1, 2, 3, 4], we: [5, 6], all: [0, 1, 2, 3, 4, 5, 6] }[btn.dataset.p];
          break;
        case "pcancel":
          this._pedit = null;
          break;
        case "psave":
          if (!(await this._savePresence())) return;
          break;
        case "slot-del":
          e.slots.splice(i, 1);
          break;
        case "day": {
          const d = Number(btn.dataset.day);
          const s = e.slots[i];
          s.days = s.days.includes(d) ? s.days.filter((x) => x !== d) : [...s.days, d].sort();
          break;
        }
        case "preset":
          e.slots[i].days = { wk: [0, 1, 2, 3, 4], we: [5, 6], all: [0, 1, 2, 3, 4, 5, 6] }[btn.dataset.p];
          break;
        case "date-add":
          this._dates = this._dates || clone(this._data.season_dates);
          this._dates.push({ season: "transition", start: "01-01" });
          break;
        case "date-del":
          this._dates = this._dates || clone(this._data.season_dates);
          this._dates.splice(i, 1);
          break;
        case "date-cancel":
          this._dates = null;
          break;
        case "date-save": {
          if (!this._dates.length) return this._toast("Deja al menos un cambio de temporada", true);
          const sorted = [...this._dates].sort((x, y) => (x.start < y.start ? -1 : 1));
          await this._ws("climate_planner/settings", { season_dates: sorted });
          this._dates = null;
          this._tab = this._data.season;
          this._toast("Fechas guardadas");
          break;
        }
        default:
          return;
      }
    } catch (_err) {
      return; // toast already shown
    }
    this._render();
  }

  async _save() {
    const e = this._edit;
    if (!e.name.trim()) return this._toast("Ponle un nombre al horario", true), false;
    if (!e.entities.length) return this._toast("Elige al menos un equipo", true), false;
    if (!e.slots.length) return this._toast("Añade al menos una franja", true), false;
    if (!e.seasons.length) return this._toast("Elige al menos una temporada", true), false;
    for (const s of e.slots) {
      if (!s.days.length) return this._toast("Cada franja necesita al menos un día", true), false;
      if (!s.start || (s.end && hm(s.start) % 1440 === hm(s.end) % 1440))
        return this._toast("Revisa las horas: inicio y fin no pueden coincidir", true), false;
    }
    const payload = clone(e);
    payload.name = payload.name.trim();
    payload.slots.forEach((s) => {
      s.temperature = s.temperature === "" || s.temperature == null ? null : Number(s.temperature);
      s.fan_mode = s.fan_mode || null;
      s.end = s.end || null;
    });
    try {
      await this._ws("climate_planner/schedule/save", { schedule: payload });
    } catch (_err) {
      return false;
    }
    if (!e.seasons.includes(this._tab)) this._tab = e.seasons[0];
    this._edit = null;
    this._toast("Horario guardado");
    return true;
  }

  async _onChange(ev) {
    const t = ev.target;
    if (t.dataset.setting) {
      const key = t.dataset.setting;
      const value = t.type === "checkbox" ? t.checked : t.value;
      try {
        await this._ws("climate_planner/settings", { [key]: value });
        if (key === "season" || key === "auto_season") this._tab = this._data.season;
      } catch (_e) { /* toast shown */ }
      this._render();
      return;
    }
    if (t.dataset.toggle) {
      const s = clone(this._schedule(t.dataset.toggle));
      s.enabled = t.checked;
      try {
        await this._ws("climate_planner/schedule/save", { schedule: s });
      } catch (_e) { /* toast shown */ }
      this._render();
      return;
    }
    if (t.dataset.date) {
      this._dates = this._dates || clone(this._data.season_dates);
      const i = Number(t.dataset.i);
      const entry = this._dates[i];
      let [m, d] = entry.start.split("-").map(Number);
      if (t.dataset.date === "season") entry.season = t.value;
      if (t.dataset.date === "day") d = Number(t.value);
      if (t.dataset.date === "month") m = Number(t.value);
      const maxDay = new Date(2024, m, 0).getDate();
      d = Math.min(d, maxDay);
      entry.start = `${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      this._render();
      return;
    }
    if (t.dataset.ptoggle) {
      const r = clone((this._data.presence_rules || []).find((x) => x.entity === t.dataset.ptoggle));
      r.enabled = t.checked;
      try {
        await this._ws("climate_planner/presence/save", { rule: r });
      } catch (_e) { /* toast shown */ }
      this._render();
      return;
    }
    if (t.dataset.p && this._pedit) {
      const k = t.dataset.p;
      if (k === "all") this._pAll = t.checked;
      else if (k === "enabled") this._pedit.enabled = t.checked;
      else if (k === "delay") this._pedit.delay = t.value;
      else this._pedit[k] = t.value;
      if (k !== "delay") this._render();
      return;
    }
    if (t.dataset.w && this._pedit) {
      this._pedit.windows[Number(t.dataset.i)][t.dataset.w] = t.value;
      return;
    }
    if (t.dataset.point !== undefined && this._edit) {
      const s = this._edit.slots[Number(t.dataset.point)];
      if (t.checked) s.end = null;
      else s.end = String((Math.floor(hm(s.start) / 60) + 1) % 24).padStart(2, "0") + ":00";
      this._render();
      return;
    }
    if (t.dataset.e && this._edit) {
      this._edit[t.dataset.e] = t.type === "checkbox" ? t.checked : t.value;
      return;
    }
    if (t.dataset.slot === "hvac_mode" && this._edit) {
      this._edit.slots[Number(t.dataset.i)].hvac_mode = t.value;
      this._render();
      return;
    }
    this._onInput(ev);
  }

  _onInput(ev) {
    const t = ev.target;
    if (this._pedit) {
      if (t.dataset.p === "delay") this._pedit.delay = t.value;
      if (t.dataset.w) this._pedit.windows[Number(t.dataset.i)][t.dataset.w] = t.value;
      return;
    }
    if (!this._edit) return;
    if (t.dataset.e === "name") {
      this._edit.name = t.value;
      return;
    }
    if (t.dataset.slot) {
      const s = this._edit.slots[Number(t.dataset.i)];
      s[t.dataset.slot] = t.value;
      this._refreshPreview();
    }
  }
}

// The tag carries the version (?v=x.y.z in the module URL) so that a newer
// panel loads even if an older one is still defined in an open app session.
let TAG = "climate-planner-panel";
try {
  const v = new URL(import.meta.url).searchParams.get("v");
  if (v) TAG += "-" + v.replace(/[^a-z0-9]/gi, "-");
} catch (_e) { /* keep default tag */ }
if (!customElements.get(TAG)) customElements.define(TAG, ClimatePlannerPanel);
