/* pages/forum-create/forum-create.js */
const { api } = require('../../utils/api')

Page({
  data: {
    sectionId: null,
    sectionName: '',
    title: '',
    content: '',
    titleLen: 0,
    contentLen: 0,
    submitting: false,
    openid: '',
    newsId: null,
    curatedId: null,
    quote: '',      // 引用内容（展示用）
    _loaded: false, // 标记 onLoad 是否已执行过
  },

  onLoad(options) {
    const prefillTitle = options.prefillTitle ? decodeURIComponent(options.prefillTitle) : ''
    const quote = options.hasQuote ? (wx.getStorageSync('f1_pending_quote') || '') : ''
    wx.removeStorageSync('f1_pending_quote')
    const prefillContent = quote ? `> ${quote}\n\n` : ''
    const openid = wx.getStorageSync('f1_openid') || ''
    this.setData({
      sectionId: parseInt(options.sectionId),
      sectionName: decodeURIComponent(options.sectionName || ''),
      title: prefillTitle,
      titleLen: prefillTitle.length,
      content: prefillContent,
      contentLen: prefillContent.length,
      newsId: options.newsId ? parseInt(options.newsId) : null,
      curatedId: options.curatedId ? parseInt(options.curatedId) : null,
      quote,
      openid,
      _loaded: true,
    })
    // 没登录：跳注册，注册取消则直接返回（不留在发帖页）
    if (!openid) {
      wx.navigateTo({
        url: '/pages/forum-register/forum-register',
        events: {
          // 注册成功后注册页主动通知发帖页
          registerSuccess: (data) => {
            this.setData({ openid: data.openid })
          }
        },
        fail: () => wx.navigateBack()
      })
    }
  },

  onShow() {
    const openid = wx.getStorageSync('f1_openid') || ''
    if (openid) {
      this.setData({ openid })
    }
  },

  onTitleInput(e) {
    const val = e.detail.value
    this.setData({ title: val, titleLen: val.length })
  },

  onContentInput(e) {
    const val = e.detail.value
    this.setData({ content: val, contentLen: val.length })
  },

  async onSubmit() {
    const { title, content, sectionId, openid, submitting, newsId, curatedId } = this.data
    if (submitting) return
    if (!title.trim()) { wx.showToast({ title: '请输入标题', icon: 'none' }); return }
    if (!content.trim()) { wx.showToast({ title: '请输入正文', icon: 'none' }); return }

    this.setData({ submitting: true })
    try {
      await api.createPost(sectionId, title.trim(), content.trim(), openid, newsId, curatedId)
      wx.setStorageSync('forum_posts_dirty', 1)
      wx.showToast({ title: '发帖成功！', icon: 'success', duration: 800 })
      setTimeout(() => wx.navigateBack(), 300)
    } catch (e) {
      this.setData({ submitting: false })
      wx.showToast({ title: typeof e === 'string' ? e : '提交失败', icon: 'none' })
    }
  },
})
