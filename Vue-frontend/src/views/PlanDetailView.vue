<template>
  <div class="plan-detail-page h-full w-full flex flex-col overflow-hidden">
    <div v-if="!plan" class="flex items-center justify-center h-full flex-1">
      <div class="text-center">
        <svg class="w-12 h-12 mx-auto text-navy-200 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" class="opacity-25" /><path d="M4 12a8 8 0 018-8" class="opacity-75" stroke-linecap="round" />
        </svg>
        <p class="mt-3 text-navy-400">加载中...</p>
      </div>
    </div>

    <div v-else class="plan-detail-workspace flex gap-0 h-full w-full overflow-x-auto overflow-y-hidden flex-1 custom-scrollbar">
    <!-- ==================== 左侧栏：模块列表（可折叠） ==================== -->
    <div
      class="plan-detail-sidebar flex-shrink-0 flex flex-col overflow-hidden transition-all duration-300 animate-fade-in-up"
      :class="sidebarCollapsed ? 'w-0 opacity-0' : 'w-[320px]'"
    >
      <div class="plan-detail-sidebar__inner flex flex-col h-full min-w-[320px]">
        <!-- Plan header -->
        <div class="plan-detail-sidebar__header px-4 py-3.5">
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
              class="p-1 rounded transition-colors"
              :class="isTreeMode ? 'text-navy-600 bg-navy-50' : 'text-navy-300 hover:text-navy-600 hover:bg-navy-50'"
              :title="isTreeMode ? '返回学习模式' : '进入知识树'"
              @click="toggleTreeMode"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 3v6" />
                <path d="M6 13h12" />
                <path d="M6 13v5" />
                <path d="M18 13v5" />
                <circle cx="12" cy="9" r="2" />
                <circle cx="6" cy="19" r="2" />
                <circle cx="18" cy="19" r="2" />
              </svg>
            </button>
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
            <span class="text-xs text-navy-400">{{ planProgress }}%</span>
          </div>
          <div class="mt-2 h-1.5 bg-navy-100 rounded-full overflow-hidden">
            <div class="h-full bg-gradient-to-r from-navy-400 to-sage-500 rounded-full transition-all duration-500" :style="{ width: `${planProgress}%` }"></div>
          </div>
        </div>

        <!-- 知识树大纲 -->
        <div class="plan-detail-sidebar__outline flex-1 min-h-0">
          <PlanResourceOutline
            :tree-modules="outlineTreeModules"
            :selected-module-id="selectedOutlineModuleId"
            :selected-resource-id="selectedResourceId"
            :type-labels="typeLabels"
            :loading="outlineLoading"
            :header-subtitle="outlineHeaderSubtitle"
            :meta-text="outlineMetaText"
            :empty-title="outlineEmptyTitle"
            :empty-hint="outlineEmptyHint"
            :progress-map="progressMap"
            :stuck-resource-ids="stuckResources"
            :drag-hint="isTreeMode && knowledgeTreeStore.draggingNodeId ? '松开鼠标，将节点挂到目标模块下' : undefined"
            :tree-mode="isTreeMode"
            :tree-dn-d="isTreeMode"
            @select-module="onOutlineSelectModule"
            @select-resource="onOutlineSelectResource"
            @retry-resource="handleRetryById"
            @generate-content="generateFromTreeNode"
            @drop-node="handleOutlineDropNode"
            @mount-resource="handleOutlineMountResource"
            @toggle-complete="onOutlineToggleComplete"
            @delete-resource="onOutlineDeleteResource"
          />
        </div>

      </div>
    </div>

    <!-- 折叠/展开按钮 -->
    <button
      class="plan-detail-collapse flex-shrink-0 flex items-center justify-center transition-colors"
      @click="sidebarCollapsed = !sidebarCollapsed"
      :title="sidebarCollapsed ? '展开侧栏' : '收起侧栏'"
    >
      <svg class="w-4 h-4 text-navy-400 transition-transform duration-300" :class="sidebarCollapsed ? 'rotate-180' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="15 18 9 12 15 6" />
      </svg>
    </button>

    <template v-if="isTreeMode">
      <section
        v-if="!treeContentVisible"
        class="plan-tree-stage flex min-w-[720px] flex-1 flex-col overflow-hidden"
      >
        <header class="flex flex-shrink-0 items-center justify-between gap-3 border-b border-navy-100 px-4 py-3">
          <div class="min-w-0">
            <h3 class="truncate font-display text-sm font-semibold text-navy-800">
              {{ knowledgeTreeStore.tree?.title || plan.title }}
            </h3>
            <p class="mt-0.5 truncate text-xs text-navy-400">
              {{ selectedTreeNode?.title || '选择节点后开始拆分' }}
            </p>
          </div>
          <div class="flex flex-shrink-0 items-center gap-2">
            <button
              v-if="knowledgeTreeStore.activeSource"
              class="h-8 rounded-lg bg-red-50 px-3 text-xs font-semibold text-red-600 hover:bg-red-100"
              @click="knowledgeTreeStore.stopStream"
            >
              {{ knowledgeTreeStore.fpStreamingActive ? '■ 停止拆解' : '停止' }}
            </button>
          </div>
        </header>

        <div v-if="knowledgeTreeStore.error" class="mx-4 mt-3 rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-600">
          {{ knowledgeTreeStore.error }}
        </div>

        <div v-if="showBootstrapPreview" class="mx-4 mt-3">
          <TreeBootstrapPreview
            :topics="knowledgeTreeStore.previewTopics"
            :loading="knowledgeTreeStore.previewLoading"
            :error="knowledgeTreeStore.previewError"
            :growing="knowledgeTreeStore.growProgress.growing"
            :current-branch="knowledgeTreeStore.growProgress.currentBranch"
            :done-count="knowledgeTreeStore.growProgress.doneCount"
            :total-count="knowledgeTreeStore.growProgress.totalCount"
            @confirm="knowledgeTreeStore.confirmPreviewGrow"
            @skip="knowledgeTreeStore.skipPreviewAndGrow"
            @retry="knowledgeTreeStore.startPreview"
          />
        </div>

        <div class="relative min-h-0 flex-1 p-3">
          <KnowledgeTreeCanvas
            :nodes="knowledgeTreeStore.nodes"
            :root-node-id="rootTreeNodeId"
            :selected-node-id="knowledgeTreeStore.currentNodeId"
            v-model:pan-x="knowledgeTreeStore.panX"
            v-model:pan-y="knowledgeTreeStore.panY"
            v-model:zoom="knowledgeTreeStore.zoom"
            @select="selectTreeNode"
            @toggle-collapse="toggleTreeNodeCollapse"
            @open-subdivide="openTreeSubdivide"
            @delete-node="confirmDeleteTreeNode"
            @node-drag-start="knowledgeTreeStore.setDraggingNodeId($event)"
            @node-drag-end="knowledgeTreeStore.setDraggingNodeId(null)"
          />
          <div
            v-if="knowledgeTreeStore.loading && !knowledgeTreeStore.activeSource"
            class="absolute inset-3 flex items-center justify-center rounded-lg bg-white/60"
          >
            <svg class="h-8 w-8 animate-spin text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" class="opacity-25" />
              <path d="M4 12a8 8 0 0 1 8-8" class="opacity-75" stroke-linecap="round" />
            </svg>
          </div>
        </div>
        <button
          v-if="knowledgeTreeStore.fpStreamingActive"
          type="button"
          class="fp-stop-button"
          title="停止第一性原理拆解；已拆出的卡片会保留"
          @click="knowledgeTreeStore.stopStream"
        >
          ■ 停止拆解
        </button>
      </section>

      <TreeSubdividePopover
        :node="treePopoverNode"
        :options="treeSubdivisionOptions"
        :caution="knowledgeTreeStore.subdivisionCaution"
        :loading="knowledgeTreeStore.subdivisionOptionsLoading"
        :error="knowledgeTreeStore.subdivisionOptionsError"
        @close="closeTreeSubdivide"
        @load-options="loadTreeSubdivideOptions"
        @single-angle="runSingleAngleSplit"
        @multi-angle="runMultiAngleSplit"
        @first-principles="runFirstPrinciplesSplit"
      />
    </template>

    <template v-if="!isTreeMode || treeContentVisible">
    <!-- ==================== 中间栏：资源详情（学习模式 / 知识树内容预览） ==================== -->
    <div
      class="plan-resource-panel resource-panel flex flex-col overflow-hidden"
      :class="{
        'resource-panel--closed': !selectedResource && !showResourceStreamPreview,
        '!transition-none': isDragging,
        'fixed inset-0 z-40 m-0 bg-white rounded-none border-none shadow-none': isFullscreen,
        'plan-resource-panel--spaced': !isFullscreen
      }"
      :style="isFullscreen ? {} : panelStyle"
    >
      <template v-if="selectedResource">
        <!-- 标题栏 -->
        <div class="plan-resource-panel__header px-4 py-3 flex items-center justify-between">
          <div class="flex items-center gap-2 min-w-0">
            <button
              v-if="isTreeMode"
              class="p-1 rounded text-navy-400 hover:text-navy-700 hover:bg-navy-50 transition-colors flex-shrink-0"
              title="返回知识树"
              @click="closeTreeContentPanel"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </button>
            <span class="text-[10px] px-1.5 py-0.5 rounded-full flex-shrink-0" :class="badgeClass(selectedResource.moduleType)">
              {{ typeLabels[selectedResource.moduleType] || selectedResource.moduleType }}
            </span>
            <h3 class="font-display text-sm font-semibold text-navy-800 truncate">
              {{ selectedResource.moduleData?.title || '学习资源' }}
            </h3>
          </div>
          <div class="flex items-center gap-1.5 flex-shrink-0">
            <button
              v-if="['text', 'document', 'reading'].includes(selectedResource.moduleType)"
              class="p-1 rounded text-navy-300 hover:text-navy-600 hover:bg-navy-50 transition-colors"
              @click="exportToPdf(selectedResource)"
              title="导出为 PDF"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
            </button>
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
              :grading-tokens="gradingStreamTokens"
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
            <div id="pdf-content" v-if="selectedResource.moduleData?.content" class="prose prose-sm max-w-none text-navy-700 leading-relaxed markdown-body" v-html="renderedResourceContent"></div>
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
            <div v-if="selectedResource.moduleData?.videos?.length" class="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <VideoPlayer 
                v-for="(v, vi) in selectedResource.moduleData.videos" 
                :key="vi" 
                :video="v" 
              />
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
                sandbox="allow-scripts"
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

          <!-- PPT 类型 -->
          <template v-else-if="selectedResource.moduleType === 'pptx'">
            <!-- 切换按钮（两种预览都有时显示） -->
            <div
              v-if="selectedResource.moduleData?.pptx_url && selectedResource.moduleData?.html"
              class="flex items-center justify-end gap-1 mb-2"
            >
              <button
                class="px-2.5 py-1 text-xs rounded-l-md border transition-colors"
                :class="pptxViewMode === 'office' ? 'bg-violet-600 text-white border-violet-600' : 'bg-white text-navy-500 border-navy-200 hover:bg-navy-50'"
                @click="pptxViewMode = 'office'"
              >Office 预览</button>
              <button
                class="px-2.5 py-1 text-xs rounded-r-md border border-l-0 transition-colors"
                :class="pptxViewMode === 'html' ? 'bg-violet-600 text-white border-violet-600' : 'bg-white text-navy-500 border-navy-200 hover:bg-navy-50'"
                @click="pptxViewMode = 'html'"
              >卡片预览</button>
            </div>
            <!-- Office Online Viewer 预览 -->
            <PptxViewer
              v-if="pptxViewMode === 'office' && selectedResource.moduleData?.pptx_url"
              :pptx-url="selectedResource.moduleData.pptx_url"
              :slide-count="selectedResource.moduleData.slide_count"
              :download-url="selectedResource.moduleData.pptx_filename ? pptxDownloadUrl(selectedResource.moduleData.pptx_filename) : ''"
            />
            <!-- HTML 卡片预览 -->
            <div v-else-if="selectedResource.moduleData?.html" class="pptx-wrapper">
              <div class="pptx-toolbar">
                <span class="pptx-slide-count">共 {{ selectedResource.moduleData.slide_count || 0 }} 页</span>
                <a
                  v-if="selectedResource.moduleData.pptx_filename"
                  class="pptx-download-btn"
                  :href="pptxDownloadUrl(selectedResource.moduleData.pptx_filename)"
                  download
                >
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
                  下载 PPT
                </a>
              </div>
              <div class="pptx-stage">
                <iframe
                  class="pptx-frame"
                  :class="{ 'pointer-events-none': isDragging }"
                  :srcdoc="selectedResource.moduleData.html"
                  sandbox="allow-scripts allow-same-origin"
                  title="PPT 预览"
                ></iframe>
              </div>
            </div>
            <div v-else class="text-center py-8 text-navy-300 text-sm">
              <p>PPT 内容待生成</p>
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
            <template v-if="placeholder.type === 'quiz'">
              <QuizStreamPreview :raw-json="chatStore.resourceStreamBuffers[placeholder.id]" />
            </template>
            <div v-else-if="chatStore.resourceStreamBuffers[placeholder.id]" class="text-sm text-navy-700 leading-relaxed markdown-body" v-html="renderMd(chatStore.resourceStreamBuffers[placeholder.id])"></div>
            <div v-else class="text-xs text-navy-400 animate-pulse">等待生成...</div>
          </div>
          <span class="inline-block w-0.5 h-4 bg-navy-400 ml-0.5 animate-pulse align-text-bottom"></span>
        </div>
      </template>
    </div>

    <!-- 拖拽分隔线（始终在 DOM 中，width 过渡动画） -->
    <div
      class="plan-resource-divider resource-divider flex-shrink-0 flex items-center justify-center cursor-col-resize group"
      :class="{ 'resource-divider--closed': !selectedResource && !showResourceStreamPreview, 'w-2': isDragging, 'w-1.5': !isDragging }"
      @mousedown="onDividerMouseDown"
    >
      <div class="w-0.5 h-8 rounded-full transition-colors" :class="isDragging ? 'bg-navy-400' : 'bg-navy-200 group-hover:bg-navy-400'"></div>
    </div>

    <!-- ==================== 右侧栏：对话界面 ==================== -->
    <aside class="plan-chat-shell">
      <PlanChatPanel
        ref="planChatPanelRef"
        class="plan-chat-panel"
        :plan-id="planIdStr"
        :resource-id="selectedResource?.id ?? null"
        v-model:mode="chatPanelMode"
        @confirm-breakdown="confirmBreakdown()"
        @submit-modification="submitModification"
        @generate-resource="generateResource"
        @open-resource="openResourceById"
      />
    </aside>
    </template>
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

  <!-- 删除资源确认弹窗 -->
  <ConfirmDialog
    :visible="showDeleteResourceConfirm"
    title="删除学习资源"
    :message="`确定要删除资源「${deletingResource?.moduleData?.title || deletingResource?.moduleType || ''}」吗？该资源相关的对话、测验记录与学习进度将一并删除，此操作不可恢复。`"
    confirm-text="确认删除"
    cancel-text="取消"
    type="danger"
    @confirm="handleDeleteResourceConfirm"
    @cancel="handleDeleteResourceCancel"
  />
