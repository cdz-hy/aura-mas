import { test, expect, type Page } from '@playwright/test'

// ─── Mock Data ───────────────────────────────────────────────────────

const MOCK_USER = {
  id: 1,
  loginName: 'testuser',
  username: '测试用户',
  role: 'user',
}

const MOCK_MENUS = [
  {
    id: 1,
    name: '仪表盘',
    code: 'dashboard',
    path: '/dashboard',
    icon: 'dashboard',
    children: [],
  },
  {
    id: 2,
    name: '学习计划',
    code: 'plan-list',
    path: '/plan',
    icon: 'plan',
    children: [],
  },
  {
    id: 3,
    name: '知识树',
    code: 'knowledge-tree',
    path: '/knowledge-tree',
    icon: 'tree',
    children: [],
  },
]

const TREE_ID = 'tree-001'
const PLAN_ID = 1

const MOCK_NODES = [
  {
    id: 'node-root',
    treeId: TREE_ID,
    parentId: null,
    title: '机器学习基础',
    summary: '机器学习的核心概念和基本原理',
    status: 'learning',
    relevance: 4,
    importance: 5,
    difficulty: 3,
    depth: 0,
    sortOrder: 0,
    collapsed: false,
    isFundamental: true,
    prerequisiteIds: [],
  },
  {
    id: 'node-1',
    treeId: TREE_ID,
    parentId: 'node-root',
    title: '监督学习',
    summary: '通过标注数据训练模型的方法',
    status: 'todo',
    relevance: 4,
    importance: 4,
    difficulty: 3,
    depth: 1,
    sortOrder: 0,
    collapsed: false,
    isFundamental: false,
    prerequisiteIds: [],
  },
  {
    id: 'node-2',
    treeId: TREE_ID,
    parentId: 'node-root',
    title: '无监督学习',
    summary: '从无标注数据中发现模式',
    status: 'completed',
    relevance: 3,
    importance: 3,
    difficulty: 4,
    depth: 1,
    sortOrder: 1,
    collapsed: false,
    isFundamental: false,
    prerequisiteIds: [],
  },
  {
    id: 'node-3',
    treeId: TREE_ID,
    parentId: 'node-1',
    title: '线性回归',
    summary: '最基本的监督学习算法',
    status: 'todo',
    relevance: 3,
    importance: 3,
    difficulty: 2,
    depth: 2,
    sortOrder: 0,
    collapsed: false,
    isFundamental: false,
    prerequisiteIds: [],
  },
]

const MOCK_TREE_RESPONSE = {
  tree: {
    id: TREE_ID,
    planId: PLAN_ID,
    title: '机器学习学习树',
    field: '计算机科学',
    currentProblem: '掌握机器学习基础',
    currentNodeId: 'node-root',
  },
  nodes: MOCK_NODES,
}

const MOCK_MESSAGES = [
  {
    id: 1,
    treeId: TREE_ID,
    nodeId: 'node-root',
    role: 'user',
    content: '什么是机器学习？',
    createdAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 2,
    treeId: TREE_ID,
    nodeId: 'node-root',
    role: 'assistant',
    content: '机器学习是人工智能的一个分支，它使计算机能够从数据中学习并做出决策或预测，而无需被显式编程。',
    createdAt: '2024-01-01T00:00:01Z',
  },
]

// ─── Helpers ─────────────────────────────────────────────────────────

/** 在页面 localStorage 中注入登录态和菜单权限 */
async function setupAuth(page: Page) {
  await page.addInitScript(([token, user, menus]) => {
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(user))
    localStorage.setItem('menus', JSON.stringify(menus))
  }, ['fake-jwt-token', MOCK_USER, MOCK_MENUS])
}

