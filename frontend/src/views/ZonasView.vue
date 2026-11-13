<template>
  <div class="zones-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Organización territorial</p>
        <h2>Zonas</h2>
        <p class="page-caption">Administra distribuciones, divisiones y la ubicación de cada terminal.</p>
      </div>
      <div class="topbar-actions">
        <span class="sync-state" :class="{ syncing: loading, failed: loadError }">
          <i></i>{{ loadError ? 'Sin conexión' : loading ? 'Sincronizando' : `Actualizado ${lastSync}` }}
        </span>
        <button class="primary-btn" type="button" :disabled="loading" @click="loadData">Actualizar</button>
      </div>
    </header>

    <p v-if="loadError" class="error-banner" role="alert">{{ loadError }}</p>
    <p v-if="actionSuccess" class="success-banner" role="status">{{ actionSuccess }}</p>
    <p v-if="actionError" class="error-banner" role="alert">{{ actionError }}</p>

    <section class="hierarchy-grid" aria-label="Catálogo de ubicaciones">
      <article class="hierarchy-card">
        <div class="card-heading">
          <div><span class="step-number">1</span><div><h3>Distribuciones</h3><small>{{ activeProcesses.length }} activas</small></div></div>
          <button v-if="!auth.isReadOnly" class="add-btn" type="button" @click="openCreate('proceso')">＋ Agregar</button>
        </div>
        <div v-if="!processes.length" class="empty-state">Agrega la primera distribución para comenzar.</div>
        <div
          v-for="process in processes"
          :key="process.id"
          class="catalog-row"
          :class="{ selected: selectedProcess?.id === process.id, inactive: !process.activo }"
        >
          <button class="catalog-select" type="button" @click="selectProcess(process)">
            <span class="catalog-copy"><strong>{{ process.nombre }}</strong><small>{{ process.activo ? 'Activa' : 'Inactiva' }}</small></span>
            <span class="chevron">›</span>
          </button>
          <span class="row-tools">
            <button v-if="!auth.isReadOnly" type="button" title="Editar distribución" @click="openEdit('proceso', process)">✎</button>
            <button v-if="!auth.isReadOnly" type="button" :title="process.activo ? 'Desactivar' : 'Activar'" @click="toggleActive('proceso', process)">{{ process.activo ? '●' : '○' }}</button>
            <button v-if="!auth.isReadOnly" class="delete-item" type="button" title="Eliminar distribución" @click="deleteCatalog('proceso', process)">×</button>
          </span>
        </div>
      </article>

      <article class="hierarchy-card" :class="{ 'waiting-card': !selectedProcess }">
        <div class="card-heading">
          <div><span class="step-number">2</span><div><h3>Divisiones</h3><small>{{ selectedProcess?.nombre || 'Elige una distribución' }}</small></div></div>
          <button
            v-if="!auth.isReadOnly"
            class="add-btn"
            type="button"
            :disabled="!selectedProcess || !selectedProcess.activo"
            @click="openCreate('subproceso')"
          >＋ Agregar</button>
        </div>
        <div v-if="!selectedProcess" class="empty-state">Selecciona una distribución para ver sus divisiones.</div>
        <div v-else-if="!visibleSubprocesos.length" class="empty-state">Todavía no hay divisiones en esta distribución.</div>
        <div
          v-for="division in visibleSubprocesos"
          :key="division.id"
          class="catalog-row"
          :class="{ selected: selectedSubproceso?.id === division.id, inactive: !division.activo }"
        >
          <button class="catalog-select" type="button" @click="selectSubproceso(division)">
            <span class="catalog-copy"><strong>{{ division.nombre }}</strong><small>{{ division.activo ? 'Activa' : 'Inactiva' }}</small></span>
            <span class="chevron">›</span>
          </button>
          <span class="row-tools">
            <button v-if="!auth.isReadOnly" type="button" title="Editar división" @click="openEdit('subproceso', division)">✎</button>
            <button v-if="!auth.isReadOnly" type="button" :title="division.activo ? 'Desactivar' : 'Activar'" @click="toggleActive('subproceso', division)">{{ division.activo ? '●' : '○' }}</button>
            <button v-if="!auth.isReadOnly" class="delete-item" type="button" title="Eliminar división" @click="deleteCatalog('subproceso', division)">×</button>
          </span>
        </div>
      </article>

      <article class="hierarchy-card" :class="{ 'waiting-card': !selectedSubproceso }">
        <div class="card-heading">
          <div><span class="step-number">3</span><div><h3>Zonas</h3><small>{{ selectedSubproceso?.nombre || 'Elige una división' }}</small></div></div>
          <button
            v-if="!auth.isReadOnly"
            class="add-btn"
            type="button"
            :disabled="!selectedSubproceso || !selectedSubproceso.activo"
            @click="openCreate('area')"
          >＋ Agregar</button>
        </div>
        <div v-if="!selectedSubproceso" class="empty-state">Selecciona una división para ver sus zonas.</div>
        <div v-else-if="!visibleAreas.length" class="empty-state">Todavía no hay zonas en esta división.</div>
        <div
          v-for="area in visibleAreas"
          :key="area.id"
          class="catalog-row"
          :class="{ selected: selectedArea?.id === area.id, inactive: !area.activo }"
        >
          <button class="catalog-select" type="button" @click="selectArea(area)">
            <span class="catalog-copy"><strong>{{ area.nombre }}</strong><small>{{ deviceCount(area.id) }} terminales · {{ area.activo ? 'Activa' : 'Inactiva' }}</small></span>
            <span class="chevron">›</span>
          </button>
          <span class="row-tools">
            <button v-if="!auth.isReadOnly" type="button" title="Editar zona" @click="openEdit('area', area)">✎</button>
            <button v-if="!auth.isReadOnly" type="button" :title="area.activo ? 'Desactivar' : 'Activar'" @click="toggleActive('area', area)">{{ area.activo ? '●' : '○' }}</button>
            <button v-if="!auth.isReadOnly" class="delete-item" type="button" title="Eliminar zona" @click="deleteCatalog('area', area)">×</button>
          </span>
        </div>
      </article>
    </section>

    <section class="devices-panel">
      <div class="devices-heading">
        <div>
          <p class="eyebrow">Asignación de terminales</p>
          <h3>{{ selectedArea ? `Terminales en ${selectedArea.nombre}` : 'Selecciona una zona' }}</h3>
          <p v-if="selectedArea" class="panel-caption">
            {{ selectedProcess?.nombre }} <span>›</span> {{ selectedSubproceso?.nombre }} <span>›</span> {{ selectedArea.nombre }}
          </p>
          <p v-else class="panel-caption">Elige una zona arriba para consultar o asignar terminales.</p>
        </div>
        <button
          v-if="selectedArea && !auth.isReadOnly"
          class="primary-btn"
          type="button"
          :disabled="!selectedArea.activo || loading"
          @click="openAssignment"
        >＋ Asignar terminales</button>
      </div>

      <div v-if="selectedArea && currentDevices.length" class="device-list">
        <div v-for="device in currentDevices" :key="device.id" class="device-row">
          <div class="device-avatar">▣</div>
          <div class="device-copy">
            <strong>{{ device.modelo || device.device_uuid || `Terminal ${device.id}` }}</strong>
            <small>{{ device.fabricante || 'Fabricante no disponible' }} · {{ device.device_uuid || 'Sin UUID' }}</small>
          </div>
          <span class="device-status" :class="device.en_linea ? 'online' : 'offline'">
            {{ device.en_linea ? '● En línea' : '● Fuera de línea' }}
          </span>
          <button
            v-if="!auth.isReadOnly"
            class="link-button"
            type="button"
            :disabled="assigningIds.includes(device.id)"
            @click="unassignDevice(device)"
          >Quitar de la zona</button>
        </div>
      </div>
      <div v-else-if="selectedArea" class="empty-state large-empty">
        No hay terminales asignadas a esta zona todavía.
        <button v-if="!auth.isReadOnly" class="text-button" type="button" @click="openAssignment">Asignar una terminal</button>
      </div>
    </section>

    <div v-if="editingCatalog" class="modal-backdrop" @click.self="closeCatalog">
      <form class="catalog-modal" @submit.prevent="saveCatalog">
        <div class="modal-heading">
          <div>
            <p class="eyebrow">{{ editingId ? 'Editar' : 'Agregar' }} {{ catalogLabel(editingCatalog) }}</p>
            <h3>{{ editingId ? 'Actualizar información' : `Nueva ${catalogLabel(editingCatalog).toLowerCase()}` }}</h3>
          </div>
          <button class="modal-close" type="button" aria-label="Cerrar" @click="closeCatalog">×</button>
        </div>
        <label>
          Nombre
          <input v-model.trim="catalogForm.nombre" maxlength="120" required autofocus />
        </label>
        <label>
          Descripción <span class="optional-label">(opcional)</span>
          <textarea v-model.trim="catalogForm.descripcion" rows="3" maxlength="2000"></textarea>
        </label>
        <p v-if="modalError" class="form-error" role="alert">{{ modalError }}</p>
        <div class="modal-actions">
          <button class="secondary-btn" type="button" :disabled="savingCatalog" @click="closeCatalog">Cancelar</button>
          <button class="primary-btn" type="submit" :disabled="savingCatalog">{{ savingCatalog ? 'Guardando…' : 'Guardar' }}</button>
        </div>
      </form>
    </div>

    <div v-if="assignmentModal && selectedArea" class="modal-backdrop" @click.self="closeAssignment">
      <section class="catalog-modal assignment-modal" aria-labelledby="assignment-title">
        <div class="modal-heading">
          <div>
            <p class="eyebrow">Asignar terminales</p>
            <h3 id="assignment-title">{{ selectedArea.nombre }}</h3>
          </div>
          <button class="modal-close" type="button" aria-label="Cerrar" @click="closeAssignment">×</button>
        </div>
        <input v-model="deviceQuery" class="device-search" placeholder="Buscar por modelo, fabricante o UUID" />
        <div class="assignment-list">
          <label v-for="device in assignableDevices" :key="device.id" class="assignment-row">
            <input v-model="selectedDeviceIds" type="checkbox" :value="device.id" />
            <span class="device-avatar">▣</span>
            <span class="device-copy">
              <strong>{{ device.modelo || device.device_uuid || `Terminal ${device.id}` }}</strong>
              <small>
                {{ device.fabricante || 'Fabricante no disponible' }} ·
                {{ device.area_id ? `Ubicación actual: ${device.distribucion_nombre} › ${device.division_nombre} › ${device.zona_nombre}` : 'Sin ubicación asignada' }}
              </small>
            </span>
          </label>
          <div v-if="!assignableDevices.length" class="empty-state">
            {{ deviceQuery ? 'No hay terminales que coincidan con la búsqueda.' : 'Todas las terminales ya están asignadas a esta zona.' }}
          </div>
        </div>
        <p v-if="modalError" class="form-error" role="alert">{{ modalError }}</p>
        <div class="modal-actions">
          <button class="secondary-btn" type="button" :disabled="savingAssignment" @click="closeAssignment">Cancelar</button>
          <button class="primary-btn" type="button" :disabled="savingAssignment || !selectedDeviceIds.length" @click="assignDevices">
            {{ savingAssignment ? 'Asignando…' : `Asignar ${selectedDeviceIds.length || ''}` }}
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import api from '../services/api';
import { useAuthStore } from '../stores/auth';