</div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPlan, updatePlan, generatePlanIcon } from '@/api/plan'
import { getPlanResources, getResource, getLatestTask, retryTask as retryTaskApi, deleteResource as deleteResourceApi, markResourceComplete, unmarkResourceComplete, getProgressByPlan, updateResourceContent, bulkCreateResources } from '@/api/resource'
import { parseMarkdown, extractCitations, normalizeMermaidCode } from '@/utils/markdown'
import { normalizeAnimationHtml } from '@/utils/animationHtml'
import { createNote, getNotes, updateNote, linkNoteToResource } from '@/api/note'
import { getQuizRecords, submitQuizSSE } from '@/api/quiz'
import { issueTicket } from '@/api/auth'
import { PYTHON_AI_BASE } from '@/api/request'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
import { useHeartbeat } from '@/composables/useHeartbeat'
import { showToast } from '@/composables/useToast'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import QuizPlayer from '@/components/resource/QuizPlayer.vue'
import QuizStreamPreview from '@/components/resource/QuizStreamPreview.vue'
import MindmapPlayer from '@/components/resource/MindmapPlayer.vue'
import VideoPlayer from '@/components/resource/VideoPlayer.vue'
import PptxViewer from '@/components/resource/PptxViewer.vue'
import PlanChatPanel from '@/components/chat/PlanChatPanel.vue'
import KnowledgeTreeCanvas from '@/components/tree/KnowledgeTreeCanvas.vue'
import PlanResourceOutline from '@/components/plan/PlanResourceOutline.vue'
import {
  buildOutlineTreeFromTreeItems,
  countOutlineTreeModules,
  countOutlineTreeResources,
  shouldShowModuleContextPromptForOutlineModule,
  type PlanOutlineTreeModule,
} from '@/components/plan/usePlanResourceOutline'
import TreeSubdividePopover from '@/components/tree/TreeSubdividePopover.vue'
import TreeBootstrapPreview from '@/components/tree/TreeBootstrapPreview.vue'
import { buildTreePlanOutline } from '@/components/tree/useTreePlanOutline'
import { useKnowledgeTreeStore } from '@/stores/knowledgeTree'
import { updateKnowledgeNode } from '@/api/knowledgeTree'
import type { KnowledgeNode } from '@/types/knowledgeTree'
import type { LearningPlan, LearningResource } from '@/types/plan'
import type { Note } from '@/types/note'
import type { GeneratedResourceRef } from '@/utils/sse'
import type { QuizData, QuizQuestion } from '@/types/quiz'
import type { TreeSubdivisionOption } from '@/types/knowledgeTree'
import type { MindElixirData } from 'mind-elixir'

