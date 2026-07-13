import { expect, test, type Page, type Route } from '@playwright/test'

// ─── Mock Data ────────────────────────────────────────────────────────

const MOCK_USER = {
  id: 1,
  loginName: 'testuser',
  username: '测试用户',
  role: 'user',
}

const MOCK_MENUS = [
  { id: 1, name: '仪表盘', code: 'dashboard', path: '/dashboard', icon: 'dashboard', children: [] },
  { id: 2, name: '学习计划', code: 'plan-list', path: '/plan', icon: 'plan', children: [] },
  { id: 3, name: '我的笔记', code: 'note-list', path: '/notes', icon: 'note', children: [] },
]

const NOTE_ID = 12

const MOCK_NOTES = [
  {
    id: NOTE_ID,
    userId: 1,
    noteName: '线性回归笔记',
    content: '## 线性回归\n![图](lr.png)\n<<A:1|重点|最小二乘>>正文段落',
    tags: [],
    isPinned: 0,
    noteType: 'quick',
    organizeStatus: 'pending',
    createdAt: '2025-01-01T00:00:00Z',
    updatedAt: '2025-01-01T00:00:00Z',
  },
  {
    id: 13,
    userId: 1,
    noteName: '逻辑回归笔记',
    content: '逻辑回归用于分类',
    tags: [],
    isPinned: 0,
    noteType: 'quick',
    organizeStatus: 'organized',
    createdAt: '2025-01-02T00:00:00Z',
    updatedAt: '2025-01-02T00:00:00Z',
  },
  {
    // Legacy note without capture metadata
    id: 14,
    userId: 1,
    noteName: '旧笔记',
    content: '没有元数据的旧笔记',
    tags: [],
    isPinned: 0,
    createdAt: '2025-01-01T00:00:00Z',
    updatedAt: '2025-01-01T00:00:00Z',
  },
]

const MOCK_RESOURCES = [
  {
    id: 1,
    noteId: NOTE_ID,
    resourceId: 3,
    planId: 4,
    moduleName: '基础',
    resourceTitle: '线性回归',
  },
]

const DRAFT_STORAGE_KEY = 'aura.note-sidebar.new-draft.v1'

// ─── Helpers ──────────────────────────────────────────────────────────

async function setupAuth(page: Page) {
  await page.addInitScript(([token, user, menus]) => {
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(user))
    localStorage.setItem('menus', JSON.stringify(menus))
  }, ['fake-jwt-token', MOCK_USER, MOCK_MENUS])
}

function javaEnvelope(data: unknown) {
  return { code: 200, data }
}

async function mockNoteApi(
  page: Page,
  options: {
    capturedKeyword: { value: string }
    putStatus: (() => number) | number
    postStatus?: number
    notes?: typeof MOCK_NOTES
    onCreate?: (body: Record<string, unknown>) => void
    onUpdate?: (body: Record<string, unknown>) => void
  },
) {
  const notes = options.notes ?? MOCK_NOTES

  await page.route('**/api/user/info', route =>
    route.fulfill({ json: javaEnvelope(MOCK_USER) }),
  )

  await page.route('**/api/plan/**', route =>
    route.fulfill({ json: javaEnvelope({ records: [], total: 0 }) }),
  )
  await page.route('**/api/stats/**', route =>
    route.fulfill({ json: javaEnvelope({ totalPlans: 0, completedPlans: 0, totalResources: 0, totalStudyHours: 0, weeklyMinutes: [], recentActivity: [] }) }),
  )
  await page.route('**/api/tracker/**', route =>
    route.fulfill({ json: javaEnvelope(0) }),
  )
  await page.route('**/api/dialogue/**', route =>
    route.fulfill({ json: javaEnvelope([]) }),
  )
  await page.route('**/api/flashcard/**', route =>
    route.fulfill({ json: javaEnvelope([]) }),
  )
  await page.route('**/api/ticket/**', route =>
    route.fulfill({ json: javaEnvelope({ ticket: 'fake-ticket' }) }),
  )

  await page.route('**/api/note/list**', (route: Route) => {
    const url = new URL(route.request().url())
    const keyword = url.searchParams.get('keyword') ?? ''
    options.capturedKeyword.value = keyword
    const filtered = keyword
      ? notes.filter(n =>
          n.noteName.includes(keyword) || n.content.includes(keyword),
        )
      : notes
    route.fulfill({ json: javaEnvelope({ records: filtered, total: filtered.length }) })
  })

  await page.route('**/api/note/*/resources', route => {
    const resources = route.request().url().includes(`/note/${NOTE_ID}/resources`)
      ? MOCK_RESOURCES
      : []
    route.fulfill({ json: javaEnvelope(resources) })
  })

  await page.route('**/api/note', route => {
    if (route.request().method() !== 'POST') return route.continue()
    if ((options.postStatus ?? 200) >= 500) {
      return route.fulfill({ status: options.postStatus, json: { code: 500, message: 'server error' } })
    }
    const body = route.request().postDataJSON() as Record<string, unknown>
    options.onCreate?.(body)
    route.fulfill({
      json: javaEnvelope({
        id: 99,
        userId: 1,
        noteName: body.noteName,
        content: body.content,
        tags: [],
        isPinned: 0,
        noteType: body.noteType ?? 'quick',
        organizeStatus: body.organizeStatus ?? 'pending',
        sourceType: body.sourceType,
        sourceId: body.sourceId,
        sourceTitle: body.sourceTitle,
        sourceRoute: body.sourceRoute,
        excerpt: body.excerpt,
        createdAt: '2025-01-03T00:00:00Z',
        updatedAt: '2025-01-03T00:00:00Z',
      }),
    })
  })

  // Only match /api/note/:id (numeric) — not /list, /resources, or bare /note
  await page.route(/\/api\/note\/\d+(\?.*)?$/, route => {
    const url = route.request().url()
    const idMatch = url.match(/\/note\/(\d+)/)
    const noteId = idMatch ? Number(idMatch[1]) : NOTE_ID

    if (route.request().method() === 'GET') {
      const note = notes.find(n => n.id === noteId) ?? notes[0]
      return route.fulfill({ json: javaEnvelope(note) })
    }
    if (route.request().method() !== 'PUT') return route.continue()
    const status = typeof options.putStatus === 'function' ? options.putStatus() : options.putStatus
    if (status >= 500) {
      return route.fulfill({ status, json: { code: 500, message: 'server error' } })
    }
    const body = route.request().postDataJSON() as Record<string, unknown>
    options.onUpdate?.(body)
    route.fulfill({
      json: javaEnvelope({
        id: noteId,
        userId: 1,
        noteName: body.noteName,
        content: body.content,
        tags: [],
        isPinned: 0,
        noteType: body.noteType,
        organizeStatus: body.organizeStatus,
        sourceType: body.sourceType,
        sourceId: body.sourceId,
        sourceTitle: body.sourceTitle,
        sourceRoute: body.sourceRoute,
        excerpt: body.excerpt,
        createdAt: '2025-01-01T00:00:00Z',
        updatedAt: '2025-01-03T00:00:00Z',
      }),
    })
  })
}

