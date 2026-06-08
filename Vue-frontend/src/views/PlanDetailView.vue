<template>
  <div class="h-full w-full flex flex-col overflow-hidden">
    <div v-if="!plan" class="flex items-center justify-center h-full flex-1">
      <div class="text-center">
        <svg class="w-12 h-12 mx-auto text-navy-200 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" class="opacity-25" /><path d="M4 12a8 8 0 018-8" class="opacity-75" stroke-linecap="round" />
        </svg>
        <p class="mt-3 text-navy-400">加载中...</p>
      </div>
    </div>

    <div v-else class="flex gap-0 h-full w-full overflow-x-auto overflow-y-hidden flex-1 custom-scrollbar">
    <!-- ==================== 左侧栏：模块列表（可折叠） ==================== -->
    <div
      class="flex-shrink-0 flex flex-col card overflow-hidden transition-all duration-300 animate-fade-in-up"
      :class="sidebarCollapsed ? 'w-0 opacity-0' : 'w-[280px]'"
    >
      <div class="flex flex-col h-full min-w-[280px]">
        <!-- Plan header -->
        <div class="px-4 py-4 border-b border-navy-100/50">
          <div class="flex items-center gap-2">
            <input
              v-if="editingTitle"
              v-model="editTitle"
              class="input-field text-sm py-1.5 flex-1"
              @keyup.enter="saveTitle"
              @keyup.escape="editingTitle = false"
              autofocus
            />
            <h2 v-else class="font-display text-base font-semibold text-navy-800 truncate flex-1">{{ plan.title }}</h2>
            <button
              v-if="!editingTitle"
              class="p-1 rounded text-navy-300 hover:text-navy-600 hover:bg-navy-50 transition-colors"
              @click="editTitle = plan.title; editingTitle = true"
              title="修改计划名称"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
            </button>
            <button
              v-if="editingTitle"
              class="p-1 rounded text-emerald-500 hover:bg-emerald-50 transition-colors"
              @click="saveTitle"
              title="保存"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </button>
            <button
              v-if="editingTitle"
              class="p-1 rounded text-navy-300 hover:text-navy-600 hover:bg-navy-50 transition-colors"
              @click="editingTitle = false"
              title="取消"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div class="flex items-center gap-2 mt-1.5">
            <span class="text-xs px-2 py-0.5 rounded-full" :class="statusClass(plan.status)">
              {{ statusText(plan.status) }}
            </span>
            <span class="text-xs text-navy-400">{{ Math.round(plan.progress || 0) }}%</span>
          </div>
          <div class="mt-2 h-1.5 bg-navy-100 rounded-full overflow-hidden">
            <div class="h-full bg-gradient-to-r from-navy-400 to-sage-500 rounded-full transition-all duration-500" :style="{ width: `${plan.progress || 0}%` }"></div>
          </div>
        </div>

        <!-- Module list -->
        <div class="flex-1 overflow-y-auto p-3 space-y-2">
          <div v-if="modules.length === 0" class="text-center py-8 text-navy-300 text-sm">
            <p>暂无学习模块</p>
            <p class="text-xs mt-1">在右侧对话中描述学习目标，AI 会自动规划</p>
          </div>
          <div
            v-for="(mod, i) in modules"
            :key="i"
            class="rounded-lg cursor-pointer transition-all duration-200 border"
            :class="selectedModuleIndex === i ? 'border-navy-300 bg-navy-50 shadow-sm' : 'border-transparent hover:bg-navy-50/50'"
            @click="selectModule(i)"
          >
            <div class="p-3">
              <div class="flex items-center gap-2.5">
                <span class="w-6 h-6 rounded-full text-xs flex items-center justify-center font-bold flex-shrink-0"
                  :class="selectedModuleIndex === i ? 'bg-navy-600 text-white' : 'bg-navy-100 text-navy-500'">
                  {{ i + 1 }}
                </span>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-navy-800 truncate">{{ mod.title }}</p>
                  <p class="text-xs text-navy-400 mt-0.5">{{ mod.estimatedHours || 2 }}学时</p>
                </div>
              </div>
              <div class="flex flex-wrap gap-1 mt-2 ml-8">
                <span v-for="type in mod.resourceTypes" :key="type"
                  class="text-[10px] px-1.5 py-0.5 rounded-full"
                  :class="badgeClass(type)">
                  {{ typeLabels[type] || type }}
                </span>
              </div>
            </div>

            <!-- 模块资源列表 -->
            <div v-if="selectedModuleIndex === i && mod.resources.length > 0" class="border-t border-navy-100/50 px-3 py-2 space-y-1.5">
              <div
                v-for="res in mod.resources"
                :key="res.id"
                class="flex items-center gap-2 p-1.5 rounded-md text-xs transition-colors cursor-pointer"
                :class="selectedResourceId === res.id ? 'bg-navy-100' : 'hover:bg-white'"
                @click.stop="toggleResource(res)"
              >
                <span class="w-2 h-2 rounded-full flex-shrink-0" :class="res.status === 2 ? 'bg-emerald-400' : res.status === 1 ? 'bg-blue-400' : res.status === 3 ? 'bg-red-400' : 'bg-navy-200'"></span>
                <span class="text-navy-600 truncate flex-1">{{ res.moduleData?.title || typeLabels[res.moduleType] || res.moduleType }}</span>
                <span v-if="res.status === 2" class="text-emerald-500 text-[10px]">已生成</span>
                <span v-else-if="res.status === 1 && !stuckResources.has(res.id)" class="text-blue-500 text-[10px]">生成中</span>
                <span v-else-if="res.status === 1 || res.status === 3" class="text-red-500 text-[10px] cursor-pointer hover:underline" @click.stop="handleRetry(res)">重试</span>
                <span v-else class="text-navy-300 text-[10px]">待生成</span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- 折叠/展开按钮 -->
    <button
      class="flex-shrink-0 w-6 flex items-center justify-center bg-navy-50 hover:bg-navy-100 transition-colors rounded-r-lg my-2"
      @click="sidebarCollapsed = !sidebarCollapsed"
      :title="sidebarCollapsed ? '展开侧栏' : '收起侧栏'"
    >
      <svg class="w-4 h-4 text-navy-400 transition-transform duration-300" :class="sidebarCollapsed ? 'rotate-180' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="15 18 9 12 15 6" />
      </svg>
    </button>

    <!-- ==================== 中间栏：资源详情（始终在 DOM 中，width 过渡动画） ==================== -->
    <div
      class="resource-panel flex flex-col card overflow-hidden"
      :class="{
        'resource-panel--closed': !selectedResource && !showResourceStreamPreview,
        '!transition-none': isDragging,
        'fixed inset-0 z-40 m-0 bg-white rounded-none border-none shadow-none': isFullscreen,
        'mx-2': !isFullscreen
      }"
      :style="isFullscreen ? {} : panelStyle"
    >
      <template v-if="selectedResource">
        <!-- 标题栏 -->
        <div class="px-4 py-3 border-b border-navy-100/50 flex items-center justify-between">
          <div class="flex items-center gap-2 min-w-0">
            <span class="text-[10px] px-1.5 py-0.5 rounded-full flex-shrink-0" :class="badgeClass(selectedResource.moduleType)">
              {{ typeLabels[selectedResource.moduleType] || selectedResource.moduleType }}
            </span>
            <h3 class="font-display text-sm font-semibold text-navy-800 truncate">
              {{ selectedResource.moduleData?.title || '学习资源' }}
            </h3>
          </div>
          <div class="flex items-center gap-1.5 flex-shrink-0">
            <button
              class="p-1 rounded text-navy-300 hover:text-navy-600 hover:bg-navy-50 transition-colors"
              @click="isFullscreen = !isFullscreen"
              :title="isFullscreen ? '退出全屏' : '全屏显示'"
            >
              <svg v-if="isFullscreen" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 14h6v6m10-6h-6v6M4 10h6V4m10 6h-6V4" />
              </svg>
              <svg v-else class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
              </svg>
            </button>
            <button
              class="p-1 rounded text-navy-300 hover:text-navy-600 hover:bg-navy-50 transition-colors"
              @click="selectedResourceId = null; selectedResource = null; quizData = null; mindmapData = null; gradingResult = null; quizSubmittedAnswers = null; showExplanations = false; isFullscreen = false"
              title="关闭"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 内容区 -->
        <div
          class="flex-1 overflow-y-auto"
          :class="selectedResource.moduleType === 'animation' ? 'resource-content--animation' : (selectedResource.moduleType === 'podcast' ? 'resource-content--podcast' : 'p-4')"
          @click="handleCitationClick($event); onResourceClick($event)"
          @mouseover="handleCitationMouseOver"
          @mouseout="handleCitationMouseOut"
          @mouseup="onResourceMouseUp"
        >
          <!-- 题目类型 -->
          <template v-if="selectedResource.moduleType === 'quiz'">
            <QuizPlayer
              v-if="quizData"
              :data="quizData"
              :initial-answers="quizSubmittedAnswers ?? undefined"
              :initial-submitted="!!quizSubmittedAnswers"
              :grading="quizSubmitting"
              :result-score="gradingResult?.score ?? null"
              :question-results="questionResults"
              @submit="onQuizSubmit"
              @retake="retakeQuiz"
            />
            <div v-else class="text-center py-8 text-navy-300 text-sm">
              <p>题目数据加载中...</p>
            </div>

            <!-- 批改总分 -->
            <div v-if="gradingResult" class="mt-4 p-4 rounded-xl border border-navy-100/50 text-center">
              <div class="text-3xl font-bold" :class="(gradingResult.score ?? 0) >= 80 ? 'text-emerald-600' : (gradingResult.score ?? 0) >= 60 ? 'text-amber-600' : 'text-red-500'">
                {{ gradingResult.score ?? '—' }}<span class="text-lg text-navy-400">分</span>
              </div>
              <p class="text-sm text-navy-500 mt-1">答对 {{ gradingResult.correct ?? 0 }} / {{ gradingResult.total ?? 0 }} 题</p>
            </div>
          </template>

          <!-- 文档/阅读/图文类型 -->
          <template v-else-if="selectedResource.moduleType === 'text' || selectedResource.moduleType === 'document' || selectedResource.moduleType === 'reading'">
            <div v-if="selectedResource.moduleData?.content" class="prose prose-sm max-w-none text-navy-700 leading-relaxed markdown-body" v-html="renderedResourceContent"></div>
            <div v-else class="text-center py-8 text-navy-300 text-sm">
              <p>资源内容待生成</p>
            </div>
          </template>

          <!-- 导图类型 -->
          <template v-else-if="selectedResource.moduleType === 'mindmap'">
            <MindmapPlayer
              v-if="mindmapData"
              :data="mindmapData"
              :title="selectedResource.moduleData?.module_title || selectedResource.moduleData?.title || '思维导图'"
            />
            <div v-else class="text-center py-8 text-navy-300 text-sm">
              <p>思维导图待生成</p>
            </div>
          </template>

          <!-- 代码类型 -->
          <template v-else-if="selectedResource.moduleType === 'code'">
            <div v-if="selectedResource.moduleData?.content" class="text-sm font-mono text-navy-700 leading-relaxed markdown-body" v-html="renderedResourceContent"></div>
            <div v-else class="text-center py-8 text-navy-300 text-sm">
              <p>代码示例待生成</p>
            </div>
          </template>

          <!-- 视频类型 -->
          <template v-else-if="selectedResource.moduleType === 'video'">
            <div v-if="selectedResource.moduleData?.videos?.length" class="space-y-3">
              <a
                v-for="(v, vi) in selectedResource.moduleData.videos"
                :key="vi"
                :href="v.url"
                target="_blank"
                rel="noopener noreferrer"
                class="block p-4 rounded-xl border border-navy-100/50 hover:border-red-200 hover:bg-red-50/30 transition-colors group"
              >
                <div class="flex items-start gap-3">
                  <div class="w-10 h-10 rounded-lg bg-red-50 flex items-center justify-center flex-shrink-0 group-hover:bg-red-100 transition-colors">
                    <svg class="w-5 h-5 text-red-500" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M8 5v14l11-7z"/>
                    </svg>
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-navy-800 group-hover:text-red-600 transition-colors line-clamp-2">{{ v.title }}</p>
                    <div class="flex items-center gap-2 mt-1.5">
                      <span v-if="v.platform" class="text-[10px] px-1.5 py-0.5 rounded-full bg-red-50 text-red-500">{{ v.platform }}</span>
                      <span v-if="v.snippet" class="text-xs text-navy-400 line-clamp-1">{{ v.snippet }}</span>
                    </div>
                  </div>
                  <svg class="w-4 h-4 text-navy-300 group-hover:text-red-400 flex-shrink-0 mt-1 transition-colors" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
                  </svg>
                </div>
              </a>
            </div>
            <div v-else class="text-center py-8 text-navy-300 text-sm">
              <p>暂无视频资源</p>
            </div>
          </template>

          <!-- 动画类型 -->
          <template v-else-if="selectedResource.moduleType === 'animation'">
            <div v-if="animationHtml" class="animation-stage" :style="isFullscreen ? { width: 'min(100%, calc((100vh - 80px) * 16 / 9))' } : {}">
              <iframe
                class="animation-frame"
                :class="{ 'pointer-events-none': isDragging }"
                :srcdoc="animationHtml"
                sandbox="allow-scripts allow-same-origin"
                title="教学动画"
              ></iframe>
            </div>
            <div v-else class="text-center py-8 text-navy-300 text-sm">
              <p>动画内容待生成</p>
            </div>
          </template>

          <!-- 播客类型 -->
          <template v-else-if="selectedResource.moduleType === 'podcast'">
            <div v-if="selectedResource.moduleData?.content || selectedResource.moduleData?.html" class="podcast-stage">
              <iframe
                class="podcast-frame"
                :class="{ 'pointer-events-none': isDragging }"
                :srcdoc="selectedResource.moduleData?.content || selectedResource.moduleData?.html"
                sandbox="allow-scripts allow-same-origin allow-downloads"
                title="播客节目"
              ></iframe>
            </div>
            <div v-else class="text-center py-8 text-navy-300 text-sm">
              <p>播客内容待生成</p>
            </div>
          </template>

          <!-- 其他类型（含图文） -->
          <template v-else>
            <div v-if="selectedResource.moduleData?.content" class="text-sm text-navy-700 leading-relaxed markdown-body" v-html="renderedResourceContent"></div>
            <div v-else class="text-center py-8 text-navy-300 text-sm">
              <p>资源内容待生成</p>
            </div>
          </template>

          <!-- 网页参考文献列表（可折叠） -->
          <div v-if="currentResourceCitations.length > 0" class="mt-8 border-t border-navy-100/50 pt-4 pb-6">
            <div>
              <button
                class="w-full flex items-center justify-between font-display text-sm font-semibold text-navy-800 cursor-pointer select-none focus:outline-none"
                @click="showCitations = !showCitations"
              >
                <div class="flex items-center gap-2 text-navy-500 hover:text-navy-700 transition-colors">
                  <svg class="w-4 h-4 text-navy-400 transition-colors" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                  </svg>
                  <span>参考网页来源 ({{ currentResourceCitations.length }})</span>
                </div>
                <svg class="w-4 h-4 text-navy-400 transition-transform duration-300" :class="showCitations ? 'rotate-180' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </button>
              
              <div class="grid transition-all duration-300 ease-in-out" :class="showCitations ? 'grid-rows-[1fr] opacity-100 mt-3.5' : 'grid-rows-[0fr] opacity-0 mt-0'">
                <div class="overflow-hidden pl-6">
                  <div class="space-y-3 pt-0.5 pb-1">
                    <div v-for="cit in currentResourceCitations" :key="cit.id" class="flex items-start gap-3 text-xs">
                      <span class="text-[10px] text-navy-500 bg-navy-50/80 px-1.5 py-0.5 rounded font-mono font-semibold text-center w-8 flex-shrink-0 inline-flex items-center justify-center">
                        {{ cit.id }}
                      </span>
                      <div class="flex-1 min-w-0">
                        <a :href="cit.url" target="_blank" rel="noopener noreferrer" class="text-navy-700 hover:text-purple-600 transition-colors font-medium break-all line-clamp-1">
                          {{ cit.title }}
                        </a>
                        <a :href="cit.url" target="_blank" rel="noopener noreferrer" class="text-[10px] text-navy-400 font-mono tracking-tight mt-0.5 block hover:underline break-all">
                          {{ cit.url }}
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- 资源流式生成预览（生成过程中在中间面板实时显示多资源流） -->
      <template v-if="showResourceStreamPreview && !selectedResource">
        <div class="px-4 py-3 border-b border-navy-100/50 flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <h3 class="font-display text-sm font-semibold text-navy-800">正在生成 {{ Object.keys(chatStore.resourceStreamBuffers).length }} 个资源...</h3>
        </div>
        <div class="flex-1 overflow-y-auto p-4 space-y-6">
          <div v-for="placeholder in chatStore.streamingPlaceholders" :key="placeholder.id" class="space-y-2">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span class="text-xs font-medium text-navy-600">{{ placeholder.title }}</span>
              <span class="text-[10px] px-1.5 py-0.5 rounded-full" :class="badgeClass(placeholder.type)">
                {{ typeLabels[placeholder.type] || placeholder.type }}
              </span>
            </div>
            <div v-if="chatStore.resourceStreamBuffers[placeholder.id]" class="text-sm text-navy-700 leading-relaxed markdown-body" v-html="renderMd(chatStore.resourceStreamBuffers[placeholder.id])"></div>
            <div v-else class="text-xs text-navy-400 animate-pulse">等待生成...</div>
          </div>
          <span class="inline-block w-0.5 h-4 bg-navy-400 ml-0.5 animate-pulse align-text-bottom"></span>
        </div>
      </template>
    </div>

    <!-- 拖拽分隔线（始终在 DOM 中，width 过渡动画） -->
    <div
      class="resource-divider flex-shrink-0 flex items-center justify-center cursor-col-resize group"
      :class="{ 'resource-divider--closed': !selectedResource && !showResourceStreamPreview, 'w-2': isDragging, 'w-1.5': !isDragging }"
      @mousedown="onDividerMouseDown"
    >
      <div class="w-0.5 h-8 rounded-full transition-colors" :class="isDragging ? 'bg-navy-400' : 'bg-navy-200 group-hover:bg-navy-400'"></div>
    </div>

    <!-- ==================== 右侧栏：对话界面 ==================== -->
    <PlanChatPanel
      ref="planChatPanelRef"
      :plan-id="planIdStr"
      :resource-id="selectedResource?.id ?? null"
      v-model:mode="chatPanelMode"
      @confirm-breakdown="confirmBreakdown()"
      @submit-modification="submitModification"
      @generate-resource="generateResource"
      @open-resource="openResourceById"
    />
  </div>

  <!-- 引用悬浮预览卡片 -->
  <Teleport to="body">
    <transition name="fade">
      <div
        v-if="hoveredCitation"
        class="fixed z-50 p-3.5 rounded-xl border border-navy-100/50 bg-white/80 backdrop-blur-md shadow-[0_8px_30px_rgb(0,0,0,0.04)] max-w-xs text-left pointer-events-auto transition-all duration-150"
        :style="popoverStyle"
        @mouseenter="clearPopoverTimeout"
        @mouseleave="handleCitationMouseOut"
      >
        <div class="flex items-start gap-2.5">
          <div class="w-7 h-7 rounded-lg bg-navy-50 flex items-center justify-center flex-shrink-0 mt-0.5 text-navy-400">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-xs font-semibold text-navy-800 line-clamp-2 leading-snug">
              {{ hoveredCitation.title }}
            </p>
            <p class="text-[10px] text-navy-400 font-mono tracking-tight mt-1.5 flex items-center gap-1">
              <svg class="w-3 h-3 text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="2" y1="12" x2="22" y2="12" />
                <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
              </svg>
              {{ hoveredCitation.domain }}
            </p>
            <div class="flex items-center justify-between mt-3 pt-2 border-t border-navy-100/30">
              <span class="text-[9px] px-1.5 py-0.5 rounded bg-navy-50 text-navy-500 font-medium font-sans">
                来源 [{{ hoveredCitation.id }}]
              </span>
              <a
                :href="hoveredCitation.url"
                target="_blank"
                rel="noopener noreferrer"
                class="text-[10px] text-navy-500 hover:text-purple-600 flex items-center gap-1 font-medium transition-colors"
              >
                查看原文
                <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
                  <polyline points="15 3 21 3 21 9" />
                  <line x1="10" y1="14" x2="21" y2="3" />
                </svg>
              </a>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- Selection popup (笔记选择) -->
    <div
      v-if="selectionPopup.show"
      class="selection-popup"
      :style="{ left: selectionPopup.x + 'px', top: selectionPopup.y + 'px' }"
    >
      <div class="selection-popup-inner">
        <button class="selection-popup-btn" @click="addToNewNote">
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" />
            <line x1="12" y1="11" x2="12" y2="17" /><line x1="9" y1="14" x2="15" y2="14" />
          </svg>
          新建笔记
        </button>
        <button class="selection-popup-btn" @click="toggleNoteList">
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" />
            <line x1="8" y1="13" x2="16" y2="13" /><line x1="8" y1="17" x2="16" y2="17" />
          </svg>
          追加到笔记
        </button>
      </div>
      <!-- Note list for append -->
      <div v-if="showNoteList" class="selection-note-list">
        <div
          v-for="note in availableNotes"
          :key="note.id"
          class="selection-note-item"
          @click="appendToExistingNote(note)"
        >
          <p class="text-sm font-medium text-navy-700 truncate">{{ note.noteName || '无标题笔记' }}</p>
          <p class="text-xs text-navy-400 truncate">{{ (note.content || '').substring(0, 50) }}</p>
        </div>
        <div v-if="availableNotes.length === 0" class="px-3 py-2 text-xs text-navy-300 text-center">
          暂无笔记
        </div>
      </div>
    </div>
  </Teleport>
