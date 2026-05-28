Page({
  data: { url: '' },

  onLoad(options) {
    const url = decodeURIComponent(options.url || '')
    this.setData({ url })
    wx.setNavigationBarTitle({ title: options.title ? decodeURIComponent(options.title) : '原文' })
  },
})
