<template>
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

    <!-- ==================== 中间栏：资源详情 ==================== -->
    <transition name="slide-fade">
      <div v-if="selectedResource" class="w-[400px] flex-shrink-0 flex flex-col card overflow-hidden animate-fade-in-up mx-2">
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
            @click="selectedResourceId = null; selectedResource = null; quizData = null; gradingResult = null"
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
            <QuizPlayer v-if="quizData" :data="quizData" @submit="onQuizSubmit" />
            <div v-else class="text-center py-8 text-navy-300 text-sm">
              <p>题目数据加载中...</p>
            </div>

            <!-- 批改结果 -->
            <div v-if="gradingResult" class="mt-4 p-4 rounded-xl border border-navy-100/50">
              <h4 class="font-display text-sm font-semibold text-navy-800 mb-2">批改结果</h4>
              <div class="text-2xl font-bold mb-2" :class="(gradingResult.score || 0) >= 80 ? 'text-emerald-600' : (gradingResult.score || 0) >= 60 ? 'text-amber-600' : 'text-red-500'">
                {{ gradingResult.score ?? '—' }}分
              </div>
              <p v-if="gradingResult.feedback" class="text-sm text-navy-600 leading-relaxed">{{ gradingResult.feedback }}</p>
              <div v-if="gradingResult.key_points_hit?.length" class="mt-2">
                <p class="text-xs font-medium text-emerald-600 mb-1">掌握的知识点:</p>
                <div class="flex flex-wrap gap-1">
                  <span v-for="p in gradingResult.key_points_hit" :key="p" class="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-600">{{ p }}</span>
                </div>
              </div>
              <div v-if="gradingResult.key_points_missed?.length" class="mt-2">
                <p class="text-xs font-medium text-red-500 mb-1">需巩固的知识点:</p>
                <div class="flex flex-wrap gap-1">
                  <span v-for="p in gradingResult.key_points_missed" :key="p" class="text-[10px] px-1.5 py-0.5 rounded-full bg-red-50 text-red-500">{{ p }}</span>
                </div>
              </div>
              <div v-if="gradingResult.improvement_suggestions?.length" class="mt-2">
                <p class="text-xs font-medium text-navy-500 mb-1">改进建议:</p>
                <ul class="text-xs text-navy-600 space-y-1">
                  <li v-for="(s, i) in gradingResult.improvement_suggestions" :key="i" class="flex gap-1.5">
                    <span class="text-navy-300">{{ i + 1 }}.</span><span>{{ s }}</span>
                  </li>
                </ul>
              </div>
            </div>
          </template>

          <!-- 文档/阅读类型 -->
          <template v-else-if="selectedResource.moduleType === 'document' || selectedResource.moduleType === 'reading'">
            <div v-if="selectedResource.moduleData?.content" class="prose prose-sm max-w-none text-navy-700 leading-relaxed markdown-body" v-html="renderMd(selectedResource.moduleData.content)"></div>
            <div v-else class="text-center py-8 text-navy-300 text-sm">
              <p>资源内容待生成</p>
            </div>
          </template>

          <!-- 导图类型 -->
          <template v-else-if="selectedResource.moduleType === 'mindmap'">
            <div v-if="selectedResource.moduleData?.content" class="text-sm text-navy-700 leading-relaxed markdown-body" v-html="renderMd(selectedResource.moduleData.content)"></div>
            <div v-else class="text-center py-8 text-navy-300 text-sm">
              <p>思维导图待生成</p>
            </div>
          </template>

          <!-- 代码类型 -->
          <template v-else-if="selectedResource.moduleType === 'code'">
            <div v-if="selectedResource.moduleData?.content" class="text-sm font-mono text-navy-700 leading-relaxed markdown-body" v-html="renderMd(selectedResource.moduleData.content)"></div>
            <div v-else class="text-center py-8 text-navy-300 text-sm">
              <p>代码示例待生成</p>
            </div>
          </template>

          <!-- 其他类型 -->
          <template v-else>
            <div v-if="selectedResource.moduleData?.content" class="text-sm text-navy-700 leading-relaxed markdown-body" v-html="renderMd(selectedResource.moduleData.content)"></div>
            <div v-else class="text-center py-8 text-navy-300 text-sm">
              <p>资源内容待生成</p>
            </div>
          </template>
        </div>
      </div>
    </transition>

    <!-- ==================== 右侧栏：对话界面 ==================== -->
    <div class="flex-1 flex flex-col card overflow-hidden animate-fade-in-up" style="animation-delay: 0.1s">
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
            @click="chatStore.stopGeneration()"
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
                <p class="text-sm text-navy-700 truncate">{{ session.title }}</p>
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
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { getPlan, updatePlan } from '@/api/plan'
import { getPlanResources, getResource } from '@/api/resource'
import { parseMarkdown } from '@/utils/markdown'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
import QuizPlayer from '@/components/resource/QuizPlayer.vue'
import type { LearningPlan, LearningResource } from '@/types/plan'
import type { QuizData, QuizQuestion } from '@/types/quiz'

