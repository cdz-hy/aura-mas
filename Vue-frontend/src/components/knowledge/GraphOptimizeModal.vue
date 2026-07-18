<template>
  <Teleport to="body">
    <transition name="gom-fade">
      <div v-if="visible" class="fixed inset-0 z-[100] flex items-center justify-center">
        <!-- Overlay -->
        <div class="gom-overlay" @click="close()"></div>

        <!-- Modal -->
        <div class="gom-modal">
          <!-- Header -->
          <div class="gom-header">
            <div class="flex items-center gap-3">
              <div class="gom-header-icon">
                <svg class="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="m21.64 3.64-1.28-1.28a1.21 1.21 0 0 0-1.72 0L2.36 18.64a1.21 1.21 0 0 0 0 1.72l1.28 1.28a1.21 1.21 0 0 0 1.72 0L21.64 5.36a1.21 1.21 0 0 0 0-1.72Z"/>
                  <path d="m14 7 3 3"/>
                  <path d="M5 6v4"/><path d="M19 14v4"/>
                  <path d="M10 2v2"/><path d="M7 8H3"/>
                  <path d="M21 16h-4"/><path d="M11 3H9"/>
                </svg>
              </div>
              <div>
                <h3 class="gom-title">智能整理图谱</h3>
                <p class="gom-subtitle">大语言模型将遵循您的要求优化知识结构</p>
              </div>
            </div>
            <button @click="close" class="gom-close-btn">
              <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          <!-- Body -->
          <div class="gom-body">
            <!-- Presets as cards -->
            <div class="gom-section">
              <h4 class="gom-section-label">
                <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                </svg>
                快速整理策略
              </h4>
              <div class="gom-preset-grid">
                <button 
                  v-for="(preset, idx) in presetItems" 
                  :key="idx"
                  @click="customInstruction = preset.text"
                  class="gom-preset-card"
                  :class="{'gom-preset-active': customInstruction === preset.text}"
                >
                  <div class="gom-preset-icon" :style="{ background: preset.iconBg }">
                    <svg class="w-4 h-4" :style="{ color: preset.iconColor }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" v-html="preset.iconPath"></svg>
                  </div>
                  <div class="gom-preset-text">
                    <span class="gom-preset-name">{{ preset.name }}</span>
                    <span class="gom-preset-desc">{{ preset.desc }}</span>
                  </div>
                </button>
              </div>
            </div>

            <!-- Custom Instruction -->
            <div class="gom-section">
              <h4 class="gom-section-label">
                <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
                详细整理要求
              </h4>
              <div class="gom-textarea-wrapper">
                <textarea
                  v-model="customInstruction"
                  placeholder="请输入您对图谱的具体整理要求，例如：&quot;将所有关于前端的知识合并为一个大节点&quot;、&quot;保留重要性大于0.5的节点即可&quot;..."
                  class="gom-textarea"
                ></textarea>
              </div>
              <p class="gom-hint">
                <svg class="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
                整理操作将保留原有节点的掌握度和重要性数据
              </p>
            </div>
          </div>

          <!-- Footer -->
          <div class="gom-footer">
            <button @click="close" class="gom-btn-cancel">取消</button>
            <button
              @click="startOptimization"
              :disabled="!customInstruction.trim()"
              class="gom-btn-primary"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="m21.64 3.64-1.28-1.28a1.21 1.21 0 0 0-1.72 0L2.36 18.64a1.21 1.21 0 0 0 0 1.72l1.28 1.28a1.21 1.21 0 0 0 1.72 0L21.64 5.36a1.21 1.21 0 0 0 0-1.72Z"/>
                <path d="m14 7 3 3"/>
              </svg>
              开始智能整理
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'

const props = defineProps<{
  visible: boolean
  domainId: number | null
}>()

const emit = defineEmits<{
  'update:visible': [val: boolean]
  'submit': [instruction: string]
}>()

const close = () => {
  emit('update:visible', false)
}

const presetItems = computed(() => [
  {
    name: '简化图谱',
    desc: '合并冗余细碎的节点',
    text: '简化图谱 (合并冗余细碎的节点)',
    iconBg: 'rgba(65, 100, 178, 0.08)',
    iconColor: '#4164b2',
    iconPath: '<circle cx="12" cy="12" r="10"/><line x1="8" y1="12" x2="16" y2="12"/>',
  },
  {
    name: '丰富图谱',
    desc: '发散关联的子概念',
    text: '丰富图谱 (根据现有结构发散关联的子概念)',
    iconBg: 'rgba(100, 155, 100, 0.08)',
    iconColor: '#649b64',
    iconPath: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>',
  },
  {
    name: '逻辑重组',
    desc: '优化和纠正连线关系',
    text: '逻辑重组 (优化和纠正连线关系)',
    iconBg: 'rgba(201, 135, 59, 0.08)',
    iconColor: '#c9873b',
    iconPath: '<polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/><line x1="4" y1="4" x2="9" y2="9"/>',
  },
  {
    name: '精准剪枝',
    desc: '保留重点，剔除边缘',
    text: '基于最新进度整理 (保留重点，剔除边缘概念)',
    iconBg: 'rgba(180, 80, 80, 0.06)',
    iconColor: '#b55050',
    iconPath: '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/>',
  },
])

const customInstruction = ref('')

watch(() => props.visible, (val) => {
  if (val) {
    customInstruction.value = presetItems.value[0].text
  }
})

const startOptimization = () => {
  if (!props.domainId || !customInstruction.value.trim()) return
  emit('submit', customInstruction.value)
  close()
}
</script>

