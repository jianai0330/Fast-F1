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
  },

  onLoad(options) {
    this.postId = options.id
    // 读取本地缓存的用户信息
    const openid   = wx.getStorageSync('f1_openid')   || ''
    const nickname = wx.getStorageSync('f1_nickname') || ''
    this.setData({ openid, nickname })
    this.loadPost()
    this.loadComments()
  },

  async loadPost() {
    try {
      const res = await api.getForumPost(this.postId)
      this.setData({ loading: false, post: res.data })
      wx.setNavigationBarTitle({ title: res.data.section_name || '帖子详情' })
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

  onInputChange(e) {
    this.setData({ inputVal: e.detail.value })
  },

  onInputFocus() {
    // 未注册则跳转注册页
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
      this.setData({ inputVal: '', submitting: false })
      wx.showToast({ title: '已提交，审核后显示', icon: 'none', duration: 2000 })
    } catch (e) {
      this.setData({ submitting: false })
      wx.showToast({ title: typeof e === 'string' ? e : '提交失败', icon: 'none' })
    }
  },

  formatTime(ts) {
    const diff = Date.now() / 1000 - ts
    if (diff < 3600)   return `${Math.floor(diff / 60)}分钟前`
    if (diff < 86400)  return `${Math.floor(diff / 3600)}小时前`
    const d = new Date(ts * 1000)
    return `${d.getMonth() + 1}/${d.getDate()}`
  },
})
