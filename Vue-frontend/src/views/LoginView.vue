<template>
  <div class="login-page">
    <!-- 动态柔和背景 (Blobs) -->
    <div class="bg-elements">
      <div class="blob blob-1"></div>
      <div class="blob blob-2"></div>
      <div class="blob blob-3"></div>
      <div class="bg-grid"></div>
    </div>

    <!-- ═══════ 左侧：沉浸展示区 ═══════ -->
    <aside class="showcase">
      <!-- 品牌 -->
      <div class="showcase__brand anim" style="--d:.0s">
        <img src="/icon.png" alt="AURA" class="showcase__icon" />
        <div>
          <h1 class="showcase__title">AURA 智学</h1>
          <p class="showcase__sub">AI 多智能体个性化学习系统</p>
        </div>
      </div>

      <!-- 功能 GIF 卡片轮播 (Liquid Glass) -->
      <div class="showcase__features anim" style="--d:.1s">
        <transition name="card-swap" mode="out-in">
          <div :key="activeFeature" class="glass-card glass-card--feature">
            <div class="glass-card__frame">
              <img :src="features[activeFeature].gif" :alt="features[activeFeature].title" class="glass-card__gif" />
            </div>
            <div class="glass-card__info">
              <span class="glass-card__tag" :style="{ background: features[activeFeature].color }">{{ features[activeFeature].tag }}</span>
              <h3>{{ features[activeFeature].title }}</h3>
              <p>{{ features[activeFeature].desc }}</p>
            </div>
          </div>
        </transition>

        <!-- 指示器 -->
        <div class="showcase__dots">
          <button
            v-for="(_, i) in features" :key="i"
            class="dot" :class="{ 'dot--active': activeFeature === i }"
            :style="activeFeature === i ? { background: features[activeFeature].color } : {}"
            @click="activeFeature = i"
          ></button>
        </div>
      </div>

      <p class="showcase__footer anim" style="--d:.2s">多智能体协作 · 个性化学习资源 · 知识库与图谱驱动</p>
    </aside>

    <!-- ═══════ 右侧：登录表单 ═══════ -->
    <main class="form-area">
      <div class="form-wrap">
        <!-- 移动端 Logo -->
        <div class="mobile-logo anim" style="--d:.0s">
          <img src="/icon.png" alt="AURA" class="w-12 h-12 rounded-xl shadow-lg" />
          <span class="font-extrabold text-slate-800 text-xl tracking-tight">AURA 智学</span>
        </div>

        <div class="form-glass anim" style="--d:.1s">
          <div class="form-header">
            <h2>欢迎回来</h2>
            <p>登录你的学习空间，继续探索</p>
          </div>

          <form @submit.prevent="handleLogin" class="login-form">
            <div class="field">
              <label>账号</label>
              <div class="input-glass">
                <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                <input v-model="form.loginName" type="text" placeholder="请输入登录账号" autocomplete="username" required />
              </div>
            </div>

            <div class="field">
              <label>密码</label>
              <div class="input-glass">
                <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                <input v-model="form.password" type="password" placeholder="请输入密码" autocomplete="current-password" required />
              </div>
            </div>

            <div v-if="expiredNotice" class="notice notice--warn">{{ expiredNotice }}</div>
            <div v-if="error" class="notice notice--error">{{ error }}</div>

            <button type="submit" class="login-btn" :disabled="loading">
              <span v-if="loading" class="login-btn__spin"></span>
              <span>{{ loading ? '登录中...' : '登 录' }}</span>
            </button>
          </form>

          <div class="form-footer">
            还没有账号？
            <router-link to="/register">立即注册</router-link>
          </div>
        </div>

        <div class="demo-badge anim" style="--d:.2s">
          <span class="demo-pulse"></span>
          登录以体验完整功能
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const form = ref({ loginName: '', password: '' })
const loading = ref(false)
const error = ref('')
const expiredNotice = ref('')
const activeFeature = ref(0)
let featureTimer: ReturnType<typeof setInterval>

