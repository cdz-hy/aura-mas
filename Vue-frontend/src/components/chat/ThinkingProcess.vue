<template>
  <div class="thinking-process-wrapper" :class="{ 'is-expanded': isExpanded }">
    <div class="thinking-header" @click="toggleExpanded">
      <div class="header-left">
        <div class="icon-wrapper">
          <svg class="chevron-icon" :class="{ 'expanded': isExpanded }" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M9 18L15 12L9 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <span class="header-title">思考过程</span>
        <span v-if="thinkings && thinkings.length > 0" class="step-count">({{ thinkings.length }} 步)</span>
      </div>
      <div v-if="isStreaming" class="streaming-status">
        <span class="status-text">正在思考</span>
        <div class="pulse-indicator"></div>
      </div>
    </div>
    
    <transition name="expand">
      <div v-show="isExpanded" class="thinking-content-container">
        <div class="thinking-content">
          <div class="timeline">
            <div v-for="(step, index) in thinkings || []" :key="index" class="timeline-item">
              <div class="timeline-marker">
                <div class="marker-dot" :class="{ 'is-last': index === (thinkings?.length || 0) - 1 && isStreaming }"></div>
                <div v-if="index < (thinkings?.length || 0) - 1 || isStreaming" class="marker-line"></div>
              </div>
              <div class="timeline-content">
                <div class="agent-name">
                  <svg v-if="getAgentType(step.agent) === 'search'" class="agent-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  <svg v-else-if="getAgentType(step.agent) === 'generate'" class="agent-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <svg v-else-if="getAgentType(step.agent) === 'check'" class="agent-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  <svg v-else-if="getAgentType(step.agent) === 'structure'" class="agent-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6z" />
                  </svg>
                  <svg v-else-if="getAgentType(step.agent) === 'media'" class="agent-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  <svg v-else-if="getAgentType(step.agent) === 'user'" class="agent-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  <svg v-else-if="getAgentType(step.agent) === 'chat'" class="agent-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  <svg v-else-if="getAgentType(step.agent) === 'tool'" class="agent-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <svg v-else class="agent-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                  {{ step.agent || '系统智能体' }}
                </div>
                <div class="step-detail">
                  <span>{{ step.content }}</span><span v-if="isStreaming && index === (thinkings?.length || 0) - 1" class="typing-cursor"></span>
                </div>
              </div>
            </div>
            
            <div v-if="isStreaming && (!thinkings || thinkings.length === 0)" class="timeline-item empty-thinking">
               <div class="timeline-marker">
                 <div class="marker-dot is-last"></div>
               </div>
               <div class="timeline-content">
                  <div class="step-detail text-gray-400">正在分析问题，请稍候...</div>
               </div>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  thinkings?: Array<{ agent: string, content: string }>
  isStreaming?: boolean
}>()

const isExpanded = ref(false)

const getAgentType = (agentName?: string) => {
  if (!agentName) return 'system';
  const name = agentName.toLowerCase();
  
  if (name.includes('搜索') || name.includes('检索') || name.includes('search') || name.includes('rag')) return 'search';
  if (name.includes('生成') || name.includes('创作') || name.includes('generator')) return 'generate';
  if (name.includes('审核') || name.includes('检查') || name.includes('reviewer') || name.includes('checker')) return 'check';
  if (name.includes('分解') || name.includes('编排') || name.includes('orchestrator') || name.includes('decomposer')) return 'structure';
  if (name.includes('视频') || name.includes('动画') || name.includes('video') || name.includes('animation')) return 'media';
  if (name.includes('画像') || name.includes('profile') || name.includes('压缩') || name.includes('compressor')) return 'user';
  if (name.includes('回答') || name.includes('答疑') || name.includes('导师') || name.includes('tutor') || name.includes('answer')) return 'chat';
  if (name.includes('工具') || name.includes('tool')) return 'tool';
  
  return 'system';
}

// 自动展开/折叠逻辑
watch(() => props.isStreaming, (newVal) => {
  if (newVal) {
    // 流式输出开始时自动展开
    isExpanded.value = true
  }
}, { immediate: true })

const toggleExpanded = () => {
  isExpanded.value = !isExpanded.value
}
</script>

<style scoped>
.thinking-process-wrapper {
  margin: 12px 0;
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.6); /* slate-50 */
  backdrop-filter: blur(8px);
  border: 1px solid rgba(59, 130, 246, 0.15); /* blue-500 */
  box-shadow: 0 2px 10px rgba(59, 130, 246, 0.04);
  overflow: hidden;
  font-family: inherit;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.thinking-process-wrapper.is-expanded {
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.25);
}