</div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { getPlan, updatePlan } from '@/api/plan'
import { getPlanResources, getResource, getLatestTask, retryTask as retryTaskApi } from '@/api/resource'
import { parseMarkdown, extractCitations } from '@/utils/markdown'
import { createNote, getNotes, updateNote, linkNoteToResource } from '@/api/note'
import { getQuizRecords, submitQuizSSE } from '@/api/quiz'
import { issueTicket } from '@/api/auth'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
import { useHeartbeat } from '@/composables/useHeartbeat'
import QuizPlayer from '@/components/resource/QuizPlayer.vue'
import MindmapPlayer from '@/components/resource/MindmapPlayer.vue'
import PlanChatPanel from '@/components/chat/PlanChatPanel.vue'
import type { LearningPlan, LearningResource } from '@/types/plan'
import type { Note } from '@/types/note'
import type { GeneratedResourceRef } from '@/utils/sse'
import type { QuizData, QuizQuestion } from '@/types/quiz'
import type { MindElixirData } from 'mind-elixir'

const route = useRoute()
const planId = computed(() => Number(route.params.id))
const planIdStr = computed(() => String(planId.value))
const chatStore = useChatStore()
const authStore = useAuthStore()
const chatPanelMode = ref<'assistant' | 'tutor'>(
  (localStorage.getItem('chatPanelMode') as 'assistant' | 'tutor') || 'assistant'
)
watch(chatPanelMode, (m) => localStorage.setItem('chatPanelMode', m))
const planChatPanelRef = ref<InstanceType<typeof PlanChatPanel> | null>(null)

