/* pages/admin/admin.js */
const { api } = require('../../utils/api')

const ADMIN_TOKEN = 'f1admin2026'

Page({
  data: {
    unlocked: false,
    pwInput: '',
    activeTab: 'posts',   // posts | comments
    posts: [],
    comments: [],
    loading: false,
    // 长按解锁计时
    pressTimer: null,
  },

  // ── 长按解锁 ───────────────────────────────
  onLogoLongPress() {
    wx.showModal({
      title: '管理员入口',
      editable: true,
      placeholderText: '输入管理密码',
      success: (res) => {
        if (res.confirm && res.content === ADMIN_TOKEN) {
          this.setData({ unlocked: true })
          this.loadAll()
        } else if (res.confirm) {
          wx.showToast({ title: '密码错误', icon: 'none' })
        }
      }
    })
  },

  onTabChange(e) {
    this.setData({ activeTab: e.currentTarget.dataset.tab })
  },

  async loadAll() {
    this.setData({ loading: true })
    try {
      const [pr, cr] = await Promise.all([
        api.adminGetPosts(),
        api.adminGetComments(),
      ])
      this.setData({
        loading: false,
        posts:    pr.data.items || [],
        comments: cr.data.items || [],
      })
    } catch (e) {
      this.setData({ loading: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  // ── 帖子操作 ──────────────────────────────
  async onApprovePost(e) {
    const id = e.currentTarget.dataset.id
    try {
      await api.adminApprovePost(id)
      this.setData({ posts: this.data.posts.filter(p => p.id !== id) })
      wx.showToast({ title: '已通过', icon: 'success' })
    } catch (e) {
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  async onRejectPost(e) {
    const id = e.currentTarget.dataset.id
    try {
      await api.adminRejectPost(id)
      this.setData({ posts: this.data.posts.filter(p => p.id !== id) })
      wx.showToast({ title: '已拒绝', icon: 'none' })
    } catch (e) {
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  // ── 评论操作 ──────────────────────────────
  async onApproveComment(e) {
    const id = e.currentTarget.dataset.id
    try {
      await api.adminApproveComment(id)
      this.setData({ comments: this.data.comments.filter(c => c.id !== id) })
      wx.showToast({ title: '已通过', icon: 'success' })
    } catch (e) {
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  async onRejectComment(e) {
    const id = e.currentTarget.dataset.id
    try {
      await api.adminRejectComment(id)
      this.setData({ comments: this.data.comments.filter(c => c.id !== id) })
      wx.showToast({ title: '已拒绝', icon: 'none' })
    } catch (e) {
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  // ── 一键爬取 + AI 分析 ────────────────────
  async onCrawl() {
    wx.showLoading({ title: '爬取中...' })
    try {
      const res = await api.adminCrawl()
      wx.hideLoading()
      const d = res.data
      const crawlInfo = Object.entries(d.crawl || {})
        .map(([src, v]) => `${src}: +${v.added}`)
        .join('\n')
      const analyzeInfo = d.analyze
        ? `AI分析：${d.analyze.success || 0} 条完成`
        : ''
      wx.showModal({
        title: '完成',
        content: [crawlInfo, analyzeInfo].filter(Boolean).join('\n'),
        showCancel: false,
      })
      // 刷新列表
      this.loadAll()
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },
})
