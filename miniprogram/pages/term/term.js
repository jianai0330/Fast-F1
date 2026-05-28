/* pages/term/term.js */
const { api } = require('../../utils/api')

const CATEGORY_COLOR = {
  power_unit: '#4a9eff',
  aero:       '#4caf50',
  tyre:       '#ff7043',
  strategy:   '#f5a623',
  rules:      '#ce93d8',
  flag:       '#aaa',
}

const CATEGORY_LABEL = {
  power_unit: '动力单元', aero: '空气动力', tyre: '轮胎',
  strategy: '策略', rules: '规则', flag: '旗语',
}

const LEVEL_LABEL = { 1: '基础', 2: '进阶', 3: '高阶' }

Page({
  data: {
    loading: true,
    error: '',
    term: null,
    relatedTerms: [],
  },

  onLoad(options) {
    this.slug = options.slug
    wx.setNavigationBarTitle({ title: '术语详情' })
    this.loadTerm()
  },

  async loadTerm() {
    this.setData({ loading: true, error: '' })
    try {
      const res = await api.getTerm(this.slug)
      const t = res.data
      const color = CATEGORY_COLOR[t.category] || '#aaa'
      const term = {
        ...t,
        color,
        category_label: CATEGORY_LABEL[t.category] || t.category,
        level_label: LEVEL_LABEL[t.level] || '基础',
        aliases_list: (t.aliases || '').split(',').map(s => s.trim()).filter(Boolean),
        related_list: (t.related_slugs || '').split(',').map(s => s.trim()).filter(Boolean),
      }
      this.setData({ loading: false, term })
      wx.setNavigationBarTitle({ title: t.name_zh })

      // 拉相关术语
      if (term.related_list.length > 0) {
        Promise.all(term.related_list.map(s => api.getTerm(s).catch(() => null)))
          .then(results => {
            const relatedTerms = results
              .filter(Boolean)
              .map(r => ({
                ...r.data,
                color: CATEGORY_COLOR[r.data.category] || '#aaa',
                level_label: LEVEL_LABEL[r.data.level] || '基础',
              }))
            this.setData({ relatedTerms })
          })
      }
    } catch (e) {
      this.setData({ loading: false, error: '加载失败，请返回重试' })
    }
  },

  onGoRelated(e) {
    const slug = e.currentTarget.dataset.slug
    wx.navigateTo({ url: `/pages/term/term?slug=${slug}` })
  },
})
