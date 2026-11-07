"use strict";

const byId = (id) => document.getElementById(id);
let authorization;

async function api(path, { method = "GET", data, admin = true, signal } = {}) {
  const headers = {};
  if (admin && authorization) headers.Authorization = authorization;
  if (data) headers["Content-Type"] = "application/json";
  const response = await fetch(path, {
    method,
    signal,
    headers,
    body: data ? JSON.stringify(data) : undefined,
    credentials: "omit",
    cache: "no-store",
  });
  if (response.status === 204) return;
  const result = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(result.detail)
      ? result.detail.map((item) => item.loc.at(-1) + " — " + item.msg).join(". ")
      : result.detail;
    throw new Error(detail || "La solicitud no se pudo completar.");
  }
  return result;
}

function submit(id, handler) {
  const form = byId(id);
  let current;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    current?.abort();
    const request = new AbortController();
    current = request;
    const button = form.querySelector("button");
    const status = form.querySelector("[role=status]");
    status.classList.remove("error");
    status.textContent = "";
    button.disabled = true;
    try {
      const message = await handler(Object.fromEntries(new FormData(form)), form, request.signal);
      if (current === request) status.textContent = message;
    } catch (error) {
      if (current !== request) return;
      status.classList.add("error");
      status.textContent = error.message;
    } finally {
      if (current === request) button.disabled = false;
    }
  });
}

function options(select, rows, label) {
  const selected = select.value;
  select.replaceChildren(new Option("Selecciona una opción", ""));
  for (const row of rows) select.add(new Option(label(row), row.id));
  if (rows.some((row) => String(row.id) === selected)) select.value = selected;
}

async function allOwners() {
  const rows = [];
  for (let skip = 0; ; skip += 100) {
    const page = await api("/personas?limit=100&skip=" + skip);
    rows.push(...page);
    if (page.length < 100) return rows;
  }
}

function actualizarClientes(types, people) {
  // Propietario es el nombre que usaba el panel antes de mostrar solo Cliente.
  const tiposCliente = ["cliente", "clientes", "propietario", "propietarios"]
    .flatMap((nombre) => types.filter((tipo) => tipo.descripcion?.trim().toLowerCase() === nombre));
  const tipoPreferido = tiposCliente[0];
  const formPersona = byId("persona");
  const selectorTipo = formPersona.elements.tipo_persona_id;
  options(selectorTipo, tipoPreferido ? [tipoPreferido] : [], () => "Cliente");
  if (tipoPreferido) selectorTipo.value = String(tipoPreferido.id);
  byId("tipo").hidden = Boolean(tipoPreferido);
  formPersona.hidden = !tipoPreferido;

  const ids = new Set(tiposCliente.map((type) => type.id));
  const clientes = people.filter((person) => ids.has(person.tipo_persona_id));
  options(byId("mascota").elements.personas_id, clientes,
    (person) => (person.nombre || "Cliente") + " · #" + person.id);
}

async function refreshAdmin() {
  const [types, people, pets] = await Promise.all([
    api("/tipos-persona"), allOwners(), api("/mascotas"),
  ]);
  actualizarClientes(types, people);
  for (const id of ["asignar", "contacto"]) {
    options(byId(id).elements.mascota_id, pets, (pet) => {
      const tag = pet.tag ? " · " + pet.tag : " · sin tag";
      return (pet.nombre || "Mascota") + " · #" + pet.id + tag;
    });
  }
}

submit("consulta", async ({ codigo }, form, signal) => {
  const ficha = byId("ficha");
  ficha.hidden = true;
  ficha.replaceChildren();
  const pet = await api("/tags/consulta?" + new URLSearchParams({ codigo }), { admin: false, signal });
  if (signal.aborted) return "";
  const fields = [["Mascota", pet.nombre], ["Especie", pet.especie], ["Raza", pet.raza]];
  if (pet.contacto) {
    fields.push(["Propietario", pet.contacto.nombre], ["Teléfono", pet.contacto.telefono]);
  }
  for (const [label, value] of fields) {
    if (!value) continue;
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = label;
    description.textContent = value;
    ficha.append(term, description);
  }
  ficha.hidden = !ficha.childElementCount;
  return "Ficha encontrada.";
});

const botonAdmin = byId("abrir-admin");
const panelAdmin = byId("panel-admin");

