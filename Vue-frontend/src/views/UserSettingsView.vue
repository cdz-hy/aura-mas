<template>
  <div class="animate-fade-in-up">
    <div class="flex items-center justify-between mb-6">
      <h1 class="section-title">个人设置</h1>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Avatar card -->
      <div class="card p-6 text-center flex flex-col">
        <div>
        <h2 class="font-display text-lg font-semibold text-navy-800 mb-4">头像</h2>
        <div class="relative inline-block mb-4">
          <div class="w-28 h-28 rounded-full overflow-hidden border-4 border-navy-50 shadow-lg mx-auto">
            <img
              v-if="avatarUrl"
              :src="avatarUrl"
              alt="头像"
              class="w-full h-full object-cover"
            />
            <div
              v-else
              class="w-full h-full bg-gradient-to-br from-sage-400 to-sage-600 flex items-center justify-center text-white text-4xl font-bold"
            >
              {{ form.nickname?.[0] || 'U' }}
            </div>
          </div>
          <label
            class="absolute bottom-0 right-0 w-8 h-8 rounded-full bg-navy-600 text-white flex items-center justify-center cursor-pointer hover:bg-navy-700 transition-colors shadow-md"
            title="更换头像"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
              <circle cx="12" cy="13" r="4"/>
            </svg>
            <input
              ref="fileInputRef"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              class="hidden"
              @change="handleFileSelect"
            />
          </label>
        </div>
        <p class="text-xs text-navy-300">支持 JPG / PNG / WebP，裁剪后自动压缩至 1MB 以内</p>
        <p v-if="uploading" class="text-xs text-sage-500 mt-1">上传中...</p>
        <button
          v-if="avatarUrl"
          class="mt-3 text-xs text-red-400 hover:text-red-600 transition-colors"
          @click="handleClearAvatar"
        >
          清空头像
        </button>

        <!-- Theme Switcher -->
        <div class="mt-5 pt-5 border-t border-navy-100">
          <h3 class="text-sm font-medium text-navy-600 mb-3">界面主题</h3>
          <div class="grid grid-cols-1 gap-2">
            <button
              v-for="theme in themePresets"
              :key="theme.id"
              class="flex items-center gap-3 px-3 py-2.5 rounded-xl border-2 transition-all duration-300 text-left group"
              :class="currentTheme === theme.id
                ? 'border-navy-500 bg-navy-50 shadow-sm'
                : 'border-transparent hover:border-navy-200 hover:bg-navy-50/50'"
              @click="handleThemeChange(theme.id)"
            >
              <!-- Color preview dots -->
              <div class="flex-shrink-0 relative w-9 h-9 rounded-lg overflow-hidden shadow-sm border border-navy-100/50">
                <div class="absolute inset-0" :style="{ background: theme.preview.bg }"></div>
                <div class="absolute bottom-0 right-0 w-5 h-5 rounded-tl-lg" :style="{ background: theme.preview.accent }"></div>
                <div class="absolute top-1 left-1 w-2 h-2 rounded-full" :style="{ background: theme.preview.text }"></div>
              </div>
              <div class="flex-1 min-w-0">
                <span class="text-sm font-medium text-navy-800 block">{{ theme.name }}</span>
                <span class="text-xs text-navy-400">{{ theme.description }}</span>
              </div>
              <!-- Check mark -->
              <svg v-if="currentTheme === theme.id" class="w-4 h-4 text-navy-600 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </button>
          </div>
        </div>
        </div>

        <!-- Delete account -->
        <div class="mt-auto pt-5 border-t border-navy-100">
          <button
            class="text-xs text-navy-300 hover:text-red-500 transition-colors"
            @click="showDeleteDialog = true"
          >
            注销账号
          </button>
        </div>
      </div>

      <!-- User info form -->
      <div class="card p-6 lg:col-span-2">
        <h2 class="font-display text-lg font-semibold text-navy-800 mb-6">基本信息</h2>
        <div class="space-y-5">
          <!-- Login name (read-only) -->
          <div>
            <label class="block text-sm font-medium text-navy-600 mb-1.5">登录名</label>
            <input
              :value="form.loginName"
              disabled
              class="w-full px-4 py-2.5 rounded-lg border border-navy-100 bg-navy-50/50 text-navy-400 cursor-not-allowed"
            />
          </div>

          <!-- Nickname -->
          <div>
            <label class="block text-sm font-medium text-navy-600 mb-1.5">昵称</label>
            <input
              v-model="form.nickname"
              class="w-full px-4 py-2.5 rounded-lg border border-navy-200 focus:border-navy-400 focus:ring-2 focus:ring-navy-100 outline-none transition-all"
              placeholder="输入昵称"
            />
          </div>

          <!-- Email -->
          <div>
            <label class="block text-sm font-medium text-navy-600 mb-1.5">邮箱</label>
            <input
              v-model="form.email"
              type="email"
              class="w-full px-4 py-2.5 rounded-lg border border-navy-200 focus:border-navy-400 focus:ring-2 focus:ring-navy-100 outline-none transition-all"
              placeholder="输入邮箱"
            />
          </div>

          <!-- Gender -->
          <div>
            <label class="block text-sm font-medium text-navy-600 mb-1.5">性别</label>
            <div class="flex gap-3">
              <button
                v-for="option in genderOptions"
                :key="option.value"
                class="px-5 py-2 rounded-lg border text-sm transition-all duration-200"
                :class="form.gender === option.value
                  ? 'border-navy-400 bg-navy-50 text-navy-700 font-medium'
                  : 'border-navy-200 text-navy-400 hover:border-navy-300'"
                @click="form.gender = option.value"
              >
                {{ option.label }}
              </button>
            </div>
          </div>

          <!-- Age -->
          <div>
            <label class="block text-sm font-medium text-navy-600 mb-1.5">年龄段</label>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="option in ageOptions"
                :key="option"
                class="px-4 py-1.5 rounded-lg border text-sm transition-all duration-200"
                :class="form.age === option
                  ? 'border-navy-400 bg-navy-50 text-navy-700 font-medium'
                  : 'border-navy-200 text-navy-400 hover:border-navy-300'"
                @click="selectAge(option)"
              >
                {{ option }}
              </button>
              <button
                class="px-4 py-1.5 rounded-lg border text-sm transition-all duration-200"
                :class="isCustomAge
                  ? 'border-navy-400 bg-navy-50 text-navy-700 font-medium'
                  : 'border-navy-200 text-navy-400 hover:border-navy-300'"
                @click="selectAge('其他')"
              >
                {{ isCustomAge && form.age ? form.age : '其他' }}
              </button>
            </div>
            <div v-if="isCustomAge" class="mt-2.5 flex items-center gap-2">
              <input
                v-model="customAge"
                type="number"
                min="1"
                max="150"
                class="w-28 px-4 py-2 rounded-lg border border-navy-200 focus:border-navy-400 focus:ring-2 focus:ring-navy-100 outline-none transition-all text-sm"
                placeholder="输入年龄"
                @input="onCustomAgeInput"
              />
              <span class="text-sm text-navy-400">岁</span>
            </div>
          </div>

          <!-- Domain -->
          <div>
            <label class="block text-sm font-medium text-navy-600 mb-1.5">学习领域</label>
            <input
              v-model="form.domain"
              class="w-full px-4 py-2.5 rounded-lg border border-navy-200 focus:border-navy-400 focus:ring-2 focus:ring-navy-100 outline-none transition-all"
              placeholder="如：计算机科学、数学、物理等"
            />
          </div>

          <!-- Save button -->
          <div class="pt-4 border-t border-navy-100 flex items-center justify-between">
            <p v-if="saveMsg" class="text-sm" :class="saveSuccess ? 'text-sage-600' : 'text-red-500'">
              {{ saveMsg }}
            </p>
            <div v-else></div>
            <button
              class="px-6 py-2.5 rounded-lg text-sm text-white bg-navy-600 hover:bg-navy-700 transition-colors font-medium"
              @click="saveAll"
            >
              保存修改
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Cropper modal -->
    <AvatarCropper
      :visible="cropperVisible"
      :image-src="cropperImageSrc"
      @cancel="closeCropper"
      @cropped="handleCropped"
    />

    <!-- Clear avatar confirm dialog -->
    <ConfirmDialog
      :visible="clearDialogVisible"
      title="清空头像"
      message="确定要清空当前头像吗？清空后将显示默认头像。"
      confirm-text="清空"
      type="danger"
      @confirm="confirmClearAvatar"
      @cancel="clearDialogVisible = false"
    />

    <!-- Delete account confirm dialog (3 steps) -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="showDeleteDialog" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="cancelDelete" />
          <div class="relative bg-white rounded-2xl shadow-2xl w-[400px] max-w-[85vw] p-6 animate-scale-in">
            <div class="flex justify-center mb-4">
              <div class="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center">
                <svg class="w-6 h-6 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/>
                  <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
              </div>
            </div>
            <h3 class="text-center text-base font-semibold text-navy-800 mb-1">{{ deleteDialogTitle }}</h3>
            <p class="text-center text-sm text-navy-400 mb-2">{{ deleteDialogMessage }}</p>
            <p class="text-center text-xs text-red-400 mb-4">确认次数 {{ deleteConfirmStep }}/3</p>
            <div class="flex gap-3">
              <button
                class="flex-1 py-2.5 rounded-lg text-sm border border-navy-200 text-navy-600 hover:bg-navy-50 transition-colors font-medium"
                @click="cancelDelete"
              >
                取消
              </button>
              <button
                class="flex-1 py-2.5 rounded-lg text-sm text-white bg-red-500 hover:bg-red-600 transition-colors font-medium"
                :disabled="deleting"
                @click="handleDeleteStep"
              >
                <span v-if="deleting" class="inline-flex items-center gap-2">
                  <svg class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="4" stroke-linecap="round" class="opacity-75"/></svg>
                  注销中...
                </span>
                <span v-else>{{ deleteConfirmButtonText }}</span>
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore, themePresets } from '@/stores/ui'
import type { ThemeId } from '@/stores/ui'
import { getCurrentUser, getCurrentProfile, updateUserInfo, uploadAvatar, clearAvatar, deleteAccount, updateProfile } from '@/api/user'
import AvatarCropper from '@/components/common/AvatarCropper.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import type { User } from '@/types/user'
import type { StudentProfile } from '@/types/profile'

