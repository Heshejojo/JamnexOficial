<template>
  <div class="crud-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Inventario de activos</p>
        <h2>Dispositivos</h2>
        <p class="page-caption">Consulta el estado y la información técnica de los equipos registrados.</p>
      </div>
      <div class="topbar-actions">
        <span class="sync-state" :class="{ syncing: loading, failed: loadError }">
          <i></i>{{ loadError ? 'Sin conexión' : loading ? 'Sincronizando' : `Actualizado ${lastSync}` }}
        </span>
        <button class="primary-btn" :disabled="loading" @click="loadData">Actualizar</button>
      </div>
    </header>

    <div class="device-layout">
      <section class="panel inventory-panel">
        <div class="panel-topline">
          <div><span class="device-section-icon">▣</span><div><p class="eyebrow">Equipos registrados</p><h3>Listado de dispositivos</h3></div></div>
          <span class="device-count">{{ filteredItems.length }}</span>
        </div>

        <div class="search-box">
          <input v-model="query" placeholder="Buscar modelo, UUID o número de serie" />
        </div>

        <div v-if="filteredItems.length" class="list">
          <div v-for="item in filteredItems" :key="item.id" class="item-row" :class="{ active: selectedDevice && selectedDevice.id === item.id }">
            <div class="item-info">
              <strong>{{ item.modelo || item.device_uuid }}</strong>
              <small>{{ item.fabricante || 'Sin info' }} · {{ item.serial || 'Sin número de serie' }}</small>
              <small
                class="sim-report-status"
                :class="{ missing: item.simCount === 0, unknown: item.simCount === null, stale: isReportStale(item) }"
              >
                {{ getSimReportText(item.simCount, item) }}
              </small>
              <small v-if="hasManySimChanges(item)" class="sim-churn">⚠ {{ item.sims_distintas_30d }} SIMs distintas en 30 días</small>
            </div>
            <div class="row-actions">
              <span class="status-badge" :class="item.en_linea ? 'active' : 'inactive'">
                {{ item.en_linea ? '● Activo' : '● Inactivo' }}
              </span>
              <button class="detail-btn" @click="selectDetail(item)">Ver detalles</button>
              <button class="revoke-btn" @click="deleteDevice(item)">Eliminar</button>
            </div>
          </div>
        </div>
        <div v-else-if="loadError" class="empty-card error-card">
          {{ loadError }}
        </div>
        <div v-else class="empty-card">
          Los dispositivos aparecerán aquí cuando se conecten desde la app.
        </div>
      </section>

      <aside class="panel detail-panel" :class="{ empty: !selectedDevice }">
        <template v-if="selectedDevice">
          <div class="panel-header">
            <div class="device-title-wrap">
              <span class="detail-heading-icon">▣</span>
              <p class="eyebrow">Ficha técnica</p>
              <h3>{{ selectedDevice.modelo || selectedDevice.device_uuid }}</h3>
            </div>
            <div class="header-actions">
              <span class="live-status" :class="selectedDevice.en_linea ? 'active' : 'inactive'">
                {{ selectedDevice.en_linea ? 'En línea' : 'Fuera de línea' }}
              </span>
              <button v-if="selectedDevice" class="secondary-btn" type="button" @click="startEdit">✎ Editar</button>
              <button class="secondary-btn" type="button" @click="selectedDevice = null">Cerrar</button>
            </div>
          </div>

          <div
            v-if="selectedDevice.simCount === 0 && isReportStale(selectedDevice)"
            class="sim-report-alert"
            role="status"
          >
            <strong>Este dispositivo no ha enviado datos de ninguna SIM</strong>
            <span>No se detecta ninguna SIM desde hace {{ timeAgo(selectedDevice.sims_reported_at) }}. Puede no tener una SIM instalada o la app no pudo leerla.</span>
          </div>
          <div
            v-else-if="selectedDevice.simCount === null"
            class="sim-report-alert unavailable"
            role="status"
          >
            <strong>Este móvil aún no ha reportado sus SIM</strong>
            <span>La app debe sincronizarse para confirmar si tiene una SIM instalada.</span>
          </div>
          <div v-else-if="selectedDevice.simCount >= 2" class="sim-report-ok" role="status">
            <strong>Atención: se recibieron datos de {{ selectedDevice.simCount }} SIMs</strong>
            <span>{{ selectedDevice.simCount }} líneas están registradas en este dispositivo.</span>
          </div>
          <div v-if="hasManySimChanges(selectedDevice)" class="sim-report-alert" role="status">
            <strong>Este dispositivo ha cambiado de SIM varias veces</strong>
            <span>Han pasado {{ selectedDevice.sims_distintas_30d }} SIMs distintas por este equipo en los últimos 30 días. Revisa si se están intercambiando SIMs entre equipos.</span>
          </div>
          <div
            v-if="selectedDevice.simCount !== null && selectedDevice.simCount !== 0 && isReportStale(selectedDevice)"
            class="sim-report-alert unavailable"
            role="status"
          >
            <strong>El reporte de SIM está desactualizado</strong>
            <span>El último reporte fue {{ timeAgo(selectedDevice.sims_reported_at) }}. La app puede estar cerrada o sin conexión.</span>
          </div>

          <div class="device-summary">
            <div class="device-badge">
              <span class="device-icon">▣</span>
              <div>
                <small>Equipo</small>
                <strong>{{ selectedDevice.fabricante || 'Sin fabricante' }}</strong>
              </div>
            </div>

            <div class="summary-grid">
              <div class="summary-card battery">
                <span class="summary-icon">◈</span>
                <span class="metric-kicker">Batería</span>
                <strong>{{ getBatteryText(selectedDevice.id) }}</strong>
              </div>
              <div class="summary-card ram">
                <span class="summary-icon">▤</span>
                <span class="metric-kicker">RAM</span>
                <strong>{{ getRamText(selectedDevice.id) }}</strong>
              </div>
              <div class="summary-card storage">
                <span class="summary-icon">●</span>
                <span class="metric-kicker">Espacio libre</span>
                <strong>{{ getStorageText(selectedDevice.id) }}</strong>
              </div>
              <div class="summary-card network">
                <span class="summary-icon">⌁</span>
                <span class="metric-kicker">Conexión</span>
                <strong>{{ getNetworkText(selectedDevice.id) }}</strong>
              </div>
            </div>
          </div>

          <div class="detail-grid">
            <div class="detail-item"><span class="detail-icon">♧</span><span>Fabricante</span><strong>{{ selectedDevice.fabricante || 'No disponible' }}</strong></div>
            <div class="detail-item"><span class="detail-icon">♟</span><span>Android</span><strong>{{ selectedDevice.version_android || 'No disponible' }}</strong></div>
            <div class="detail-item"><span class="detail-icon">&lt;/&gt;</span><span>SDK</span><strong>{{ selectedDevice.android_sdk || 'No disponible' }}</strong></div>
            <div class="detail-item"><span class="detail-icon">▥</span><span>Número de serie</span><strong>{{ selectedDevice.serial || 'Restringido / no disponible' }}</strong></div>
            <div class="detail-item"><span class="detail-icon">▯</span><span>IMEI 1</span><strong>{{ selectedDevice.imei_1 || 'Restringido / no disponible' }}</strong></div>
            <div class="detail-item status-detail"><span class="detail-icon">✓</span><span>Estado</span><strong :class="selectedDevice.en_linea ? 'active-text' : 'inactive-text'">{{ selectedDevice.en_linea ? 'Activo' : 'Inactivo' }}</strong></div>
            <div class="detail-item uuid-detail"><span class="detail-icon">◎</span><span>UUID</span><strong class="uuid">{{ selectedDevice.device_uuid || 'No disponible' }}</strong></div>
          </div>

        </template>

        <div v-else class="empty-detail">
          <h4>Selecciona un dispositivo</h4>
          <p>El detalle técnico aparecerá aquí con batería, RAM, almacenamiento y conexión.</p>
        </div>
      </aside>
    </div>

    <div v-if="editingDevice" class="modal-backdrop" @click.self="editingDevice = false">
      <form class="edit-modal" @submit.prevent="saveEdit">
        <div class="modal-heading">
          <div><p class="eyebrow">Editar dispositivo</p><h3>{{ editForm.modelo || editForm.device_uuid || 'Dispositivo' }}</h3></div>
          <button type="button" class="modal-close" aria-label="Cerrar" @click="editingDevice = false">×</button>
        </div>

        <label>IMEI 1<input v-model="editForm.imei_1" type="text" /></label>
        <label>Número de serie<input v-model="editForm.serial" type="text" /></label>

        <div class="modal-actions">
          <button type="button" class="secondary-btn" @click="editingDevice = false">Cancelar</button>
          <button type="submit" class="primary-btn" :disabled="savingDeviceEdit">{{ savingDeviceEdit ? 'Guardando...' : 'Guardar cambios' }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, onActivated, onBeforeUnmount, onDeactivated, reactive, ref } from 'vue';