botonAdmin.addEventListener("click", () => {
  const abrir = panelAdmin.hidden;
  panelAdmin.hidden = !abrir;
  botonAdmin.setAttribute("aria-expanded", String(abrir));
  if (abrir) {
    const acceso = byId("acceso");
    const campoActivo = acceso.hidden ? byId("salir") : acceso.elements.clave;
    campoActivo.focus();
  }
});

submit("acceso", async ({ usuario, clave }, form) => {
  if (usuario.includes(":") || /[^\x20-\x7E]/.test(usuario + clave)) {
    throw new Error("Usa caracteres ASCII y evita los dos puntos en el usuario.");
  }
  authorization = "Basic " + btoa(usuario + ":" + clave);
  try {
    await refreshAdmin();
  } catch (error) {
    authorization = undefined;
    throw error;
  }
  form.reset();
  form.hidden = true;
  byId("admin").hidden = false;
  if (!panelAdmin.hidden) byId("salir").focus();
  return "";
});

byId("salir").addEventListener("click", () => {
  // Recargar elimina credenciales y datos privados de la página.
  window.location.reload();
});

function create(id, path, prepare, message) {
  submit(id, async (data, form) => {
    await api(path, { method: "POST", data: prepare(data) });
    form.reset();
    try {
      await refreshAdmin();
    } catch (error) {
      return message + " No se pudo actualizar la lista. Vuelve a entrar para verla.";
    }
    return message;
  });
}

create("tipo", "/tipos-persona", () => ({ descripcion: "Cliente" }), "Tipo Cliente habilitado.");
create("persona", "/personas", (data) => ({
  ...data, tipo_persona_id: Number(data.tipo_persona_id),
}), "Cliente guardado.");
create("mascota", "/mascotas", (data) => ({
  ...data,
  personas_id: Number(data.personas_id),
  fecha_nacimiento: data.fecha_nacimiento || null,
  tag: data.tag || null,
  compartir_contacto: data.compartir_contacto === "on",
}), "Mascota guardada.");

submit("asignar", async ({ mascota_id, tag }, form) => {
  const pet = await api("/mascotas/" + mascota_id + "/tag", { method: "PUT", data: { tag } });
  form.elements.tag.value = "";
  try {
    await refreshAdmin();
  } catch (error) {
    return "Tag guardado. No se pudo actualizar la lista.";
  }
  return "Tag asignado · " + pet.tag;
});

submit("contacto", async ({ mascota_id, compartir }) => {
  await api("/mascotas/" + mascota_id + "/contacto-publico?" + new URLSearchParams({ compartir }), { method: "PUT" });
  return compartir === "true" ? "Contacto visible en la ficha." : "Contacto oculto en la ficha.";
});

if ("serial" in navigator) {
  byId("lector").hidden = false;
  const button = byId("conectar");
  const status = byId("estado-lector");
  let reader;

  button.addEventListener("click", async () => {
    if (reader) {
      button.disabled = true;
      await reader.cancel().catch(() => {});
      return;
    }

    button.disabled = true;
    status.classList.remove("error");
    let port;
    let opened = false;
    try {
      port = await navigator.serial.requestPort();
      await port.open({ baudRate: 9600 });
      opened = true;
      reader = port.readable.getReader();
      button.textContent = "Desconectar lector USB";
      button.disabled = false;
      status.textContent = "Lector conectado. Acerca un tag.";

      const decoder = new TextDecoder();
      let pending = "";
      const form = byId("consulta");
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const lines = (pending + decoder.decode(value, { stream: true })).split("\n");
        pending = lines.pop();
        if (pending.length > 230) pending = "";
        for (const line of lines) {
          if (!/^UID de la tarjeta:\s+[\da-f]{2}(?: [\da-f]{2}){3,9}\s*$/i.test(line)) continue;
          form.elements.codigo.value = line.trim();
          form.requestSubmit();
        }
      }
      status.textContent = "Lector desconectado.";
    } catch (error) {
      status.classList.add("error");
      status.textContent = error.name === "NotFoundError"
        ? "Selecciona el puerto del lector para conectarlo."
        : "No se pudo leer el puerto. Revisa el cable y cierra el monitor serie.";
    } finally {
      if (reader) reader.releaseLock();
      reader = undefined;
      if (opened) await port.close().catch(() => {});
      button.textContent = "Conectar lector USB";
      button.disabled = false;
    }
  });
}
