// Punto de entrada: registra Pinia, el router y los estilos globales antes de montar Vue.
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import './styles.css';
import 'bootstrap/dist/css/bootstrap.min.css';

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount('#app');