import api from '../services/api';

defineOptions({ name: 'DispositivosView' });

const items = ref([]);
const selectedDevice = ref(null);
const query = ref('');
const deviceDetails = ref({});
const loadError = ref('');
const loading = ref(false);
const lastSync = ref('nunca');
const editingDevice = ref(false);
const savingDeviceEdit = ref(false);
const editForm = reactive({
  serial: '',
  imei_1: '',
});
const filteredItems = computed(() => 
  items.value.filter((item) => 
    `${item.device_uuid} ${item.fabricante} ${item.modelo} ${item.serial}`.toLowerCase().includes(query.value.toLowerCase())
  )
);

function formatDate(dateString) {
  if (!dateString) return 'Sin contacto';
  const date = new Date(dateString);
  return date.toLocaleString('es-ES');
}

function formatMegabytes(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'No disponible';
  const number = Number(value);
  if (number >= 1024) return `${(number / 1024).toFixed(1)} GB`;
  return `${number.toFixed(1)} MB`;
}

function formatLastUsed(value) {
  if (!value) return 'Sin registro';
  const lastUsed = new Date(value);
  const diffMinutes = Math.max(0, Math.round((Date.now() - lastUsed.getTime()) / 60000));
  if (diffMinutes < 60) return `Última vez: hace ${diffMinutes} min`;
  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) return `Última vez: hace ${diffHours} h`;
  const diffDays = Math.round(diffHours / 24);
  return `Última vez: hace ${diffDays} d`;
}