const features = [
  { title: '图文学习资源', desc: 'AI 生成个性化图文并茂的学习内容', tag: '图文', color: '#4164b2', gif: '/show/图文学习资源.gif' },
  { title: '教学动画演示', desc: '可视化讲解复杂概念，如 Transformer', tag: '动画', color: '#e8b06a', gif: '/show/教学动画资源.gif' },
  { title: '智能对话生成', desc: '与 AI 对话，按需生成个性化资料', tag: '对话', color: '#649b64', gif: '/show/对话式资源生成.gif' },
  { title: '测验与错题辅导', desc: '自适应测验 + 个性化错题讲解', tag: '测验', color: '#c06080', gif: '/show/测验作答与个性化错题辅导.gif' },
  { title: '知识图谱追踪', desc: '随学更新，实时掌握知识薄弱点', tag: '图谱', color: '#7b68c8', gif: '/show/随学更新知识图谱.gif' },
]

onMounted(() => {
  if (route.query.expired === '1') expiredNotice.value = '登录已过期，请重新登录'
  else if (route.query.deleted === '1') expiredNotice.value = '账号已成功注销'
  featureTimer = setInterval(() => { activeFeature.value = (activeFeature.value + 1) % features.length }, 4000)
})
onUnmounted(() => clearInterval(featureTimer))

async function handleLogin() {
  loading.value = true; error.value = ''; expiredNotice.value = ''
  try { await authStore.login(form.value); router.push(authStore.homeRoute) }
  catch (e: any) { error.value = e.response?.data?.message || e.message || '登录失败，请检查账号密码' }
  finally { loading.value = false }
}
</script>

<style scoped>
/* ══════════════════════════════════════════════════════════
   DESIGN TOKENS — Soft UI + Liquid Glass 
   ══════════════════════════════════════════════════════════ */

