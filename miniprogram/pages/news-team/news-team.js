/* pages/news-team/news-team.js */
const { api } = require('../../utils/api')

Page({
  data: {
    loading: false,
    loadingMore: false,
    error: '',
    items: [],
    page: 1,
    hasMore: true,
    teamSlug: '',
    teamName: '',
    teamColor: '',
  },

  onLoad(options) {
    const teamName = decodeURIComponent(options.teamName || options.team || '')
    this.setData({
      teamSlug: options.team || '',
      teamName,
      teamColor: decodeURIComponent(options.color || '#e10600'),
    })
    wx.setNavigationBarTitle({ title: teamName + ' 资讯' })
    this.loadNews()
  },

  async loadNews() {
    this.setData({ loading: true, error: '' })
    try {
      const res = await api.getNews(1, this.data.teamSlug)
      const items = res.data.items || []
      this.setData({ loading: false, items, page: 1, hasMore: items.length >= 20 })
    } catch (e) {
      this.setData({ loading: false, error: '加载失败，请重试' })
    }
  },

  async loadMore() {
    if (!this.data.hasMore || this.data.loadingMore) return
    const nextPage = this.data.page + 1
    this.setData({ loadingMore: true })
    try {
      const res = await api.getNews(nextPage, this.data.teamSlug)
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

  onReachBottom() { this.loadMore() },

  onPullDownRefresh() {
    this.loadNews().then(() => wx.stopPullDownRefresh())
  },

  onTapNews(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/news-detail/news-detail?id=${id}` })
  },
})
