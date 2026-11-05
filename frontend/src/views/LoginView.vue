<template>
  <div class="login-shell">
    <div class="login-panel">
      <section class="login-aside">
        <div class="aside-top">
          <span class="aside-kicker">Sistema interno</span>
          <div class="aside-line"></div>
        </div>

        <div class="aside-copy">
          <div class="logo-plate">
            <img class="brand-logo" src="/images/Logo1.jpg" alt="Jamnex" />
          </div>
          <h1>JAMNEX</h1>
          <p>Monitorea dispositivos y líneas móviles desde un solo lugar.</p>
          <ul class="aside-features">
            <li>Dispositivos en tiempo real</li>
            <li>Consumo de datos por línea</li>
            <li>Reportes en Excel</li>
          </ul>
        </div>

        <small class="aside-footer">© 2026 Jamnex</small>
      </section>

      <section class="login-content">
        <div class="welcome-copy">
          <span class="form-kicker">Acceso</span>
          <h2>Bienvenido</h2>
          <p>Ingresa para continuar al panel de control.</p>
        </div>

        <form class="login-form" @submit.prevent="submitLogin">
          <div class="mb-3">
            <label class="form-label" for="login-identifier">Usuario</label>
            <input id="login-identifier" v-model="identifier" type="text" class="form-control" placeholder="Ingresa tu correo electrónico" autocomplete="username" autofocus required />
          </div>

          <div class="mb-3">
            <div class="password-label-row">
              <label class="form-label" for="login-password">Contraseña</label>
              <button type="button" class="password-toggle" @click="showPassword = !showPassword">
                {{ showPassword ? 'Ocultar' : 'Mostrar' }}
              </button>
            </div>
            <input id="login-password" v-model="password" :type="showPassword ? 'text' : 'password'" class="form-control" placeholder="Escribe tu contraseña" autocomplete="current-password" required />
          </div>

          <div v-if="errorMessage" class="alert alert-danger py-2 mb-3">{{ errorMessage }}</div>

          <button type="submit" class="btn btn-primary w-100" :disabled="loading">
            <span>{{ loading ? 'Validando acceso...' : 'Iniciar sesión' }}</span>
          </button>
        </form>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import api from '../services/api';
import { useAuthStore } from '../stores/auth';

const identifier = ref('');
const password = ref('');
const showPassword = ref(false);
const errorMessage = ref('');
const loading = ref(false);
const router = useRouter();
const auth = useAuthStore();

async function submitLogin() {
  loading.value = true;
  errorMessage.value = '';

  try {
    const response = await api.post('/auth/login/', {
      identifier: identifier.value.trim(),
      password: password.value,
    });

    auth.setAuth(response.data);
    router.push('/');
  } catch (error) {
    errorMessage.value = 'Credenciales inválidas o servicio no disponible.';
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
/* ---------- Fondo de la página ---------- */
.login-shell {
  width: 100%;
  margin: 0 auto;
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 28px 18px;
  background:
    radial-gradient(circle at 15% 20%, rgba(52, 201, 143, 0.22), transparent 45%),
    radial-gradient(circle at 85% 85%, rgba(27, 42, 68, 0.14), transparent 45%),
    #f4f7f6;
}

.login-panel {
  width: min(100%, 940px);
  display: grid;
  grid-template-columns: 0.86fr 1.14fr;
  overflow: hidden;
  background: #fff;
  border: 0;
  border-radius: 20px;
  box-shadow: 0 30px 70px rgba(10, 18, 28, 0.18);
}

/* ---------- Lado oscuro ---------- */
.login-aside {
  position: relative;
  display: flex;
  min-height: 620px;
  flex-direction: column;
  justify-content: space-between;
  padding: 40px 36px;
  overflow: hidden;
  color: #fff;
  background: linear-gradient(155deg, #1E9B48 0%, #167A39 30%, #1B2A44 78%, #0A121C 100%);
}

.login-aside::after {
  content: '';
  position: absolute;
  right: -90px;
  bottom: -90px;
  width: 280px;
  height: 280px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.06);
}

.login-aside > * {
  position: relative;
  z-index: 1;
}

.aside-top {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.aside-kicker,
.form-kicker {
  color: #a7e2cf;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.aside-line {
  width: 48px;
  height: 4px;
  border-radius: 2px;
  background: #34C98F;
}

.aside-copy {
  margin-top: auto;
  padding: 0 0 36px;
}

.aside-copy h1 {
  margin: 0 0 12px;
  font-size: 2.8rem;
  font-weight: 900;
  letter-spacing: 0.04em;
}

.aside-copy p {
  max-width: 280px;
  margin: 0;
  color: #d7f3e9;
  line-height: 1.6;
}

.aside-features {
  margin: 22px 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 10px;
}

.aside-features li {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #e4f7ee;
  font-size: 0.88rem;
}

.aside-features li::before {
  content: '✓';
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.16);
  color: #a7f0cf;
  font-size: 0.7rem;
  font-weight: 800;
}

.aside-footer {
  color: #b7e4d4;
  font-size: 0.72rem;
}

/* ---------- Lado blanco (logo + formulario) ---------- */
.login-content {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 48px 58px;
}

.logo-plate {
  width: 100%;
  max-width: 270px;
  margin: 0 0 28px;
  padding: 14px 18px;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 14px 30px rgba(0, 0, 0, 0.28);
}

.brand-logo {
  display: block;
  width: 100%;
  height: auto;
  max-height: 150px;
  object-fit: contain;
  object-position: center;
}

.welcome-copy {
  margin-bottom: 26px;
}

.form-kicker {
  color: #1E9B48;
}

.welcome-copy h2 {
  margin: 10px 0 8px;
  color: #121A2B;
  font-size: 2rem;
  font-weight: 800;
}

.welcome-copy p {
  margin: 0;
  color: #64756f;
}

/* ---------- Formulario ---------- */
.login-form .form-label {
  font-size: 0.82rem;
  font-weight: 700;
  color: #334155;
}

.login-form .form-control {
  padding: 0.82rem 0.9rem;
  border-radius: 9px;
  border: 1px solid #d5e2dc;
  background: #f7faf9;
  transition: all 0.18s ease;
}

.login-form .form-control:focus {
  background: #fff;
  border-color: #1E9B48;
  box-shadow: 0 0 0 0.2rem rgba(30, 155, 72, 0.14);
}

.password-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.password-toggle {
  margin-bottom: 0.5rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: #1E9B48;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
}

.password-toggle:hover,
.password-toggle:focus-visible {
  color: #1B2A44;
  text-decoration: underline;
}

.btn-primary {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 6px;
  padding: 0.85rem 1rem;
  border: 0;
  border-radius: 9px;
  font-weight: 700;
  background: #1E9B48;
  box-shadow: 0 8px 16px rgba(30, 155, 72, 0.18);
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}

.btn-primary:hover:not(:disabled),
.btn-primary:focus {
  background: #167A39;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 22px rgba(30, 155, 72, 0.28);
}

/* ---------- Móvil ---------- */
@media (max-width: 700px) {
  .login-panel {
    grid-template-columns: 1fr;
  }

  .login-aside {
    min-height: 0;
    padding: 26px 22px;
  }

  .aside-copy {
    padding: 22px 0 10px;
  }

  .aside-copy h1 { font-size: 2rem; }
  .aside-copy p,
  .aside-features { display: none; }

  .login-content { padding: 30px 22px 28px; }
  .logo-plate { max-width: 200px; margin-bottom: 16px; }
}
</style>