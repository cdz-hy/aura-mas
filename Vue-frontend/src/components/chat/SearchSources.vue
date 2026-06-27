<template>
  <div v-if="sources.length > 0 || isSearching" class="search-sources">
    <!-- Searching animation -->
    <div v-if="isSearching" class="search-sources-header">
      <div class="search-pulse"></div>
      <span class="search-label">正在搜索{{ searchQuery ? '：' + searchQuery : '...' }}</span>
    </div>
    <div v-else class="search-sources-header">
      <svg class="w-3.5 h-3.5 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
      <span class="search-label">找到 {{ sources.length }} 条相关资料</span>
    </div>

    <!-- Source cards -->
    <div class="search-sources-list">
      <TransitionGroup name="source-card">
        <a
          v-for="(source, i) in sources"
          :key="source.url + i"
          :href="source.url"
          target="_blank"
          rel="noopener noreferrer"
          class="source-card"
        >
          <div class="source-card-header">
            <img
              :src="faviconUrl(source.url)"
              alt=""
              class="source-favicon"
              @error="($event.target as HTMLImageElement).style.display = 'none'"
            />
            <span class="source-title">{{ source.title || '未知来源' }}</span>
          </div>
          <span class="source-domain">{{ domain(source.url) }}</span>
          <p v-if="source.snippet" class="source-snippet">{{ source.snippet }}</p>
        </a>
      </TransitionGroup>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface SearchSource {
  title: string
  url: string
  snippet?: string
  score?: number
}

defineProps<{
  sources: SearchSource[]
  isSearching?: boolean
  searchQuery?: string
}>()

function domain(url: string): string {
  try {
    return new URL(url).hostname.replace('www.', '')
  } catch {
    return url
  }
}

function faviconUrl(url: string): string {
  try {
    const u = new URL(url)
    return `${u.protocol}//${u.hostname}/favicon.ico`
  } catch {
    return ''
  }
}
</script>

<style scoped>
.search-sources {
  margin-bottom: 10px;
}

.search-sources-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.search-label {
  font-size: 12px;
  color: #7c3aed;
  font-weight: 500;
}

.search-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #8b5cf6;
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}

.search-sources-list {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
  scrollbar-width: thin;
  scrollbar-color: rgba(139, 92, 246, 0.2) transparent;
}

.search-sources-list::-webkit-scrollbar {
  height: 4px;
}
.search-sources-list::-webkit-scrollbar-track {
  background: transparent;
}
.search-sources-list::-webkit-scrollbar-thumb {
  background: rgba(139, 92, 246, 0.2);
  border-radius: 2px;
}

.source-card {
  flex-shrink: 0;
  width: 200px;
  padding: 10px 12px;
  background: linear-gradient(135deg, rgba(245, 243, 255, 0.95), rgba(237, 233, 254, 0.8));
  border: 1px solid rgba(139, 92, 246, 0.1);
  border-radius: 10px;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.source-card:hover {
  border-color: rgba(139, 92, 246, 0.25);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.1);
  transform: translateY(-1px);
}

.source-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.source-favicon {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  flex-shrink: 0;
}

.source-title {
  font-size: 12.5px;
  font-weight: 600;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.source-domain {
  font-size: 11px;
  color: #94a3b8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-snippet {
  font-size: 11px;
  color: #64748b;
  line-height: 1.5;
  margin: 0;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* Card enter animation */
.source-card-enter-active {
  transition: all 0.3s ease;
}
.source-card-enter-from {
  opacity: 0;
  transform: translateY(8px) scale(0.95);
}
</style>
