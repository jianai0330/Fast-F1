const { api } = require('../../utils/api')
const app = getApp()

const PLATFORM_MAP = {
  wechat: '微信公众号',
  weibo: '微博',
  bilibili: 'B站',
  douyin: '抖音',
  zhihu: '知乎',
  web: '网页',
  other: '其他',
}

/**
 * 从混合分享文本中提取 URL
 * 抖音分享格式如: "rEu:/ :2pm 01/11 L@W.Zm https://v.douyin.com/xxx/"
 * 小红书分享格式如: "复制打开小红书查看 https://www.xiaohongshu.com/xxx"
 */
function extractUrl(text) {
  if (!text) return ''
  text = text.trim()
  // 如果本身就是纯 URL，直接返回
  if (/^https?:\/\//i.test(text)) return text
  // 从混合文本中提取第一个 URL
  const m = text.match(/https?:\/\/[^\s<>"]+/i)
  return m ? m[0] : text.trim()
}

Page({
  data: {
    mode: 'link',  // 'link' | 'manual'
    url: '',
    manualTitle: '',
    manualSummary: '',
    manualPlatform: 'douyin',
    manualUrl: '',
    presetTags: ['技术分析', '赛车策略', '车手动态', '趣闻', '数据解读', '历史回顾', '新闻速报'],
    selectedTags: [],
    selectedTagMap: {},
    note: '',
    nickname: '',
    submitting: false,
    result: null,
    baseUrl: app.globalData.BASE_URL,
  },

  onLoad() {
    // 从本地缓存读取上次昵称
    const saved = wx.getStorageSync('curated_nickname')
    if (saved) {
      this.setData({ nickname: saved })
    }
  },

  switchMode(e) {
    this.setData({ mode: e.currentTarget.dataset.mode })
  },

  onUrlInput(e) {
    // 抖音/小红书等分享文本可能包含乱码追踪文本，需要从中提取 URL
    const raw = e.detail.value
    const url = extractUrl(raw)
    this.setData({ url })
  },

  onManualTitleInput(e) { this.setData({ manualTitle: e.detail.value }) },
  onManualSummaryInput(e) { this.setData({ manualSummary: e.detail.value }) },
  onManualUrlInput(e) { this.setData({ manualUrl: e.detail.value }) },
  selectPlatform(e) { this.setData({ manualPlatform: e.currentTarget.dataset.platform }) },

  onToggleTag(e) {
    const tag = e.currentTarget.dataset.tag
    let { selectedTags, selectedTagMap } = this.data
    if (selectedTagMap[tag]) {
      // 取消选中
      selectedTags = selectedTags.filter(t => t !== tag)
      delete selectedTagMap[tag]
    } else {
      // 选中
      selectedTags = [...selectedTags, tag]
      selectedTagMap[tag] = true
    }
    // 必须创建新对象，否则 setData 不触发渲染
    this.setData({ selectedTags, selectedTagMap: { ...selectedTagMap } })
  },

  onNoteInput(e) {
    this.setData({ note: e.detail.value })
  },

  onNicknameInput(e) {
    this.setData({ nickname: e.detail.value })
  },

  async onSubmit() {
    const { mode, url, manualTitle, manualSummary, manualPlatform, manualUrl,
            selectedTags, note, nickname } = this.data

    // 记住昵称
    if (nickname) {
      wx.setStorageSync('curated_nickname', nickname)
    }

    if (mode === 'manual') {
      // 手动投稿
      if (!manualTitle.trim() || !manualSummary.trim()) {
        wx.showToast({ title: '请填写标题和摘要', icon: 'none' })
        return
      }

      this.setData({ submitting: true, result: null })
      try {
        const res = await api.submitCuratedManual({
          title: manualTitle.trim(),
          summary: manualSummary.trim(),
          platform: manualPlatform,
          url: manualUrl || '',
          tags: selectedTags,
          note: note || '',
          submitted_by: nickname || '',
        })
        this.setData({
          submitting: false,
          result: {
            title: manualTitle.trim(),
            platformLabel: PLATFORM_MAP[manualPlatform] || manualPlatform,
            cover_image: '',
          },
        })
        wx.setStorageSync('curated_list_dirty', 1)
        wx.showToast({ title: '投稿成功', icon: 'success' })
        setTimeout(() => {
          wx.navigateBack({ delta: 1 })
        }, 1500)
      } catch (err) {
        this.setData({ submitting: false })
        wx.showToast({
          title: typeof err === 'string' ? err : '投稿失败，请重试',
          icon: 'none',
          duration: 2500,
        })
      }
    } else {
      // 链接投稿
      if (!url) return

      this.setData({ submitting: true, result: null })
      try {
        const body = {
          url,
          tags: selectedTags.length > 0 ? selectedTags : undefined,
          note: note || undefined,
          submitted_by: nickname || undefined,
        }
        // 去掉 undefined 字段
        Object.keys(body).forEach(k => body[k] === undefined && delete body[k])

        const res = await api.submitCurated(body)
        const parsed = res.data && res.data.parsed ? res.data.parsed : {}
        const platform = parsed.platform || ''
        this.setData({
          submitting: false,
          result: {
            ...parsed,
            platformLabel: PLATFORM_MAP[platform] || platform || '网页',
          },
        })
        wx.setStorageSync('curated_list_dirty', 1)
        wx.showToast({ title: '投稿成功', icon: 'success' })
        // 1.5s 后跳回上一页（精选列表）
        setTimeout(() => {
          wx.navigateBack({ delta: 1 })
        }, 1500)
      } catch (err) {
        this.setData({ submitting: false })
        wx.showToast({
          title: typeof err === 'string' ? err : '投稿失败，请重试',
          icon: 'none',
          duration: 2500,
        })
      }
    }
  },
})
