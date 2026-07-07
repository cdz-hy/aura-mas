<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <h1 class="section-title">资源库管理</h1>
    </div>

    <!-- 主内容区：左侧生成 + 右侧列表 -->
    <div class="flex gap-6" style="height: calc(100vh - 180px);">

      <!-- ========== 左侧：AI 生成区 ========== -->
      <div class="w-[480px] flex-shrink-0 flex flex-col card overflow-hidden">
        <!-- Tab 切换 -->
        <div class="flex border-b border-navy-100">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="flex-1 py-3 text-sm font-medium transition-colors relative"
            :class="activeTab === tab.key
              ? 'text-navy-700 bg-white'
              : 'text-navy-400 hover:text-navy-600 bg-navy-50/50'"
            @click="activeTab = tab.key"
          >
            <span class="flex items-center justify-center gap-2" v-html="tab.icon" />
            {{ tab.label }}
            <div v-if="activeTab === tab.key" class="absolute bottom-0 left-4 right-4 h-0.5 bg-navy-600 rounded-full" />
          </button>
        </div>

        <!-- 文本生成 -->
        <div v-if="activeTab === 'text'" class="flex-1 flex flex-col p-5 overflow-hidden">
          <div class="space-y-3 mb-4">
            <div>
              <label class="text-xs font-medium text-navy-500 mb-1.5 block">主题 <span class="text-red-400">*</span></label>
              <div class="flex gap-2">
                <input
                  v-model="textForm.topic"
                  type="text"
                  class="input-field flex-1"
                  placeholder="输入学习主题，如：机器学习基础"
                />
                <button
                  class="btn-ghost text-xs text-navy-500 flex items-center gap-1 whitespace-nowrap px-3 border border-dashed border-navy-200 hover:border-navy-400 rounded-xl"
                  :disabled="!textForm.topic.trim() || polishing.text"
                  @click="handlePolishPrompt('text')"
                >
                  <svg v-if="polishing.text" class="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" opacity="0.3"/><path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/></svg>
                  <svg v-else class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                  润色
                </button>
              </div>
            </div>
            <div>
              <label class="text-xs font-medium text-navy-500 mb-1.5 block">自定义指令（可选）</label>
              <textarea
                v-model="textForm.prompt"
                class="input-field resize-none"
                rows="2"
                placeholder="额外要求，如：侧重实践案例、面向初学者..."
              />
            </div>
            <button
              class="btn-primary w-full flex items-center justify-center gap-2"
              :disabled="!textForm.topic.trim() || textGenerating"
              @click="handleGenerateText"
            >
              <svg v-if="textGenerating" class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" opacity="0.3"/><path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/></svg>
              <svg v-else class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
              {{ textGenerating ? '生成中...' : '开始生成' }}
            </button>
          </div>

          <!-- 生成结果预览 -->
          <div class="flex-1 overflow-y-auto border border-navy-100 rounded-xl p-4 bg-navy-50/30 min-h-0">
            <div v-if="!textResult && !textGenerating" class="text-center text-navy-300 py-12">
              <svg class="w-12 h-12 mx-auto mb-3 opacity-40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
              <p class="text-sm">输入主题后点击生成，AI 将创建学习资料</p>
            </div>
            <div v-else class="prose prose-sm max-w-none preview-content" v-html="renderedTextResult" />
          </div>

          <!-- 操作按钮 -->
          <div v-if="textResult" class="flex gap-2 mt-3">
            <button
              class="btn-primary flex-1 flex items-center justify-center gap-2"
              :disabled="savingDraft"
              @click="handleSaveTextDraft"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
              保存草稿
            </button>
            <button class="btn-ghost text-sm text-navy-500 flex items-center gap-1" @click="openRewriteDialog('text')">
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              智能改写
            </button>
            <button class="btn-ghost text-sm text-navy-400" @click="textResult = ''">清空</button>
          </div>
        </div>

        <!-- 图片生成 -->
        <div v-if="activeTab === 'image'" class="flex-1 flex flex-col p-5 overflow-hidden">
          <div class="space-y-3 mb-4">
            <div>
              <div class="flex items-center justify-between mb-1.5">
                <label class="text-xs font-medium text-navy-500">绘图描述 <span class="text-red-400">*</span></label>
                <button
                  class="text-xs text-navy-400 hover:text-navy-600 flex items-center gap-1 transition-colors"
                  :disabled="!imageForm.prompt.trim() || polishing.image"
                  @click="handlePolishPrompt('image')"
                >
                  <svg v-if="polishing.image" class="w-3 h-3 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" opacity="0.3"/><path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/></svg>
                  <svg v-else class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                  润色提示词
                </button>
              </div>
              <textarea
                v-model="imageForm.prompt"
                class="input-field resize-none"
                rows="3"
                placeholder="描述你想生成的图片，如：一张展示神经网络结构的示意图，包含输入层、隐藏层和输出层..."
              />
            </div>
            <button
              class="btn-primary w-full flex items-center justify-center gap-2"
              :disabled="!imageForm.prompt.trim() || imageGenerating"
              @click="handleGenerateImage"
            >
              <svg v-if="imageGenerating" class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" opacity="0.3"/><path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/></svg>
              <svg v-else class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
              {{ imageGenerating ? '生成中...' : '生成图片' }}
            </button>
          </div>

          <!-- 图片预览 -->
          <div class="flex-1 overflow-y-auto border border-navy-100 rounded-xl p-4 bg-navy-50/30 min-h-0 flex items-center justify-center">
            <div v-if="!imageResult && !imageGenerating" class="text-center text-navy-300">
              <svg class="w-12 h-12 mx-auto mb-3 opacity-40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
              <p class="text-sm">输入描述后点击生成，AI 将创建图片</p>
            </div>
            <img v-else-if="imageResult" :src="imageResult.url" class="max-w-full max-h-full object-contain rounded-lg shadow-sm" />
          </div>

          <!-- 操作按钮 -->
          <div v-if="imageResult" class="flex gap-2 mt-3">
            <button
              class="btn-primary flex-1 flex items-center justify-center gap-2"
              :disabled="savingDraft"
              @click="handleSaveImageDraft"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
              保存草稿
            </button>
            <button class="btn-ghost text-sm text-navy-400" @click="imageResult = null">清空</button>
          </div>
        </div>

        <!-- 图文一体化生成 -->
        <div v-if="activeTab === 'rich'" class="flex-1 flex flex-col p-5 overflow-hidden">
          <div class="space-y-3 mb-4">
            <div>
              <label class="text-xs font-medium text-navy-500 mb-1.5 block">主题 <span class="text-red-400">*</span></label>
              <div class="flex gap-2">
                <input
                  v-model="richForm.topic"
                  type="text"
                  class="input-field flex-1"
                  placeholder="输入学习主题，如：快速排序算法"
                />
                <button
                  class="btn-ghost text-xs text-navy-500 flex items-center gap-1 whitespace-nowrap px-3 border border-dashed border-navy-200 hover:border-navy-400 rounded-xl"
                  :disabled="!richForm.topic.trim() || polishing.rich"
                  @click="handlePolishPrompt('rich')"
                >
                  <svg v-if="polishing.rich" class="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" opacity="0.3"/><path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/></svg>
                  <svg v-else class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                  润色
                </button>
              </div>
            </div>
            <div>
              <label class="text-xs font-medium text-navy-500 mb-1.5 block">自定义指令（可选）</label>
              <textarea
                v-model="richForm.prompt"
                class="input-field resize-none"
                rows="2"
                placeholder="额外要求..."
              />
            </div>
            <button
              class="btn-primary w-full flex items-center justify-center gap-2"
              :disabled="!richForm.topic.trim() || richGenerating"
              @click="handleGenerateRich"
            >
              <svg v-if="richGenerating" class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" opacity="0.3"/><path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/></svg>
              <svg v-else class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 3v18"/></svg>
              {{ richGenerating ? richPhase : '一键生成图文' }}
            </button>
          </div>

          <!-- 图文预览 -->
          <div class="flex-1 overflow-y-auto border border-navy-100 rounded-xl p-4 bg-navy-50/30 min-h-0">
            <div v-if="!richResult && !richGenerating" class="text-center text-navy-300 py-12">
              <svg class="w-12 h-12 mx-auto mb-3 opacity-40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><rect x="8" y="12" width="8" height="6" rx="1"/><circle cx="10.5" cy="15" r="1"/></svg>
              <p class="text-sm">输入主题后一键生成图文并茂的学习资料</p>
              <p class="text-xs mt-1 text-navy-300">AI 自动生成文本并为关键内容配图</p>
            </div>
            <template v-else>
              <!-- 图片生成进度 -->
              <div v-if="richImageProgress.length > 0" class="mb-3 space-y-1.5">
                <div
                  v-for="(img, idx) in richImageProgress"
                  :key="idx"
                  class="flex items-center gap-2 text-xs px-2.5 py-1.5 rounded-lg"
                  :class="img.url === '__failed__' ? 'bg-red-50 text-red-600'
                    : img.url ? 'bg-emerald-50 text-emerald-700'
                    : 'bg-amber-50 text-amber-700'"
                >
                  <svg v-if="img.url && img.url !== '__failed__'" class="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
                  <svg v-else-if="img.url === '__failed__'" class="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                  <svg v-else class="w-3.5 h-3.5 animate-spin flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" opacity="0.3"/><path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/></svg>
                  <span class="truncate">{{ img.prompt }}</span>
                </div>
              </div>
              <!-- 内容预览 -->
              <div class="prose prose-sm max-w-none preview-content" v-html="renderedRichResult" />
            </template>
          </div>

          <!-- 操作按钮 -->
          <div v-if="richResult && !richGenerating" class="flex gap-2 mt-3">
            <button
              class="btn-primary flex-1 flex items-center justify-center gap-2"
              :disabled="savingDraft"
              @click="handleSaveRichDraft"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
              保存草稿
            </button>
            <button class="btn-ghost text-sm text-navy-500 flex items-center gap-1" @click="openRewriteDialog('rich')">
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              智能改写
            </button>
            <button class="btn-ghost text-sm text-navy-400" @click="richResult = ''; richImageProgress = []">清空</button>
          </div>
        </div>
      </div>

      <!-- ========== 右侧：资源库列表 ========== -->
      <div class="flex-1 flex flex-col card overflow-hidden min-w-0">
        <!-- 筛选栏 -->
        <div class="p-4 border-b border-navy-100">
          <div class="flex flex-wrap items-center gap-3">
            <div class="relative flex-1 min-w-[180px]">
              <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-navy-300 pointer-events-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input
                v-model="filters.keyword"
                type="text"
                class="w-full pl-10 pr-3 py-2 text-sm border border-navy-200 rounded-xl bg-white text-navy-700 placeholder:text-navy-300 focus:outline-none focus:ring-2 focus:ring-navy-200 focus:border-navy-400 transition-all"
                placeholder="搜索资源标题..."
                @input="debouncedSearch"
              />
            </div>
            <!-- 类型筛选 -->
            <div class="custom-dropdown" v-click-outside="() => typeDropdownOpen = false">
              <button class="dropdown-trigger" :class="{ 'has-value': filters.contentType }" @click="typeDropdownOpen = !typeDropdownOpen">
                <span>{{ typeLabel }}</span>
                <svg class="w-4 h-4 text-navy-300 transition-transform" :class="{ 'rotate-180': typeDropdownOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
              </button>
              <transition name="dropdown">
                <div v-if="typeDropdownOpen" class="dropdown-menu">
                  <button v-for="opt in typeOptions" :key="opt.value" class="dropdown-item" :class="{ active: filters.contentType === opt.value }" @click="filters.contentType = opt.value; typeDropdownOpen = false; loadResources(1)">
                    {{ opt.label }}
                    <svg v-if="filters.contentType === opt.value" class="w-4 h-4 ml-auto text-navy-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
                  </button>
                </div>
              </transition>
            </div>
            <!-- 状态筛选 -->
            <div class="custom-dropdown" v-click-outside="() => statusDropdownOpen = false">
              <button class="dropdown-trigger" :class="{ 'has-value': filters.status !== null }" @click="statusDropdownOpen = !statusDropdownOpen">
                <span>{{ statusFilterLabel }}</span>
                <svg class="w-4 h-4 text-navy-300 transition-transform" :class="{ 'rotate-180': statusDropdownOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
              </button>
              <transition name="dropdown">
                <div v-if="statusDropdownOpen" class="dropdown-menu">
                  <button v-for="opt in statusFilterOptions" :key="String(opt.value)" class="dropdown-item" :class="{ active: filters.status === opt.value }" @click="filters.status = opt.value; statusDropdownOpen = false; loadResources(1)">
                    <span v-if="opt.color" class="w-2 h-2 rounded-full" :class="opt.color" />
                    {{ opt.label }}
                    <svg v-if="filters.status === opt.value" class="w-4 h-4 ml-auto text-navy-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
                  </button>
                </div>
              </transition>
            </div>
            <button class="btn-ghost text-sm" @click="resetFilters">
              <svg class="w-4 h-4 inline mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
              重置
            </button>
          </div>
        </div>

        <!-- 列表 -->
        <div class="flex-1 overflow-y-auto min-h-0">
          <div v-if="loading" class="p-12 text-center">
            <div class="inline-block w-8 h-8 border-2 border-navy-200 border-t-navy-600 rounded-full animate-spin" />
            <p class="text-sm text-navy-400 mt-3">加载中...</p>
          </div>

          <template v-else-if="resources.length > 0">
            <table class="w-full">
              <thead>
                <tr class="border-b border-navy-100 bg-navy-50/50">
                  <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">标题</th>
                  <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider w-20">类型</th>
                  <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider w-24">状态</th>
                  <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider w-40">创建时间</th>
                  <th class="px-5 py-3 text-center text-xs font-semibold text-navy-500 uppercase tracking-wider w-36">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(item, idx) in resources"
                  :key="item.id"
                  class="border-b border-navy-50 hover:bg-navy-50/30 transition-colors group animate-row"
                  :style="{ animationDelay: `${idx * 40}ms` }"
                >
                  <td class="px-5 py-3">
                    <div class="flex items-center gap-2">
                      <span v-if="item.contentType === 'image'" class="w-8 h-8 rounded-lg bg-pink-50 flex items-center justify-center flex-shrink-0">
                        <svg class="w-4 h-4 text-pink-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                      </span>
                      <span v-else-if="item.contentType === 'rich'" class="w-8 h-8 rounded-lg bg-violet-50 flex items-center justify-center flex-shrink-0">
                        <svg class="w-4 h-4 text-violet-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><rect x="8" y="12" width="8" height="6" rx="1"/><circle cx="10.5" cy="15" r="1"/></svg>
                      </span>
                      <span v-else class="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                        <svg class="w-4 h-4 text-blue-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                      </span>
                      <span class="text-sm text-navy-700 font-medium truncate max-w-[200px]" :title="item.title">{{ item.title }}</span>
                    </div>
                  </td>
                  <td class="px-5 py-3">
                    <span class="badge"
                      :class="item.contentType === 'image' ? 'bg-pink-50 text-pink-700 border border-pink-200'
                        : item.contentType === 'rich' ? 'bg-violet-50 text-violet-700 border border-violet-200'
                        : 'bg-blue-50 text-blue-700 border border-blue-200'">
                      {{ item.contentType === 'image' ? '图片' : item.contentType === 'rich' ? '图文' : '文本' }}
                    </span>
                  </td>
                  <td class="px-5 py-3">
                    <span class="badge" :class="statusBadgeClass(item.status)">
                      {{ statusText(item.status) }}
                    </span>
                  </td>
                  <td class="px-5 py-3 text-sm text-navy-400">{{ formatTime(item.createdAt) }}</td>
                  <td class="px-5 py-3">
                    <div class="flex items-center justify-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button v-if="item.status === 0" class="btn-icon text-emerald-500 hover:bg-emerald-50" title="审核通过" @click="handleApprove(item)">
                        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
                      </button>
                      <button v-if="item.status === 0" class="btn-icon text-amber-500 hover:bg-amber-50" title="拒绝" @click="handleReject(item)">
                        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
                      </button>
                      <button class="btn-icon text-navy-400 hover:bg-navy-50" title="预览" @click="handlePreview(item)">
                        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                      </button>
                      <button v-if="item.contentType === 'text'" class="btn-icon text-navy-400 hover:bg-navy-50" title="智能改写" @click="handleRewriteFromList(item)">
                        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                      </button>
                      <button class="btn-icon text-red-400 hover:bg-red-50" title="删除" @click="handleDelete(item)">
                        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </template>

          <!-- 空状态 -->
          <div v-else class="p-12 text-center">
            <svg class="w-16 h-16 mx-auto mb-4 text-navy-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <p class="text-navy-400 text-sm">暂无资源</p>
          </div>
        </div>

        <!-- 分页 -->
        <div v-if="totalPages > 1" class="p-4 border-t border-navy-100 flex items-center justify-between">
          <span class="text-sm text-navy-400">共 {{ total }} 条</span>
          <div class="flex items-center gap-1">
            <button
              v-for="p in visiblePages"
              :key="p"
              class="w-8 h-8 rounded-lg text-sm font-medium transition-colors"
              :class="p === pagination.page ? 'bg-navy-600 text-white shadow-sm' : 'text-navy-500 hover:bg-navy-50'"
              @click="loadResources(p)"
            >
              {{ p }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== 预览弹窗 ========== -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="previewItem" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="previewItem = null" />
          <div class="relative bg-white rounded-2xl shadow-2xl w-[700px] max-w-[90vw] max-h-[85vh] overflow-y-auto animate-modal-in">
            <div class="sticky top-0 bg-white z-10 px-6 py-4 border-b border-navy-100 flex items-center justify-between rounded-t-2xl">
              <h3 class="text-lg font-semibold text-navy-700">{{ previewItem.title }}</h3>
              <button class="btn-icon text-navy-400 hover:text-navy-600" @click="previewItem = null">
                <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
            <div class="p-6">
              <div v-if="previewItem.contentType === 'image'" class="text-center">
                <img :src="previewItem.imageUrl" class="max-w-full rounded-lg shadow-sm mx-auto cursor-pointer hover:ring-2 hover:ring-navy-300 transition-all rounded-lg" @click="handleImageClick(previewItem.imageUrl!, 'preview')" title="点击重新生成图片" />
                <p v-if="previewItem.imageCaption" class="text-sm text-navy-400 mt-3">{{ previewItem.imageCaption }}</p>
              </div>
              <div v-else class="prose prose-sm max-w-none preview-content" v-html="renderPreviewMarkdown(previewItem.content || '')" />
              <div v-if="previewItem.contentType !== 'image'" class="mt-4 pt-3 border-t border-navy-100">
                <button class="btn-ghost text-sm text-navy-500 flex items-center gap-1" @click="previewItem = null; openRewriteDialog('preview')">
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                  智能改写
                </button>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- ========== 确认弹窗 ========== -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="confirmDialog.visible" class="fixed inset-0 z-[60] flex items-center justify-center">
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="closeConfirm" />
          <div class="relative bg-white rounded-2xl shadow-2xl w-[400px] max-w-[90vw] animate-modal-in">
            <div class="px-6 pt-6 pb-4">
              <div class="flex items-start gap-3">
                <div class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                  :class="confirmDialog.type === 'danger' ? 'bg-red-50' : 'bg-amber-50'">
                  <svg v-if="confirmDialog.type === 'danger'" class="w-5 h-5 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                  </svg>
                  <svg v-else class="w-5 h-5 text-amber-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                    <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                  </svg>
                </div>
                <div class="flex-1 min-w-0">
                  <h3 class="text-base font-semibold text-navy-700 mb-1">{{ confirmDialog.title }}</h3>
                  <p class="text-sm text-navy-500 leading-relaxed">{{ confirmDialog.message }}</p>
                </div>
              </div>
            </div>
            <div class="px-6 pb-5 flex items-center justify-end gap-2">
              <button class="btn-ghost" @click="closeConfirm" :disabled="confirmDialog.loading">取消</button>
              <button
                class="px-4 py-2 text-sm font-medium text-white rounded-xl transition-all disabled:opacity-50"
                :class="confirmDialog.type === 'danger'
                  ? 'bg-red-500 hover:bg-red-600 active:scale-[0.98]'
                  : 'bg-navy-600 hover:bg-navy-700 active:scale-[0.98]'"
                :disabled="confirmDialog.loading"
                @click="execConfirm"
              >
                <span v-if="confirmDialog.loading" class="flex items-center gap-2">
                  <svg class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" opacity="0.3"/><path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/></svg>
                  处理中...
                </span>
                <span v-else>{{ confirmDialog.confirmText }}</span>
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- ========== Toast 提示 ========== -->
    <Teleport to="body">
      <transition name="slide-toast">
        <div v-if="toast.visible" class="fixed top-6 left-1/2 -translate-x-1/2 z-[70]">
          <div class="flex items-center gap-2.5 px-4 py-2.5 rounded-xl shadow-lg border text-sm font-medium"
            :class="toast.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
              : 'bg-red-50 border-red-200 text-red-700'">
            <svg v-if="toast.type === 'success'" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
            <svg v-else class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
            {{ toast.message }}
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- ========== 智能改写弹窗 ========== -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="rewriteDialog.visible" class="fixed inset-0 z-[55] flex items-stretch">
          <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="closeRewriteDialog" />
          <div class="relative mx-auto my-4 w-[95vw] max-w-[1400px] h-[calc(100vh-32px)] bg-white rounded-2xl shadow-2xl flex flex-col animate-modal-in overflow-hidden">

            <!-- Header -->
            <div class="px-6 py-3.5 border-b border-navy-100 flex items-center justify-between flex-shrink-0 bg-navy-50/30">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-navy-100 flex items-center justify-center">
                  <svg class="w-4 h-4 text-navy-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                </div>
                <h3 class="text-base font-semibold text-navy-700">智能改写</h3>
              </div>
              <button class="btn-icon text-navy-400 hover:text-navy-600 hover:bg-navy-100 rounded-lg" @click="closeRewriteDialog">
                <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>

            <!-- 主体：左侧原文 + 右侧操作 -->
            <div class="flex-1 flex min-h-0">

              <!-- 左侧：原文（始终可见） -->
              <div class="w-1/2 border-r border-navy-100 flex flex-col">
                <div class="px-5 py-2.5 border-b border-navy-50 flex items-center justify-between flex-shrink-0">
                  <span class="text-xs font-semibold text-navy-400 uppercase tracking-wider">原始内容</span>
                  <span class="text-xs text-navy-300">{{ rewriteDialog.originalContent.length }} 字</span>
                </div>
                <div class="flex-1 overflow-y-auto p-5">
                  <div class="prose prose-sm max-w-none text-navy-600" v-html="renderedOriginalForRewrite" />
                </div>
              </div>

              <!-- 右侧：修改要求 + 结果 -->
              <div class="w-1/2 flex flex-col">

                <!-- 修改要求输入区 -->
                <div class="p-5 border-b border-navy-50 flex-shrink-0">
                  <label class="text-sm font-medium text-navy-600 mb-2 block">你想怎么改？</label>
                  <textarea
                    v-model="rewriteDialog.requirement"
                    class="w-full px-4 py-3 text-sm border border-navy-200 rounded-xl bg-white text-navy-700 placeholder:text-navy-300 focus:outline-none focus:ring-2 focus:ring-navy-200 focus:border-navy-400 transition-all resize-y min-h-[120px]"
                    rows="8"
                    placeholder="描述你的修改要求，例如：&#10;&#10;• 第3段的例子换成 Python 的&#10;• 把第二部分扩写得更详细，加一些实际应用场景&#10;• 将全文改为更学术的风格&#10;• 在开头加一段概述&#10;• 把代码注释改成中文&#10;• 用表格替换第三部分的列表"
                    @keydown.ctrl.enter="handleStartRewrite"
                  />
                  <div class="flex items-center justify-between mt-3">
                    <span class="text-xs text-navy-300">Ctrl+Enter 发送 · 只改你要求的部分</span>
                    <button
                      class="px-5 py-2 bg-navy-600 text-white text-sm font-medium rounded-xl hover:bg-navy-700 active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                      :disabled="!rewriteDialog.requirement.trim() || rewriteDialog.loading"
                      @click="handleStartRewrite"
                    >
                      <svg v-if="rewriteDialog.loading" class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" opacity="0.3"/><path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/></svg>
                      <svg v-else class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                      {{ rewriteDialog.loading ? '改写中...' : '开始改写' }}
                    </button>
                  </div>
                </div>

                <!-- 改写结果区 -->
                <div class="flex-1 overflow-y-auto min-h-0">
                  <div v-if="!rewriteDialog.result && !rewriteDialog.loading" class="h-full flex items-center justify-center text-navy-300">
                    <div class="text-center">
                      <svg class="w-16 h-16 mx-auto mb-4 opacity-30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                      <p class="text-sm">在左侧输入修改要求</p>
                      <p class="text-xs mt-1">AI 将输出完整修改后的内容</p>
                    </div>
                  </div>
                  <div v-else-if="rewriteDialog.loading" class="p-5">
                    <div class="flex items-center gap-2 text-sm text-navy-500 mb-4">
                      <svg class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" opacity="0.3"/><path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/></svg>
                      正在生成改写结果...
                    </div>
                    <div v-if="rewriteDialog.result" class="prose prose-sm max-w-none" v-html="renderedRewriteResult" />
                  </div>
                  <div v-else class="p-5">
                    <div class="flex items-center gap-2 mb-3">
                      <span class="text-xs font-semibold text-emerald-500 uppercase tracking-wider">改写结果</span>
                    </div>
                    <div class="prose prose-sm max-w-none" v-html="renderedRewriteResult" />
                  </div>
                </div>
              </div>
            </div>

            <!-- 底部按钮 -->
            <div class="px-6 py-3.5 border-t border-navy-100 flex items-center justify-between flex-shrink-0 bg-navy-50/20">
              <button v-if="rewriteDialog.result && !rewriteDialog.loading" class="text-sm text-navy-400 hover:text-navy-600 transition-colors flex items-center gap-1.5" @click="rewriteDialog.result = ''">
                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
                重新改写
              </button>
              <span v-else />
              <div class="flex gap-2">
                <button class="px-4 py-2 text-sm text-navy-500 hover:text-navy-700 hover:bg-navy-50 rounded-xl transition-colors" @click="closeRewriteDialog">取消</button>
                <button
                  v-if="rewriteDialog.result && !rewriteDialog.loading"
                  class="px-5 py-2 bg-emerald-600 text-white text-sm font-medium rounded-xl hover:bg-emerald-700 active:scale-[0.98] transition-all flex items-center gap-2"
                  @click="applyRewrite"
                >
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
                  替换原文
                </button>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- ========== 图片编辑弹窗 ========== -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="imageEditDialog.visible" class="fixed inset-0 z-[60] flex items-center justify-center">
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="imageEditDialog.visible = false" />
          <div class="relative bg-white rounded-2xl shadow-2xl w-[500px] max-w-[90vw] animate-modal-in">
            <div class="sticky top-0 bg-white z-10 px-6 py-4 border-b border-navy-100 flex items-center justify-between rounded-t-2xl">
              <h3 class="text-lg font-semibold text-navy-700">重新生成图片</h3>
              <button class="btn-icon text-navy-400 hover:text-navy-600" @click="imageEditDialog.visible = false">
                <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
            <div class="p-6 space-y-4">
              <!-- 当前图片预览 -->
              <div class="text-center">
                <img :src="imageEditDialog.imageUrl" class="max-w-full max-h-[200px] rounded-lg shadow-sm mx-auto" />
              </div>
              <!-- 提示词编辑 -->
              <div>
                <label class="text-xs font-medium text-navy-500 mb-1.5 block">图片描述（可修改）</label>
                <textarea
                  v-model="imageEditDialog.editPrompt"
                  class="input-field resize-none"
                  rows="3"
                  placeholder="描述你想要的图片..."
                />
              </div>
            </div>
            <div class="px-6 pb-5 flex items-center justify-end gap-2">
              <button class="btn-ghost" @click="imageEditDialog.visible = false">取消</button>
              <button
                class="btn-primary flex items-center gap-2"
                :disabled="!imageEditDialog.editPrompt.trim() || imageEditDialog.loading"
                @click="handleRegenerateImage"
              >
                <svg v-if="imageEditDialog.loading" class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" opacity="0.3"/><path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/></svg>
                {{ imageEditDialog.loading ? '生成中...' : '重新生成' }}
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { marked } from 'marked'
import katex from 'katex'
import 'katex/dist/katex.min.css'

// marked 数学公式扩展：支持 $$...$$ 块级和 $...$ 行内公式
const mathExtension = {
  name: 'math',
  level: 'inline' as const,
  start(src: string) { return src.match(/\$+/)?.index },
  tokenizer(src: string) {
    // 块级公式 $$...$$
    const blockMatch = src.match(/^\$\$([\s\S]+?)\$\$/)
    if (blockMatch) {
      return { type: 'math', raw: blockMatch[0], text: blockMatch[1].trim(), display: true }
    }
    // 行内公式 $...$（不匹配 $$，不匹配空内容）
    const inlineMatch = src.match(/^\$([^\$\n]+?)\$/)
    if (inlineMatch) {
      return { type: 'math', raw: inlineMatch[0], text: inlineMatch[1].trim(), display: false }
    }
  },
  renderer(token: any) {
    try {
      return katex.renderToString(token.text, { displayMode: token.display, throwOnError: false })
    } catch {
      return token.display ? `<div class="math-error">${token.text}</div>` : `<span class="math-error">${token.text}</span>`
    }
  },
}

marked.use({ extensions: [mathExtension] })
import {
  getAdminResources,
  saveDraft,
  approveResource,
  rejectResource,
  deleteAdminResource,
  updateAdminResource,
  generateTextSSE,
  generateImage,
  generateTextWithImagesSSE,
  rewriteSSE,
  polishPrompt,
  type ResourceLibrary,
} from '@/api/adminResource'

// ==================== Tab 配置 ====================
const tabs = [
  {
    key: 'text',
    label: '文本生成',
    icon: '<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
  },
  {
    key: 'image',
    label: '图片生成',
    icon: '<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
  },
  {
    key: 'rich',
    label: '图文一体',
    icon: '<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><rect x="8" y="12" width="8" height="6" rx="1"/><circle cx="10.5" cy="15" r="1"/></svg>',
  },
]
const activeTab = ref<'text' | 'image'>('text')

// ==================== 文本生成 ====================
const textForm = reactive({ topic: '', prompt: '' })
const textGenerating = ref(false)
const textResult = ref('')
let textSSE: EventSource | null = null

const renderedTextResult = computed(() => {
  if (!textResult.value) return ''
  return marked(textResult.value, { breaks: true }) as string
})

function handleGenerateText() {
  if (!textForm.topic.trim() || textGenerating.value) return
  textResult.value = ''
  textGenerating.value = true

  textSSE = generateTextSSE(textForm.topic, textForm.prompt, {
    onChunk(content) {
      textResult.value += content
    },
    onDone() {
      textGenerating.value = false
    },
    onError(error) {
      textGenerating.value = false
      textResult.value += `\n\n> ❌ 生成失败: ${error}`
    },
  })
}

// ==================== 图片生成 ====================
const imageForm = reactive({ prompt: '' })
const imageGenerating = ref(false)
const imageResult = ref<{ url: string; caption: string } | null>(null)

async function handleGenerateImage() {
  if (!imageForm.prompt.trim() || imageGenerating.value) return
  imageGenerating.value = true
  imageResult.value = null

  try {
    const data = await generateImage(imageForm.prompt)
    imageResult.value = data
  } catch (e: any) {
    showToast('图片生成失败: ' + (e.message || e), 'error')
  } finally {
    imageGenerating.value = false
  }
}

// ==================== 润色提示词 ====================
const polishing = reactive({ text: false, image: false, rich: false })

async function handlePolishPrompt(mode: 'text' | 'image' | 'rich') {
  let rawPrompt = ''
  if (mode === 'text') rawPrompt = textForm.topic
  else if (mode === 'image') rawPrompt = imageForm.prompt
  else if (mode === 'rich') rawPrompt = richForm.topic

  if (!rawPrompt.trim() || polishing[mode]) return

  polishing[mode] = true
  try {
    const polished = await polishPrompt(rawPrompt, mode)
    if (mode === 'text') textForm.topic = polished
    else if (mode === 'image') imageForm.prompt = polished
    else if (mode === 'rich') richForm.topic = polished
    showToast('提示词已润色')
  } catch (e: any) {
    showToast('润色失败: ' + (e.message || e), 'error')
  } finally {
    polishing[mode] = false
  }
}

// ==================== 图文一体化生成 ====================
const richForm = reactive({ topic: '', prompt: '' })
const richGenerating = ref(false)
const richPhase = ref('生成中...')
const richResult = ref('')
const richImageProgress = ref<Array<{ prompt: string; url: string }>>([])
let richSSE: EventSource | null = null

const renderedRichResult = computed(() => {
  if (!richResult.value) return ''
  return marked(richResult.value, { breaks: true }) as string
})

const renderedOriginalForRewrite = computed(() => {
  if (!rewriteDialog.originalContent) return ''
  return marked(rewriteDialog.originalContent, { breaks: true }) as string
})

const renderedRewriteResult = computed(() => {
  if (!rewriteDialog.result) return ''
  return marked(rewriteDialog.result, { breaks: true }) as string
})

function handleGenerateRich() {
  if (!richForm.topic.trim() || richGenerating.value) return
  richResult.value = ''
  richImageProgress.value = []
  richGenerating.value = true
  richPhase.value = '正在生成文本...'

  richSSE = generateTextWithImagesSSE(richForm.topic, richForm.prompt, {
    onTextChunk(content) {
      richResult.value += content
    },
    onTextDone(content) {
      richResult.value = content
      richPhase.value = '正在生成配图...'
    },
    onImageStart(index, prompt) {
      richImageProgress.value.push({ prompt, url: '' })
    },
    onImageDone(index, url) {
      if (index < richImageProgress.value.length) {
        richImageProgress.value[index].url = url || '__failed__'
      }
    },
    onDone(finalContent) {
      richResult.value = finalContent
      richGenerating.value = false
      richSSE = null
    },
    onError(error) {
      richGenerating.value = false
      richResult.value += `\n\n> ❌ 生成失败: ${error}`
      richSSE = null
    },
  })
}

// ==================== 智能改写 ====================
const rewriteDialog = reactive({
  visible: false,
  source: '' as 'text' | 'rich' | 'preview',
  originalContent: '',
  requirement: '',
  result: '',
  loading: false,
})
let rewriteSSEInstance: EventSource | null = null

// 图片编辑弹窗
const imageEditDialog = reactive({
  visible: false,
  imageUrl: '',
  originalPrompt: '',
  editPrompt: '',
  source: '' as 'text' | 'rich' | 'preview',
  loading: false,
})

function openRewriteDialog(source: 'text' | 'rich' | 'preview') {
  let content = ''
  if (source === 'text') content = textResult.value
  else if (source === 'rich') content = richResult.value
  else if (source === 'preview' && previewItem.value) content = previewItem.value.content || ''

  if (!content) return

  rewriteDialog.source = source
  rewriteDialog.originalContent = content
  rewriteDialog.requirement = ''
  rewriteDialog.result = ''
  rewriteDialog.loading = false
  rewriteDialog.visible = true
}

function closeRewriteDialog() {
  rewriteSSEInstance?.close()
  rewriteSSEInstance = null
  rewriteDialog.visible = false
  rewriteDialog.loading = false
}

function handleStartRewrite() {
  if (!rewriteDialog.requirement.trim() || rewriteDialog.loading) return
  rewriteDialog.result = ''
  rewriteDialog.loading = true

  const topic = rewriteDialog.source === 'text' ? textForm.topic
    : rewriteDialog.source === 'rich' ? richForm.topic
    : ''

  rewriteSSEInstance = rewriteSSE(
    rewriteDialog.originalContent,
    rewriteDialog.requirement,
    topic,
    {
      onChunk(content) {
        rewriteDialog.result += content
      },
      onDone() {
        rewriteDialog.loading = false
        rewriteSSEInstance = null
      },
      onError(error) {
        rewriteDialog.loading = false
        rewriteDialog.result += `\n\n❌ ${error}`
        rewriteSSEInstance = null
      },
    }
  )
}

function applyRewrite() {
  if (!rewriteDialog.result) return

  if (rewriteDialog.source === 'text') {
    textResult.value = rewriteDialog.result
  } else if (rewriteDialog.source === 'rich') {
    richResult.value = rewriteDialog.result
  } else if (rewriteDialog.source === 'preview' && previewItem.value) {
    previewItem.value.content = rewriteDialog.result
    if (previewItem.value.id) {
      updateAdminResource(previewItem.value.id, { content: rewriteDialog.result }).catch(() => {})
    }
  }

  closeRewriteDialog()
  showToast('已替换')
}

// 图片编辑
function handleImageClick(imageUrl: string, source: 'text' | 'rich' | 'preview') {
  // 从 markdown 中提取原始 prompt
  const content = source === 'text' ? textResult.value
    : source === 'rich' ? richResult.value
    : (previewItem.value?.content || '')

  // 匹配 ![prompt](url) 或 <img src="url" alt="prompt" />
  let prompt = ''
  const mdMatch = content.match(new RegExp(`!\\[([^\\]]*)\\]\\(${imageUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\)`))
  if (mdMatch) {
    prompt = mdMatch[1]
  }
  const altMatch = content.match(new RegExp(`<img[^>]*src="${imageUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}"[^>]*alt="([^"]*)"[^>]*>`))
  if (altMatch) {
    prompt = altMatch[1]
  }

  imageEditDialog.imageUrl = imageUrl
  imageEditDialog.originalPrompt = prompt
  imageEditDialog.editPrompt = prompt
  imageEditDialog.source = source
  imageEditDialog.visible = false
  imageEditDialog.loading = false
  imageEditDialog.visible = true
}

async function handleRegenerateImage() {
  if (!imageEditDialog.editPrompt.trim() || imageEditDialog.loading) return
  imageEditDialog.loading = true

  try {
    const result = await generateImage(imageEditDialog.editPrompt)
    const oldUrl = imageEditDialog.imageUrl
    const newUrl = result.url
    const newPrompt = imageEditDialog.editPrompt

    // 替换内容中的图片
    const source = imageEditDialog.source
    let content = source === 'text' ? textResult.value
      : source === 'rich' ? richResult.value
      : (previewItem.value?.content || '')

    // 替换 markdown 图片
    content = content.replace(
      new RegExp(`!\\[[^\\]]*\\]\\(${oldUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\)`),
      `![${newPrompt}](${newUrl})`
    )
    // 替换 HTML figure 图片
    content = content.replace(
      new RegExp(`(<img[^>]*src=")${oldUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}"([^>]*>)`),
      `$1${newUrl}"`
    )

    if (source === 'text') textResult.value = content
    else if (source === 'rich') richResult.value = content
    else if (previewItem.value) {
      previewItem.value.content = content
      if (previewItem.value.id) {
        updateAdminResource(previewItem.value.id, { content }).catch(() => {})
      }
    }

    imageEditDialog.visible = false
    showToast('图片已重新生成')
  } catch (e: any) {
    showToast('图片生成失败: ' + (e.message || e), 'error')
  } finally {
    imageEditDialog.loading = false
  }
}

// ==================== 保存草稿 ====================
const savingDraft = ref(false)

async function handleSaveTextDraft() {
  if (!textResult.value || savingDraft.value) return
  savingDraft.value = true
  try {
    await saveDraft({
      title: textForm.topic,
      contentType: 'text',
      content: textResult.value,
    })
    showToast('草稿保存成功')
    loadResources(1)
  } catch (e: any) {
    showToast('保存失败: ' + (e.message || e), 'error')
  } finally {
    savingDraft.value = false
  }
}

async function handleSaveImageDraft() {
  if (!imageResult.value || savingDraft.value) return
  savingDraft.value = true
  try {
    await saveDraft({
      title: imageResult.value.caption.slice(0, 50) || 'AI 生成图片',
      contentType: 'image',
      imageUrl: imageResult.value.url,
      imageCaption: imageResult.value.caption,
    })
    showToast('草稿保存成功')
    loadResources(1)
  } catch (e: any) {
    showToast('保存失败: ' + (e.message || e), 'error')
  } finally {
    savingDraft.value = false
  }
}

async function handleSaveRichDraft() {
  if (!richResult.value || savingDraft.value) return
  savingDraft.value = true
  try {
    await saveDraft({
      title: richForm.topic,
      contentType: 'rich',
      content: richResult.value,
    })
    showToast('草稿保存成功')
    loadResources(1)
  } catch (e: any) {
    showToast('保存失败: ' + (e.message || e), 'error')
  } finally {
    savingDraft.value = false
  }
}

// ==================== 资源库列表 ====================
const resources = ref<ResourceLibrary[]>([])
const loading = ref(false)
const total = ref(0)
const pagination = reactive({ page: 1, size: 10 })
const filters = reactive({ keyword: '', contentType: '', status: null as number | null })

const typeDropdownOpen = ref(false)
const statusDropdownOpen = ref(false)

const typeOptions = [
  { label: '全部类型', value: '' },
  { label: '文本', value: 'text' },
  { label: '图片', value: 'image' },
  { label: '图文', value: 'rich' },
]
const typeLabel = computed(() => typeOptions.find(o => o.value === filters.contentType)?.label || '全部类型')

const statusFilterOptions = [
  { label: '全部状态', value: null, color: '' },
  { label: '待审核', value: 0, color: 'bg-amber-400' },
  { label: '已入库', value: 1, color: 'bg-emerald-400' },
  { label: '已拒绝', value: 2, color: 'bg-red-400' },
]
const statusFilterLabel = computed(() => statusFilterOptions.find(o => o.value === filters.status)?.label || '全部状态')

const totalPages = computed(() => Math.ceil(total.value / pagination.size))
const visiblePages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, pagination.page - 2)
  const end = Math.min(totalPages.value, pagination.page + 2)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

