/* pages/glossary/glossary.js */
const { api } = require('../../utils/api')

const CATEGORY_COLOR = {
  power_unit: '#e10600',
  aero:       '#4a9eff',
  tyre:       '#f5a623',
  strategy:   '#7ed321',
  rules:      '#9b59b6',
  driving:    '#00d2be',
}

const CATEGORY_LABEL = {
  power_unit: '动力单元',
  aero:       '空气动力',
  tyre:       '轮胎',
  strategy:   '策略',
  rules:      '规则',
  driving:    '驾驶技术',
}

const TECH_CATEGORIES = [
  { key: 'all',        label: '全部',    color: '#aaa' },
  { key: 'aero',       label: '空气动力', color: '#4a9eff' },
  { key: 'tyre',       label: '轮胎',    color: '#f5a623' },
  { key: 'strategy',   label: '策略',    color: '#7ed321' },
  { key: 'power_unit', label: '动力单元', color: '#e10600' },
  { key: 'rules',      label: '规则',    color: '#9b59b6' },
  { key: 'driving',    label: '驾驶技术', color: '#00d2be' },
]

const SCENE_CATEGORIES = [
  { key: 'all',         label: '全部',     color: '#aaa' },
  { key: 'race_common', label: '比赛常用', color: '#e10600' },
  { key: 'tech_talk',   label: '解说热词', color: '#4a9eff' },
  { key: '2026_new',    label: '2026必知', color: '#7ed321' },
]