// ==================== 学习时长心跳 ====================
const heartbeat = useHeartbeat()

// ==================== 资源选中提取笔记 ====================
const selectionPopup = ref({
  show: false,
  x: 0,
  y: 0,
  text: '',
  planId: 0,
  resourceId: 0,
  resourceTitle: '',
  moduleName: '',
  mode: 'selection' as 'selection' | 'heading',
})
const showNoteList = ref(false)
const availableNotes = ref<Note[]>([])
const highlightedEls: HTMLElement[] = []

function clearHighlight() {
  highlightedEls.forEach(el => el.classList.remove('heading-highlight'))
  highlightedEls.length = 0
}

function getHeadingRangeElements(headingEl: HTMLElement): HTMLElement[] {
  const headingLevel = parseInt(headingEl.tagName.charAt(1))
  const els: HTMLElement[] = [headingEl]
  let sibling = headingEl.nextElementSibling as HTMLElement | null
  while (sibling) {
    if (/^H[1-6]$/.test(sibling.tagName)) {
      const siblingLevel = parseInt(sibling.tagName.charAt(1))
      if (siblingLevel <= headingLevel) break
    }
    els.push(sibling)
    sibling = sibling.nextElementSibling as HTMLElement | null
  }
  return els
}

function clampPopupPos(x: number, y: number): { x: number; y: number } {
  const popupW = 260
  const popupH = 80
  const vw = window.innerWidth
  const vh = window.innerHeight
  return {
    x: Math.max(8, Math.min(x, vw - popupW - 8)),
    y: Math.max(8, Math.min(y, vh - popupH - 8)),
  }
}

function onResourceMouseUp(e: MouseEvent) {
  const selection = window.getSelection()
  const range = selection?.rangeCount > 0 ? selection.getRangeAt(0) : null
  if (!range || range.collapsed) {
    if (!showNoteList.value) { clearHighlight(); selectionPopup.value.show = false }
    return
  }

  // 用 DOM 遍历提取文本+图片（markdown 格式）
  const content = extractRangeContent(range)
  const hasImages = content.includes('![')
  const hasText = content.replace(/!\[[^\]]*\]\([^)]*\)/g, '').trim().length >= 10

  if (!hasText && !hasImages) {
    if (!showNoteList.value) selectionPopup.value.show = false
    return
  }

  const rect = range.getBoundingClientRect()
  const pos = clampPopupPos(rect.right + 8, rect.top - 10)
  const res = selectedResource.value
  const currentModule = modules.value.find(m => m.resources.some(r => r.id === res?.id))

  selectionPopup.value = {
    show: true,
    x: pos.x,
    y: pos.y,
    text: content,
    planId: planId.value,
    resourceId: res?.id || 0,
    resourceTitle: res?.moduleData?.title || '学习资源',
    moduleName: currentModule?.title || '',
    mode: 'selection',
  }
  showNoteList.value = false
}

function onResourceClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!/^H[1-3]$/.test(target.tagName)) return
  // Don't trigger heading extraction if user just selected text
  const selection = window.getSelection()
  if (selection && selection.toString().trim().length > 0) return

  const content = extractHeadingContentMd(target)
  const hasImages = content.includes('![')
  const hasText = content.replace(/!\[[^\]]*\]\([^)]*\)/g, '').trim().length >= 10
  if (!hasText && !hasImages) return

  // Highlight heading + content range
  clearHighlight()
  const els = getHeadingRangeElements(target)
  els.forEach(el => {
    el.classList.add('heading-highlight')
    highlightedEls.push(el)
  })

  const rect = target.getBoundingClientRect()
  const pos = clampPopupPos(rect.right + 8, rect.top)
  const res = selectedResource.value
  const currentModule = modules.value.find(m => m.resources.some(r => r.id === res?.id))

  selectionPopup.value = {
    show: true,
    x: pos.x,
    y: pos.y,
    text: content,
    planId: planId.value,
    resourceId: res?.id || 0,
    resourceTitle: res?.moduleData?.title || '学习资源',
    moduleName: currentModule?.title || '',
    mode: 'heading',
  }
  showNoteList.value = false
}

function extractHeadingContentMd(headingEl: HTMLElement): string {
  const headingLevel = parseInt(headingEl.tagName.charAt(1))
  const parts: string[] = []
  // 标题自身
  const headingText = headingEl.textContent?.trim()
  if (headingText) parts.push(headingText)
  // 遍历后续兄弟节点
  let sibling = headingEl.nextElementSibling
  while (sibling) {
    if (/^H[1-6]$/.test(sibling.tagName)) {
      const siblingLevel = parseInt(sibling.tagName.charAt(1))
      if (siblingLevel <= headingLevel) break
    }
    // 提取图片
    const imgs = sibling.querySelectorAll('img')
    imgs.forEach(img => {
      const src = img.getAttribute('src')
      if (src) {
        const alt = img.getAttribute('alt') || ''
        parts.push(`![${alt}](${src})`)
      }
    })
    // 提取文本（去掉 img alt 文本避免重复）
    const clone = sibling.cloneNode(true) as HTMLElement
    clone.querySelectorAll('img').forEach(img => img.remove())
    const text = clone.textContent?.trim()
    if (text) parts.push(text)
    sibling = sibling.nextElementSibling
  }
  return parts.join('\n').trim()
}

function extractRangeContent(range: Range): string {
  const BLOCK_TAGS = new Set(['P', 'DIV', 'LI', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'BLOCKQUOTE', 'TR', 'SECTION', 'ARTICLE'])
  const parts: string[] = []

  // 获取选区内的文档片段
  const fragment = range.cloneContents()

  // 递归遍历节点
  function walk(node: Node) {
    if (node.nodeType === Node.TEXT_NODE) {
      const t = node.textContent || ''
      if (t.trim()) parts.push(t)
      return
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return
    const el = node as HTMLElement

    // img 标签
    if (el.tagName === 'IMG') {
      const src = el.getAttribute('src')
      if (src) {
        parts.push(`\n![${el.getAttribute('alt') || ''}](${src})\n`)
      }
      return
    }

    // br
    if (el.tagName === 'BR') {
      parts.push('\n')
      return
    }

    // 块级元素：前后加换行
    const isBlock = BLOCK_TAGS.has(el.tagName)
    if (isBlock) parts.push('\n')

    // 递归子节点
    el.childNodes.forEach(child => walk(child))

    if (isBlock) parts.push('\n')
  }

  fragment.childNodes.forEach(child => walk(child))

  // 清理：合并连续空行，trim
  return parts.join('')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function formatNoteContent(text: string): string {
  return text
}

function buildPositionInfo(): string {
  const p = selectionPopup.value
  // 去掉图片 markdown，只保留纯文本用于定位
  const plainText = p.text.replace(/!\[[^\]]*\]\([^)]*\)/g, '').trim()
  if (p.mode === 'heading') {
    const firstLine = plainText.split('\n')[0].trim().substring(0, 80)
    return `heading:${firstLine}`
  }
  const snippet = plainText.substring(0, 50).replace(/\n/g, ' ').trim()
  return `selection:${snippet}`
}

