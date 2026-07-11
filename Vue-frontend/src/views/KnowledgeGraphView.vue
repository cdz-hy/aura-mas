<template>
  <div class="kg-root h-full flex flex-col relative overflow-hidden">
    <!-- Background texture -->
    <div class="kg-bg"></div>

    <!-- Header -->
    <div class="kg-header relative z-10 px-6 pt-5 pb-4 animate-fade-in-up">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="font-display text-2xl font-bold text-navy-800 tracking-tight">领域知识图谱</h2>
          <p class="text-sm text-navy-400 mt-1">可视化你的知识掌握网络</p>
        </div>
        <div class="flex items-center gap-2">
          <!-- Search Box -->
          <div ref="searchBoxRef" class="relative group">
            <div class="flex items-center bg-white rounded-xl border border-navy-100/60 px-3 py-1.5 focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-100 transition-all shadow-sm h-9">
              <svg class="w-4 h-4 text-navy-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              <input 
                v-model="searchQuery" 
                @focus="searchFocused = true"
                @blur="handleSearchBlur"
                type="text" 
                placeholder="搜索节点..." 
                class="bg-transparent border-none outline-none text-sm text-navy-700 w-32 placeholder:text-navy-300 ml-2 focus:ring-0 p-0"
              />
            </div>
            <!-- Search Results Dropdown -->
            <Teleport to="body">
              <transition name="fade-up">
                <div v-if="searchFocused && searchResults.length > 0" class="kg-search-dropdown" :style="searchDropdownStyle">
                  <div
                    v-for="res in searchResults"
                    :key="res.id"
                    @mousedown.prevent="handleSearchSelect(res)"
                    class="px-3 py-2 hover:bg-indigo-50/60 cursor-pointer transition-colors"
                  >
                    <div class="text-sm font-semibold text-navy-800 truncate" :title="res.name">
                      <span v-html="highlightText(res.name, searchQuery)"></span>
                    </div>
                    <div v-if="res.description" class="text-[10px] text-navy-400 truncate mt-0.5" :title="res.description">{{ res.description }}</div>
                  </div>
                </div>
              </transition>
            </Teleport>
          </div>

          <!-- Actions -->
          <button
            @click="optimizeModalVisible = true"
            v-if="selectedDomainId"
            class="kg-refresh-btn flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="m21.64 3.64-1.28-1.28a1.21 1.21 0 0 0-1.72 0L2.36 18.64a1.21 1.21 0 0 0 0 1.72l1.28 1.28a1.21 1.21 0 0 0 1.72 0L21.64 5.36a1.21 1.21 0 0 0 0-1.72Z"/>
              <path d="m14 7 3 3"/>
              <path d="M5 6v4"/>
              <path d="M19 14v4"/>
              <path d="M10 2v2"/>
              <path d="M7 8H3"/>
              <path d="M21 16h-4"/>
              <path d="M11 3H9"/>
            </svg>
            智能整理
          </button>
          <button
            @click="reanalyzeModalVisible = true"
            class="kg-refresh-btn flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300"
          >
            重新分析资源
          </button>
          <button
            @click="loadDomainGraph"
            class="kg-refresh-btn flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300"
            :class="loading ? 'opacity-60 pointer-events-none' : ''"
          >
            <svg class="w-4 h-4" :class="loading ? 'animate-spin' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" />
              <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
            </svg>
            刷新
          </button>
        </div>
      </div>

      <!-- Domain pill selector -->
      <div class="mt-4 flex flex-wrap gap-2" v-if="domains.length > 0">
        <button
          v-for="d in domains"
          :key="d.id"
          @click="selectDomain(d.id)"
          class="kg-pill transition-all duration-300 group flex items-center"
          :class="selectedDomainId === d.id ? 'kg-pill-active pr-2' : 'kg-pill-inactive'"
        >
          <span>{{ d.domainName }}</span>
          <span 
            v-if="selectedDomainId === d.id"
            @click.stop="handleDeleteDomain(d)"
            class="ml-1.5 p-1 rounded-full text-white/60 hover:text-white hover:bg-white/20 transition-all opacity-0 group-hover:opacity-100"
            title="删除此图谱"
          >
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </span>
        </button>
      </div>
    </div>

    <!-- Graph container -->
    <div class="flex-1 relative z-10 px-6 pb-6 animate-fade-in-up min-h-0" style="animation-delay: 0.1s">
      <!-- Empty state -->
      <div v-if="domains.length === 0 && !loading" class="kg-empty h-full flex flex-col items-center justify-center">
        <div class="kg-empty-icon mb-6">
          <svg class="w-20 h-20 text-navy-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <circle cx="12" cy="12" r="3" /><circle cx="5" cy="6" r="2" /><circle cx="19" cy="6" r="2" />
            <circle cx="5" cy="18" r="2" /><circle cx="19" cy="18" r="2" />
            <line x1="7" y1="7" x2="10" y2="10" /><line x1="17" y1="7" x2="14" y2="10" />
            <line x1="7" y1="17" x2="10" y2="14" /><line x1="17" y1="17" x2="14" y2="14" />
          </svg>
        </div>
        <h3 class="font-display text-xl text-navy-600 mb-2">暂无知识领域</h3>
        <p class="text-navy-400 text-sm">开始学习后，系统会自动构建你的知识图谱</p>
      </div>

      <!-- Chart -->
      <div v-else class="kg-chart-wrapper h-full rounded-2xl overflow-hidden relative">
        <v-chart
          ref="chartRef"
          class="w-full h-full min-h-[500px]"
          :option="chartOption"
          @click="handleNodeClick"
          @zr:mousedown="handleZrMouseDown"
          @zr:mousemove="handleZrMouseMove"
          @zr:mouseup="handleZrMouseUp"
          @zr:globalout="handleZrMouseUp"
          autoresize
        />

        <!-- Zoom controls -->
        <div class="kg-zoom-controls">
          <button @click="zoomIn" class="kg-zoom-btn" title="放大">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
          <button @click="zoomOut" class="kg-zoom-btn" title="缩小">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
          <button @click="resetZoom" class="kg-zoom-btn" title="复位">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
          </button>
        </div>

        <!-- Relationship type legend -->
        <div class="kg-rel-legend">
          <div class="kg-rel-legend-title">关系类型</div>
          <div v-for="(group, key) in relationColorGroups" :key="key" class="kg-rel-legend-item">
            <svg width="24" height="10" class="kg-rel-legend-line">
              <line 
                x1="0" y1="5" x2="24" y2="5" 
                :stroke="group.color" 
                :stroke-width="group.width"
                :stroke-dasharray="group.lineType === 'solid' ? '' : (group.dashPattern || [4,4]).join(',')"
                stroke-linecap="round"
              />
            </svg>
            <span class="kg-rel-legend-label">{{ group.label }}</span>
          </div>
        </div>

        <!-- Mastery legend -->
        <div class="kg-legend">
          <span class="text-xs text-navy-500 font-medium">掌握度:</span>
          <div class="flex items-center gap-1">
            <span class="w-3 h-3 rounded-full" style="background: #1a2847"></span>
            <span class="text-xs text-navy-400">低</span>
          </div>
          <div class="kg-legend-bar"></div>
          <div class="flex items-center gap-1">
            <span class="w-3 h-3 rounded-full" style="background: #649b64"></span>
            <span class="text-xs text-navy-400">高</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Drawer overlay -->
    <transition name="kg-overlay">
      <div v-if="drawerVisible" class="kg-drawer-overlay" @click="drawerVisible = false"></div>
    </transition>

    <!-- Side drawer -->
    <transition name="kg-drawer">
      <div v-if="drawerVisible && selectedNode" class="kg-drawer">
        <!-- Drawer header -->
        <div class="kg-drawer-header">
          <div class="flex items-center gap-3">
            <div class="kg-drawer-icon">
              <svg class="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="18" cy="5" r="3" />
                <circle cx="6" cy="12" r="3" />
                <circle cx="18" cy="19" r="3" />
                <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
                <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
              </svg>
            </div>
            <div>
              <h3 class="font-display text-lg font-bold text-navy-800">节点详情</h3>
              <p class="text-xs text-navy-400">查看与编辑知识节点</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button 
              @click="handleDeleteNode" 
              class="kg-drawer-close text-red-500 hover:bg-red-50 hover:text-red-600 !w-auto !px-2 flex items-center gap-1.5 transition-colors"
              :disabled="isDeleting"
            >
              <svg v-if="isDeleting" class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" class="opacity-25" /><path d="M4 12a8 8 0 018-8" class="opacity-75" stroke-linecap="round" /></svg>
              <svg v-else class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
              <span class="text-[11px] font-bold">删除</span>
            </button>
            <button @click="drawerVisible = false" class="kg-drawer-close">
              <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Drawer body -->
        <div class="kg-drawer-body">
          <!-- Node name & description -->
          <div class="kg-node-info">
            <h4 class="font-display text-xl font-bold text-navy-800 mb-2">{{ selectedNode.name }}</h4>
            <p class="text-sm text-navy-500 leading-relaxed">{{ selectedNode.description || '暂无描述' }}</p>
          </div>

          <!-- Mastery progress -->
          <div class="kg-stat-card group">
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm font-semibold text-navy-700">掌握度</span>
              <span class="text-sm font-bold transition-colors duration-300" :style="{ color: masteryColor }">
                {{ Math.round((selectedNode.mastery_level || 0) * 100) }}%
              </span>
            </div>
            
            <div class="relative h-2.5 mt-3 mb-1">
              <!-- Background Track -->
              <div class="absolute inset-0 bg-navy-900/5 rounded-full overflow-hidden shadow-inner border border-navy-900/5">
                <!-- Fill -->
                <div class="h-full rounded-full transition-all duration-150 ease-out" 
                     :style="{ width: (selectedNode.mastery_level || 0) * 100 + '%', background: masteryGradient }">
                </div>
              </div>
              <!-- Custom Thumb -->
              <div class="absolute top-1/2 w-4 h-4 -mt-2 -ml-2 bg-white rounded-full shadow-[0_2px_8px_rgba(26,40,71,0.2)] pointer-events-none transition-all duration-150 ease-out flex items-center justify-center group-hover:scale-125 border border-navy-50"
                   :style="{ left: (selectedNode.mastery_level || 0) * 100 + '%' }">
                <div class="w-1.5 h-1.5 rounded-full" :style="{ background: masteryColor }"></div>
              </div>
              <!-- Invisible Input -->
              <input
                type="range" min="0" max="1" step="0.1"
                v-model.number="selectedNode.mastery_level"
                class="absolute inset-0 w-full h-full opacity-0 cursor-pointer m-0 z-10"
                @change="saveNodePatch"
              />
            </div>
            <p class="text-[10px] text-navy-400 mt-2">滑动调整对该知识点的掌握程度</p>
          </div>

          <!-- Importance progress -->
          <div class="kg-stat-card group">
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm font-semibold text-navy-700">重要性</span>
              <span class="text-sm font-bold text-accent transition-colors duration-300">
                {{ Math.round((selectedNode.importance || 0) * 100) }}%
              </span>
            </div>
            
            <div class="relative h-2.5 mt-3 mb-1">
              <!-- Background Track -->
              <div class="absolute inset-0 bg-navy-900/5 rounded-full overflow-hidden shadow-inner border border-navy-900/5">
                <!-- Fill -->
                <div class="h-full rounded-full transition-all duration-150 ease-out" 
                     :style="{ width: (selectedNode.importance || 0) * 100 + '%', background: accentGradient }">
                </div>
              </div>
              <!-- Custom Thumb -->
              <div class="absolute top-1/2 w-4 h-4 -mt-2 -ml-2 bg-white rounded-full shadow-[0_2px_8px_rgba(26,40,71,0.2)] pointer-events-none transition-all duration-150 ease-out flex items-center justify-center group-hover:scale-125 border border-navy-50"
                   :style="{ left: (selectedNode.importance || 0) * 100 + '%' }">
                <div class="w-1.5 h-1.5 rounded-full bg-accent"></div>
              </div>
              <!-- Invisible Input -->
              <input
                type="range" min="0" max="1" step="0.1"
                v-model.number="selectedNode.importance"
                class="absolute inset-0 w-full h-full opacity-0 cursor-pointer m-0 z-10"
                @change="saveNodePatch"
              />
            </div>
            <p class="text-[10px] text-navy-400 mt-2">评估该知识点对你当前阶段的重要程度</p>
          </div>

          <!-- Connected relations -->
          <div class="mt-5" v-if="selectedNodeRelations.length > 0">
            <h5 class="text-sm font-bold text-navy-700 mb-3 flex items-center gap-2">
              <svg class="w-4 h-4 text-navy-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" /><polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" />
              </svg>
              关联关系 ({{ selectedNodeRelations.length }})
            </h5>
            <div class="space-y-1.5">
              <div
                v-for="rel in selectedNodeRelations"
                :key="rel.id"
                class="kg-relation-item group"
              >
                <div class="flex items-center gap-2 w-full">
                  <!-- From Node -->
                  <div class="flex-1 flex justify-end min-w-0">
                    <span 
                      class="text-xs line-clamp-1 group-hover:line-clamp-none transition-all duration-300 break-words text-right"
                      :class="rel.fromName === selectedNode?.name ? 'font-bold text-blue-600 bg-blue-50/80 px-1.5 py-0.5 rounded' : 'font-semibold text-navy-700'"
                    >
                      {{ rel.fromName }}
                    </span>
                  </div>
                  
                  <!-- Relation Badge with Dashed Line -->
                  <div class="flex-shrink-0 flex items-center justify-center relative px-3 min-w-[80px]">
                    <svg class="absolute inset-x-0 top-1/2 -translate-y-1/2 w-full h-2 z-0" preserveAspectRatio="none">
                      <line 
                        x1="0" y1="4" x2="100%" y2="4" 
                        :stroke="rel.color" 
                        stroke-width="1.5"
                        :stroke-dasharray="rel.lineType === 'solid' ? '' : (rel.dashPattern || [4,4]).join(',')"
                        stroke-linecap="round"
                        opacity="0.5"
                      />
                    </svg>
                    <span class="text-[10px] px-2 py-0.5 rounded-full border bg-white shadow-[0_2px_4px_rgba(26,40,71,0.04)] font-bold z-10 whitespace-nowrap"
                          :style="{ color: rel.color, borderColor: rel.color + '50' }">
                      {{ rel.label }}
                    </span>
                  </div>

                  <!-- To Node -->
                  <div class="flex-1 flex justify-start min-w-0">
                    <span 
                      class="text-xs line-clamp-1 group-hover:line-clamp-none transition-all duration-300 break-words text-left"
                      :class="rel.toName === selectedNode?.name ? 'font-bold text-blue-600 bg-blue-50/80 px-1.5 py-0.5 rounded' : 'font-semibold text-navy-700'"
                    >
                      {{ rel.toName }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Related resources -->
          <div class="mt-5">
            <h5 class="text-sm font-bold text-navy-700 mb-3 flex items-center gap-2">
              <svg class="w-4 h-4 text-navy-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z" />
              </svg>
              关联学习资源
            </h5>
            <div v-if="selectedNode.resource_ids?.length" class="space-y-2">
              <div
                v-for="rid in selectedNode.resource_ids"
                :key="rid"
                class="kg-resource-card flex items-center gap-3 px-3 py-2.5 transition-all duration-200"
                @click="openResource(rid)"
              >
                <!-- Resource Type Badge -->
                <div 
                  class="flex-shrink-0 text-[10px] font-bold px-2 py-0.5 rounded-md"
                  :class="typeBadgeClass(resourceCache[rid]?.type)"
                >
                  {{ typeLabels[resourceCache[rid]?.type] || resourceCache[rid]?.type || '加载中' }}
                </div>
                <!-- Title -->
                <span class="text-sm text-navy-700 font-medium truncate flex-1" :title="resourceCache[rid]?.title">
                  {{ resourceCache[rid]?.title || `学习资源 #${rid}` }}
                </span>
                <!-- Arrow -->
                <svg class="w-4 h-4 text-navy-300 ml-auto flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </div>
            </div>
            <div v-else class="text-sm text-navy-300 italic py-3">暂无关联资源</div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 资源预览抽屉 -->
    <TransitionGroup name="drawer-list">
      <ResourcePreviewDrawer 
        v-for="(rid, index) in activePreviews"
        :key="rid"
        :resource-id="rid" 
        :index="index"
        :base-offset="drawerVisible ? 380 : 0"
        @close="closePreview(rid)"
      />
    </TransitionGroup>

    <!-- 重新分析模态框 -->
    <ResourceReanalyzeModal 
      v-model:visible="reanalyzeModalVisible" 
      @success="handleReanalyzeSuccess" 
    />

    <!-- 图谱智能整理模态框 -->
    <GraphOptimizeModal
      v-model:visible="optimizeModalVisible"
      :domainId="selectedDomainId"
      @submit="handleOptimizeSubmit"
    />

    <!-- 删除确认弹窗 -->
    <ConfirmDialog
      :visible="deleteConfirmVisible"
      type="danger"
      title="删除知识节点"
      :message="`确定要彻底删除节点 [${selectedNode?.name}] 吗？与此节点相关的所有连线也将被一并删除！该操作不可撤销。`"
      confirmText="确定删除"
      @confirm="executeDeleteNode"
      @cancel="deleteConfirmVisible = false"
    />

    <!-- 全领域删除确认弹窗 -->
    <ConfirmDialog
      :visible="domainDeleteConfirmVisible"
      type="danger"
      title="彻底删除知识领域"
      :message="`确定要彻底删除整个领域 [${domainToDelete?.domainName}] 及其所有图谱节点和关系吗？该操作不可撤销。`"
      confirmText="确定删除"
      @confirm="executeDeleteDomain"
      @cancel="domainDeleteConfirmVisible = false"
    />

    <!-- Global Task Indicator -->
    <transition-group name="kg-toast" tag="div" class="fixed bottom-6 right-6 z-[120] flex flex-col gap-3 pointer-events-none">
      <div 
        v-for="task in globalTasks" 
        :key="task.id"
        class="kg-toast-card pointer-events-auto"
        :class="{ 'kg-toast-done': task.status === 'done', 'kg-toast-error': task.status === 'error' }"
      >
        <!-- Animated icon area -->
        <div class="relative w-10 h-10 flex-shrink-0">
          <template v-if="task.status === 'processing'">
            <div class="kg-toast-orbit">
              <div class="kg-toast-orbit-dot"></div>
            </div>
            <div class="kg-toast-orbit-inner"></div>
            <div class="absolute inset-0 flex items-center justify-center">
              <svg class="w-[18px] h-[18px] kg-toast-icon-pulse" viewBox="0 0 24 24" fill="none" stroke="#4164b2" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="m21.64 3.64-1.28-1.28a1.21 1.21 0 0 0-1.72 0L2.36 18.64a1.21 1.21 0 0 0 0 1.72l1.28 1.28a1.21 1.21 0 0 0 1.72 0L21.64 5.36a1.21 1.21 0 0 0 0-1.72Z"/>
                <path d="m14 7 3 3"/>
              </svg>
            </div>
          </template>
          <div v-else-if="task.status === 'done'" class="kg-toast-status-icon" style="background: rgba(100,155,100,0.12); border-color: rgba(100,155,100,0.25);">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="#649b64" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
          <div v-else class="kg-toast-status-icon" style="background: rgba(201,100,80,0.1); border-color: rgba(201,100,80,0.2);">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="#c9644f" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </div>
        </div>
        <!-- Text -->
        <div class="flex-1 min-w-0">
          <div class="text-[13px] font-semibold" style="color: #1a2847;">{{ task.title }}</div>
          <div class="text-[11px] mt-0.5 leading-snug"
            :class="{ 'kg-toast-msg-processing': task.status === 'processing', 'kg-toast-msg-done': task.status === 'done', 'kg-toast-msg-error': task.status === 'error' }">
            {{ task.message }}
          </div>
        </div>
        <!-- Close -->
        <button @click="removeGlobalTask(task.id)" class="kg-toast-close" title="关闭">
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    </transition-group>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { PYTHON_AI_BASE } from '@/api/request'
import { useAuthStore } from '@/stores/auth'
import { getKnowledgeDomains, getDomainGraph, patchKnowledgeNode, updateDomainGraph, deleteKnowledgeNode, deleteKnowledgeDomain } from '@/api/knowledgeGraph'
import { getResource } from '@/api/resource'
import type { UserKnowledgeDomain, KnowledgeGraphNode } from '@/api/knowledgeGraph'
import ResourceReanalyzeModal from './ResourceReanalyzeModal.vue'
import ResourcePreviewDrawer from '@/components/resource/ResourcePreviewDrawer.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import GraphOptimizeModal from '@/components/knowledge/GraphOptimizeModal.vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { GraphChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([CanvasRenderer, GraphChart, TooltipComponent])

// ─── Relationship Chinese mapping ───
const RELATION_CN: Record<string, string> = {
  is_a: '属于', part_of: '包含', uses: '使用', related_to: '相关',
  has_pattern: '模式', has_principle: '原则', has_component: '组件',
  prerequisite_for: '前置', has_layer: '层级', enables: '支撑',
  implements: '实现', implemented_by: '实现于', supersedes: '取代',
  manages: '管理', monitors: '监控', contains: '包含', defines: '定义',
  has_subsystem: '子系统', has_pillar: '支柱', supports: '支持',
  modeled_by: '建模于', designed: '设计', has_project: '项目',
  platform_for: '平台', has_activity: '活动', documented_on: '记录于',
  drives: '驱动', center_of: '核心', appears_in: '出现于',
  executes_in: '执行于', provides: '提供', includes: '包括',
  
  // 额外补充常见的 LLM 自由发挥词汇
  used_in: '应用于', used_by: '使用于', depends_on: '依赖于',
  based_on: '基于', applied_in: '应用于', requires: '需要',
  extends: '扩展/继承', improves: '改进', optimizes: '优化',
  belongs_to: '属于', features: '特性', examples: '示例',
  integrated_with: '集成于', runs_on: '运行于', managed_by: '受管于',
  configured_by: '配置于', deployed_on: '部署于', tests: '测试',
  analyzes: '分析', generates: '生成', process: '处理',
  alternative_to: '替代方案', similar_to: '类似于', composed_of: '组成',
}

function getRelationCN(rel: string): string {
  if (!rel) return ''
  // 统一下划线和空格的格式，忽略大小写
  const normalized = rel.trim().toLowerCase().replace(/ /g, '_')
  return RELATION_CN[normalized] || RELATION_CN[rel] || rel.replace(/_/g, ' ')
}

// ─── Relationship visual config ───
interface RelationGroupConfig {
  label: string
  color: string
  rels: string[]
  lineType: 'solid' | 'dashed' | 'dotted'
  width: number
  curveness: number
  opacity: number
  dashPattern?: number[]
}

const relationColorGroups: Record<string, RelationGroupConfig> = {
  structure: {
    label: '层级结构',
    color: '#4a90d9',
    rels: ['part_of', 'has_component', 'has_layer', 'has_subsystem', 'has_pillar', 'includes', '包含', '组成', '层级', '子系统', '包括'],
    lineType: 'solid',
    width: 2.5,
    curveness: 0.15,
    opacity: 0.6,
  },
  dependency: {
    label: '依赖使用',
    color: '#50b86c',
    rels: ['uses', 'enables', 'supports', 'implemented_by', 'implements', 'provides', '使用', '支撑', '支持', '实现于', '实现', '提供', '依赖于', '需要', '应用于', '运行于', '使用于'],
    lineType: 'dashed',
    width: 2,
    curveness: 0.25,
    opacity: 0.55,
    dashPattern: [8, 4],
  },
  semantic: {
    label: '语义关联',
    color: '#e8914a',
    rels: ['related_to', 'is_a', 'modeled_by', 'appears_in', '相关', '属于', '建模于', '出现于', '类似于', '关联'],
    lineType: 'dotted',
    width: 1.8,
    curveness: 0.35,
    opacity: 0.5,
    dashPattern: [3, 3],
  },
  design: {
    label: '设计原则',
    color: '#9b6dd7',
    rels: ['has_principle', 'has_pattern', 'defines', 'has_project', '原则', '模式', '定义', '项目', '特性', '示例'],
    lineType: 'solid',
    width: 2.2,
    curveness: 0.2,
    opacity: 0.55,
  },
  control: {
    label: '约束管控',
    color: '#e05c6c',
    rels: ['monitors', 'contains', 'manages', 'executes_in', '监控', '管理', '执行于', '测试', '处理', '分析', '生成'],
    lineType: 'dashed',
    width: 2,
    curveness: 0.3,
    opacity: 0.5,
    dashPattern: [6, 3],
  },
  evolution: {
    label: '演化替代',
    color: '#d4a944',
    rels: ['supersedes', 'prerequisite_for', 'designed', 'platform_for', 'has_activity', 'documented_on', 'drives', 'center_of', '取代', '前置', '设计', '平台', '活动', '记录于', '驱动', '核心', '替代方案', '改进', '优化', '扩展/继承'],
    lineType: 'dotted',
    width: 1.5,
    curveness: 0.4,
    opacity: 0.45,
    dashPattern: [4, 4],
  },
}

function getRelationConfig(rel: string): RelationGroupConfig {
  for (const group of Object.values(relationColorGroups)) {
    if (group.rels.includes(rel)) return group
  }
  // fallback config
  return {
    label: '其他',
    color: '#8899bb',
    rels: [],
    lineType: 'solid',
    width: 1.5,
    curveness: 0.2,
    opacity: 0.4,
  }
}

function getRelationColor(rel: string): string {
  return getRelationConfig(rel).color
}

function getGroupKey(rel: string): string {
  for (const [key, group] of Object.entries(relationColorGroups)) {
    if (group.rels.includes(rel)) return key
  }
  return 'other'
}

// ─── State ───
const authStore = useAuthStore()
const domains = ref<UserKnowledgeDomain[]>([])
const selectedDomainId = ref<number | null>(null)
const currentGraphData = ref<any>(null)
const loading = ref(false)
const reanalyzeModalVisible = ref(false)
const optimizeModalVisible = ref(false)
const chartRef = ref<InstanceType<typeof VChart> | null>(null)

// ─── Search State & Logic ───
const searchQuery = ref('')
const searchFocused = ref(false)
const searchBoxRef = ref<HTMLElement | null>(null)
const searchResults = computed(() => {
  if (!searchQuery.value.trim() || !currentGraphData.value?.nodes) return []
  const q = searchQuery.value.toLowerCase()
  return currentGraphData.value.nodes.filter((n: any) => n.name.toLowerCase().includes(q)).slice(0, 8)
})

const searchDropdownStyle = computed(() => {
  const el = searchBoxRef.value
  if (!el) return {}
  const rect = el.getBoundingClientRect()
  return {
    position: 'fixed' as const,
    top: rect.bottom + 8 + 'px',
    left: rect.left + 'px',
    width: Math.max(rect.width, 200) + 'px',
    zIndex: 9999,
  }
})

const highlightText = (text: string, query: string) => {
  if (!query.trim()) return text
  const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
  return text.replace(regex, '<span class="text-indigo-600 bg-indigo-50">$1</span>')
}

const handleSearchBlur = () => {
  setTimeout(() => { searchFocused.value = false }, 200)
}

const handleSearchSelect = (node: KnowledgeGraphNode) => {
  searchQuery.value = ''
  searchFocused.value = false
  // 模拟点击打开侧边栏
  handleNodeClick({ dataType: 'node', data: node })
  // ECharts 高亮
  const chart = chartRef.value?.chart
  if (chart) {
    chart.dispatchAction({ type: 'downplay' })
    chart.dispatchAction({ type: 'highlight', seriesIndex: 0, name: node.name })
  }
}

// ─── Delete Node Logic ───
const isDeleting = ref(false)
const deleteConfirmVisible = ref(false)

const handleDeleteNode = () => {
  if (!selectedNode.value || !currentGraphData.value || !selectedDomainId.value) return
  deleteConfirmVisible.value = true
}

const executeDeleteNode = async () => {
  deleteConfirmVisible.value = false
  isDeleting.value = true
  try {
    const nodeId = selectedNode.value!.id
    const domainId = selectedDomainId.value!
    
    // 调用后端的单节点专属删除 API
    await deleteKnowledgeNode(domainId, nodeId)
    
    // 从本地直接同步清洗，避免再次走网络获取几兆的全量 JSON
    const newNodes = currentGraphData.value.nodes.filter((n: any) => String(n.id) !== String(nodeId))
    const newEdges = currentGraphData.value.edges.filter((e: any) => String(e.source) !== String(nodeId) && String(e.target) !== String(nodeId))
    currentGraphData.value = { nodes: newNodes, edges: newEdges }
    
    selectedNode.value = null
    drawerVisible.value = false
  } catch (error) {
    console.error('Failed to delete node', error)
    alert('删除节点失败，请稍后重试')
  } finally {
    isDeleting.value = false
  }
}

// ─── Delete Domain Logic ───
const domainDeleteConfirmVisible = ref(false)
const domainToDelete = ref<UserKnowledgeDomain | null>(null)

const handleDeleteDomain = (domain: UserKnowledgeDomain) => {
  domainToDelete.value = domain
  domainDeleteConfirmVisible.value = true
}

const executeDeleteDomain = async () => {
  domainDeleteConfirmVisible.value = false
  if (!domainToDelete.value) return
  
  loading.value = true
  try {
    await deleteKnowledgeDomain(domainToDelete.value.id)
    await loadDomains() // 重新拉取图谱列表
  } catch (error) {
    console.error('Failed to delete domain', error)
    alert('删除图谱失败，请稍后重试')
    loading.value = false
  } finally {
    domainToDelete.value = null
  }
}

// ─── Background Tasks Logic ───
interface GlobalTask {
  id: string
  title: string
  message: string
  status: 'processing' | 'done' | 'error'
}
const globalTasks = ref<GlobalTask[]>([])

const removeGlobalTask = (id: string) => {
  globalTasks.value = globalTasks.value.filter(t => t.id !== id)
}

const handleReanalyzeSuccess = () => {
  const taskId = 'reanalyze_' + Date.now()
  globalTasks.value.push({
    id: taskId,
    title: '重新分析资源',
    message: '任务已提交至后台，系统将逐步解析新知识...',
    status: 'processing'
  })
  setTimeout(() => {
    const t = globalTasks.value.find(x => x.id === taskId)
    if (t) {
      t.status = 'done'
      t.message = '后台分析已启动，请稍后手动刷新图谱查看'
      setTimeout(() => {
        globalTasks.value = globalTasks.value.filter(x => x.id !== taskId)
      }, 5000)
    }
  }, 3000)
  loadDomainGraph()
}

const handleOptimizeSubmit = async (instruction: string) => {
  const domainId = selectedDomainId.value
  if (!domainId) return
  
  const taskId = 'optimize_' + Date.now()
  const task: GlobalTask = {
    id: taskId,
    title: '图谱智能整理',
    message: '正在连接知识图谱架构师...',
    status: 'processing'
  }
  globalTasks.value.push(task)

  try {
    const response = await fetch(`${PYTHON_AI_BASE}/api/ai/knowledge-graph/optimize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ domain_id: domainId, instruction })
    })

    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    if (!response.body) throw new Error('Response body is null')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    const processBuffer = (isDone: boolean) => {
      const messages = buffer.split('\n\n')
      if (!isDone) {
        buffer = messages.pop() || ''
      } else {
        buffer = ''
      }
      for (const message of messages) {
        if (!message.trim()) continue
        const lines = message.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const dataStr = line.substring(6)
              if (!dataStr.trim()) continue
              const data = JSON.parse(dataStr)
              
              if (data.type === 'progress') {
                task.message = data.message
              } else if (data.type === 'error') {
                task.status = 'error'
                task.message = `整理失败: ${data.message}`
                setTimeout(() => { globalTasks.value = globalTasks.value.filter(t => t.id !== taskId) }, 5000)
              } else if (data.type === 'done') {
                task.status = 'done'
                task.message = '整理完成！图谱已重构。'
                currentGraphData.value = data.graphData
                setTimeout(() => { globalTasks.value = globalTasks.value.filter(t => t.id !== taskId) }, 5000)
              }
            } catch (e) {
              console.error('Failed to parse SSE data', e, line.substring(0, 100) + '...')
            }
          }
        }
      }
    }

    while (true) {
      const { value, done } = await reader.read()
      if (value) {
        buffer += decoder.decode(value, { stream: !done })
      }
      processBuffer(done)
      if (done) break
    }
  } catch (err) {
    console.error('Optimization error:', err)
    task.status = 'error'
    task.message = '请求整理失败，请检查网络或后端服务。'
    setTimeout(() => { globalTasks.value = globalTasks.value.filter(t => t.id !== taskId) }, 5000)
  }
}

const windowWidth = ref(window.innerWidth)
const onResize = () => { windowWidth.value = window.innerWidth }
onMounted(() => window.addEventListener('resize', onResize))
onUnmounted(() => window.removeEventListener('resize', onResize))

const drawerVisible = ref(false)

const maxPreviews = computed(() => {
  const baseOffset = drawerVisible.value ? 380 : 0
  // baseOffset is main drawer, 420 is each preview drawer. Leave 100px padding.
  const available = windowWidth.value - baseOffset - 100
  return Math.max(1, Math.floor(available / 420))
})

const activePreviews = ref<number[]>([])

watch(maxPreviews, (newMax) => {
  if (activePreviews.value.length > newMax) {
    activePreviews.value = activePreviews.value.slice(0, newMax)
  }
})

const selectedNode = ref<KnowledgeGraphNode | null>(null)

const masteryGradient = 'linear-gradient(90deg, #1a2847, #4164b2, #649b64)'
const accentGradient = 'linear-gradient(90deg, #c9873b, #e8b06a)'
const masteryColor = computed(() => {
  const m = selectedNode.value?.mastery_level || 0
  if (m < 0.3) return '#1a2847'
  if (m < 0.6) return '#4164b2'
  return '#649b64'
})

// ─── Selected node's connected relations ───
const selectedNodeRelations = computed(() => {
  if (!selectedNode.value || !currentGraphData.value) return []
  const nodeId = String(selectedNode.value.id)
  const edges = currentGraphData.value.edges || []
  const nodesMap: Record<string, string> = {}
  for (const n of (currentGraphData.value.nodes || [])) {
    nodesMap[String(n.id)] = n.name
  }
  return edges
    .filter((e: any) => String(e.source) === nodeId || String(e.target) === nodeId)
    .slice(0, 15) // limit to 15 for drawer readability
    .map((e: any) => {
      const rel = e.relationship || ''
      const config = getRelationConfig(rel)
      return {
        id: e.id,
        fromName: nodesMap[String(e.source)] || e.source,
        toName: nodesMap[String(e.target)] || e.target,
        label: getRelationCN(rel),
        color: config.color,
        lineType: config.lineType,
        dashPattern: config.dashPattern,
      }
    })
})

// ─── Data loading ───
const loadDomains = async () => {
  if (!authStore.user?.id) return
  loading.value = true
  try {
    const res = await getKnowledgeDomains(authStore.user.id)
    if (res.data?.length) {
      domains.value = res.data
      selectedDomainId.value = res.data[0].id
      await loadDomainGraph()
    }
  } catch (e) {
    console.error('Failed to load domains', e)
  } finally {
    loading.value = false
  }
}

const loadDomainGraph = async () => {
  if (!selectedDomainId.value) return
  loading.value = true
  try {
    const res = await getDomainGraph(selectedDomainId.value)
    let gData = res.data?.graphData
    if (typeof gData === 'string') {
      try {
        gData = JSON.parse(gData)
      } catch (e) {
        console.error('Failed to parse graphData string', e)
      }
    }
    currentGraphData.value = gData || { nodes: [], edges: [] }
  } catch (e) {
    console.error('Failed to load graph', e)
  } finally {
    loading.value = false
  }
}

const selectDomain = (id: number) => {
  selectedDomainId.value = id
  loadDomainGraph()
}

// ─── Node click handler ───
const handleNodeClick = (params: any) => {
  if (params.dataType === 'node' && currentGraphData.value) {
    const nodeData = currentGraphData.value.nodes.find((n: any) => String(n.id) === String(params.data.id))
    if (nodeData) {
      selectedNode.value = { ...nodeData }
      if (selectedNode.value!.mastery_level === undefined) selectedNode.value!.mastery_level = 0
      if (selectedNode.value!.importance === undefined) selectedNode.value!.importance = 0.5
      drawerVisible.value = true
    }
  }
}

// ─── Custom Background Panning (solves empty space drag issue) ───
let isDraggingBg = false
let lastPoint = { x: 0, y: 0 }

const handleZrMouseDown = (e: any) => {
  if (e.target) return
  isDraggingBg = true
  lastPoint = { x: e.offsetX, y: e.offsetY }
  drawerVisible.value = false
  activePreviews.value = []
}

const handleZrMouseMove = (params: any) => {
  if (isDraggingBg) {
    const dx = params.offsetX - lastPoint.x
    const dy = params.offsetY - lastPoint.y
    lastPoint = { x: params.offsetX, y: params.offsetY }
    const chart = chartRef.value?.chart
    if (chart) {
      chart.dispatchAction({
        type: 'graphRoam',
        seriesIndex: 0,
        dx,
        dy
      })
    }
  }
}

const handleZrMouseUp = () => {
  isDraggingBg = false
}

// ─── Resource Data Fetching ───
const resourceCache = ref<Record<number, { title: string, type: string }>>({})

const typeLabels: Record<string, string> = {
  text: '正文', image: '图片', diagram: '导图', code: '代码', quiz: '题目', summary: '总结',
  document: '文档', mindmap: '导图', reading: '阅读', video: '视频', podcast: '播客', animation: '动画',
}

function typeBadgeClass(type?: string): string {
  if (!type) return 'bg-navy-100 text-navy-500'
  const map: Record<string, string> = {
    text: 'bg-blue-100 text-blue-700', document: 'bg-blue-100 text-blue-700', mindmap: 'bg-purple-100 text-purple-700',
    quiz: 'bg-amber-100 text-amber-700', code: 'bg-green-100 text-green-700', reading: 'bg-rose-100 text-rose-700',
    video: 'bg-red-100 text-red-700', summary: 'bg-sky-100 text-sky-700', podcast: 'bg-emerald-100 text-emerald-700',
    animation: 'bg-orange-100 text-orange-700', image: 'bg-pink-100 text-pink-700', diagram: 'bg-indigo-100 text-indigo-700',
  }
  return map[type] || 'bg-navy-100 text-navy-500'
}

const fetchResourceInfo = async (rid: number) => {
  if (resourceCache.value[rid]) return
  try {
    const res = await getResource(rid)
    if (res.data) {
      const data = res.data
      let title = `学习资源 #${rid}`
      if (data.moduleData?.title) title = data.moduleData.title
      else if (data.moduleData?.name) title = data.moduleData.name
      else if (typeof data.moduleData === 'string') {
        try {
          const parsed = JSON.parse(data.moduleData)
          if (parsed.title) title = parsed.title
          else if (parsed.name) title = parsed.name
        } catch {}
      } else if ((data as any).title) {
        title = (data as any).title
      }
      resourceCache.value[rid] = { title, type: data.moduleType || 'text' }
    }
  } catch {
    resourceCache.value[rid] = { title: `学习资源 #${rid}`, type: 'text' }
  }
}

watch(selectedNode, (newVal) => {
  if (newVal?.resource_ids) {
    newVal.resource_ids.forEach(rid => {
      fetchResourceInfo(rid)
    })
  }
})

const openResource = (rid: number) => {
  if (!activePreviews.value.includes(rid)) {
    // 每次新开插入到最前面（离主抽屉最近的位置）
    activePreviews.value.unshift(rid)
    // 超过当前屏幕容量则剔除最早打开的
    if (activePreviews.value.length > maxPreviews.value) {
      activePreviews.value.pop()
    }
  } else {
    // 如果已经打开，将其移到最前面
    activePreviews.value = activePreviews.value.filter(id => id !== rid)
    activePreviews.value.unshift(rid)
  }
}

const closePreview = (rid: number) => {
  activePreviews.value = activePreviews.value.filter(id => id !== rid)
}

// ─── Save node patch ───
const saveNodePatch = async () => {
  if (!selectedDomainId.value || !selectedNode.value) return
  try {
    await patchKnowledgeNode(
      selectedDomainId.value,
      selectedNode.value.id,
      selectedNode.value.mastery_level,
      selectedNode.value.importance
    )
    const target = currentGraphData.value.nodes.find((n: any) => n.id === selectedNode.value!.id)
    if (target) {
      target.mastery_level = selectedNode.value.mastery_level
      target.importance = selectedNode.value.importance
      currentGraphData.value = { ...currentGraphData.value }
    }
  } catch (e) {
    console.error('Failed to patch node', e)
  }
}

// ─── Zoom controls ───
const zoomIn = () => {
  const chart = chartRef.value
  if (!chart) return
  const inst = chart.chart
  if (!inst) return
  const option = inst.getOption() as any
  const zoom = (option?.series?.[0]?.zoom || 1) * 1.3
  inst.setOption({ series: [{ zoom }] })
}

const zoomOut = () => {
  const chart = chartRef.value
  if (!chart) return
  const inst = chart.chart
  if (!inst) return
  const option = inst.getOption() as any
  const zoom = (option?.series?.[0]?.zoom || 1) / 1.3
  inst.setOption({ series: [{ zoom }] })
}

const resetZoom = () => {
  const chart = chartRef.value
  if (!chart) return
  const inst = chart.chart
  if (!inst) return
  inst.setOption({ series: [{ zoom: 1, center: undefined }] })
}

// ─── Color interpolation: navy -> sage based on mastery ───
function masteryToColor(mastery: number): string {
  const colors = [
    { r: 26, g: 40, b: 71 },    // #1a2847 navy
    { r: 65, g: 100, b: 178 },   // #4164b2 navy-light
    { r: 100, g: 155, b: 100 },  // #649b64 sage
  ]
  const t = Math.max(0, Math.min(1, mastery))
  const idx = t * (colors.length - 1)
  const i = Math.floor(idx)
  const f = idx - i
  const c0 = colors[Math.min(i, colors.length - 1)]
  const c1 = colors[Math.min(i + 1, colors.length - 1)]
  const r = Math.round(c0.r + (c1.r - c0.r) * f)
  const g = Math.round(c0.g + (c1.g - c0.g) * f)
  const b = Math.round(c0.b + (c1.b - c0.b) * f)
  return `rgb(${r},${g},${b})`
}

// ─── Chart option ───
const chartOption = computed(() => {
  if (!currentGraphData.value) return {}

  const rawNodes = currentGraphData.value.nodes || []
  const rawEdges = currentGraphData.value.edges || []

  const nodes = rawNodes.map((n: any) => {
    const mastery = n.mastery_level || 0
    const importance = n.importance || 0.5
    const color = masteryToColor(mastery)
    // 3-tier sizing based on importance
    let size: number
    if (importance >= 0.8) size = 48
    else if (importance >= 0.5) size = 34
    else size = 22

    return {
      ...n,
      id: String(n.id),
      name: n.name,
      symbolSize: size,
      itemStyle: {
        color: {
          type: 'radial', x: 0.4, y: 0.35, r: 0.6,
          colorStops: [
            { offset: 0, color: lightenColor(color, 40) },
            { offset: 0.7, color },
            { offset: 1, color: darkenColor(color, 20) },
          ],
        },
        borderColor: 'rgba(255,255,255,0.7)',
        borderWidth: importance >= 0.8 ? 3 : 2,
        shadowBlur: importance >= 0.8 ? 20 : (importance >= 0.5 ? 10 : 4),
        shadowColor: color.replace('rgb', 'rgba').replace(')', ',0.35)'),
      },
      label: {
        show: true,
        position: 'bottom',
        distance: 6,
        formatter: '{b}',
        fontSize: importance >= 0.8 ? 13 : (importance >= 0.5 ? 11 : 10),
        color: '#2c3e5f',
        fontWeight: importance >= 0.8 ? 700 : 500,
        textShadowColor: 'rgba(253,249,240,0.9)',
        textShadowBlur: 3,
      },
    }
  })

  const edges = rawEdges.map((e: any) => {
    const rel = e.relationship || ''
    const config = getRelationConfig(rel)
    const relCN = getRelationCN(rel)
    
    // Build line style based on relationship type
    const lineStyle: any = {
      color: config.color,
      opacity: config.opacity,
      curveness: config.curveness,
      width: config.width,
    }
    
    // Apply dash pattern for dashed/dotted lines
    if (config.lineType === 'dashed' && config.dashPattern) {
      lineStyle.type = 'dashed'
      lineStyle.dashOffset = 0
    } else if (config.lineType === 'dotted' && config.dashPattern) {
      lineStyle.type = 'dotted'
      lineStyle.dashOffset = 0
    }
    
    return {
      ...e,
      source: String(e.source),
      target: String(e.target),
      relationship: rel,
      // Show edge label for important relationships, hide for others
      label: {
        show: ['structure', 'dependency', 'design'].includes(getGroupKey(rel)),
        formatter: relCN,
        fontSize: 9,
        color: config.color,
        backgroundColor: 'rgba(253,249,240,0.9)',
        padding: [2, 6],
        borderRadius: 4,
        fontWeight: 500,
      },
      lineStyle,
    }
  })

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item' as const,
      backgroundColor: 'rgba(253,249,240,0.96)',
      borderColor: 'rgba(26,40,71,0.1)',
      borderWidth: 1,
      padding: [16, 20],
      textStyle: { color: '#1a2847', fontSize: 13 },
      extraCssText: 'white-space: normal; word-break: break-word; max-width: 320px; box-shadow: 0 8px 32px rgba(26, 40, 71, 0.12); border-radius: 16px;',
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const d = params.data
          const mastery = Math.round((d.mastery_level || 0) * 100)
          const importance = Math.round((d.importance || 0.5) * 100)
          const desc = d.description
            ? `<div style="color:#6783c1;font-size:13px;margin-top:10px;line-height:1.6;border-top:1px solid rgba(26,40,71,0.06);padding-top:10px;">${d.description}</div>`
            : ''
          return `<div style="font-weight:800;font-size:16px;margin-bottom:10px;color:#1a2847;">${d.name}</div>
            <div style="display:flex;gap:16px;font-size:12px">
              <span style="color:#649b64">掌握 ${mastery}%</span>
              <span style="color:#c9873b">重要 ${importance}%</span>
            </div>${desc}`
        }
        if (params.dataType === 'edge') {
          const d = params.data
          const relCN = getRelationCN(d.relationship || '')
          const relColor = getRelationColor(d.relationship || '')
          const groupKey = getGroupKey(d.relationship || '')
          const groupLabel = relationColorGroups[groupKey]?.label || '其他'
          return `<div style="font-size:13px">
            <div style="color:${relColor};font-weight:700;margin-bottom:4px">${relCN}</div>
            <div style="font-size:11px;color:#6783c1">${groupLabel}</div>
          </div>`
        }
        return ''
      },
    },
    animationDuration: 800,
    animationEasing: 'cubicOut' as const,
    animationDurationUpdate: 300,
    animationEasingUpdate: 'cubicInOut' as const,
    series: [
      {
        type: 'graph' as const,
        layout: 'force' as const,
        data: nodes,
        links: edges,
        roam: 'scale', // Only native scale; panning is handled by our zr events
        draggable: true,
        // Performance: disable layout animation to prevent freezing
        layoutAnimation: false,
        emphasis: {
          focus: 'adjacency' as const,
          lineStyle: { width: 4, opacity: 0.9 },
          itemStyle: {
            borderWidth: 4,
            borderColor: '#e8b06a',
            shadowBlur: 25,
          },
          label: { fontWeight: 700, fontSize: 14, color: '#1a2847' },
          edgeLabel: { show: true, fontWeight: 600, fontSize: 11 },
        },
        blur: {
          itemStyle: { opacity: 0.1 },
          lineStyle: { opacity: 0.03, width: 0.5 },
          label: { color: 'rgba(44,62,95,0.15)' },
        },
        force: {
          repulsion: 1200,
          edgeLength: [120, 280],
          gravity: 0.12,
          friction: 0.6,
        },
        lineStyle: { opacity: 0.4 },
        edgeLabel: {
          show: false,
        },
      },
    ],
  }
})

