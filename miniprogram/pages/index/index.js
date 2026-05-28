// 首页：赛历列表
const { api } = require('../../utils/api')
const app = getApp()

Page({
  data: {
    year: 2026,
    events: [],
    loading: true,
    error: '',
  },

  onLoad() {
    this.loadEvents()
  },

  async loadEvents() {
    this.setData({ loading: true, error: '' })
    try {
      const res = await api.getEvents(this.data.year)
      // 过滤掉测试赛，只保留正式比赛
      const events = res.data.filter(e => e.round > 0)
      this.setData({ events, loading: false })
    } catch (e) {
      this.setData({ loading: false, error: e })
    }
  },

  onEventTap(e) {
    const event = e.currentTarget.dataset.event
    wx.navigateTo({
      url: `/pages/event/event?round=${event.round}&name=${encodeURIComponent(event.name)}&year=${this.data.year}`
    })
  },
})
