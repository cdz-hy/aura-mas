<template>
  <Teleport to="body">
    <transition name="fade">
      <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('cancel')" />

        <!-- Dialog -->
        <div class="relative bg-white rounded-2xl shadow-2xl w-[480px] max-w-[90vw] overflow-hidden animate-scale-in">
          <div class="px-6 pt-5 pb-3">
            <h3 class="text-lg font-semibold text-navy-800">裁剪头像</h3>
            <p class="text-sm text-navy-400 mt-1">拖动或缩放调整裁剪区域，输出为 1:1 正方形</p>
          </div>

          <!-- Cropper area -->
          <div class="px-6">
            <div class="w-full aspect-square rounded-xl overflow-hidden border border-navy-100 bg-navy-50">
              <Cropper
                ref="cropperRef"
                class="w-full h-full"
                :src="imageSrc"
                :stencil-props="{ aspectRatio: 1 }"
                :resize-image="{ adjustStencil: false }"
                image-restriction="stencil"
              />
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center justify-between px-6 py-4 mt-2 border-t border-navy-100">
            <p class="text-xs text-navy-300">裁剪后将压缩为 1MB 以内</p>
            <div class="flex gap-3">
              <button
                class="px-5 py-2 rounded-lg text-sm text-navy-600 border border-navy-200 hover:bg-navy-50 transition-colors"
                @click="$emit('cancel')"
              >
                取消
              </button>
              <button
                class="px-5 py-2 rounded-lg text-sm text-white bg-navy-600 hover:bg-navy-700 transition-colors font-medium disabled:opacity-50"
                :disabled="processing"
                @click="handleCrop"
              >
                {{ processing ? '处理中...' : '确认上传' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Cropper } from 'vue-advanced-cropper'
import 'vue-advanced-cropper/dist/style.css'

const props = defineProps<{
  visible: boolean
  imageSrc: string
}>()

const emit = defineEmits<{
  (e: 'cancel'): void
  (e: 'cropped', file: File): void
}>()

const cropperRef = ref<InstanceType<typeof Cropper>>()
const processing = ref(false)

const MAX_SIZE = 1024 * 1024 // 1MB
const OUTPUT_SIZE = 512 // output 512x512

async function handleCrop() {
  if (!cropperRef.value) return
  processing.value = true

  try {
    const { canvas } = cropperRef.value.getResult()
    if (!canvas) return

    // Draw to output canvas at fixed size
    const output = document.createElement('canvas')
    output.width = OUTPUT_SIZE
    output.height = OUTPUT_SIZE
    const ctx = output.getContext('2d')!
    ctx.drawImage(canvas, 0, 0, OUTPUT_SIZE, OUTPUT_SIZE)

    // Try WebP first (smaller), fall back to JPEG
    let blob = await canvasToBlob(output, 'image/webp', 0.9)
    if (!blob || blob.size > MAX_SIZE) {
      // Try JPEG with lower quality
      let quality = 0.85
      while (quality >= 0.3) {
        blob = await canvasToBlob(output, 'image/jpeg', quality)
        if (blob && blob.size <= MAX_SIZE) break
        quality -= 0.1
      }
    }

    if (!blob) {
      alert('图片处理失败，请重试')
      return
    }

    if (blob.size > MAX_SIZE) {
      alert('图片压缩后仍超过 1MB，请选择更小的图片')
      return
    }

    const ext = blob.type === 'image/webp' ? 'webp' : 'jpg'
    const file = new File([blob], `avatar.${ext}`, { type: blob.type })
    emit('cropped', file)
  } catch (e) {
    console.error('Crop failed:', e)
    alert('裁剪失败，请重试')
  } finally {
    processing.value = false
  }
}

function canvasToBlob(canvas: HTMLCanvasElement, type: string, quality: number): Promise<Blob | null> {
  return new Promise(resolve => canvas.toBlob(resolve, type, quality))
}

watch(() => props.visible, (val) => {
  if (val) processing.value = false
})
</script>

<style scoped>
.animate-scale-in {
  animation: scaleIn 0.2s ease-out;
}

@keyframes scaleIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
