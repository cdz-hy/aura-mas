<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <h1 class="section-title">知识库管理</h1>
      <button class="btn-primary flex items-center gap-2" @click="showUpload = true">
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        上传文档
      </button>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <div class="card p-5">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
            <svg class="w-5 h-5 text-blue-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
            </svg>
          </div>
          <div>
            <p class="text-xs text-navy-400 uppercase tracking-wider">文档总数</p>
            <p class="text-2xl font-bold text-navy-800">{{ total }}</p>
          </div>
        </div>
      </div>

      <div class="card p-5">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center">
            <svg class="w-5 h-5 text-emerald-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
            </svg>
          </div>
          <div>
            <p class="text-xs text-navy-400 uppercase tracking-wider">Qdrant 切片</p>
            <p class="text-2xl font-bold text-navy-800">{{ collectionStats?.total_points ?? '—' }}</p>
          </div>
        </div>
      </div>

      <div class="card p-5">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg flex items-center justify-center" :class="collectionStats?.status === 'green' ? 'bg-emerald-50' : 'bg-amber-50'">
            <svg class="w-5 h-5" :class="collectionStats?.status === 'green' ? 'text-emerald-600' : 'text-amber-600'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <div>
            <p class="text-xs text-navy-400 uppercase tracking-wider">集合状态</p>
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full" :class="collectionStats?.status === 'green' ? 'bg-emerald-500' : 'bg-amber-500'" />
              <p class="text-lg font-semibold text-navy-800">{{ collectionStats?.status === 'green' ? '健康' : collectionStats?.status ?? '未知' }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div v-if="loading" class="p-12 text-center">
        <div class="inline-block w-8 h-8 border-2 border-navy-200 border-t-navy-600 rounded-full animate-spin" />
        <p class="text-sm text-navy-400 mt-3">加载中...</p>
      </div>

      <template v-else-if="documents.length > 0">
        <table class="w-full">
          <thead>
            <tr class="border-b border-navy-100 bg-navy-50/50">
              <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">文档名称</th>
              <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">文件大小</th>
              <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">解析状态</th>
              <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">切片数量</th>
              <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">上传时间</th>
              <th class="px-5 py-3 text-right text-xs font-semibold text-navy-500 uppercase tracking-wider">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(doc, idx) in documents"
              :key="doc.id"
              class="border-b border-navy-50 hover:bg-navy-50/30 transition-colors group"
              :class="!documentsLoaded && 'animate-row'"
              :style="{ animationDelay: `${idx * 40}ms` }"
            >
              <td class="px-5 py-4">
                <div class="flex items-center gap-3">
                  <div class="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-100 to-blue-200 flex items-center justify-center">
                    <svg class="w-5 h-5 text-blue-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                    </svg>
                  </div>
                  <div>
                    <p class="text-sm font-medium text-navy-800">{{ doc.docName }}</p>
                    <p class="text-xs text-navy-400">ID: {{ doc.id }}</p>
                  </div>
                </div>
              </td>
              <td class="px-5 py-4 text-sm text-navy-500">{{ formatFileSize(doc.fileSize) }}</td>
              <td class="px-5 py-4">
                <span class="badge inline-flex items-center gap-1.5" :class="statusClass(doc.parseStatus)">
                  <span v-if="doc.parseStatus === 1 || doc.parseStatus === 4" class="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  <span v-else class="w-1.5 h-1.5 rounded-full" :class="statusDotClass(doc.parseStatus)" />
                  {{ statusLabel(doc.parseStatus) }}
                </span>
              </td>
              <td class="px-5 py-4 text-sm text-navy-500">{{ doc.chunkCount ?? '—' }}</td>
              <td class="px-5 py-4 text-sm text-navy-400">{{ formatTime(doc.uploadTime) }}</td>
              <td class="px-5 py-4">
                <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    class="p-1.5 rounded-lg hover:bg-blue-50 text-navy-400 hover:text-blue-600 transition-colors disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-navy-400"
                    title="查看详情"
                    @click="openDetail(doc)"
                    :disabled="doc.parseStatus !== 2"
                  >
                    <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
                    </svg>
                  </button>
                  <button
                    class="p-1.5 rounded-lg hover:bg-amber-50 text-navy-400 hover:text-amber-600 transition-colors disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-navy-400"
                    title="重新处理"
                    @click="handleReprocess(doc)"
                    :disabled="doc.parseStatus === 1 || doc.parseStatus === 2 || doc.parseStatus === 4"
                  >
                    <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                      <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                    </svg>
                  </button>
                  <button
                    class="p-1.5 rounded-lg hover:bg-red-50 text-navy-400 hover:text-red-500 transition-colors"
                    title="删除"
                    @click="confirmDelete(doc)"
                  >
                    <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                      <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Pagination -->
        <div class="px-5 py-4 border-t border-navy-100 flex items-center justify-between">
          <p class="text-sm text-navy-400">
            共 <span class="font-medium text-navy-600">{{ total }}</span> 条记录
          </p>
          <div class="flex items-center gap-1">
            <button
              class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
              :class="currentPage > 1 ? 'text-navy-600 hover:bg-navy-50' : 'text-navy-300 cursor-not-allowed'"
              :disabled="currentPage <= 1"
              @click="loadDocuments(currentPage - 1)"
            >
              上一页
            </button>
            <button
              v-for="p in visiblePages"
              :key="p"
              class="w-9 h-9 rounded-lg text-sm font-medium transition-colors"
              :class="p === currentPage ? 'bg-navy-600 text-white shadow-sm' : 'text-navy-600 hover:bg-navy-50'"
              @click="loadDocuments(p)"
            >
              {{ p }}
            </button>
            <button
              class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
              :class="currentPage < totalPages ? 'text-navy-600 hover:bg-navy-50' : 'text-navy-300 cursor-not-allowed'"
              :disabled="currentPage >= totalPages"
              @click="loadDocuments(currentPage + 1)"
            >
              下一页
            </button>
          </div>
        </div>
      </template>

      <div v-else class="p-12 text-center">
        <svg class="w-16 h-16 mx-auto text-navy-200 mb-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
        </svg>
        <p class="text-navy-400">暂无文档</p>
        <button class="btn-ghost text-sm mt-3" @click="showUpload = true">上传第一份文档</button>
      </div>
    </div>

    <!-- Upload Modal -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="showUpload" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="cancelUpload" />
          <div class="relative bg-white rounded-2xl shadow-2xl w-[480px] max-w-[90vw] p-6 animate-scale-in">
            <h3 class="text-lg font-semibold text-navy-800 mb-4">上传知识库文档</h3>

            <!-- Drag & Drop Zone -->
            <div
              class="border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer"
              :class="isDragging ? 'border-blue-400 bg-blue-50' : 'border-navy-200 hover:border-navy-300'"
              @dragover.prevent="isDragging = true"
              @dragleave="isDragging = false"
              @drop.prevent="handleDrop"
              @click="triggerFileInput"
            >
              <input ref="fileInput" type="file" class="hidden" accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md" @change="handleFileSelect" />
              <svg class="w-12 h-12 mx-auto mb-3" :class="uploadForm.file ? 'text-blue-500' : 'text-navy-300'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              <p v-if="uploadForm.file" class="text-sm font-medium text-blue-600">{{ uploadForm.file.name }}</p>
              <p v-else class="text-sm text-navy-400">拖拽文件到此处或点击选择</p>
              <p class="text-xs text-navy-300 mt-1">支持 PDF、Word、PPT、Excel、TXT、Markdown</p>
            </div>

            <!-- Document Name -->
            <div class="mt-4">
              <label class="block text-sm font-medium text-navy-600 mb-1.5">文档名称</label>
              <input
                v-model="uploadForm.docName"
                type="text"
                class="input-field"
                placeholder="输入文档名称（可选，默认使用文件名）"
              />
            </div>

            <!-- Actions -->
            <div class="flex justify-end gap-3 mt-6">
              <button class="btn-ghost text-sm" @click="cancelUpload">取消</button>
              <button
                class="btn-primary text-sm flex items-center gap-2"
                :disabled="!uploadForm.file || uploading"
                @click="handleUpload"
              >
                <span v-if="uploading" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                {{ uploading ? '上传中...' : '开始上传' }}
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Delete Confirm Modal -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="showDeleteConfirm" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="showDeleteConfirm = false" />
          <div class="relative bg-white rounded-2xl shadow-2xl w-[400px] max-w-[85vw] p-6 animate-scale-in">
            <div class="flex justify-center mb-4">
              <div class="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center">
                <svg class="w-6 h-6 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                  <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
              </div>
            </div>
            <h3 class="text-center text-base font-semibold text-navy-800 mb-1">确认删除</h3>
            <p class="text-center text-sm text-navy-400 mb-6">
              确定要删除文档「{{ deleteTarget?.docName }}」吗？此操作将同时删除 Qdrant 中的所有切片数据。
            </p>
            <div class="flex gap-3">
              <button class="flex-1 py-2.5 rounded-lg text-sm border border-navy-200 text-navy-600 hover:bg-navy-50 transition-colors font-medium" @click="showDeleteConfirm = false">
                取消
              </button>
              <button class="flex-1 py-2.5 rounded-lg text-sm text-white bg-red-500 hover:bg-red-600 transition-colors font-medium" @click="handleDelete">
                确认删除
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Detail Drawer -->
    <Teleport to="body">
      <transition name="slide-right">
        <div v-if="showDetail" class="fixed inset-0 z-50 flex justify-end">
          <div class="absolute inset-0 bg-black/30 backdrop-blur-sm" @click="closeDetail" />
          <div class="relative w-[520px] max-w-[90vw] bg-white h-full shadow-2xl overflow-y-auto animate-slide-in-right">
            <!-- Header -->
            <div class="sticky top-0 bg-white border-b border-navy-100 px-6 py-4 flex items-center justify-between z-10">
              <div>
                <h3 class="text-lg font-semibold text-navy-800">{{ selectedDoc?.docName }}</h3>
                <p class="text-xs text-navy-400 mt-0.5">文档详情 & 切片统计</p>
              </div>
              <button class="p-2 rounded-lg hover:bg-navy-100 text-navy-400 hover:text-navy-700 transition-colors" @click="closeDetail">
                <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>

            <div v-if="detailLoading" class="p-12 text-center">
              <div class="inline-block w-8 h-8 border-2 border-navy-200 border-t-navy-600 rounded-full animate-spin" />
              <p class="text-sm text-navy-400 mt-3">加载详情...</p>
            </div>

            <template v-else-if="docDetail">
              <!-- Summary -->
              <div class="px-6 py-5 border-b border-navy-100">
                <div class="grid grid-cols-2 gap-4">
                  <div class="bg-navy-50 rounded-xl p-4">
                    <p class="text-xs text-navy-400 uppercase tracking-wider">切片总数</p>
                    <p class="text-3xl font-bold text-navy-800 mt-1">{{ docDetail.total_chunks }}</p>
                  </div>
                  <div class="bg-navy-50 rounded-xl p-4">
                    <p class="text-xs text-navy-400 uppercase tracking-wider">类型分布</p>
                    <div class="mt-2 space-y-1">
                      <div v-for="(count, type) in docDetail.type_distribution" :key="type" class="flex items-center justify-between">
                        <span class="text-sm text-navy-600">{{ type === 'text' ? '文本' : type === 'image' ? '图片' : type }}</span>
                        <span class="text-sm font-medium text-navy-800">{{ count }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Heading Distribution -->
              <div class="px-6 py-5 border-b border-navy-100">
                <h4 class="text-sm font-semibold text-navy-700 mb-3">章节结构</h4>
                <div class="space-y-2 max-h-[200px] overflow-y-auto">
                  <div
                    v-for="item in docDetail.heading_distribution"
                    :key="item.heading"
                    class="flex items-center justify-between py-1.5 px-3 rounded-lg hover:bg-navy-50"
                  >
                    <span class="text-sm text-navy-600 truncate flex-1 mr-3">{{ item.heading }}</span>
                    <span class="text-xs font-medium text-navy-400 bg-navy-100 px-2 py-0.5 rounded-full">{{ item.count }}</span>
                  </div>
                </div>
              </div>

              <!-- Sample Chunks -->
              <div class="px-6 py-5">
                <h4 class="text-sm font-semibold text-navy-700 mb-3">切片预览</h4>
                <div class="space-y-3">
                  <div
                    v-for="chunk in docDetail.sample_chunks"
                    :key="chunk.id"
                    class="bg-navy-50 rounded-xl p-4"
                  >
                    <div class="flex items-center gap-2 mb-2">
                      <span class="badge text-xs" :class="chunk.type === 'text' ? 'bg-blue-50 text-blue-700' : 'bg-purple-50 text-purple-700'">
                        {{ chunk.type === 'text' ? '文本' : '图片' }}
                      </span>
                      <span v-if="chunk.heading?.length" class="text-xs text-navy-400 truncate">
                        {{ chunk.heading.join(' > ') }}
                      </span>
                    </div>
                    <p class="text-sm text-navy-600 line-clamp-3">{{ chunk.content_preview || '(无内容预览)' }}</p>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  getKBList,
  createKB,
  deleteKB,
  ingestKB,
  reprocessKB,
  getCollectionStats,
  getDocDetail,
  type KnowledgeBase,
  type CollectionStats,
  type KBDetailStats,
} from '@/api/kb'
import { showToast } from '@/composables/useToast'

// State
const documents = ref<KnowledgeBase[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const loading = ref(false)

const collectionStats = ref<CollectionStats | null>(null)

const showUpload = ref(false)
const uploading = ref(false)
const isDragging = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const uploadForm = ref({ docName: '', file: null as File | null })

const showDeleteConfirm = ref(false)
const deleteTarget = ref<KnowledgeBase | null>(null)

const showDetail = ref(false)
const detailLoading = ref(false)
const selectedDoc = ref<KnowledgeBase | null>(null)
const docDetail = ref<KBDetailStats | null>(null)

let pollingTimer: number | null = null
const documentsLoaded = ref(false)

// Constants
const MAX_FILE_SIZE = 200 * 1024 * 1024 // 200MB
const ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.txt', '.md']

// Computed
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const visiblePages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

const hasProcessingDocs = computed(() => documents.value.some(d => d.parseStatus === 1 || d.parseStatus === 4))

// Methods
async function loadDocuments(page: number, showLoading = true) {
  if (showLoading) loading.value = true
  try {
    const res = await getKBList({ page, size: pageSize.value })
    const data = res.data ?? res
    documents.value = data.records || []
    total.value = data.total || 0
    currentPage.value = page
    documentsLoaded.value = true
  } catch (e) {
    console.error('加载文档列表失败:', e)
  } finally {
    if (showLoading) loading.value = false
  }
}

async function loadCollectionStats() {
  try {
    collectionStats.value = await getCollectionStats('aura_multimodal_resources')
  } catch (e) {
    console.error('加载集合统计失败:', e)
  }
}

function triggerFileInput() {
  fileInput.value?.click()
}

function validateFile(file: File): boolean {
  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    showToast(`不支持的文件格式: ${ext}`, 'warning', { title: '格式错误' })
    return false
  }
  if (file.size > MAX_FILE_SIZE) {
    showToast(`文件大小超过限制: ${(file.size / 1024 / 1024).toFixed(1)}MB，最大支持 200MB`, 'warning', { title: '文件过大' })
    return false
  }
  return true
}

function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) {
    const file = input.files[0]
    if (!validateFile(file)) {
      input.value = ''
      return
    }
    uploadForm.value.file = file
    if (!uploadForm.value.docName) {
      uploadForm.value.docName = file.name.replace(/\.[^/.]+$/, '')
    }
  }
}