const route = useRoute()
const planId = Number(route.params.id)
const planIdStr = String(planId)
const chatStore = useChatStore()
const authStore = useAuthStore()

// ==================== 状态 ====================
const plan = ref<LearningPlan | null>(null)
const resources = ref<LearningResource[]>([])
const selectedModuleIndex = ref(-1)
const selectedResourceId = ref<number | null>(null)
const selectedResource = ref<LearningResource | null>(null)
const quizData = ref<QuizData | null>(null)
const gradingResult = ref<Record<string, any> | null>(null)
const messagesContainer = ref<HTMLElement>()
const inputText = ref('')
const showModifyInput = ref(false)
const modifyText = ref('')
const sidebarCollapsed = ref(false)
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
  document: '文档', mindmap: '导图', quiz: '题目', code: '代码', reading: '阅读',
}

// ==================== 计算属性 ====================

// 按 moduleOrder 分组构建模块列表
const modules = computed(() => {
  const moduleMap = new Map<number, { order: number; title: string; estimatedHours: number; resourceTypes: string[]; resources: LearningResource[] }>()
  resources.value.forEach(r => {
    if (!moduleMap.has(r.moduleOrder)) {
      moduleMap.set(r.moduleOrder, {
        order: r.moduleOrder,
        title: r.moduleData?.module_title || `模块 ${r.moduleOrder}`,
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

// ==================== 资源详情 ====================

function selectModule(index: number) {
  if (selectedModuleIndex.value === index) {
    // 收起当前模块，清除选中状态
    selectedModuleIndex.value = -1
    selectedResourceId.value = null
    selectedResource.value = null
    quizData.value = null
    gradingResult.value = null
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
    gradingResult.value = null
    return
  }

  selectedResourceId.value = res.id
  selectedResource.value = res
  gradingResult.value = null

  // 展开侧栏中包含该资源的模块
  const modIdx = modules.value.findIndex(m => m.resources.some(r => r.id === res.id))
  if (modIdx >= 0) {
    selectedModuleIndex.value = modIdx
  }

  // 解析题目数据
  if (res.moduleType === 'quiz') {
    quizData.value = parseQuizData(res)
  } else {
    quizData.value = null
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
      points: 20,
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
    points: q.points || 20,
  }))

  return {
    title: md.title || md.quiz_title || '练习题',
    description: md.description || '',
    questions,
    totalPoints: md.totalPoints || md.total_points || questions.length * 20,
    estimatedMinutes: md.estimatedMinutes || questions.length * 2,
  }
}

// ==================== 答题提交 ====================

function onQuizSubmit(userAnswers: Record<number, any>) {
  if (!quizData.value) return

  const gradingMessage = quizData.value.questions.map((q, i) => {
    const ua = userAnswers[i]
    const userAns = Array.isArray(ua) ? ua.map((idx: number) => q.options?.[idx] ?? String(idx)).join(', ') : (q.options?.[ua] ?? String(ua ?? '未作答'))
    const correctAns = Array.isArray(q.correctAnswer) ? q.correctAnswer.join(', ') : String(q.correctAnswer)
    return `${i + 1}. ${q.question}\n   用户答案: ${userAns}\n   正确答案: ${correctAns}`
  }).join('\n\n')

  const message = `请批改以下答题结果，给出分数和详细分析：\n\n${gradingMessage}`
  chatStore.sendMessage(message, planIdStr)
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

// ==================== 滚动 ====================

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

watch(() => chatStore.messages.length + chatStore.streamBuffer.length, scrollToBottom)

// ==================== 消息发送 ====================

function sendMessage(text?: string) {
  const msg = text || inputText.value.trim()
  if (!msg) return
  inputText.value = ''
  showModifyInput.value = false
  chatStore.sendMessage(msg, planIdStr)
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
  return { document: 'bg-blue-50 text-blue-500', mindmap: 'bg-purple-50 text-purple-500', quiz: 'bg-amber-50 text-amber-500', code: 'bg-emerald-50 text-emerald-500', reading: 'bg-rose-50 text-rose-500' }[type] || 'bg-navy-50 text-navy-500'
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

// ==================== 生命周期 ====================

onMounted(async () => {
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

  // 加载会话列表，如果已有活跃会话则不重新加载消息（避免中断流式输出）
  await chatStore.loadSessions(planIdStr)
  if (!chatStore.activeSessionId && chatStore.sessions.length > 0) {
    await chatStore.selectSession(chatStore.sessions[0].sessionId)
  }
})
</script>

<style scoped>
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.3s ease;
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateX(-20px);
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
