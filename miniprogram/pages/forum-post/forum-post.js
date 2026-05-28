/* pages/forum-post/forum-post.js */
const { api } = require('../../utils/api')

Page({
  data: {
    loading: true,
    post: null,
    comments: [],
    inputVal: '',
    submitting: false,
    openid: '',
    nickname: '',
    likes: 0,
    dislikes: 0,
    myVote: null,   // 'like' | 'dislike' | null
  },

  onLoad(options) {
    this.postId = options.id
    const openid   = wx.getStorageSync('f1_openid')   || ''
    const nickname = wx.getStorageSync('f1_nickname') || ''
    this.setData({ openid, nickname })
    this.loadPost()
    this.loadComments()
  },

  onShow() {
    const openid   = wx.getStorageSync('f1_openid')   || ''
    const nickname = wx.getStorageSync('f1_nickname') || ''
    if (openid !== this.data.openid) {
      this.setData({ openid, nickname })
    }
  },

  async loadPost() {
    try {
      // 每次 loadPost 都重新读 Storage，防止开发者工具重编译后 openid 丢失
      const openid = wx.getStorageSync('f1_openid') || ''
      const nickname = wx.getStorageSync('f1_nickname') || ''
      const [postRes, likeRes] = await Promise.all([
        api.getForumPost(this.postId),
        api.getLike(this.postId, openid).catch(() => ({ data: { likes: 0, dislikes: 0, my_vote: null } })),
      ])
      this.setData({
        loading: false,
        post: postRes.data,
        openid,
        nickname,
        likes: likeRes.data.likes || 0,
        dislikes: likeRes.data.dislikes || 0,
        myVote: likeRes.data.my_vote || null,
      })
      wx.setNavigationBarTitle({ title: postRes.data.section_name || '帖子详情' })
    } catch (e) {
      this.setData({ loading: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  async loadComments() {
    try {
      const res = await api.getForumComments(this.postId)
      this.setData({ comments: res.data.items || [] })
    } catch (e) {}
  },

  // ── 点赞 / 点踩 ──────────────────────────────
  async onLike(e) {
    const type = e.currentTarget.dataset.type
    if (!this.data.openid) {
      wx.navigateTo({ url: '/pages/forum-register/forum-register' })
      return
    }
    try {
      const res = await api.likePost(this.postId, this.data.openid, type)
      this.setData({
        likes: res.data.likes,
        dislikes: res.data.dislikes,
        myVote: res.data.my_vote,
      })
    } catch (e) {
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  // ── 删帖 ─────────────────────────────────────
  onDeletePost() {
    const { post, openid } = this.data
    if (!post || post.author_openid !== openid) return
    wx.showModal({
      title: '确认删除',
      content: '删除后无法恢复，确定吗？',
      confirmColor: '#e10600',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await api.deletePost(this.postId, openid)
          wx.showToast({ title: '已删除', icon: 'success', duration: 800 })
          setTimeout(() => wx.navigateBack(), 800)
        } catch (e) {
          wx.showToast({ title: typeof e === 'string' ? e : '删除失败', icon: 'none' })
        }
      }
    })
  },

  onInputChange(e) {
    this.setData({ inputVal: e.detail.value })
  },

  onInputFocus() {
    if (!this.data.openid) {
      wx.navigateTo({ url: '/pages/forum-register/forum-register' })
    }
  },

  async onSubmitComment() {
    const content = this.data.inputVal.trim()
    if (!content) return
    if (!this.data.openid) {
      wx.navigateTo({ url: '/pages/forum-register/forum-register' })
      return
    }
    this.setData({ submitting: true })
    try {
      await api.createComment(this.postId, content, this.data.openid)
      const newComment = {
        id: Date.now(),
        content,
        author_nickname: this.data.nickname || wx.getStorageSync('f1_nickname') || '我',
        created_at: Math.floor(Date.now() / 1000),
      }
      this.setData({
        inputVal: '',
        submitting: false,
        comments: [...this.data.comments, newComment],
      })
      wx.showToast({ title: '评论成功！', icon: 'success', duration: 800 })
      setTimeout(() => this.loadComments(), 1000)
    } catch (e) {
      this.setData({ submitting: false })
      wx.showToast({ title: typeof e === 'string' ? e : '提交失败', icon: 'none' })
    }
  },

  onGoNews() {
    const newsId = this.data.post?.news_id
    if (!newsId) return
    wx.navigateTo({ url: `/pages/news-detail/news-detail?id=${newsId}` })
  },

  formatTime(ts) {
    const diff = Date.now() / 1000 - ts
    if (diff < 3600)   return `${Math.floor(diff / 60)}分钟前`
    if (diff < 86400)  return `${Math.floor(diff / 3600)}小时前`
    const d = new Date(ts * 1000)
    return `${d.getMonth() + 1}/${d.getDate()}`
  },
})