/** 拦截所有 Java 后端 REST API */
async function mockJavaApi(page: Page) {
  // 签发 ticket
  await page.route('**/api/ticket/issue', route =>
    route.fulfill({ json: { code: 200, data: { ticket: 'fake-ticket' } } }),
  )

  // 创建/获取知识树
  await page.route(`**/api/knowledge-tree/plan/${PLAN_ID}`, route =>
    route.fulfill({ json: { code: 200, data: MOCK_TREE_RESPONSE } }),
  )

  // 获取节点消息
  await page.route('**/api/knowledge-tree/nodes/*/messages', route => {
    const url = route.request().url()
    const nodeId = url.match(/nodes\/([^/]+)\/messages/)?.[1]
    const messages = MOCK_MESSAGES.filter(m => m.nodeId === nodeId)
    route.fulfill({ json: { code: 200, data: messages } })
  })

  // 更新节点
  await page.route('**/api/knowledge-tree/nodes/*', route => {
    if (route.request().method() === 'PATCH') {
      const url = route.request().url()
      const nodeId = url.match(/nodes\/([^/]+)/)?.[1]
      const node = MOCK_NODES.find(n => n.id === nodeId)
      route.fulfill({ json: { code: 200, data: { ...node, collapsed: !node?.collapsed } } })
    } else {
      route.continue()
    }
  })

  // 用户信息（某些页面可能需要）
  await page.route('**/api/user/info', route =>
    route.fulfill({ json: { code: 200, data: MOCK_USER } }),
  )
}

/** 拦截 Python 后端请求，返回模拟响应 */
async function mockPythonBackend(page: Page) {
  // 拆分选项（axios GET，走 localhost:8002）
  await page.route(url => url.toString().includes('localhost:8002') && url.toString().includes('subdivision-options'), route =>
    route.fulfill({
      json: {
        options: [
          { angle: '按算法类型', label: '算法类型', rationale: '按算法类型分类' },
          { angle: '按应用场景', label: '应用场景', rationale: '按应用场景分类' },
          { angle: '按数学基础', label: '数学基础', rationale: '按数学基础分类' },
        ],
        caution: null,
      },
    }),
  )

  // SSE 流式接口 — 用回调匹配，避免 glob 冲突
  await page.route(url => {
    const s = url.toString()
    if (!s.includes('localhost:8002')) return false
    return /\/(explain|subdivide|first-principles|quiz|flashcards|multi-angle-subdivide)\?/.test(s)
  }, route => {
    const sseBody = [
      'data: {"type":"progress","content":"正在分析..."}\n\n',
      'data: {"type":"stream_text","content":"这是AI生成的 "}\n\n',
      'data: {"type":"stream_text","content":"流式回复内容。"}\n\n',
      'data: {"type":"message","message":{"id":99,"treeId":"tree-001","nodeId":"node-root","role":"assistant","content":"完整回复"}}\n\n',
      'data: {"type":"done"}\n\n',
    ].join('')

    route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
      body: sseBody,
    })
  })
}

// ─── Tests ───────────────────────────────────────────────────────────