function handleDrop(e: DragEvent) {
  isDragging.value = false
  if (e.dataTransfer?.files?.[0]) {
    const file = e.dataTransfer.files[0]
    if (!validateFile(file)) return
    uploadForm.value.file = file
    if (!uploadForm.value.docName) {
      uploadForm.value.docName = file.name.replace(/\.[^/.]+$/, '')
    }
  }
}

function cancelUpload() {
  showUpload.value = false
  uploadForm.value = { docName: '', file: null }
  isDragging.value = false
}

async function handleUpload() {
  if (!uploadForm.value.file) return

  uploading.value = true
  try {
    const file = uploadForm.value.file
    const docName = uploadForm.value.docName || file.name.replace(/\.[^/.]+$/, '')

    // 1. Java: 创建 KB 记录（只传元数据）
    const res = await createKB(docName, file.size)
    const kb = res.data ?? res

    // 2. Python: 传文件进行解析、切片、入库
    await ingestKB(kb.id, docName, file)

    cancelUpload()
    showToast('文档已提交解析，处理完成后自动更新', 'success', { title: '上传成功' })
    loadDocuments(1)
    startPolling()
  } catch (e) {
    console.error('上传失败:', e)
    showToast('上传失败: ' + (e instanceof Error ? e.message : String(e)), 'error', { title: '上传失败' })
  } finally {
    uploading.value = false
  }
}