const route = useRoute()
const router = useRouter()
const planId = computed(() => Number(route.params.id))
const planIdStr = computed(() => String(planId.value))
const isTreeMode = computed(() => route.query.view === 'tree')
const chatStore = useChatStore()
const authStore = useAuthStore()
const knowledgeTreeStore = useKnowledgeTreeStore()
const treePopoverNodeId = ref<string | null>(null)
const treeSubdivisionOptions = ref<TreeSubdivisionOption[]>([])
const bootstrapPreviewDismissed = ref(false)

const showBootstrapPreview = computed(() => {
  if (bootstrapPreviewDismissed.value) return false
  if (!knowledgeTreeStore.tree || !isTreeMode.value) return false
  // 仅在主动预览/生成过程中显示，L1 节点已从学习资源同步时不再弹出
  if (knowledgeTreeStore.growProgress.growing) return true
  if (knowledgeTreeStore.previewTopics.length > 0) return true
  if (knowledgeTreeStore.previewLoading) return true
  return false
})
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
  const range = selection && selection.rangeCount > 0 ? selection.getRangeAt(0) : null
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
const progressMap = ref<Record<number, number>>({}) // resourceId -> status (0/1/2)
const selectedModuleIndex = ref(-1)
const selectedResourceId = ref<number | null>(null)
const selectedResource = ref<LearningResource | null>(null)

// 流式资源生成开始时，清除选中的资源，让中间面板显示流式预览
watch(() => chatStore.isResourceStreaming, (streaming) => {
  if (streaming) {
    selectedResource.value = null
    selectedResourceId.value = null
  }
})
const isFullscreen = ref(false)
const quizData = ref<QuizData | null>(null)
const mindmapData = ref<MindElixirData | null>(null)
const gradingResult = ref<Record<string, any> | null>(null)
const quizSubmittedAnswers = ref<Record<number, any> | null>(null)
const gradingStreamTokens = ref<Record<number, string>>({})
const showExplanations = ref(false)
const showCitations = ref(true)
const pptxViewMode = ref<'office' | 'html'>('office')

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

function clearSelectedResource() {
  if (selectedResourceId.value !== null) {
    heartbeat.stop()
  }
  selectedResourceId.value = null
  selectedResource.value = null
  quizData.value = null
  mindmapData.value = null
  gradingResult.value = null
  quizSubmittedAnswers.value = null
  showExplanations.value = false
  isFullscreen.value = false
  chatStore.selectedModuleContext = null
}

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

    // 加载资源完成进度
    await loadProgress()
  } catch (e) {
    console.error('[PlanDetail] 加载资源失败:', e)
  }
}

async function loadProgress() {
  const id = planId.value
  if (!id) return
  try {
    const res = await getProgressByPlan(id)
    const map: Record<number, number> = {}
    for (const p of (res.data || [])) {
      map[p.resourceId] = p.status
    }
    progressMap.value = map
  } catch (e) {
    console.error('[PlanDetail] 加载进度失败:', e)
  }
}

async function toggleResourceComplete(res: LearningResource, e: Event) {
  e.stopPropagation()
  const planIdVal = planId.value
  if (!planIdVal) return
  const currentStatus = progressMap.value[res.id]
  try {
    if (currentStatus === 2) {
      await unmarkResourceComplete(planIdVal, res.id)
      progressMap.value = { ...progressMap.value, [res.id]: 1 }
    } else {
      await markResourceComplete(planIdVal, res.id)
      progressMap.value = { ...progressMap.value, [res.id]: 2 }
    }
  } catch (err) {
    console.error('[PlanDetail] 更新完成状态失败:', err)
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
  if (queryResource && !isTreeMode.value) {
    const resId = Number(queryResource)
    if (resId > 0) {
      openResourceById(resId)
    }
  }
  // 刷新后恢复：检查后端是否仍在生成中
  if (chatStore.activeSessionId) {
    await chatStore.recoverStreaming(String(planId.value))
  }
})

watch(selectedResource, (newRes) => {
  if (!newRes) {
    isFullscreen.value = false
  }
  pptxViewMode.value = 'office'
})

watch(planId, () => {
  if (planId.value) {
    heartbeat.stop()
    loadPlan()
    loadResources()
    selectedModuleIndex.value = -1
    clearSelectedResource()
    if (isTreeMode.value) {
      ensureTreeLoaded(true)
    }
  }
})

// 监听 ?resource= 查询参数变化（同 plan 内跳转不同资源）
watch(() => route.query.resource, (resId) => {
  if (resId && resources.value.length > 0 && !isTreeMode.value) {
    openResourceById(Number(resId))
  }
})

watch(isTreeMode, async value => {
  if (value) {
    bootstrapPreviewDismissed.value = false
  } else {
    closeTreeSubdivide()
  }
  // 两个模式都需要加载知识树（大纲侧栏统一展示树节点）
  await ensureTreeLoaded()
}, { immediate: true })

// 标题编辑
const editingTitle = ref(false)
const editTitle = ref('')

function saveTitle() {
  if (!editTitle.value.trim() || !plan.value) return
  const newTitle = editTitle.value.trim()
  plan.value.title = newTitle
  editingTitle.value = false
  updatePlan(planId.value, { title: newTitle }).catch(e =>
    console.error('[PlanDetail] 保存标题失败:', e)
  )
  // 异步生成计划图标
  regeneratePlanIcon()
}

async function regeneratePlanIcon() {
  if (!plan.value) return
  try {
    const resourceTitles = resources.value.map(r => {
      try {
        const md = typeof r.moduleData === 'string' ? JSON.parse(r.moduleData) : r.moduleData
        return md?.title || (r as any).title || ''
      } catch { return (r as any).title || '' }
    }).filter(Boolean)

    // Python后端会直接更新Java后端，无需前端再更新
    const result = await generatePlanIcon(planId.value, plan.value.title, resourceTitles)
    if (result.svg && plan.value) {
      // 本地更新planConfig用于立即显示
      const config = plan.value.planConfig ? (typeof plan.value.planConfig === 'string' ? JSON.parse(plan.value.planConfig) : plan.value.planConfig) : {}
      config.iconSvg = result.svg
      config.iconDescription = result.description
      plan.value.planConfig = config

      // 发送自定义广播事件让其他界面（如列表页）自动同步更新图标
      window.dispatchEvent(new CustomEvent('plan-icon-updated', {
        detail: { planId: planId.value, planConfig: config }
      }))
    }
  } catch (e) {
    console.warn('[PlanDetail] 生成图标失败:', e)
  }
}

// 从planConfig中提取图标SVG
const planIconSvg = computed(() => {
  if (!plan.value?.planConfig) return null
  try {
    const config = typeof plan.value.planConfig === 'string'
      ? JSON.parse(plan.value.planConfig)
      : plan.value.planConfig
    return config?.iconSvg || null
  } catch {
    return null
  }
})

function statusClass(status: number) {
  return status === 2 ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
}

function statusText(status: number) {
  return status === 2 ? '已完成' : '进行中'
}