// ─── Color helpers ───
function lightenColor(rgbStr: string, amount: number): string {
  const match = rgbStr.match(/rgb\((\d+),(\d+),(\d+)\)/)
  if (!match) return rgbStr
  const [, rs, gs, bs] = match
  const r = Math.min(255, parseInt(rs) + amount)
  const g = Math.min(255, parseInt(gs) + amount)
  const b = Math.min(255, parseInt(bs) + amount)
  return `rgb(${r},${g},${b})`
}

function darkenColor(rgbStr: string, amount: number): string {
  const match = rgbStr.match(/rgb\((\d+),(\d+),(\d+)\)/)
  if (!match) return rgbStr
  const [, rs, gs, bs] = match
  const r = Math.max(0, parseInt(rs) - amount)
  const g = Math.max(0, parseInt(gs) - amount)
  const b = Math.max(0, parseInt(bs) - amount)
  return `rgb(${r},${g},${b})`
}

onMounted(() => {
  loadDomains()
})
</script>

<style scoped>
/* ─── Root & background ─── */
.kg-root {
  background: #fdf9f0;
}

.kg-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 20% 30%, rgba(65, 100, 178, 0.05) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 70%, rgba(100, 155, 100, 0.04) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 50%, rgba(201, 135, 59, 0.02) 0%, transparent 50%);
  pointer-events: none;
}