function confirmDelete(doc: KnowledgeBase) {
  deleteTarget.value = doc
  showDeleteConfirm.value = true
}

async function handleDelete() {
  if (!deleteTarget.value) return
  try {
    await deleteKB(deleteTarget.value.id)
    const docName = deleteTarget.value.docName
    showDeleteConfirm.value = false
    deleteTarget.value = null
    loadDocuments(currentPage.value)
    loadCollectionStats()
    showToast(`文档「${docName}」已删除`, 'success', { title: '删除成功' })
  } catch (e) {
    console.error('删除失败:', e)
    showToast('删除失败，请稍后重试', 'error', { title: '删除失败' })
  }
}

async function handleReprocess(doc: KnowledgeBase) {
  if (doc.parseStatus === 1 || doc.parseStatus === 2 || doc.parseStatus === 4) return
  try {
    const res = await reprocessKB(doc.id, doc.docName)
    const data = res.data ?? res
    const mode = data.mode === 'local' ? '从本地结果重新处理' : '重新执行完整解析'
    showToast(`${mode}任务已提交（doc_id=${doc.id}）`, 'success', { title: '重试已提交' })
    startPolling()
  } catch (e) {
    console.error('重新处理失败:', e)
    showToast('重新处理失败: ' + (e instanceof Error ? e.message : String(e)), 'error', { title: '重试失败' })
  }
}

