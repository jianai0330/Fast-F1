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
    trackName: '',
    // 分析步骤流程
    showPipeline: false,
    currentStep: 0,
    // 方法论面板
    showMethodology: false,
    knowledgeSize: '1884',
    reportSummary: null,
    // 各维度折叠状态
    userTriggerNeeded: false,
    feedbackData: null,
    feedbackLoading: false,
    expanded: {
      conclusion: true,
      sectors: false,
      corners: false,
      straights: false,
      tyre: false,
    },
    // 悬浮查词
    termSheetVisible: false,
    termQuery: '',
    termResults: [],
    popularTerms: [],
    selectedTerm: null,
    allTerms: [],
    fabX: 280,
    fabY: 500,
  },

  onLoad(options) {
    this.setData({
      year: parseInt(options.year || 2026),
      round: parseInt(options.round),
      d1: options.d1 || 'ALB',
      d2: options.d2 || 'ALO',
      session: options.session || 'Q',
    })
    this.tryLoadCached()
    this.loadTermsData()
  },

  // 只从本地缓存加载，不触发 API 调用（省 token）
  tryLoadCached() {
    const { year, round, d1, d2, session } = this.data
    try {
      const key = `f1cache:/analysis:${year}:${round}:${d1}:${d2}:${session}`
      const raw = wx.getStorageSync(key)
      if (raw && raw.data && raw.data.data) {
        const data = raw.data.data
        const sections = this.parseReport(data.report || '')
        const reportSummary = this.buildReportSummary(data.metrics, sections, true)
        this.setData({
          report: data.report || '',
          sections,
          metrics: data.metrics,
          cached: true,
          trackName: data.track_name || '',
          reportSummary,
          userTriggerNeeded: false,
        })
        return
      }
    } catch (e) {}
    // 无缓存，显示用户触发按钮
    this.setData({ userTriggerNeeded: true, loading: false })
  },

  // 用户点击「开始分析」按钮时触发
  onStartAnalysis() {
    this.loadAnalysis()
  },

  async loadAnalysis(force = false) {
    const { year, round, d1, d2, session } = this.data
    this.setData({ loading: true, error: '', showPipeline: false, currentStep: 0 })
    this.startPipelineAnimation()
    try {
      const res = await api.getAnalysis(year, round, d1, d2, session, force)
      const data = res.data
      // 按 ## 标题把 report 拆分成段落，方便渲染
      const sections = this.parseReport(data.report || '')
      const reportSummary = this.buildReportSummary(data.metrics, sections, data.cached || false)
      // 提取赛道名称
      let trackName = data.track_name || data.race_name || ''
      this.setData({
        loading: false,
        report: data.report || '',
        sections,
        metrics: data.metrics,
        cached: data.cached || false,
        trackName,
        reportSummary,
        showPipeline: false,
      })
      this.loadFeedback()
    } catch (e) {
      this.setData({ loading: false, error: typeof e === 'string' ? e : 'AI 分析加载失败', showPipeline: false })
    }
  },

  buildReportSummary(metrics, sections, cached) {
    const summary = {
      sectionCount: sections.length,
      sourceLabel: cached ? '缓存复盘' : '实时生成',
      keyLine: '',
      metricCards: [],
    }

    if (sections.length > 0) {
      const firstSection = sections[0].content || ''
      summary.keyLine = firstSection.split('\n').find(Boolean) || 'AI 已完成本场对比复盘。'
    } else {
      summary.keyLine = 'AI 已完成本场对比复盘。'
    }

    if (metrics && typeof metrics === 'object') {
      const cards = []
      Object.entries(metrics).slice(0, 3).forEach(([key, value]) => {
        cards.push({
          label: key,
          value: typeof value === 'number' ? String(value) : String(value),
        })
      })
      summary.metricCards = cards
    }

    return summary
  },

  // 加载时展示步骤进度
  startPipelineAnimation() {
    this.setData({ showPipeline: true, currentStep: 0 })
    this._pipelineTimers = []
    this._pipelineTimers.push(setTimeout(() => this.setData({ currentStep: 1 }), 300))
    this._pipelineTimers.push(setTimeout(() => this.setData({ currentStep: 2 }), 800))
    this._pipelineTimers.push(setTimeout(() => this.setData({ currentStep: 3 }), 1600))
    this._pipelineTimers.push(setTimeout(() => this.setData({ currentStep: 4 }), 2400))
  },

  onUnload() {
    if (this._pipelineTimers) {
      this._pipelineTimers.forEach(t => clearTimeout(t))
    }
  },

  // 把 Markdown 按 ## 标题拆成段落数组
  parseReport(text) {
    // 各section对应的数据来源
    const dataSourceMap = {
      '赛道总结': 'FastF1 遥测数据 + 规则引擎指标',
      '总结': 'FastF1 遥测数据 + 规则引擎指标',
      '赛段分析': 'FastF1 扇区计时数据',
      '弯角分析': 'FastF1 弯角遥测 + 赛道知识库',
      '直道分析': 'FastF1 速度遥测数据',
      '轮胎策略': 'FastF1 轮胎数据 + 策略知识库',
      '制动分析': 'FastF1 制动遥测数据',
    }
    const lines = text.split('\n')
    const sections = []
    let current = null
    for (const line of lines) {
      if (line.startsWith('## ')) {
        if (current) sections.push(current)
        const title = line.replace('## ', '').trim()
        current = { title, content: [], expanded: true, dataSource: dataSourceMap[title] || 'FastF1 遥测数据 + AI推理' }
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

  onToggleMethodology() {
    this.setData({ showMethodology: !this.data.showMethodology })
  },

  onRefresh() {
    this.loadAnalysis(true)
  },

  // ── 分析反馈 ──────────────────────────────────────
  async loadFeedback() {
    try {
      const { year, round, d1, d2, session } = this.data
      const raw = `${year}-${round}-${d1}-${d2}-${session}`
      const ck = this.md5(raw)
      const openid = wx.getStorageSync('f1_openid') || ''
      const res = await api.getAnalysisFeedback(ck, openid)
      if (res && res.data) {
        this.setData({ feedbackData: res.data })
      }
    } catch (e) {}
  },

  onFeedback(e) {
    const rating = parseInt(e.currentTarget.dataset.rating)
    if (this.data.feedbackLoading) return
    this.setData({ feedbackLoading: true })
    const { year, round, d1, d2, session } = this.data
    const raw = `${year}-${round}-${d1}-${d2}-${session}`
    const ck = this.md5(raw)
    const openid = wx.getStorageSync('f1_openid') || ''
    api.submitAnalysisFeedback(ck, 'driver', openid, rating).then(res => {
      if (res && res.data) {
        this.setData({ feedbackData: res.data, feedbackLoading: false })
      }
    }).catch(() => {
      this.setData({ feedbackLoading: false })
    })
  },

  md5(str) {
    // 简单的 JS MD5 实现，用于生成缓存 key
    let hash = 0
    for (let i = 0; i < str.length; i++) {
      const chr = str.charCodeAt(i)
      hash = ((hash << 5) - hash) + chr
      hash |= 0
    }
    return 'hash_' + Math.abs(hash).toString(16)
  },

  // ── 悬浮查词 ──────────────────────────────────────
  async loadTermsData() {
    try {
      const [termsRes, popularRes] = await Promise.all([
        api.getTerms(),
        api.getTermsPopular()
      ])
      this.setData({
        allTerms: termsRes.data || [],
        popularTerms: (popularRes.data || []).map(slug => {
          const t = (termsRes.data || []).find(t => t.slug === slug)
          return t || { slug, name_zh: slug }
        })
      })
    } catch(e) { console.error('loadTermsData', e) }
  },

  onTermFabTap() {
    this.setData({ termSheetVisible: true })
  },

  closeTermSheet() {
    this.setData({ termSheetVisible: false, termQuery: '', termResults: [], selectedTerm: null })
  },

  onTermSearch(e) {
    const query = e.detail.value.toLowerCase().trim()
    this.setData({ termQuery: query })
    if (!query) { this.setData({ termResults: [] }); return }

    const results = this.data.allTerms.filter(t => {
      const searchFields = `${t.name_zh} ${t.name_en} ${t.aliases || ''}`.toLowerCase()
      return searchFields.includes(query)
    }).slice(0, 5)

    this.setData({ termResults: results })
  },

  onTermResultTap(e) {
    const slug = e.currentTarget.dataset.slug
    this.closeTermSheet()
    wx.navigateTo({ url: `/pages/term/term?slug=${slug}` })
  },

  goTermDetail() {
    if (this.data.selectedTerm) {
      this.closeTermSheet()
      wx.navigateTo({ url: `/pages/term/term?slug=${this.data.selectedTerm.slug}` })
    }
  },
})