const auth = useAuthStore();
const processes = ref([]);
const subprocesos = ref([]);
const areas = ref([]);
const devices = ref([]);
const selectedProcess = ref(null);
const selectedSubproceso = ref(null);
const selectedArea = ref(null);
const loading = ref(false);
const loadError = ref('');
const actionError = ref('');
const actionSuccess = ref('');
const lastSync = ref('nunca');
const editingCatalog = ref('');
const editingId = ref(null);
const catalogForm = reactive({ nombre: '', descripcion: '' });
const modalError = ref('');
const savingCatalog = ref(false);
const assignmentModal = ref(false);
const deviceQuery = ref('');
const selectedDeviceIds = ref([]);
const assigningIds = ref([]);
const savingAssignment = ref(false);

const activeProcesses = computed(() => processes.value.filter((item) => item.activo));
const visibleSubprocesos = computed(() => selectedProcess.value
  ? subprocesos.value.filter((item) => item.proceso_id === selectedProcess.value.id)
  : []);
const visibleAreas = computed(() => selectedSubproceso.value
  ? areas.value.filter((item) => item.subproceso_id === selectedSubproceso.value.id)
  : []);
const currentDevices = computed(() => selectedArea.value
  ? devices.value.filter((item) => item.area_id === selectedArea.value.id)
  : []);
