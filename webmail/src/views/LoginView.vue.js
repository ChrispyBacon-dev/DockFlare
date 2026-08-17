/// <reference types="../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { ref, onMounted, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import { useAuth } from '../composables/useAuth';
import { useMailStore } from '../stores/mail';
import { authApi } from '../api/auth';
import { Sun, Moon } from 'lucide-vue-next';
const route = useRoute();
const { login } = useAuth();
const store = useMailStore();
const email = ref('');
const password = ref('');
const error = ref('');
const loading = ref(false);
const canvasRef = ref(null);
const taglineText = ref('Manage OAuth/OIDC providers directly in DockFlare.');
const taglineVisible = ref(true);
let animFrameId = 0;
const taglineTimers = [];
const getMasterUrl = async () => {
    let url = import.meta.env.VITE_MASTER_URL;
    if (!url) {
        try {
            const cfg = await fetch('/config.json').then(r => r.json());
            url = cfg.masterUrl;
        }
        catch { }
    }
    return url || window.location.origin.replace('mail.', '');
};
const handleLogin = async () => {
    error.value = '';
    loading.value = true;
    try {
        const data = await authApi.loginWithPassword(email.value, password.value);
        if (data.success && data.token) {
            login(data.token);
        }
        else {
            error.value = data.error || 'Invalid email or password';
        }
    }
    catch {
        error.value = 'Connection error. Please try again.';
    }
    finally {
        loading.value = false;
    }
};
const redirectToMaster = async () => {
    const masterUrl = await getMasterUrl();
    window.location.href = `${masterUrl}/email/sso/callback?return_to=${window.location.hostname}`;
};
function startTagline() {
    const lines = [
        'Manage OAuth/OIDC providers directly in DockFlare.',
        'Zone Default Policies protect all subdomains automatically.',
        'Security-audited with CSRF, XSS, and injection protection.',
        'Deploy agents across your multi-server infrastructure.',
        "Now you're thinking with Zero Trust security.",
    ];
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)
        return;
    let idx = 0;
    const DISPLAY_MS = 5500;
    const FADE_MS = 2800;
    function cycle() {
        taglineVisible.value = false;
        const t1 = setTimeout(() => {
            idx = (idx + 1) % lines.length;
            taglineText.value = lines[idx];
            taglineVisible.value = true;
            const t2 = setTimeout(cycle, DISPLAY_MS);
            taglineTimers.push(t2);
        }, FADE_MS);
        taglineTimers.push(t1);
    }
    const t0 = setTimeout(cycle, DISPLAY_MS);
    taglineTimers.push(t0);
}
function startCanvas() {
    const canvas = canvasRef.value;
    if (!canvas)
        return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches)
        return;
    const ctx = canvas.getContext('2d');
    let W = 0, H = 0;
    const events = [];
    function isDark() {
        return document.documentElement.classList.contains('dark');
    }
    function resize() {
        W = canvas.width = canvas.parentElement.clientWidth;
        H = canvas.height = canvas.parentElement.clientHeight;
    }
    window.addEventListener('resize', resize);
    resize();
    const dockerWhite = new Image();
    dockerWhite.src = '/envelope-white.svg';
    const dockerBlue = new Image();
    dockerBlue.src = '/envelope-blue.svg';
    function easeIn5(t) { return t * t * t * t * t; }
    function easeOut5(t) { return 1 - Math.pow(1 - t, 5); }
    const RX = 11, RY = 27;
    const LOGO_R = 165;
    function safePt(pad) {
        const cx = W / 2, cy = H / 2;
        let x, y;
        do {
            x = pad + Math.random() * (W - pad * 2);
            y = pad + Math.random() * (H - pad * 2);
        } while ((x - cx) ** 2 + (y - cy) ** 2 < LOGO_R * LOGO_R);
        return { x, y };
    }
    class PortalEvent {
        sx;
        sy;
        ex;
        ey;
        aIn;
        aOut;
        phase = 0;
        timer = 0;
        bScale = 0;
        oScale = 0;
        prog = 0;
        OPEN_MS = 533;
        READY_MS = 750;
        TRAVEL_MS = 1000;
        TRANSIT_MS = 300;
        PRECLOSE_MS = 667;
        CLOSE_MS = 467;
        isDead = false;
        constructor() {
            const pad = 100;
            const s = safePt(pad), e = safePt(pad);
            this.sx = s.x;
            this.sy = s.y;
            this.ex = e.x;
            this.ey = e.y;
            this.aIn = Math.PI * (0.3 + Math.random() * 0.4);
            this.aOut = Math.PI * (0.3 + Math.random() * 0.4);
        }
        update(delta) {
            this.timer += delta;
            switch (this.phase) {
                case 0:
                    this.bScale = Math.min(1, this.timer / this.OPEN_MS);
                    if (this.bScale === 1) {
                        this.phase = 1;
                        this.timer = 0;
                    }
                    break;
                case 1:
                    this.oScale = Math.min(1, this.timer / this.OPEN_MS);
                    if (this.oScale === 1) {
                        this.phase = 2;
                        this.timer = 0;
                    }
                    break;
                case 2:
                    if (this.timer >= this.READY_MS) {
                        this.phase = 3;
                        this.timer = 0;
                    }
                    break;
                case 3:
                    this.prog = Math.min(1, this.timer / this.TRAVEL_MS);
                    if (this.prog === 1) {
                        this.phase = 4;
                        this.timer = 0;
                    }
                    break;
                case 4:
                    if (this.timer >= this.TRANSIT_MS) {
                        this.phase = 5;
                        this.timer = 0;
                    }
                    break;
                case 5:
                    this.prog = Math.min(1, this.timer / this.TRAVEL_MS);
                    if (this.prog === 1) {
                        this.phase = 6;
                        this.timer = 0;
                    }
                    break;
                case 6:
                    if (this.timer >= this.PRECLOSE_MS) {
                        this.phase = 7;
                        this.timer = 0;
                    }
                    break;
                case 7: {
                    const t6 = this.timer / this.CLOSE_MS;
                    this.bScale = Math.max(0, 1 - t6);
                    this.oScale = Math.max(0, 1 - t6);
                    if (this.bScale === 0)
                        this.isDead = true;
                    break;
                }
            }
        }
        readyPulse() {
            if (this.phase !== 2)
                return 1;
            return 1 + 0.18 * Math.sin((this.timer / this.READY_MS) * Math.PI);
        }
        drawPortal(x, y, angle, scale, type, pulse) {
            if (scale <= 0)
                return;
            ctx.save();
            ctx.translate(x, y);
            ctx.rotate(angle + Math.PI / 2);
            ctx.scale(1, scale);
            const ga = (type === 'blue' ? 0.22 : 0.20) * pulse;
            const grd = ctx.createRadialGradient(0, 0, 0, 0, 0, RY);
            if (type === 'blue') {
                grd.addColorStop(0, `rgba(59,130,246,${ga})`);
                grd.addColorStop(1, 'rgba(59,130,246,0)');
            }
            else {
                grd.addColorStop(0, `rgba(249,115,22,${ga})`);
                grd.addColorStop(1, 'rgba(249,115,22,0)');
            }
            ctx.fillStyle = grd;
            ctx.beginPath();
            ctx.ellipse(0, 0, RX, RY, 0, 0, Math.PI * 2);
            ctx.fill();
            const a = Math.min(1, (isDark() ? 0.70 : 0.75) * pulse);
            const glowColor = type === 'blue' ? '96,165,250' : '249,115,22';
            ctx.lineWidth = 2.5;
            ctx.shadowBlur = 18;
            ctx.shadowColor = `rgba(${glowColor},${a * 0.9})`;
            ctx.beginPath();
            ctx.ellipse(0, 0, RX, RY, 0, 0, Math.PI * 2);
            ctx.strokeStyle = `rgba(${glowColor},${a})`;
            ctx.stroke();
            ctx.shadowBlur = 0;
            ctx.restore();
        }
        drawContainer(px, py, angle, alpha) {
            const img = isDark() ? dockerBlue : dockerWhite;
            if (!img.complete || !img.naturalWidth)
                return;
            const SIZE = 40;
            ctx.save();
            ctx.globalAlpha = Math.max(0, Math.min(1, alpha));
            ctx.translate(px, py);
            ctx.rotate(angle);
            ctx.shadowColor = isDark() ? 'rgba(36,150,237,0.45)' : 'rgba(36,150,237,0.55)';
            ctx.shadowBlur = 10;
            ctx.drawImage(img, -SIZE / 2, -SIZE / 2, SIZE, SIZE);
            ctx.restore();
        }
        wiggle(x, y, angle, prog, entering) {
            const AMP = 5, FREQ = 2.0;
            let fade;
            if (entering) {
                const rampUp = Math.min(1, prog / 0.20);
                const rampDown = Math.min(1, (1 - prog) / 0.28);
                fade = rampUp * rampDown;
            }
            else {
                fade = Math.min(1, prog / 0.25);
            }
            const wave = Math.sin(prog * FREQ * Math.PI * 2);
            const dwave = Math.cos(prog * FREQ * Math.PI * 2);
            const offset = AMP * wave * fade;
            const tilt = 0.30 * dwave * fade;
            const perp = angle + Math.PI / 2;
            return { wx: x + Math.cos(perp) * offset, wy: y + Math.sin(perp) * offset, tilt };
        }
        draw() {
            const pulse = this.readyPulse();
            this.drawPortal(this.sx, this.sy, this.aIn, this.bScale, 'blue', pulse);
            if (this.phase >= 1)
                this.drawPortal(this.ex, this.ey, this.aOut, this.oScale, 'orange', pulse);
            if (this.phase === 3) {
                const dist3 = 145 * (1 - easeIn5(this.prog));
                const alpha3 = this.prog < 0.15 ? this.prog / 0.15 : 1 - Math.max(0, (this.prog - 0.78) / 0.22);
                const tAngle3 = this.aIn + Math.PI / 2;
                const w3 = this.wiggle(this.sx + Math.sin(this.aIn) * dist3, this.sy - Math.cos(this.aIn) * dist3, tAngle3, this.prog, true);
                this.drawContainer(w3.wx, w3.wy, tAngle3 + w3.tilt + Math.PI, alpha3);
            }
            if (this.phase === 5) {
                const dist5 = 145 * easeOut5(this.prog);
                const alpha5 = this.prog < 0.12 ? this.prog / 0.12 : 1 - Math.max(0, (this.prog - 0.80) / 0.20);
                const tAngle5 = this.aOut + Math.PI / 2;
                const w5 = this.wiggle(this.ex - Math.sin(this.aOut) * dist5, this.ey + Math.cos(this.aOut) * dist5, tAngle5, this.prog, false);
                this.drawContainer(w5.wx, w5.wy, tAngle5 + w5.tilt + Math.PI, alpha5);
            }
        }
    }
    let nextSpawn = 0;
    const SPAWN_PAUSE_MS = 3500;
    let lastTime = 0;
    function animate(now) {
        const delta = lastTime ? Math.min(now - lastTime, 50) : 16.67;
        lastTime = now;
        ctx.fillStyle = isDark() ? 'rgba(238,242,255,0.32)' : 'rgba(13,13,26,0.32)';
        ctx.fillRect(0, 0, W, H);
        for (let i = events.length - 1; i >= 0; i--) {
            events[i].update(delta);
            events[i].draw();
            if (events[i].isDead) {
                events.splice(i, 1);
                nextSpawn = now + SPAWN_PAUSE_MS;
            }
        }
        if (events.length < 1 && now >= nextSpawn) {
            events.push(new PortalEvent());
            nextSpawn = Infinity;
        }
        animFrameId = requestAnimationFrame(animate);
    }
    animFrameId = requestAnimationFrame(animate);
}
onMounted(() => {
    const token = route.query.token;
    if (token) {
        login(token);
    }
    startTagline();
    startCanvas();
});
onUnmounted(() => {
    if (animFrameId)
        cancelAnimationFrame(animFrameId);
    taglineTimers.forEach(clearTimeout);
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "df-login-root" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.store.toggleTheme();
        } },
    type: "button",
    ...{ class: "df-theme-btn" },
    title: (__VLS_ctx.store.isDark ? 'Switch to light mode' : 'Switch to dark mode'),
});
if (__VLS_ctx.store.isDark) {
    const __VLS_0 = {}.Sun;
    /** @type {[typeof __VLS_components.Sun, ]} */ ;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
        ...{ class: "size-5" },
    }));
    const __VLS_2 = __VLS_1({
        ...{ class: "size-5" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
}
else {
    const __VLS_4 = {}.Moon;
    /** @type {[typeof __VLS_components.Moon, ]} */ ;
    // @ts-ignore
    const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
        ...{ class: "size-5" },
    }));
    const __VLS_6 = __VLS_5({
        ...{ class: "size-5" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_5));
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "df-panel-left" },
    'aria-hidden': "true",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "df-aurora" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "df-aurora-blob" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "df-aurora-blob" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "df-aurora-blob" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.canvas, __VLS_intrinsicElements.canvas)({
    ref: "canvasRef",
    ...{ class: "df-portal-canvas" },
});
/** @type {typeof __VLS_ctx.canvasRef} */ ;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "df-panel-left-content" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.img)({
    src: (__VLS_ctx.store.isDark ? '/logo-light.svg' : '/logo-dark.svg'),
    alt: "",
    ...{ class: "df-portal-logo-center" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "df-tagline" },
    ...{ class: ({ 'df-tagline-hidden': !__VLS_ctx.taglineVisible }) },
});
(__VLS_ctx.taglineText);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "df-panel-right" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "df-form-container" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.img)({
    src: (__VLS_ctx.store.isDark ? '/logo-dark.svg' : '/logo-light.svg'),
    alt: "DockFlare",
    ...{ class: "df-mobile-logo" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h1, __VLS_intrinsicElements.h1)({
    ...{ class: "df-form-heading" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
    ...{ class: "df-form-sub" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.form, __VLS_intrinsicElements.form)({
    ...{ onSubmit: (__VLS_ctx.handleLogin) },
    ...{ class: "df-form-fields" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.input)({
    type: "email",
    placeholder: "you@example.com",
    required: true,
    ...{ class: "df-input" },
});
(__VLS_ctx.email);
__VLS_asFunctionalElement(__VLS_intrinsicElements.input)({
    type: "password",
    placeholder: "Password",
    required: true,
    ...{ class: "df-input" },
});
(__VLS_ctx.password);
if (__VLS_ctx.error) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "df-error" },
    });
    (__VLS_ctx.error);
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    type: "submit",
    ...{ class: "df-btn-primary" },
    disabled: (__VLS_ctx.loading),
});
(__VLS_ctx.loading ? 'Signing in…' : 'Sign in');
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "df-or" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (__VLS_ctx.redirectToMaster) },
    ...{ class: "df-btn-outline" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "df-btn-outline-label" },
});
/** @type {__VLS_StyleScopedClasses['df-login-root']} */ ;
/** @type {__VLS_StyleScopedClasses['df-theme-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['size-5']} */ ;
/** @type {__VLS_StyleScopedClasses['size-5']} */ ;
/** @type {__VLS_StyleScopedClasses['df-panel-left']} */ ;
/** @type {__VLS_StyleScopedClasses['df-aurora']} */ ;
/** @type {__VLS_StyleScopedClasses['df-aurora-blob']} */ ;
/** @type {__VLS_StyleScopedClasses['df-aurora-blob']} */ ;
/** @type {__VLS_StyleScopedClasses['df-aurora-blob']} */ ;
/** @type {__VLS_StyleScopedClasses['df-portal-canvas']} */ ;
/** @type {__VLS_StyleScopedClasses['df-panel-left-content']} */ ;
/** @type {__VLS_StyleScopedClasses['df-portal-logo-center']} */ ;
/** @type {__VLS_StyleScopedClasses['df-tagline']} */ ;
/** @type {__VLS_StyleScopedClasses['df-panel-right']} */ ;
/** @type {__VLS_StyleScopedClasses['df-form-container']} */ ;
/** @type {__VLS_StyleScopedClasses['df-mobile-logo']} */ ;
/** @type {__VLS_StyleScopedClasses['df-form-heading']} */ ;
/** @type {__VLS_StyleScopedClasses['df-form-sub']} */ ;
/** @type {__VLS_StyleScopedClasses['df-form-fields']} */ ;
/** @type {__VLS_StyleScopedClasses['df-input']} */ ;
/** @type {__VLS_StyleScopedClasses['df-input']} */ ;
/** @type {__VLS_StyleScopedClasses['df-error']} */ ;
/** @type {__VLS_StyleScopedClasses['df-btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['df-or']} */ ;
/** @type {__VLS_StyleScopedClasses['df-btn-outline']} */ ;
/** @type {__VLS_StyleScopedClasses['df-btn-outline-label']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            Sun: Sun,
            Moon: Moon,
            store: store,
            email: email,
            password: password,
            error: error,
            loading: loading,
            canvasRef: canvasRef,
            taglineText: taglineText,
            taglineVisible: taglineVisible,
            handleLogin: handleLogin,
            redirectToMaster: redirectToMaster,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=LoginView.vue.js.map