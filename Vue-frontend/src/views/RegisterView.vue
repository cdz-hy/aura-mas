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

      <!-- 注册引导步骤 (Liquid Glass) -->
      <div class="showcase__steps anim" style="--d:.05s">
        <div v-for="(step, i) in steps" :key="step.title" class="glass-step">
          <div class="glass-step__num" :style="{ background: step.color }">{{ i + 1 }}</div>
          <div class="glass-step__text">
            <h3>{{ step.title }}</h3>
            <p>{{ step.desc }}</p>
          </div>
        </div>
      </div>



      <p class="showcase__footer anim" style="--d:.2s">多智能体协作 · 个性化学习资源 · 知识库与图谱驱动</p>
    </aside>

    <!-- ═══════ 右侧：注册表单 ═══════ -->
    <main class="form-area">
      <div class="form-wrap">
        <!-- 移动端 Logo -->
        <div class="mobile-logo anim" style="--d:.0s">
          <img src="/icon.png" alt="AURA" class="w-12 h-12 rounded-xl shadow-lg" />
          <span class="font-extrabold text-slate-800 text-xl tracking-tight">AURA 智学</span>
        </div>

        <div class="form-glass anim" style="--d:.1s">
          <div class="form-header">
            <h2>创建账号</h2>
            <p>加入智学，开启个性化学习之旅</p>
          </div>

          <form @submit.prevent="handleRegister" class="login-form">
            <!-- 账号 + 昵称 -->
            <div class="field-row">
              <div class="field field--half">
                <label>登录账号</label>
                <div class="input-glass">
                  <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                  <input v-model="form.loginName" type="text" placeholder="设置账号" required />
                </div>
              </div>
              <div class="field field--half">
                <label>昵称</label>
                <div class="input-glass">
                  <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 2a5 5 0 0 1 5 5c0 2.76-2.24 5-5 5s-5-2.24-5-5a5 5 0 0 1 5-5z"/><path d="M17 21v-2a4 4 0 0 0-3-3.87M7 21v-2a4 4 0 0 1 3-3.87"/></svg>
                  <input v-model="form.nickname" type="text" placeholder="你的昵称" required />
                </div>
              </div>
            </div>

            <!-- 邮箱 -->
            <div class="field">
              <label>邮箱 <span class="req">*</span></label>
              <div class="input-glass">
                <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
                <input v-model="form.email" type="email" placeholder="your@email.com" required />
              </div>
            </div>

            <!-- 验证码 -->
            <div class="field">
              <label>邮箱验证码 <span class="req">*</span></label>
              <div class="input-glass input-glass--code">
                <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                <input v-model="form.emailCode" type="text" placeholder="输入验证码" required maxlength="6" />
                <button type="button" class="code-btn" :disabled="codeCooldown > 0 || !form.email || sendingCode" @click="handleSendCode">
                  {{ codeCooldown > 0 ? `${codeCooldown}s` : sendingCode ? '发送中...' : '获取验证码' }}
                </button>
              </div>
            </div>

            <!-- 密码 -->
            <div class="field">
              <label>密码</label>
              <div class="input-glass">
                <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                <input v-model="form.password" type="password" placeholder="设置密码（至少6位）" required minlength="6" />
              </div>
            </div>

            <div v-if="error" class="notice notice--error">{{ error }}</div>
            <div v-if="successMsg" class="notice notice--success">{{ successMsg }}</div>

            <button type="submit" class="login-btn" :disabled="loading">
              <span v-if="loading" class="login-btn__spin"></span>
              <span>{{ loading ? '注册中...' : '注 册' }}</span>
            </button>
          </form>

          <div class="form-footer">
            已有账号？
            <router-link to="/login">去登录</router-link>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { sendVerificationCode } from '@/api/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = ref({ loginName: '', password: '', nickname: '', email: '', emailCode: '' })
const loading = ref(false)
const error = ref('')
const successMsg = ref('')
const sendingCode = ref(false)
const codeCooldown = ref(0)
let cooldownTimer: ReturnType<typeof setInterval> | null = null

onUnmounted(() => { if (cooldownTimer) clearInterval(cooldownTimer) })