.thinking-header {
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  user-select: none;
  background: transparent;
  transition: background-color 0.2s ease;
}

.thinking-header:hover {
  background-color: rgba(59, 130, 246, 0.04);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 8px;
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  transition: background 0.3s ease;
}

.thinking-header:hover .icon-wrapper {
  background: rgba(59, 130, 246, 0.18);
}

.chevron-icon {
  width: 14px;
  height: 14px;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.chevron-icon.expanded {
  transform: rotate(90deg);
}

.header-title {
  font-size: 13.5px;
  font-weight: 600;
  color: #1e3a8a; /* blue-900 */
  letter-spacing: 0.3px;
}

.step-count {
  font-size: 12px;
  color: #3b82f6; /* blue-500 */
  background: rgba(59, 130, 246, 0.1);
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.streaming-status {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(59, 130, 246, 0.08);
  padding: 4px 10px;
  border-radius: 12px;
}

.status-text {
  font-size: 12px;
  color: #3b82f6;
  font-weight: 500;
  animation: pulse-text 2s infinite;
}

@keyframes pulse-text {
  0%, 100% { opacity: 0.8; }
  50% { opacity: 1; }
}

.pulse-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #60a5fa; /* blue-400 */
  animation: pulse-glow 1.5s infinite cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes pulse-glow {
  0% { transform: scale(0.8); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.5); }
  50% { transform: scale(1.2); box-shadow: 0 0 0 4px rgba(59, 130, 246, 0); }
  100% { transform: scale(0.8); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
}

.thinking-content-container {
  border-top: 1px dashed rgba(59, 130, 246, 0.15);
  background: linear-gradient(180deg, rgba(241, 245, 249, 0.4) 0%, rgba(255, 255, 255, 0) 100%);
}

.thinking-content {
  padding: 20px 16px;
  max-height: 400px;
  overflow-y: auto;
}

/* Timeline */
.timeline {
  display: flex;
  flex-direction: column;
}

.timeline-item {
  display: flex;
  gap: 16px;
  position: relative;
  animation: fade-in-up 0.4s ease forwards;
}

@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.timeline-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 16px;
  margin-top: 4px;
}

.marker-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: white;
  border: 2.5px solid #93c5fd; /* blue-300 */
  flex-shrink: 0;
  z-index: 2;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.8);
  transition: all 0.3s ease;
}

.marker-dot.is-last {
  border-color: #3b82f6; /* blue-500 */
  background-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
  animation: marker-pulse 2s infinite;
}

@keyframes marker-pulse {
  0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(59, 130, 246, 0); }
  100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
}

.marker-line {
  width: 2px;
  flex-grow: 1;
  background: linear-gradient(to bottom, #bfdbfe, rgba(191, 219, 254, 0.3)); /* blue-200 */
  margin: 2px 0;
  min-height: 24px;
}

.timeline-content {
  padding-bottom: 20px;
  flex-grow: 1;
}

.agent-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  font-weight: 600;
  color: #2563eb; /* blue-600 */
  margin-bottom: 6px;
}

.agent-icon {
  width: 14px;
  height: 14px;
  opacity: 0.8;
}

.step-detail {
  font-size: 13.5px;
  color: #475569; /* slate-600 */
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 120px;
  overflow-y: auto;
  padding-right: 4px;
}

.typing-cursor {
  display: inline-block;
  width: 2px;
  height: 14px;
  background: #3b82f6;
  margin-left: 2px;
  vertical-align: text-bottom;
  animation: blink 0.8s steps(2) infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.step-detail::-webkit-scrollbar {
  width: 4px;
}
.step-detail::-webkit-scrollbar-track {
  background: transparent;
}
.step-detail::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.15);
  border-radius: 4px;
}
.step-detail::-webkit-scrollbar-thumb:hover {
  background: rgba(59, 130, 246, 0.3);
}

.empty-thinking {
  opacity: 0.8;
}

/* Scrollbar styling for content */
.thinking-content::-webkit-scrollbar {
  width: 6px;
}
.thinking-content::-webkit-scrollbar-track {
  background: transparent;
}
.thinking-content::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.2);
  border-radius: 10px;
}
.thinking-content::-webkit-scrollbar-thumb:hover {
  background: rgba(59, 130, 246, 0.4);
}

/* Transition Animations */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}
.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
  transform: translateY(-8px);
}
.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 500px;
  transform: translateY(0);
}
</style>