function formatDuration(minutes) {
  const total = Number(minutes || 0);
  if (!total) return '0 min';
  if (total >= 60) return `${(total / 60).toFixed(1)} h`;
  return `${Math.round(total)} min`;
}

function formatBatteryState(state) {
  const normalized = String(state || '').trim().toUpperCase();

  switch (normalized) {
    case 'CARGANDO':
      return 'Cargando';
    case 'DESCARGANDO':
      return 'No cargando';
    case 'CARGADA':
      return 'Carga completa';
    case 'DESCONOCIDO':
    case 'DESCONOCIDA':
      return 'Sin datos';
    default:
      return state || 'Sin datos';
  }
}

function getBatteryText(deviceId) {
  const battery = deviceDetails.value[deviceId]?.battery;
  if (!battery) return 'Sin datos';
  return `${battery.porcentaje ?? 0}% · ${formatBatteryState(battery.estado)}`;
}

function getRamText(deviceId) {
  const ram = deviceDetails.value[deviceId]?.ram;
  if (!ram) return 'Sin datos';
  const used = ram.ram_usada ?? 0;
  const total = ram.ram_total ?? 0;
  return `${formatMegabytes(used)} / ${formatMegabytes(total)}`;
}

function getStorageText(deviceId) {
  const storage = deviceDetails.value[deviceId]?.storage;
  if (!storage) return 'Sin datos';
  return `${formatMegabytes(storage.disponible ?? 0)} libres`;
}

function getNetworkText(deviceId) {
  const network = deviceDetails.value[deviceId]?.network;
  if (!network) return 'Sin datos';
  return network.tipo_conexion === 'WIFI' ? 'Wi‑Fi' : network.tipo_conexion === 'DATOS_MOVILES' ? 'Datos móviles' : 'Sin conexión';
}

const REPORT_STALE_MS = 72 * 60 * 60 * 1000;
// Un celular de doble SIM puede tener 2 sin problema; desde 3 distintas en 30 días se marca.
const SIM_CHANGE_ALERT = 3;

function hasManySimChanges(device) {
  return Number(device?.sims_distintas_30d || 0) >= SIM_CHANGE_ALERT;
}

function timeAgo(value) {
  if (!value) return 'nunca';
  const minutes = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 60000));
  if (minutes < 1) return 'hace un momento';
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `hace ${hours} h`;
  return `hace ${Math.round(hours / 24)} d`;
}

function isReportStale(device) {
  if (!device?.sims_reported_at) return false;
  return Date.now() - new Date(device.sims_reported_at).getTime() >= REPORT_STALE_MS;
}

function getSimReportText(count, device) {
  if (count === null || count === undefined) return 'SIM: sin reporte';
  const when = device?.sims_reported_at ? ` · reportó ${timeAgo(device.sims_reported_at)}` : '';
  if (count === 0 && isReportStale(device)) return `Sin SIM detectada${when}`;
  if (count === 0) return `Reportó 0 SIMs${when}`;
  return `${count} ${count === 1 ? 'SIM' : 'SIMs'}${when}`;
}

function getDeviceApps(deviceId) {
  const apps = deviceDetails.value[deviceId]?.apps || [];
  return Array.isArray(apps)
    ? [...apps].sort((a, b) => Number(b.duration_minutes || 0) - Number(a.duration_minutes || 0)).slice(0, 5)
    : [];
}

async function loadDeviceDetails(deviceId) {
  try {
    const [batteryRes, ramRes, storageRes, networkRes] = await Promise.all([
      api.get('/bateria/'),
      api.get('/ram/'),
      api.get('/almacenamiento/'),
      api.get('/redes/'),
    ]);

    const battery = [...(batteryRes.data || [])]
      .filter((entry) => Number(entry.dispositivo) === Number(deviceId))
      .sort((a, b) => new Date(b.fecha_hora) - new Date(a.fecha_hora))[0];

    const ram = [...(ramRes.data || [])]
      .filter((entry) => Number(entry.dispositivo) === Number(deviceId))
      .sort((a, b) => new Date(b.fecha_hora) - new Date(a.fecha_hora))[0];

    const storage = [...(storageRes.data || [])]
      .filter((entry) => Number(entry.dispositivo) === Number(deviceId))
      .sort((a, b) => new Date(b.fecha_hora) - new Date(a.fecha_hora))[0];

    const network = [...(networkRes.data || [])]
      .filter((entry) => Number(entry.dispositivo) === Number(deviceId))
      .sort((a, b) => new Date(b.fecha_hora) - new Date(a.fecha_hora))[0];

    const apps = [
      { name: 'WhatsApp', package_name: 'com.whatsapp', last_used: new Date(Date.now() - 12 * 60000).toISOString(), duration_minutes: 42 },
      { name: 'Google Maps', package_name: 'com.google.android.apps.maps', last_used: new Date(Date.now() - 38 * 60000).toISOString(), duration_minutes: 26 },
      { name: 'Chrome', package_name: 'com.android.chrome', last_used: new Date(Date.now() - 90 * 60000).toISOString(), duration_minutes: 18 },
      { name: 'Telegram', package_name: 'org.telegram.messenger', last_used: new Date(Date.now() - 3 * 60 * 60000).toISOString(), duration_minutes: 14 },
      { name: 'YouTube', package_name: 'com.google.android.youtube', last_used: new Date(Date.now() - 5 * 60 * 60000).toISOString(), duration_minutes: 9 },
    ];

    deviceDetails.value[deviceId] = { battery, ram, storage, network, apps };
  } catch (error) {
    console.error('Error cargando detalle del dispositivo:', error);
    deviceDetails.value[deviceId] = {};
  }
}

