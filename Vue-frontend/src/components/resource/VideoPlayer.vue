<template>
  <div class="video-player-card group relative bg-white/60 backdrop-blur-md border border-navy-100/50 rounded-2xl overflow-hidden shadow-sm hover:shadow-xl hover:border-red-200/60 transition-all duration-300 flex flex-col">
    <!-- 视频播放区域 (如果可以嵌入) -->
    <div v-if="embedUrl" class="relative w-full aspect-video bg-navy-900 overflow-hidden rounded-t-2xl">
      <iframe
        :src="embedUrl"
        class="w-full h-full absolute top-0 left-0"
        frameborder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen
        sandbox="allow-top-navigation allow-same-origin allow-forms allow-scripts allow-popups allow-popups-to-escape-sandbox"
      ></iframe>
    </div>
    
    <!-- 降级区域 (如果不支持嵌入) -->
    <a 
      v-else 
      :href="video.url" 
      target="_blank" 
      rel="noopener noreferrer"
      class="w-full flex items-center p-5 bg-gradient-to-r from-red-50/50 to-transparent hover:from-red-50 group transition-colors cursor-pointer border-b border-navy-100/50"
    >
      <div class="w-12 h-12 rounded-xl bg-red-100/50 text-red-500 flex items-center justify-center flex-shrink-0 group-hover:scale-110 group-hover:bg-red-500 group-hover:text-white transition-all duration-300 shadow-sm">
        <svg class="w-6 h-6 ml-0.5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M8 5v14l11-7z"/>
        </svg>
      </div>
      <div class="ml-4 flex-1">
        <p class="text-sm font-semibold text-navy-800 group-hover:text-red-600 transition-colors">{{ video.platform || '外部视频' }}</p>
        <p class="text-xs text-navy-400 mt-0.5">点击在新窗口打开并播放视频</p>
      </div>
      <div class="flex-shrink-0 text-navy-300 group-hover:text-red-400 transition-colors">
        <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
        </svg>
      </div>
    </a>

    <!-- 卡片底部信息 -->
    <div class="p-4 flex flex-col flex-1">
      <a 
        :href="video.url" 
        target="_blank" 
        rel="noopener noreferrer"
        class="text-base font-semibold text-navy-800 line-clamp-2 leading-snug group-hover:text-red-600 hover:underline transition-colors decoration-red-600/50" 
        :title="video.title"
      >
        {{ video.title }}
      </a>
      
      <div class="flex items-center gap-2 mt-3 mb-1">
        <span 
          v-if="video.platform" 
          class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium tracking-wide shadow-sm"
          :class="platformColorClass"
        >
          <svg v-if="video.platform === 'YouTube'" class="w-3 h-3 mr-1" viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
          <svg v-else-if="video.platform === 'Bilibili'" class="w-3 h-3 mr-1" viewBox="0 0 24 24" fill="currentColor"><path d="M17.813 4.653h.854c1.51.054 2.769.578 3.773 1.574 1.004.995 1.524 2.249 1.56 3.76v7.36c-.036 1.51-.556 2.769-1.56 3.773s-2.262 1.524-3.773 1.56H5.333c-1.51-.036-2.769-.556-3.773-1.56S.036 18.8580.0 17.347v-7.36c.036-1.511.556-2.765 1.56-3.76 1.004-.996 2.262-1.52 3.773-1.574h.774l-1.174-1.12a1.234 1.234 0 0 1-.373-.906c0-.356.124-.658.373-.907l.027-.027c.267-.249.573-.373.92-.373.3470.124.658.373.907l2.433 2.333h7.107l2.433-2.333c.249-.249.556-.373.92-.373.364 0 .671.124.92.373.249.249.373.551.373.907 0 .356-.124.658-.373.907l-1.174 1.12zM3.32 8.667c-.64.036-1.178.267-1.614.693-.435.427-.657.965-.666 1.614v7.36c.009.649.231 1.187.666 1.613.436.427.974.658 1.614.694h17.36c.64-.036 1.178-.267 1.614-.694.435-.426.657-.964.666-1.613v-7.36c-.009-.649-.231-1.187-.666-1.614-.436-.426-.974-.657-1.614-.693H3.32zm5.827 5.053c.036-.515-.151-.942-.56-1.28-.409-.338-.89-.507-1.44-.507-.551 0-1.031.169-1.44.507-.409.338-.596.765-.56 1.28v.534c-.036.515.151.942.56 1.28.409.338.889.507 1.44.507.55 0 1.031-.169 1.44-.507.409-.338.596-.765.56-1.28v-.534zm7.36 0c.036-.515-.151-.942-.56-1.28-.409-.338-.89-.507-1.44-.507-.551 0-1.031.169-1.44.507-.409.338-.596.765-.56 1.28v.534c-.036.515.151.942.56 1.28.409.338.889.507 1.44.507.55 0 1.031-.169 1.44-.507.409-.338.596-.765.56-1.28v-.534z"/></svg>
          <svg v-else class="w-3 h-3 mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg>
          {{ video.platform }}
        </span>
      </div>
      <p v-if="video.snippet" class="text-xs text-navy-500 line-clamp-2 mt-auto">
        {{ video.snippet }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface VideoData {
  title: string
  url: string
  snippet?: string
  platform: string
}

const props = defineProps<{
  video: VideoData
}>()

// 提取并转换 iframe 嵌入链接
const embedUrl = computed(() => {
  const url = props.video.url
  if (!url) return null

  // 1. YouTube 解析
  if (url.includes('youtube.com') || url.includes('youtu.be')) {
    let videoId = ''
    if (url.includes('youtu.be/')) {
      videoId = url.split('youtu.be/')[1].split('?')[0]
    } else if (url.includes('v=')) {
      videoId = new URL(url).searchParams.get('v') || ''
    }
    if (videoId) {
      return `https://www.youtube.com/embed/${videoId}?rel=0`
    }
  }

  // 2. Bilibili 解析 (BV号)
  const bvMatch = url.match(/(BV[A-Za-z0-9]+)/)
  if (bvMatch && bvMatch[1]) {
    const bvid = bvMatch[1]
    // 添加 autoplay=0 防止自动播放，high_quality=1 和 high_wide=1 强制请求最高画质
    return `https://player.bilibili.com/player.html?bvid=${bvid}&page=1&high_quality=1&high_wide=1&as_wide=1&autoplay=0`
  }

  // 其他不支持纯净 iframe 嵌入的平台，返回 null 进行降级跳转
  return null
})

// 根据平台设置不同的标签颜色
const platformColorClass = computed(() => {
  const p = props.video.platform?.toLowerCase() || ''
  if (p.includes('youtube')) return 'bg-red-50 text-red-600 border border-red-100'
  if (p.includes('bilibili') || p.includes('b站')) return 'bg-pink-50 text-pink-600 border border-pink-100'
  if (p.includes('腾讯')) return 'bg-orange-50 text-orange-600 border border-orange-100'
  if (p.includes('爱奇艺')) return 'bg-green-50 text-green-600 border border-green-100'
  return 'bg-navy-50 text-navy-600 border border-navy-100'
})
</script>

<style scoped>
.video-player-card {
  will-change: transform, box-shadow;
}
</style>
