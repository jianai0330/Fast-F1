/* pages/forum/forum.js */
const { api } = require('../../utils/api')

Page({
  data: {
    loading: true,
    error: '',
    activeTab: 'general',   // general | race | team
    raceSections: [],
    teamSections: [],
    // 综合讨论分区
    generalId: null,
    generalName: '综合讨论',
    generalPosts: [],
    generalLoading: false,
    generalPage: 1,
    generalHasMore: true,
    lastGeneralRefreshAt: 0,
  },

  _forumDirtyKey: 'forum_posts_dirty',

  onLoad() {
    this.loadSections()
  },

  onShow() {
    // 防御性确保 tabBar 可见（修复部分机型从子页面返回后 tabBar 消失的问题）
    wx.showTabBar({ animation: false })
    const dirty = wx.getStorageSync(this._forumDirtyKey)
    if (dirty) wx.removeStorageSync(this._forumDirtyKey)
    // 只在明确有新帖子或首次未加载时刷新，避免每次返回都抖一下
    if (this.data.generalId && dirty) {
      this.loadGeneralPosts(true)
    } else if (this.data.raceSections.length === 0) {
      this.loadSections()
    }
  },

  async loadSections() {
    try {
      const res = await api.getForumSections()
      const race = res.data.race || []
      const team = res.data.team || []

      // 找出综合讨论（slug=general），从 race 列表里摘出来单独处理
      const generalSection = race.find(s => s.slug === 'general')
      const raceSections = race.filter(s => s.slug !== 'general')

      this.setData({
        loading: false,
        raceSections,
        teamSections: team,
        generalId: generalSection ? generalSection.id : null,
        generalName: generalSection ? generalSection.name : '综合讨论',
      })

      // 默认加载综合讨论帖子
      if (generalSection) this.loadGeneralPosts(true)
    } catch (e) {
      this.setData({ loading: false, error: typeof e === 'string' ? e : '加载失败' })
    }
  },

  onTabChange(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab })
    // 切到综合讨论时若还没加载就加载
    if (tab === 'general' && this.data.generalPosts.length === 0 && this.data.generalId) {
      this.loadGeneralPosts(true)
    }
  },

  // ── 综合讨论帖子列表 ──────────────────────────
  async loadGeneralPosts(refresh = false) {
    if (refresh) this.setData({ generalLoading: true, generalPage: 1, generalHasMore: true })
    try {
      const res = await api.getForumPosts(this.data.generalId, 1)
      const items = res.data.items || []
      this.setData({
        generalLoading: false,
        generalPosts: items,
        generalPage: 1,
        generalHasMore: items.length >= 20,
        lastGeneralRefreshAt: Date.now(),
      })
    } catch (e) {
      this.setData({ generalLoading: false })
    }
  },

  async loadGeneralMore() {
    if (!this.data.generalHasMore || this.data.generalLoading) return
    const nextPage = this.data.generalPage + 1
    this.setData({ generalLoading: true })
    try {
      const res = await api.getForumPosts(this.data.generalId, nextPage)
      const newItems = res.data.items || []
      this.setData({
        generalLoading: false,
        generalPosts: [...this.data.generalPosts, ...newItems],
        generalPage: nextPage,
        generalHasMore: newItems.length >= 20,
      })
    } catch (e) {
      this.setData({ generalLoading: false })
    }
  },

  onGeneralScrollBottom() {
    this.loadGeneralMore()
  },

  onTapPost(e) {
    wx.navigateTo({ url: `/pages/forum-post/forum-post?id=${e.currentTarget.dataset.id}` })
  },

  goToChatroom() {
    wx.navigateTo({ url: '/pages/chatroom/chatroom' })
  },

  onCreateGeneral() {
    const { generalId, generalName } = this.data
    wx.navigateTo({
      url: `/pages/forum-create/forum-create?sectionId=${generalId}&sectionName=${encodeURIComponent(generalName)}`
    })
  },

  // ── 分区跳转 ──────────────────────────────────
  onTapSection(e) {
    const { id, name } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/forum-section/forum-section?id=${id}&name=${encodeURIComponent(name)}`
    })
  },
})