Page({
  data: {
    loading: true,
    allTerms: [],
    filtered: [],
    activeCategory: 'all',
    searchVal: '',
    categories: TECH_CATEGORIES,
    catViewMode: 'tech',
    hotMap: {},
    maxHot: 0,
    popularSlugs: [],
    popularTerms: [],
    hotTop3: [],
    searchFocused: false,
    recentTerms: [],
    suggestions: [],
    submitVisible: false,
    submitting: false,
    form: { name_zh: '', name_en: '', short_def: '', category: '' },
  },

  onLoad() {
    this.loadAllData()
  },

  onShow() {
    wx.showTabBar({ animation: false })
    this._loadRecentTerms()
  },

  async loadAllData() {
    this.setData({ loading: true })
    try {
      const [termsRes, hotRes, popularRes] = await Promise.all([
        api.getTermsCatalog(),
        api.getTermsHot().catch(() => ({ data: {} })),
        api.getTermsPopular().catch(() => ({ data: [] })),
      ])
      const hotMap = hotRes.data || {}
      const hotCounts = Object.values(hotMap)
      const maxHot = hotCounts.length ? Math.max(...hotCounts) : 0

      const allTerms = (termsRes.data || []).map(t => ({
        ...t,
        color: CATEGORY_COLOR[t.category] || '#aaa',
        category_label: CATEGORY_LABEL[t.category] || t.category,
        hotCount: hotMap[t.slug] || 0,
        hotPercent: maxHot > 0 ? ((hotMap[t.slug] || 0) / maxHot * 100) : 0,
        levelStars: t.level === 1 ? '★' : t.level === 2 ? '★★' : '★★★',
      }))

      const popularSlugs = popularRes.data || []
      const popularTerms = popularSlugs.map(slug =>
        allTerms.find(t => t.slug === slug)
      ).filter(Boolean)

      const sorted = Object.entries(hotMap)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
      const hotTop3 = sorted.map(([slug, count]) => {
        const term = allTerms.find(t => t.slug === slug)
        if (!term) return null
        return {
          slug,
          name_zh: term.name_zh,
          hotCount: count,
          hotPercent: maxHot > 0 ? (count / maxHot * 100) : 0,
          color: term.color,
        }
      }).filter(Boolean)

      this.setData({
        loading: false,
        allTerms,
        hotMap,
        maxHot,
        popularSlugs,
        popularTerms,
        hotTop3,
      })
      this._applyFilter()
      this._loadRecentTerms()
    } catch (e) {
      console.error('loadAllData error', e)
      this.setData({ loading: false })
    }
  },

  onToggleCatView() {
    const next = this.data.catViewMode === 'tech' ? 'scene' : 'tech'
    this.setData({
      catViewMode: next,
      categories: next === 'tech' ? TECH_CATEGORIES : SCENE_CATEGORIES,
      activeCategory: 'all',
    })
    this._applyFilter()
  },

  onCategoryTap(e) {
    this.setData({ activeCategory: e.currentTarget.dataset.key })
    this._applyFilter()
  },

  onSearchFocus() {
    this.setData({ searchFocused: true })
    this._loadRecentTerms()
  },

  onSearchBlur() {
    setTimeout(() => {
      this.setData({ searchFocused: false, suggestions: [] })
    }, 200)
  },

  onSearchInput(e) {
    const val = e.detail.value
    this.setData({ searchVal: val })
    if (val.trim()) {
      this.setData({ searchFocused: false })
      this._buildSuggestions(val.trim())
    } else {
      this.setData({ suggestions: [], searchFocused: true })
    }
    this._applyFilter()
  },

  onSearchClear() {
    this.setData({ searchVal: '', suggestions: [], searchFocused: true })
    this._loadRecentTerms()
    this._applyFilter()
  },

  _buildSuggestions(query) {
    const q = query.toLowerCase()
    const { allTerms } = this.data
    const results = []
    for (const t of allTerms) {
      if (results.length >= 5) break
      if (t.name_zh.toLowerCase().includes(q)) {
        results.push({ keyword: t.name_zh, name_zh: t.name_zh, slug: t.slug, color: t.color })
        continue
      }
      if (t.name_en.toLowerCase().includes(q)) {
        results.push({ keyword: t.name_en, name_zh: t.name_zh, slug: t.slug, color: t.color })
        continue
      }
      if (t.aliases) {
        const aliasList = t.aliases.split(',').map(a => a.trim()).filter(Boolean)
        for (const alias of aliasList) {
          if (alias.toLowerCase().includes(q)) {
            results.push({ keyword: alias, name_zh: t.name_zh, slug: t.slug, color: t.color })
            break
          }
        }
      }
    }
    this.setData({ suggestions: results })
  },

  onSuggestionTap(e) {
    const { slug } = e.currentTarget.dataset
    this._saveRecentTerm(slug)
    wx.navigateTo({ url: `/pages/term/term?slug=${slug}` })
  },

  onPopularTap(e) {
    const { slug } = e.currentTarget.dataset
    this._saveRecentTerm(slug)
    wx.navigateTo({ url: `/pages/term/term?slug=${slug}` })
  },

  onRecentTap(e) {
    const { slug } = e.currentTarget.dataset
    this._saveRecentTerm(slug)
    wx.navigateTo({ url: `/pages/term/term?slug=${slug}` })
  },

  onHotTermTap(e) {
    const { slug } = e.currentTarget.dataset
    this._saveRecentTerm(slug)
    wx.navigateTo({ url: `/pages/term/term?slug=${slug}` })
  },

  _loadRecentTerms() {
    try {
      const slugs = wx.getStorageSync('recent_terms') || []
      const { allTerms } = this.data
      const recentTerms = slugs.slice(0, 5).map(slug => {
        const term = allTerms.find(t => t.slug === slug)
        return term
          ? { slug: slug, name_zh: term.name_zh, color: term.color }
          : { slug: slug, name_zh: slug, color: '#666' }
      })
      this.setData({ recentTerms: recentTerms })
    } catch (e) {
      this.setData({ recentTerms: [] })
    }
  },

  _saveRecentTerm(slug) {
    try {
      var list = wx.getStorageSync('recent_terms') || []
      list = list.filter(function(s) { return s !== slug })
      list.unshift(slug)
      if (list.length > 10) list = list.slice(0, 10)
      wx.setStorageSync('recent_terms', list)
    } catch (e) {}
  },

  _applyFilter() {
    const { allTerms, activeCategory, searchVal, catViewMode } = this.data
    const q = searchVal.trim().toLowerCase()
    var list = allTerms

    if (activeCategory !== 'all') {
      if (catViewMode === 'scene') {
        list = list.filter(function(t) {
          if (!t.scene_tags) return false
          var tags = t.scene_tags.split(',').map(function(s) { return s.trim() })
          return tags.indexOf(activeCategory) !== -1
        })
      } else {
        list = list.filter(function(t) { return t.category === activeCategory })
      }
    }

    if (q) {
      list = list.filter(function(t) {
        return t.name_zh.toLowerCase().indexOf(q) !== -1 ||
               t.name_en.toLowerCase().indexOf(q) !== -1 ||
               (t.aliases || '').toLowerCase().indexOf(q) !== -1
      })
    }
    this.setData({ filtered: list })
  },

  onTermTap(e) {
    const slug = e.currentTarget.dataset.slug
    this._saveRecentTerm(slug)
    wx.navigateTo({ url: '/pages/term/term?slug=' + slug })
  },

  onShowSubmit() {
    this.setData({ submitVisible: true, form: { name_zh: '', name_en: '', short_def: '', category: '' } })
  },

  onHideSubmit() {
    this.setData({ submitVisible: false })
  },

  onFormInput(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ ['form.' + field]: e.detail.value })
  },

  onPickCategory(e) {
    this.setData({ 'form.category': e.currentTarget.dataset.key })
  },

  noop() {},

  onSubmitTerm() {
    const { form, submitting } = this.data
    if (submitting) return
    if (!form.name_zh.trim()) return wx.showToast({ title: '请填写中文名', icon: 'none' })
    if (!form.short_def.trim()) return wx.showToast({ title: '请填写解释', icon: 'none' })
    if (!form.category) return wx.showToast({ title: '请选择分类', icon: 'none' })

    this.setData({ submitting: true })
    const openid = wx.getStorageSync('f1_openid') || null
    api.submitTerm({
      name_zh: form.name_zh.trim(),
      name_en: form.name_en.trim(),
      short_def: form.short_def.trim(),
      category: form.category,
      openid: openid,
    }).then(function() {
      this.setData({ submitting: false, submitVisible: false })
      wx.showToast({ title: '提交成功，等待审核', icon: 'success' })
    }.bind(this)).catch(function() {
      this.setData({ submitting: false })
      wx.showToast({ title: '提交失败，请重试', icon: 'none' })
    }.bind(this))
  },
})
