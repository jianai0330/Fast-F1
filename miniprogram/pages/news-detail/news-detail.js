/* pages/news-detail/news-detail.js */
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

const LEVEL_LABEL = { 1: '基础', 2: '进阶', 3: '高阶' }

Page({
  data: {
    loading: true,
    error: '',
    item: null,
    polling: false,
    pollCount: 0,
    MAX_POLL: 12,
    analyzeStep: 0,
    triggerLoading: false,
    reanalyzeLoading: false,
    raceImpactConfidence: { level: '', text: '', cleanText: '' },
    relatedPosts: [],
    relatedTotal: 0,
    relatedNews: [],
    termTags: [],
    teamTags: [],
    termCard: null,
    termCardVisible: false,
    showMethodology: false,
  },

  _pollTimer: null,

  onLoad(options) {
    this.newsId = options.id
    wx.setNavigationBarTitle({ title: '资讯详情' })
    const preview = wx.getStorageSync(`news_preview_${this.newsId}`)
    if (preview) {
      this.setData({ loading: false, item: preview })
      wx.removeStorageSync(`news_preview_${this.newsId}`)
    }
    this.loadDetail()
  },

  onShow() {
    if (this.newsId && !this.data.loading) {
      api.getNewsPosts(this.newsId)
        .then(res => {
          const items = (res.data.items || []).slice(0, 3)
          const total = res.data.total || 0
          this.setData({ relatedPosts: items, relatedTotal: total })
        })
        .catch(() => {})
    }
  },

  onUnload() {
    this._stopPoll()
  },

  async loadDetail() {
    if (!this.data.item) this.setData({ loading: true, error: '' })
    try {
      const [detailRes, postsRes, termsRes, teamsRes, relatedRes] = await Promise.all([
        api.getNewsDetail(this.newsId),
        api.getNewsPosts(this.newsId).catch(() => ({ data: { items: [], total: 0 } })),
        api.getTermsByNews(this.newsId).catch(() => ({ data: [] })),
        api.getTeamsByNews(this.newsId).catch(() => ({ data: [] })),
        api.getRelatedNews(this.newsId).catch(() => ({ data: { items: [] } })),
      ])
      const item = detailRes.data
      const termTags = (termsRes.data || []).map(t => ({
        ...t,
        color: CATEGORY_COLOR[t.category] || '#888',
        category_label: CATEGORY_LABEL[t.category] || t.category,
        level_label: LEVEL_LABEL[t.level] || '基础',
      }))
      this.setData({
        loading: false,
        item,
        relatedPosts: (postsRes.data.items || []).slice(0, 3),
        relatedTotal: postsRes.data.total || 0,
        termTags,
        teamTags: teamsRes.data || [],
        relatedNews: relatedRes.data.items || [],
      })
      if (item.analyzed && item.race_impact) {
        this._parseConfidence(item.race_impact)
      }
      wx.setNavigationBarTitle({ title: '资讯详情' })
    } catch (e) {
      this.setData({
        loading: false,
        error: typeof e === 'string' ? e : '加载失败，请返回重试',
      })
    }
  },

  onTeamTap(e) {
    const { slug, name, color } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/news-team/news-team?team=${slug}&teamName=${encodeURIComponent(name)}&color=${encodeURIComponent(color)}`
    })
  },

  onTermTap(e) {
    const slug = e.currentTarget.dataset.slug
    const tag = this.data.termTags.find(t => t.slug === slug)
    if (!tag) return
    this.setData({ termCard: tag, termCardVisible: true })
    api.getTerm(slug).then(res => {
      if (this.data.termCardVisible && this.data.termCard?.slug === slug) {
        this.setData({
          termCard: { ...this.data.termCard, full_def: res.data.full_def }
        })
      }
    }).catch(() => {})
  },

  onCloseTermCard() {
    this.setData({ termCardVisible: false, termCard: null })
  },

  onGoTermDetail(e) {
    const slug = e.currentTarget.dataset.slug || this.data.termCard?.slug
    if (!slug) return
    this.setData({ termCardVisible: false, termCard: null })
    wx.navigateTo({ url: `/pages/term/term?slug=${slug}` })
  },

  onGoForumFromTerm() {
    const item = this.data.item
    if (!item) return
    const rawTitle = '讨论：' + item.title
    const prefillTitle = rawTitle.length > 48 ? rawTitle.slice(0, 48) : rawTitle
    this.setData({ termCardVisible: false, termCard: null })
    wx.navigateTo({
      url: `/pages/forum-create/forum-create?sectionId=35&sectionName=${encodeURIComponent('综合讨论')}&prefillTitle=${encodeURIComponent(prefillTitle)}&newsId=${item.id}`
    })
  },

  _startPoll() {
    this.setData({ polling: true, pollCount: 0, analyzeStep: 0 })
    this._startAnalyzeStepAnimation()
    this._doPoll()
  },

  _startAnalyzeStepAnimation() {
    this._analyzeStepTimers = []
    this._analyzeStepTimers.push(setTimeout(() => this.setData({ analyzeStep: 1 }), 300))
    this._analyzeStepTimers.push(setTimeout(() => this.setData({ analyzeStep: 2 }), 1500))
    this._analyzeStepTimers.push(setTimeout(() => this.setData({ analyzeStep: 3 }), 3000))
    this._analyzeStepLoop = setInterval(() => {
      if (!this.data.polling) {
        clearInterval(this._analyzeStepLoop)
        return
      }
      this.setData({ analyzeStep: 1 })
      setTimeout(() => this.data.polling && this.setData({ analyzeStep: 2 }), 1200)
      setTimeout(() => this.data.polling && this.setData({ analyzeStep: 3 }), 2400)
    }, 4000)
  },

  _stopAnalyzeStepAnimation() {
    if (this._analyzeStepTimers) {
      this._analyzeStepTimers.forEach(t => clearTimeout(t))
    }
    if (this._analyzeStepLoop) {
      clearInterval(this._analyzeStepLoop)
      this._analyzeStepLoop = null
    }
  },

  _doPoll() {
    if (this.data.pollCount >= this.data.MAX_POLL) {
      this.setData({ polling: false })
      return
    }
    this._pollTimer = setTimeout(async () => {
      try {
        const res = await api.getNewsDetail(this.newsId)
        const item = res.data
        this.setData({ item, pollCount: this.data.pollCount + 1 })
        if (item.analyzed) {
          this.setData({ polling: false })
          this._stopAnalyzeStepAnimation()
          wx.setStorageSync('news_list_dirty', 1)
          this._parseConfidence(item.race_impact)
          api.getTermsByNews(this.newsId).then(r => {
            const termTags = (r.data || []).map(t => ({
              ...t,
              color: CATEGORY_COLOR[t.category] || '#888',
              category_label: CATEGORY_LABEL[t.category] || t.category,
              level_label: LEVEL_LABEL[t.level] || '基础',
            }))
            this.setData({ termTags })
          }).catch(() => {})
          // 分析完成后刷新关联资讯
          api.getRelatedNews(this.newsId).then(r => {
            this.setData({ relatedNews: r.data.items || [] })
          }).catch(() => {})
        } else {
          this._doPoll()
        }
      } catch (e) {
        this.setData({ polling: false })
        this._stopAnalyzeStepAnimation()
      }
    }, 3000)
  },

  _stopPoll() {
    if (this._pollTimer) {
      clearTimeout(this._pollTimer)
      this._pollTimer = null
    }
    this._stopAnalyzeStepAnimation()
  },

  _parseConfidence(text) {
    if (!text) {
      this.setData({ raceImpactConfidence: { level: '', text: '', cleanText: '' } })
      return
    }
    const highMatch = text.match(/\[高置信度\]/)
    const medMatch  = text.match(/\[中置信度\]/)
    const lowMatch  = text.match(/\[低置信度\]/)
    let level = ''
    let levelText = ''
    if (highMatch) { level = 'high'; levelText = '高置信度' }
    else if (medMatch) { level = 'medium'; levelText = '中置信度' }
    else if (lowMatch) { level = 'low'; levelText = '低置信度' }
    const cleanText = text.replace(/\[(?:高|中|低)置信度\]/g, '').trim()
    this.setData({
      raceImpactConfidence: { level, text: levelText, cleanText }
    })
  },

  async onTriggerAnalyze() {
    if (this.data.triggerLoading || this.data.polling) return
    this.setData({ triggerLoading: true })
    try {
      await api.triggerAnalyzePublic(this.newsId)
      this.setData({ triggerLoading: false })
      this._startPoll()
    } catch (e) {
      this.setData({ triggerLoading: false })
      wx.setStorageSync('news_list_dirty', 1)
      this.loadDetail()
    }
  },

  async onReanalyze() {
    if (this.data.reanalyzeLoading || this.data.polling) return
    wx.showModal({
      title: '重新生成解读',
      content: '将清除当前解读并重新分析，约需 15~30 秒，确定吗？',
      confirmText: '确定',
      cancelText: '取消',
      success: async ({ confirm }) => {
        if (!confirm) return
        this.setData({ reanalyzeLoading: true })
        try {
          await api.triggerAnalyzePublic(this.newsId, true)
          this.setData({
            reanalyzeLoading: false,
            item: { ...this.data.item, analyzed: false, tech_points: '', plain_explain: '', race_impact: '' },
          })
          this._startPoll()
        } catch (e) {
          this.setData({ reanalyzeLoading: false })
          wx.showToast({ title: '触发失败', icon: 'none' })
        }
      },
    })
  },

  onQuote(e) {
    const { label, content } = e.currentTarget.dataset
    const item = this.data.item
    if (!item) return
    const rawTitle = '讨论：' + item.title
    const prefillTitle = rawTitle.length > 48 ? rawTitle.slice(0, 48) : rawTitle
    const quote = `【${label}】${content}`
    wx.setStorageSync('f1_pending_quote', quote)
    wx.navigateTo({
      url: `/pages/forum-create/forum-create?sectionId=35&sectionName=${encodeURIComponent('综合讨论')}&prefillTitle=${encodeURIComponent(prefillTitle)}&newsId=${item.id}&hasQuote=1`
    })
  },

  onGoForum() {
    const item = this.data.item
    if (!item) return
    const rawTitle = '讨论：' + item.title
    const prefillTitle = rawTitle.length > 48 ? rawTitle.slice(0, 48) : rawTitle
    wx.navigateTo({
      url: `/pages/forum-create/forum-create?sectionId=35&sectionName=${encodeURIComponent('综合讨论')}&prefillTitle=${encodeURIComponent(prefillTitle)}&newsId=${item.id}&newsTitle=${encodeURIComponent(item.title)}`
    })
  },

  onViewAllPosts() {
    wx.navigateTo({
      url: `/pages/forum-section/forum-section?id=35&name=${encodeURIComponent('综合讨论')}`
    })
  },

  onGoPost(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/forum-post/forum-post?id=${id}` })
  },

  onGoRelatedNews(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/news-detail/news-detail?id=${id}` })
  },

  noop() {},

  onToggleMethodology() {
    this.setData({ showMethodology: !this.data.showMethodology })
  },

  onOpenUrl() {
    const item = this.data.item
    if (!item?.url) return
    wx.setClipboardData({
      data: item.url,
      success() {
        wx.showToast({ title: '链接已复制，请在浏览器打开', icon: 'none', duration: 2500 })
      }
    })
  },

  noop() {},
})