async function loadData() {
  loading.value = true;
  loadError.value = '';
  try {
    const devicesResponse = await api.get('/dispositivos/');
    const devices = Array.isArray(devicesResponse.data)
      ? devicesResponse.data
      : devicesResponse.data?.results || [];
    items.value = devices.map((device) => ({
      ...device,
      simCount: Number.isInteger(device.sim_count_reported)
        ? device.sim_count_reported
        : null,
    }));
    if (selectedDevice.value) {
      selectedDevice.value = items.value.find((item) => item.id === selectedDevice.value.id) || null;
    }
    lastSync.value = new Date().toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', hour12: true });
  } catch (error) {
    console.error(error);
    items.value = [];
    loadError.value = error.response?.status === 401
      ? 'Tu sesión no está autenticada. Inicia sesión nuevamente para ver los dispositivos.'
      : 'No fue posible cargar los dispositivos. Verifica que el backend esté activo.';
  } finally {
    loading.value = false;
  }
}

function startEdit() {
  if (!selectedDevice.value) return;

  Object.assign(editForm, {
    serial: selectedDevice.value.serial || '',
    imei_1: selectedDevice.value.imei_1 || '',
  });

  editingDevice.value = true;
}

async function saveEdit() {
  if (!selectedDevice.value) return;

  savingDeviceEdit.value = true;
  try {
    await api.patch(`/dispositivos/${selectedDevice.value.id}/`, {
      serial: editForm.serial,
      imei_1: editForm.imei_1,
    });
    editingDevice.value = false;
    await loadData();

    selectedDevice.value = items.value.find((item) => item.id === selectedDevice.value.id) || null;
    if (selectedDevice.value) {
      loadDeviceDetails(selectedDevice.value.id);
    }
  } catch (error) {
    console.error('Error al guardar el dispositivo:', error);
    window.alert('No se pudo guardar la información del dispositivo.');
  } finally {
    savingDeviceEdit.value = false;
  }
}

async function deleteDevice(item) {
  const nombre = item.modelo || item.device_uuid || 'este dispositivo';
  const confirmar = window.confirm(`¿Seguro que deseas eliminar ${nombre}?\n\nSe borrarán también sus registros de batería, RAM, almacenamiento, red y consumo. Las SIMs que tuvo se conservan, con su historial.\n\nEsta acción no se puede deshacer.`);

  if (!confirmar) return;

  try {
    await api.delete(`/dispositivos/${item.id}/`);
    if (selectedDevice.value?.id === item.id) {
      selectedDevice.value = null;
    }
    await loadData();
  } catch (error) {
    console.error('Error al eliminar el dispositivo:', error);
  }
}

function selectDetail(item) {
  selectedDevice.value = item;
  loadDeviceDetails(item.id);
}

let refreshTimer = null;

function activateView() {
  loadData();
  refreshTimer = setInterval(loadData, 30000);
}

function deactivateView() {
  if (!refreshTimer) return;
  clearInterval(refreshTimer);
  refreshTimer = null;
}

onActivated(activateView);
onDeactivated(deactivateView);
onBeforeUnmount(deactivateView);
</script>

<style scoped>
.crud-page {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.73rem;
  color: #64748b;
  margin: 0 0 8px;
}

h2 {
  margin: 0;
  font-size: clamp(1.6rem, 2vw, 2.1rem);
}

.primary-btn {
  border: 0;
  background: linear-gradient(135deg, #1E9B48, #34C98F);
  color: white;
  border-radius: 10px;
  padding: 11px 17px;
  font-size: 0.92rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.18);
  transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease;
}

.primary-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 18px rgba(30, 155, 72, 0.22);
  filter: brightness(1.02);
}

