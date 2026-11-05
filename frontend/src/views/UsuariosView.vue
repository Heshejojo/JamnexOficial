<template>
  <div class="crud-page">
    <header class="page-header"><div><p class="eyebrow">Administración de acceso</p><h2>Usuarios</h2><p class="page-caption">Gestiona cuentas, permisos y acceso al panel de control.</p></div><div class="topbar-actions"><span class="sync-state" :class="{ syncing: loading, failed: loadError }"><i></i>{{ loadError ? 'Sin conexión' : loading ? 'Sincronizando' : `Actualizado ${lastSync}` }}</span><button class="primary-btn" :disabled="loading" @click="load">Actualizar</button></div></header>
    <div class="grid-layout">
      <section class="panel user-form-panel">
        <div class="panel-heading">
          <span class="panel-icon">＋</span>
          <div>
            <h3>{{ editing ? 'Editar administrador' : 'Agregar administrador' }}</h3>
            <p class="panel-intro">Define qué módulos puede consultar cada cuenta.</p>
          </div>
        </div>
        <form @submit.prevent="save">
          <input v-model="form.username" placeholder="Usuario" required />
          <input v-model="form.email" type="email" placeholder="Correo" required />
          <div class="form-columns">
            <input v-model="form.first_name" placeholder="Nombre" />
            <input v-model="form.last_name" placeholder="Apellidos" />
          </div>
          <input v-model="form.password" type="password" placeholder="Contraseña (opcional al editar)" />
          <div class="role-lock"><span>Rol asignado</span><strong>Administrador</strong></div>
          <div class="permissions">
            <span class="field-label">Permisos de acceso</span>
            <label v-for="permission in permissionOptions" :key="permission.key">
              <input v-model="form.permisos[permission.key]" type="checkbox" />{{ permission.label }}
            </label>
          </div>
          <select v-model="form.activo">
            <option :value="true">Activo</option>
            <option :value="false">Inactivo</option>
          </select>
          <p v-if="saveError" class="save-error">{{ saveError }}</p>
          <div class="actions-row">
            <button class="primary-btn" :disabled="loading">{{ editing ? 'Actualizar' : 'Guardar administrador' }}</button>
            <button v-if="editing" class="secondary-btn" type="button" @click="reset">Cancelar</button>
          </div>
        </form>
      </section>
      <section class="panel users-list-panel">
        <div class="panel-heading">
          <span class="panel-icon">♙</span>
          <div>
            <h3>Administradores</h3>
            <p class="panel-intro">{{ filtered.length }} cuentas registradas</p>
          </div>
          <span class="user-count">{{ filtered.length }}</span>
        </div>
        <input class="user-search" v-model="query" placeholder="Buscar usuario o correo" />
        <div class="list">
          <div v-for="item in filtered" :key="item.id" class="item-row">
            <div class="user-avatar">{{ (item.first_name || item.username || 'U').slice(0, 1).toUpperCase() }}</div>
            <div class="user-row-info">
              <strong>{{ item.email || item.username }}</strong>
              <small>{{ item.first_name }} {{ item.last_name }} · {{ item.rol?.nombre || 'Administrador' }}</small>
              <div class="permission-list">
                <span v-for="permission in visiblePermissions(item)" :key="permission.key">{{ permission.label }}</span>
              </div>
            </div>
            <span class="user-status" :class="item.activo ? 'active' : 'inactive'">● {{ item.activo ? 'Activo' : 'Inactivo' }}</span>
            <div class="row-actions">
              <button class="edit-btn" title="Editar usuario" @click="edit(item)">✎</button>
              <button class="delete-btn" title="Eliminar usuario" @click="remove(item)">×</button>
            </div>
          </div>
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
const items = ref([]);
const roles = ref([]);
const query = ref('');
const loading = ref(false);
const editing = ref(false);
const editingId = ref(null);
const loadError = ref('');
const saveError = ref('');
const lastSync = ref('nunca');
const form = reactive({
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  password: '',
  rol_id: null,
  activo: true,
  permisos: { dashboard: true, dispositivos: true, sims: true, usuarios: true },
});
const permissionOptions = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'dispositivos', label: 'Dispositivos' },
  { key: 'sims', label: 'SIMs' },
  { key: 'usuarios', label: 'Usuarios' },
];
const filtered = computed(() => items.value.filter((item) =>
  `${item.username} ${item.email} ${item.first_name} ${item.last_name}`.toLowerCase().includes(query.value.toLowerCase())
));