async function openDetail(doc: KnowledgeBase) {
  if (doc.parseStatus !== 2) return
  selectedDoc.value = doc
  showDetail.value = true
  detailLoading.value = true
  docDetail.value = null

  try {
    docDetail.value = await getDocDetail('aura_multimodal_resources', doc.id)
  } catch (e) {
    console.error('加载详情失败:', e)
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  showDetail.value = false
  selectedDoc.value = null
  docDetail.value = null
}

function startPolling() {
  if (pollingTimer) return
  pollingTimer = window.setInterval(async () => {
    if (!hasProcessingDocs.value) {
      stopPolling()
      return
    }
    await loadDocuments(currentPage.value, false)
    await loadCollectionStats()
  }, 5000)
}

function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

function formatFileSize(bytes: number | null | undefined): string {
  if (!bytes) return '—'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatTime(time: string | null | undefined): string {
  if (!time) return '—'
  const d = new Date(time)
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function statusLabel(status: number): string {
  const map: Record<number, string> = { 0: '待解析', 1: '解析中', 2: '已入库', 3: '解析失败', 4: '向量化中' }
  return map[status] ?? '未知'
}

function statusClass(status: number): string {
  const map: Record<number, string> = {
    0: 'bg-gray-50 text-gray-600 border border-gray-200',
    1: 'bg-blue-50 text-blue-700 border border-blue-200',
    2: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
    3: 'bg-red-50 text-red-700 border border-red-200',
    4: 'bg-amber-50 text-amber-700 border border-amber-200',
  }
  return map[status] ?? ''
}

function statusDotClass(status: number): string {
  const map: Record<number, string> = { 0: 'bg-gray-400', 1: 'bg-blue-500', 2: 'bg-emerald-500', 3: 'bg-red-500', 4: 'bg-amber-500' }
  return map[status] ?? ''
}

// Lifecycle
onMounted(async () => {
  await Promise.all([loadDocuments(1), loadCollectionStats()])
  if (hasProcessingDocs.value) startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.animate-scale-in {
  animation: scaleIn 0.2s ease-out;
}

@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

.animate-row {
  animation: fadeInRow 0.3s ease-out both;
}

@keyframes fadeInRow {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-slide-in-right {
  animation: slideInRight 0.3s ease-out;
}

@keyframes slideInRight {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-right-enter-active, .slide-right-leave-active { transition: opacity 0.2s ease; }
.slide-right-enter-from, .slide-right-leave-to { opacity: 0; }

.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
