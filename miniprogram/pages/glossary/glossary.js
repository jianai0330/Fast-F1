/* pages/glossary/glossary.js */
const { api } = require('../../utils/api')

const CATEGORY_COLOR = {
  power_unit: '#e10600',
  aero:       '#4a9eff',
  tyre:       '#f5a623',
  strategy:   '#7ed321',
  rules:      '#9b59b6',
  flag:       '#f0f0f0',
}

const CATEGORY_LABEL = {
  power_unit: '动力单元',
  aero:       '空气动力',
  tyre:       '轮胎',
  strategy:   '策略',
  rules:      '规则',
  flag:       '旗语',
}

const CATEGORY_LIST = [
  { key: 'all',        label: '全部',    color: '#aaa' },
  { key: 'aero',       label: '空气动力', color: '#4a9eff' },
  { key: 'tyre',       label: '轮胎',    color: '#f5a623' },
  { key: 'strategy',   label: '策略',    color: '#7ed321' },
  { key: 'power_unit', label: '动力单元', color: '#e10600' },
  { key: 'rules',      label: '规则',    color: '#9b59b6' },
  { key: 'flag',       label: '旗语',    color: '#f0f0f0' },
]

Page({
  data: {
    loading: true,
    allTerms: [],       // 全量数据
    filtered: [],       // 当前展示
    activeCategory: 'all',
    searchVal: '',
    categories: CATEGORY_LIST,
  },

  onLoad() {
    this.loadTerms()
  },

  async loadTerms() {
    this.setData({ loading: true })
    try {
      const res = await api.getTerms()
      const allTerms = (res.data || []).map(t => ({
        ...t,
        color: CATEGORY_COLOR[t.category] || '#aaa',
        category_label: CATEGORY_LABEL[t.category] || t.category,
      }))
      this.setData({ loading: false, allTerms })
      this._applyFilter()
    } catch (e) {
      this.setData({ loading: false })
    }
  },

  onCategoryTap(e) {
    const key = e.currentTarget.dataset.key
    this.setData({ activeCategory: key })
    this._applyFilter()
  },

  onSearchInput(e) {
    this.setData({ searchVal: e.detail.value })
    this._applyFilter()
  },

  onSearchClear() {
    this.setData({ searchVal: '' })
    this._applyFilter()
  },

  _applyFilter() {
    const { allTerms, activeCategory, searchVal } = this.data
    const q = searchVal.trim().toLowerCase()
    let list = allTerms
    if (activeCategory !== 'all') {
      list = list.filter(t => t.category === activeCategory)
    }
    if (q) {
      list = list.filter(t =>
        t.name_zh.toLowerCase().includes(q) ||
        t.name_en.toLowerCase().includes(q) ||
        (t.aliases || '').toLowerCase().includes(q)
      )
    }
    this.setData({ filtered: list })
  },

  onTermTap(e) {
    const slug = e.currentTarget.dataset.slug
    wx.navigateTo({ url: `/pages/term/term?slug=${slug}` })
  },
})