/* ─── Refresh button ─── */
.kg-refresh-btn {
  background: rgba(26, 40, 71, 0.06);
  color: #4164b2;
  border: 1px solid rgba(26, 40, 71, 0.08);
}
.kg-refresh-btn:hover {
  background: rgba(65, 100, 178, 0.1);
  border-color: rgba(65, 100, 178, 0.2);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(65, 100, 178, 0.12);
}


/* ─── Domain pills ─── */
.kg-pill {
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
}
.kg-pill-active {
  background: #1a2847;
  color: #fdf9f0;
  box-shadow: 0 2px 8px rgba(26, 40, 71, 0.25);
}
.kg-pill-inactive {
  background: rgba(26, 40, 71, 0.04);
  color: #6783c1;
  border-color: rgba(26, 40, 71, 0.08);
}
.kg-pill-inactive:hover {
  background: rgba(65, 100, 178, 0.08);
  border-color: rgba(65, 100, 178, 0.15);
}

/* ─── Chart wrapper ─── */
.kg-chart-wrapper {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(26, 40, 71, 0.06);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 4px 16px rgba(0, 0, 0, 0.03);
}

/* ─── Zoom controls ─── */
.kg-zoom-controls {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  z-index: 10;
}

.kg-zoom-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(253, 249, 240, 0.92);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(26, 40, 71, 0.08);
  color: #4164b2;
  cursor: pointer;
  transition: all 0.2s;
}
.kg-zoom-btn:hover {
  background: rgba(65, 100, 178, 0.1);
  border-color: rgba(65, 100, 178, 0.2);
  transform: scale(1.08);
  box-shadow: 0 2px 8px rgba(65, 100, 178, 0.15);
}
.kg-zoom-btn:active {
  transform: scale(0.95);
}

