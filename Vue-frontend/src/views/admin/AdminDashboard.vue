<template>
  <div>
    <h1 class="section-title mb-6">管理概览</h1>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
      <div class="stat-card animate-fade-in-up" v-for="(stat, i) in adminStats" :key="stat.label" :style="{ animationDelay: `${i * 0.08}s` }">
        <span class="stat-label">{{ stat.label }}</span>
        <span class="stat-value">{{ stat.value }}</span>
      </div>
    </div>
    <div class="card p-6">
      <h2 class="font-display text-lg font-semibold text-navy-800 mb-4">系统日志</h2>
      <p class="text-navy-400 text-sm">管理员可在此查看系统运行状态</p>
    </div>
  </div>
</template>

<script setup lang="ts">
const adminStats = [
  { label: '总用户数', value: 128 },
  { label: '活跃计划', value: 45 },
  { label: '知识库文档', value: 256 },
  { label: '今日AI调用', value: 1024 },
]
</script>
