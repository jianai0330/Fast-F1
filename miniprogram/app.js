const BASE_URL = 'https://api.aifuwan.site'

App({
  globalData: {
    BASE_URL,
    currentYear: 2026,
    deviceId: '',
  },

  onLaunch() {
    console.log('F1 Data App launched')
    // 生成持久设备 ID，确保评分等数据不因重编译丢失
    let deviceId = wx.getStorageSync('f1_device_id')
    if (!deviceId) {
      deviceId = 'dev_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 10)
      wx.setStorageSync('f1_device_id', deviceId)
    }
    this.globalData.deviceId = deviceId

    const shown = wx.getStorageSync('f1_welcome_shown')
    if (!shown) {
      wx.showModal({
        title: '欢迎使用 🏎️',
        content: '第一次启动因为服务器在香港，可能会有点慢哦，耐心等待一下，下次就有缓存啦 😊',
        showCancel: false,
        confirmText: '好的',
      })
      wx.setStorageSync('f1_welcome_shown', true)
    }
  },
})