async function loadResources(page = 1) {
  loading.value = true
  pagination.page = page
  try {
    const res = await getAdminResources({
      page,
      size: pagination.size,
      keyword: filters.keyword || undefined,
      contentType: filters.contentType || undefined,
      status: filters.status ?? undefined,
    })
    resources.value = res.data.records
    total.value = res.data.total
  } catch (e) {
    console.error('加载资源列表失败', e)
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.keyword = ''
  filters.contentType = ''
  filters.status = null
  loadResources(1)
}

// 防抖搜索
let searchTimer: ReturnType<typeof setTimeout> | null = null
function debouncedSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadResources(1), 300)
}

// ==================== 确认弹窗 ====================
const confirmDialog = reactive({
  visible: false,
  title: '',
  message: '',
  type: 'warning' as 'warning' | 'danger',
  confirmText: '确认',
  loading: false,
  onConfirm: () => {},
})

function showConfirm(opts: {
  title: string
  message: string
  type?: 'warning' | 'danger'
  confirmText?: string
  onConfirm: () => void
}) {
  confirmDialog.title = opts.title
  confirmDialog.message = opts.message
  confirmDialog.type = opts.type || 'warning'
  confirmDialog.confirmText = opts.confirmText || '确认'
  confirmDialog.loading = false
  confirmDialog.onConfirm = opts.onConfirm
  confirmDialog.visible = true
}

