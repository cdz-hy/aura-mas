<template>
  <div>
  <div v-if="!plan" class="flex items-center justify-center h-64">
    <div class="text-center">
      <svg class="w-12 h-12 mx-auto text-navy-200 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" class="opacity-25" /><path d="M4 12a8 8 0 018-8" class="opacity-75" stroke-linecap="round" />
      </svg>
      <p class="mt-3 text-navy-400">加载中...</p>
    </div>
  </div>

  <div v-else class="flex gap-0 h-[calc(100vh-12rem)]">
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
              v-if="!editingTitle"
              class="p-0.5 rounded transition-colors"
              :class="tutorEnabled ? 'bg-amber-50 ring-1 ring-amber-300' : 'hover:bg-navy-50'"
              @click="toggleTutor()"
              title="智能辅导"
            >
              <img :src="tutorGif" alt="智能辅导" class="w-5 h-5 rounded" />
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
                <span class="w-2 h-2 rounded-full flex-shrink-0" :class="res.status === 2 ? 'bg-emerald-400' : 'bg-navy-200'"></span>
                <span class="text-navy-600 truncate flex-1">{{ res.moduleData?.title || typeLabels[res.moduleType] || res.moduleType }}</span>
                <span v-if="res.status === 2" class="text-emerald-500 text-[10px]">已生成</span>
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
      class="resource-panel flex flex-col card overflow-hidden mx-2"
      :class="{ 'resource-panel--closed': !selectedResource && !showResourceStreamPreview }"
      :style="panelStyle"
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
          <button
            class="p-1 rounded text-navy-300 hover:text-navy-600 hover:bg-navy-50 transition-colors flex-shrink-0"
            @click="selectedResourceId = null; selectedResource = null; quizData = null; mindmapData = null; gradingResult = null; quizSubmittedAnswers = null; showExplanations = false"
            title="关闭"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <!-- 内容区 -->
        <div class="flex-1 overflow-y-auto p-4">
          <!-- 题目类型 -->
          <template v-if="selectedResource.moduleType === 'quiz'">
            <QuizPlayer
              v-if="quizData"
              :data="quizData"
              :initial-answers="quizSubmittedAnswers"
              :initial-submitted="!!quizSubmittedAnswers"
              :grading="quizSubmitting"
              :result-score="gradingResult?.correct ?? null"
              :question-results="questionResults"
              @submit="onQuizSubmit"
              @retake="retakeQuiz"
            />
            <div v-else class="text-center py-8 text-navy-300 text-sm">
              <p>题目数据加载中...</p>
            </div>

            <!-- 批改总分 -->
            <div v-if="gradingResult" class="mt-4 p-4 rounded-xl border border-navy-100/50 text-center">
              <div class="text-3xl font-bold" :class="(gradingResult.correct || 0) >= (gradingResult.total || 1) * 0.8 ? 'text-emerald-600' : (gradingResult.correct || 0) >= (gradingResult.total || 1) * 0.6 ? 'text-amber-600' : 'text-red-500'">
                {{ gradingResult.correct ?? 0 }} / {{ gradingResult.total ?? 0 }}
              </div>
              <p class="text-sm text-navy-500 mt-1">答对 {{ gradingResult.correct ?? 0 }} 题，共 {{ gradingResult.total ?? 0 }} 题</p>
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

          <!-- 其他类型（含图文） -->
          <template v-else>
            <div v-if="selectedResource.moduleData?.content" class="text-sm text-navy-700 leading-relaxed markdown-body" v-html="renderedResourceContent"></div>
            <div v-else class="text-center py-8 text-navy-300 text-sm">
              <p>资源内容待生成</p>
            </div>
          </template>
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
    <div class="flex-1 flex-shrink-0 flex flex-col card overflow-hidden animate-fade-in-up min-w-[300px]" style="animation-delay: 0.1s">
      <!-- Chat header -->
      <div class="px-6 py-3 border-b border-navy-100/50 flex items-center justify-between">
        <div class="flex items-center gap-3 min-w-0">
          <h3 class="font-display text-base font-semibold text-navy-800">AI 学习助手</h3>
          <span class="text-xs text-navy-400 truncate hidden lg:inline">描述学习目标，AI 会为你规划路径并生成资源</span>
        </div>
        <div class="flex items-center gap-2 flex-shrink-0">
          <button
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
            :class="showSessionList ? 'bg-navy-100 text-navy-700' : 'bg-navy-50 text-navy-500 hover:bg-navy-100'"
            @click="showSessionList = !showSessionList"
            title="会话历史"
          >
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
            </svg>
            会话 ({{ chatStore.sessions.length }})
          </button>
          <button
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-navy-50 text-navy-500 hover:bg-navy-100 transition-colors"
            @click="startNewSession()"
            title="新建会话"
          >
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            新会话
          </button>
          <button
            v-if="chatStore.streaming"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
            @click="chatStore.stopGeneration(planIdStr)"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
            停止
          </button>
        </div>
      </div>

      <!-- 会话列表面板 -->
      <transition name="slide-down">
        <div v-if="showSessionList" class="border-b border-navy-100/50 bg-navy-50/30 max-h-[240px] overflow-y-auto">
          <div v-if="chatStore.sessionsLoading" class="p-4 text-center text-navy-400 text-sm">加载中...</div>
          <div v-else-if="chatStore.sessions.length === 0" class="p-4 text-center text-navy-300 text-sm">暂无历史会话</div>
          <div v-else class="py-1">
            <div
              v-for="session in chatStore.sessions"
              :key="session.sessionId"
              class="flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors group"
              :class="chatStore.activeSessionId === session.sessionId ? 'bg-navy-100/60' : 'hover:bg-white'"
              @click="switchSession(session.sessionId)"
            >
              <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                :class="chatStore.activeSessionId === session.sessionId ? 'bg-navy-600 text-white' : 'bg-navy-100 text-navy-400'">
                <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
                </svg>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm text-navy-700 truncate flex items-center gap-1.5">
                  {{ session.title }}
                  <span v-if="chatStore.streamingSessionIds.has(session.sessionId)" class="inline-block w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse flex-shrink-0"></span>
                </p>
                <p class="text-[11px] text-navy-400 mt-0.5">{{ session.messageCount }} 条消息 · {{ formatTime(session.lastMessageAt) }}</p>
              </div>
              <button
                class="p-1.5 rounded-md text-navy-300 opacity-0 group-hover:opacity-100 hover:text-red-500 hover:bg-red-50 transition-all"
                @click.stop="deleteSession(session.sessionId)"
                title="删除会话"
              >
                <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </transition>

      <!-- Messages -->
      <div ref="messagesContainer" class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        <!-- Welcome -->
        <div v-if="chatStore.messages.length === 0" class="flex items-start gap-3">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-navy-500 to-navy-700 flex items-center justify-center flex-shrink-0">
            <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <div class="bg-navy-50 rounded-2xl rounded-tl-sm px-5 py-3 max-w-[80%]">
            <p class="text-navy-700">你好！请告诉我你想学习什么，我会为你规划学习路径并生成个性化资源。</p>
            <div class="mt-3 flex flex-wrap gap-2">
              <button v-for="q in quickQuestions" :key="q"
                class="text-xs px-3 py-1.5 rounded-full bg-white text-navy-600 border border-navy-200 hover:bg-navy-50 transition-colors"
                @click="sendMessage(q)">
                {{ q }}
              </button>
            </div>
          </div>
        </div>

        <!-- Message list -->
        <div v-for="(msg, i) in chatStore.messages" :key="i" class="flex gap-3" :class="msg.role === 'user' ? 'justify-end' : ''">
          <template v-if="msg.role === 'assistant'">
            <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-navy-500 to-navy-700 flex items-center justify-center flex-shrink-0">
              <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
              </svg>
            </div>

            <!-- 任务分解确认卡片 -->
            <div v-if="msg.type === 'confirm' && msg.breakdown" class="max-w-[85%] space-y-3">
              <div class="bg-navy-50 rounded-2xl rounded-tl-sm px-5 py-3">
                <p class="text-navy-700 mb-3">{{ msg.content }}</p>
                <div v-if="msg.breakdown.modules" class="space-y-2">
                  <div v-for="(mod, j) in msg.breakdown.modules" :key="j" class="bg-white rounded-lg p-3 border border-navy-100">
                    <div class="flex items-center gap-2 mb-1">
                      <span class="w-6 h-6 rounded-full bg-navy-600 text-white text-xs flex items-center justify-center">{{ mod.module_id || j + 1 }}</span>
                      <span class="font-medium text-navy-800 text-sm">{{ mod.title }}</span>
                      <span v-if="mod.estimated_hours" class="text-xs text-navy-400 ml-auto">{{ mod.estimated_hours }}h</span>
                    </div>
                    <p v-if="mod.description" class="text-xs text-navy-500 ml-8">{{ mod.description }}</p>
                    <div v-if="mod.resources && mod.resources.length" class="flex flex-wrap gap-1 mt-1.5 ml-8">
                      <span v-for="r in mod.resources" :key="r.resource_type"
                        class="text-[10px] px-1.5 py-0.5 rounded-full"
                        :class="badgeClass(r.resource_type)">
                        {{ typeLabels[r.resource_type] || r.resource_type }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-if="chatStore.awaitingConfirmation && i === chatStore.messages.length - 1" class="flex gap-2 ml-2">
                <button class="px-4 py-2 rounded-lg bg-navy-600 text-white text-sm font-medium hover:bg-navy-700 transition-colors"
                  @click="confirmBreakdown()">
                  确认，开始生成
                </button>
                <button class="px-4 py-2 rounded-lg bg-white text-navy-600 text-sm font-medium border border-navy-200 hover:bg-navy-50 transition-colors"
                  @click="showModifyInput = true">
                  补充说明
                </button>
              </div>
              <div v-if="showModifyInput && chatStore.awaitingConfirmation && i === chatStore.messages.length - 1" class="ml-2">
                <form @submit.prevent="submitModification" class="flex gap-2">
                  <input v-model="modifyText" type="text" class="input-field flex-1 text-sm" placeholder="输入补充说明..." autofocus />
                  <button type="submit" class="btn-primary px-4 text-sm" :disabled="!modifyText.trim()">发送</button>
                </form>
              </div>
            </div>

            <!-- 资源生成卡片 -->
            <div v-else-if="msg.type === 'resource_generated' && msg.resources?.length" class="max-w-[85%]">
              <div class="bg-navy-50 rounded-2xl rounded-tl-sm px-5 py-3">
                <p class="text-navy-700 mb-3">{{ msg.content }}</p>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="r in msg.resources" :key="r.id"
                    class="flex items-center gap-2 bg-white rounded-lg px-3 py-2 border border-navy-100 hover:border-navy-300 hover:shadow-sm transition-all cursor-pointer"
                    @click="openResourceById(r.id, r.type)"
                  >
                    <span class="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs"
                      :class="badgeClass(r.type)">
                      {{ typeLabels[r.type]?.[0] || r.type[0]?.toUpperCase() || 'R' }}
                    </span>
                    <span class="text-sm text-navy-700 font-medium">{{ r.title }}</span>
                    <span class="text-[10px] px-1.5 py-0.5 rounded-full" :class="badgeClass(r.type)">
                      {{ typeLabels[r.type] || r.type }}
                    </span>
                  </button>
                </div>
              </div>
            </div>

            <!-- 普通消息 -->
            <div v-else class="bg-navy-50 rounded-2xl rounded-tl-sm px-5 py-3 max-w-[80%]">
              <div class="text-navy-700 leading-relaxed markdown-body" v-html="renderMd(msg.content)"></div>
            </div>
          </template>

          <template v-else>
            <div class="bg-navy-600 text-white rounded-2xl rounded-tr-sm px-5 py-3 max-w-[80%]">
              <p class="leading-relaxed">{{ msg.content }}</p>
            </div>
          </template>
        </div>

        <!-- Streaming -->
        <div v-if="chatStore.streaming" class="flex items-start gap-3">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-navy-500 to-navy-700 flex items-center justify-center flex-shrink-0">
            <svg class="w-4 h-4 text-white animate-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
            </svg>
          </div>
          <div class="bg-navy-50 rounded-2xl rounded-tl-sm px-5 py-3 max-w-[80%]">
            <div v-if="chatStore.streamBuffer" class="text-navy-700 leading-relaxed markdown-body" v-html="renderMd(chatStore.streamBuffer)"></div>
            <div v-else class="flex gap-1.5 py-1">
              <span class="w-2 h-2 rounded-full bg-navy-300 animate-bounce" style="animation-delay: 0s"></span>
              <span class="w-2 h-2 rounded-full bg-navy-300 animate-bounce" style="animation-delay: 0.15s"></span>
              <span class="w-2 h-2 rounded-full bg-navy-300 animate-bounce" style="animation-delay: 0.3s"></span>
            </div>
          </div>
        </div>

        <!-- 模块上下文提示（固定在对话底部） -->
        <div v-if="moduleContextMessage && !chatStore.streaming" class="flex items-start gap-3">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-navy-500 to-navy-700 flex items-center justify-center flex-shrink-0">
            <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <div class="bg-navy-50 rounded-2xl rounded-tl-sm px-5 py-3 max-w-[80%]">
            <p class="text-navy-700">你正在查看「<span class="font-medium">{{ moduleContextMessage.title }}</span>」，如需为该模块生成补充资源，请点击：</p>
            <div class="mt-3 flex flex-wrap gap-2">
              <button
                v-for="opt in resourceOptions" :key="opt.type"
                class="text-xs px-3 py-1.5 rounded-full border transition-colors"
                :class="generatingType === opt.type ? 'bg-navy-600 text-white border-navy-600' : 'bg-white text-navy-600 border-navy-200 hover:bg-navy-50'"
                :disabled="!!generatingType"
                @click="generateResource(opt.type)">
                {{ opt.label }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Input -->
      <div class="px-6 py-3 border-t border-navy-100/50 bg-white">
        <form @submit.prevent="sendMessage()" class="flex gap-3">
          <input
            v-model="inputText"
            type="text"
            class="input-field flex-1"
            :placeholder="chatStore.streaming ? 'AI回复中...' : chatStore.awaitingConfirmation ? '输入补充说明...' : '描述你想学习的内容...'"
            :disabled="chatStore.streaming"
          />
          <button type="submit" class="btn-primary px-5" :disabled="!inputText.trim() || chatStore.streaming">
            发送
          </button>
        </form>
      </div>
    </div>
  </div>

  <!-- ==================== 智能辅导浮动对话框 ==================== -->
  <teleport to="body" v-if="tutorEnabled">
      <!-- 折叠态：GIF 图标入口 -->
      <div
        v-if="!tutorOpen"
        class="tutor-fab"
        @click="tutorOpen = true; nextTick(() => scrollTutorBottom())"
        title="打开智能辅导"
      >
        <img :src="tutorGif" alt="智能辅导" />
      </div>

      <!-- 展开态：对话框 -->
      <div v-else class="tutor-dialog" :style="tutorDialogStyle">
        <!-- 标题栏（仅此区域可拖拽） -->
        <div class="tutor-header" @mousedown="onTutorDragStart">
          <div class="tutor-header-left">
            <img :src="tutorGif" alt="智能辅导" class="tutor-header-gif" />
            <div>
              <div class="tutor-header-title">智能辅导</div>
              <div v-if="selectedResource" class="tutor-header-sub">{{ selectedResource.moduleData?.title || selectedResource.moduleData?.module_title }}</div>
            </div>
          </div>
          <div class="tutor-header-actions">
            <button @click="tutorShowSessionList = !tutorShowSessionList" title="历史会话">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" /></svg>
            </button>
            <button @click="tutorNewSession()" title="新会话">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
            </button>
            <button @click="closeTutorChat()" title="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          </div>
        </div>

        <!-- 会话列表面板 -->
        <div v-if="tutorShowSessionList" class="tutor-session-panel">
          <div v-if="tutorSessionsLoading" class="tutor-session-empty">加载中...</div>
          <div v-else-if="tutorSessions.length === 0" class="tutor-session-empty">暂无历史会话</div>
          <div v-else class="tutor-session-list">
            <div
              v-for="s in tutorSessions"
              :key="s.sessionId"
              class="tutor-session-item"
              :class="{ active: tutorSessionId === s.sessionId }"
              @click="tutorSelectSession(s.sessionId)"
            >
              <div class="tutor-session-item-title">{{ s.title || '未命名会话' }}</div>
              <div class="tutor-session-item-meta">{{ s.messageCount }} 条消息</div>
            </div>
          </div>
        </div>

        <!-- 对话区域 -->
        <div ref="tutorContainer" class="tutor-messages">
          <!-- 空状态 -->
          <div v-if="tutorMessages.length === 0" class="tutor-empty">
            <img :src="tutorGif" alt="" class="tutor-empty-gif" />
            <div class="tutor-empty-bubble">{{ tutorFollowUp }}</div>
          </div>

          <!-- 对话列表 -->
          <div v-for="(msg, i) in tutorMessages" :key="i" class="tutor-msg-row" :class="msg.role">
            <!-- 助手头像 -->
            <div v-if="msg.role === 'assistant'" class="tutor-avatar">
              <img :src="tutorGif" alt="" />
            </div>
            <div class="tutor-bubble" :class="msg.role">
              <template v-if="msg.role === 'assistant'">
                <span v-if="!msg.content && tutorLoading && i === tutorMessages.length - 1" class="tutor-typing">
                  <span></span><span></span><span></span>
                </span>
                <div v-else class="tutor-md-content" v-html="renderTutorMd(msg.content)"></div>
              </template>
              <template v-else>{{ msg.content }}</template>
            </div>
          </div>
        </div>

        <!-- 输入栏 -->
        <div class="tutor-input-bar">
          <input
            v-model="tutorInput"
            type="text"
            class="tutor-input"
            placeholder="输入你的问题..."
            :disabled="tutorLoading"
            @keyup.enter="sendTutorMessage()"
          />
          <button
            class="tutor-send-btn"
            :disabled="!tutorInput.trim() || tutorLoading"
            @click="sendTutorMessage()"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>

        <!-- 缩放手柄 -->
        <div class="tutor-resize-handle" @mousedown="onTutorResizeStart">
          <svg viewBox="0 0 16 16" fill="none"><path d="M10 2L6 8l4 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" /><path d="M6 2L2 8l4 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" opacity="0.4" /></svg>
        </div>
      </div>
  </teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { getPlan, updatePlan } from '@/api/plan'
import { getPlanResources, getResource } from '@/api/resource'
import { parseMarkdown } from '@/utils/markdown'
import { getQuizRecords, submitQuizSSE } from '@/api/quiz'
import { issueTicket } from '@/api/auth'
import { PYTHON_AI_BASE } from '@/api/request'
import { getSessions, getSessionMessages } from '@/api/chat'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
import QuizPlayer from '@/components/resource/QuizPlayer.vue'
import MindmapPlayer from '@/components/resource/MindmapPlayer.vue'
import tutorGif from '@/image/智能辅导.gif'
import type { LearningPlan, LearningResource } from '@/types/plan'
import type { QuizData, QuizQuestion } from '@/types/quiz'
import type { MindElixirData } from 'mind-elixir'

const route = useRoute()
const planId = Number(route.params.id)
const planIdStr = String(planId)
const chatStore = useChatStore()
const authStore = useAuthStore()

// ==================== 面板拖拽调整 ====================
const panelWidth = ref(400)
const isDragging = ref(false)

// 中间面板的宽度样式（包含关闭态：width=0，由 CSS transition 驱动动画）
const panelStyle = computed(() => {
  if (!selectedResource.value && !showResourceStreamPreview.value) {
    return { width: '0px', minWidth: '0px', marginLeft: '0px', marginRight: '0px' }
  }
  return { width: panelWidth.value + 'px', minWidth: '280px' }
})

// 辅导对话框位置样式
const tutorDialogStyle = computed(() => {
  const style: Record<string, string> = {
    width: tutorSize.value.w + 'px',
    height: tutorSize.value.h + 'px',
  }
  if (tutorPosition.value.x >= 0) {
    style.left = tutorPosition.value.x + 'px'
    style.top = tutorPosition.value.y + 'px'
    style.right = 'auto'
    style.bottom = 'auto'
  }
  return style
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
  dragState.pendingWidth = Math.max(280, Math.min(800,
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
  // 关闭辅导 SSE 连接
  if (tutorEventSource.value) {
    tutorEventSource.value.close()
    tutorEventSource.value = null
  }
  // 移除 teleport 元素（v-if="tutorEnabled"，设为 false 即从 body 移除）
  tutorEnabled.value = false
  // 重置 body 样式
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
})

// ==================== 状态 ====================
const plan = ref<LearningPlan | null>(null)
const resources = ref<LearningResource[]>([])
const selectedModuleIndex = ref(-1)
const selectedResourceId = ref<number | null>(null)
const selectedResource = ref<LearningResource | null>(null)
const quizData = ref<QuizData | null>(null)
const mindmapData = ref<MindElixirData | null>(null)
const gradingResult = ref<Record<string, any> | null>(null)
const quizSubmittedAnswers = ref<Record<number, any> | null>(null)
const showExplanations = ref(false)

// 逐题批改结果（按 index 索引，供 QuizPlayer 使用）
const questionResults = computed(() => {
  const details = gradingResult.value?.details
  if (!details?.length) return null
  const map: Record<number, any> = {}
  details.forEach((d: any, i: number) => { map[d.index ?? i] = d })
  return map
})
const quizSubmitting = ref(false)
const messagesContainer = ref<HTMLElement>()
const inputText = ref('')
const showModifyInput = ref(false)
const modifyText = ref('')
const sidebarCollapsed = ref(false)
const moduleContextMessage = ref<{ title: string } | null>(null)
const generatingType = ref<string | null>(null)
const resourceOptions = [
  { type: 'quiz', label: '生成测验' },
  { type: 'mindmap', label: '生成思维导图' },
  { type: 'code', label: '生成代码示例' },
  { type: 'summary', label: '生成总结' },
  { type: 'video', label: '生成教学视频' },
]
const showSessionList = ref(false)

// 标题编辑
const editingTitle = ref(false)
const editTitle = ref('')

const quickQuestions = [
  '我想学习 Python 基础',
  '帮我生成一些练习题',
  '这个知识点不太理解',
]

const typeLabels: Record<string, string> = {
  document: '文档', text: '图文', mindmap: '导图', quiz: '题目', code: '代码', reading: '阅读', summary: '总结', video: '视频', image: '图片', diagram: '图表',
}

// ==================== 智能辅导 ====================
const tutorEnabled = ref(false)
const tutorOpen = ref(false)
const tutorInput = ref('')
const tutorMessages = ref<Array<{ role: 'user' | 'assistant'; content: string }>>([])
const tutorLoading = ref(false)
const tutorContainer = ref<HTMLElement>()
const tutorEventSource = ref<EventSource | null>(null)
const tutorSessionId = ref('')
const tutorSessionCounter = ref(0)

// 辅导会话管理
const tutorSessions = ref<Array<{ sessionId: string; title: string; messageCount: number; lastMessageAt: string }>>([])
const tutorSessionsLoading = ref(false)
const tutorShowSessionList = ref(false)

// 拖拽状态
const tutorDragState = ref<{ dragging: boolean; offsetX: number; offsetY: number } | null>(null)
const tutorPosition = ref({ x: -1, y: -1 }) // -1 表示使用默认位置

// 缩放状态
const tutorSize = ref({ w: 380, h: 480 })
const tutorResizeState = ref<{ resizing: boolean; startX: number; startY: number; startW: number; startH: number } | null>(null)

// 反问文案模板
const tutorFollowUps: Record<string, string[]> = {
  quiz: ['测验有没有什么不理解的知识点，我可以帮帮你哦', '测验做得怎么样？有不会的题目吗？'],
  document: ['图文内容有什么不懂的地方吗，我可以教教你哦', '这个知识点理解了吗？'],
  text: ['图文内容有什么不懂的地方吗，我可以教教你哦', '这个知识点理解了吗？'],
  code: ['代码部分有什么疑问吗？', '这段代码能看懂吗？'],
  mindmap: ['思维导图清晰吗？有需要解释的分支吗？'],
  summary: ['总结内容理解了吗？有遗漏的要点吗？'],
  video: ['视频内容有什么不明白的吗？'],
  default: ['有什么不懂的地方吗，我可以帮你哦'],
}
const tutorFollowUp = ref('有什么不懂的地方吗，我可以帮你哦')

function pickFollowUp(moduleType: string): string {
  const templates = tutorFollowUps[moduleType] || tutorFollowUps.default
  return templates[Math.floor(Math.random() * templates.length)]
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
  const content = selectedResource.value?.moduleData?.content
  if (!content) return ''
  return renderMd(content)
})

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

function toggleResource(res: LearningResource) {
  // 点击已选中的资源 → 取消选中
  if (selectedResourceId.value === res.id) {
    selectedResourceId.value = null
    selectedResource.value = null
    quizData.value = null
    mindmapData.value = null
    gradingResult.value = null
    quizSubmittedAnswers.value = null
    showExplanations.value = false
    moduleContextMessage.value = null
    chatStore.selectedModuleContext = null
    return
  }

  selectedResourceId.value = res.id
  selectedResource.value = res
  gradingResult.value = null
  quizSubmittedAnswers.value = null
  showExplanations.value = false

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
    planId: res.planId || planId,
  }
  // 仅在非 quiz 资源时提示（quiz 本身已是补充资源）
  if (res.moduleType !== 'quiz') {
    moduleContextMessage.value = { title: moduleTitle }
  } else {
    moduleContextMessage.value = null
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
  if (!md?.content) return null

  try {
    // content 应该是 MindElixir nodeData 的 JSON 字符串
    const parsed = typeof md.content === 'string' ? JSON.parse(md.content) : md.content

    // 验证基本结构：必须有 id 和 topic
    if (!parsed || !parsed.topic) return null

    return {
      nodeData: parsed,
      direction: 2, // SIDE: 左右分布
    } as MindElixirData
  } catch {
    // JSON 解析失败，尝试将纯文本包装为简单的思维导图
    const text = typeof md.content === 'string' ? md.content : ''
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
      planId,
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

    latestBatch.forEach((record, i) => {
      answers[i] = record.userAnswer
      const isCorrect = record.isCorrect === 1
      if (isCorrect) correctCount++
      details.push({
        index: i,
        question_type: record.questionType,
        user_answer: record.userAnswer,
        correct_answer: record.correctAnswer,
        is_correct: isCorrect,
        score: isCorrect ? 1 : 0,
        feedback: isCorrect ? '回答正确' : `回答错误，正确答案: ${record.correctAnswer}`,
        key_points_hit: isCorrect ? [] : [],
        key_points_missed: isCorrect ? [] : [],
        improvement_suggestions: isCorrect ? [] : [`正确答案: ${record.correctAnswer}`],
        explanation: '',
      })
    })

    quizSubmittedAnswers.value = answers
    gradingResult.value = {
      total: expectedCount || latestBatch.length,
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

// 监听聊天中的新题目资源事件
watch(() => chatStore.lastQuizResource, (data) => {
  if (!data) return

  const maxOrder = resources.value.length > 0 ? Math.max(...resources.value.map(r => r.moduleOrder)) : 0
  const newResource: LearningResource = {
    id: Date.now(),
    planId,
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

// 监听新生成的资源事件 — 从后端获取完整资源并添加到侧栏
watch(() => chatStore.lastGeneratedResources, async (resList) => {
  if (!resList || !resList.length) return
  let firstNewRes: LearningResource | null = null
  for (const r of resList) {
    // 跳过已存在的资源
    if (resources.value.some(existing => existing.id === r.id)) continue
    try {
      const res = await getResource(r.id)
      const fullRes = res.data
      if (fullRes) {
        // 解析 moduleData（API 返回 JSON 字符串，需转为对象）
        parseModuleData([fullRes])
        resources.value.push(fullRes)
        if (!firstNewRes) firstNewRes = fullRes
      }
    } catch (e) {
      console.error('Failed to fetch generated resource:', e)
    }
  }
  // 自动打开第一个新资源
  if (firstNewRes) {
    toggleResource(firstNewRes)
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
      planId,
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
      planId,
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

// ==================== 滚动 ====================

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

watch(() => chatStore.messages.length + chatStore.streamBuffer.length, scrollToBottom)

// 生成完成后重置按钮状态
watch(() => chatStore.streaming, (val) => {
  if (!val) generatingType.value = null
})

// ==================== 消息发送 ====================

function sendMessage(text?: string) {
  const msg = text || inputText.value.trim()
  if (!msg) return
  inputText.value = ''
  showModifyInput.value = false

  // 检测是否为补充资源生成请求
  const ctx = chatStore.selectedModuleContext
  if (ctx) {
    const resourceType = detectResourceType(msg)
    if (resourceType) {
      chatStore.requestSupplementaryResource(planIdStr, ctx, resourceType)
      return
    }
  }

  chatStore.sendMessage(msg, planIdStr)
}

/** 快捷按钮生成补充资源 */
function generateResource(type: string) {
  const ctx = chatStore.selectedModuleContext
  if (!ctx || generatingType.value) return
  generatingType.value = type
  chatStore.requestSupplementaryResource(planIdStr, ctx, type)
  // 生成开始后清除上下文消息
  moduleContextMessage.value = null
}

/** 从用户消息中检测补充资源类型 */
function detectResourceType(msg: string): string | null {
  const lower = msg.toLowerCase()
  if (/测验|题目|练习|quiz|做题|出题/.test(lower)) return 'quiz'
  if (/思维导图|导图|mindmap|脑图/.test(lower)) return 'mindmap'
  if (/代码|code|示例代码|编程/.test(lower)) return 'code'
  if (/总结|摘要|summary|复习|要点/.test(lower)) return 'summary'
  if (/视频|video|教程|教学视频/.test(lower)) return 'video'
  return null
}

function confirmBreakdown() {
  showModifyInput.value = false

  // 保存学习目标到计划
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
    updatePlan(planId, { learningGoal: goal }).catch(e =>
      console.error('[PlanDetail] 保存学习目标失败:', e)
    )
  }

  chatStore.confirmBreakdown(planIdStr)
}

function submitModification() {
  const text = modifyText.value.trim()
  if (!text) return
  modifyText.value = ''
  showModifyInput.value = false
  chatStore.confirmBreakdown(planIdStr, text)
}

// ==================== 会话管理 ====================

function startNewSession() {
  chatStore.newSession()
  chatStore.loadSessions(planIdStr)
  showSessionList.value = false
}

async function switchSession(sessionId: string) {
  await chatStore.selectSession(sessionId)
  showSessionList.value = false
}

async function deleteSession(sessionId: string) {
  await chatStore.deleteSession(sessionId)
}

function formatTime(time?: string) {
  if (!time) return ''
  const d = new Date(time)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour}小时前`
  const diffDay = Math.floor(diffHour / 24)
  if (diffDay < 7) return `${diffDay}天前`
  return `${d.getMonth() + 1}/${d.getDate()}`
}

// ==================== 计划标题编辑 ====================

async function saveTitle() {
  const title = editTitle.value.trim()
  if (!title || !plan.value) return
  editingTitle.value = false
  if (title === plan.value.title) return
  try {
    await updatePlan(planId, { title })
    plan.value.title = title
  } catch (e) {
    console.error('Failed to update plan title:', e)
  }
}

// ==================== 状态辅助 ====================

function statusText(s: number) { return ['待规划', '生成中', '待确认', '学习中', '已完成'][s] || '未知' }
function statusClass(s: number) {
  return ['bg-gray-100 text-gray-600', 'bg-blue-100 text-blue-600', 'bg-amber-100 text-amber-600', 'bg-emerald-100 text-emerald-600', 'bg-sage-100 text-sage-700'][s] || 'bg-gray-100 text-gray-600'
}
function badgeClass(type: string) {
  return { text: 'bg-blue-50 text-blue-500', document: 'bg-blue-50 text-blue-500', mindmap: 'bg-purple-50 text-purple-500', quiz: 'bg-amber-50 text-amber-500', code: 'bg-emerald-50 text-emerald-500', reading: 'bg-rose-50 text-rose-500', video: 'bg-red-50 text-red-500', summary: 'bg-sky-50 text-sky-500', image: 'bg-pink-50 text-pink-500', diagram: 'bg-indigo-50 text-indigo-500' }[type] || 'bg-navy-50 text-navy-500'
}

// ==================== 资源生成 ====================

async function refreshResources() {
  try {
    const res = await getPlanResources(planId)
    resources.value = res.data || []
    parseModuleData(resources.value)
  } catch (e) {
    console.error('[PlanDetail] 刷新资源失败:', e)
  }
}

function parseModuleData(res: LearningResource[]) {
  res.forEach(r => {
    if (typeof r.moduleData === 'string') {
      try { r.moduleData = JSON.parse(r.moduleData) } catch { r.moduleData = {} }
    }
  })
}

// ==================== 智能辅导功能 ====================

function renderTutorMd(text: string) {
  if (!text) return ''
  return parseMarkdown(text)
}

// 监听资源切换：更新反问文案，已有对话时自动插入反问消息
// 记录上一次反问内容，用于识别反问消息
let lastFollowUpContent = ''

watch(selectedResource, (res, oldRes) => {
  if (!res || !tutorEnabled.value) return
  if (oldRes && res.id === oldRes.id) return
  const followUp = pickFollowUp(res.moduleType)
  tutorFollowUp.value = followUp

  if (tutorMessages.value.length > 0) {
    const lastMsg = tutorMessages.value[tutorMessages.value.length - 1]
    // 如果最后一条是上次的反问消息，直接替换内容
    if (lastMsg.role === 'assistant' && lastMsg.content === lastFollowUpContent) {
      lastMsg.content = followUp
    } else {
      // 否则新增一条反问
      tutorMessages.value.push({ role: 'assistant', content: followUp })
    }
    lastFollowUpContent = followUp
    nextTick(() => scrollTutorBottom())
  }
})

function toggleTutor() {
  tutorEnabled.value = !tutorEnabled.value
  if (tutorEnabled.value) {
    tutorOpen.value = true
    tutorLoadSessions()
    nextTick(() => scrollTutorBottom())
  } else {
    tutorOpen.value = false
  }
}

/** 加载辅导会话列表，自动选中最近一个 */
async function tutorLoadSessions() {
  tutorSessionsLoading.value = true
  try {
    const res = await getSessions('chat', planId)
    const allSessions = res.data || []
    // 筛选辅导会话（session_id 以 tutor-{planId}- 开头）
    const prefix = `tutor-${planId}-`
    tutorSessions.value = allSessions.filter((s: any) => s.sessionId?.startsWith(prefix))
    // 如果有历史会话，加载最近一个
    if (tutorSessions.value.length > 0 && !tutorSessionId.value) {
      const latest = tutorSessions.value[0]
      tutorSessionId.value = latest.sessionId
      await tutorLoadSessionMessages(latest.sessionId)
    } else if (!tutorSessionId.value) {
      // 无历史会话，初始化新会话 ID
      tutorSessionId.value = `${prefix}${authStore.user?.id || 0}`
      if (selectedResource.value) {
        tutorFollowUp.value = pickFollowUp(selectedResource.value.moduleType)
      }
    }
  } catch (e) {
    console.error('[Tutor] 加载会话列表失败:', e)
    if (!tutorSessionId.value) {
      tutorSessionId.value = `tutor-${planId}-${authStore.user?.id || 0}`
    }
  } finally {
    tutorSessionsLoading.value = false
  }
}

/** 加载指定会话的消息 */
async function tutorLoadSessionMessages(sessionId: string) {
  try {
    const res = await getSessionMessages(sessionId, 50)
    const dbMessages = res.data || []
    tutorMessages.value = dbMessages.map((m: any) => ({
      role: m.dialogueType === 'USER' ? 'user' as const : 'assistant' as const,
      content: m.conversationText || '',
    }))
    await nextTick()
    scrollTutorBottom()
  } catch (e) {
    console.error('[Tutor] 加载会话消息失败:', e)
    tutorMessages.value = []
  }
}

/** 切换到指定会话 */
async function tutorSelectSession(sessionId: string) {
  if (sessionId === tutorSessionId.value) return
  // 关闭当前 SSE
  if (tutorEventSource.value) {
    tutorEventSource.value.close()
    tutorEventSource.value = null
  }
  tutorLoading.value = false
  tutorSessionId.value = sessionId
  tutorShowSessionList.value = false
  await tutorLoadSessionMessages(sessionId)
}

/** 新建会话 */
function tutorNewSession() {
  if (tutorEventSource.value) {
    tutorEventSource.value.close()
    tutorEventSource.value = null
  }
  tutorLoading.value = false
  tutorMessages.value = []
  lastFollowUpContent = ''
  tutorSessionCounter.value++
  tutorSessionId.value = `tutor-${planId}-${authStore.user?.id || 0}-${tutorSessionCounter.value}`
  tutorShowSessionList.value = false
  tutorFollowUp.value = selectedResource.value ? pickFollowUp(selectedResource.value.moduleType) : '有什么不懂的地方吗，我可以帮你哦'
  // 刷新会话列表
  tutorLoadSessions()
}

async function sendTutorMessage(text?: string) {
  const msg = text || tutorInput.value.trim()
  if (!msg || tutorLoading.value) return
  tutorInput.value = ''
  tutorMessages.value.push({ role: 'user', content: msg })
  tutorMessages.value.push({ role: 'assistant', content: '' })
  tutorLoading.value = true

  await nextTick()
  scrollTutorBottom()

  try {
    const ticketRes = await issueTicket()
    const ticket = ticketRes.data.ticket
    const params = new URLSearchParams({
      ticket,
      plan_id: planIdStr,
      resource_id: selectedResource.value ? String(selectedResource.value.id) : '0',
      message: msg,
      session_id: tutorSessionId.value,
    })

    const es = new EventSource(`${PYTHON_AI_BASE}/api/ai/tutor/chat?${params}`)
    tutorEventSource.value = es

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'chunk') {
          const last = tutorMessages.value[tutorMessages.value.length - 1]
          if (last?.role === 'assistant') {
            last.content += data.content
            nextTick(() => scrollTutorBottom())
          }
        } else if (data.type === 'progress') {
          // 可选：显示进度
        } else if (data.type === 'error') {
          const last = tutorMessages.value[tutorMessages.value.length - 1]
          if (last?.role === 'assistant') {
            last.content = data.content || '发生错误，请稍后再试'
          }
        } else if (data.type === 'done') {
          es.close()
          tutorEventSource.value = null
          tutorLoading.value = false
          // 刷新会话列表
          tutorLoadSessions()
        }
      } catch {}
    }

    es.onerror = () => {
      es.close()
      tutorEventSource.value = null
      tutorLoading.value = false
      const last = tutorMessages.value[tutorMessages.value.length - 1]
      if (last?.role === 'assistant' && !last.content) {
        last.content = '连接中断，请稍后再试'
      }
    }
  } catch (e) {
    tutorLoading.value = false
    const last = tutorMessages.value[tutorMessages.value.length - 1]
    if (last?.role === 'assistant' && !last.content) {
      last.content = '发送失败，请稍后再试'
    }
  }
}

function scrollTutorBottom() {
  if (tutorContainer.value) {
    tutorContainer.value.scrollTop = tutorContainer.value.scrollHeight
  }
}

function closeTutorChat() {
  if (tutorEventSource.value) {
    tutorEventSource.value.close()
    tutorEventSource.value = null
  }
  tutorOpen.value = false
}

// 拖拽对话框（仅标题栏触发）
function onTutorDragStart(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (target.closest('button')) return
  e.preventDefault()
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  tutorDragState.value = { dragging: true, offsetX: e.clientX - rect.left, offsetY: e.clientY - rect.top }

  const onMove = (ev: MouseEvent) => {
    if (!tutorDragState.value) return
    tutorPosition.value = {
      x: ev.clientX - tutorDragState.value.offsetX,
      y: ev.clientY - tutorDragState.value.offsetY,
    }
  }
  const onUp = () => {
    tutorDragState.value = null
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    document.body.style.userSelect = ''
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
  document.body.style.userSelect = 'none'
}

// 缩放对话框
function onTutorResizeStart(e: MouseEvent) {
  e.preventDefault()
  e.stopPropagation()
  tutorResizeState.value = { resizing: true, startX: e.clientX, startY: e.clientY, startW: tutorSize.value.w, startH: tutorSize.value.h }

  const onMove = (ev: MouseEvent) => {
    if (!tutorResizeState.value) return
    tutorSize.value = {
      w: Math.max(300, tutorResizeState.value.startW + (ev.clientX - tutorResizeState.value.startX)),
      h: Math.max(200, tutorResizeState.value.startH - (ev.clientY - tutorResizeState.value.startY)),
    }
  }
  const onUp = () => {
    tutorResizeState.value = null
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    document.body.style.userSelect = ''
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
  document.body.style.userSelect = 'none'
}

// ==================== 生命周期 ====================

onMounted(async () => {
  // 保存 activeSessionId，resetForPlan 可能在跨计划时清空它
  const savedSessionId = chatStore.activeSessionId
  chatStore.resetForPlan(planIdStr)

  try {
    const [planRes, resourcesRes] = await Promise.all([
      getPlan(planId),
      getPlanResources(planId),
    ])
    plan.value = planRes.data
    resources.value = resourcesRes.data || []
    parseModuleData(resources.value)
  } catch (e) {
    console.error('[PlanDetail] 加载失败:', e)
  }

  // 加载会话列表
  await chatStore.loadSessions(planIdStr)

  // 如果 resetForPlan 清空了会话 ID，恢复之
  if (!chatStore.activeSessionId && savedSessionId) {
    chatStore.activeSessionId = savedSessionId
  }

  // 刷新后恢复：先检查后端是否仍在处理，再决定加载策略
  let isRecovering = false
  if (chatStore.activeSessionId) {
    isRecovering = await chatStore.recoverStreaming(planIdStr)
  }

  // 如果后端没有在处理，正常加载消息
  if (!isRecovering) {
    if (!chatStore.activeSessionId && chatStore.sessions.length > 0) {
      await chatStore.selectSession(chatStore.sessions[0].sessionId)
    } else if (chatStore.activeSessionId && chatStore.messages.length === 0) {
      await chatStore.selectSession(chatStore.activeSessionId)
    }
  }

  // 定期检查后端是否在生成资源（页面刷新后 SSE 断开时，通过轮询补偿）
  // 后端线程仍在运行并保存资源，前端通过轮询发现新资源并加载
  const startPolling = () => {
    if (refreshTimer) return
    refreshTimer = setInterval(async () => {
      if (chatStore.streaming) return // SSE 活跃时不轮询
      try {
        const res = await getPlanResources(planId)
        const dbResources = res.data || []
        parseModuleData(dbResources)
        // 检测新增资源
        const existingIds = new Set(resources.value.map(r => r.id))
        const newOnes = dbResources.filter((r: LearningResource) => !existingIds.has(r.id))
        if (newOnes.length) {
          resources.value.push(...newOnes)
          toggleResource(newOnes[0])
        }
        // 没有"生成中"状态的资源时停止轮询
        const hasGenerating = dbResources.some((r: LearningResource) => r.status === 1)
        if (!hasGenerating && !chatStore.streaming) {
          if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null }
        }
      } catch { /* ignore */ }
    }, 3000)
  }
  // 检查是否有生成中的资源需要轮询
  if (resources.value.some(r => r.status === 1)) startPolling()
  // 监听 streaming 状态变化：开始流式时停止轮询，结束时静默刷新 + 启动轮询
  watch(() => chatStore.streaming, async (isStreaming) => {
    if (isStreaming) {
      if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null }
    } else {
      // 流式结束后立即静默刷新：用后端最终数据替换本地流式拼接内容，修复 markdown/LaTeX 渲染问题
      try {
        const res = await getPlanResources(planId)
        const dbResources: LearningResource[] = res.data || []
        parseModuleData(dbResources)
        // 用后端数据全量替换本地资源列表（保留用户当前选中状态）
        const selectedId = selectedResource.value?.id
        resources.value = dbResources
        if (selectedId) {
          const match = dbResources.find((r: LearningResource) => r.id === selectedId)
          if (match) selectedResource.value = match
        }
      } catch { /* ignore */ }
      startPolling()
      setTimeout(() => {
        if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null }
      }, 10000)
    }
  })
})
</script>

<style scoped>
/* 资源面板：width 过渡驱动打开/关闭动画，flex 布局联动右侧面板 */
.resource-panel {
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              min-width 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              margin 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              opacity 0.25s ease;
}
.resource-panel--closed {
  opacity: 0;
  pointer-events: none;
}

.resource-divider {
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              opacity 0.25s ease;
}
.resource-divider--closed {
  width: 0 !important;
  opacity: 0;
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.25s ease;
  overflow: hidden;
}
.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  max-height: 0;
}
.slide-down-enter-to,
.slide-down-leave-from {
  max-height: 240px;
}

</style>

<!-- 非 scoped 样式：teleport 到 body 的元素无法匹配 scoped 样式 -->
<style>
/* ========== 浮动入口按钮 ========== */
.tutor-fab {
  position: fixed;
  bottom: 28px;
  right: 28px;
  width: 58px;
  height: 58px;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 8px 28px rgba(139, 92, 246, 0.3), 0 0 0 0 rgba(139, 92, 246, 0.15);
  transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.4s;
  z-index: 9999;
  animation: tutor-fab-pulse 3s ease-in-out infinite;
}
.tutor-fab:hover {
  transform: scale(1.12) rotate(-3deg);
  box-shadow: 0 12px 36px rgba(139, 92, 246, 0.45);
  animation: none;
}
.tutor-fab img { width: 100%; height: 100%; object-fit: cover; }
@keyframes tutor-fab-pulse {
  0%, 100% { box-shadow: 0 8px 28px rgba(139, 92, 246, 0.3), 0 0 0 0 rgba(139, 92, 246, 0.15); }
  50% { box-shadow: 0 8px 28px rgba(139, 92, 246, 0.3), 0 0 0 12px rgba(139, 92, 246, 0); }
}

/* ========== 对话框主体 ========== */
.tutor-dialog {
  position: fixed;
  bottom: 28px;
  right: 28px;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 24px;
  box-shadow:
    0 32px 80px rgba(88, 28, 135, 0.1),
    0 12px 28px rgba(88, 28, 135, 0.06),
    0 0 0 1px rgba(139, 92, 246, 0.06);
  overflow: hidden;
  z-index: 9999;
  animation: tutor-dialog-in 0.4s cubic-bezier(0.22, 1, 0.36, 1);
}
@keyframes tutor-dialog-in {
  from { opacity: 0; transform: translateY(24px) scale(0.92); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

/* ========== 会话列表面板 ========== */
.tutor-session-panel {
  max-height: 200px;
  overflow-y: auto;
  background: linear-gradient(180deg, #f5f3ff, #faf9ff);
  border-bottom: 1px solid rgba(139, 92, 246, 0.06);
}
.tutor-session-empty {
  padding: 20px;
  text-align: center;
  font-size: 12px;
  color: #a1a1aa;
}
.tutor-session-list { padding: 6px 10px; }
.tutor-session-item {
  padding: 10px 14px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.tutor-session-item:hover {
  background: rgba(139, 92, 246, 0.06);
  transform: translateX(2px);
}
.tutor-session-item.active {
  background: rgba(139, 92, 246, 0.1);
}
.tutor-session-item-title {
  font-size: 13px;
  color: #1e293b;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tutor-session-item-meta {
  font-size: 11px;
  color: #a1a1aa;
  margin-top: 3px;
}

/* ========== 标题栏 ========== */
.tutor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  background: linear-gradient(135deg, #a78bfa 0%, #8b5cf6 40%, #7c3aed 100%);
  cursor: move;
  user-select: none;
  flex-shrink: 0;
  position: relative;
}
.tutor-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
}
.tutor-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.tutor-header-gif {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  object-fit: cover;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);
  border: 1.5px solid rgba(255, 255, 255, 0.2);
}
.tutor-header-title {
  font-size: 15px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.03em;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}
.tutor-header-sub {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.75);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 2px;
}
.tutor-header-actions {
  display: flex;
  align-items: center;
  gap: 5px;
}
.tutor-header-actions button {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.08);
  cursor: pointer;
  transition: all 0.25s;
}
.tutor-header-actions button svg {
  width: 14px;
  height: 14px;
  color: rgba(255, 255, 255, 0.85);
  transition: transform 0.25s;
}
.tutor-header-actions button:hover {
  background: rgba(255, 255, 255, 0.22);
  transform: scale(1.08);
}
.tutor-header-actions button:hover svg {
  transform: scale(1.1);
}

/* ========== 消息区域 ========== */
.tutor-messages {
  flex: 1;
  overflow-y: auto;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: linear-gradient(180deg, #faf9ff 0%, #f8f7ff 40%, #ffffff 100%);
}
.tutor-messages::-webkit-scrollbar { width: 5px; }
.tutor-messages::-webkit-scrollbar-track { background: transparent; }
.tutor-messages::-webkit-scrollbar-thumb { background: #e4e4e7; border-radius: 5px; }
.tutor-messages::-webkit-scrollbar-thumb:hover { background: #d4d4d8; }

/* ========== 空状态 ========== */
.tutor-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 24px 12px;
}
.tutor-empty-gif {
  width: 72px;
  height: 72px;
  border-radius: 20px;
  object-fit: cover;
  box-shadow: 0 8px 24px rgba(139, 92, 246, 0.12);
  border: 2px solid rgba(139, 92, 246, 0.08);
}
.tutor-empty-bubble {
  background: linear-gradient(135deg, #f5f3ff, #ede9fe);
  color: #5b21b6;
  padding: 14px 18px;
  border-radius: 20px 20px 20px 6px;
  font-size: 13.5px;
  line-height: 1.8;
  max-width: 88%;
  box-shadow: 0 4px 14px rgba(139, 92, 246, 0.06);
  border: 1px solid rgba(139, 92, 246, 0.06);
}

/* ========== 消息行 ========== */
.tutor-msg-row {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}
.tutor-msg-row.user { justify-content: flex-end; }

/* ========== 头像 ========== */
.tutor-avatar {
  width: 30px;
  height: 30px;
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
  box-shadow: 0 3px 8px rgba(139, 92, 246, 0.12);
  border: 1.5px solid rgba(139, 92, 246, 0.1);
}
.tutor-avatar img { width: 100%; height: 100%; object-fit: cover; }

/* ========== 气泡 ========== */
.tutor-bubble {
  max-width: 82%;
  padding: 12px 16px;
  font-size: 13.5px;
  line-height: 1.8;
  word-break: break-word;
}
.tutor-bubble.assistant {
  background: #ffffff;
  color: #334155;
  border-radius: 6px 20px 20px 20px;
  box-shadow: 0 3px 12px rgba(0, 0, 0, 0.04), 0 1px 4px rgba(0, 0, 0, 0.02);
  border: 1px solid rgba(139, 92, 246, 0.06);
}
.tutor-bubble.user {
  background: linear-gradient(135deg, #a78bfa, #8b5cf6);
  color: white;
  border-radius: 20px 6px 20px 20px;
  box-shadow: 0 4px 14px rgba(139, 92, 246, 0.2);
}

/* ========== Markdown 内容样式 ========== */
.tutor-md-content p { margin: 0 0 10px 0; }
.tutor-md-content p:last-child { margin-bottom: 0; }
.tutor-md-content strong { font-weight: 600; color: #1e293b; }
.tutor-md-content em { font-style: italic; color: #64748b; }
.tutor-md-content code {
  background: linear-gradient(135deg, #f5f3ff, #ede9fe);
  padding: 2px 6px;
  border-radius: 6px;
  font-size: 12px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  color: #7c3aed;
}
.tutor-md-content pre {
  background: linear-gradient(135deg, #1e1b4b, #2e1065);
  color: #e0e7ff;
  padding: 14px;
  border-radius: 14px;
  overflow-x: auto;
  margin: 10px 0;
  font-size: 12px;
  line-height: 1.7;
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.2);
}
.tutor-md-content pre code {
  background: none;
  color: inherit;
  padding: 0;
  font-size: inherit;
}
.tutor-md-content ul, .tutor-md-content ol {
  padding-left: 20px;
  margin: 8px 0;
}
.tutor-md-content li { margin: 4px 0; line-height: 1.7; }
.tutor-md-content blockquote {
  border-left: 3px solid #a78bfa;
  padding-left: 14px;
  margin: 10px 0;
  color: #64748b;
  font-style: italic;
  background: rgba(139, 92, 246, 0.03);
  padding: 8px 14px;
  border-radius: 0 8px 8px 0;
}
.tutor-md-content h1, .tutor-md-content h2, .tutor-md-content h3, .tutor-md-content h4 {
  font-weight: 700;
  color: #1e293b;
  margin: 14px 0 8px 0;
  letter-spacing: -0.01em;
}
.tutor-md-content h1 { font-size: 17px; }
.tutor-md-content h2 { font-size: 15.5px; border-bottom: 1px solid rgba(139, 92, 246, 0.08); padding-bottom: 4px; }
.tutor-md-content h3 { font-size: 14.5px; }
.tutor-md-content h4 { font-size: 13.5px; color: #64748b; }

/* ========== 打字动画 ========== */
.tutor-typing {
  display: inline-flex;
  gap: 6px;
  padding: 8px 0;
}
.tutor-typing span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: linear-gradient(135deg, #c4b5fd, #a78bfa);
  animation: tutor-bounce 1.4s infinite ease-in-out;
}
.tutor-typing span:nth-child(1) { animation-delay: -0.32s; }
.tutor-typing span:nth-child(2) { animation-delay: -0.16s; }
@keyframes tutor-bounce {
  0%, 80%, 100% { transform: scale(0); opacity: 0.3; }
  40% { transform: scale(1); opacity: 1; }
}

/* ========== 输入栏 ========== */
.tutor-input-bar {
  display: flex;
  gap: 10px;
  padding: 14px 18px;
  border-top: 1px solid rgba(139, 92, 246, 0.05);
  background: linear-gradient(180deg, #faf9ff, #f8f7ff);
}
.tutor-input {
  flex: 1;
  border: 1.5px solid #e9e5f5;
  border-radius: 14px;
  padding: 10px 16px;
  font-size: 13.5px;
  outline: none;
  transition: all 0.25s;
  background: white;
  color: #1e293b;
}
.tutor-input:focus {
  border-color: #a78bfa;
  box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.12);
}
.tutor-input:disabled {
  background: #f9f8ff;
  color: #a1a1aa;
}
.tutor-input::placeholder { color: #c4b5fd; }

.tutor-send-btn {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  background: linear-gradient(135deg, #a78bfa, #8b5cf6);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  flex-shrink: 0;
}
.tutor-send-btn svg { width: 17px; height: 17px; }
.tutor-send-btn:hover:not(:disabled) {
  transform: scale(1.08);
  box-shadow: 0 6px 18px rgba(139, 92, 246, 0.3);
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
}
.tutor-send-btn:active:not(:disabled) {
  transform: scale(0.95);
}
.tutor-send-btn:disabled {
  background: #e9e5f5;
  cursor: not-allowed;
}

/* ========== 缩放手柄 ========== */
.tutor-resize-handle {
  position: absolute;
  top: 0;
  left: 0;
  width: 24px;
  height: 24px;
  cursor: nw-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.25s;
  color: #c4b5fd;
}
.tutor-dialog:hover .tutor-resize-handle { opacity: 0.5; }
.tutor-resize-handle:hover { opacity: 1 !important; }
</style>