const authStore = useAuthStore()
const uiStore = useUiStore()
const router = useRouter()

const currentTheme = computed(() => uiStore.currentTheme)

function handleThemeChange(themeId: ThemeId) {
  uiStore.setTheme(themeId)
}

// Delete account state
const showDeleteDialog = ref(false)
const deleteConfirmStep = ref(1)
const deleting = ref(false)

const deleteMessages = [
  { title: '注销账号', msg: '确定要注销账号吗？所有相关资源将会被清空！', btn: '继续' },
  { title: '警告', msg: '此操作不可撤销！所有学习计划、笔记、对话记录等数据将被永久删除！', btn: '继续' },
  { title: '最后确认', msg: '你真的要永久注销此账号吗？一旦确认，所有数据将无法恢复！', btn: '确认注销' },
]

const deleteDialogTitle = computed(() => deleteMessages[deleteConfirmStep.value - 1].title)
const deleteDialogMessage = computed(() => deleteMessages[deleteConfirmStep.value - 1].msg)
const deleteConfirmButtonText = computed(() => deleteMessages[deleteConfirmStep.value - 1].btn)

function cancelDelete() {
  showDeleteDialog.value = false
  deleteConfirmStep.value = 1
}

async function handleDeleteStep() {
  if (deleteConfirmStep.value < 3) {
    deleteConfirmStep.value++
    return
  }

  deleting.value = true
  try {
    await deleteAccount()
    showDeleteDialog.value = false
    deleteConfirmStep.value = 1
    authStore.logout()
    router.push({ path: '/login', query: { deleted: '1' } })
  } catch {
    // Keep dialog open for retry
  } finally {
    deleting.value = false
  }
}

