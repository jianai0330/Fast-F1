/* pages/forum-section/forum-section.js */
const { api } = require('../../utils/api')

Page({
  data: {
    sectionId: null,
    sectionName: '',
    loading: false,
    loadingMore: false,
    items: [],
    page: 1,
    hasMore: true,
    sortMode: 'latest',  // 'latest' | 'hot'
    hotPosts: [],
  },

  _forumDirtyKey: 'forum_posts_dirty',

  onLoad(options) {
    const name = decodeURIComponent(options.name || '论坛')
    this.setData({ sectionId: parseInt(options.id), sectionName: name })
    wx.setNavigationBarTitle({ title: name })
    this.loadHotPosts()
    this.loadPosts(true)
  },

  async loadHotPosts() {
    try {
      const res = await api.getForumPosts(this.data.sectionId, 1, 'hot')
      const items = (res.data.items || []).slice(0, 3)
      this.setData({ hotPosts: items })
    } catch (e) {
      // 热帖加载失败静默处理，不影响主列表
    }
  },

  onShow() {
    const dirty = wx.getStorageSync(this._forumDirtyKey)
    if (dirty) wx.removeStorageSync(this._forumDirtyKey)
    // 从发帖页返回后按需刷新；首次打开时 loading=true，跳过避免双重请求
    if (dirty && this.data.sectionId && !this.data.loading) {
      this.loadHotPosts()
      this.loadPosts(true)
    }
  },

  onPullDownRefresh() {
    this.loadPosts(true).then(() => wx.stopPullDownRefresh())
  },

  onReachBottom() {
    if (!this.data.hasMore || this.data.loadingMore) return
    this.loadMore()
  },

  onSwitchSort(e) {
    const sort = e.currentTarget.dataset.sort
    if (sort === this.data.sortMode) return
    this.setData({ sortMode: sort })
    this.loadPosts(true)
  },

  async loadPosts(refresh = false) {
    if (refresh) this.setData({ loading: true, page: 1, hasMore: true })
    try {
      const res = await api.getForumPosts(this.data.sectionId, 1, this.data.sortMode)
      const items = res.data.items || []
      this.setData({ loading: false, items, page: 1, hasMore: items.length >= 20 })
    } catch (e) {
      this.setData({ loading: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  async loadMore() {
    const nextPage = this.data.page + 1
    this.setData({ loadingMore: true })
    try {
      const res = await api.getForumPosts(this.data.sectionId, nextPage, this.data.sortMode)
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

  onTapPost(e) {
    wx.navigateTo({ url: `/pages/forum-post/forum-post?id=${e.currentTarget.dataset.id}` })
  },

  onCreatePost() {
    wx.navigateTo({
      url: `/pages/forum-create/forum-create?sectionId=${this.data.sectionId}&sectionName=${encodeURIComponent(this.data.sectionName)}`
    })
  },

  formatTime(ts) {
    const diff = Date.now() / 1000 - ts
    if (diff < 3600)   return `${Math.floor(diff / 60)}分钟前`
    if (diff < 86400)  return `${Math.floor(diff / 3600)}小时前`
    if (diff < 604800) return `${Math.floor(diff / 86400)}天前`
    const d = new Date(ts * 1000)
    return `${d.getMonth() + 1}/${d.getDate()}`
  },
})
