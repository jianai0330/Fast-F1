const { api } = require('../../utils/api')

Page({
  data: {
    nickname: '',
    messages: [],
    inputValue: '',
    scrollToId: '',
    lastMsgId: 0,
    polling: null
  },

  onLoad() {
    this.initNickname()
    this.loadMessages()
    // 开始轮询
    const polling = setInterval(() => this.pollMessages(), 4000)
    this.setData({ polling })
  },

  onUnload() {
    if (this.data.polling) clearInterval(this.data.polling)
  },

  onHide() {
    if (this.data.polling) clearInterval(this.data.polling)
  },

  onShow() {
    if (!this.data.polling) {
      const polling = setInterval(() => this.pollMessages(), 4000)
      this.setData({ polling })
      this.pollMessages()
    }
  },

  async initNickname() {
    const stored = wx.getStorageSync('chat_nickname')
    if (stored) {
      this.setData({ nickname: stored })
    } else {
      try {
        const res = await api.getChatNickname()
        if (res && res.status === 'ok') {
          this.setData({ nickname: res.data.nickname })
          wx.setStorageSync('chat_nickname', res.data.nickname)
        }
      } catch (e) {
        this.setData({ nickname: '匿名车迷' })
      }
    }
  },

  async loadMessages() {
    try {
      const res = await api.getChatMessages(0)
      if (res && res.status === 'ok') {
        const messages = this.formatMessages(res.data)
        const lastMsg = messages[messages.length - 1]
        this.setData({
          messages,
          lastMsgId: lastMsg ? lastMsg.id : 0,
          scrollToId: lastMsg ? `msg-${lastMsg.id}` : ''
        })
      }
    } catch (e) {
      console.error('加载消息失败', e)
    }
  },

  async pollMessages() {
    try {
      const res = await api.getChatMessages(this.data.lastMsgId)
      if (res && res.status === 'ok' && res.data.length > 0) {
        const newMsgs = this.formatMessages(res.data)
        const messages = [...this.data.messages, ...newMsgs].slice(-200)
        const lastMsg = newMsgs[newMsgs.length - 1]
        this.setData({
          messages,
          lastMsgId: lastMsg.id,
          scrollToId: `msg-${lastMsg.id}`
        })
      }
    } catch (e) {
      // 轮询失败静默处理，避免打断用户体验
    }
  },

  formatMessages(list) {
    return list.map(m => ({
      ...m,
      timeStr: this.formatTime(m.created_at)
    }))
  },

  formatTime(ts) {
    if (!ts) return ''
    const d = new Date(ts.replace(' ', 'T') + '+08:00')
    const now = new Date()
    if (d.toDateString() === now.toDateString()) {
      return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
    }
    return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  },

  onInput(e) {
    this.setData({ inputValue: e.detail.value })
  },

  async sendMessage() {
    const content = this.data.inputValue.trim()
    if (!content) return
    this.setData({ inputValue: '' })
    try {
      const res = await api.sendChatMessage(this.data.nickname, content)
      if (res && res.status === 'ok') {
        // 立即拉取最新消息
        this.pollMessages()
      }
    } catch (e) {
      wx.showToast({ title: '发送失败', icon: 'none' })
    }
  },

  changeNickname() {
    wx.showModal({
      title: '修改昵称',
      editable: true,
      placeholderText: '输入新昵称（最多20字）',
      success: (res) => {
        if (res.confirm && res.content && res.content.trim()) {
          const nickname = res.content.trim().slice(0, 20)
          this.setData({ nickname })
          wx.setStorageSync('chat_nickname', nickname)
        }
      }
    })
  }
})
