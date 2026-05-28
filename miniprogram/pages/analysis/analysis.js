const { api } = require('../../utils/api')

Page({
  data: {
    year: 2026,
    round: null,
    d1: 'ALB',
    d2: 'ALO',
    session: 'Q',
    loading: false,
    error: '',
    report: '',
    metrics: null,
    cached: false,
    // 各维度折叠状态
    expanded: {
      conclusion: true,
      sectors: false,
      corners: false,
      straights: false,
      tyre: false,
    }
  },

  onLoad(options) {
    this.setData({
      year: parseInt(options.year || 2026),
      round: parseInt(options.round),
      d1: options.d1 || 'ALB',
      d2: options.d2 || 'ALO',
      session: options.session || 'Q',
    })
    this.loadAnalysis()
  },

  async loadAnalysis() {
    const { year, round, d1, d2, session } = this.data
    this.setData({ loading: true, error: '' })
    try {
      const res = await api.getAnalysis(year, round, d1, d2, session)
      const data = res.data
      // 按 ## 标题把 report 拆分成段落，方便渲染
      const sections = this.parseReport(data.report || '')
      this.setData({
        loading: false,
        report: data.report || '',
        sections,
        metrics: data.metrics,
        cached: data.cached || false,
      })
    } catch (e) {
      this.setData({ loading: false, error: typeof e === 'string' ? e : 'AI 分析加载失败' })
    }
  },

  // 把 Markdown 按 ## 标题拆成段落数组
  parseReport(text) {
    const lines = text.split('\n')
    const sections = []
    let current = null
    for (const line of lines) {
      if (line.startsWith('## ')) {
        if (current) sections.push(current)
        current = { title: line.replace('## ', '').trim(), content: [], expanded: true }
      } else if (current) {
        current.content.push(line)
      }
    }
    if (current) sections.push(current)
    // content 合并成字符串
    return sections.map(s => ({ ...s, content: s.content.join('\n').trim() }))
  },

  onSectionToggle(e) {
    const idx = e.currentTarget.dataset.idx
    const sections = this.data.sections
    sections[idx].expanded = !sections[idx].expanded
    this.setData({ sections })
  },

  onRefresh() {
    this.loadAnalysis()
  },
})