async function addToNewNote() {
  const text = selectionPopup.value.text
  clearHighlight()
  selectionPopup.value.show = false
  showNoteList.value = false
  if (!text) return

  try {
    const p = selectionPopup.value
    const noteName = `摘录 - ${p.resourceTitle}`
    const content = formatNoteContent(text)
    const res = await createNote({ noteName, content })
    const noteId = (res as any)?.data?.id
    if (noteId && p.resourceId) {
      await linkNoteToResource(noteId, {
        resourceId: p.resourceId,
        selectedText: text.substring(0, 5000),
        positionInfo: buildPositionInfo(),
        planId: p.planId,
        moduleName: p.moduleName,
        resourceTitle: p.resourceTitle,
      }).catch(() => {})
    }
  } catch (e) {
    console.error('Failed to create note from selection:', e)
  }
}

async function loadAvailableNotes() {
  try {
    const res = await getNotes({ page: 1, size: 20 })
    availableNotes.value = res.data?.records || []
  } catch {
    availableNotes.value = []
  }
}

function toggleNoteList() {
  if (!showNoteList.value) {
    loadAvailableNotes()
  }
  showNoteList.value = !showNoteList.value
}

async function appendToExistingNote(note: Note) {
  const text = selectionPopup.value.text
  clearHighlight()
  selectionPopup.value.show = false
  showNoteList.value = false
  if (!text) return

  try {
    const p = selectionPopup.value
    const existing = note.content || ''
    const newContent = existing + (existing ? '\n\n' : '') + formatNoteContent(text)
    await updateNote(note.id, { noteName: note.noteName, content: newContent })
    if (p.resourceId) {
      await linkNoteToResource(note.id, {
        resourceId: p.resourceId,
        selectedText: text.substring(0, 5000),
        positionInfo: buildPositionInfo(),
        planId: p.planId,
        moduleName: p.moduleName,
        resourceTitle: p.resourceTitle,
      }).catch(() => {})
    }
  } catch (e) {
    console.error('Failed to append to note:', e)
  }
}

function onDocumentMouseDown(e: MouseEvent) {
  const popup = document.querySelector('.selection-popup')
  if (popup && !popup.contains(e.target as Node)) {
    clearHighlight()
    selectionPopup.value.show = false
    showNoteList.value = false
  }
}

// ==================== 面板拖拽调整 ====================
const panelWidth = ref(window.innerWidth > 1400 ? 760 : 560)
const isDragging = ref(false)

// 中间面板的宽度样式（包含关闭态：width=0，由 CSS transition 驱动动画）
const panelStyle = computed(() => {
  if (isFullscreen.value) {
    return {}
  }
  if (!selectedResource.value && !showResourceStreamPreview.value) {
    return { width: '0px', minWidth: '0px', marginLeft: '0px', marginRight: '0px' }
  }
  return { width: panelWidth.value + 'px', minWidth: '240px' }
})

// 是否显示资源流式生成预览（中间面板）
const showResourceStreamPreview = computed(() => chatStore.isResourceStreaming && Object.keys(chatStore.resourceStreamBuffers).length > 0)

interface DragState {
  containerLeft: number
  sidebarW: number
  collapseW: number
  offset: number
  pendingWidth: number
  rafId: number | null
}

let dragState: DragState | null = null

function onDividerMouseDown(e: MouseEvent) {
  e.preventDefault()
  isDragging.value = true

  const container = document.querySelector('.flex.gap-0')
  if (!container) return
  const rect = container.getBoundingClientRect()
  const sidebarEl = container.children[0] as HTMLElement
  const collapseBtn = container.children[1] as HTMLElement

  dragState = {
    containerLeft: rect.left,
    sidebarW: sidebarEl?.offsetWidth || 280,
    collapseW: collapseBtn?.offsetWidth || 24,
    offset: 8,
    pendingWidth: panelWidth.value,
    rafId: null,
  }

  document.addEventListener('mousemove', onDividerMouseMove)
  document.addEventListener('mouseup', onDividerMouseUp)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function onDividerMouseMove(e: MouseEvent) {
  if (!dragState) return
  const maxLimit = Math.max(300, window.innerWidth - (sidebarCollapsed.value ? 360 : 640))
  dragState.pendingWidth = Math.max(280, Math.min(maxLimit,
    e.clientX - dragState.containerLeft - dragState.sidebarW - dragState.collapseW - dragState.offset
  ))

  if (dragState.rafId === null) {
    dragState.rafId = requestAnimationFrame(() => {
      if (!dragState) return
      dragState.rafId = null
      panelWidth.value = dragState.pendingWidth
    })
  }
}

function endDrag() {
  isDragging.value = false
  if (dragState) {
    if (dragState.rafId !== null) {
      cancelAnimationFrame(dragState.rafId)
      dragState.rafId = null
    }
    panelWidth.value = dragState.pendingWidth
  }
  dragState = null
  document.removeEventListener('mousemove', onDividerMouseMove)
  document.removeEventListener('mouseup', onDividerMouseUp)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

function onDividerMouseUp() { endDrag() }

let refreshTimer: ReturnType<typeof setInterval> | null = null
// 在组件卸载前清理资源
onBeforeUnmount(() => {
  document.body.style.userSelect = ''
})

onUnmounted(() => {
  chatStore.stopRecovering()
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null }
  if (dragState) {
    if (dragState.rafId !== null) {
      cancelAnimationFrame(dragState.rafId)
    }
    dragState = null
  }
  document.removeEventListener('mousemove', onDividerMouseMove)
  document.removeEventListener('mouseup', onDividerMouseUp)
  window.removeEventListener('keydown', handleKeyDown)
  document.removeEventListener('mousedown', onDocumentMouseDown)
})

// ==================== 状态 ====================
const plan = ref<LearningPlan | null>(null)
const resources = ref<LearningResource[]>([])
const stuckResources = ref(new Set<number>())
const selectedModuleIndex = ref(-1)
const selectedResourceId = ref<number | null>(null)
const selectedResource = ref<LearningResource | null>(null)
const isFullscreen = ref(false)
const quizData = ref<QuizData | null>(null)
const mindmapData = ref<MindElixirData | null>(null)
const gradingResult = ref<Record<string, any> | null>(null)
const quizSubmittedAnswers = ref<Record<number, any> | null>(null)
const showExplanations = ref(false)
const showCitations = ref(true)

// 逐题批改结果（按 index 索引，供 QuizPlayer 使用）
const questionResults = computed(() => {
  const details = gradingResult.value?.details
  if (!details?.length) return null
  const map: Record<number, any> = {}
  details.forEach((d: any, i: number) => { map[d.index ?? i] = d })
  return map
})
const quizSubmitting = ref(false)
const sidebarCollapsed = ref(false)

// ==================== 数据加载 ====================
async function loadPlan() {
  const id = planId.value
  if (!id) return
  try {
    const res = await getPlan(id)
    plan.value = res.data
  } catch (e) {
    console.error('[PlanDetail] 加载计划失败:', e)
  }
}

async function loadResources() {
  const id = planId.value
  if (!id) return
  try {
    const res = await getPlanResources(id)
    const list = res.data || []
    parseModuleData(list)
    resources.value = list

    // 检测卡住的资源：status=1 但 task 也是 status=1（没有在真正执行）
    const stuck = new Set<number>()
    const generating = list.filter((r: LearningResource) => r.status === 1)
    await Promise.all(generating.map(async (r: LearningResource) => {
      try {
        const { data: task } = await getLatestTask(r.id)
        if (!task || task.taskStatus === 1) {
          stuck.add(r.id)
        }
      } catch {}
    }))
    stuckResources.value = stuck
  } catch (e) {
    console.error('[PlanDetail] 加载资源失败:', e)
  }
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape' && isFullscreen.value) {
    isFullscreen.value = false
  }
}

onMounted(async () => {
  loadPlan()
  await loadResources()
  window.addEventListener('keydown', handleKeyDown)
  document.addEventListener('mousedown', onDocumentMouseDown)
  // 支持 ?resource=xxx 跳转自动打开对应资源
  const queryResource = route.query.resource
  if (queryResource) {
    const resId = Number(queryResource)
    if (resId > 0) {
      openResourceById(resId)
    }
  }
})

watch(selectedResource, (newRes) => {
  if (!newRes) {
    isFullscreen.value = false
  }
})

watch(planId, () => {
  if (planId.value) {
    heartbeat.stop()
    loadPlan()
    loadResources()
    selectedModuleIndex.value = -1
    selectedResourceId.value = null
    selectedResource.value = null
    quizData.value = null
    mindmapData.value = null
    gradingResult.value = null
    quizSubmittedAnswers.value = null
  }
})

// 监听 ?resource= 查询参数变化（同 plan 内跳转不同资源）
watch(() => route.query.resource, (resId) => {
  if (resId && resources.value.length > 0) {
    openResourceById(Number(resId))
  }
})

// 标题编辑
const editingTitle = ref(false)
const editTitle = ref('')

function saveTitle() {
  if (!editTitle.value.trim() || !plan.value) return
  plan.value.title = editTitle.value.trim()
  editingTitle.value = false
  updatePlan(planId.value, { title: plan.value.title }).catch(e =>
    console.error('[PlanDetail] 保存标题失败:', e)
  )
}

function statusClass(status: number) {
  return status === 2 ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
}

function statusText(status: number) {
  return status === 2 ? '已完成' : '进行中'
}