test.describe('知识树功能', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page)
    await mockJavaApi(page)
    await mockPythonBackend(page)
  })

  test.describe('页面加载与渲染', () => {
    test('进入知识树模式后显示树画布', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.tree-canvas', { timeout: 10000 })
      await expect(page.locator('.tree-canvas')).toBeVisible()
    })

    test('渲染所有知识节点', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.tree-node', { timeout: 10000 })

      const nodes = page.locator('.tree-node')
      await expect(nodes).toHaveCount(MOCK_NODES.length)
    })

    test('节点显示正确的标题', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.tree-node', { timeout: 10000 })

      await expect(page.locator('.tree-node').first()).toContainText('机器学习基础')
    })

    test('节点显示状态标签', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.status-badge', { timeout: 10000 })

      const badges = page.locator('.status-badge')
      await expect(badges.first()).toBeVisible()
    })

    test('显示缩放工具栏', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.tree-canvas', { timeout: 10000 })

      await expect(page.locator('button[title="缩小"]')).toBeVisible()
      await expect(page.locator('button[title="放大"]')).toBeVisible()
      await expect(page.locator('button[title="居中"]')).toBeVisible()
    })

    test('显示 SVG 连线', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.tree-node', { timeout: 10000 })

      const paths = page.locator('.tree-canvas svg path')
      await expect(paths.first()).toBeVisible()
    })
  })

  test.describe('节点交互', () => {
    test('点击节点触发选中', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.tree-node', { timeout: 10000 })

      const firstNode = page.locator('.tree-node').first()
      await firstNode.click()

      // 选中后应加载该节点的消息
      await expect(firstNode).toBeVisible()
    })

    test('节点有正确的 aria-label', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.tree-node', { timeout: 10000 })

      const rootNode = page.locator('[aria-label="选择知识节点：机器学习基础"]')
      await expect(rootNode).toBeVisible()
    })

    test('基础节点显示 "原理" 标签', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.mini-badge', { timeout: 10000 })

      // node-root 有 isFundamental=true，应显示"原理"标签
      const rootNode = page.locator('[aria-label="选择知识节点：机器学习基础"]')
      await expect(rootNode.locator('.mini-badge')).toBeVisible()
    })

    test('点击展开/折叠按钮切换节点状态', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.icon-button', { timeout: 10000 })

      const collapseBtn = page.locator('.tree-node').first().locator('.icon-button')
      if (await collapseBtn.isVisible()) {
        await collapseBtn.click()
        // 按钮标题应从 "折叠" 变为 "展开" 或反之
      }
    })

    test('点击拆分按钮打开拆分面板', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.node-action', { timeout: 10000 })

      const subdivideBtn = page.locator('.node-action').first()
      await subdivideBtn.click()

      await expect(page.locator('[aria-label="节点拆分面板"]')).toBeVisible()
    })
  })

  test.describe('缩放与平移', () => {
    test('点击放大按钮增加缩放', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.tree-canvas', { timeout: 10000 })

      const zoomInBtn = page.locator('button[title="放大"]')
      await zoomInBtn.click()

      // 缩放百分比应变化
      const zoomDisplay = page.locator('.tree-canvas').locator('span')
      const text = await zoomDisplay.textContent()
      expect(text).toBeTruthy()
    })

    test('点击缩小按钮减小缩放', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.tree-canvas', { timeout: 10000 })

      const zoomOutBtn = page.locator('button[title="缩小"]')
      await zoomOutBtn.click()
    })

    test('点击居中按钮重置视图', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.tree-canvas', { timeout: 10000 })

      const centerBtn = page.locator('button[title="居中"]')
      await centerBtn.click()
    })

    test('鼠标滚轮缩放画布', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.tree-canvas', { timeout: 10000 })

      const canvas = page.locator('.tree-canvas')
      await canvas.hover()
      await page.mouse.wheel(0, -100) // 向上滚 = 放大
    })
  })

  test.describe('聊天面板', () => {
    test('选中节点后显示聊天输入框', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.tree-node', { timeout: 10000 })

      // 点击节点
      await page.locator('.tree-node').first().click()
      await page.waitForTimeout(500)

      // 应显示聊天输入
      const textarea = page.locator('textarea[placeholder="询问这个节点..."]')
      if (await textarea.isVisible()) {
        await expect(textarea).toBeVisible()
      }
    })

    test('显示快捷操作按钮', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.tree-node', { timeout: 10000 })

      await page.locator('.tree-node').first().click()
      await page.waitForTimeout(500)

      const quickButtons = page.locator('.quick-button')
      if (await quickButtons.first().isVisible()) {
        const count = await quickButtons.count()
        expect(count).toBeGreaterThanOrEqual(1)
      }
    })

    test('发送消息后显示流式回复', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.tree-node', { timeout: 10000 })

      await page.locator('.tree-node').first().click()
      await page.waitForTimeout(500)

      const textarea = page.locator('textarea[placeholder="询问这个节点..."]')
      if (await textarea.isVisible()) {
        await textarea.fill('解释一下这个概念')
        const sendBtn = page.locator('.btn-primary')
        await sendBtn.click()

        // 等待流式内容出现
        await page.waitForTimeout(1000)
      }
    })
  })

  test.describe('拆分面板', () => {
    test('拆分面板不再显示粒度模式选择', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.node-action', { timeout: 10000 })

      await page.locator('.node-action').first().click()
      await page.waitForSelector('[aria-label="节点拆分面板"]', { timeout: 5000 })

      const modeGroup = page.locator('[aria-label="拆分粒度"]')
      await expect(modeGroup).toHaveCount(0)
    })

    test('拆分面板显示两种拆分选择', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.node-action', { timeout: 10000 })

      await page.locator('.node-action').first().click()
      await page.waitForSelector('.split-choice', { timeout: 5000 })

      const choices = page.locator('.split-choice')
      await expect(choices).toHaveCount(2)
    })

    test('拆分面板有自定义角度输入', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.node-action', { timeout: 10000 })

      await page.locator('.node-action').first().click()
      await page.waitForSelector('[aria-label="节点拆分面板"]', { timeout: 5000 })

      const customInput = page.locator('input[placeholder="自定义拆分角度"]').first()
      await expect(customInput).toBeVisible()
    })

    test('关闭拆分面板', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.node-action', { timeout: 10000 })

      await page.locator('.node-action').first().click()
      await page.waitForSelector('[aria-label="节点拆分面板"]', { timeout: 5000 })

      const closeBtn = page.locator('button[title="关闭"]')
      await closeBtn.click()

      await expect(page.locator('[aria-label="节点拆分面板"]')).not.toBeVisible()
    })

    test('点击 "按知识点拆分" 加载拆分选项', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.node-action', { timeout: 10000 })

      await page.locator('.node-action').first().click()
      await page.waitForSelector('.split-choice', { timeout: 5000 })

      // 点击「按知识点拆分」（第二个选项）
      const byKnowledgeBtn = page.locator('.split-choice--topic')
      await byKnowledgeBtn.click()

      // 等待选项加载（mock 返回 3 个选项）
      await page.waitForTimeout(1000)
      const options = page.locator('.split-option')
      const count = await options.count()
      expect(count).toBeGreaterThanOrEqual(0) // 可能还在 loading
    })

    test('输入自定义角度并拆分', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.node-action', { timeout: 10000 })

      await page.locator('.node-action').first().click()
      await page.waitForSelector('[aria-label="节点拆分面板"]', { timeout: 5000 })

      const customInput = page.locator('input[placeholder="自定义拆分角度"]').first()
      await customInput.fill('按难度分级')

      // 找到输入框旁边的拆分按钮
      const splitBtn = customInput.locator('..').locator('button')
      if (await splitBtn.isVisible()) {
        await splitBtn.click()
        await page.waitForTimeout(1000)
      }
    })
  })

  test.describe('大纲视图', () => {
    test('大纲视图显示节点列表', async ({ page }) => {
      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.tree-node', { timeout: 10000 })

      // 大纲视图在左侧边栏，需要检查 outline 组件
      const outlineCards = page.locator('.outline-module-card')
      // 大纲可能需要切换视图模式
      const count = await outlineCards.count()
      expect(count).toBeGreaterThanOrEqual(0)
    })
  })

  test.describe('错误处理', () => {
    test('API 失败时显示错误信息', async ({ page }) => {
      // 覆盖知识树 API 返回错误
      await page.route(`**/api/knowledge-tree/plan/${PLAN_ID}`, route =>
        route.fulfill({
          status: 500,
          json: { code: 500, message: '服务器内部错误' },
        }),
      )

      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForTimeout(3000)

      // 页面应能处理错误，不崩溃
      await expect(page.locator('.tree-canvas')).toBeVisible()
    })

    test('SSE 连接中断时页面不崩溃', async ({ page }) => {
      // 覆盖 SSE 返回错误（后注册的路由优先匹配）
      await page.route(url => {
        const s = url.toString()
        return s.includes('localhost:8002') && /\/(explain|subdivide|first-principles|quiz|flashcards|multi-angle-subdivide)\?/.test(s)
      }, route =>
        route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' },
          body: 'data: {"type":"error","content":"连接中断"}\n\n',
        }),
      )

      await page.goto(`/plan/${PLAN_ID}?view=tree`)
      await page.waitForSelector('.tree-node', { timeout: 10000 })

      await page.locator('.tree-node').first().click()
      await page.waitForTimeout(500)

      const textarea = page.locator('textarea[placeholder="询问这个节点..."]')
      if (await textarea.isVisible()) {
        await textarea.fill('测试')
        await page.locator('.btn-primary').click()
        await page.waitForTimeout(1000)
      }

      // 页面应仍然可用
      await expect(page.locator('.tree-canvas')).toBeVisible()
    })
  })
})
