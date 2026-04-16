import { createApp } from 'vue';
import { createPinia } from 'pinia';
import router from './router';
import App from './App.vue';
import './assets/styles/main.css';
// Apply dark mode before mount to avoid flash
if (localStorage.getItem('theme') === 'dark') {
    document.documentElement.classList.add('dark');
}
const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount('#app');
//# sourceMappingURL=main.js.map