/* ─── Relationship type legend ─── */
.kg-rel-legend {
  position: absolute;
  bottom: 12px;
  right: 12px;
  background: rgba(253, 249, 240, 0.92);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(26, 40, 71, 0.06);
  border-radius: 12px;
  padding: 10px 14px;
  z-index: 10;
}
.kg-rel-legend-title {
  font-size: 11px;
  font-weight: 600;
  color: #4a5874;
  margin-bottom: 6px;
  letter-spacing: 0.5px;
}
.kg-rel-legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 0;
}
.kg-rel-legend-line {
  flex-shrink: 0;
}
.kg-rel-legend-label {
  font-size: 11px;
  color: #5a6a84;
}

/* ─── Mastery legend ─── */
.kg-legend {
  position: absolute;
  bottom: 12px;
  left: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 12px;
  background: rgba(253, 249, 240, 0.92);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(26, 40, 71, 0.06);
  z-index: 10;
}
.kg-legend-bar {
  width: 48px;
  height: 6px;
  border-radius: 3px;
  background: linear-gradient(90deg, #1a2847, #4164b2, #649b64);
}

/* ─── Empty state ─── */
.kg-empty-icon {
  animation: float 3s ease-in-out infinite;
}
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

/* ─── Drawer overlay ─── */
.kg-drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(26, 40, 71, 0.2);
  backdrop-filter: blur(2px);
  z-index: 40;
}

