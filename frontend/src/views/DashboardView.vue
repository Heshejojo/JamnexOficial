<template>
  <div class="dashboard-page">
    <header class="topbar">
      <div class="welcome-heading">
        <p class="eyebrow">Panel de control</p>
        <h2>Bienvenido a Jamnex<span aria-hidden="true"></span></h2>
        <p>Sistema de Monitoreo y Administracion de Terminales Android</p>
      </div>
      <div class="topbar-actions">
        <span class="sync-state" :class="{ syncing: loading, failed: syncError }">
          <i></i>{{ syncError ? syncMessage : loading ? 'Sincronizando' : `Actualizado ${lastSync}` }}
        </span>
        <button class="primary-btn" :disabled="loading" @click="loadDashboard">Actualizar</button>
      </div>
    </header>

    <section class="stats-grid">
      <div class="stat-card stat-devices"><div class="stat-icon">▣</div><div class="stat-body"><span>Dispositivos</span><strong>{{ metrics.devices }}</strong><small>Total de dispositivos registrados</small></div></div>
      <div class="stat-card stat-sims"><div class="stat-icon">▤</div><div class="stat-body"><span>SIMs</span><strong>{{ metrics.sims }}</strong><small>Total de SIMs activas</small></div></div>
      <div class="stat-card stat-online"><div class="stat-icon">▥</div><div class="stat-body"><span>En línea</span><strong>{{ metrics.connected }}</strong><small>Dispositivos conectados</small></div></div>
      <div class="stat-card stat-data"><div class="stat-icon">▤</div><div class="stat-body"><span>Datos móviles usados</span><strong>{{ formatMb(metrics.mobile) }}</strong><small>Consumo total por mes</small></div></div>
    </section>

    <section class="command-grid">
      <div class="command-hero">
        <div class="hero-heading"><div><span class="hero-kicker">▥ &nbsp; Red móvil</span><h3>Consumo acumulado</h3></div><span class="hero-period">◷ &nbsp; {{ monthLabel }}</span></div>
        <strong class="hero-value">{{ formatMb(metrics.mobile) }}</strong>
        <p>{{ metrics.sims }} SIM{{ metrics.sims === 1 ? '' : 's' }} activa{{ metrics.sims === 1 ? '' : 's' }}</p>
        <div class="hero-chart"><span v-for="(bar, i) in weekBars" :key="i" :style="{ height: `${bar.height}px` }" :title="`${bar.label}: ${formatMb(bar.value)}`"></span></div>
       <div class="hero-footer"><span>Últimos 7 días</span><span class="hero-note">{{ alerts.length ? `⚠ ${alerts.length} alerta${alerts.length === 1 ? '' : 's'}` : '✓ Sin alertas' }}</span></div>
      </div>


      <div class="attention-panel">
        <div class="attention-heading"><div><span class="hero-kicker">♧ &nbsp; Atención</span><h3>Top 5 SIMs por consumo</h3></div><router-link to="/sims">Ver todas →</router-link></div>
        <ul v-if="topSims.length" class="top-list">
          <li v-for="(s, i) in topSims" :key="s.id">
            <span class="top-rank">{{ i + 1 }}</span>
            <div class="top-info">
              <strong>{{ s.label }}</strong>
              <div class="top-track"><span :style="{ width: `${s.percent}%` }"></span></div>
            </div>
            <b>{{ formatMb(s.value) }}</b>
          </li>
        </ul>
        <p v-else class="top-empty">No se ha registrado consumo en {{ monthLabel }}.</p>
        <div class="attention-footer">ⓘ &nbsp; Consumo de datos móviles de {{ monthLabel }}, según la actividad de los dispositivos.</div>
      </div>
    </section>

    <section class="alerts-panel">
      <div class="alerts-heading"><span class="hero-kicker">⚠ &nbsp; Alertas</span><h3>Requieren atención</h3></div>
      <ul v-if="alerts.length" class="alerts-list">
        <li v-for="(alert, i) in alerts" :key="i" :class="alert.level">{{ alert.text }}</li>
      </ul>
      <p v-else class="alerts-ok">✓ Todo en orden: ningún equipo ni SIM necesita atención.</p>
    </section>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import api from '../services/api';

