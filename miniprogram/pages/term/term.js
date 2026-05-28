/* pages/term/term.js */
const { api } = require('../../utils/api')

const CATEGORY_COLOR = {
  power_unit: '#e10600',  // 红
  aero:       '#4a9eff',  // 蓝
  tyre:       '#f5a623',  // 橙
  strategy:   '#7ed321',  // 绿
  rules:      '#9b59b6',  // 紫
  flag:       '#f0f0f0',  // 白
  driving:    '#00d2be',  // 青
}

const CATEGORY_COLORS = {
  aero: '#4a9eff',
  tyre: '#f5a623',
  strategy: '#7ed321',
  power_unit: '#e10600',
  rules: '#9b59b6',
  driving: '#00d2be',
}

const CATEGORY_LABEL = {
  power_unit: '动力单元', aero: '空气动力', tyre: '轮胎',
  strategy: '策略', rules: '规则', flag: '旗语', driving: '驾驶',
}

const LEVEL_LABEL = { 1: '基础', 2: '进阶', 3: '高阶' }

function enrichTerm(rawTerm) {
  if (!rawTerm) return null
  const color = CATEGORY_COLOR[rawTerm.category] || '#aaa'
  return {
    ...rawTerm,
    color,
    category_label: CATEGORY_LABEL[rawTerm.category] || rawTerm.category,
    level_label: LEVEL_LABEL[rawTerm.level] || '基础',
    aliases_list: (rawTerm.aliases || '').split(',').map(s => s.trim()).filter(Boolean),
    related_list: (rawTerm.related_slugs || '').split(',').map(s => s.trim()).filter(Boolean),
  }
}

function buildRadialNodes(relatedTerms) {
  const count = relatedTerms.length
  if (count === 0) return []

  const radius = 140
  const startAngle = -Math.PI / 2
  return relatedTerms.map((t, i) => {
    const angle = startAngle + (2 * Math.PI * i) / count
    return {
      ...t,
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
      angle: (angle * 180) / Math.PI,
    }
  })
}

function buildBreadcrumbData(fromSlug, fromPath, allTerms) {
  let breadcrumb = []
  if (fromSlug && fromPath.length > 0) {
    breadcrumb = fromPath.map(slug => ({ slug, name: '' }))
    if (!breadcrumb.find(b => b.slug === fromSlug)) {
      breadcrumb.push({ slug: fromSlug, name: '' })
    }
  } else if (fromSlug) {
    breadcrumb = [{ slug: fromSlug, name: '' }]
  }
  if (breadcrumb.length === 0) return []

  const termNameMap = {}
  allTerms.forEach(item => {
    termNameMap[item.slug] = item.name_zh || item.slug
  })

  breadcrumb.forEach(item => {
    item.name = termNameMap[item.slug] || item.slug
  })
  if (breadcrumb.length > 3) {
    breadcrumb = breadcrumb.slice(breadcrumb.length - 3)
  }
  return breadcrumb
}

Page({
  data: {
    loading: true,
    error: '',
    term: null,
    relatedTerms: [],
    radialNodes: [],
    breadcrumb: [],
    fromSlug: '',
    fromPath: [],
    deepVisible: false,
  },

  onLoad(options) {
    this.slug = options.slug
    this.fromSlug = options.from_slug || ''
    let fromPath = []
    if (options.from_path) {
      try { fromPath = JSON.parse(decodeURIComponent(options.from_path)) } catch (e) {}
    }
    this.setData({ fromSlug: this.fromSlug, fromPath })
    wx.setNavigationBarTitle({ title: '术语详情' })
    this.loadTerm()
  },

  onShow() {
    const term = this.data.term
    if (!term || !term.slug) return
    const slug = term.slug
    let recent = wx.getStorageSync('recent_terms') || []
    recent = recent.filter(s => s !== slug)
    recent.unshift(slug)
    if (recent.length > 10) recent = recent.slice(0, 10)
    wx.setStorageSync('recent_terms', recent)
  },

  async loadTerm() {
    this.setData({ loading: true, error: '' })
    try {
      const catalogRes = await api.getTermsCatalog()
      const allTerms = catalogRes.data || []
      const termRaw = allTerms.find(item => item.slug === this.slug)

      if (!termRaw) {
        throw new Error('term_not_found')
      }

      const term = enrichTerm(termRaw)
      const relatedTerms = term.related_list.length > 0
        ? term.related_list
            .map(slug => allTerms.find(item => item.slug === slug))
            .filter(Boolean)
            .map(enrichTerm)
        : []
      const radialNodes = buildRadialNodes(relatedTerms)
      const breadcrumb = buildBreadcrumbData(this.data.fromSlug, this.data.fromPath, allTerms)

      this.setData({
        loading: false,
        term,
        relatedTerms,
        radialNodes,
        breadcrumb,
      })
      wx.setNavigationBarTitle({ title: term.name_zh })
    } catch (e) {
      this.setData({ loading: false, error: '加载失败，请返回重试' })
    }
  },

  onGoRelated(e) {
    const slug = e.currentTarget.dataset.slug
    const currentSlug = this.data.term.slug
    const fromPath = [...this.data.fromPath]
    if (this.data.fromSlug && !fromPath.includes(this.data.fromSlug)) {
      fromPath.push(this.data.fromSlug)
    }
    if (!fromPath.includes(currentSlug)) {
      fromPath.push(currentSlug)
    }
    const pathStr = encodeURIComponent(JSON.stringify(fromPath))
    wx.navigateTo({ url: `/pages/term/term?slug=${slug}&from_slug=${currentSlug}&from_path=${pathStr}` })
  },

  onBreadcrumbTap(e) {
    const slug = e.currentTarget.dataset.slug
    const fromPath = this.data.fromPath
    const fromSlug = this.data.fromSlug
    const fullChain = [...fromPath]
    if (fromSlug && !fullChain.includes(fromSlug)) {
      fullChain.push(fromSlug)
    }
    const idx = fullChain.indexOf(slug)
    if (idx === -1) return
    let newFromSlug = ''
    let newFromPath = []
    if (idx > 0) {
      newFromSlug = fullChain[idx - 1]
      newFromPath = fullChain.slice(0, idx - 1)
    }
    const pathStr = encodeURIComponent(JSON.stringify(newFromPath))
    wx.redirectTo({ url: `/pages/term/term?slug=${slug}&from_slug=${newFromSlug}&from_path=${pathStr}` })
  },

  onDeepDive() {
    this.setData({ deepVisible: true })
  },

  onCloseDeep() {
    this.setData({ deepVisible: false })
  },

  onCopyTerm() {
    const t = this.data.term
    if (!t) return
    const text = `【${t.name_zh}】${t.name_en ? '(' + t.name_en + ')' : ''}
分类：${t.category_label}　难度：${t.level_label}
${t.short_def}${t.full_def ? '\n\n' + t.full_def : ''}${t.example ? '\n\n📌 ' + t.example : ''}`
    wx.setClipboardData({
      data: text,
      success: () => wx.showToast({ title: '已复制', icon: 'success' })
    })
  },
})