.login-page {
  display: flex; min-height: 100vh;
  background: #f8fafc; /* Fallback */
  background: radial-gradient(circle at top left, #fdfbfb 0%, #ebedee 100%);
  position: relative;
  overflow: hidden;
  font-family: 'Inter', system-ui, sans-serif;
}
@media (max-width: 900px) {
  .login-page { flex-direction: column; }
  .showcase { display: none; }
}

/* ─── 动态柔和背景 (Blobs) ─── */
.bg-elements {
  position: absolute; inset: 0; pointer-events: none; z-index: 0;
  overflow: hidden;
}
.bg-grid {
  position: absolute; inset: 0; opacity: 0.2;
  background-image:
    linear-gradient(#94a3b8 1px, transparent 1px),
    linear-gradient(90deg, #94a3b8 1px, transparent 1px);
  background-size: 64px 64px;
}
.blob {
  position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.45;
}
.blob-1 { top: -10%; left: -10%; width: 50vw; height: 50vw; background: #4164b2; animation: float 20s infinite alternate; }
.blob-2 { bottom: -20%; right: -10%; width: 60vw; height: 60vw; background: #a2c3a2; animation: float 25s infinite alternate-reverse; }
.blob-3 { top: 30%; left: 40%; width: 45vw; height: 45vw; background: #e8b06a; opacity: 0.3; animation: float 22s infinite alternate; }

@keyframes float {
  0% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(5%, 10%) scale(1.1); }
  100% { transform: translate(-5%, -5%) scale(0.9); }
}

/* ─── 左侧展示区 ─── */
.showcase {
  position: relative; z-index: 1; flex: 1; 
  display: flex; flex-direction: column; justify-content: center;
  padding: 60px 80px; color: #1e293b;
  max-width: 58%;
}

/* 品牌 */
.showcase__brand {
  display: flex; align-items: center; gap: 20px; margin-bottom: 48px;
}
.showcase__icon {
  width: 64px; height: 64px; border-radius: 16px;
  box-shadow: 0 12px 24px rgba(65, 100, 178, 0.25);
}
.showcase__title { font-size: 2.2rem; font-weight: 800; color: #0f172a; letter-spacing: -0.02em; }
.showcase__sub { font-size: 1.05rem; color: #64748b; margin-top: 4px; font-weight: 500; }

/* Liquid Glass 功能卡片 */
.glass-card--feature {
  background: linear-gradient(to bottom, rgba(255,255,255,0.7), rgba(255,255,255,0.3));
  backdrop-filter: blur(60px) saturate(180%);
  -webkit-backdrop-filter: blur(60px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 20px;
  padding: 24px;
  box-shadow: 
    0 24px 48px rgba(15, 23, 42, 0.08),
    inset 0 2px 6px rgba(255, 255, 255, 0.8),
    inset 0 -1px 2px rgba(255, 255, 255, 0.3),
    0 0 0 1px rgba(255, 255, 255, 0.5);
  position: relative;
}

.glass-card--feature::before {
  content: ''; position: absolute; inset: 0;
  background-image: linear-gradient(to bottom, rgba(255,255,255,0.4), transparent);
  pointer-events: none; border-radius: inherit;
}

.glass-card__frame {
  width: 100%; aspect-ratio: 16/9; border-radius: 12px; overflow: hidden;
  background: rgba(0,0,0,0.03); position: relative;
  box-shadow: inset 0 2px 10px rgba(0,0,0,0.05);
}
.glass-card__gif { width: 100%; height: 100%; object-fit: cover; }

.glass-card__info { padding: 24px 12px 8px; position: relative; z-index: 1; }
.glass-card__tag {
  display: inline-block; padding: 6px 16px; border-radius: 24px;
  font-size: 0.8rem; font-weight: 700; color: #fff; margin-bottom: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  text-shadow: 0 1px 2px rgba(0,0,0,0.1);
}
.glass-card__info h3 { font-size: 1.3rem; font-weight: 700; color: #0f172a; margin-bottom: 6px; }
.glass-card__info p  { font-size: 1rem; color: #475569; line-height: 1.5; font-weight: 500; }

/* 指示器 */
.showcase__dots { display: flex; gap: 10px; justify-content: center; margin-top: 24px; }
.dot {
  width: 10px; height: 10px; border-radius: 50%; border: none; cursor: pointer;
  background: rgba(15, 23, 42, 0.15); transition: all .4s cubic-bezier(.4,0,.2,1);
}
.dot--active { width: 32px; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }

/* 卡片切换动画 */
.card-swap-enter-active, .card-swap-leave-active { transition: all .5s cubic-bezier(.4,0,.2,1); }
.card-swap-enter-from { opacity: 0; transform: translateY(20px) scale(.98); filter: blur(4px); }
.card-swap-leave-to   { opacity: 0; transform: translateY(-20px) scale(.98); filter: blur(4px); }

.showcase__footer { margin-top: 40px; font-size: 0.85rem; color: #64748b; font-weight: 600; letter-spacing: 0.05em; text-align: center; }

/* ═══════════════ 右侧表单区 ═══════════════ */
.form-area {
  flex: 1; display: flex; align-items: center; justify-content: center;
  padding: 40px; position: relative; z-index: 1;
}

.form-wrap { width: 100%; max-width: 460px; }

.mobile-logo { display: none; align-items: center; gap: 12px; margin-bottom: 32px; }
@media (max-width: 900px) { .mobile-logo { display: flex; } }

/* ─── Liquid Glass 表单卡片 ─── */
.form-glass {
  position: relative;
  background: linear-gradient(to bottom, rgba(255,255,255,0.85), rgba(255,255,255,0.6));
  backdrop-filter: blur(60px) saturate(180%);
  -webkit-backdrop-filter: blur(60px) saturate(180%);
  border: 1px solid rgba(255,255,255,0.9);
  border-radius: 24px;
  padding: 48px 44px 40px;
  box-shadow:
    0 20px 40px rgba(15, 23, 42, 0.06),
    0 4px 12px rgba(15, 23, 42, 0.04),
    inset 0 2px 4px rgba(255,255,255,0.8),
    inset 0 -1px 2px rgba(255,255,255,0.4);
}
.form-glass::before {
  content: ''; position: absolute; inset: 0; border-radius: inherit;
  background-image: linear-gradient(to bottom, rgba(255,255,255,0.5), transparent);
  pointer-events: none;
}

.form-header { margin-bottom: 32px; position: relative; z-index: 1; }
.form-header h2 { font-size: 1.8rem; font-weight: 800; color: #0f172a; letter-spacing: -0.01em; }
.form-header p  { font-size: 0.95rem; color: #64748b; margin-top: 6px; font-weight: 500; }

/* ─── 输入框（Soft UI） ─── */
.login-form { display: flex; flex-direction: column; gap: 24px; position: relative; z-index: 1; }
.field label { display: block; font-size: 0.95rem; font-weight: 700; color: #334155; margin-bottom: 10px; }

.input-glass {
  display: flex; align-items: center; gap: 14px;
  padding: 0 18px; height: 56px;
  background: rgba(255,255,255,0.8);
  border: 1.5px solid rgba(226, 232, 240, 0.8);
  border-radius: 12px;
  box-shadow: inset 0 2px 4px rgba(15, 23, 42, 0.02);
  transition: all .3s ease;
}
.input-glass:focus-within {
  background: #ffffff;
  border-color: #4164b2;
  box-shadow: 
    inset 0 2px 4px rgba(15, 23, 42, 0.01),
    0 0 0 4px rgba(65, 100, 178, 0.15);
  transform: translateY(-1px);
}
.input-icon { width: 20px; height: 20px; color: #94a3b8; flex-shrink: 0; transition: color .3s; }
.input-glass:focus-within .input-icon { color: #4164b2; }
.input-glass input {
  flex: 1; border: none; outline: none; background: transparent;
  font-size: 1.05rem; color: #0f172a; font-weight: 500; min-width: 0;
}
.input-glass input::placeholder { color: #94a3b8; font-weight: 400; }

/* ─── 提示 ─── */
.notice { padding: 14px 18px; border-radius: 10px; font-size: 0.95rem; line-height: 1.5; font-weight: 500; }
.notice--warn  { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
.notice--error { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }

/* ─── 按钮 ─── */
.login-btn {
  margin-top: 12px;
  position: relative; width: 100%; height: 56px; border: none; border-radius: 12px;
  background: linear-gradient(135deg, #4164b2 0%, #649b64 100%);
  color: #fff; font-size: 1.15rem; font-weight: 700; cursor: pointer;
  box-shadow:
    0 8px 20px rgba(65,100,178,.3),
    inset 0 2px 4px rgba(255,255,255,.3);
  transition: all .3s ease;
  overflow: hidden;
}
.login-btn::before {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(to bottom, rgba(255,255,255,.2), transparent);
  border-radius: inherit; pointer-events: none;
}
.login-btn:hover { 
  transform: translateY(-2px); 
  box-shadow: 
    0 12px 24px rgba(65,100,178,.4), 
    inset 0 2px 4px rgba(255,255,255,.4); 
}
.login-btn:active { transform: translateY(0); box-shadow: 0 4px 12px rgba(65,100,178,.3); }
.login-btn:disabled { opacity: .6; cursor: not-allowed; transform: none; }

.login-btn__spin {
  display: inline-block; width: 18px; height: 18px; border: 2.5px solid rgba(255,255,255,.3);
  border-top-color: #fff; border-radius: 50%; animation: spin .6s linear infinite;
  margin-right: 10px; vertical-align: middle;
}

/* ─── 底部 ─── */
.form-footer { text-align: center; margin-top: 32px; font-size: 1rem; color: #64748b; position: relative; z-index: 1; font-weight: 500; }
.form-footer a { color: #4164b2; font-weight: 700; text-decoration: none; padding: 6px 12px; border-radius: 10px; transition: all .2s; }
.form-footer a:hover { background: rgba(65, 100, 178, 0.1); }

.demo-badge {
  display: flex; align-items: center; gap: 8px; justify-content: center;
  margin-top: 28px; font-size: 0.8rem; color: #64748b; font-weight: 600;
}
.demo-pulse {
  width: 8px; height: 8px; border-radius: 50%; background: #649b64;
  box-shadow: 0 0 12px rgba(100,155,100,.6);
  animation: pulse 2.5s ease-in-out infinite;
}
@keyframes pulse { 0%,100% { opacity:.5; transform:scale(1); } 50% { opacity:1; transform:scale(1.5); } }

/* ─── 入场动画 ─── */
.anim { animation: slideUp .8s cubic-bezier(.22,1,.36,1) both; animation-delay: var(--d, 0s); }
@keyframes slideUp { from { opacity:0; transform:translateY(30px); } to { opacity:1; transform:translateY(0); } }
</style>