const notesPanelToggle = (page: Page) => page.getByRole('button', { name: '笔记', exact: true })

test.describe('全局笔记侧栏', () => {
  test.describe('搜索、来源与全屏入口', () => {
    test('搜索关键字后展示来源标签并可跳转全屏笔记', async ({ page }) => {
      const capturedKeyword = { value: '' }
      await setupAuth(page)
      await mockNoteApi(page, { capturedKeyword, putStatus: 200 })

      await page.goto('/dashboard')
      await notesPanelToggle(page).click()

      await page.getByPlaceholder('搜索笔记').fill('线性')
      await expect.poll(() => capturedKeyword.value, { timeout: 5000 }).toBe('线性')
      await expect(page.getByText('基础 · 线性回归')).toBeVisible()

      await page.getByText('线性回归笔记').click()
      await page.getByPlaceholder(/补充|笔记补充|理解|问题|思路/).fill('更新内容')
      await page.getByRole('button', { name: '保存' }).click()
      await expect(page.getByRole('button', { name: '已保存' })).toBeVisible({ timeout: 5000 })

      await page.getByRole('button', { name: '打开完整笔记' }).click()
      await expect(page).toHaveURL(/\/notes\/12$/)
    })
  })

  test.describe('捕获工作台', () => {
    test('折叠行展开、模式切换与分组渲染', async ({ page }) => {
      const capturedKeyword = { value: '' }
      await setupAuth(page)
      await mockNoteApi(page, { capturedKeyword, putStatus: 200 })

      await page.goto('/dashboard')
      await notesPanelToggle(page).click()

      // Collapsed capture row
      await expect(page.getByTestId('capture-row')).toBeVisible()
      await expect(page.getByText('记一条笔记')).toBeVisible()

      // Groups
      await expect(page.getByTestId('group-pending')).toBeVisible()
      await expect(page.getByTestId('group-organized')).toBeVisible()
      await expect(page.getByText('待整理')).toBeVisible()
      await expect(page.getByText('已整理')).toBeVisible()

      // Expand capture
      await page.getByTestId('capture-row').click()
      await expect(page.getByRole('tab', { name: '速记' })).toBeVisible()
      await expect(page.getByRole('tab', { name: '摘录' })).toBeVisible()
      await expect(page.getByRole('tab', { name: '问题' })).toBeVisible()

      // Mode switch
      await page.getByRole('tab', { name: '问题' }).click()
      await expect(page.getByText('笔记补充')).toBeVisible()
      await expect(page.getByPlaceholder('补充你的问题或思路…')).toBeVisible()

      // Collapse
      await page.getByRole('button', { name: '收起' }).click()
      await expect(page.getByRole('tab', { name: '问题' })).toHaveCount(0)
    })

    test('拖拽内容进入摘录模式', async ({ page }) => {
      const capturedKeyword = { value: '' }
      await setupAuth(page)
      await mockNoteApi(page, { capturedKeyword, putStatus: 200 })

      await page.goto('/dashboard')
      await notesPanelToggle(page).click()

      // Simulate drop of text onto the sidebar capture surface
      await page.getByTestId('capture-row').dispatchEvent('drop', {
        dataTransfer: await page.evaluateHandle(() => {
          const dt = new DataTransfer()
          dt.setData('text/plain', '拖入的摘录原文')
          return dt
        }),
      })

      // Fallback: programmatically trigger via evaluating drop if Playwright DataTransfer is limited
      await page.evaluate(() => {
        const root = document.querySelector('[data-testid="capture-row"]')?.closest('.flex.flex-col.h-full')
        if (!root) return
        const dt = new DataTransfer()
        dt.setData('text/plain', '拖入的摘录原文')
        root.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }))
      })

      await expect(page.getByText('摘录原文', { exact: true })).toBeVisible({ timeout: 3000 })
      await expect(page.getByText('拖入的摘录原文', { exact: true })).toBeVisible()
      await expect(page.getByRole('tab', { name: '摘录' })).toHaveAttribute('aria-selected', 'true')
    })

    test('遗留笔记以速记/待整理默认值可编辑', async ({ page }) => {
      const capturedKeyword = { value: '' }
      await setupAuth(page)
      await mockNoteApi(page, { capturedKeyword, putStatus: 200 })

      await page.goto('/dashboard')
      await notesPanelToggle(page).click()

      // Legacy note (id 14) should appear under 待整理
      const legacyItem = page.getByTestId('group-pending').getByText('旧笔记', { exact: true })
      await expect(legacyItem).toBeVisible()
      await legacyItem.click()
      await expect(page.getByRole('tab', { name: '速记' })).toHaveAttribute('aria-selected', 'true')
      await page.getByPlaceholder(/补充|笔记补充|理解|问题|思路/).fill('补充内容')
      await page.getByRole('button', { name: '保存' }).click()
      await expect(page.getByRole('button', { name: '已保存' })).toBeVisible({ timeout: 5000 })
    })
  })

  test.describe('草稿恢复', () => {
    test('未保存的新笔记草稿在关闭侧栏和刷新后恢复', async ({ page }) => {
      const capturedKeyword = { value: '' }
      await setupAuth(page)
      await mockNoteApi(page, { capturedKeyword, putStatus: 200, postStatus: 500 })

      await page.goto('/dashboard')
      await notesPanelToggle(page).click()

      // 开启新笔记并输入内容（不创建）
      await page.getByRole('button', { name: '新建笔记' }).click()
      await page.getByPlaceholder('可选，不填则自动命名').fill('草稿标题')
      await page.getByPlaceholder(/补充|笔记补充|理解|问题|思路/).fill('草稿正文')

      // 验证已写入 localStorage
      await expect.poll(
        async () => await page.evaluate((key) => localStorage.getItem(key), DRAFT_STORAGE_KEY),
        { timeout: 3000 },
      ).not.toBeNull()

      // 关闭并重新打开侧栏
      await notesPanelToggle(page).click()
      await notesPanelToggle(page).click()
      await expect(page.getByPlaceholder('可选，不填则自动命名')).toHaveValue('草稿标题')
      await expect(page.getByPlaceholder(/补充|笔记补充|理解|问题|思路/)).toHaveValue('草稿正文')

      // 刷新页面后再次打开
      await page.reload()
      await notesPanelToggle(page).click()

      await expect(page.getByPlaceholder('可选，不填则自动命名')).toHaveValue('草稿标题')
      await expect(page.getByPlaceholder(/补充|笔记补充|理解|问题|思路/)).toHaveValue('草稿正文')
    })
  })

  test.describe('保存失败与重试', () => {
    test('PUT 500 后显示重试，重试成功后显示已保存', async ({ page }) => {
      const capturedKeyword = { value: '' }
      let nextPutStatus = 500
      await setupAuth(page)
      await mockNoteApi(page, {
        capturedKeyword,
        putStatus: () => {
          const s = nextPutStatus
          nextPutStatus = 200
          return s
        },
      })

      await page.goto('/dashboard')
      await notesPanelToggle(page).click()

      await page.getByText('线性回归笔记').click()
      await page.getByPlaceholder(/补充|笔记补充|理解|问题|思路/).fill('首次更新')
      await page.getByRole('button', { name: '保存' }).click()

      await expect(page.getByRole('button', { name: '重试保存' })).toBeVisible({ timeout: 5000 })

      await page.getByRole('button', { name: '重试保存' }).click()
      await expect(page.getByRole('button', { name: '已保存' })).toBeVisible({ timeout: 5000 })
    })
  })
})
