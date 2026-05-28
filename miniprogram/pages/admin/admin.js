/* pages/admin/admin.js */
const { api } = require('../../utils/api')

const ADMIN_TOKEN = 'f1admin2026'

Page({
  data: {
    unlocked: false,
    pwInput: '',
    activeTab: 'posts',   // posts | comments | terms
    posts: [],
    comments: [],
    terms: [],
    loading: false,
    // 分析进度
    analyzing: false,
    analyzeStep: '',      // 当前步骤文字
    analyzeProgress: 0,   // 0-100
    analyzeTotal: 0,
    analyzeDone: 0,
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
      const [pr, cr, tr] = await Promise.all([
        api.adminGetPosts(),
        api.adminGetComments(),
        api.adminGetTerms(),
      ])
      this.setData({
        loading: false,
        posts:    pr.data.items || [],
        comments: cr.data.items || [],
        terms:    tr.data.items || [],
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

  async onApproveTerm(e) {
    const id = e.currentTarget.dataset.id
    try {
      await api.adminApproveTerm(id)
      this.setData({ terms: this.data.terms.filter(t => t.id !== id) })
      wx.showToast({ title: '已通过', icon: 'success' })
    } catch (e) {
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  async onRejectTerm(e) {
    const id = e.currentTarget.dataset.id
    try {
      await api.adminRejectTerm(id)
      this.setData({ terms: this.data.terms.filter(t => t.id !== id) })
      wx.showToast({ title: '已拒绝', icon: 'none' })
    } catch (e) {
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  // ── 爬取 + 逐条 AI 分析（带进度条）────────
  async onCrawl() {
    if (this.data.analyzing) return
    this.setData({
      analyzing: true,
      analyzeStep: '正在爬取最新资讯...',
      analyzeProgress: 0,
      analyzeTotal: 0,
      analyzeDone: 0,
    })

    try {
      // Step 1: 只爬取
      const crawlRes = await api.adminCrawlOnly()
      const pending = crawlRes.data.pending || []
      const added = crawlRes.data.crawl?.added || crawlRes.data.added || 0

      if (pending.length === 0) {
        this.setData({ analyzing: false, analyzeStep: '' })
        wx.showToast({ title: '爬取完成，无待分析内容', icon: 'success' })
        return
      }

      // Step 2: 逐条分析
      this.setData({
        analyzeTotal: pending.length,
        analyzeDone: 0,
        analyzeStep: `新增 ${added} 条，开始 AI 分析...`,
        analyzeProgress: 5,
      })

      let success = 0
      let failed = 0
      for (let i = 0; i < pending.length; i++) {
        const item = pending[i]
        const shortTitle = item.title.length > 18
          ? item.title.substring(0, 18) + '...'
          : item.title
        this.setData({
          analyzeStep: `分析中 (${i + 1}/${pending.length})\n${shortTitle}`,
          analyzeProgress: Math.round(5 + (i / pending.length) * 90),
          analyzeDone: i,
        })
        try {
          await api.adminAnalyzeOne(item.id)
          success++
        } catch (e) {
          failed++
        }
      }

      this.setData({
        analyzeProgress: 100,
        analyzeDone: pending.length,
        analyzeStep: `完成！成功 ${success} 条${failed > 0 ? `，失败 ${failed} 条` : ''}`,
      })
      setTimeout(() => {
        this.setData({ analyzing: false, analyzeStep: '', analyzeProgress: 0 })
        this.loadAll()
      }, 2000)

    } catch (e) {
      this.setData({ analyzing: false, analyzeStep: '操作失败，请重试', analyzeProgress: 0 })
      setTimeout(() => this.setData({ analyzeStep: '' }), 2000)
    }
  },
})