.secondary-btn {
  border: 1px solid #cbd5e1;
  background: white;
  color: #475569;
  border-radius: 10px;
  padding: 10px 15px;
  font-size: 0.9rem;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.secondary-btn:hover {
  transform: translateY(-1px);
  border-color: #b7c9de;
  box-shadow: 0 8px 16px rgba(15, 23, 42, 0.06);
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 30;
}

.edit-modal {
  width: min(100%, 520px);
  background: white;
  border: 1px solid #dbe5f0;
  border-radius: 16px;
  padding: 22px;
  box-shadow: 0 22px 60px rgba(15, 23, 42, 0.18);
  display: grid;
  gap: 14px;
}

.modal-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.modal-heading h3 {
  margin: 0;
}

.modal-close {
  border: 0;
  background: transparent;
  color: #475569;
  font-size: 1.5rem;
  line-height: 1;
  cursor: pointer;
}

.edit-modal label {
  display: grid;
  gap: 6px;
  color: #475569;
  font-size: 0.76rem;
  font-weight: 700;
}

.edit-modal input {
  width: 100%;
  padding: 10px 11px;
  border: 1px solid #d8e2ef;
  border-radius: 9px;
  background: #f8fafc;
  color: #0f172a;
}

.edit-modal input:focus {
  outline: none;
  border-color: #1E9B48;
  box-shadow: 0 0 0 0.18rem rgba(30, 155, 72, 0.12);
}

.edit-check {
  display: flex !important;
  align-items: center;
  gap: 8px !important;
  color: #0f172a !important;
}

.edit-check input {
  width: auto;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 4px;
}

.device-layout {
  display: grid;
  grid-template-columns: minmax(330px, 1fr) minmax(420px, 1.45fr);
  gap: 20px;
  align-items: start;
}

.panel {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 18px;
  padding: 18px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.03);
}

.inventory-panel {
  min-height: 600px;
}