const steps = [
  { title: '填写基本信息', desc: '账号、昵称、邮箱注册', color: 'linear-gradient(135deg,#4164b2,#5a7ec7)' },
  { title: '验证邮箱', desc: '接收验证码完成身份确认', color: 'linear-gradient(135deg,#649b64,#80b380)' },
  { title: 'AI 生成学习计划', desc: '输入目标，智能规划路径', color: 'linear-gradient(135deg,#e8b06a,#f0c088)' },
  { title: '个性化多模态资源学习', desc: '图文、动画、播客、测验全覆盖', color: 'linear-gradient(135deg,#7b68c8,#9382dc)' },
]


async function handleSendCode() {
  if (!form.value.email) return
  sendingCode.value = true; error.value = ''; successMsg.value = ''
  try {
    await sendVerificationCode(form.value.email)
    successMsg.value = '验证码已发送到您的邮箱，请查收'
    codeCooldown.value = 60
    cooldownTimer = setInterval(() => { codeCooldown.value--; if (codeCooldown.value <= 0) { clearInterval(cooldownTimer!); cooldownTimer = null } }, 1000)
  } catch (e: any) { error.value = e.response?.data?.message || e.message || '发送失败' }
  finally { sendingCode.value = false }
}

async function handleRegister() {
  loading.value = true; error.value = ''; successMsg.value = ''
  try { await authStore.register(form.value); router.push(authStore.homeRoute) }
  catch (e: any) { error.value = e.response?.data?.message || e.message || '注册失败' }
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
  padding: 50px 80px; color: #1e293b;
  max-width: 55%;
}

