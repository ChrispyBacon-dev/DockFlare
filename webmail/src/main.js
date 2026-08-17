import { createApp } from 'vue';
import { createPinia } from 'pinia';
import router from './router';
import App from './App.vue';
import './assets/styles/main.css';
// Apply dark mode before mount to avoid flash
// Priority: explicit user preference → system preference
const _storedTheme = localStorage.getItem('theme');
const _prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
if (_storedTheme === 'dark' || (_storedTheme === null && _prefersDark)) {
    document.documentElement.classList.add('dark');
}
const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount('#app');
//# sourceMappingURL=main.js.map