<style scoped>
/* ─── Overlay ─── */
.gom-overlay {
  position: absolute;
  inset: 0;
  background: rgba(26, 40, 71, 0.2);
  backdrop-filter: blur(3px);
}

/* ─── Modal ─── */
.gom-modal {
  position: relative;
  width: 520px;
  max-width: 90vw;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 20px;
  background: #fdf9f0;
  box-shadow:
    0 24px 64px rgba(26, 40, 71, 0.18),
    0 4px 16px rgba(26, 40, 71, 0.08),
    0 0 0 1px rgba(26, 40, 71, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.7);
  animation: gom-slide-in 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
@keyframes gom-slide-in {
  from { opacity: 0; transform: translateY(16px) scale(0.97); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

/* ─── Header ─── */
.gom-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.65) 0%, rgba(255, 255, 255, 0.3) 100%);
  border-bottom: 1px solid rgba(26, 40, 71, 0.06);
  border-radius: 20px 20px 0 0;
}
.gom-header-icon {
  width: 40px; height: 40px; border-radius: 12px;
  background: linear-gradient(135deg, #1a2847, #4164b2);
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(26, 40, 71, 0.2);
}
.gom-title {
  font-size: 18px; font-weight: 700; color: #1a2847; line-height: 1.3;
}
.gom-subtitle {
  font-size: 12px; color: #6783c1; margin-top: 2px;
}
.gom-close-btn {
  width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  color: #6783c1; transition: all 0.2s; cursor: pointer; background: none; border: none;
}
.gom-close-btn:hover { background: rgba(26, 40, 71, 0.06); color: #1a2847; }

/* ─── Body ─── */
.gom-body {
  padding: 20px 24px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(26, 40, 71, 0.08) transparent;
}

.gom-section { margin-bottom: 20px; }
.gom-section:last-child { margin-bottom: 0; }

.gom-section-label {
  font-size: 13px; font-weight: 600; color: #4a5874;
  margin-bottom: 10px; display: flex; align-items: center; gap: 6px;
}

/* ─── Preset cards ─── */
.gom-preset-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.gom-preset-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 1px 4px rgba(26, 40, 71, 0.03), inset 0 1px 0 rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}
.gom-preset-card:hover {
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(65, 100, 178, 0.15);
  box-shadow: 0 4px 12px rgba(26, 40, 71, 0.06);
  transform: translateY(-1px);
}
.gom-preset-active {
  border-color: rgba(65, 100, 178, 0.35) !important;
  background: rgba(65, 100, 178, 0.06) !important;
  box-shadow: 0 2px 12px rgba(65, 100, 178, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.5) !important;
}

.gom-preset-icon {
  width: 36px; height: 36px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.gom-preset-text {
  display: flex; flex-direction: column; gap: 2px; min-width: 0;
}
.gom-preset-name {
  font-size: 13px; font-weight: 600; color: #1a2847; line-height: 1.3;
}
.gom-preset-desc {
  font-size: 11px; color: #8899aa; line-height: 1.3;
}

/* ─── Textarea ─── */
.gom-textarea-wrapper {
  position: relative;
}
.gom-textarea {
  width: 100%;
  height: 100px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(26, 40, 71, 0.08);
  border-radius: 14px;
  padding: 14px;
  font-size: 13px;
  color: #1a2847;
  line-height: 1.6;
  transition: all 0.2s;
  resize: none;
  box-shadow: inset 0 1px 3px rgba(26, 40, 71, 0.03);
}
.gom-textarea::placeholder {
  color: #a0aab4;
}
.gom-textarea:focus {
  outline: none;
  border-color: #4164b2;
  box-shadow: 0 0 0 3px rgba(65, 100, 178, 0.08), inset 0 1px 3px rgba(26, 40, 71, 0.02);
  background: rgba(255, 255, 255, 0.9);
}

.gom-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  font-size: 11px;
  color: #8899aa;
}
.gom-hint svg {
  color: #c9873b;
}

/* ─── Footer ─── */
.gom-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid rgba(26, 40, 71, 0.06);
  background: linear-gradient(0deg, rgba(255, 255, 255, 0.5) 0%, rgba(255, 255, 255, 0.25) 100%);
  border-radius: 0 0 20px 20px;
}

.gom-btn-cancel {
  padding: 9px 22px; font-size: 13px; font-weight: 500;
  color: #6783c1; border-radius: 10px; border: 1px solid rgba(26, 40, 71, 0.08);
  cursor: pointer; transition: all 0.2s; background: rgba(255, 255, 255, 0.5);
}
.gom-btn-cancel:hover { background: rgba(26, 40, 71, 0.04); color: #1a2847; border-color: rgba(26, 40, 71, 0.12); }

.gom-btn-primary {
  padding: 9px 22px; font-size: 13px; font-weight: 600;
  color: #fdf9f0; border-radius: 10px; border: none; cursor: pointer;
  background: linear-gradient(135deg, #1a2847, #4164b2);
  box-shadow: 0 2px 8px rgba(26, 40, 71, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.1);
  transition: all 0.2s; display: flex; align-items: center; gap: 6px;
}
.gom-btn-primary:hover {
  box-shadow: 0 4px 16px rgba(26, 40, 71, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.15);
  transform: translateY(-1px);
}
.gom-btn-primary:active { transform: translateY(0); }
.gom-btn-primary:disabled { opacity: 0.45; cursor: not-allowed; transform: none; box-shadow: 0 1px 4px rgba(26, 40, 71, 0.1); }

/* ─── Transitions ─── */
.gom-fade-enter-active, .gom-fade-leave-active {
  transition: opacity 0.25s ease;
}
.gom-fade-enter-from, .gom-fade-leave-to {
  opacity: 0;
}
</style>