const avatarUrl = ref('')
const uploading = ref(false)
const saveMsg = ref('')
const saveSuccess = ref(false)
const fileInputRef = ref<HTMLInputElement>()

// Cropper state
const cropperVisible = ref(false)
const cropperImageSrc = ref('')

// Clear avatar dialog state
const clearDialogVisible = ref(false)

const form = reactive({
  loginName: '',
  nickname: '',
  email: '',
  gender: '',
  age: '',
  domain: '',
})

const genderOptions = [
  { value: 'male', label: '男' },
  { value: 'female', label: '女' },
  { value: 'other', label: '其他' },
]

const ageOptions = ['18岁以下', '18-22岁', '23-30岁', '31-40岁', '40岁以上']

const isCustomAge = ref(false)
const customAge = ref('')

function selectAge(option: string) {
  if (option === '其他') {
    isCustomAge.value = true
    form.age = customAge.value ? `${customAge.value}岁` : ''
  } else {
    isCustomAge.value = false
    customAge.value = ''
    form.age = option
  }
}

function onCustomAgeInput() {
  const num = customAge.value.replace(/[^0-9]/g, '')
  customAge.value = num
  form.age = num ? `${num}岁` : ''
}

async function loadUser() {
  try {
    const userRes = await getCurrentUser()
    const user = userRes.data as User
    form.loginName = user.loginName || ''
    form.nickname = user.nickname || ''
    form.email = user.email || ''
    avatarUrl.value = user.avatarUrl || ''
  } catch (e) {
    console.error('Failed to load user:', e)
  }

  try {
    const profileRes = await getCurrentProfile()
    const profile = profileRes.data as StudentProfile
    if (profile) {
      form.gender = profile.gender || ''
      form.domain = profile.domain || ''
      // 判断年龄是预设选项还是自定义输入
      const ageVal = profile.age || ''
      if (ageOptions.includes(ageVal)) {
        form.age = ageVal
        isCustomAge.value = false
        customAge.value = ''
      } else if (ageVal) {
        form.age = ageVal
        isCustomAge.value = true
        customAge.value = ageVal.replace(/岁$/, '')
      } else {
        form.age = ''
        isCustomAge.value = false
        customAge.value = ''
      }
    }
  } catch {
    // Profile may not exist yet
  }
}

