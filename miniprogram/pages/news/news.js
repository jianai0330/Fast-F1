/* pages/news/news.js */
const { api } = require('../../utils/api')

Page({
  data: {
    loading: false,
    loadingMore: false,
    error: '',
    items: [],
    page: 1,
    hasMore: true,
    showRoadmap: false,
    // 车队筛选模式
    teamFilter: null,   // slug
    teamName: '',       // 显示名
    // 搜索
    searchKeyword: '',  // 搜索关键词
    // 语言筛选
    languageTabs: [
      { key: 'all', label: '全部' },
      { key: 'zh', label: '中文' },
      { key: 'en', label: 'English' },
    ],
    activeLanguage: 'all',
    // 精选
    baseUrl: getApp().globalData.BASE_URL,
    curatedItems: [],
    curatedPage: 1,
    curatedLoading: false,
    curatedNoMore: false,
    lastAnalyzedSyncAt: 0,
    lastCuratedLoadAt: 0,
  },

  // 防抖定时器
  _searchTimer: null,
  _newsDirtyKey: 'news_list_dirty',
  _curatedDirtyKey: 'curated_list_dirty',

  onLoad(options) {
    if (options.team) {
      this.setData({ teamFilter: options.team, teamName: decodeURIComponent(options.teamName || options.team) })
      wx.setNavigationBarTitle({ title: `${decodeURIComponent(options.teamName || options.team)} 相关资讯` })
    }
    this.loadNews(true)
    this.loadCurated()
  },

  onShow() {
    wx.showTabBar({ animation: false })
    const now = Date.now()
    const newsDirty = wx.getStorageSync(this._newsDirtyKey)
    const curatedDirty = wx.getStorageSync(this._curatedDirtyKey)
    if (newsDirty) wx.removeStorageSync(this._newsDirtyKey)
    if (curatedDirty) wx.removeStorageSync(this._curatedDirtyKey)

    if ((newsDirty || now - this.data.lastAnalyzedSyncAt > 60000) && this.data.items.length > 0 && !this.data.loading) {
      this._syncAnalyzed()
    }
    if (curatedDirty) {
      this.setData({ curatedItems: [], curatedPage: 1, curatedNoMore: false })
      this.loadCurated()
    }
  },

  async _syncAnalyzed() {
    try {
      const language = this.data.activeLanguage
      const res = await api.getNews(1, this.data.teamFilter, null, language)
      const fresh = res.data.items || []
      const merged = this.data.items.map(old => {
        const hit = fresh.find(n => n.id === old.id)
        return hit ? Object.assign({}, old, { analyzed: hit.analyzed }) : old
      })
      this.setData({ items: merged, lastAnalyzedSyncAt: Date.now() })
    } catch (e) { /* 静默失败 */ }
  },

  onPullDownRefresh() {
    this.loadNews(true).then(() => wx.stopPullDownRefresh())
  },

  onReachBottom() {
    if (!this.data.hasMore || this.data.loadingMore) return
    this.loadMore()
  },

  async loadNews(refresh = false) {
    if (refresh) {
      this.setData({ loading: true, error: '', page: 1, hasMore: true })
    }
    try {
      const keyword = this.data.searchKeyword || null
      const language = this.data.activeLanguage
      const res = await api.getNews(1, this.data.teamFilter, keyword, language)
      const items = res.data.items || []
      this.setData({ loading: false, items, page: 1, hasMore: items.length >= 20 })
    } catch (e) {
      this.setData({ loading: false, error: typeof e === 'string' ? e : '加载失败，请重试' })
    }
  },

  async loadMore() {
    const nextPage = this.data.page + 1
    this.setData({ loadingMore: true })
    try {
      const keyword = this.data.searchKeyword || null
      const language = this.data.activeLanguage
      const res = await api.getNews(nextPage, this.data.teamFilter, keyword, language)
      const newItems = res.data.items || []
      this.setData({
        loadingMore: false,
        items: [...this.data.items, ...newItems],
        page: nextPage,
        hasMore: newItems.length >= 20,
      })
    } catch (e) {
      this.setData({ loadingMore: false })
    }
  },

  onGoGlossary() {
    wx.switchTab({ url: '/pages/glossary/glossary' })
  },

  onTapNews(e) {
    const item = this.data.items.find(n => n.id === e.currentTarget.dataset.id)
    if (!item) return
    wx.setStorageSync(`news_preview_${item.id}`, {
      title: item.title,
      source: item.source,
      summary: item.summary,
      published_at: item.published_at,
      url: item.url,
    })
    wx.navigateTo({ url: `/pages/news-detail/news-detail?id=${item.id}` })
  },

  onShowRoadmap() { this.setData({ showRoadmap: true }) },
  onCloseRoadmap() { this.setData({ showRoadmap: false }) },

  onBack() {
    wx.navigateBack()
  },

  onCopyFeedback() {
    wx.setClipboardData({
      data: 'jianaijane@foxmail.com',
      success: () => wx.showToast({ title: '邮箱已复制', icon: 'success' }),
    })
  },

  // ── 搜索功能 ──────────────────────────────────────
  onSearchInput(e) {
    const val = e.detail.value
    this.setData({ searchKeyword: val })
    // 清除上一次防抖定时器
    if (this._searchTimer) {
      clearTimeout(this._searchTimer)
      this._searchTimer = null
    }
    // 输入为空时立即清空搜索，恢复全部列表
    if (!val.trim()) {
      this.loadNews(true)
      return
    }
    // 300ms 防抖
    this._searchTimer = setTimeout(() => {
      this.loadNews(true)
    }, 300)
  },

  onSearchConfirm() {
    // 点击键盘搜索按钮，立即触发
    if (this._searchTimer) {
      clearTimeout(this._searchTimer)
      this._searchTimer = null
    }
    if (this.data.searchKeyword.trim()) {
      this.loadNews(true)
    }
  },

  onSearchClear() {
    this.setData({ searchKeyword: '' })
    if (this._searchTimer) {
      clearTimeout(this._searchTimer)
      this._searchTimer = null
    }
    this.loadNews(true)
  },

  // ── 语言筛选 Tab ──────────────────────────────────
  onLanguageTab(e) {
    const key = e.currentTarget.dataset.key
    if (key === this.data.activeLanguage) return
    this.setData({ activeLanguage: key })
    this.loadNews(true)
  },

  // ── 精选 ──────────────────────────────────
  async loadCurated() {
    if (this.data.curatedLoading || this.data.curatedNoMore) return
    this.setData({ curatedLoading: true })
    try {
      const res = await api.getCuratedList(this.data.curatedPage)
      const baseUrl = this.data.baseUrl
      const items = (res.data.items || []).map(item => {
        // 图片 URL 处理：cover_image 优先 → snapshot_image 兜底
        let displayImage = ''
        if (item.cover_image) {
          displayImage = item.cover_image.startsWith('http') ? item.cover_image : baseUrl + item.cover_image
        } else if (item.snapshot_image) {
          displayImage = item.snapshot_image.startsWith('http') ? item.snapshot_image : baseUrl + item.snapshot_image
        }
        return {
          ...item,
          displayImage,
          platformLabel: {weibo:'微博',wechat:'公众号',douyin:'抖音',bilibili:'B站',web:'网页'}[item.platform] || '网页',
          typeLabel: {article:'文章',video:'视频',post:'帖子'}[item.content_type] || '文章',
          parsedTags: item.tags ? (() => { try { return JSON.parse(item.tags) } catch(e) { return [] } })() : [],
        }
      })
      this.setData({
        curatedItems: [...this.data.curatedItems, ...items],
        curatedLoading: false,
        curatedNoMore: items.length < 20,
        curatedPage: this.data.curatedPage + 1,
        lastCuratedLoadAt: Date.now(),
      })
    } catch (e) {
      this.setData({ curatedLoading: false })
    }
  },

  onCuratedTap(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/curated-detail/curated-detail?id=${id}` })
  },

  onCuratedImgError(e) {
    // 封面图加载失败，清除 displayImage 显示占位
    const id = e.currentTarget.dataset.id
    const items = this.data.curatedItems.map(item =>
      item.id === id ? { ...item, displayImage: '' } : item
    )
    this.setData({ curatedItems: items })
  },

  goSubmit() {
    wx.navigateTo({ url: '/pages/curated-submit/curated-submit' })
  },

  noop() {},
})