/* ─── Drawer ─── */
.kg-drawer {
  position: fixed;
  top: 0;
  right: 0;
  width: 380px;
  height: 100%;
  background: rgba(253, 249, 240, 0.85);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  box-shadow: -8px 0 32px rgba(26, 40, 71, 0.1), -1px 0 0 rgba(255, 255, 255, 0.4) inset;
  z-index: 50;
  display: flex;
  flex-direction: column;
  border-left: 1px solid rgba(255, 255, 255, 0.6);
}

.kg-drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 28px;
  border-bottom: 1px solid rgba(26, 40, 71, 0.06);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.8) 0%, rgba(255, 255, 255, 0.4) 100%);
}

.kg-drawer-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #4164b2, #649b64);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.kg-drawer-close {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6783c1;
  transition: all 0.2s;
  cursor: pointer;
  background: none;
  border: none;
}
.kg-drawer-close:hover {
  background: rgba(26, 40, 71, 0.06);
  color: #1a2847;
}

.kg-drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
}

.kg-node-info {
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  padding: 18px;
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 2px 8px rgba(26, 40, 71, 0.03), 0 1px 1px rgba(255, 255, 255, 0.6) inset;
  margin-bottom: 18px;
}

/* ─── Stat cards ─── */
.kg-stat-card {
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  padding: 16px 18px;
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 2px 8px rgba(26, 40, 71, 0.03), 0 1px 1px rgba(255, 255, 255, 0.6) inset;
  margin-bottom: 14px;
}