function badgeClass(type: string) {
  const map: Record<string, string> = {
    document: 'bg-blue-100 text-blue-700',
    text: 'bg-blue-100 text-blue-700',
    mindmap: 'bg-purple-100 text-purple-700',
    quiz: 'bg-amber-100 text-amber-700',
    code: 'bg-green-100 text-green-700',
    reading: 'bg-cyan-100 text-cyan-700',
    summary: 'bg-indigo-100 text-indigo-700',
    video: 'bg-rose-100 text-rose-700',
    image: 'bg-pink-100 text-pink-700',
    diagram: 'bg-teal-100 text-teal-700',
    animation: 'bg-orange-100 text-orange-700',
    podcast: 'bg-emerald-100 text-emerald-700',
  }
  return map[type] || 'bg-navy-100 text-navy-700'
}

function parseModuleData(resources: LearningResource[]) {
  resources.forEach(r => {
    if (typeof r.moduleData === 'string') {
      try {
        r.moduleData = JSON.parse(r.moduleData)
      } catch {
        r.moduleData = { content: r.moduleData }
      }
    }
    r.moduleData = normalizeResourceModuleData(r.moduleType, r.moduleData || {})
  })
}

function normalizeResourceModuleData(moduleType: string, rawData: Record<string, any>): Record<string, any> {
  const moduleData = { ...rawData }
  const nested = moduleData.generated_content || moduleData.data || null
  if (nested && typeof nested === 'object') {
    Object.assign(moduleData, nested, moduleData)
  }

  if (moduleType === 'animation') {
    const html = moduleData.html || moduleData.content || ''
    moduleData.html = html
    moduleData.content = moduleData.content || html
  } else if (moduleType === 'mindmap') {
    const nodeData = moduleData.nodeData || moduleData.node_data
    if (!moduleData.content && nodeData) {
      moduleData.content = typeof nodeData === 'string' ? nodeData : JSON.stringify(nodeData)
    }
  } else {
    moduleData.content = moduleData.content || moduleData.html || ''
  }

  return moduleData
}

function moduleDataFromGeneratedResource(resource: GeneratedResourceRef): Record<string, any> {
  const generated = resource.generated_content || resource.moduleData || resource.data || {}
  const moduleType = resource.type || generated.module_type || generated.moduleType || 'document'
  const baseData: Record<string, any> = {
    ...generated,
    title: generated.title || resource.title,
    description: generated.description || '',
    content: generated.content || resource.content || '',
  }

  if (moduleType === 'animation') {
    const html = generated.html || resource.html || baseData.content || ''
    baseData.html = html
    baseData.content = baseData.content || html
  }
  if (moduleType === 'mindmap') {
    const nodeData = generated.nodeData || resource.nodeData
    if (nodeData && !baseData.content) {
      baseData.content = typeof nodeData === 'string' ? nodeData : JSON.stringify(nodeData)
    }
    if (nodeData) baseData.nodeData = nodeData
  }

  return normalizeResourceModuleData(moduleType, baseData)
}

function upsertGeneratedResource(resource: GeneratedResourceRef): LearningResource {
  const existing = resource.id ? resources.value.find(r => r.id === resource.id) : null
  const moduleType = resource.type || existing?.moduleType || resource.generated_content?.module_type || 'document'
  const moduleData = moduleDataFromGeneratedResource({ ...resource, type: moduleType })

  if (existing) {
    existing.moduleType = moduleType
    existing.moduleData = { ...existing.moduleData, ...moduleData }
    existing.status = resource.status ?? 2
    existing.updatedAt = new Date().toISOString()
    return existing
  }

  const moduleOrder = resources.value.length > 0
    ? Math.max(...resources.value.map(r => r.moduleOrder)) + 1 : 1
  const newResource: LearningResource = {
    id: resource.id || Date.now(),
    planId: planId.value,
    parentId: null,
    moduleOrder,
    moduleType,
    moduleData,
    status: resource.status ?? 2,
    storagePath: null,
    generatedByAgent: moduleType === 'animation' ? 'animation_skill_generator' : 'resource_type_generator',
    version: 1,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
  resources.value.push(newResource)
  return newResource
}

const typeLabels: Record<string, string> = {
  document: '文档', text: '图文', mindmap: '导图', quiz: '题目', code: '代码', reading: '阅读', summary: '总结', video: '视频', image: '图片', diagram: '图表', animation: '动画', podcast: '播客',
}

// ==================== 计算属性 ====================

// 按 moduleOrder 分组构建模块列表
const modules = computed(() => {
  const moduleMap = new Map<number, { order: number; title: string; estimatedHours: number; resourceTypes: string[]; resources: LearningResource[] }>()
  resources.value.forEach(r => {
    if (!moduleMap.has(r.moduleOrder)) {
      moduleMap.set(r.moduleOrder, {
        order: r.moduleOrder,
        title: r.moduleData?.module_title || r.moduleData?.title || `模块 ${r.moduleOrder}`,
        estimatedHours: r.moduleData?.estimated_hours || 2,
        resourceTypes: [],
        resources: [],
      })
    }
    const mod = moduleMap.get(r.moduleOrder)!
    if (!mod.resourceTypes.includes(r.moduleType)) {
      mod.resourceTypes.push(r.moduleType)
    }
    mod.resources.push(r)
  })
  return Array.from(moduleMap.values()).sort((a, b) => a.order - b.order)
})

function renderMd(text: string) { return parseMarkdown(text) }

// 缓存资源内容的 markdown 渲染结果，避免每次 Vue 重渲染都重新解析
const renderedResourceContent = computed(() => {
  let content = selectedResource.value?.moduleData?.content
  if (!content) return ''
  // 移除 markdown 中的参考文献列表部分，避免双重显示
  const refHeaders = ['## 参考文献', '### 参考文献', '## 参考资料', '### 参考资料', '## 引用文献', '### 引用文献']
  for (const header of refHeaders) {
    const idx = content.indexOf(header)
    if (idx !== -1) {
      content = content.substring(0, idx).trim()
      break
    }
  }
  return renderMd(content)
})

// === 引用源（Citation）解析与交互逻辑 ===
const hoveredCitation = ref<{ id: string; title: string; url: string; domain: string } | null>(null)
const popoverX = ref(0)
const popoverY = ref(0)
const popoverPlacement = ref<'top' | 'bottom'>('top')
let popoverTimeout: ReturnType<typeof setTimeout> | null = null

const popoverStyle = computed(() => {
  return {
    left: `${popoverX.value}px`,
    top: `${popoverY.value}px`,
    transform: popoverPlacement.value === 'top' ? 'translate(-50%, -100%) translateY(-8px)' : 'translate(-50%, 8px)'
  }
})

const currentResourceCitations = computed(() => {
  const md = selectedResource.value?.moduleData?.content || ''
  const dbRefs = selectedResource.value?.moduleData?.references || []
  
  // 1. 从 Markdown 内容中提取引用
  const extracted = extractCitations(md)
  
  // 2. 合并提取到的和数据库保存的引用列表（以 ID 去重）
  const refsMap = new Map<string, { id: string; title: string; url: string }>()
  extracted.forEach(c => refsMap.set(c.id, c))
  
  dbRefs.forEach((refStr: string) => {
    if (typeof refStr !== 'string') return
    const match = refStr.match(/^\[(\d+|page\d+)\]\s*(.*?)\s*(?:-|:|来源:)\s*(https?:\/\/[^\s\)]+)/i)
    if (match) {
      const id = match[1]
      refsMap.set(id, {
        id,
        title: match[2].trim() || `来源 [${id}]`,
        url: match[3].trim()
      })
    } else {
      const simpleMatch = refStr.match(/^\[(\d+|page\d+)\]\s*(https?:\/\/[^\s\)]+)/i)
      if (simpleMatch) {
        const id = simpleMatch[1]
        refsMap.set(id, {
          id,
          title: `网页来源 [${id}]`,
          url: simpleMatch[2].trim()
        })
      }
    }
  })
  
  // 3. 排序：数字引用在前，page 引用在后，按 ID 数字升序排列
  return Array.from(refsMap.values()).sort((a, b) => {
    const aIsPage = a.id.startsWith('page')
    const bIsPage = b.id.startsWith('page')
    if (aIsPage && !bIsPage) return 1
    if (!aIsPage && bIsPage) return -1
    const aNum = parseInt(a.id.replace('page', '')) || 0
    const bNum = parseInt(b.id.replace('page', '')) || 0
    return aNum - bNum
  })
})

