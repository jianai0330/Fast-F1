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

  onSubmit() {
    const { nickname, submitting } = this.data
    const trimmed = nickname.trim()
    if (submitting) return
    if (trimmed.length < 2 || trimmed.length > 12) {
      wx.showToast({ title: '昵称需 2-12 字', icon: 'none' })
      return
    }

    const existingOpenid = wx.getStorageSync('f1_openid') || ''

    if (existingOpenid) {
      // 已有 openid，直接更新昵称
      this.setData({ submitting: true })
      api.updateNickname(existingOpenid, trimmed).then((res) => {
        wx.setStorageSync('f1_nickname', trimmed)
        wx.showToast({ title: '昵称已更新！', icon: 'success' })
        setTimeout(() => {
          const pages = getCurrentPages()
          if (pages.length > 1) {
            const prev = pages[pages.length - 2]
            if (prev && prev.setData) prev.setData({ openid: existingOpenid })
            wx.navigateBack()
          } else {
            wx.switchTab({ url: '/pages/forum/forum' })
          }
        }, 800)
      }).catch((err) => {
        this.setData({ submitting: false })
        wx.showToast({ title: '更新失败，请重试', icon: 'none' })
      })
      return
    }

    this.setData({ submitting: true })

    wx.login({
      success: (loginRes) => {
        api.registerUser(loginRes.code, trimmed).then((res) => {
          const openid = res.data.openid
          wx.setStorageSync('f1_openid', openid)
          wx.setStorageSync('f1_nickname', trimmed)
          wx.showToast({ title: '注册成功！', icon: 'success' })
          setTimeout(() => {
            const pages = getCurrentPages()
            if (pages.length > 1) {
              const prev = pages[pages.length - 2]
              if (prev && prev.setData) prev.setData({ openid })
              wx.navigateBack()
            } else {
              wx.switchTab({ url: '/pages/forum/forum' })
            }
          }, 800)
        }).catch((err) => {
          this.setData({ submitting: false })
          wx.showToast({ title: '注册失败，请重试', icon: 'none' })
        })
      },
      fail: () => {
        this.setData({ submitting: false })
        wx.showToast({ title: '登录失败', icon: 'none' })
      }
    })
  },
})