function pptxDownloadUrl(filename: string) {
  return `${PYTHON_AI_BASE}/api/ai/resource/pptx/download/${filename}`
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
    pptx: 'bg-violet-100 text-violet-700',
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

type GeneratedResourcePlacement = {
  parentId: number | null
  moduleOrder: number
  nodeId?: string
}

function generatedResourcePlacement(): GeneratedResourcePlacement {
  const ctx = chatStore.selectedModuleContext
  const parent = ctx ? resources.value.find(resource => resource.id === ctx.moduleId) : null
  const fallbackOrder = resources.value.length > 0
    ? Math.max(...resources.value.map(resource => resource.moduleOrder)) + 1
    : 1

  return {
    parentId: parent?.id ?? null,
    moduleOrder: parent?.moduleOrder ?? fallbackOrder,
    nodeId: ctx?.nodeId
      || (parent?.moduleData?.nodeId as string | undefined)
      || (parent?.moduleData?.node_id as string | undefined),
  }
}

function withGeneratedResourceNodeData(
  moduleData: Record<string, any>,
  placement: GeneratedResourcePlacement = generatedResourcePlacement(),
) {
  return {
    ...moduleData,
    nodeId: moduleData.nodeId || placement.nodeId || undefined,
    node_id: moduleData.node_id || placement.nodeId || undefined,
  }
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
    const placement = generatedResourcePlacement()
    existing.parentId = existing.parentId ?? placement.parentId
    existing.moduleOrder = existing.moduleOrder || placement.moduleOrder
    existing.moduleData = withGeneratedResourceNodeData(existing.moduleData, placement)
    return existing
  }

  const placement = generatedResourcePlacement()

  const newResource: LearningResource = {
    id: resource.id || -Date.now(),
    planId: planId.value,
    parentId: placement.parentId,
    moduleOrder: placement.moduleOrder,
    moduleType,
    moduleData: withGeneratedResourceNodeData(moduleData, placement),
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
  document: '文档', text: '图文', mindmap: '导图', quiz: '题目', code: '代码', reading: '阅读', summary: '总结', video: '视频', image: '图片', diagram: '图表', animation: '动画', podcast: '播客', pptx: 'PPT',
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

// 基于 progressMap 计算计划进度
const planProgress = computed(() => {
  const validResourceIds = new Set(resources.value.filter(r => r.status >= 2).map(r => r.id))
  const total = validResourceIds.size
  const completed = Object.entries(progressMap.value).filter(
    ([id, status]) => status === 2 && validResourceIds.has(Number(id))
  ).length
  return total > 0 ? Math.min(100, Math.round((completed / total) * 100)) : 0
})


const rootTreeNodeId = computed(() => {
  const root = knowledgeTreeStore.nodes.find(node => !node.parentId)
    || knowledgeTreeStore.nodes.find(node => node.depth === 0)
    || knowledgeTreeStore.nodes[0]
  return root?.id || null
})

const treePlanOutline = computed(() =>
  buildTreePlanOutline(knowledgeTreeStore.nodes, resources.value, rootTreeNodeId.value)
)

const outlineTreeModules = computed(() => {
  return buildOutlineTreeFromTreeItems(treePlanOutline.value, resources.value)
})

const selectedOutlineModuleId = computed(() => {
  const nodeId = knowledgeTreeStore.currentNodeId
  return nodeId ? `node:${nodeId}` : null
})

const outlineLoading = computed(() =>
  knowledgeTreeStore.loading && outlineTreeModules.value.length === 0
)

const outlineHeaderSubtitle = '由知识树管理 · 在此生成学习内容'

const outlineEmptyTitle = '暂无知识树节点'

const outlineEmptyHint = '在画布中拆分节点后会出现在这里'

const outlineMetaText = computed(() => {
  const mods = outlineTreeModules.value
  if (mods.length === 0) return ''
  const moduleCount = countOutlineTreeModules(mods)
  const resourceCount = countOutlineTreeResources(mods)
  return `${moduleCount} 节点 · ${resourceCount} 资源`
})

const selectedTreeNode = computed(() =>
  knowledgeTreeStore.nodes.find(node => node.id === knowledgeTreeStore.currentNodeId) || null
)

/** 知识树模式下是否展示内容面板（仅用户主动选中资源时隐藏树画布） */
const treeContentVisible = computed(() =>
  isTreeMode.value && !!selectedResource.value
)

const treePopoverNode = computed(() =>
  knowledgeTreeStore.nodes.find(node => node.id === treePopoverNodeId.value) || null
)

async function ensureTreeLoaded(force = false) {
  if (!Number.isFinite(planId.value)) return
  if (!force && knowledgeTreeStore.tree?.planId === planId.value && knowledgeTreeStore.nodes.length > 0) return
  if (force) {
    await loadResources()
  }
  await knowledgeTreeStore.loadByPlan(planId.value)
}

async function enterTreeMode() {
  heartbeat.stop()
  clearSelectedResource()
  await router.replace({ query: { ...route.query, view: 'tree', resource: undefined } })
  await ensureTreeLoaded(true)
}

async function toggleTreeMode() {
  if (isTreeMode.value) {
    await exitTreeMode()
    return
  }
  await enterTreeMode()
}

async function exitTreeMode() {
  closeTreeSubdivide()
  const nextQuery = { ...route.query }
  delete nextQuery.view
  await router.replace({ query: nextQuery })
}

async function selectTreeNode(nodeId: string) {
  await knowledgeTreeStore.selectNode(nodeId)
}

async function toggleTreeNodeCollapse(nodeId: string) {
  await knowledgeTreeStore.toggleCollapsed(nodeId)
}

async function confirmDeleteTreeNode(nodeId: string) {
  const node = knowledgeTreeStore.nodes.find(n => n.id === nodeId)
  if (!node || !node.parentId) return // 根节点不可删除

  const hasChildren = knowledgeTreeStore.nodes.some(n => n.parentId === nodeId)
  const title = node.title || '未命名节点'
  const msg = hasChildren
    ? `确定删除「${title}」及其所有子节点？此操作不可恢复。`
    : `确定删除「${title}」？此操作不可恢复。`

  if (!window.confirm(msg)) return

  await knowledgeTreeStore.deleteNode(nodeId)
}

/** 查找资源对应的节点ID */
function findNodeIdForResource(res: LearningResource): string | null {
  const data = res.moduleData || {}

  // 1. 优先从资源的 nodeId 字段获取
  const directNodeId = (res as any).nodeId || data.nodeId || data.node_id
  if (directNodeId && knowledgeTreeStore.nodes.some(n => n.id === directNodeId)) {
    return directNodeId
  }

  // 2. 通过节点的 resourceId 字段反查
  const nodeByResourceId = knowledgeTreeStore.nodes.find(n => n.resourceId === res.id)
  if (nodeByResourceId) return nodeByResourceId.id

  // 3. 通过标题匹配
  const title = data.module_title || data.moduleTitle || data.title
  if (title) {
    const normalizedTitle = String(title).replace(/\s+/g, '').trim().toLowerCase()
    const nodeByTitle = knowledgeTreeStore.nodes.find(n =>
      n.title && n.title.replace(/\s+/g, '').trim().toLowerCase() === normalizedTitle
    )
    if (nodeByTitle) return nodeByTitle.id
  }

  // 4. 通过 moduleOrder 匹配（同 moduleOrder 的其他资源已关联的节点）
  if (res.moduleOrder != null && res.moduleOrder > 0) {
    const siblings = resources.value.filter(r =>
      r.id !== res.id && r.moduleOrder === res.moduleOrder
    )
    for (const sibling of siblings) {
      const siblingNodeId = findNodeIdForResource(sibling)
      if (siblingNodeId) return siblingNodeId
    }
  }

  return null
}

async function openOutlineResource(resourceId: number) {
  const resource = resources.value.find(item => item.id === resourceId)
  const nodeId = resource?.moduleData?.nodeId as string | undefined

  if (isTreeMode.value) {
    // 树模式下：只选中节点，不打开资源面板
    if (nodeId) {
      await knowledgeTreeStore.selectNode(nodeId)
    }
    return
  }

  await openResourceById(resourceId)
  if (nodeId) {
    await knowledgeTreeStore.selectNode(nodeId)
  }
}

function onOutlineSelectModule(mod: PlanOutlineTreeModule) {
  const nodeId = mod.nodeId
  if (!nodeId) return

  const showModuleContext = shouldShowModuleContextPromptForOutlineModule(mod)

  if (knowledgeTreeStore.currentNodeId === nodeId) {
    knowledgeTreeStore.currentNodeId = null
    clearSelectedResource()
    return
  }
  void selectTreeNode(nodeId).then(() => {
    if (isTreeMode.value) return
    const node = knowledgeTreeStore.nodes.find(n => n.id === nodeId)
    const resourceId = node?.resourceId
      || resources.value.find(r => {
        const data = r.moduleData || {}
        return data.nodeId === nodeId || data.node_id === nodeId
      })?.id
    if (resourceId) {
      void openResourceById(resourceId, undefined, { showModuleContext })
    } else {
      clearSelectedResource()
    }
  })
}

function onOutlineSelectResource(resourceId: number) {
  void openOutlineResource(resourceId)
}

async function handleRetryById(resourceId: number) {
  const res = resources.value.find(item => item.id === resourceId)
  if (res) await handleRetry(res)
}

function closeTreeContentPanel() {
  clearSelectedResource()
}

/** 为知识树节点创建或复用占位资源，供内容生成管线使用 */
async function ensureNodePlaceholderResource(node: KnowledgeNode, resourceType: string = 'text'): Promise<number> {
  if (node.resourceId && resourceType === 'text') return node.resourceId

  const linked = resources.value.find(item => {
    const data = item.moduleData || {}
    return data.nodeId === node.id || data.node_id === node.id
  })
  if (linked?.id && resourceType === 'text') {
    if (!node.resourceId) {
      await updateKnowledgeNode(node.id, { resourceId: linked.id })
      const idx = knowledgeTreeStore.nodes.findIndex(n => n.id === node.id)
      if (idx >= 0) knowledgeTreeStore.nodes[idx] = { ...knowledgeTreeStore.nodes[idx], resourceId: linked.id }
    }
    return linked.id
  }

  const maxOrder = resources.value.length > 0
    ? Math.max(...resources.value.map(r => r.moduleOrder))
    : 0
  const res = await bulkCreateResources([{
    planId: planId.value,
    moduleOrder: maxOrder + 1,
    moduleType: resourceType,
    moduleData: JSON.stringify({
      title: node.title,
      module_title: node.title,
      description: node.summary || '',
      nodeId: node.id,
    }),
    status: 1,
  }])
  const created = res.data?.[0]
  if (!created?.id) throw new Error('创建占位资源失败')

  await updateKnowledgeNode(node.id, { resourceId: created.id })
  const nodeIdx = knowledgeTreeStore.nodes.findIndex(n => n.id === node.id)
  if (nodeIdx >= 0) {
    knowledgeTreeStore.nodes[nodeIdx] = { ...knowledgeTreeStore.nodes[nodeIdx], resourceId: created.id }
  }
  parseModuleData([created])
  resources.value.push(created)
  return created.id
}

async function generateFromTreeNode(payload: { nodeId: string; type: string }) {
  const node = knowledgeTreeStore.nodes.find(item => item.id === payload.nodeId)
  if (!node) return

  try {
    await knowledgeTreeStore.selectNode(payload.nodeId)
    const resourceId = await ensureNodePlaceholderResource(node, payload.type)
    const ctx = {
      title: node.title,
      description: node.summary || '',
      moduleId: resourceId,
      nodeId: node.id,
      planId: planId.value,
    }
    chatStore.selectedModuleContext = ctx
    await chatStore.requestNodeResourceGeneration(String(planId.value), ctx, payload.type)
    // quiz 类型由流式预览（QuizStreamPreview）处理，不要提前打开占位资源
    if (!isTreeMode.value && payload.type !== 'quiz') {
      await openResourceById(resourceId, payload.type)
    }
  } catch (e) {
    knowledgeTreeStore.error = e instanceof Error ? e.message : '生成内容失败'
  }
}

async function handleOutlineDropNode(payload: { nodeId: string; targetNodeId: string }) {
  const ok = await knowledgeTreeStore.reparentNode(payload.nodeId, payload.targetNodeId)
  if (ok) {
    await knowledgeTreeStore.selectNode(payload.targetNodeId)
  }
  knowledgeTreeStore.setDraggingNodeId(null)
}

async function handleOutlineMountResource(payload: { resourceId: number; targetNodeId: string }) {
  const resource = resources.value.find(item => item.id === payload.resourceId)
  if (!resource) return
  try {
    const moduleData = {
      ...(resource.moduleData || {}),
      nodeId: payload.targetNodeId,
    }
    await updateResourceContent(payload.resourceId, moduleData, resource.status ?? 2)
    await loadResources()
    await knowledgeTreeStore.selectNode(payload.targetNodeId)
  } catch (e) {
    knowledgeTreeStore.error = e instanceof Error ? e.message : '关联资源失败'
  }
}

async function openTreeSubdivide(nodeId: string) {
  const selected = await knowledgeTreeStore.selectNode(nodeId)
  if (!selected) return
  treeSubdivisionOptions.value = []
  treePopoverNodeId.value = nodeId
}

function closeTreeSubdivide() {
  treePopoverNodeId.value = null
  treeSubdivisionOptions.value = []
}

async function loadTreeSubdivideOptions() {
  treeSubdivisionOptions.value = await knowledgeTreeStore.loadSubdivisionOptionsCurrent()
}

async function runSingleAngleSplit(angle: string) {
  closeTreeSubdivide()
  await knowledgeTreeStore.subdivideCurrent(angle)
}

async function runMultiAngleSplit(options: TreeSubdivisionOption[]) {
  closeTreeSubdivide()
  await knowledgeTreeStore.multiAngleSubdivideCurrent(options)
}

async function runFirstPrinciplesSplit() {
  closeTreeSubdivide()
  await knowledgeTreeStore.firstPrinciplesCurrent()
}

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

// === 导出为 PDF ===
async function exportToPdf(resource: any) {
  if (!resource) return;
  const contentEl = document.getElementById('pdf-content');
  if (!contentEl) return;

  try {
    // 克隆 DOM，避免修改页面上可见的元素
    const clone = contentEl.cloneNode(true) as HTMLElement;
    const images = clone.querySelectorAll('img');
    const placeholder = document.createElement('div');
    placeholder.style.cssText = 'position:absolute;left:-9999px;top:-9999px;';
    document.body.appendChild(placeholder);
    placeholder.appendChild(clone);

    // 通过后端代理将所有图片转为 base64 data URL，绕过 CORS
    const convertPromises = Array.from(images).map(async (img) => {
      const src = img.getAttribute('src');
      if (!src || src.startsWith('data:')) return;
      try {
        const resp = await fetch(`${PYTHON_AI_BASE}/api/ai/proxy-image?url=${encodeURIComponent(src)}`);
        const data = await resp.json();
        if (data.data_url) {
          img.setAttribute('src', data.data_url);
        }
      } catch {
        // 转换失败时保留原图，html2canvas 会处理
      }
    });
    await Promise.all(convertPromises);

    const html2pdf = (await import('html2pdf.js')).default;
    const opt = {
      margin:       10,
      filename:     `${resource.moduleData?.title || '文档'}.pdf`,
      image:        { type: 'jpeg', quality: 0.98 },
      html2canvas:  { scale: 2 },
      jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' },
      pagebreak:    { mode: ['avoid-all', 'css', 'legacy'] }
    };
    await html2pdf().set(opt).from(clone).save();

    // 清理临时 DOM
    document.body.removeChild(placeholder);
  } catch (err) {
    console.error('Failed to load html2pdf or export:', err);
  }
}

// === Mermaid 图表渲染 ===
async function renderMermaidInResource() {
  await nextTick()
  const containers = document.querySelectorAll('.markdown-body')
  for (const container of containers) {
    const unrendered = container.querySelectorAll('.gv-mermaid-wrapper:not([data-rendered="true"]):not([data-rendering="true"])')
    if (unrendered.length === 0) continue

    unrendered.forEach(el => el.setAttribute('data-rendering', 'true'))

    try {
      const mermaid = (await import('mermaid')).default
      if (!(window as any).__mermaid_initialized__) {
        mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose' })
        ;(window as any).__mermaid_initialized__ = true
      }

      for (const el of Array.from(unrendered)) {
        const codeBase64 = el.getAttribute('data-mermaid-code')
        if (!codeBase64) continue

        try {
          const rawCode = decodeURIComponent(codeBase64)
          const normalizedCode = normalizeMermaidCode(rawCode)

          const id = 'mermaid-' + Math.random().toString(36).substr(2, 9)
          const { svg } = await mermaid.render(id, normalizedCode)

          if (el.getAttribute('data-mermaid-code') !== codeBase64) continue

          // 构建带工具栏和缩放平移的容器
          const uid = Math.random().toString(36).substr(2, 6)
          el.innerHTML = `
            <div class="mermaid-viewer" data-uid="${uid}" style="position:relative;overflow:hidden;border-radius:12px;border:1px solid rgba(26,40,71,0.08);background:#fafbfc;">
              <div class="mermaid-toolbar" style="position:absolute;top:8px;right:8px;z-index:10;display:flex;gap:4px;opacity:0;transition:opacity 0.2s;">
                <button class="mermaid-zoom-in" title="放大" style="width:28px;height:28px;border-radius:6px;border:1px solid rgba(26,40,71,0.12);background:rgba(255,255,255,0.9);backdrop-filter:blur(8px);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:14px;color:#34508e;">+</button>
                <button class="mermaid-zoom-out" title="缩小" style="width:28px;height:28px;border-radius:6px;border:1px solid rgba(26,40,71,0.12);background:rgba(255,255,255,0.9);backdrop-filter:blur(8px);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:14px;color:#34508e;">-</button>
                <button class="mermaid-reset" title="重置" style="width:28px;height:28px;border-radius:6px;border:1px solid rgba(26,40,71,0.12);background:rgba(255,255,255,0.9);backdrop-filter:blur(8px);cursor:pointer;display:flex;align-items:center;justify-content:center;color:#34508e;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg></button>
                <div class="mermaid-export-dropdown" style="position:relative;">
                  <button class="mermaid-export-btn" title="导出图片" style="width:28px;height:28px;border-radius:6px;border:1px solid rgba(26,40,71,0.12);background:rgba(255,255,255,0.9);backdrop-filter:blur(8px);cursor:pointer;display:flex;align-items:center;justify-content:center;color:#34508e;">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                  </button>
                  <div class="mermaid-export-menu" style="display:none;position:absolute;right:0;top:100%;margin-top:4px;background:white;border-radius:8px;border:1px solid rgba(26,40,71,0.12);box-shadow:0 4px 12px rgba(0,0,0,0.1);overflow:hidden;min-width:90px;z-index:20;">
                    <button class="mermaid-export-png" style="width:100%;padding:6px 12px;text-align:left;font-size:12px;color:#34508e;background:none;border:none;cursor:pointer;font-family:inherit;" onmouseover="this.style.background='#f0f3f9'" onmouseout="this.style.background='none'">导出 PNG</button>
                    <button class="mermaid-export-svg" style="width:100%;padding:6px 12px;text-align:left;font-size:12px;color:#34508e;background:none;border:none;cursor:pointer;font-family:inherit;" onmouseover="this.style.background='#f0f3f9'" onmouseout="this.style.background='none'">导出 SVG</button>
                  </div>
                </div>
              </div>
              <div class="mermaid-viewport" style="transform-origin:0 0;cursor:grab;transition:none;padding:16px;">
                ${svg}
              </div>
            </div>
          `
          el.setAttribute('data-rendered', 'true')
          el.removeAttribute('data-rendering')
          el.classList.add('stream-fade-in')

          // 初始化缩放平移交互并居中
          _initMermaidInteraction(el, uid, true)
        } catch (err: any) {
          if (el.getAttribute('data-mermaid-code') === codeBase64) {
            console.warn('Mermaid rendering failed, showing raw code:', err.message)
            // 清理 mermaid.render 失败后插入到 body 的错误 SVG 残留
            document.querySelectorAll('div[id^="dmermaid-"], svg[id^="mermaid-"]').forEach(n => n.remove())
            el.innerHTML = `
              <pre class="text-xs text-navy-500 bg-navy-50 rounded-xl p-4 border border-navy-100/50 overflow-x-auto leading-relaxed">${normalizedCode}</pre>
            `
            el.setAttribute('data-rendered', 'true')
            el.removeAttribute('data-rendering')
          }
        }
      }
    } catch (err) {
      console.error('Failed to load Mermaid module:', err)
      unrendered.forEach(el => el.removeAttribute('data-rendering'))
    }
  }
}

function _initMermaidInteraction(wrapper: Element, uid: string, center = false) {
  const viewer = wrapper.querySelector(`.mermaid-viewer[data-uid="${uid}"]`) as HTMLElement
  if (!viewer) return
  const viewport = viewer.querySelector('.mermaid-viewport') as HTMLElement
  const toolbar = viewer.querySelector('.mermaid-toolbar') as HTMLElement
  if (!viewport || !toolbar) return

  let scale = 1
  let panX = 0
  let panY = 0
  let isDragging = false
  let startX = 0
  let startY = 0

  function applyTransform() {
    viewport.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`
  }

  viewer.addEventListener('mouseenter', () => { toolbar.style.opacity = '1' })
  viewer.addEventListener('mouseleave', () => { toolbar.style.opacity = '0' })

  viewer.addEventListener('wheel', (e: WheelEvent) => {
    e.preventDefault()
    const rect = viewer.getBoundingClientRect()
    const mouseX = e.clientX - rect.left
    const mouseY = e.clientY - rect.top
    const oldScale = scale
    scale = Math.max(0.2, Math.min(5, scale * (e.deltaY > 0 ? 0.9 : 1.1)))
    panX = mouseX - (mouseX - panX) * (scale / oldScale)
    panY = mouseY - (mouseY - panY) * (scale / oldScale)
    applyTransform()
  }, { passive: false })

  viewport.addEventListener('mousedown', (e: MouseEvent) => {
    if (e.button !== 0) return
    isDragging = true
    startX = e.clientX - panX
    startY = e.clientY - panY
    viewport.style.cursor = 'grabbing'
    e.preventDefault()
  })

  const onMove = (e: MouseEvent) => {
    if (!isDragging) return
    panX = e.clientX - startX
    panY = e.clientY - startY
    applyTransform()
  }
  const onUp = () => {
    if (isDragging) { isDragging = false; viewport.style.cursor = 'grab' }
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)

  viewer.querySelector('.mermaid-zoom-in')?.addEventListener('click', (e) => {
    e.stopPropagation(); scale = Math.min(5, scale * 1.25); applyTransform()
  })
  viewer.querySelector('.mermaid-zoom-out')?.addEventListener('click', (e) => {
    e.stopPropagation(); scale = Math.max(0.2, scale * 0.8); applyTransform()
  })
  viewer.querySelector('.mermaid-reset')?.addEventListener('click', (e) => {
    e.stopPropagation()
    scale = 1; panX = 0; panY = 0
    // 居中显示
    const vw = viewer.clientWidth
    const vh = viewer.clientHeight
    const sw = viewport.scrollWidth
    const sh = viewport.scrollHeight
    panX = Math.max(0, (vw - sw) / 2)
    panY = Math.max(0, (vh - sh) / 2)
    applyTransform()
  })

  // 导出下拉菜单
  const exportBtn = viewer.querySelector('.mermaid-export-btn') as HTMLElement
  const exportMenu = viewer.querySelector('.mermaid-export-menu') as HTMLElement
  if (exportBtn && exportMenu) {
    exportBtn.addEventListener('click', (e) => {
      e.stopPropagation()
      exportMenu.style.display = exportMenu.style.display === 'none' ? 'block' : 'none'
    })
    // 点击外部关闭
    const closeMenu = (e: MouseEvent) => {
      if (!exportMenu.contains(e.target as Node) && e.target !== exportBtn) {
        exportMenu.style.display = 'none'
      }
    }
    document.addEventListener('click', closeMenu)
  }

  async function _doExport(format: 'png' | 'svg') {
    const svgEl = viewport.querySelector('svg')
    if (!svgEl) return
    exportMenu.style.display = 'none'

    try {
      const cloned = svgEl.cloneNode(true) as SVGSVGElement
      cloned.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
      cloned.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink')

      const bbox = svgEl.getBoundingClientRect()
      const w = Math.ceil(bbox.width) || parseInt(cloned.getAttribute('width') || '800')
      const h = Math.ceil(bbox.height) || parseInt(cloned.getAttribute('height') || '600')
      cloned.setAttribute('width', String(w))
      cloned.setAttribute('height', String(h))
      cloned.removeAttribute('viewBox')

      // 内嵌字体 CSS 到 SVG（避免外部请求污染 canvas）
      let fontCss = ''
      try {
        const resp = await fetch('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Noto+Sans+SC:wght@400;600&display=swap')
        fontCss = await resp.text()
        // 将 url(...) 中的相对路径转为绝对路径
        fontCss = fontCss.replace(/url\((\/[^)]+)\)/g, 'url(https://fonts.gstatic.com$1)')
      } catch { /* 字体加载失败，降级 */ }

      // 注入 <style> 到 SVG
      const styleEl = document.createElementNS('http://www.w3.org/2000/svg', 'style')
      styleEl.textContent = fontCss + `
        .node rect, .node circle, .node polygon, .node ellipse { shape-rendering: crispEdges; }
        foreignObject div { display: inline-block; }
      `
      cloned.insertBefore(styleEl, cloned.firstChild)

      // 外层添加白色背景
      const bgRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
      bgRect.setAttribute('width', '100%')
      bgRect.setAttribute('height', '100%')
      bgRect.setAttribute('fill', '#ffffff')
      cloned.insertBefore(bgRect, cloned.firstChild)

      const svgData = new XMLSerializer().serializeToString(cloned)

      if (format === 'svg') {
        const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url; a.download = 'mermaid-diagram.svg'
        document.body.appendChild(a); a.click(); document.body.removeChild(a)
        URL.revokeObjectURL(url)
        return
      }

      // PNG: data URL → Image → Canvas
      const svgBase64 = btoa(unescape(encodeURIComponent(svgData)))
      const img = new Image()
      img.onload = () => {
        const canvas = document.createElement('canvas')
        const pad = 24
        canvas.width = img.naturalWidth + pad * 2
        canvas.height = img.naturalHeight + pad * 2
        const ctx = canvas.getContext('2d')!
        ctx.fillStyle = '#ffffff'
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.drawImage(img, pad, pad)
        try {
          canvas.toBlob((blob) => {
            if (blob) {
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url; a.download = 'mermaid-diagram.png'
              document.body.appendChild(a); a.click(); document.body.removeChild(a)
              URL.revokeObjectURL(url)
            }
          }, 'image/png')
        } catch (e) { console.error('Canvas export failed:', e) }
      }
      img.onerror = () => { console.error('SVG image load failed') }
      img.src = 'data:image/svg+xml;base64,' + svgBase64
    } catch (err) { console.error('导出图表失败:', err) }
  }

  viewer.querySelector('.mermaid-export-png')?.addEventListener('click', (e) => {
    e.stopPropagation(); _doExport('png')
  })
  viewer.querySelector('.mermaid-export-svg')?.addEventListener('click', (e) => {
    e.stopPropagation(); _doExport('svg')
  })

  // 初始居中
  if (center) {
    requestAnimationFrame(() => {
      const vw = viewer.clientWidth
      const vh = viewer.clientHeight
      const sw = viewport.scrollWidth
      const sh = viewport.scrollHeight
      panX = Math.max(0, (vw - sw) / 2)
      panY = Math.max(0, (vh - sh) / 2)
      applyTransform()
    })
  }
}

watch(() => selectedResource.value?.moduleData?.content, () => {
  // 流式输出进行中不渲染 mermaid：每个 chunk 都会通过 v-html 替换掉已渲染的 SVG，
  // 再触发 watch 调用 mermaid.render，造成图表反复重渲闪烁。
  // 仅在当前资源不在流式中时渲染。
  const rid = selectedResourceId.value
  if (chatStore.isResourceStreaming && rid != null && chatStore.resourceStreamBuffers[rid] != null) {
    return
  }
  renderMermaidInResource()
})

// 流式结束后统一渲染一次（此时内容为最终态，SVG 不再被 v-html 清除）
watch(() => chatStore.isResourceStreaming, (streaming) => {
  if (!streaming) {
    nextTick(() => renderMermaidInResource())
  }
})

// 切换选中资源时立即渲染
watch(selectedResourceId, () => {
  nextTick(() => renderMermaidInResource())
})

onMounted(() => {
  renderMermaidInResource()
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

function onOutlineToggleComplete(resourceId: number) {
  const res = resources.value.find(r => r.id === resourceId)
  if (res) toggleResourceComplete(res, new Event('click'))
}

function onOutlineDeleteResource(resourceId: number) {
  const res = resources.value.find(r => r.id === resourceId)
  if (res) confirmDeleteResource(res)
}

// 删除资源
const showDeleteResourceConfirm = ref(false)
const deletingResource = ref<LearningResource | null>(null)

function confirmDeleteResource(res: LearningResource) {
  deletingResource.value = res
  showDeleteResourceConfirm.value = true
}

function handleDeleteResourceCancel() {
  showDeleteResourceConfirm.value = false
  deletingResource.value = null
}

async function handleDeleteResourceConfirm() {
  const res = deletingResource.value
  if (!res) return
  try {
    await deleteResourceApi(res.id)
    // 从本地列表移除
    resources.value = resources.value.filter(r => r.id !== res.id)
    // 若删除的是当前选中资源，清空选中态
    if (selectedResourceId.value === res.id) {
      heartbeat.stop()
      selectedResourceId.value = null
      selectedResource.value = null
      quizData.value = null
      mindmapData.value = null
      gradingResult.value = null
      quizSubmittedAnswers.value = null
      showExplanations.value = false
      isFullscreen.value = false
    }
    showToast('资源已删除', 'success', { title: '删除成功' })
  } catch (e) {
    console.error('删除资源失败:', e)
    showToast('删除失败，请稍后重试', 'error', { title: '删除失败' })
  } finally {
    showDeleteResourceConfirm.value = false
    deletingResource.value = null
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

type ToggleResourceOptions = {
  showModuleContext?: boolean
}

function toggleResource(res: LearningResource, options: ToggleResourceOptions = {}) {
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
    // 取消左侧大纲高亮
    knowledgeTreeStore.currentNodeId = null
    return
  }

  // Stop previous heartbeat if switching resource
  if (selectedResourceId.value !== null) {
    heartbeat.stop()
  }

  selectedResourceId.value = res.id
  selectedResource.value = res

  // 联动左侧大纲：找到资源对应的节点并高亮
  const nodeId = findNodeIdForResource(res)
  if (nodeId) {
    knowledgeTreeStore.currentNodeId = nodeId
  }

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
  if (options.showModuleContext === false) {
    chatStore.selectedModuleContext = null
    return
  }

  const moduleTitle = res.moduleData?.module_title || res.moduleData?.title || `模块 ${res.moduleOrder}`
  const moduleDesc = res.moduleData?.description || res.moduleData?.module_description || ''
  chatStore.selectedModuleContext = {
    title: moduleTitle,
    description: moduleDesc,
    moduleId: res.id,
    planId: res.planId || planId.value,
    nodeId: (res.moduleData?.nodeId || res.moduleData?.node_id) as string | undefined,
  }
  // 仅在非 quiz 资源时提示（quiz 本身已是补充资源）
  if (res.moduleType !== 'quiz') {
  } else {
  }
}

/** 通过资源 ID 打开资源（先从本地列表查找，未命中则请求后端） */
async function openResourceById(
  resourceId: number,
  resourceType?: string,
  options: ToggleResourceOptions = {},
) {
  // 先从本地已加载的资源中查找
  const local = resources.value.find(r => r.id === resourceId)
  if (local) {
    toggleResource(local, options)
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
      toggleResource(res.data, options)
    }
  } catch (e) {
    console.error('Failed to open resource by ID:', e)
  }
}

function parsePartialQuizJSON(str: string): QuizData | null {
  if (!str.trim()) return null

  const quizTitleMatch = str.match(/"quiz_title"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)(?:"|$)/) ||
                         str.match(/"title"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)(?:"|$)/)
  const title = quizTitleMatch ? quizTitleMatch[1] : '练习题'
  
  const descMatch = str.match(/"description"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)(?:"|$)/)
  const description = descMatch ? descMatch[1] : ''

  const questionsIndex = str.indexOf('"questions"')
  if (questionsIndex === -1) {
    return { title, description, questions: [], totalPoints: 0, estimatedMinutes: 0 }
  }

  const questionsStr = str.substring(questionsIndex)
  const parts = questionsStr.split('{')
  const questions: any[] = []

  for (let i = 1; i < parts.length; i++) {
    const part = parts[i]

    // Extract question text
    const qMatch = part.match(/"question(?:_text)?"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)(?:"|$)/)
    const questionText = qMatch ? qMatch[1] : ''

    // Extract question type
    const tMatch = part.match(/"question_type"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)(?:"|$)/) ||
                   part.match(/"type"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)(?:"|$)/)
    const type = tMatch ? tMatch[1] : 'single_choice'

    // Extract difficulty
    const dMatch = part.match(/"difficulty"\s*:\s*(\d+)/)
    const difficulty = dMatch ? parseInt(dMatch[1]) : 3

    // Extract options
    const options: string[] = []
    const optMatch = part.match(/"options"\s*:\s*\[([^\]]*)(?:\]|$)/)
    if (optMatch) {
      const optStr = optMatch[1]
      const optRegex = /"([^"\\]*(?:\\.[^"\\]*)*)"/g
      let m
      while ((m = optRegex.exec(optStr)) !== null) {
        options.push(m[1])
      }
    }

    // Extract correct answer
    const caMatch = part.match(/"correct_answer"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)(?:"|$)/) ||
                    part.match(/"correctAnswer"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)(?:"|$)/)
    const correctAnswer = caMatch ? caMatch[1] : ''

    // Extract explanation
    const expMatch = part.match(/"explanation"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)(?:"|$)/)
    const explanation = expMatch ? expMatch[1] : ''

    if (questionText || options.length > 0) {
      questions.push({
        index: i - 1,
        type,
        question: questionText,
        options,
        correctAnswer,
        explanation,
        difficulty,
        points: 1,
      })
    }
  }

  return {
    title,
    description,
    questions,
    totalPoints: questions.length,
    estimatedMinutes: questions.length * 2
  }
}

function parseQuizData(res: LearningResource): QuizData | null {
  const md = res.moduleData
  if (!md) return null

  // questions 可能在顶层、md.content 对象里、或 md.content JSON 字符串里
  let rawQuestions = md.questions || []
  let title = md.title || md.quiz_title || '练习题'
  let description = md.description || ''

  if (rawQuestions.length === 0 && md.content) {
    try {
      const c = typeof md.content === 'string' ? JSON.parse(md.content) : md.content
      rawQuestions = c?.questions || []
      if (c?.quiz_title || c?.title) {
        title = c.quiz_title || c.title
      }
      if (c?.description) {
        description = c.description
      }
    } catch {
      // JSON.parse failed. If it's a string, try partial parsing.
      if (typeof md.content === 'string') {
        const partialData = parsePartialQuizJSON(md.content)
        if (partialData && partialData.questions.length > 0) {
          partialData.id = res.id // Add the ID so watch works correctly
          return partialData
        }
      }
    }
  }

  // 如果仍未找到结构化 questions，将 content 文本解析为简答题
  if (rawQuestions.length === 0) {
    const text = typeof md.content === 'string' ? md.content : (md.description || '')
    if (!text.trim()) return null
    // 如果 text 看起来是一堆以 { 开始的 JSON 文本（说明可能还在流式输出中），不要直接退化为 short_answer
    if (text.trim().startsWith('{') || text.trim().includes('"questions"')) {
      // 尝试部分解析，万一有内容了
      const partialData = parsePartialQuizJSON(text)
      if (partialData && partialData.questions.length > 0) {
        partialData.id = res.id
        return partialData
      }
      return null // 还在生成中，返回 null 不渲染 code block
    }
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
    id: res.id,
    title: title,
    description: description,
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
  gradingStreamTokens.value = {}
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
        onToken(index, token) {
          if (!gradingStreamTokens.value[index]) {
            gradingStreamTokens.value[index] = ''
          }
          gradingStreamTokens.value[index] += token
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

  // 如果当前选中的就是 quiz 资源，直接合并数据，防止流式输出/生成完重复添加
  if (selectedResource.value && selectedResource.value.moduleType === 'quiz') {
    const existing = resources.value.find(r => r.id === selectedResource.value!.id)
    if (existing) {
      existing.moduleData = {
        ...existing.moduleData,
        questions: data.questions,
      }
      quizData.value = parseQuizData(existing)
      chatStore.lastQuizResource = null
      return
    }
  }

  const placement = generatedResourcePlacement()
  const newResource: LearningResource = {
    id: Date.now(),
    planId: planId.value,
    parentId: placement.parentId,
    moduleOrder: placement.moduleOrder,
    moduleType: 'quiz',
    moduleData: withGeneratedResourceNodeData({
      title: '练习题',
      questions: data.questions,
    }, placement),
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

        // 防御性：确保 moduleData 中有 nodeId，以便侧栏正确挂载到树节点
        if (fullRes.moduleData && !fullRes.moduleData.nodeId && !fullRes.moduleData.node_id) {
          const ctxNodeId = chatStore.selectedModuleContext?.nodeId
          if (ctxNodeId) {
            fullRes.moduleData.nodeId = ctxNodeId
            fullRes.moduleData.node_id = ctxNodeId
          }
        }

        // 清理由于提前接收到内联内容而创建的临时资源
        const tempIndex = resources.value.findIndex(res => res.id < 0 && res.moduleType === fullRes.moduleType)
        if (tempIndex >= 0) {
          resources.value.splice(tempIndex, 1)
        }

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
  await ensureTreeLoaded(true)
  chatStore.lastGeneratedResources = null
})

// 监听流式资源更新 — 即时添加到侧栏
watch(() => chatStore.streamingResources.length, () => {
  const items = chatStore.streamingResources
  if (!items.length) return
  for (const { resource, content } of items) {
    if (resources.value.some(existing => existing.id === resource.id)) continue
    const placement = generatedResourcePlacement()
    const newRes: LearningResource = {
      id: resource.id,
      planId: planId.value,
      parentId: placement.parentId,
      moduleOrder: placement.moduleOrder,
      moduleType: resource.type || 'document',
      moduleData: withGeneratedResourceNodeData({
        title: resource.title,
        content,
      }, placement),
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
    const placement = generatedResourcePlacement()
    const placeholderRes: LearningResource = {
      id: p.id,
      planId: planId.value,
      parentId: placement.parentId,
      moduleOrder: p.moduleOrder ?? placement.moduleOrder,
      moduleType: p.type || 'document',
      moduleData: withGeneratedResourceNodeData({ title: p.title, content: '' }, placement),
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
      // 如果当前选中该资源，并且它是测验，实时解析更新 quizData
      if (selectedResourceId.value === resId && existing.moduleType === 'quiz') {
        quizData.value = parseQuizData(existing)
      }
    }
  }
}, { deep: true })
</script>

<style scoped>
.plan-detail-page {
  background:
    radial-gradient(circle at top left, rgba(239, 244, 255, 0.72), transparent 30%),
    linear-gradient(180deg, #fbfcff 0%, #f7f9fd 100%);
}

.plan-detail-workspace {
  gap: 10px;
  padding: 20px 20px 26px;
  align-items: stretch;
}

.plan-detail-sidebar {
  border: 1px solid rgba(185, 201, 232, 0.72);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 10px 28px rgba(42, 67, 113, 0.06);
}

.plan-detail-sidebar__inner {
  overflow: hidden;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 251, 255, 0.96) 100%);
}

.plan-detail-sidebar__header {
  min-height: 116px;
  border-bottom: 1px solid rgba(188, 203, 232, 0.58);
  background: linear-gradient(180deg, #ffffff 0%, rgba(249, 252, 255, 0.94) 100%);
}

.plan-detail-sidebar__outline {
  background: rgba(248, 251, 255, 0.78);
}

.plan-detail-collapse {
  width: 24px;
  align-self: stretch;
  margin: 14px -3px;
  border: 1px solid rgba(185, 201, 232, 0.62);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 8px 18px rgba(42, 67, 113, 0.05);
}

.plan-detail-collapse:hover {
  background: #eef3fb;
}

.plan-tree-stage,
.plan-resource-panel,
.plan-chat-shell :deep(.plan-chat-panel) {
  border: 1px solid rgba(185, 201, 232, 0.72);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 10px 28px rgba(42, 67, 113, 0.06);
}

.plan-tree-stage {
  margin: 0;
  background: rgba(255, 255, 255, 0.98);
}

.plan-tree-stage > header {
  min-height: 78px;
  border-bottom-color: rgba(188, 203, 232, 0.58);
  background: linear-gradient(180deg, #ffffff 0%, rgba(249, 252, 255, 0.94) 100%);
}

.plan-resource-panel {
  min-width: 0;
  background: rgba(255, 255, 255, 0.98);
  transition: width 0.3s ease, min-width 0.3s ease, margin 0.3s ease;
}

.plan-resource-panel--spaced {
  margin: 0;
}

.plan-resource-panel__header {
  min-height: 64px;
  border-bottom: 1px solid rgba(188, 203, 232, 0.58);
  background: linear-gradient(180deg, #ffffff 0%, rgba(249, 252, 255, 0.94) 100%);
}

.plan-resource-divider {
  width: 12px;
  margin: 14px -1px;
  border-radius: 999px;
  transition: width 0.25s ease, margin 0.25s ease, opacity 0.25s ease;
}

.plan-resource-divider.resource-divider--closed {
  width: 0;
  margin: 14px 0;
  opacity: 0;
  pointer-events: none;
}

.plan-chat-shell {
  display: flex;
  min-width: 340px;
  flex: 1 1 0;
  transition: flex-basis 0.3s ease;
}

.plan-chat-shell :deep(.plan-chat-panel) {
  width: 100%;
  min-width: 0;
  flex: 1 1 auto;
  animation-delay: 0.1s;
}

.plan-chat-shell :deep(.plan-chat-panel.card) {
  box-shadow: 0 10px 28px rgba(42, 67, 113, 0.06);
}

.plan-chat-shell :deep(.plan-chat-panel > div:first-child) {
  min-height: 72px;
  border-bottom-color: rgba(188, 203, 232, 0.58);
  background: linear-gradient(180deg, #ffffff 0%, rgba(249, 252, 255, 0.94) 100%);
}

.plan-chat-shell :deep(.plan-chat-panel > .flex-1.overflow-y-auto) {
  padding: 18px 24px;
  background: #fff;
}

.plan-chat-shell :deep(.plan-chat-panel > div:last-child) {
  border-top-color: rgba(188, 203, 232, 0.58);
  background: #fff;
  padding: 16px 24px;
}

.plan-chat-shell :deep(.plan-chat-panel .input-field) {
  height: 48px;
  border-radius: 9px;
  border-color: rgba(154, 176, 218, 0.78);
  color: #5a7099;
}

.plan-chat-shell :deep(.plan-chat-panel .btn-primary) {
  min-width: 88px;
  height: 48px;
  border-radius: 9px;
}

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

.pptx-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.pptx-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: #f8f7ff;
  border-bottom: 1px solid #ede9fe;
  flex-shrink: 0;
}

.pptx-slide-count {
  font-size: 13px;
  color: #7c3aed;
  font-weight: 600;
  background: rgba(124, 58, 237, 0.08);
  padding: 4px 12px;
  border-radius: 16px;
}

.pptx-download-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 18px;
  background: linear-gradient(135deg, #7c3aed, #6d28d9);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(124, 58, 237, 0.25);
}

.pptx-download-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(124, 58, 237, 0.35);
}

.pptx-stage {
  flex: 1;
  width: 100%;
  margin: 0;
  overflow: hidden;
  border: none;
  border-radius: 0;
}

.pptx-frame {
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

.fp-stop-button {
  position: fixed;
  bottom: 28px;
  left: 50%;
  z-index: 1200;
  transform: translateX(-50%);
  padding: 10px 20px;
  border: 1px solid rgba(248, 113, 113, 0.45);
  border-radius: 999px;
  background: rgba(254, 242, 242, 0.96);
  color: #dc2626;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 12px 36px rgba(26, 40, 71, 0.12);
  backdrop-filter: blur(12px);
  transition: background 0.18s ease, border-color 0.18s ease;
}

.fp-stop-button:hover {
  background: rgba(254, 226, 226, 0.98);
  border-color: rgba(248, 113, 113, 0.65);
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
