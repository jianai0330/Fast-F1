/* pages/forum-register/forum-register.js */
const { api } = require('../../utils/api')

Page({
  data: {
    nickname: '',
    nicknameLen: 0,
    submitting: false,
  },

  onNicknameInput(e) {
    const val = e.detail.value
    this.setData({ nickname: val, nicknameLen: val.length })
  },

  async onSubmit() {
    const { nickname, submitting } = this.data
    const trimmed = nickname.trim()
    if (submitting) return
    if (trimmed.length < 2 || trimmed.length > 12) {
      wx.showToast({ title: '昵称需 2-12 字', icon: 'none' })
      return
    }

    this.setData({ submitting: true })
    try {
      // 获取微信 code
      const loginRes = await new Promise((resolve, reject) =>
        wx.login({ success: resolve, fail: reject })
      )
      const code = loginRes.code

      // 注册到后端
      const res = await api.registerUser(code, trimmed)
      const openid = res.data.openid

      // 本地缓存
      wx.setStorageSync('f1_openid',   openid)
      wx.setStorageSync('f1_nickname', trimmed)

      wx.showToast({ title: '注册成功！', icon: 'success', duration: 1500 })
      setTimeout(() => wx.navigateBack(), 1500)
    } catch (e) {
      this.setData({ submitting: false })
      wx.showToast({ title: typeof e === 'string' ? e : '注册失败，请重试', icon: 'none' })
    }
  },
})
