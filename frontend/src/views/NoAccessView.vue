<template>
  <section class="no-access" role="status">
    <span class="no-access-icon" aria-hidden="true">⊘</span>
    <p class="eyebrow">Acceso restringido</p>
    <h1>No tienes permisos asignados</h1>
    <p>Solicita a un administrador que habilite el acceso a los módulos que necesitas.</p>
  </section>
</template>

<style scoped>
.no-access {
  display: grid;
  min-height: 60vh;
  align-content: center;
  justify-items: center;
  padding: 32px 20px;
  text-align: center;
}

.no-access-icon {
  display: grid;
  width: 54px;
  height: 54px;
  place-items: center;
  margin-bottom: 18px;
  border-radius: 50%;
  background: #fff0ee;
  color: #b42318;
  font-size: 1.8rem;
}

.eyebrow {
  margin: 0 0 8px;
  color: #1e9b48;
  font-size: 0.76rem;
  font-weight: 800;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  color: #121a2b;
  font-size: 1.6rem;
}

.no-access p:last-child {
  max-width: 420px;
  margin: 10px 0 0;
  color: #5b6b82;
  line-height: 1.5;
}
</style>