function closeConfirm() {
  if (confirmDialog.loading) return
  confirmDialog.visible = false
}

async function execConfirm() {
  confirmDialog.loading = true
  try {
    await confirmDialog.onConfirm()
    confirmDialog.visible = false
  } catch (e: any) {
    showToast(e.message || '操作失败', 'error')
  } finally {
    confirmDialog.loading = false
  }
}

// ==================== Toast 提示 ====================
const toast = reactive({ visible: false, message: '', type: 'success' as 'success' | 'error' })
let toastTimer: ReturnType<typeof setTimeout> | null = null

function showToast(message: string, type: 'success' | 'error' = 'success') {
  if (toastTimer) clearTimeout(toastTimer)
  toast.message = message
  toast.type = type
  toast.visible = true
  toastTimer = setTimeout(() => { toast.visible = false }, 2500)
}

// ==================== 审核操作 ====================
function handleApprove(item: ResourceLibrary) {
  showConfirm({
    title: '审核入库',
    message: `确认将「${item.title}」入库？入库后将向量化存入知识库。`,
    type: 'warning',
    confirmText: '入库',
    onConfirm: async () => {
      await approveResource(item.id)
      showToast('入库成功')
      loadResources(pagination.page)
    },
  })
}

function handleReject(item: ResourceLibrary) {
  showConfirm({
    title: '拒绝资源',
    message: `确认拒绝「${item.title}」？`,
    type: 'warning',
    confirmText: '拒绝',
    onConfirm: async () => {
      await rejectResource(item.id)
      showToast('已拒绝')
      loadResources(pagination.page)
    },
  })
}