const loading = ref(false);
const lastSync = ref('nunca');
const syncError = ref(false);
const syncMessage = ref('');
const weekBars = ref(Array.from({ length: 7 }, () => ({ label: '', value: 0, height: 5 })));
const alerts = ref([]);
const nowDate = new Date();
const selectedMonth = `${nowDate.getFullYear()}-${String(nowDate.getMonth() + 1).padStart(2, '0')}`;
const monthLabel = nowDate.toLocaleDateString('es-MX', { month: 'long', year: 'numeric' });
const topSims = ref([]);
const metrics = reactive({ devices: 0, sims: 0, connected: 0, stale: 0, mobile: 0, consumption: 0 });

function asList(data) {
  return Array.isArray(data) ? data : data?.results || data?.value || [];
}

async function loadDashboard() {
  loading.value = true;
  syncError.value = false;
  syncMessage.value = '';
  try {
    const [selYear, selMonth] = selectedMonth.split('-').map(Number);
    const summaryResponse = await api.get('/dashboard/summary/', {
      params: { anio: selYear, mes: selMonth },
    });
    const summary = summaryResponse.data;
    const devices = asList(summary.devices);
    const sims = asList(summary.sims);
    const monthly = asList(summary.consumption);

    const dayKey = (date) =>
      typeof date === 'string'
        ? date.slice(0, 10)
        : `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;

    metrics.devices = summary.metrics.devices;
    metrics.sims = summary.metrics.sims;
    metrics.connected = summary.metrics.connected;
    metrics.mobile = monthly.reduce((sum, item) => sum + Number(item.consumo_datos_movil || 0), 0);
    metrics.consumption = metrics.mobile;

    // Barras reales de los últimos 7 días
    const byDay = {};
    monthly.forEach((item) => {
      const key = dayKey(item.fecha);
      byDay[key] = (byDay[key] || 0) + Number(item.consumo_datos_movil || 0);
    });
    const today = new Date();
    const isCurrentMonth = selYear === today.getFullYear() && selMonth === today.getMonth() + 1;
    const endDate = isCurrentMonth ? today : new Date(selYear, selMonth, 0);
    const lastSeven = Array.from({ length: 7 }, (_, i) => {
      const date = new Date(endDate);
      date.setDate(date.getDate() - (6 - i));
      return date;
    });
    const maxDay = Math.max(0, ...lastSeven.map((date) => byDay[dayKey(date)] || 0));
    weekBars.value = lastSeven.map((date) => {
      const value = byDay[dayKey(date)] || 0;
      return {
        label: date.toLocaleDateString('es-MX', { weekday: 'short' }),
        value,
        height: maxDay ? 5 + (value / maxDay) * 50 : 5,
      };
    });

    // SIM con mayor consumo del mes
    const consumptionBySim = monthly.reduce((result, item) => {
      const key = item.sim || item.dispositivo || 'Sin asignar';
      result[key] = (result[key] || 0) + Number(item.consumo_datos_movil || 0);
      return result;
    }, {});
    const newAlerts = [];
    const now = Date.now();
    devices.forEach((device) => {
      const name = device.modelo || device.device_uuid;
      const last = device.ultimo_contacto ? new Date(device.ultimo_contacto).getTime() : null;
      if (!last) {
        newAlerts.push({ level: 'danger', text: `${name} está inactivo: nunca ha reportado` });
      } else if (now - last > 72 * 60 * 60 * 1000) {
        newAlerts.push({ level: 'danger', text: `${name} está inactivo: lleva más de 72 h sin reportar` });
      }
      if (device.battery_percent != null && device.battery_percent <= 20 && device.battery_state !== 'CARGANDO') {
        newAlerts.push({ level: 'warn', text: `${name} con batería baja (${device.battery_percent}%)` });
      }
    });
    sims.forEach((item) => {
      const pct = ((consumptionBySim[item.id] || 0) / 2048) * 100;
      if (pct >= 80) {
        newAlerts.push({
          level: pct >= 100 ? 'danger' : 'warn',
          text: `${item.numero_telefonico || `SIM ${item.id}`} lleva ${pct.toFixed(0)}% del límite de 2 GB`,
        });
      }
    });
    const bySim = {};
    monthly.forEach((item) => {
      if (item.sim) bySim[item.sim] = (bySim[item.sim] || 0) + Number(item.consumo_datos_movil || 0);
    });
    const ranking = Object.entries(bySim).sort((a, b) => b[1] - a[1]).slice(0, 5);
    const maxSim = ranking[0]?.[1] || 0;
    topSims.value = ranking.map(([id, value]) => {
      const found = sims.find((s) => String(s.id) === String(id));
      return {
        id,
        label: found?.numero_telefonico || found?.operador_nombre || `SIM ${id}`,
        value,
        percent: maxSim ? Math.max(3, (value / maxSim) * 100) : 0,
      };
    });
    alerts.value = newAlerts;
    lastSync.value = new Date().toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', hour12: true });
  } catch (error) {
    console.error(error);
    syncError.value = true;
    const status = error.response?.status;
    syncMessage.value = status === 403
      ? 'Sin permiso'
      : status
        ? `Error ${status}`
        : 'Sin conexión';
  } finally {
    loading.value = false;
  }
}

function formatMb(value) {
  const amount = Number(value || 0);
  return amount >= 1024 ? `${(amount / 1024).toFixed(1)} GB` : `${amount.toFixed(1)} MB`;
}

let refreshTimer = null;

onMounted(() => {
  loadDashboard();
  refreshTimer = setInterval(loadDashboard, 30000);
});

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
  background: linear-gradient(180deg, #F4F6FA 0%, #EDF0F7 100%);
  border-radius: 24px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.topbar-caption {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 0.88rem;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sync-state {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #15803d;
  font-size: 0.78rem;
  font-weight: 700;
  white-space: nowrap;
}

.sync-state i,
.device-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.12);
}

.sync-state.syncing i { background: #f59e0b; }
.sync-state.failed { color: #dc2626; }
.sync-state.failed i { background: #ef4444; }

.eyebrow {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #1E9B48;
  font-size: 0.85rem;
  font-weight: 800;
}

.topbar h2 {
  margin: 4px 0 0;
  font-size: 1.8rem;
  font-weight: 800;
  color: #0f172a;
}

.primary-btn {
  border: 0;
  background: linear-gradient(135deg, #1E9B48, #00a878);
  color: white;
  border-radius: 12px;
  padding: 10px 16px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 8px 16px rgba(0, 127, 95, 0.22);
}

.primary-btn:disabled {
  cursor: wait;
  opacity: 0.65;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  background: white;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.15);
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
}

.card-blue { background: linear-gradient(135deg, #effaf5, #ffffff); }
.card-green { background: linear-gradient(135deg, #ecfdf5, #ffffff); }
.card-violet { background: linear-gradient(135deg, #fff4f2, #ffffff); }
.card-green-light { background: linear-gradient(135deg, #dcfce7, #ffffff); }

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 1.3rem;
  flex-shrink: 0;
}

.stat-icon.blue { background: linear-gradient(135deg, #00a878, #1E9B48); }
.stat-icon.green { background: linear-gradient(135deg, #34d399, #10b981); }
.stat-icon.violet { background: linear-gradient(135deg, #ef4444, #c81e1e); }

.stat-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-body span {
  color: #64748b;
  font-size: 0.8rem;
  font-weight: 600;
}

.stat-body strong {
  font-size: 1.6rem;
  line-height: 1;
  color: #0f172a;
  font-weight: 800;
}

.content-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 16px;
}

.signal-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  overflow: hidden;
  background: #dbe4ee;
  border: 1px solid #dbe4ee;
  border-radius: 14px;
}

.signal-strip > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px 18px;
  background: rgba(255, 255, 255, 0.92);
}

.strip-label,
.panel-meta {
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.signal-strip strong {
  color: #0f172a;
  font-size: 1.35rem;
}

.signal-strip strong.warning { color: #d97706; }
.signal-strip small { color: #94a3b8; }

.panel {
  background: white;
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 14px;
  padding: 18px;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  padding-bottom: 12px;
}

.panel-meta {
  margin-left: auto;
  text-transform: none;
  letter-spacing: 0;
  font-weight: 600;
}

.panel-subtitle {
  margin: 5px 0 0;
  color: #94a3b8;
  font-size: 0.8rem;
}

.panel-link {
  margin-left: auto;
  color: #1E9B48;
  font-size: 0.82rem;
  font-weight: 700;
  text-decoration: none;
}

.device-list {
  display: grid;
  gap: 2px;
}

.device-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 4px;
  border-bottom: 1px solid #eef2f7;
}

.device-row:last-child { border-bottom: 0; }
.device-dot { flex: 0 0 auto; background: #94a3b8; box-shadow: 0 0 0 4px rgba(148, 163, 184, 0.12); }
.device-dot.online { background: #22c55e; box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.12); }

.device-name {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 3px;
}

.device-name strong {
  overflow: hidden;
  color: #1e293b;
  font-size: 0.9rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.device-name small { color: #94a3b8; font-size: 0.76rem; }
.device-status { color: #64748b; font-size: 0.76rem; font-weight: 700; }
.device-status.online { color: #15803d; }

.panel-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
}

.bar-chart {
  height: 160px;
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 8px 0;
}

.bar-column {
  flex: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
  gap: 6px;
}

.bar {
  width: 100%;
  max-width: 36px;
  min-height: 6px;
  border-radius: 6px 6px 2px 2px;
  background: linear-gradient(180deg, #34d399, #10b981);
  transition: all 0.3s ease;
}

.bar:hover {
  opacity: 0.8;
  transform: scaleY(1.05);
}

.bar-column small {
  color: #64748b;
  font-size: 0.7rem;
  font-weight: 600;
}

.status-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: linear-gradient(135deg, #f8fafc, #f0f9ff);
  border-radius: 10px;
  border: 1px solid rgba(37, 99, 235, 0.1);
}

.status-label {
  color: #475569;
  font-weight: 600;
  font-size: 0.9rem;
}

.status-value {
  color: #34C98F;
  font-weight: 700;
  font-size: 1.1rem;
}

.status-value.alert {
  color: #ef4444;
}

.empty-list {
  padding: 20px;
  text-align: center;
  color: #94a3b8;
  background: rgba(248, 250, 252, 0.6);
  border-radius: 10px;
  border: 1px dashed #cbd5e1;
}

@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .content-grid {
    grid-template-columns: 1fr;
  }

  .signal-strip {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .topbar h2 {
    font-size: 1.4rem;
  }

  .topbar,
  .topbar-actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .topbar-actions { width: 100%; }
  .primary-btn { width: 100%; }

  .bar-chart {
    height: 140px;
  }
}

.welcome-heading h2 { margin: 4px 0 2px; font-size: 1.75rem; color: #102a22; }
.welcome-heading > p:last-child { margin: 0; color: #5B6B82; font-size: 0.78rem; }
.stats-grid { gap: 12px; }
.stat-card { min-height: 102px; padding: 14px; border-radius: 8px; box-shadow: 0 5px 14px rgba(15, 23, 42, 0.04); }
.stat-card b { margin-left: auto; color: #6c8790; font-size: 1.4rem; font-weight: 400; }
.stat-card .stat-icon { width: 40px; height: 40px; border-radius: 10px; color: #1E9B48; background: #d6f7e6; font-size: 1.3rem; }
.stat-sims .stat-icon { color: #1478bd; background: #dceeff; }
.stat-online .stat-icon { color: #7045d9; background: #ebe2ff; }
.stat-data .stat-icon { color: #078b90; background: #d8f7f5; }
.stat-body { gap: 4px; }
.stat-body span { color: #26423a; font-size: 0.72rem; }
.stat-body strong { font-size: 1.35rem; }
.stat-body small { color: #5B6B82; font-size: 0.65rem; }
.command-grid { grid-template-columns: 1.35fr 1fr; gap: 12px; }
.command-hero { min-height: 250px; padding: 20px 22px; border-radius: 9px; background: linear-gradient(125deg, #167A39, #008c68); }
.hero-heading h3 { margin: 8px 0 0; font-size: 1rem; }
.hero-period { padding: 7px 10px; border: 1px solid rgba(255,255,255,0.22); border-radius: 6px; color: #e4fff4; font-size: 0.7rem; }
.hero-value { margin: 22px 0 2px; font-size: 2.7rem; letter-spacing: -0.03em; }
.hero-chart { height: 55px; display: flex; align-items: flex-end; gap: 2px; margin-top: 14px; border-bottom: 1px solid rgba(255,255,255,0.2); background: repeating-linear-gradient(90deg, transparent 0, transparent calc(14.28% - 1px), rgba(255,255,255,0.08) calc(14.28% - 1px), rgba(255,255,255,0.08) 14.28%); }
.hero-chart span { flex: 1; max-width: 7px; margin: 0 auto; border-radius: 5px 5px 0 0; background: #72e0ba; box-shadow: 0 0 0 3px rgba(114,224,186,0.12); }
.hero-footer { margin-top: 12px; padding-top: 0; border-top: 0; }
.hero-note { padding: 7px 10px; border-radius: 8px; background: rgba(84, 218, 155, 0.25); color: #e4fff4; }
.attention-panel { min-height: 250px; padding: 20px; border: 1px solid #e1ece7; border-radius: 9px; background: #fff; box-shadow: 0 5px 14px rgba(15, 23, 42, 0.04); }
.attention-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.attention-heading h3 { margin: 8px 0 0; color: #173b30; font-size: 0.95rem; }
.attention-heading a { color: #1E9B48; font-size: 0.68rem; font-weight: 800; text-decoration: none; }
.attention-main { display: flex; align-items: center; gap: 14px; margin: 23px 0; }
.attention-icon { width: 46px; height: 46px; display: grid; place-items: center; border-radius: 50%; background: #e4f8ee; color: #1E9B48; font-size: 1.4rem; }
.attention-main strong { display: block; color: #26423a; font-size: 0.88rem; }
.attention-main p { margin: 4px 0 6px; color: #8a9a94; font-size: 0.68rem; }
.attention-main b { display: block; color: #1E9B48; font-size: 1.25rem; }
.attention-main small { color: #8a9a94; font-size: 0.66rem; }
.attention-footer { padding-top: 14px; border-top: 1px solid #edf2ef; color: #5B6B82; font-size: 0.68rem; line-height: 1.45; }

@media (max-width: 760px) {
  .welcome-heading h2 { font-size: 1.45rem; }
  .topbar-actions { width: 100%; flex-wrap: wrap; }
  .command-grid { grid-template-columns: 1fr; }
}

.dashboard-page {
  position: relative;
  gap: 18px;
  padding: 30px;
  border: 1px solid #DCE3EE;
  border-radius: 12px;
}

.dashboard-page::before {
  position: absolute;
  top: 0;
  left: 30px;
  width: 72px;
  height: 4px;
  content: '';
  background: #e1261c;
}

.topbar { padding-bottom: 8px; }
.topbar h2 { font-size: 2.1rem; letter-spacing: -0.02em; }
.topbar-caption { color: #5B6B82; }
.sync-state { padding: 8px 10px; border: 1px solid #DCE3EE; border-radius: 7px; background: #F4F6FA; }
.primary-btn { border-radius: 7px; }

.command-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(270px, 0.8fr);
  gap: 16px;
}

.command-hero {
  min-height: 218px;
  padding: 24px 26px;
  color: #fff;
  background: linear-gradient(125deg, #167A39, #008c68);
  border-radius: 10px;
  box-shadow: 0 12px 22px rgba(0, 88, 63, 0.16);
}

.hero-heading,
.hero-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.hero-kicker { color: #c4efde; font-size: 0.78rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }
.hero-live { color: #e4fff4; font-size: 0.68rem; font-weight: 800; }
.hero-live i { display: inline-block; width: 7px; height: 7px; margin-right: 5px; border-radius: 50%; background: #a7f3d0; }
.hero-value { display: block; margin: 34px 0 4px; font-size: 4.2rem; font-weight: 800; letter-spacing: -0.05em; }
.command-hero p { margin: 0; color: #d7f3e9; }
.hero-footer { margin-top: 30px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.2); color: #b7e4d4; font-size: 0.78rem; }

.quick-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1px;
  overflow: hidden;
  background: #DCE3EE;
  border: 1px solid #DCE3EE;
  border-radius: 10px;
}

.quick-metric { display: flex; min-height: 108px; flex-direction: column; justify-content: center; padding: 16px 18px; background: #fff; }
.quick-metric span { color: #5B6B82; font-size: 0.74rem; font-weight: 800; text-transform: uppercase; }
.quick-metric strong { margin-top: 7px; color: #121A2B; font-size: 1.7rem; }
.quick-metric small { color: #94a79f; }
.green-text { color: #008c68 !important; }
.warning { color: #c2410c !important; }

.content-grid { grid-template-columns: minmax(0, 1.35fr) minmax(240px, 0.65fr); }
.panel { padding: 20px; border: 1px solid #DCE3EE; border-radius: 10px; box-shadow: 0 6px 18px rgba(0, 67, 49, 0.05); }
.panel-header { margin-bottom: 14px; padding-bottom: 14px; border-color: #e1eee8; }
.panel-header > div { display: flex; align-items: center; gap: 9px; }
.section-number { color: #e1261c; font-size: 0.7rem; font-weight: 900; }
.panel-meta { color: #81948c; }
.bar { background: linear-gradient(180deg, #00a878, #167A39); border-radius: 3px 3px 1px 1px; }
.status-item { padding: 14px; background: #f6fbf8; border-color: #DCE3EE; border-radius: 7px; }
.status-value { color: #1E9B48; }
.devices-panel { margin-top: 0; }

.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.overview-panel {
  min-height: 164px;
  padding: 22px 24px;
  border: 1px solid #DCE3EE;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 6px 18px rgba(0, 67, 49, 0.05);
}

.connection-panel { background: linear-gradient(135deg, #fff, #effaf5); }
.usage-panel { background: linear-gradient(135deg, #167A39, #008c68); color: #fff; }
.overview-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.overview-kicker { color: #5B6B82; font-size: 0.7rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }
.usage-panel .overview-kicker { color: #b7e4d4; }
.overview-heading h3 { margin: 6px 0 0; color: #121A2B; font-size: 1.08rem; }
.usage-panel .overview-heading h3 { color: #fff; }
.overview-heading > strong { color: #1E9B48; font-size: 2rem; line-height: 1; }
.usage-dot { width: 10px; height: 10px; margin-top: 5px; border-radius: 50%; background: #a7f3d0; box-shadow: 0 0 0 5px rgba(167, 243, 208, 0.18); }
.connection-track { height: 10px; margin-top: 28px; overflow: hidden; border-radius: 5px; background: #d9ebe2; }
.connection-track span { display: block; height: 100%; border-radius: inherit; background: #1E9B48; transition: width 0.3s ease; }
.overview-footer { display: flex; justify-content: space-between; gap: 12px; margin-top: 12px; color: #5B6B82; font-size: 0.78rem; }
.usage-panel .overview-footer { color: #d7f3e9; }
.usage-value { display: block; margin-top: 22px; color: #fff; font-size: 2.25rem; }
.top-sim-panel { background: #fff; }
.top-sim-value { display: block; overflow: hidden; margin-top: 28px; color: #121A2B; font-size: 1.75rem; text-overflow: ellipsis; white-space: nowrap; }
.top-sim-panel .overview-footer a { color: #1E9B48; font-weight: 800; text-decoration: none; }

@media (max-width: 900px) {
  .command-grid { grid-template-columns: 1fr; }
  .overview-grid { grid-template-columns: 1fr; }
}

@media (max-width: 640px) {
  .dashboard-page { padding: 18px 14px; }
  .dashboard-page::before { left: 14px; }
  .topbar h2 { font-size: 1.65rem; }
  .command-hero { padding: 20px; }
  .hero-value { margin-top: 28px; font-size: 2.6rem; }
  .quick-metrics { grid-template-columns: repeat(3, 1fr); }
  .quick-metric { min-height: 92px; padding: 12px 9px; }
  .quick-metric strong { font-size: 1.35rem; }
  .quick-metric span, .quick-metric small { font-size: 0.65rem; }
}
.hero-chart span { max-width: 22px; }
.alerts-panel { padding: 20px; border: 1px solid #DCE3EE; border-radius: 10px; background: #fff; box-shadow: 0 6px 18px rgba(0, 67, 49, 0.05); }
.alerts-heading .hero-kicker { color: #1E9B48; }
.alerts-heading h3 { margin: 6px 0 12px; color: #121A2B; font-size: 1rem; }
.alerts-list { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }
.alerts-list li { padding: 10px 12px; border-left: 3px solid; border-radius: 6px; font-size: 0.82rem; font-weight: 600; }
.alerts-list li.warn { background: #fff8e8; border-color: #f59e0b; color: #92400e; }
.alerts-list li.danger { background: #fff0ee; border-color: #ef4444; color: #b42318; }
.alerts-ok { margin: 0; color: #167A39; font-size: 0.85rem; font-weight: 700; }
.top-list { display: grid; gap: 12px; margin: 18px 0; padding: 0; list-style: none; }
.top-list li { display: flex; align-items: center; gap: 12px; }
.top-rank { width: 24px; height: 24px; display: grid; place-items: center; flex-shrink: 0; border-radius: 50%; background: #E6F6EC; color: #167A39; font-size: 0.72rem; font-weight: 800; }
.top-info { min-width: 0; flex: 1; }
.top-info strong { display: block; overflow: hidden; color: #26423a; font-size: 0.82rem; text-overflow: ellipsis; white-space: nowrap; }
.top-track { height: 6px; margin-top: 5px; overflow: hidden; border-radius: 3px; background: #E6EDF0; }
.top-track span { display: block; height: 100%; border-radius: inherit; background: #1E9B48; }
.top-list li > b { flex-shrink: 0; color: #121A2B; font-size: 0.8rem; }
.top-empty { margin: 22px 0; color: #8a9a94; font-size: 0.82rem; text-align: center; }
</style>