async function load() {
  loading.value = true;
  loadError.value = '';
  try {
    const [users, roleData] = await Promise.all([
      api.get('/usuarios/'),
      api.get('/roles/').catch(() => ({ data: [] })),
    ]);
    items.value = Array.isArray(users.data) ? users.data : users.data.results || [];
    roles.value = Array.isArray(roleData.data) ? roleData.data : roleData.data.results || [];
    lastSync.value = new Date().toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', hour12: true });
    const admin = roles.value.find((role) => role.nombre.toUpperCase() === 'ADMIN');
    if (!editing.value && admin) form.rol_id = admin.id;
  } catch (error) {
    console.error(error);
    items.value = [];
    loadError.value = error.response?.status === 401
      ? 'Tu sesión no está autenticada.'
      : 'No fue posible cargar los usuarios.';
  } finally {
    loading.value = false;
  }
}

function reset() {
  Object.assign(form, {
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    password: '',
    rol_id: roles.value.find((role) => role.nombre.toUpperCase() === 'ADMIN')?.id || null,
    activo: true,
    permisos: { dashboard: true, dispositivos: true, sims: true, usuarios: true },
  });
  editing.value = false;
  editingId.value = null;
  saveError.value = '';
}

function edit(item) {
  editing.value = true;
  editingId.value = item.id;
  saveError.value = '';
  Object.assign(form, {
    username: item.username,
    email: item.email,
    first_name: item.first_name || '',
    last_name: item.last_name || '',
    password: '',
    rol_id: item.rol?.id || null,
    activo: item.activo,
    permisos: {
      dashboard: false,
      dispositivos: false,
      sims: false,
      usuarios: false,
      ...(item.permisos || {}),
    },
  });
}

function visiblePermissions(item) {
  return permissionOptions.filter((permission) => item.permisos?.[permission.key] === true);
}

async function save() {
  const isEditingSelf = editingId.value === auth.user?.id;
  const removingOwnUsersAccess = isEditingSelf && !form.permisos.usuarios;
  if (removingOwnUsersAccess && !window.confirm('Te estás quitando el acceso a Usuarios a ti mismo. ¿Seguro?')) return;

  loading.value = true;
  saveError.value = '';
  try {
    const payload = {
      username: form.username,
      email: form.email,
      first_name: form.first_name,
      last_name: form.last_name,
      activo: form.activo,
      permisos: { ...form.permisos },
    };
    if (form.password) payload.password = form.password;

    if (editingId.value) await api.patch(`/usuarios/${editingId.value}/`, payload);
    else await api.post('/usuarios/', payload);

    if (isEditingSelf) await auth.fetchCurrentUser();
    reset();
    if (!removingOwnUsersAccess) await load();
  } catch (error) {
    console.error(error.response?.data || error);
    saveError.value = JSON.stringify(error.response?.data || 'Error al guardar');
  } finally {
    loading.value = false;
  }
}

async function remove(item) {
  if (!window.confirm(`¿Eliminar a ${item.email || item.username}? Esta acción no se puede deshacer.`)) return;
  try {
    await api.delete(`/usuarios/${item.id}/`);
    await load();
  } catch (error) {
    console.error(error);
    window.alert('No se pudo eliminar el usuario.');
  }
}