function handleFileSelect(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return

  // Reset input so the same file can be selected again
  if (fileInputRef.value) fileInputRef.value.value = ''

  if (!file.type.startsWith('image/')) {
    saveMsg.value = '请选择图片文件'
    saveSuccess.value = false
    return
  }

  // Read file and open cropper（裁剪后会自动压缩至 1MB 以内）
  const reader = new FileReader()
  reader.onload = (ev) => {
    cropperImageSrc.value = ev.target?.result as string
    cropperVisible.value = true
  }
  reader.readAsDataURL(file)
}

function closeCropper() {
  cropperVisible.value = false
  cropperImageSrc.value = ''
}

async function handleCropped(file: File) {
  closeCropper()
  uploading.value = true
  saveMsg.value = ''
  try {
    const res = await uploadAvatar(file)
    avatarUrl.value = (res.data as any).avatarUrl
    if (authStore.user) {
      authStore.user.avatarUrl = avatarUrl.value
      localStorage.setItem('user', JSON.stringify(authStore.user))
    }
    saveMsg.value = '头像更新成功'
    saveSuccess.value = true
    setTimeout(() => { saveMsg.value = '' }, 3000)
  } catch (err: any) {
    const msg = err?.response?.data?.message || '头像上传失败'
    saveMsg.value = msg
    saveSuccess.value = false
    console.error('Avatar upload failed:', err)
  } finally {
    uploading.value = false
  }
}

function handleClearAvatar() {
  clearDialogVisible.value = true
}

async function confirmClearAvatar() {
  clearDialogVisible.value = false
  try {
    await clearAvatar()
    avatarUrl.value = ''
    if (authStore.user) {
      authStore.user.avatarUrl = ''
      localStorage.setItem('user', JSON.stringify(authStore.user))
    }
    saveMsg.value = '头像已清空'
    saveSuccess.value = true
    setTimeout(() => { saveMsg.value = '' }, 3000)
  } catch (err) {
    saveMsg.value = '清空头像失败'
    saveSuccess.value = false
    console.error('Clear avatar failed:', err)
  }
}

async function saveAll() {
  saveMsg.value = ''
  try {
    // Update user info (nickname, email)
    const userRes = await updateUserInfo({
      nickname: form.nickname,
      email: form.email,
    })
    const updatedUser = userRes.data as User
    // Sync to local store
    if (authStore.user && updatedUser) {
      authStore.user.nickname = updatedUser.nickname
      authStore.user.email = updatedUser.email
      localStorage.setItem('user', JSON.stringify(authStore.user))
    }

    // Update profile (gender, age, domain) - need to get current profile first
    try {
      const profileRes = await getCurrentProfile()
      const currentProfile = profileRes.data as StudentProfile
      const learningBehavior = currentProfile?.learningBehavior
        ? (typeof currentProfile.learningBehavior === 'string'
          ? currentProfile.learningBehavior
          : JSON.stringify(currentProfile.learningBehavior))
        : null

      await updateProfile({
        gender: form.gender || null,
        age: form.age || null,
        domain: form.domain || null,
        learningBehavior,
      })
    } catch {
      // No profile yet - create one
      await updateProfile({
        gender: form.gender || null,
        age: form.age || null,
        domain: form.domain || null,
      })
    }

    saveMsg.value = '保存成功'
    saveSuccess.value = true
    setTimeout(() => { saveMsg.value = '' }, 3000)
  } catch (e) {
    saveMsg.value = '保存失败，请重试'
    saveSuccess.value = false
    console.error('Save failed:', e)
  }
}

onMounted(loadUser)
</script>

<style scoped>
.animate-scale-in {
  animation: scaleIn 0.2s ease-out;
}

@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
