<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="section-title">知识库管理</h1>
      <button class="btn-primary text-sm" @click="showUpload = true">上传文档</button>
    </div>
    <div class="card p-6">
      <p class="text-navy-400 text-sm">管理AI知识库中的文档资源</p>
    </div>
    <Teleport to="body">
      <div v-if="showUpload" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" @click.self="showUpload = false">
        <div class="card w-full max-w-md p-6">
          <h3 class="font-display text-lg font-semibold text-navy-800 mb-4">上传知识库文档</h3>
          <div class="border-2 border-dashed border-navy-200 rounded-xl p-8 text-center">
            <p class="text-navy-400">拖拽文件到此处或点击选择</p>
          </div>
          <div class="flex justify-end gap-2 mt-4">
            <button class="btn-ghost text-sm" @click="showUpload = false">取消</button>
            <button class="btn-primary text-sm">上传</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
const showUpload = ref(false)
</script>
