<template>
  <div>
    <h1 class="section-title mb-6">用户管理</h1>
    <div class="card overflow-hidden">
      <table class="w-full">
        <thead>
          <tr class="border-b border-navy-100 bg-navy-50/50">
            <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">用户</th>
            <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">角色</th>
            <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">状态</th>
            <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">注册时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id" class="border-b border-navy-50 hover:bg-navy-50/30 transition-colors">
            <td class="px-5 py-4">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-full bg-gradient-to-br from-sage-400 to-sage-600 flex items-center justify-center text-white text-sm font-bold">
                  {{ u.nickname[0] }}
                </div>
                <div>
                  <p class="text-sm font-medium text-navy-800">{{ u.nickname }}</p>
                  <p class="text-xs text-navy-400">{{ u.loginName }}</p>
                </div>
              </div>
            </td>
            <td class="px-5 py-4">
              <span class="badge" :class="u.role === 'admin' ? 'bg-purple-50 text-purple-700' : 'bg-blue-50 text-blue-700'">
                {{ u.role === 'admin' ? '管理员' : '学生' }}
              </span>
            </td>
            <td class="px-5 py-4">
              <span class="badge" :class="u.status === 1 ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'">
                {{ u.status === 1 ? '正常' : '禁用' }}
              </span>
            </td>
            <td class="px-5 py-4 text-sm text-navy-500">{{ u.createdAt }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const users = ref([
  { id: 1, loginName: 'admin', nickname: '管理员', role: 'admin', status: 1, createdAt: '2026-01-01' },
  { id: 2, loginName: 'student1', nickname: '张三', role: 'student', status: 1, createdAt: '2026-03-15' },
])
</script>