/* ─── Removed old slider CSS, using Tailwind composite ─── */

/* ─── Relation items in drawer ─── */
.kg-relation-item {
  padding: 8px 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 1px 4px rgba(26, 40, 71, 0.02), 0 1px 1px rgba(255, 255, 255, 0.6) inset;
  transition: all 0.2s;
  cursor: default;
}
.kg-relation-item:hover {
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 4px 12px rgba(26, 40, 71, 0.05);
}

/* ─── Resource cards ─── */
.kg-resource-card {
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 2px 8px rgba(26, 40, 71, 0.03), 0 1px 1px rgba(255, 255, 255, 0.6) inset;
  cursor: pointer;
}
.kg-resource-card:hover {
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(65, 100, 178, 0.2);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(65, 100, 178, 0.08);
}

/* ─── Drawer transitions ─── */
.kg-overlay-enter-active,
.kg-overlay-leave-active {
  transition: opacity 0.3s ease;
}
.kg-overlay-enter-from,
.kg-overlay-leave-to {
  opacity: 0;
}

.kg-drawer-enter-active {
  transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}
.kg-drawer-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.kg-drawer-enter-from,
.kg-drawer-leave-to {
  transform: translateX(100%);
}

/* ─── Multiple Preview Drawers transitions ─── */
.drawer-list-move,
.drawer-list-enter-active,
.drawer-list-leave-active {
  transition: opacity 0.35s ease, transform 0.35s ease, right 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-list-enter-from,
.drawer-list-leave-to {
  opacity: 0;
  transform: translateX(40px);
}
</style>

<!-- Non-scoped: teleported search dropdown -->
<style>
.kg-search-dropdown {
  background: #fdf9f0;
  border: 1px solid rgba(26, 40, 71, 0.08);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(26, 40, 71, 0.12);
  padding: 6px 0;
  max-height: 320px;
  overflow-y: auto;
}
.kg-search-dropdown::-webkit-scrollbar { width: 4px; }
.kg-search-dropdown::-webkit-scrollbar-thumb { background: rgba(26,40,71,0.1); border-radius: 2px; }
.fade-up-enter-active { transition: all 0.2s ease; }
.fade-up-leave-active { transition: all 0.15s ease; }
.fade-up-enter-from, .fade-up-leave-to { opacity: 0; transform: translateY(-4px); }

/* ─── Global Task Toast ─── */
.kg-toast-card {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 340px;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(253, 249, 240, 0.92);
  backdrop-filter: blur(16px) saturate(1.4);
  border: 1px solid rgba(26, 40, 71, 0.08);
  box-shadow:
    0 4px 24px rgba(26, 40, 71, 0.10),
    0 1px 3px rgba(26, 40, 71, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.6);
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}
.kg-toast-card:hover {
  box-shadow:
    0 8px 32px rgba(26, 40, 71, 0.14),
    0 2px 6px rgba(26, 40, 71, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.7);
}
.kg-toast-done { border-color: rgba(100, 155, 100, 0.2); }
.kg-toast-error { border-color: rgba(201, 100, 80, 0.15); }

.kg-toast-status-icon {
  position: absolute; inset: 0; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  border: 1.5px solid;
}

/* Orbital ring */
.kg-toast-orbit {
  position: absolute; inset: 0; border-radius: 50%;
  border: 2px solid rgba(65, 100, 178, 0.12);
  animation: kg-orbit-spin 1.6s linear infinite;
}
.kg-toast-orbit-dot {
  position: absolute; top: -3px; left: 50%; margin-left: -3px;
  width: 6px; height: 6px; border-radius: 50%;
  background: #4164b2;
  box-shadow: 0 0 8px rgba(65, 100, 178, 0.5);
}
.kg-toast-orbit-inner {
  position: absolute; inset: 5px; border-radius: 50%;
  border: 1.5px dashed rgba(65, 100, 178, 0.1);
  animation: kg-orbit-spin-reverse 3s linear infinite;
}
@keyframes kg-orbit-spin { to { transform: rotate(360deg); } }
@keyframes kg-orbit-spin-reverse { to { transform: rotate(-360deg); } }

.kg-toast-icon-pulse { animation: kg-icon-breathe 2s ease-in-out infinite; }
@keyframes kg-icon-breathe {
  0%, 100% { opacity: 0.7; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.1); }
}

.kg-toast-msg-processing { color: #4164b2; }
.kg-toast-msg-done { color: #4a7a4a; }
.kg-toast-msg-error { color: #b5543e; }

.kg-toast-close {
  flex-shrink: 0; padding: 5px; border-radius: 8px;
  color: rgba(26, 40, 71, 0.25); cursor: pointer; transition: all 0.2s;
}
.kg-toast-close:hover { color: #4164b2; background: rgba(65, 100, 178, 0.08); }

.kg-toast-enter-active, .kg-toast-leave-active, .kg-toast-move {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
.kg-toast-enter-from { opacity: 0; transform: translateX(60px) scale(0.9); }
.kg-toast-leave-to { opacity: 0; transform: translateY(16px) scale(0.92); }
</style>