function handleDelete(item: ResourceLibrary) {
  showConfirm({
    title: '删除资源',
    message: `确认删除「${item.title}」？${item.status === 1 ? '已入库的向量数据也将被删除。' : ''}`,
    type: 'danger',
    confirmText: '删除',
    onConfirm: async () => {
      await deleteAdminResource(item.id)
      showToast('已删除')
      loadResources(pagination.page)
    },
  })
}

// ==================== 预览 ====================
const previewItem = ref<ResourceLibrary | null>(null)

// 从列表直接打开改写
function handleRewriteFromList(item: ResourceLibrary) {
  rewriteDialog.source = 'preview'
  rewriteDialog.originalContent = item.content || ''
  rewriteDialog.requirement = ''
  rewriteDialog.result = ''
  rewriteDialog.loading = false
  rewriteDialog.visible = true
  // 保存引用以便替换后更新
  previewItem.value = item
}

function handlePreview(item: ResourceLibrary) {
  previewItem.value = item
}

function renderPreviewMarkdown(content: string): string {
  return marked(content, { breaks: true }) as string
}

// ==================== 工具函数 ====================
function statusText(status: number): string {
  return { 0: '待审核', 1: '已入库', 2: '已拒绝' }[status] || '未知'
}

function statusBadgeClass(status: number): string {
  return {
    0: 'bg-amber-50 text-amber-700 border border-amber-200',
    1: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
    2: 'bg-red-50 text-red-700 border border-red-200',
  }[status] || 'bg-gray-50 text-gray-700 border border-gray-200'
}