onMounted(load);
</script>
<style scoped>
.crud-page{width:100%}.page-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px}.eyebrow{text-transform:uppercase;letter-spacing:.12em;font-size:.7rem;color:#64748b;margin:0 0 6px}h2{margin:0;font-size:2rem}.primary-btn,.secondary-btn,.edit-btn,.delete-btn{border:0;border-radius:10px;padding:10px 14px;font-weight:700}.primary-btn{background:#1E9B48;color:#fff}.secondary-btn{background:#fff;border:1px solid #cbd5e1}.grid-layout{display:grid;grid-template-columns:1fr 1.2fr;gap:20px}.panel{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:20px}.panel h3{margin-top:0}.panel form{display:flex;flex-direction:column;gap:12px}input,select{width:100%;padding:.8rem;border:1px solid #dbe2ed;border-radius:10px}.actions-row,.row-actions{display:flex;gap:10px;align-items:center}.list{display:flex;flex-direction:column;gap:10px;margin-top:12px}.item-row{display:flex;justify-content:space-between;gap:12px;padding:12px;background:#f8fafc;border-radius:10px}.item-row small{display:block;color:#64748b}.edit-btn{background:#e0f2fe;color:#167A39}.delete-btn{background:#fee2e2;color:#b91c1c}@media(max-width:840px){.grid-layout{grid-template-columns:1fr}}

.crud-page { gap: 18px; padding: 24px; border: 1px solid #DCE3EE; border-radius: 12px; background: linear-gradient(180deg, #F4F6FA, #EDF0F7); }
.page-header { margin-bottom: 0; padding-bottom: 16px; border-bottom: 1px solid #DCE3EE; }
.page-header h2 { color: #121A2B; font-size: 2rem; font-weight: 800; letter-spacing: -0.02em; }
.eyebrow { color: #1E9B48; font-weight: 800; font-size: 0.85rem; }
.primary-btn { background: #1E9B48; border-radius: 7px; box-shadow: 0 7px 14px rgba(0, 127, 95, 0.18); }
.primary-btn:hover { background: #167A39; }
.grid-layout { gap: 16px; }
.panel { padding: 20px; border-color: #DCE3EE; border-radius: 10px; box-shadow: 0 6px 18px rgba(0, 67, 49, 0.05); }
.panel h3 { color: #121A2B; }
.panel form input:focus, .panel form select:focus, .panel > input:focus { border-color: #008f68; box-shadow: 0 0 0 0.18rem rgba(0,143,104,0.12); outline: 0; }
.panel input, .panel select { border-color: #DCE3EE; border-radius: 7px; background: #F4F6FA; }
.item-row { border: 1px solid #DCE3EE; border-radius: 8px; background: #F4F6FA; }
.edit-btn { background: #E6F6EC; color: #167A39; border-radius: 7px; }
.delete-btn { border-radius: 7px; }
.save-error { margin: 0; color: #b42318; font-size: 0.8rem; }
.user-row-info { min-width: 0; }
.permission-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 9px; }
.permission-list span { padding: 4px 8px; border: 1px solid #C7D3E8; border-radius: 4px; background: #E6F6EC; color: #167A39; font-size: 0.68rem; font-weight: 800; }
.role-lock { display: flex; flex-direction: column; gap: 5px; padding: 11px 12px; border: 1px solid #DCE3EE; border-radius: 7px; background: #F4F6FA; }
.role-lock span, .field-label { color: #5B6B82; font-size: 0.72rem; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; }
.role-lock strong { color: #121A2B; }
.permissions { display: flex; flex-direction: column; gap: 8px; padding: 12px; border: 1px solid #DCE3EE; border-radius: 7px; background: #fff; }
.permissions .field-label { margin-bottom: 2px; }
.permissions label { display: flex; align-items: center; gap: 8px; color: #121A2B; font-size: 0.88rem; }
.permissions input { width: auto; }
.topbar-actions { display: flex; align-items: center; gap: 12px; }
.sync-state { display: inline-flex; align-items: center; gap: 7px; color: #15803d; font-size: 0.78rem; font-weight: 700; white-space: nowrap; padding: 8px 10px; border: 1px solid #DCE3EE; border-radius: 7px; background: #F4F6FA; }
.sync-state i { width: 8px; height: 8px; display: inline-block; border-radius: 50%; background: #22c55e; box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.12); }
.sync-state.syncing i { background: #f59e0b; }
.sync-state.failed { color: #dc2626; }
.sync-state.failed i { background: #ef4444; }
.users-heading { display: flex; align-items: center; gap: 14px; }
.users-title-icon, .panel-icon { display: grid; place-items: center; flex: 0 0 auto; width: 42px; height: 42px; border-radius: 10px; color: #1E9B48; background: #E6F6EC; font-size: 1.35rem; }
.users-heading h2 { margin: 0; }
.page-caption { margin: 5px 0 0; color: #5B6B82; font-size: 0.78rem; }
.panel-heading { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.panel-heading .panel-icon { width: 36px; height: 36px; font-size: 1.1rem; }
.panel-heading h3 { margin: 0; }
.panel-intro { margin: 4px 0 0; color: #5B6B82; font-size: 0.76rem; }
.user-count { display: grid; place-items: center; min-width: 24px; height: 24px; margin-left: auto; padding: 0 7px; border-radius: 999px; color: #1E9B48; background: #E6F6EC; font-size: 0.76rem; font-weight: 800; }
.form-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.user-search { margin-bottom: 12px; }
.user-row-info { flex: 1; min-width: 0; }
.user-avatar { display: grid; place-items: center; flex: 0 0 auto; width: 38px; height: 38px; border-radius: 10px; color: #1E9B48; background: #E6F6EC; font-weight: 800; }
.user-row-info strong { color: #121A2B; }
.user-row-info small { color: #5B6B82; }
.user-status { padding: 6px 9px; border-radius: 5px; font-size: 0.72rem; font-weight: 800; white-space: nowrap; }
.user-status.active { color: #1E9B48; background: #E6F6EC; }
.user-status.inactive { color: #b42318; background: #fff0ee; }
.users-list-panel .item-row { align-items: center; padding: 13px; }
.users-list-panel .edit-btn, .users-list-panel .delete-btn { width: 30px; padding: 8px 0; font-size: 1rem; line-height: 1; }
.users-list-panel .edit-btn { background: #E6F6EC; color: #167A39; }
.users-list-panel .delete-btn { background: #fff0ee; color: #b42318; }

@media (max-width: 640px) {
  .crud-page { padding: 16px 12px; }
  .page-header h2 { font-size: 1.55rem; }
  .page-header, .item-row { align-items: flex-start; flex-direction: column; }
  .row-actions { width: 100%; flex-wrap: wrap; }
  .form-columns { grid-template-columns: 1fr; }
  .users-list-panel .item-row { align-items: flex-start; flex-wrap: wrap; }
  .user-status { margin-left: 50px; }
}
</style>