function getDomainName(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

function handleCitationMouseOver(e: MouseEvent) {
  const target = (e.target as HTMLElement).closest('.citation-ref') as HTMLElement
  if (!target) return

  if (popoverTimeout) clearTimeout(popoverTimeout)

  const refId = target.getAttribute('data-ref') || ''
  const cit = currentResourceCitations.value.find(c => c.id === refId)
  if (!cit) return

  const rect = target.getBoundingClientRect()
  popoverX.value = rect.left + rect.width / 2
  
  // 边缘检测：如果元素距离顶部太近，气泡向下展示，否则向上
  if (rect.top < 150) {
    popoverPlacement.value = 'bottom'
    popoverY.value = rect.bottom
  } else {
    popoverPlacement.value = 'top'
    popoverY.value = rect.top
  }

  hoveredCitation.value = {
    id: cit.id,
    title: cit.title,
    url: cit.url,
    domain: getDomainName(cit.url)
  }
}

function handleCitationMouseOut(e: MouseEvent) {
  if (popoverTimeout) clearTimeout(popoverTimeout)
  const target = (e.target as HTMLElement).closest('.citation-ref') as HTMLElement
  const related = e.relatedTarget as HTMLElement
  // 如果离开后进入的元素依然属于当前 citation-ref，则忽略，避免抖动
  if (target && related && target.contains(related)) {
    return
  }
  
  popoverTimeout = setTimeout(() => {
    hoveredCitation.value = null
  }, 250)
}

function clearPopoverTimeout() {
  if (popoverTimeout) clearTimeout(popoverTimeout)
}

function handleCitationClick(e: MouseEvent) {
  const target = (e.target as HTMLElement).closest('.citation-ref') as HTMLElement
  if (!target) return
  
  const url = target.getAttribute('data-url')
  if (url) {
    window.open(url, '_blank')
  }
}

const animationHtml = computed(() => {
  const md = selectedResource.value?.moduleData
  if (!md) return ''
  return normalizeAnimationHtml(md.html || md.content || '')
})

function escapeJsonForHtml(value: string) {
  return JSON.stringify(value)
    .replace(/</g, '\\u003C')
    .replace(/>/g, '\\u003E')
    .replace(/&/g, '\\u0026')
}

function normalizeAnimationHtml(raw: string) {
  if (!raw) return ''
  const html = String(raw)

  const payload = escapeJsonForHtml(html)
  const closeScript = '<' + '/script>'
  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    * { box-sizing: border-box; }
    html, body { margin: 0; width: 100vw; height: 100vh; overflow: hidden; background: #050505; }
    .viewport { position: relative; width: 100vw; height: 100vh; display: grid; place-items: center; overflow: hidden; background: #050505; }
    .stage { position: relative; width: min(100vw, calc(100vh * 16 / 9)); height: min(100vh, calc(100vw * 9 / 16)); aspect-ratio: 16 / 9; overflow: hidden; background: #050505; }
    iframe { position: absolute; width: 1920px; height: 1080px; border: 0; transform-origin: top left; background: #050505; }
    .legacy-control-bar { position: absolute; left: 50%; bottom: 10px; z-index: 20; transform: translateX(-50%); display: flex; gap: 8px; align-items: center; padding: 8px 10px; border: 1px solid rgba(255,255,255,.16); border-radius: 14px; background: rgba(0,0,0,.68); backdrop-filter: blur(16px); }
    .legacy-control-bar button { width: 38px; height: 34px; border: 1px solid rgba(255,255,255,.16); border-radius: 10px; background: rgba(255,255,255,.08); color: #f5f5f7; cursor: pointer; font-size: 16px; }
    .legacy-control-bar button:hover { background: rgba(255,255,255,.16); }
    .legacy-progress { min-width: 46px; text-align: center; color: rgba(245,245,247,.68); font: 12px/1.2 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; font-variant-numeric: tabular-nums; }
  </style>
</head>
<body>
  <div class="viewport">
    <div class="stage">
      <iframe title="教学动画内容" allow="autoplay"></iframe>
      <nav class="legacy-control-bar" aria-label="动画控制">
        <button type="button" data-action="prev" aria-label="上一页">‹</button>
        <button type="button" data-action="pause" aria-label="暂停">Ⅱ</button>
        <button type="button" data-action="replay" aria-label="重播">↻</button>
        <button type="button" data-action="next" aria-label="下一页">›</button>
        <span class="legacy-progress" aria-live="polite"></span>
      </nav>
    </div>
  </div>
  <script type="application/json" id="animation-html">${payload}${closeScript}
  <script>
    (() => {
      const stage = document.querySelector('.stage');
      const frame = document.querySelector('iframe');
      const pauseButton = document.querySelector('[data-action="pause"]');
      const progress = document.querySelector('.legacy-progress');
      let paused = false;
      let autoplayTimer = null;
      const raw = JSON.parse(document.getElementById('animation-html').textContent || '""');
      const closeScriptTag = '<' + '/script>';
      const intervalShim = '<script>(()=>{const nativeSetInterval=window.setInterval.bind(window);window.__AURA_LEGACY_PAUSED=false;window.setInterval=(fn,delay,...args)=>nativeSetInterval(()=>{if(!window.__AURA_LEGACY_PAUSED)fn(...args)},delay);window.__AURA_LEGACY_PAUSE=()=>{window.__AURA_LEGACY_PAUSED=true;document.getAnimations({subtree:true}).forEach(animation=>animation.pause())};window.__AURA_LEGACY_PLAY=()=>{window.__AURA_LEGACY_PAUSED=false;document.getAnimations({subtree:true}).forEach(animation=>animation.play())}})();' + closeScriptTag;
      const controlHideStyle = '<style>.animation-control-bar,nav[aria-label="动画控制"]{display:none!important}</style>';
      const instrumented = /<head[^>]*>/i.test(raw)
        ? raw.replace(/<head[^>]*>/i, match => match + intervalShim + controlHideStyle)
        : intervalShim + controlHideStyle + raw;
      frame.srcdoc = instrumented;

      function fit() {
        const rect = stage.getBoundingClientRect();
        const scale = Math.min(rect.width / 1920, rect.height / 1080);
        frame.style.transform = 'scale(' + scale + ')';
        frame.style.left = Math.max(0, (rect.width - 1920 * scale) / 2) + 'px';
        frame.style.top = Math.max(0, (rect.height - 1080 * scale) / 2) + 'px';
      }

      function innerDocument() {
        return frame.contentDocument;
      }

      function innerBeats() {
        const doc = innerDocument();
        return doc ? [...doc.querySelectorAll('.beat')] : [];
      }

      function innerActiveIndex() {
        const beats = innerBeats();
        const index = beats.findIndex(beat => beat.classList.contains('active'));
        return { beats, index: Math.max(0, index) };
      }

      function syncProgress() {
        const { beats, index } = innerActiveIndex();
        progress.textContent = beats.length ? (index + 1) + ' / ' + beats.length : '';
      }

      function replayInnerAnimations() {
        const doc = innerDocument();
        const active = doc?.querySelector('.beat.active') || doc?.body;
        active?.getAnimations({ subtree: true }).forEach(animation => {
          animation.cancel();
          animation.play();
        });
      }

      function showInnerBeat(nextIndex) {
        const { beats } = innerActiveIndex();
        if (!beats.length) return false;
        const normalized = ((nextIndex % beats.length) + beats.length) % beats.length;
        beats.forEach((beat, index) => beat.classList.toggle('active', index === normalized));
        syncProgress();
        requestAnimationFrame(replayInnerAnimations);
        return true;
      }

      function findInnerButton(action) {
        const doc = innerDocument();
        if (!doc) return null;
        const matchers = {
          prev: text => /上一|prev|‹|←/i.test(text),
          next: text => /下一|next|›|→/i.test(text),
          replay: text => /重播|replay|↻|restart/i.test(text),
          pause: text => /暂停|播放|pause|play|Ⅱ|▶/i.test(text),
        };
        return [...doc.querySelectorAll('button')].find(button => {
          const text = [
            button.getAttribute('data-action'),
            button.getAttribute('aria-label'),
            button.textContent,
          ].filter(Boolean).join(' ');
          return text.includes(action) || matchers[action](text);
        }) || null;
      }

      function runInnerAction(action, delta = 0) {
        if (action === 'prev' || action === 'next') {
          const { index } = innerActiveIndex();
          if (showInnerBeat(index + delta)) return true;
        }
        if (action === 'replay') {
          replayInnerAnimations();
          return true;
        }
        const button = findInnerButton(action);
        if (button) {
          button.click();
          setTimeout(syncProgress, 0);
          return true;
        }
        return false;
      }

      function setPaused(nextPaused) {
        paused = nextPaused;
        pauseButton.textContent = paused ? '▶' : 'Ⅱ';
        pauseButton.setAttribute('aria-label', paused ? '播放' : '暂停');
        const inner = frame.contentWindow;
        if (paused) {
          const innerPause = findInnerButton('pause');
          if (innerPause && /暂停|pause|Ⅱ/i.test((innerPause.getAttribute('aria-label') || '') + innerPause.textContent)) {
            innerPause.click();
          }
          inner?.__AURA_LEGACY_PAUSE?.();
        } else {
          const innerPause = findInnerButton('pause');
          if (innerPause && /播放|play|▶/i.test((innerPause.getAttribute('aria-label') || '') + innerPause.textContent)) {
            innerPause.click();
          }
          inner?.__AURA_LEGACY_PLAY?.();
        }
      }

      function startAutoplay() {
        if (autoplayTimer) clearInterval(autoplayTimer);
        autoplayTimer = setInterval(() => {
          if (paused) return;
          runInnerAction('next', 1);
        }, 4200);
      }

      document.querySelector('.legacy-control-bar').addEventListener('click', event => {
        const button = event.target.closest('button');
        if (!button) return;
        const action = button.getAttribute('data-action');
        if (action === 'pause') {
          setPaused(!paused);
          return;
        }
        if (action === 'prev') runInnerAction('prev', -1);
        else if (action === 'next') runInnerAction('next', 1);
        else if (action === 'replay' && !runInnerAction('replay')) {
          frame.srcdoc = instrumented;
          requestAnimationFrame(fit);
        }
        startAutoplay();
      });

      window.addEventListener('resize', fit);
      frame.addEventListener('load', () => {
        fit();
        syncProgress();
        startAutoplay();
      });
      requestAnimationFrame(fit);
    })();
  ${closeScript}
</body>
</html>`
}

// ==================== 资源详情 ====================

function selectModule(index: number) {
  if (selectedModuleIndex.value === index) {
    // 收起当前模块，清除选中状态
    selectedModuleIndex.value = -1
    selectedResourceId.value = null
    selectedResource.value = null
    quizData.value = null
    mindmapData.value = null
    gradingResult.value = null
    quizSubmittedAnswers.value = null
    showExplanations.value = false
    return
  }
  // 展开模块并自动选中第一个资源
  selectedModuleIndex.value = index
  const mod = modules.value[index]
  if (mod?.resources.length > 0) {
    toggleResource(mod.resources[0])
  }
}

async function handleRetry(res: LearningResource) {
  try {
    const { data: task } = await getLatestTask(res.id)
    if (!task) return
    await retryTaskApi(task.id)
    res.status = 1
    // 轮询等待生成结果
    const poll = setInterval(async () => {
      try {
        const { data: updated } = await getLatestTask(res.id)
        if (updated && (updated.taskStatus === 2 || updated.taskStatus === 3)) {
          clearInterval(poll)
          res.status = updated.taskStatus === 2 ? 2 : 3
          loadResources()
        }
      } catch {
        clearInterval(poll)
      }
    }, 3000)
  } catch (e) {
    console.error('重试失败:', e)
  }
}

function toggleResource(res: LearningResource) {
  // 点击已选中的资源 → 取消选中
  if (selectedResourceId.value === res.id) {
    heartbeat.stop()
    selectedResourceId.value = null
    selectedResource.value = null
    quizData.value = null
    mindmapData.value = null
    gradingResult.value = null
    quizSubmittedAnswers.value = null
    showExplanations.value = false
    chatStore.selectedModuleContext = null
    return
  }

  // Stop previous heartbeat if switching resource
  if (selectedResourceId.value !== null) {
    heartbeat.stop()
  }

  selectedResourceId.value = res.id
  selectedResource.value = res

  // Start heartbeat for this resource
  heartbeat.start(planId.value, res.id)
  gradingResult.value = null
  quizSubmittedAnswers.value = null
  showExplanations.value = false

  // Notify chat panel of resource type for follow-up template
  planChatPanelRef.value?.updateResourceTitle(res.moduleData?.title || res.moduleData?.module_title || `模块 ${res.moduleOrder}`)
  planChatPanelRef.value?.updateResourceType(res.moduleType || '')

  // 展开侧栏中包含该资源的模块
  const modIdx = modules.value.findIndex(m => m.resources.some(r => r.id === res.id))
  if (modIdx >= 0) {
    selectedModuleIndex.value = modIdx
  }

  // 解析题目数据
  if (res.moduleType === 'quiz') {
    quizData.value = parseQuizData(res)
    mindmapData.value = null
    // 优先从 module_data.latestResult 恢复批改结果，否则从 quiz_record 表加载
    const lr = res.moduleData?.latestResult
    if (lr && lr.details) {
      quizSubmittedAnswers.value = lr.answers || {}
      gradingResult.value = {
        score: lr.score,
        total: lr.total,
        correct: lr.correct,
        details: lr.details,
      }
    } else {
      loadQuizRecords(res.id)
    }
  } else if (res.moduleType === 'mindmap') {
    quizData.value = null
    mindmapData.value = parseMindmapData(res)
  } else {
    quizData.value = null
    mindmapData.value = null
  }

  // 设置模块上下文并提示用户可以生成补充资源
  const moduleTitle = res.moduleData?.module_title || res.moduleData?.title || `模块 ${res.moduleOrder}`
  const moduleDesc = res.moduleData?.description || res.moduleData?.module_description || ''
  chatStore.selectedModuleContext = {
    title: moduleTitle,
    description: moduleDesc,
    moduleId: res.id,
    planId: res.planId || planId.value,
  }
  // 仅在非 quiz 资源时提示（quiz 本身已是补充资源）
  if (res.moduleType !== 'quiz') {
  } else {
  }
}

/** 通过资源 ID 打开资源（先从本地列表查找，未命中则请求后端） */
async function openResourceById(resourceId: number, resourceType?: string) {
  // 先从本地已加载的资源中查找
  const local = resources.value.find(r => r.id === resourceId)
  if (local) {
    toggleResource(local)
    return
  }
  // 本地未命中，从后端获取
  try {
    const res = await getResource(resourceId)
    if (res.data) {
      // 解析 moduleData
      parseModuleData([res.data])
      // 添加到本地列表（避免重复）
      if (!resources.value.some(r => r.id === res.data.id)) {
        resources.value.push(res.data)
      }
      toggleResource(res.data)
    }
  } catch (e) {
    console.error('Failed to open resource by ID:', e)
  }
}

function parseQuizData(res: LearningResource): QuizData | null {
  const md = res.moduleData
  if (!md) return null

  // questions 可能在顶层、md.content 对象里、或 md.content JSON 字符串里
  let rawQuestions = md.questions || []
  if (rawQuestions.length === 0 && md.content) {
    try {
      const c = typeof md.content === 'string' ? JSON.parse(md.content) : md.content
      rawQuestions = c?.questions || []
    } catch {}
  }

  // 如果仍未找到结构化 questions，将 content 文本解析为简答题
  if (rawQuestions.length === 0) {
    const text = typeof md.content === 'string' ? md.content : (md.description || '')
    if (!text.trim()) return null
    rawQuestions = [{
      type: 'short_answer',
      question: text.trim(),
      correctAnswer: '',
      explanation: '',
      difficulty: 3,
      points: 1,
    }]
  }

  const questions: QuizQuestion[] = rawQuestions.map((q: any, i: number) => ({
    index: q.index ?? i,
    type: q.type || q.question_type || 'short_answer',
    question: q.question || q.question_text || '',
    options: q.options || undefined,
    correctAnswer: q.correctAnswer ?? q.correct_answer ?? '',
    explanation: q.explanation || '',
    difficulty: q.difficulty || 3,
    points: q.points || 1,
  }))

  return {
    title: md.title || md.quiz_title || '练习题',
    description: md.description || '',
    questions,
    totalPoints: md.totalPoints || md.total_points || questions.length,
    estimatedMinutes: md.estimatedMinutes || questions.length * 2,
  }
}

function parseMindmapData(res: LearningResource): MindElixirData | null {
  const md = res.moduleData
  const rawNodeData = md?.nodeData || md?.node_data || md?.content
  if (!rawNodeData) return null

  try {
    // content 应该是 MindElixir nodeData 的 JSON 字符串，也兼容 nodeData 对象
    const parsed = typeof rawNodeData === 'string' ? JSON.parse(rawNodeData) : rawNodeData

    // 验证基本结构：必须有 id 和 topic
    if (!parsed || !parsed.topic) return null

    return {
      nodeData: parsed,
      direction: 2, // SIDE: 左右分布
    } as MindElixirData
  } catch {
    // JSON 解析失败，尝试将纯文本包装为简单的思维导图
    const text = typeof rawNodeData === 'string' ? rawNodeData : ''
    if (!text.trim()) return null

    // 按行拆分，每行作为一个子节点
    const lines = text.split('\n').filter(l => l.trim()).slice(0, 20)
    return {
      nodeData: {
        id: 'root',
        topic: res.moduleData?.module_title || res.moduleData?.title || '思维导图',
        expanded: true,
        children: lines.map((line, i) => ({
          id: `n${i}`,
          topic: line.replace(/^[-*•\d.]+\s*/, '').trim(),
        })),
      },
      direction: 2,
    } as MindElixirData
  }
}

// ==================== 答题提交 ====================

function onQuizSubmit(userAnswers: Record<number, any>) {
  if (!selectedResource.value || quizSubmitting.value) return
  quizSubmitting.value = true
  gradingResult.value = null
  quizSubmittedAnswers.value = userAnswers
  showExplanations.value = false

  issueTicket().then(ticketRes => {
    const ticket = ticketRes.data.ticket
    submitQuizSSE(
      ticket,
      selectedResource.value!.id,
      planId.value,
      userAnswers,
      {
        onProgress(content) {
          // 可选：在对话区显示进度
          console.debug('[Quiz] progress:', content)
        },
        onQuestionResult(index, result) {
          console.debug(`[Quiz] Q${index + 1}:`, result.is_correct ? 'correct' : 'incorrect')
        },
        onQuizResult(result) {
          gradingResult.value = {
            score: result.score,
            total: result.total,
            correct: result.correct,
            details: result.details,
          }
          // 同步更新本地资源的 moduleData.latestResult，避免重新打开时再请求
          const res = selectedResource.value
          if (res && res.moduleData) {
            res.moduleData.latestResult = {
              answers: userAnswers,
              score: result.score,
              total: result.total,
              correct: result.correct,
              details: result.details,
            }
          }
        },
        onDone() {
          quizSubmitting.value = false
        },
        onError(err) {
          quizSubmitting.value = false
          gradingResult.value = { total: 0, correct: 0, details: [], error: `批改失败: ${err}` }
        },
      }
    )
  }).catch(() => {
    quizSubmitting.value = false
  })
}

// 加载指定资源的最新答题记录
async function loadQuizRecords(resourceId: number) {
  try {
    const userId = authStore.user?.id
    if (!userId) return
    const res = await getQuizRecords(userId, resourceId)
    const records = res.data || []
    if (records.length === 0) return

    // quiz_record 中每条记录对应一道题的作答
    // 由于每条记录的 answerTime 是各自 LocalDateTime.now()，同一提交批次内
    // 时间戳会有几秒差异，因此使用 120 秒时间窗口来识别同一批次
    const expectedCount = quizData.value?.questions.length || 0

    // 按时间窗口分组：从最新记录开始，收集 120 秒内的所有记录
    const latestTime = new Date(records[0].answerTime).getTime()
    const WINDOW_MS = 120_000
    const latestBatch = records.filter(r => {
      const t = new Date(r.answerTime).getTime()
      return latestTime - t <= WINDOW_MS
    })

    // 还原用户答案
    const answers: Record<number, any> = {}
    const details: any[] = []
    let correctCount = 0
    let scoreSum = 0

    const questions = quizData.value?.questions || []

    latestBatch.forEach((record, i) => {
      // 选择题：将文本答案还原为索引
      const q = questions[i]
      const recordExtra = record as typeof record & { score?: number; questionText?: string; feedback?: string }
      const userAnswer = record.userAnswer || ''
      if (q && (q.type === 'single_choice' || q.type === 'multiple_choice') && q.options) {
        if (q.type === 'single_choice') {
          const idx = q.options.indexOf(userAnswer)
          answers[i] = idx >= 0 ? idx : userAnswer
        } else {
          // 多选：逗号分隔的文本 -> 索引数组
          const texts = userAnswer.split(',').map((s: string) => s.trim())
          answers[i] = texts.map((t: string) => q.options!.indexOf(t)).filter((idx: number) => idx >= 0)
        }
      } else {
        answers[i] = userAnswer
      }

      const isCorrect = record.isCorrect === 1
      if (isCorrect) correctCount++
      const score = recordExtra.score ?? (isCorrect ? 1 : 0)
      scoreSum += score
      details.push({
        index: i,
        question_type: record.questionType,
        question: recordExtra.questionText || q?.question || '',
        user_answer: userAnswer,
        correct_answer: record.correctAnswer,
        is_correct: isCorrect,
        score,
        feedback: recordExtra.feedback || (isCorrect ? '回答正确' : `回答错误，正确答案: ${record.correctAnswer}`),
        key_points_hit: [],
        key_points_missed: [],
        improvement_suggestions: isCorrect ? [] : [`正确答案: ${record.correctAnswer}`],
        explanation: q?.explanation || '',
      })
    })

    const total = expectedCount || latestBatch.length
    quizSubmittedAnswers.value = answers
    gradingResult.value = {
      score: total > 0 ? Math.round(scoreSum / total * 100) : 0,
      total,
      correct: correctCount,
      details,
    }
  } catch (e) {
    console.error('Failed to load quiz records:', e)
  }
}

// 重新作答
function retakeQuiz() {
  quizSubmittedAnswers.value = null
  gradingResult.value = null
  showExplanations.value = false
  // 清除本地资源的 latestResult，避免切回时恢复旧结果
  if (selectedResource.value?.moduleData) {
    delete selectedResource.value.moduleData.latestResult
  }
}

// 切换解析显示
function toggleExplanations() {
  showExplanations.value = !showExplanations.value
}

// ==================== PlanChatPanel 事件处理 ====================

function confirmBreakdown() {
  const breakdown = chatStore.pendingTaskBreakdown
  if (breakdown?.modules) {
    const goal = {
      final_goal: plan.value?.title || '学习计划',
      modules: breakdown.modules.map((m: any, i: number) => ({
        title: m.title,
        description: m.description || '',
        order: m.module_id || i + 1,
        resource_types: (m.resources || []).map((r: any) => r.resource_type),
      })),
    }
    updatePlan(planId.value, { learningGoal: goal }).catch(e =>
      console.error('[PlanDetail] 保存学习目标失败:', e)
    )
  }
  chatStore.confirmBreakdown(String(planId.value))
}

function submitModification(text: string) {
  if (!text.trim()) return
  chatStore.confirmBreakdown(String(planId.value), text)
}

function generateResource(type: string) {
  const ctx = chatStore.selectedModuleContext
  if (!ctx) return
  chatStore.requestSupplementaryResource(String(planId.value), ctx, type)
}

// 监听聊天中的新题目资源事件
watch(() => chatStore.lastQuizResource, (data) => {
  if (!data) return

  const maxOrder = resources.value.length > 0 ? Math.max(...resources.value.map(r => r.moduleOrder)) : 0
  const newResource: LearningResource = {
    id: Date.now(),
    planId: planId.value,
    parentId: null,
    moduleOrder: maxOrder + 1,
    moduleType: 'quiz',
    moduleData: {
      title: '练习题',
      questions: data.questions,
    },
    status: 2,
    storagePath: null,
    generatedByAgent: 'quiz_generator',
    version: 1,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
  resources.value.push(newResource)
  toggleResource(newResource)
  chatStore.lastQuizResource = null
})

// 监听批改结果
watch(() => chatStore.lastGradingResult, (data) => {
  if (!data) return
  gradingResult.value = data
  chatStore.lastGradingResult = null
})

// 监听新生成的资源事件 — 从 SSE 内联内容或后端详情添加/更新到侧栏
watch(() => chatStore.lastGeneratedResources, async (resList) => {
  if (!resList || !resList.length) return
  let firstUpdatedRes: LearningResource | null = null
  for (const r of resList) {
    const hasInlineContent = !!(r.content || r.html || r.nodeData || r.moduleData || r.generated_content || r.data)
    if (hasInlineContent) {
      const localRes = upsertGeneratedResource(r)
      if (!firstUpdatedRes) firstUpdatedRes = localRes
      continue
    }

    const existing = resources.value.find(resource => resource.id === r.id)
    try {
      const res = await getResource(r.id)
      const fullRes = res.data
      if (fullRes) {
        // 解析 moduleData（API 返回 JSON 字符串，需转为对象）
        parseModuleData([fullRes])
        const existingIndex = resources.value.findIndex(resource => resource.id === fullRes.id)
        if (existingIndex >= 0) {
          // 生成前通常已经插入 status=1 的占位资源；生成完成后必须用完整资源覆盖，
          // 否则详情面板会一直停留在“资源内容待生成”。
          resources.value.splice(existingIndex, 1, fullRes)
        } else {
          resources.value.push(fullRes)
        }
        if (!firstUpdatedRes) firstUpdatedRes = fullRes
      }
    } catch (e) {
      console.error('Failed to fetch generated resource:', e)
      if (existing) {
        existing.status = 2
        if (!firstUpdatedRes) firstUpdatedRes = existing
      }
    }
  }
  // 自动打开第一个生成完成的资源；如果它已经处于选中状态，则原地刷新派生数据，避免 toggle 反向关闭面板
  if (firstUpdatedRes) {
    if (selectedResourceId.value === firstUpdatedRes.id) {
      selectedResource.value = firstUpdatedRes
      if (firstUpdatedRes.moduleType === 'quiz') {
        quizData.value = parseQuizData(firstUpdatedRes)
        mindmapData.value = null
      } else if (firstUpdatedRes.moduleType === 'mindmap') {
        quizData.value = null
        mindmapData.value = parseMindmapData(firstUpdatedRes)
      } else {
        quizData.value = null
        mindmapData.value = null
      }
    } else {
      toggleResource(firstUpdatedRes)
    }
  }
  chatStore.lastGeneratedResources = null
})

// 监听流式资源更新 — 即时添加到侧栏
watch(() => chatStore.streamingResources.length, () => {
  const items = chatStore.streamingResources
  if (!items.length) return
  for (const { resource, content } of items) {
    if (resources.value.some(existing => existing.id === resource.id)) continue
    const newRes: LearningResource = {
      id: resource.id,
      planId: planId.value,
      parentId: null,
      moduleOrder: resources.value.length > 0
        ? Math.max(...resources.value.map(r => r.moduleOrder)) + 1 : 1,
      moduleType: resource.type || 'document',
      moduleData: { title: resource.title, content },
      status: 2,
      storagePath: null,
      generatedByAgent: 'content_orchestrator',
      version: 1,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    resources.value.push(newRes)
    toggleResource(newRes)
  }
  chatStore.streamingResources = []
  chatStore.isResourceStreaming = false
})

// 监听占位符创建 — 在侧栏立即显示 status=1 的占位条目
watch(() => chatStore.streamingPlaceholders, (placeholders) => {
  if (!placeholders.length) return
  for (const p of placeholders) {
    // 跳过已存在的资源
    if (resources.value.some(r => r.id === p.id)) continue
    const placeholderRes: LearningResource = {
      id: p.id,
      planId: planId.value,
      parentId: null,
      moduleOrder: resources.value.length > 0
        ? Math.max(...resources.value.map(r => r.moduleOrder)) + 1 : 1,
      moduleType: p.type || 'document',
      moduleData: { title: p.title, content: '' },
      status: 1,
      storagePath: null,
      generatedByAgent: 'content_orchestrator',
      version: 1,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    resources.value.push(placeholderRes)
  }
  // 自动选中第一个占位资源以在中间面板显示流式内容
  if (placeholders.length > 0 && !selectedResource.value) {
    const firstPlaceholder = resources.value.find(r => r.id === placeholders[0].id)
    if (firstPlaceholder) {
      selectedResourceId.value = firstPlaceholder.id
      selectedResource.value = firstPlaceholder
      const modIdx = modules.value.findIndex(m => m.resources.some(r => r.id === firstPlaceholder.id))
      if (modIdx >= 0) selectedModuleIndex.value = modIdx
    }
  }
}, { deep: true })

// 监听多资源流式缓冲 — 实时更新侧栏资源内容
watch(() => chatStore.resourceStreamBuffers, (buffers) => {
  for (const [resIdStr, content] of Object.entries(buffers)) {
    const resId = Number(resIdStr)
    if (!content) continue
    const existing = resources.value.find(r => r.id === resId)
    if (existing) {
      existing.moduleData = { ...existing.moduleData, content }
    }
  }
}, { deep: true })
</script>

<style scoped>
.resource-content--animation {
  padding: 0;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #050505;
}

.animation-stage {
  width: min(100%, calc((100vh - 250px) * 16 / 9));
  aspect-ratio: 16 / 9;
  margin: 0 auto;
  overflow: hidden;
  background: #050505;
}

.animation-frame {
  width: 100%;
  height: 100%;
  border: 0;
  background: #050505;
  display: block;
}

.resource-content--podcast {
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.podcast-stage {
  width: 100%;
  height: 100%;
  margin: 0;
  overflow: hidden;
  border: none;
  border-radius: 0;
}

.podcast-frame {
  width: 100%;
  height: 100%;
  border: 0;
  display: block;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease-out;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

<style>
/* Selection popup styles (not scoped — teleported to body) */
.selection-popup {
  position: fixed;
  z-index: 1200;
  animation: selectionPopupFade 0.15s ease;
}

.selection-popup-inner {
  display: flex;
  gap: 4px;
  padding: 4px;
  background: white;
  border: 1px solid rgba(26, 40, 71, 0.1);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.selection-popup-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  color: #273c6b;
  background: none;
  border: none;
  border-radius: 7px;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.12s;
}

.selection-popup-btn:hover {
  background: #f0f3f9;
}

.selection-note-list {
  margin-top: 4px;
  background: white;
  border: 1px solid rgba(26, 40, 71, 0.1);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  max-height: 200px;
  overflow-y: auto;
  padding: 4px;
}

.selection-note-item {
  padding: 8px 10px;
  border-radius: 7px;
  cursor: pointer;
  transition: background 0.12s;
}

.selection-note-item:hover {
  background: #f0f3f9;
}

/* Heading hover hint */
.markdown-body h1,
.markdown-body h2,
.markdown-body h3 {
  cursor: pointer;
  position: relative;
  transition: color 0.15s;
}

.markdown-body h1:hover,
.markdown-body h2:hover,
.markdown-body h3:hover {
  color: #4164b2;
}

.markdown-body h1:hover::after,
.markdown-body h2:hover::after,
.markdown-body h3:hover::after {
  content: '  ';
  font-size: 12px;
  margin-left: 8px;
  opacity: 0.6;
}

@keyframes selectionPopupFade {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

.heading-highlight {
  background: rgba(124, 156, 135, 0.1);
  border-left: 3px solid rgba(124, 156, 135, 0.6);
  border-radius: 4px;
  padding-left: 10px;
  margin-left: -13px;
  transition: background 0.2s, border-color 0.2s;
}
</style>