function formatTime(time: string): string {
  if (!time) return '-'
  const d = new Date(time)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

// v-click-outside 指令
const vClickOutside = {
  mounted(el: HTMLElement, binding: any) {
    el._clickOutside = (event: Event) => {
      if (!el.contains(event.target as Node)) binding.value()
    }
    document.addEventListener('click', el._clickOutside)
  },
  unmounted(el: HTMLElement) {
    document.removeEventListener('click', el._clickOutside)
  },
}

// ==================== 生命周期 ====================
onMounted(() => {
  loadResources(1)
})

onUnmounted(() => {
  textSSE?.close()
  richSSE?.close()
  rewriteSSEInstance?.close()
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<style scoped>
.section-title {
  @apply text-xl font-bold text-navy-700;
}

.card {
  @apply bg-white rounded-2xl shadow-sm border;
  border-color: rgba(198, 210, 232, 0.5);
}

.input-field {
  @apply w-full px-3 py-2 text-sm border border-navy-200 rounded-xl bg-white text-navy-700
         placeholder:text-navy-300 focus:outline-none focus:ring-2 focus:ring-navy-200 focus:border-navy-400 transition-all;
}

.btn-primary {
  @apply px-4 py-2 bg-navy-600 text-white text-sm font-medium rounded-xl
         hover:bg-navy-700 active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed;
}

.btn-ghost {
  @apply px-3 py-1.5 text-navy-500 text-sm rounded-lg hover:bg-navy-50 transition-colors;
}

.btn-icon {
  @apply w-8 h-8 rounded-lg flex items-center justify-center transition-colors;
}

.badge {
  @apply inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full;
}

/* Dropdown */
.custom-dropdown {
  @apply relative;
}
.dropdown-trigger {
  @apply flex items-center gap-2 px-3 py-2 text-sm border border-dashed border-navy-200
         rounded-xl text-navy-500 hover:border-navy-400 hover:text-navy-600
         transition-all cursor-pointer bg-white;
}
.dropdown-trigger.has-value {
  @apply border-solid border-navy-400 text-navy-700;
}
.dropdown-menu {
  @apply absolute top-full left-0 mt-1 w-44 bg-white border border-navy-100 rounded-xl
         shadow-lg py-1 z-50 origin-top;
}
.dropdown-item {
  @apply flex items-center gap-2 px-3 py-2 text-sm text-navy-600 hover:bg-navy-50
         transition-colors cursor-pointer w-full text-left;
}
.dropdown-item.active {
  @apply text-navy-700 font-medium;
}

/* Animations */
.animate-row {
  animation: fadeInUp 0.3s ease-out both;
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-modal-in {
  animation: modalIn 0.25s ease-out both;
}
@keyframes modalIn {
  from { opacity: 0; transform: scale(0.95) translateY(10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.dropdown-enter-active { transition: all 0.15s ease-out; }
.dropdown-leave-active { transition: all 0.1s ease-in; }
.dropdown-enter-from { opacity: 0; transform: scaleY(0.9) translateY(-4px); }
.dropdown-leave-to { opacity: 0; transform: scaleY(0.95) translateY(-2px); }

.slide-toast-enter-active { transition: all 0.25s ease-out; }
.slide-toast-leave-active { transition: all 0.2s ease-in; }
.slide-toast-enter-from { opacity: 0; transform: translate(-50%, -20px); }
.slide-toast-leave-to { opacity: 0; transform: translate(-50%, -20px); }


/* Prose for markdown preview */
.prose :deep(h1) { @apply text-lg font-bold text-navy-700 mb-3 mt-4; }
.prose :deep(h2) { @apply text-base font-bold text-navy-700 mb-2 mt-3; }
.prose :deep(h3) { @apply text-sm font-semibold text-navy-600 mb-2 mt-3; }
.prose :deep(p) { @apply text-sm text-navy-600 mb-2 leading-relaxed; }
.prose :deep(ul), .prose :deep(ol) { @apply text-sm text-navy-600 mb-2 pl-5; }
.prose :deep(li) { @apply mb-1; }
.prose :deep(blockquote) { @apply border-l-[3px] border-navy-200 pl-3 text-sm text-navy-500 italic my-2; }
.prose :deep(code) { @apply bg-navy-50 text-navy-700 px-1 py-0.5 rounded text-xs; }
.prose :deep(pre) { @apply bg-navy-50 rounded-xl p-3 overflow-x-auto my-2; }
.prose :deep(pre code) { @apply bg-transparent p-0; }
.prose :deep(img) { @apply rounded-lg my-2 max-w-full; }
.prose :deep(table) { @apply w-full text-sm border-collapse my-2; }
.prose :deep(th) { @apply bg-navy-50 px-3 py-2 text-left font-semibold text-navy-600 border border-navy-100; }
.prose :deep(td) { @apply px-3 py-2 text-navy-600 border border-navy-100; }

/* 图文一体：图片 figure 样式 */
.prose :deep(figure.rich-image) {
  @apply my-4 text-center;
}
.prose :deep(figure.rich-image img) {
  @apply rounded-xl shadow-sm mx-auto max-w-full;
}
.prose :deep(figure.rich-image figcaption) {
  @apply text-xs text-navy-400 mt-2 leading-relaxed;
}
.prose :deep(figure.rich-image figcaption strong) {
  @apply text-navy-600;
}
</style>