/* 品牌 */
.showcase__brand {
  display: flex; align-items: center; gap: 16px; margin-bottom: 36px;
}
.showcase__icon {
  width: 56px; height: 56px; border-radius: 14px;
  box-shadow: 0 12px 24px rgba(65, 100, 178, 0.25);
}
.showcase__title { font-size: 2rem; font-weight: 800; color: #0f172a; letter-spacing: -0.02em; }
.showcase__sub { font-size: 1rem; color: #64748b; margin-top: 2px; font-weight: 500; }

/* ─── 步骤卡片 (Liquid Glass) ─── */
.showcase__steps { display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px; }
.glass-step {
  display: flex; align-items: center; gap: 16px; padding: 16px 20px;
  background: linear-gradient(to right, rgba(255,255,255,0.7), rgba(255,255,255,0.4));
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 16px;
  box-shadow: 
    0 10px 20px rgba(15, 23, 42, 0.05),
    inset 0 1px 2px rgba(255, 255, 255, 0.8);
  transition: all .3s ease;
}
.glass-step:hover { 
  background: linear-gradient(to right, rgba(255,255,255,0.8), rgba(255,255,255,0.5));
  transform: translateX(6px); 
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.08), inset 0 1px 2px rgba(255, 255, 255, 1);
}
.glass-step__num {
  width: 38px; height: 38px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1rem; font-weight: 800; color: #fff; flex-shrink: 0;
  box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}
.glass-step__text h3 { font-size: 1rem; font-weight: 700; color: #0f172a; }
.glass-step__text p  { font-size: 0.85rem; color: #475569; margin-top: 2px; font-weight: 500; }


.showcase__footer { margin-top: 32px; font-size: 0.85rem; color: #64748b; font-weight: 600; letter-spacing: 0.05em; text-align: center; }

/* ═══════════════ 右侧表单区 ═══════════════ */
.form-area { flex: 1; display: flex; align-items: center; justify-content: center; padding: 40px 24px; position: relative; z-index: 1; }

.form-wrap { width: 100%; max-width: 480px; }
.mobile-logo { display: none; align-items: center; gap: 12px; margin-bottom: 28px; }
@media (max-width: 900px) { .mobile-logo { display: flex; } }

.form-glass {
  position: relative;
  background: linear-gradient(to bottom, rgba(255,255,255,0.85), rgba(255,255,255,0.6));
  backdrop-filter: blur(60px) saturate(180%);
  -webkit-backdrop-filter: blur(60px) saturate(180%);
  border: 1px solid rgba(255,255,255,0.9);
  border-radius: 24px;
  padding: 44px 40px 36px;
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

.form-header { margin-bottom: 28px; position: relative; z-index: 1; }
.form-header h2 { font-size: 1.7rem; font-weight: 800; color: #0f172a; letter-spacing: -0.01em; }
.form-header p  { font-size: 0.9rem; color: #64748b; margin-top: 4px; font-weight: 500; }

.login-form { display: flex; flex-direction: column; gap: 24px; position: relative; z-index: 1; }
.field-row { display: flex; gap: 20px; }
.field--half { flex: 1; min-width: 0; }
@media (max-width: 480px) { .field-row { flex-direction: column; gap: 24px; } }
.field label { display: block; font-size: 0.95rem; font-weight: 700; color: #334155; margin-bottom: 10px; }
.req { color: #e11d48; }

.input-glass {
  display: flex; align-items: center; gap: 14px; padding: 0 18px; height: 56px;
  background: rgba(255,255,255,0.8);
  border: 1.5px solid rgba(226, 232, 240, 0.8); border-radius: 12px;
  box-shadow: inset 0 2px 4px rgba(15, 23, 42, 0.02);
  transition: all .3s ease;
}
.input-glass:focus-within {
  background: #ffffff; border-color: #4164b2;
  box-shadow: inset 0 2px 4px rgba(15, 23, 42, 0.01), 0 0 0 4px rgba(65, 100, 178, 0.15);
  transform: translateY(-1px);
}
.input-icon { width: 20px; height: 20px; color: #94a3b8; flex-shrink: 0; transition: color .3s; }
.input-glass:focus-within .input-icon { color: #4164b2; }
.input-glass input { flex: 1; border: none; outline: none; background: transparent; font-size: 1.05rem; color: #0f172a; font-weight: 500; min-width: 0; }
.input-glass input::placeholder { color: #94a3b8; font-weight: 400; }

.input-glass--code { padding-right: 8px; }
.code-btn { 
  flex-shrink: 0; padding: 0 18px; height: 42px; border: none; border-radius: 8px; 
  background: #f1f5f9; color: #4164b2; font-size: 0.95rem; font-weight: 700; cursor: pointer; 
  transition: all .2s; white-space: nowrap; 
}
.code-btn:hover:not(:disabled) { background: #e2e8f0; color: #1e3a8a; }
.code-btn:disabled { opacity: .5; cursor: not-allowed; background: #f8fafc; color: #94a3b8; }

.notice { padding: 14px 18px; border-radius: 10px; font-size: 0.95rem; line-height: 1.5; font-weight: 500; }
.notice--error  { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.notice--success { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }

.login-btn {
  margin-top: 12px;
  position: relative; width: 100%; height: 56px; border: none; border-radius: 12px;
  background: linear-gradient(135deg, #4164b2 0%, #649b64 100%);
  color: #fff; font-size: 1.15rem; font-weight: 700; cursor: pointer;
  box-shadow: 0 8px 20px rgba(65,100,178,.3), inset 0 2px 4px rgba(255,255,255,.3);
  transition: all .3s ease; overflow: hidden;
}
.login-btn::before { content: ''; position: absolute; inset: 0; background: linear-gradient(to bottom, rgba(255,255,255,.2), transparent); border-radius: inherit; pointer-events: none; }
.login-btn:hover { transform: translateY(-2px); box-shadow: 0 12px 24px rgba(65,100,178,.4), inset 0 2px 4px rgba(255,255,255,.4); }
.login-btn:active { transform: translateY(0); box-shadow: 0 4px 12px rgba(65,100,178,.3); }
.login-btn:disabled { opacity: .6; cursor: not-allowed; transform: none; }
.login-btn__spin { display: inline-block; width: 16px; height: 16px; border: 2.5px solid rgba(255,255,255,.3); border-top-color: #fff; border-radius: 50%; animation: spin .6s linear infinite; margin-right: 8px; vertical-align: middle; }

.form-footer { text-align: center; margin-top: 32px; font-size: 1rem; color: #64748b; position: relative; z-index: 1; font-weight: 500; }
.form-footer a { color: #4164b2; font-weight: 700; text-decoration: none; padding: 6px 12px; border-radius: 10px; transition: all .2s; }
.form-footer a:hover { background: rgba(65, 100, 178, 0.1); }

.anim { animation: slideUp .8s cubic-bezier(.22,1,.36,1) both; animation-delay: var(--d, 0s); }
@keyframes slideUp { from { opacity:0; transform:translateY(24px); } to { opacity:1; transform:translateY(0); } }
</style>