.panel-topline {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.panel h3 {
  margin: 0;
  font-size: 1.12rem;
  color: #0f172a;
}

.search-box {
  margin-bottom: 14px;
}

.search-box input {
  width: 100%;
  padding: 10px 12px;
  border-radius: 11px;
  border: 1px solid #d8e2ef;
  font-size: 0.9rem;
  background: #f8fafc;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.item-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  background: linear-gradient(135deg, #f8fafc, #eef7ff);
  border: 1px solid rgba(148, 163, 184, 0.12);
  transition: all 0.2s ease;
}

.item-row:hover,
.item-row.active {
  background: linear-gradient(135deg, #eef8ff, #ebf5ff);
  border-color: rgba(37, 99, 235, 0.2);
  transform: translateY(-1px);
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-info strong {
  display: block;
  color: #0f172a;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-info small {
  display: block;
  color: #64748b;
  font-size: 0.8rem;
  margin-top: 4px;
}

.sim-report-status {
  color: #166534 !important;
  font-weight: 700;
}

.sim-report-status.missing {
  color: #b91c1c !important;
}

.sim-report-status.unknown {
  color: #92400e !important;
}

.sim-report-alert,
.sim-report-ok {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 0 0 16px;
  padding: 12px 14px;
  border: 1px solid #fecaca;
  border-radius: 10px;
  background: #fef2f2;
  color: #991b1b;
}

.sim-report-alert span {
  font-size: 0.85rem;
}

.sim-report-alert.unavailable {
  border-color: #fcd34d;
  background: #fffbeb;
  color: #92400e;
}

.sim-report-ok {
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-color: #bbf7d0;
  background: #f0fdf4;
  color: #166534;
}

.sim-report-ok span {
  font-size: 0.85rem;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-badge {
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  white-space: nowrap;
}

.status-badge.active {
  background: linear-gradient(135deg, #dcfce7, #bbf7d0);
  color: #166534;
}

.status-badge.inactive {
  background: linear-gradient(135deg, #fee2e2, #fecaca);
  color: #991b1b;
}

.detail-btn {
  border: 0;
  background: rgba(16, 185, 129, 0.12);
  color: #047857;
  border-radius: 8px;
  padding: 8px 12px;
  font-weight: 700;
  cursor: pointer;
  font-size: 0.8rem;
  transition: transform 0.18s ease, filter 0.18s ease;
}

.detail-btn:hover {
  transform: translateY(-1px);
  filter: brightness(1.02);
}

.revoke-btn {
  border: 0;
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
  border-radius: 8px;
  padding: 8px 12px;
  font-weight: 700;
  cursor: pointer;
  font-size: 0.8rem;
  transition: transform 0.18s ease, filter 0.18s ease;
}

.revoke-btn:hover {
  transform: translateY(-1px);
  filter: brightness(1.02);
}

.empty-card {
  border: 2px dashed #d8e2ef;
  background: #f8fafc;
  border-radius: 12px;
  padding: 34px 18px;
  text-align: center;
  color: #64748b;
  font-size: 0.92rem;
}

.detail-panel {
  background: linear-gradient(135deg, #f8fbff 0%, #f5f3ff 100%);
  min-height: 600px;
}

.detail-panel.empty {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f8fafc, #f4f7fb);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 18px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(37, 99, 235, 0.12);
}

.device-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.panel-header h3 {
  margin: 0;
  font-size: 1.38rem;
  color: #0f172a;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.live-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 7px 11px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.live-status.active {
  background: linear-gradient(135deg, #dcfce7, #bbf7d0);
  color: #166534;
}

.live-status.inactive {
  background: linear-gradient(135deg, #fee2e2, #fecaca);
  color: #991b1b;
}

.device-summary {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 22px;
}

.device-badge {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  width: fit-content;
  padding: 10px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.device-icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: linear-gradient(135deg, #dbeafe, #e0e7ff);
  font-size: 1.2rem;
}

.device-badge small {
  display: block;
  color: #64748b;
  font-size: 0.7rem;
  margin-bottom: 2px;
}

.device-badge strong {
  color: #0f172a;
  font-size: 1rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.summary-card {
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.summary-card.battery {
  background: linear-gradient(135deg, rgba(254, 249, 195, 0.35), rgba(255, 255, 255, 0.7));
}

.summary-card.ram {
  background: linear-gradient(135deg, rgba(219, 234, 254, 0.4), rgba(255, 255, 255, 0.7));
}

.summary-card.storage {
  background: linear-gradient(135deg, rgba(220, 252, 231, 0.4), rgba(255, 255, 255, 0.72));
}

.summary-card.network {
  background: linear-gradient(135deg, rgba(233, 213, 255, 0.36), rgba(255, 255, 255, 0.7));
}

.metric-kicker {
  color: #475569;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 800;
}

.summary-card strong {
  color: #0f172a;
  font-size: 0.96rem;
  line-height: 1.45;
  word-break: break-word;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 11px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.1);
}

.detail-item span {
  color: #64748b;
  font-size: 0.73rem;
  font-weight: 700;
}

.detail-item strong {
  color: #0f172a;
  font-weight: 700;
  word-break: break-word;
}

.apps-mini-box {
  margin-top: 18px;
  padding: 16px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(239,246,255,0.82));
  border: 1px solid rgba(148, 163, 184, 0.12);
}

.apps-mini-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.apps-mini-header h4 {
  margin: 0;
  font-size: 1rem;
  color: #0f172a;
}

.apps-mini-header span {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
  font-weight: 800;
}

.apps-mini-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.app-history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(148, 163, 184, 0.1);
}

.app-history-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.app-history-main div {
  min-width: 0;
}

.app-history-main strong {
  display: block;
  color: #0f172a;
  font-size: 0.86rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.app-history-main small {
  display: block;
  color: #64748b;
  font-size: 0.73rem;
}

.app-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: linear-gradient(135deg, #22c55e, #14b8a6);
  display: inline-block;
  flex-shrink: 0;
}

.duration-badge {
  padding: 6px 9px;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.08);
  color: #1d4ed8;
  font-size: 0.72rem;
  font-weight: 800;
  white-space: nowrap;
}

.apps-empty,
.empty-detail {
  color: #64748b;
  font-size: 0.85rem;
  text-align: center;
}

.empty-detail {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 240px;
  gap: 10px;
}

.empty-detail-icon {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  background: rgba(148, 163, 184, 0.08);
  display: grid;
  place-items: center;
  font-size: 1.4rem;
}

.empty-detail h4 {
  margin: 0;
  color: #0f172a;
}

.empty-detail p {
  margin: 0;
  max-width: 260px;
  line-height: 1.5;
}

.uuid {
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.75rem;
}

.active-text {
  color: #059669;
  font-weight: 700;
}

.inactive-text {
  color: #dc2626;
  font-weight: 700;
}

@media (max-width: 1100px) {
  .device-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .page-header,
  .panel-header,
  .header-actions,
  .item-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
  }

  .summary-grid,
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .row-actions {
    width: 100%;
    flex-wrap: wrap;
  }
}

.crud-page { gap: 18px; padding: 24px; border: 1px solid #DCE3EE; border-radius: 12px; background: linear-gradient(180deg, #F4F6FA, #EDF0F7); }
.page-header { padding-bottom: 10px; border-bottom: 1px solid #DCE3EE; }
.page-header h2 { color: #121A2B; font-size: 2rem; }
.eyebrow { color: #1E9B48; }
.primary-btn { background: #1E9B48; border-radius: 7px; box-shadow: 0 7px 14px rgba(0, 127, 95, 0.18); }
.primary-btn:hover { background: #167A39; }
.panel { padding: 20px; border-color: #DCE3EE; border-radius: 10px; box-shadow: 0 6px 18px rgba(0, 67, 49, 0.05); }
.inventory-panel { background: #fff; }
.detail-panel { background: linear-gradient(145deg, #E6F6EC, #F4F6FA); }
.search-box input { border-color: #DCE3EE; background: #F4F6FA; border-radius: 7px; }
.item-row { border-color: #DCE3EE; border-radius: 8px; background: #F4F6FA; }
.item-row:hover, .item-row.active { border-color: #3A6FB0; background: #E9EEFA; transform: none; }
.detail-btn { background: #E6F6EC; color: #167A39; border-radius: 7px; }
.revoke-btn { border-radius: 7px; }
.panel-header { border-color: #DCE3EE; }
.panel-header h3 { color: #121A2B; }
.device-badge, .summary-card, .detail-item, .apps-mini-box { border-color: #DCE3EE; border-radius: 8px; }
.device-icon { background: #dff3e9; }
.summary-card.network { background: #fff1ef; }
.summary-card strong, .detail-item strong { color: #121A2B; }
.duration-badge { background: #E6F6EC; color: #167A39; }

@media (max-width: 640px) {
  .crud-page { padding: 16px 12px; }
  .page-header h2 { font-size: 1.55rem; }
}

/* Inventario operativo */
.crud-page {
  position: relative;
  gap: 16px;
  padding: 28px;
  background: #F0F2F8;
  border: 1px solid #DCE3EE;
  border-radius: 8px;
}
.crud-page::before { position: absolute; top: 0; left: 28px; width: 64px; height: 4px; content: ''; background: #e1261c; }
.page-header { margin-bottom: 8px; padding-bottom: 16px; border-bottom: 1px solid #DCE3EE; }
.page-header > div { min-width: 0; }
.page-header h2 { color: #121A2B; font-size: 2.15rem; font-weight: 800; letter-spacing: -0.02em; }
.topbar-actions { display: flex; align-items: center; gap: 12px; }
.sync-state { display: inline-flex; align-items: center; gap: 7px; color: #15803d; font-size: 0.78rem; font-weight: 700; white-space: nowrap; padding: 8px 10px; border: 1px solid #DCE3EE; border-radius: 7px; background: #F4F6FA; }
.sync-state i { width: 8px; height: 8px; display: inline-block; border-radius: 50%; background: #22c55e; box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.12); }
.sync-state.syncing i { background: #f59e0b; }
.sync-state.failed { color: #dc2626; }
.sync-state.failed i { background: #ef4444; }
.page-caption { margin: 7px 0 0; color: #5B6B82; font-size: 0.88rem; }
.eyebrow { color: #1E9B48; font-weight: 800; font-size: 0.85rem; }
.primary-btn { background: #1E9B48; border-radius: 6px; box-shadow: none; }
.primary-btn:hover { background: #167A39; }
.device-layout { grid-template-columns: minmax(280px, 0.78fr) minmax(420px, 1.22fr); gap: 12px; }
.panel { padding: 22px; border: 1px solid #DCE3EE; border-radius: 8px; box-shadow: 0 5px 15px rgba(0, 67, 49, 0.045); }
.inventory-panel { min-height: 620px; background: #fff; }
.panel-topline > div { display: flex; align-items: center; gap: 12px; }
.panel-index { color: #e1261c; font-size: 0.72rem; font-weight: 900; }
.panel-topline { border-bottom: 1px solid #DCE3EE; padding-bottom: 14px; }
.search-box input { padding: 12px; background: #F4F6FA; border: 1px solid #DCE3EE; border-radius: 6px; }
.item-row { padding: 14px; background: #F4F6FA; border: 1px solid #DCE3EE; border-left: 3px solid transparent; border-radius: 6px; }
.item-row:hover, .item-row.active { background: #E9EEFA; border-color: #9AACC9; border-left-color: #1E9B48; transform: none; }
.status-badge { border-radius: 4px; }
.status-badge.active { background: #E6F6EC; color: #167A39; }
.status-badge.inactive { background: #fff0ee; color: #b42318; }
.detail-btn { padding: 9px 12px; background: #E6F6EC; color: #167A39; border-radius: 6px; }
.detail-panel { min-height: 620px; background: #fff; border-top: 4px solid #1E9B48; }
.detail-panel.empty { background: #F8F9FC; border-top-color: #b8d5c7; }
.panel-header { margin-bottom: 20px; padding-bottom: 16px; border-color: #DCE3EE; }
.panel-header h3 { color: #121A2B; }
.live-status { border-radius: 4px; }
.live-status.active { background: #E6F6EC; color: #167A39; }
.live-status.inactive { background: #fff0ee; color: #b42318; }
.device-badge, .summary-card, .detail-item, .apps-mini-box { border-radius: 6px; border-color: #DCE3EE; }
.device-badge { background: #F4F6FA; }
.device-icon { background: #E6F6EC; }
.summary-card { background: #F4F6FA; }
.summary-card.battery { background: #fff8e8; }
.summary-card.ram { background: #E9EEFA; }
.summary-card.storage { background: #E9EEFA; }
.summary-card.network { background: #fff0ee; }
.summary-card strong, .detail-item strong, .apps-mini-header h4 { color: #121A2B; }
.detail-item { background: #F8F9FC; }
.apps-mini-box { background: #F4F6FA; }
.duration-badge { background: #E6F6EC; color: #167A39; border-radius: 4px; }
.device-section-icon, .detail-heading-icon { display: grid; place-items: center; flex: 0 0 auto; width: 38px; height: 38px; border-radius: 10px; color: #1E9B48; background: #E6F6EC; font-size: 1.25rem; }
.panel-topline { align-items: center; }
.panel-topline > div:first-child { min-width: 0; }
.device-count { display: grid; place-items: center; min-width: 24px; height: 24px; padding: 0 7px; border-radius: 999px; color: #1E9B48; background: #E6F6EC; font-size: 0.76rem; font-weight: 800; }
.device-title-wrap { position: relative; padding-left: 52px; }
.detail-heading-icon { position: absolute; left: 0; top: 0; width: 40px; height: 40px; background: #e7f6ef; }
.device-title-wrap .eyebrow { padding-top: 2px; }
.device-title-wrap h3 { font-size: 1.2rem; }
.item-info strong { color: #121A2B; }
.item-info small { color: #5B6B82; }
.row-actions .detail-btn { font-size: 0; width: 30px; padding: 8px 0; background: #E6F6EC; }
.row-actions .detail-btn::after { content: '›'; font-size: 1.2rem; line-height: 1; }
.row-actions .revoke-btn { font-size: 0; width: 30px; padding: 8px 0; background: #fff0ee; }
.row-actions .revoke-btn::after { content: '×'; font-size: 1.1rem; line-height: 1; }
.summary-card { min-height: 62px; }
.summary-card.battery { background: #fff8e8; }
.summary-card.ram { background: #f1f8fc; }
.summary-card.storage { background: #f1f8fc; }
.summary-card.network { background: #E6F6EC; }
.device-badge { width: 100%; padding: 13px 14px; background: #F4F6FA; }
.device-icon { width: 42px; height: 42px; display: grid; place-items: center; border-radius: 11px; color: #1E9B48; background: #e0f4e9; font-size: 1.25rem; }
.summary-card { position: relative; min-height: 74px; padding: 12px 14px 12px 60px; justify-content: center; }
.summary-icon { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); width: 38px; height: 38px; display: grid; place-items: center; border-radius: 11px; color: #1E9B48; background: rgba(255,255,255,0.75); font-size: 1.25rem; }
.summary-card.battery .summary-icon { color: #b7791f; background: #FFEFBD; }
.summary-card.ram .summary-icon, .summary-card.storage .summary-icon { color: #167A39; background: #e3f1ff; }
.summary-card.network .summary-icon { color: #1E9B48; background: #E6F6EC; }
.summary-card .metric-kicker { color: #5B6B82; text-transform: none; letter-spacing: 0; font-size: 0.7rem; }
.summary-card strong { font-size: 0.88rem; }
.detail-grid { gap: 14px; }
.detail-item { position: relative; min-height: 86px; justify-content: flex-start; padding: 16px 15px 16px 68px; background: #f7fbf9; border: 1px solid #DCE3EE; border-radius: 8px; }
.detail-icon { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); width: 42px; height: 42px; display: grid; place-items: center; border-radius: 11px; color: #5B6B82; background: #EEF1F8; font-size: 1.25rem; font-weight: 700; }
.status-detail { background: #eefaf3; border-color: #CBD8EC; }
.status-detail .detail-icon { color: #078858; background: #E6F6EC; }
.status-detail span:not(.detail-icon), .status-detail strong { color: #078858; }
.uuid-detail { background: #EEF1F8; }
.uuid-detail .detail-icon { color: #5B6B82; background: #e7f1f2; }
.detail-item span { color: #5B6B82; font-size: 0.78rem; font-weight: 700; }
.detail-item strong { color: #121A2B; font-size: 0.88rem; line-height: 1.35; }
.detail-item span.detail-icon { color: #5B6B82; font-size: 1.25rem; font-weight: 700; }
.status-detail span.detail-icon { color: #078858; }
.uuid-detail span.detail-icon { color: #5B6B82; }
.apps-mini-box { margin-top: 14px; padding: 14px; background: #F4F6FA; }
.apps-mini-header h4 { font-size: 0.92rem; }

@media (max-width: 640px) {
  .crud-page { padding: 18px 12px; }
  .crud-page::before { left: 12px; }
  .page-header h2 { font-size: 1.7rem; }
}
/* ===== Tarjetas sin color en Ficha técnica ===== */
.summary-card,
.summary-card.battery,
.summary-card.ram,
.summary-card.storage,
.summary-card.network,
.detail-item,
.status-detail,
.uuid-detail {
  background: #fff;
  border-color: #DCE3EE;
}

.summary-icon,
.summary-card.battery .summary-icon,
.summary-card.ram .summary-icon,
.summary-card.storage .summary-icon,
.summary-card.network .summary-icon,
.detail-icon,
.status-detail .detail-icon,
.uuid-detail .detail-icon,
.status-detail span.detail-icon,
.uuid-detail span.detail-icon {
  background: #F4F6FA;
  color: #5B6B82;
}

.status-detail span:not(.detail-icon) {
  color: #5B6B82;
}

.status-detail strong {
  color: #121A2B;
}

/* ---- SIMs por dispositivo ---- */
.sim-report-status.stale { color: #92400e !important; }

.sim-churn { color: #B54708 !important; font-weight: 700; }
</style>