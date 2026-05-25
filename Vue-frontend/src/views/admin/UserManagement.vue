<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <h1 class="section-title">用户管理</h1>
      <button class="btn-primary flex items-center gap-2" @click="openCreateModal">
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        新增用户
      </button>
    </div>

    <!-- Filter Bar -->
    <div class="card p-4 mb-4">
      <div class="flex flex-wrap items-center gap-3">
        <div class="relative flex-1 min-w-[220px]">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input
            v-model="filters.keyword"
            type="text"
            class="input-field pl-10"
            placeholder="搜索用户名、昵称、邮箱..."
            @input="debouncedSearch"
          />
        </div>
        <!-- Role Dropdown -->
        <div class="custom-dropdown" v-click-outside="() => roleDropdownOpen = false">
          <button
            class="dropdown-trigger"
            :class="{ 'has-value': filters.role }"
            @click="roleDropdownOpen = !roleDropdownOpen"
          >
            <svg class="w-4 h-4 text-navy-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
            </svg>
            <span>{{ roleLabel }}</span>
            <svg class="w-4 h-4 text-navy-300 transition-transform" :class="{ 'rotate-180': roleDropdownOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
          </button>
          <transition name="dropdown">
            <div v-if="roleDropdownOpen" class="dropdown-menu">
              <button
                v-for="opt in roleOptions"
                :key="opt.value"
                class="dropdown-item"
                :class="{ 'active': filters.role === opt.value }"
                @click="filters.role = opt.value; roleDropdownOpen = false; loadUsers(1)"
              >
                <span v-if="opt.color" class="w-2 h-2 rounded-full" :class="opt.color" />
                <span>{{ opt.label }}</span>
                <svg v-if="filters.role === opt.value" class="w-4 h-4 ml-auto text-navy-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
              </button>
            </div>
          </transition>
        </div>

        <!-- Status Dropdown -->
        <div class="custom-dropdown" v-click-outside="() => statusDropdownOpen = false">
          <button
            class="dropdown-trigger"
            :class="{ 'has-value': filters.status !== null }"
            @click="statusDropdownOpen = !statusDropdownOpen"
          >
            <svg class="w-4 h-4 text-navy-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
            <span>{{ statusLabel }}</span>
            <svg class="w-4 h-4 text-navy-300 transition-transform" :class="{ 'rotate-180': statusDropdownOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
          </button>
          <transition name="dropdown">
            <div v-if="statusDropdownOpen" class="dropdown-menu">
              <button
                v-for="opt in statusOptions"
                :key="String(opt.value)"
                class="dropdown-item"
                :class="{ 'active': filters.status === opt.value }"
                @click="filters.status = opt.value; statusDropdownOpen = false; loadUsers(1)"
              >
                <span v-if="opt.color" class="w-2 h-2 rounded-full" :class="opt.color" />
                <span>{{ opt.label }}</span>
                <svg v-if="filters.status === opt.value" class="w-4 h-4 ml-auto text-navy-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
              </button>
            </div>
          </transition>
        </div>
        <button class="btn-ghost text-sm" @click="resetFilters">
          <svg class="w-4 h-4 inline mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
          重置
        </button>
      </div>
    </div>

    <!-- Batch Action Bar -->
    <transition name="slide-bar">
      <div v-if="selectedIds.length > 0" class="card p-3 mb-4 bg-navy-50/80 border-navy-200 flex items-center gap-4">
        <span class="text-sm text-navy-600 font-medium">已选 {{ selectedIds.length }} 项</span>
        <div class="h-4 w-px bg-navy-200" />
        <button class="btn-ghost text-sm text-emerald-600 hover:bg-emerald-50" @click="batchEnable">
          <svg class="w-4 h-4 inline mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
          批量启用
        </button>
        <button class="btn-ghost text-sm text-amber-600 hover:bg-amber-50" @click="batchDisable">
          <svg class="w-4 h-4 inline mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
          批量禁用
        </button>
        <button class="btn-ghost text-sm text-red-500 hover:bg-red-50" @click="batchDelete">
          <svg class="w-4 h-4 inline mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          批量删除
        </button>
        <button class="ml-auto btn-ghost text-xs text-navy-400" @click="selectedIds = []">取消选择</button>
      </div>
    </transition>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div v-if="loading" class="p-12 text-center">
        <div class="inline-block w-8 h-8 border-2 border-navy-200 border-t-navy-600 rounded-full animate-spin" />
        <p class="text-sm text-navy-400 mt-3">加载中...</p>
      </div>

      <template v-else-if="users.length > 0">
        <table class="w-full">
          <thead>
            <tr class="border-b border-navy-100 bg-navy-50/50">
              <th class="px-4 py-3 w-10">
                <input type="checkbox" :checked="allSelected" @change="toggleSelectAll" class="rounded border-navy-300 text-navy-600 focus:ring-navy-200" />
              </th>
              <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">用户</th>
              <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">角色</th>
              <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">状态</th>
              <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">邮箱</th>
              <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">最近登录</th>
              <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">注册时间</th>
              <th class="px-5 py-3 text-right text-xs font-semibold text-navy-500 uppercase tracking-wider">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(u, idx) in users"
              :key="u.id"
              class="border-b border-navy-50 hover:bg-navy-50/30 transition-colors group animate-row"
              :style="{ animationDelay: `${idx * 40}ms` }"
              :class="{ 'bg-navy-50/50': selectedIds.includes(u.id) }"
            >
              <td class="px-4 py-4">
                <input type="checkbox" :checked="selectedIds.includes(u.id)" @change="toggleSelect(u.id)" class="rounded border-navy-300 text-navy-600 focus:ring-navy-200" />
              </td>
              <td class="px-5 py-4">
                <div class="flex items-center gap-3">
                  <div class="w-9 h-9 rounded-full flex items-center justify-center text-white text-sm font-bold shadow-sm"
                    :class="u.avatarUrl ? '' : 'bg-gradient-to-br from-sage-400 to-sage-600'"
                  >
                    <img v-if="u.avatarUrl" :src="u.avatarUrl" class="w-full h-full rounded-full object-cover" />
                    <span v-else>{{ (u.nickname || u.loginName)[0] }}</span>
                  </div>
                  <div>
                    <p class="text-sm font-medium text-navy-800">{{ u.nickname || u.loginName }}</p>
                    <p class="text-xs text-navy-400">@{{ u.loginName }}</p>
                  </div>
                </div>
              </td>
              <td class="px-5 py-4">
                <button
                  class="badge cursor-pointer transition-all hover:scale-105"
                  :class="u.role === 'admin' ? 'bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100' : 'bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100'"
                  @click="quickToggleRole(u)"
                  :title="'点击切换为' + (u.role === 'admin' ? '学生' : '管理员')"
                >
                  {{ u.role === 'admin' ? '管理员' : '学生' }}
                </button>
              </td>
              <td class="px-5 py-4">
                <button
                  class="badge cursor-pointer transition-all hover:scale-105"
                  :class="u.status === 1 ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100' : 'bg-red-50 text-red-700 border border-red-200 hover:bg-red-100'"
                  @click="quickToggleStatus(u)"
                  :title="'点击' + (u.status === 1 ? '禁用' : '启用')"
                >
                  <span class="w-1.5 h-1.5 rounded-full mr-1.5" :class="u.status === 1 ? 'bg-emerald-500' : 'bg-red-500'" />
                  {{ u.status === 1 ? '正常' : '禁用' }}
                </button>
              </td>
              <td class="px-5 py-4 text-sm text-navy-500">{{ u.email || '—' }}</td>
              <td class="px-5 py-4 text-sm text-navy-400">{{ formatTime(u.lastLoginTime) }}</td>
              <td class="px-5 py-4 text-sm text-navy-400">{{ formatTime(u.createdAt) }}</td>
              <td class="px-5 py-4">
                <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button class="p-1.5 rounded-lg hover:bg-navy-100 text-navy-400 hover:text-navy-700 transition-colors" title="编辑" @click="openEditModal(u)">
                    <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                  </button>
                  <button class="p-1.5 rounded-lg hover:bg-red-50 text-navy-400 hover:text-red-500 transition-colors" title="删除" @click="confirmDelete(u)">
                    <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
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
              @click="loadUsers(currentPage - 1)"
            >
              上一页
            </button>
            <button
              v-for="p in visiblePages"
              :key="p"
              class="w-9 h-9 rounded-lg text-sm font-medium transition-colors"
              :class="p === currentPage ? 'bg-navy-600 text-white shadow-sm' : 'text-navy-600 hover:bg-navy-50'"
              @click="loadUsers(p)"
            >
              {{ p }}
            </button>
            <button
              class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
              :class="currentPage < totalPages ? 'text-navy-600 hover:bg-navy-50' : 'text-navy-300 cursor-not-allowed'"
              :disabled="currentPage >= totalPages"
              @click="loadUsers(currentPage + 1)"
            >
              下一页
            </button>
          </div>
        </div>
      </template>

      <!-- Empty State -->
      <div v-else class="p-16 text-center">
        <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-navy-50 flex items-center justify-center">
          <svg class="w-8 h-8 text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
          </svg>
        </div>
        <p class="text-navy-500 font-medium">暂无用户数据</p>
        <p class="text-sm text-navy-400 mt-1">点击"新增用户"创建第一个账户</p>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="showModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="closeModal" />
          <div class="relative bg-white rounded-2xl shadow-2xl w-[520px] max-w-[90vw] max-h-[85vh] overflow-y-auto animate-modal-in">
            <!-- Modal Header -->
            <div class="sticky top-0 bg-white px-6 pt-6 pb-4 border-b border-navy-100 rounded-t-2xl z-10">
              <div class="flex items-center justify-between">
                <h2 class="text-lg font-display font-bold text-navy-800">{{ editingUser ? '编辑用户' : '新增用户' }}</h2>
                <button class="p-1.5 rounded-lg hover:bg-navy-50 text-navy-400 transition-colors" @click="closeModal">
                  <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
              </div>
            </div>

            <!-- Modal Body -->
            <form @submit.prevent="handleSubmit" class="px-6 py-5 space-y-4">
              <div v-if="formError" class="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-600">
                {{ formError }}
              </div>

              <!-- Login Name -->
              <div>
                <label class="block text-sm font-medium text-navy-700 mb-1.5">登录名 <span class="text-red-400">*</span></label>
                <input
                  v-model="form.loginName"
                  type="text"
                  class="input-field"
                  :class="{ 'border-red-300 focus:border-red-400 focus:ring-red-100': formErrors.loginName }"
                  placeholder="请输入登录名"
                  :disabled="!!editingUser"
                />
                <p v-if="formErrors.loginName" class="text-xs text-red-500 mt-1">{{ formErrors.loginName }}</p>
              </div>

              <!-- Password -->
              <div v-if="!editingUser">
                <label class="block text-sm font-medium text-navy-700 mb-1.5">密码 <span class="text-red-400">*</span></label>
                <input
                  v-model="form.password"
                  type="password"
                  class="input-field"
                  :class="{ 'border-red-300 focus:border-red-400 focus:ring-red-100': formErrors.password }"
                  placeholder="请输入密码（至少6位）"
                />
                <p v-if="formErrors.password" class="text-xs text-red-500 mt-1">{{ formErrors.password }}</p>
              </div>
              <div v-else>
                <label class="block text-sm font-medium text-navy-700 mb-1.5">重置密码</label>
                <input
                  v-model="form.password"
                  type="password"
                  class="input-field"
                  placeholder="留空则不修改密码"
                />
              </div>

              <!-- Nickname -->
              <div>
                <label class="block text-sm font-medium text-navy-700 mb-1.5">昵称</label>
                <input v-model="form.nickname" type="text" class="input-field" placeholder="请输入昵称" />
              </div>

              <!-- Email -->
              <div>
                <label class="block text-sm font-medium text-navy-700 mb-1.5">邮箱</label>
                <input
                  v-model="form.email"
                  type="email"
                  class="input-field"
                  :class="{ 'border-red-300 focus:border-red-400 focus:ring-red-100': formErrors.email }"
                  placeholder="请输入邮箱"
                />
                <p v-if="formErrors.email" class="text-xs text-red-500 mt-1">{{ formErrors.email }}</p>
              </div>

              <!-- Role -->
              <div>
                <label class="block text-sm font-medium text-navy-700 mb-2">角色</label>
                <div class="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    class="role-card"
                    :class="form.role === 'student' ? 'role-card-active-blue' : 'role-card-inactive'"
                    @click="form.role = 'student'"
                  >
                    <div class="role-card-icon" :class="form.role === 'student' ? 'bg-blue-100 text-blue-600' : 'bg-navy-100 text-navy-400'">
                      <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                        <path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c0 1.66 2.69 3 6 3s6-1.34 6-3v-5"/>
                      </svg>
                    </div>
                    <span class="font-medium text-sm">学生</span>
                    <span class="text-xs opacity-60">学习者</span>
                  </button>
                  <button
                    type="button"
                    class="role-card"
                    :class="form.role === 'admin' ? 'role-card-active-purple' : 'role-card-inactive'"
                    @click="form.role = 'admin'"
                  >
                    <div class="role-card-icon" :class="form.role === 'admin' ? 'bg-purple-100 text-purple-600' : 'bg-navy-100 text-navy-400'">
                      <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                        <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
                      </svg>
                    </div>
                    <span class="font-medium text-sm">管理员</span>
                    <span class="text-xs opacity-60">系统管理</span>
                  </button>
                </div>
              </div>

              <!-- Status -->
              <div>
                <label class="block text-sm font-medium text-navy-700 mb-2">状态</label>
                <div class="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    class="role-card"
                    :class="form.status === 1 ? 'role-card-active-green' : 'role-card-inactive'"
                    @click="form.status = 1"
                  >
                    <div class="role-card-icon" :class="form.status === 1 ? 'bg-emerald-100 text-emerald-600' : 'bg-navy-100 text-navy-400'">
                      <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
                      </svg>
                    </div>
                    <span class="font-medium text-sm">正常</span>
                    <span class="text-xs opacity-60">可登录</span>
                  </button>
                  <button
                    type="button"
                    class="role-card"
                    :class="form.status === 0 ? 'role-card-active-red' : 'role-card-inactive'"
                    @click="form.status = 0"
                  >
                    <div class="role-card-icon" :class="form.status === 0 ? 'bg-red-100 text-red-600' : 'bg-navy-100 text-navy-400'">
                      <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                        <circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>
                      </svg>
                    </div>
                    <span class="font-medium text-sm">禁用</span>
                    <span class="text-xs opacity-60">不可登录</span>
                  </button>
                </div>
              </div>

              <!-- Submit -->
              <div class="pt-2 flex gap-3">
                <button type="button" class="btn-secondary flex-1" @click="closeModal">取消</button>
                <button type="submit" class="btn-primary flex-1" :disabled="submitting">
                  <span v-if="submitting" class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                  {{ editingUser ? '保存修改' : '创建用户' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Delete Confirmation -->
    <ConfirmDialog
      :visible="showDeleteConfirm"
      :title="deletingUser ? '删除用户' : '批量删除'"
      :message="deletingUser
        ? `确定要删除用户「${deletingUser.nickname || deletingUser.loginName}」吗？该操作将删除该用户的所有数据且不可恢复。`
        : `确定要删除选中的 ${selectedIds.length} 个用户吗？该操作不可恢复。`"
      confirm-text="确认删除"
      cancel-text="取消"
      type="danger"
      @confirm="handleDelete"
      @cancel="showDeleteConfirm = false"
    />

    <!-- Role Change Confirmation -->
    <ConfirmDialog
      :visible="showRoleConfirm"
      title="切换角色"
      :message="roleChangeUser
        ? `确定要将「${roleChangeUser.nickname || roleChangeUser.loginName}」的角色切换为${roleChangeUser.role === 'admin' ? '学生' : '管理员'}吗？`
        : ''"
      confirm-text="确认切换"
      cancel-text="取消"
      @confirm="handleRoleChange"
      @cancel="showRoleConfirm = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { User } from '@/types/user'
import {
  getUsers, createUser, updateUser, deleteUser as apiDeleteUser,
  toggleUserStatus, changeUserRole, batchToggleStatus, batchDeleteUsers,
} from '@/api/admin'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

// Click-outside directive
const vClickOutside = {
  mounted(el: HTMLElement, binding: any) {
    el._clickOutside = (e: MouseEvent) => {
      if (!el.contains(e.target as Node)) binding.value(e)
    }
    document.addEventListener('click', el._clickOutside)
  },
  unmounted(el: HTMLElement) {
    document.removeEventListener('click', el._clickOutside)
  },
}

// ========== State ==========
const users = ref<User[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const selectedIds = ref<number[]>([])
const filters = ref({ keyword: '', role: '', status: null as number | null })

// Modal
const showModal = ref(false)
const editingUser = ref<User | null>(null)
const submitting = ref(false)
const formError = ref('')
const formErrors = ref<Record<string, string>>({})
const form = ref({
  loginName: '',
  password: '',
  nickname: '',
  email: '',
  role: 'student',
  status: 1,
})

// Delete
const showDeleteConfirm = ref(false)
const deletingUser = ref<User | null>(null)
const isBatchDelete = ref(false)

// Role
const showRoleConfirm = ref(false)
const roleChangeUser = ref<User | null>(null)

// Dropdowns
const roleDropdownOpen = ref(false)
const statusDropdownOpen = ref(false)

const roleOptions = [
  { value: '', label: '全部角色', color: null },
  { value: 'admin', label: '管理员', color: 'bg-purple-500' },
  { value: 'student', label: '学生', color: 'bg-blue-500' },
]
const statusOptions = [
  { value: null, label: '全部状态', color: null },
  { value: 1, label: '正常', color: 'bg-emerald-500' },
  { value: 0, label: '禁用', color: 'bg-red-500' },
]

const roleLabel = computed(() => roleOptions.find(o => o.value === filters.value.role)?.label || '全部角色')
const statusLabel = computed(() => statusOptions.find(o => o.value === filters.value.status)?.label || '全部状态')

// ========== Computed ==========
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const allSelected = computed(() =>
  users.value.length > 0 && users.value.every(u => selectedIds.value.includes(u.id))
)

const visiblePages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

// ========== Data Loading ==========
let searchTimer: ReturnType<typeof setTimeout> | null = null

function debouncedSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadUsers(1), 300)
}

async function loadUsers(page: number) {
  if (page < 1 || (totalPages.value > 1 && page > totalPages.value)) return
  loading.value = true
  currentPage.value = page
  try {
    const res = await getUsers({
      page,
      size: pageSize.value,
      keyword: filters.value.keyword || undefined,
      role: filters.value.role || undefined,
      status: filters.value.status,
    })
    const data = (res as any).data ?? res
    users.value = data.records ?? []
    total.value = data.total ?? 0
  } catch (e: any) {
    console.error('加载用户列表失败:', e)
    users.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.value = { keyword: '', role: '', status: null }
  loadUsers(1)
}

// ========== Selection ==========
function toggleSelect(id: number) {
  const idx = selectedIds.value.indexOf(id)
  if (idx === -1) selectedIds.value.push(id)
  else selectedIds.value.splice(idx, 1)
}

function toggleSelectAll() {
  if (allSelected.value) {
    selectedIds.value = []
  } else {
    selectedIds.value = users.value.map(u => u.id)
  }
}

// ========== Quick Actions ==========
function quickToggleStatus(user: User) {
  showDeleteConfirm.value = false
  showRoleConfirm.value = false
  // Direct toggle without confirmation
  toggleUserStatus(user.id).then(() => {
    user.status = user.status === 1 ? 0 : 1
  }).catch(e => {
    console.error('切换状态失败:', e)
  })
}

function quickToggleRole(user: User) {
  roleChangeUser.value = user
  showRoleConfirm.value = true
}

async function handleRoleChange() {
  if (!roleChangeUser.value) return
  const newRole = roleChangeUser.value.role === 'admin' ? 'student' : 'admin'
  try {
    await changeUserRole(roleChangeUser.value.id, newRole)
    roleChangeUser.value.role = newRole as 'student' | 'admin'
  } catch (e: any) {
    console.error('切换角色失败:', e)
  } finally {
    showRoleConfirm.value = false
    roleChangeUser.value = null
  }
}

// ========== Create/Edit Modal ==========
function openCreateModal() {
  editingUser.value = null
  form.value = { loginName: '', password: '', nickname: '', email: '', role: 'student', status: 1 }
  formError.value = ''
  formErrors.value = {}
  showModal.value = true
}

function openEditModal(user: User) {
  editingUser.value = user
  form.value = {
    loginName: user.loginName,
    password: '',
    nickname: user.nickname || '',
    email: user.email || '',
    role: user.role,
    status: user.status,
  }
  formError.value = ''
  formErrors.value = {}
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  editingUser.value = null
  formError.value = ''
  formErrors.value = {}
}

function validateForm(): boolean {
  formErrors.value = {}
  if (!editingUser.value && !form.value.loginName.trim()) {
    formErrors.value.loginName = '登录名不能为空'
  }
  if (!editingUser.value && form.value.password.length < 6) {
    formErrors.value.password = '密码至少需要6位'
  }
  if (form.value.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.email)) {
    formErrors.value.email = '邮箱格式不正确'
  }
  return Object.keys(formErrors.value).length === 0
}

async function handleSubmit() {
  if (!validateForm()) return
  submitting.value = true
  formError.value = ''
  try {
    if (editingUser.value) {
      const updateData: any = {
        nickname: form.value.nickname,
        email: form.value.email,
        role: form.value.role,
        status: form.value.status,
      }
      if (form.value.password) updateData.password = form.value.password
      const res = await updateUser(editingUser.value.id, updateData)
      const data = (res as any).data ?? res
      // 更新列表中的用户数据
      const idx = users.value.findIndex(u => u.id === editingUser.value!.id)
      if (idx !== -1 && data) {
        Object.assign(users.value[idx], data)
      }
    } else {
      await createUser({
        loginName: form.value.loginName,
        password: form.value.password,
        nickname: form.value.nickname,
        email: form.value.email,
        role: form.value.role,
        status: form.value.status,
      })
    }
    closeModal()
    loadUsers(currentPage.value)
  } catch (e: any) {
    formError.value = e.message || '操作失败，请重试'
  } finally {
    submitting.value = false
  }
}

// ========== Delete ==========
function confirmDelete(user: User) {
  isBatchDelete.value = false
  deletingUser.value = user
  showDeleteConfirm.value = true
}

function batchDelete() {
  isBatchDelete.value = true
  deletingUser.value = null
  showDeleteConfirm.value = true
}

async function handleDelete() {
  try {
    if (isBatchDelete.value) {
      await batchDeleteUsers(selectedIds.value)
      selectedIds.value = []
    } else if (deletingUser.value) {
      await apiDeleteUser(deletingUser.value.id)
    }
    showDeleteConfirm.value = false
    deletingUser.value = null
    loadUsers(currentPage.value)
  } catch (e: any) {
    console.error('删除失败:', e)
  }
}

// ========== Batch Actions ==========
async function batchEnable() {
  try {
    await batchToggleStatus(selectedIds.value, 1)
    selectedIds.value = []
    loadUsers(currentPage.value)
  } catch (e: any) {
    console.error('批量启用失败:', e)
  }
}

async function batchDisable() {
  try {
    await batchToggleStatus(selectedIds.value, 0)
    selectedIds.value = []
    loadUsers(currentPage.value)
  } catch (e: any) {
    console.error('批量禁用失败:', e)
  }
}

// ========== Utils ==========
function formatTime(time: string | null | undefined): string {
  if (!time) return '—'
  const d = new Date(time)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// ========== Lifecycle ==========
onMounted(() => loadUsers(1))
</script>

<style scoped>
.animate-row {
  animation: fadeInUp 0.4s ease-out forwards;
  opacity: 0;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-modal-in {
  animation: modalIn 0.25s ease-out;
}

@keyframes modalIn {
  from { opacity: 0; transform: scale(0.95) translateY(8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.slide-bar-enter-active { transition: all 0.3s ease-out; }
.slide-bar-leave-active { transition: all 0.2s ease-in; }
.slide-bar-enter-from { opacity: 0; transform: translateY(-8px); }
.slide-bar-leave-to { opacity: 0; transform: translateY(-8px); }

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* Custom Dropdown */
.custom-dropdown {
  position: relative;
}

.dropdown-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  min-width: 130px;
  background: white;
  border: 1.5px dashed #c8d6e0;
  border-radius: 10px;
  font-size: 0.875rem;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.dropdown-trigger:hover {
  border-color: #94a3b8;
  background: #f8fafc;
}

.dropdown-trigger.has-value {
  color: #1e293b;
  border-color: #94a3b8;
  border-style: solid;
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  min-width: 100%;
  background: white;
  border: 1.5px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08), 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 4px;
  z-index: 50;
  overflow: hidden;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 0.875rem;
  color: #475569;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
  font-family: inherit;
}

.dropdown-item:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.dropdown-item.active {
  background: #f1f5f9;
  color: #1e293b;
  font-weight: 500;
}

/* Dropdown transition */
.dropdown-enter-active { transition: all 0.2s ease-out; }
.dropdown-leave-active { transition: all 0.15s ease-in; }
.dropdown-enter-from { opacity: 0; transform: translateY(-6px) scale(0.98); }
.dropdown-leave-to { opacity: 0; transform: translateY(-4px) scale(0.98); }

/* Role Cards (Modal) */
.role-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 16px 12px;
  border-radius: 12px;
  border: 2px solid #e2e8f0;
  background: white;
  cursor: pointer;
  transition: all 0.25s ease;
  position: relative;
  overflow: hidden;
}

.role-card::before {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0;
  transition: opacity 0.25s ease;
  border-radius: 10px;
}

.role-card:hover {
  border-color: #cbd5e1;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.role-card-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s ease;
}

.role-card-inactive {
  border-color: #e2e8f0;
}

.role-card-inactive:hover {
  border-color: #cbd5e1;
}

.role-card-active-blue {
  border-color: #60a5fa;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.15);
}

.role-card-active-purple {
  border-color: #a78bfa;
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15);
}

.role-card-active-green {
  border-color: #34d399;
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  box-shadow: 0 0 0 3px rgba(52, 211, 153, 0.15);
}

.role-card-active-red {
  border-color: #f87171;
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
  box-shadow: 0 0 0 3px rgba(248, 113, 113, 0.15);
}
</style>