const assignableDevices = computed(() => {
  const search = deviceQuery.value.trim().toLowerCase();
  return devices.value.filter((device) => {
    if (device.area_id === selectedArea.value?.id) return false;
    return !search || `${device.modelo || ''} ${device.fabricante || ''} ${device.device_uuid || ''}`
      .toLowerCase()
      .includes(search);
  });
});

function unwrap(response) {
  if (Array.isArray(response.data)) return response.data;
  return response.data?.results || [];
}

async function loadData() {
  loading.value = true;
  loadError.value = '';
  actionError.value = '';
  actionSuccess.value = '';
  const selectedIds = {
    process: selectedProcess.value?.id,
    division: selectedSubproceso.value?.id,
    zone: selectedArea.value?.id,
  };
  try {
    const [processResponse, divisionResponse, zoneResponse, deviceResponse] = await Promise.all([
      api.get('/procesos/'),
      api.get('/subprocesos/'),
      api.get('/areas/'),
      api.get('/zonas/dispositivos/'),
    ]);
    processes.value = unwrap(processResponse);
    subprocesos.value = unwrap(divisionResponse);
    areas.value = unwrap(zoneResponse).filter((area) => area.subproceso_id !== null);
    devices.value = unwrap(deviceResponse);
    selectedProcess.value = processes.value.find((item) => item.id === selectedIds.process) || null;
    selectedSubproceso.value = subprocesos.value.find((item) =>
      item.id === selectedIds.division && item.proceso_id === selectedProcess.value?.id
    ) || null;
    selectedArea.value = areas.value.find((item) =>
      item.id === selectedIds.zone && item.subproceso_id === selectedSubproceso.value?.id
    ) || null;
    lastSync.value = new Date().toLocaleTimeString('es-MX', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  } catch (error) {
    console.error('Error cargando el catálogo de zonas:', error);
    loadError.value = error.response?.status === 401
      ? 'Tu sesión no está autenticada.'
      : 'No fue posible cargar el catálogo o las terminales.';
  } finally {
    loading.value = false;
  }
}

function selectProcess(process) {
  selectedProcess.value = process;
  selectedSubproceso.value = null;
  selectedArea.value = null;
  actionError.value = '';
  actionSuccess.value = '';
}

function selectSubproceso(division) {
  selectedSubproceso.value = division;
  selectedArea.value = null;
  actionError.value = '';
  actionSuccess.value = '';
}

function selectArea(area) {
  selectedArea.value = area;
  actionError.value = '';
  actionSuccess.value = '';
}

function openCreate(type) {
  editingCatalog.value = type;
  editingId.value = null;
  catalogForm.nombre = '';
  catalogForm.descripcion = '';
  modalError.value = '';
}

function openEdit(type, item) {
  editingCatalog.value = type;
  editingId.value = item.id;
  catalogForm.nombre = item.nombre;
  catalogForm.descripcion = item.descripcion || '';
  modalError.value = '';
}

function closeCatalog() {
  if (savingCatalog.value) return;
  editingCatalog.value = '';
  editingId.value = null;
  modalError.value = '';
}

function catalogLabel(type) {
  return { proceso: 'Distribución', subproceso: 'División', area: 'Zona' }[type] || '';
}

function catalogEndpoint(type) {
  return { proceso: '/procesos/', subproceso: '/subprocesos/', area: '/areas/' }[type];
}

async function saveCatalog() {
  if (!catalogForm.nombre.trim()) return;
  savingCatalog.value = true;
  modalError.value = '';
  try {
    const endpoint = catalogEndpoint(editingCatalog.value);
    const payload = {
      nombre: catalogForm.nombre.trim(),
      descripcion: catalogForm.descripcion.trim(),
    };
    if (editingCatalog.value === 'subproceso') payload.proceso_id = selectedProcess.value.id;
    if (editingCatalog.value === 'area') payload.subproceso_id = selectedSubproceso.value.id;
    const response = editingId.value
      ? await api.patch(`${endpoint}${editingId.value}/`, payload)
      : await api.post(endpoint, payload);
    const createdId = response.data.id;
    const type = editingCatalog.value;
    const savedName = payload.nombre;
    closeCatalog();
    await loadData();
    if (type === 'proceso') selectProcess(processes.value.find((item) => item.id === createdId));
    if (type === 'subproceso') selectSubproceso(subprocesos.value.find((item) => item.id === createdId));
    if (type === 'area') selectArea(areas.value.find((item) => item.id === createdId));
    actionSuccess.value = `${catalogLabel(type)} "${savedName}" guardada y visible en la lista.`;
  } catch (error) {
    console.error('Error guardando elemento del catálogo:', error.response?.data || error);
    modalError.value = error.response?.data?.nombre?.[0]
      || error.response?.data?.detail
      || 'No se pudo guardar. Revisa si ya existe un registro con ese nombre.';
  } finally {
    savingCatalog.value = false;
  }
}

async function toggleActive(type, item) {
  actionError.value = '';
  actionSuccess.value = '';
  const endpoint = catalogEndpoint(type);
  try {
    await api.patch(`${endpoint}${item.id}/`, { activo: !item.activo });
    await loadData();
    actionSuccess.value = `${catalogLabel(type)} "${item.nombre}" ${item.activo ? 'desactivada' : 'activada'}.`;
  } catch (error) {
    console.error('Error cambiando estado del catálogo:', error.response?.data || error);
    actionError.value = error.response?.data?.detail || 'No se pudo actualizar el estado.';
  }
}

async function deleteCatalog(type, item) {
  const label = catalogLabel(type).toLowerCase();
  if (!window.confirm(`¿Eliminar ${label} "${item.nombre}"? No se podrá recuperar.`)) return;

  actionError.value = '';
  actionSuccess.value = '';
  try {
    await api.delete(`${catalogEndpoint(type)}${item.id}/`);
    await loadData();
    actionSuccess.value = `${catalogLabel(type)} "${item.nombre}" eliminada.`;
  } catch (error) {
    console.error(`Error eliminando ${label}:`, error.response?.data || error);
    actionError.value = error.response?.data?.detail
      || `No se pudo eliminar ${label}. Elimina primero sus elementos o asignaciones dependientes.`;
  }
}

function openAssignment() {
  if (!selectedArea.value?.activo || auth.isReadOnly) return;
  deviceQuery.value = '';
  selectedDeviceIds.value = [];
  modalError.value = '';
  assignmentModal.value = true;
}

function closeAssignment() {
  if (savingAssignment.value) return;
  assignmentModal.value = false;
  modalError.value = '';
}

async function assignDevices() {
  if (!selectedArea.value || !selectedDeviceIds.value.length) return;
  savingAssignment.value = true;
  modalError.value = '';
  try {
    for (const deviceId of selectedDeviceIds.value) {
      await api.patch(`/zonas/dispositivos/${deviceId}/`, { area_id: selectedArea.value.id });
    }
    assignmentModal.value = false;
    selectedDeviceIds.value = [];
    await loadData();
  } catch (error) {
    console.error('Error asignando terminales a la zona:', error.response?.data || error);
    modalError.value = error.response?.data?.detail
      || 'No se pudieron asignar todas las terminales. Actualiza la lista y revisa sus ubicaciones.';
    await loadData();
  } finally {
    savingAssignment.value = false;
  }
}

async function unassignDevice(device) {
  assigningIds.value = [...assigningIds.value, device.id];
  actionError.value = '';
  try {
    await api.patch(`/zonas/dispositivos/${device.id}/`, { area_id: null });
    await loadData();
  } catch (error) {
    console.error('Error quitando la terminal de la zona:', error.response?.data || error);
    actionError.value = error.response?.data?.detail || 'No se pudo quitar la terminal de la zona.';
  } finally {
    assigningIds.value = assigningIds.value.filter((id) => id !== device.id);
  }
}

function deviceCount(areaId) {
  return devices.value.filter((device) => device.area_id === areaId).length;
}

onMounted(loadData);
</script>

<style scoped>
.zones-page { display: grid; gap: 18px; padding: 24px; border: 1px solid #DCE3EE; border-radius: 12px; background: linear-gradient(180deg, #F4F6FA, #EDF0F7); }
.page-header { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding-bottom: 16px; border-bottom: 1px solid #DCE3EE; }
.page-header h2 { margin: 0; color: #121A2B; font-size: 2rem; font-weight: 800; }
.eyebrow { margin: 0 0 6px; color: #1E9B48; font-size: .75rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
.page-caption,.panel-caption { margin: 5px 0 0; color: #5B6B82; font-size: .82rem; }
.topbar-actions { display: flex; align-items: center; gap: 12px; }
.sync-state { display: inline-flex; align-items: center; gap: 7px; color: #15803d; font-size: .78rem; font-weight: 700; white-space: nowrap; padding: 8px 10px; border: 1px solid #DCE3EE; border-radius: 7px; background: #F4F6FA; }
.sync-state i { width: 8px; height: 8px; border-radius: 50%; background: #22c55e; }
.sync-state.syncing i { background: #f59e0b; }.sync-state.failed { color: #dc2626; }.sync-state.failed i { background: #ef4444; }
.primary-btn,.secondary-btn { border: 0; border-radius: 7px; padding: 10px 14px; font-weight: 700; cursor: pointer; }
.primary-btn { color: #fff; background: #1E9B48; }.primary-btn:hover:not(:disabled) { background: #167A39; }.secondary-btn { color: #334155; background: #E8EDF5; }
button:disabled { cursor: not-allowed; opacity: .55; }
.hierarchy-grid { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 14px; align-items: stretch; }
.hierarchy-card,.devices-panel { min-width: 0; padding: 16px; border: 1px solid #DCE3EE; border-radius: 10px; background: #fff; box-shadow: 0 6px 18px rgba(0,67,49,.04); }
.waiting-card { background: #F8FAFC; }
.card-heading,.card-heading>div,.devices-heading { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.card-heading { min-height: 48px; margin-bottom: 10px; }
.card-heading>div { justify-content: flex-start; }
.step-number { display: grid; place-items: center; flex: 0 0 auto; width: 30px; height: 30px; border-radius: 9px; color: #167A39; background: #E6F6EC; font-size: .8rem; font-weight: 800; }
.card-heading h3,.devices-heading h3 { margin: 0; color: #121A2B; font-size: 1rem; }
.card-heading small { display: block; max-width: 180px; margin-top: 3px; overflow: hidden; color: #64748b; font-size: .7rem; text-overflow: ellipsis; white-space: nowrap; }
.add-btn { flex: 0 0 auto; padding: 8px 9px; border: 1px solid #BFE6CB; border-radius: 7px; color: #167A39; background: #F0FAF3; font-size: .72rem; font-weight: 800; cursor: pointer; }
.catalog-row { display: flex; width: 100%; align-items: center; gap: 8px; margin-top: 6px; padding: 6px 8px 6px 10px; border: 1px solid #E5EAF1; border-radius: 7px; color: #243247; background: #fff; }
.catalog-row:hover,.catalog-row.selected { border-color: #8BC99A; background: #F0FAF3; }.catalog-row.inactive { opacity: .58; }
.catalog-select { display: flex; min-width: 0; flex: 1; align-items: center; justify-content: space-between; gap: 8px; padding: 3px 0; border: 0; color: inherit; background: transparent; text-align: left; cursor: pointer; }
.catalog-copy,.device-copy { display: grid; min-width: 0; gap: 4px; }.catalog-copy strong,.device-copy strong { overflow: hidden; color: #172337; font-size: .83rem; text-overflow: ellipsis; white-space: nowrap; }.catalog-copy small,.device-copy small { overflow: hidden; color: #64748b; font-size: .7rem; text-overflow: ellipsis; white-space: nowrap; }
.row-tools { display: flex; align-items: center; gap: 3px; flex: 0 0 auto; }.row-tools button { width: 27px; height: 27px; padding: 0; border: 0; border-radius: 5px; color: #526179; background: transparent; cursor: pointer; }.row-tools button:hover { color: #167A39; background: #E6F6EC; }.row-tools .delete-item { color: #b42318; }.row-tools .delete-item:hover { color: #991b1b; background: #fee2e2; }.chevron { color: #94a3b8; font-size: 1.15rem; }
.empty-state { display: grid; min-height: 92px; place-content: center; gap: 8px; padding: 14px; color: #64748b; font-size: .78rem; text-align: center; }.large-empty { min-height: 130px; }
.devices-panel { padding: 18px; }.devices-heading { margin-bottom: 14px; }.devices-heading>div { min-width: 0; }.panel-caption span { padding: 0 5px; color: #94a3b8; }
.device-list { display: grid; gap: 8px; }.device-row { display: flex; min-width: 0; align-items: center; gap: 12px; padding: 10px 12px; border: 1px solid #E5EAF1; border-radius: 8px; background: #F8FAFC; }.device-avatar { display: grid; place-items: center; flex: 0 0 auto; width: 36px; height: 36px; border-radius: 9px; color: #167A39; background: #E6F6EC; font-size: 1.1rem; }.device-copy { flex: 1; }.device-status { flex: 0 0 auto; font-size: .7rem; font-weight: 800; white-space: nowrap; }.device-status.online { color: #15803d; }.device-status.offline { color: #64748b; }.link-button,.text-button { border: 0; color: #167A39; background: transparent; font-size: .74rem; font-weight: 800; cursor: pointer; }.text-button { justify-self: center; }
.error-banner,.form-error,.success-banner { margin: 0; padding: 10px 12px; border: 1px solid #fecaca; border-radius: 7px; color: #b42318; background: #fff0ee; font-size: .78rem; }.success-banner { border-color: #bbf7d0; color: #166534; background: #f0fdf4; }.form-error { margin-top: 12px; }
.modal-backdrop { position: fixed; z-index: 20; inset: 0; display: grid; place-items: center; overflow-y: auto; padding: 18px; background: rgba(15,23,42,.55); }
.catalog-modal { width: min(100%,480px); max-height: min(90vh,760px); overflow-y: auto; padding: 20px; border: 1px solid #DCE3EE; border-radius: 12px; background: #fff; box-shadow: 0 24px 70px rgba(15,23,42,.25); }.assignment-modal { width: min(100%,650px); }
.modal-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; margin-bottom: 18px; }.modal-heading h3 { margin: 0; color: #121A2B; }.modal-close { width: 34px; height: 34px; border: 0; border-radius: 7px; color: #475569; background: #F1F5F9; font-size: 1.35rem; cursor: pointer; }
.catalog-modal>label { display: grid; gap: 6px; margin: 14px 0; color: #334155; font-size: .78rem; font-weight: 700; }.catalog-modal input:not([type=checkbox]),.catalog-modal textarea { width: 100%; padding: 10px 11px; border: 1px solid #DCE3EE; border-radius: 7px; color: #172337; background: #F8FAFC; font: inherit; }.catalog-modal textarea { resize: vertical; }.optional-label { color: #94a3b8; font-weight: 400; }.modal-actions { display: flex; justify-content: flex-end; gap: 9px; margin-top: 16px; }.device-search { margin-bottom: 10px; }
.assignment-list { display: grid; max-height: 45vh; overflow-y: auto; gap: 6px; }.assignment-row { display: flex; align-items: center; gap: 10px; padding: 9px; border: 1px solid #E5EAF1; border-radius: 7px; cursor: pointer; }.assignment-row input { flex: 0 0 auto; accent-color: #1E9B48; }.assignment-row .device-copy { flex: 1; }
@media(max-width:1000px) { .hierarchy-grid { grid-template-columns: 1fr 1fr; }.hierarchy-card:last-child { grid-column: 1 / -1; } }
@media(max-width:680px) { .zones-page { padding: 15px 11px; }.page-header,.devices-heading { align-items: flex-start; flex-direction: column; }.hierarchy-grid { grid-template-columns: 1fr; }.hierarchy-card:last-child { grid-column: auto; }.topbar-actions { width: 100%; justify-content: space-between; }.device-row { flex-wrap: wrap; }.device-copy { min-width: calc(100% - 60px); }.device-status { margin-left: 48px; }.link-button { margin-left: auto; }.catalog-modal { padding: 16px; } }
</style>
