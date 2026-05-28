const { api } = require('../../utils/api')
const app = getApp()

const PLATFORM_MAP = {
  wechat: '微信公众号',
  weibo: '微博',
  bilibili: 'B站',
  douyin: '抖音',
  zhihu: '知乎',
  web: '网页',
}

/**
 * 去掉 archived_html 中可能存在的 <script> 标签，避免 rich-text 执行
 */
function stripScript(html) {
  if (!html) return ''
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<script[\s\S]*?>/gi, '')
    .replace(/visibility:\s*hidden/gi, 'visibility:visible')
    .replace(/opacity:\s*0([^.])/gi, 'opacity:1$1')
    .replace(/display:\s*none/gi, 'display:block')
}

/**
 * 把时间戳格式化为可读日期
 */
function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

Page({
  data: {
    loading: true,
    error: '',
    detail: null,
    baseUrl: app.globalData.BASE_URL,
    viewMode: 'screenshot',  // 'screenshot' | 'html'
    // AI 分析轮询
    polling: false,
    pollCount: 0,
    MAX_POLL: 15,
    triggerLoading: false,
    reanalyzeLoading: false,
    // 讨论区
    relatedPosts: [],
    relatedTotal: 0,
  },

  _pollTimer: null,

  onLoad(options) {
    const id = options.id
    if (!id) {
      this.setData({ loading: false, error: '缺少内容 ID' })
      return
    }
    this.contentId = id
    this.fetchDetail(id)
  },

  onShow() {
    // 从 forum-create 返回后自动刷新关联帖子
    if (this.contentId && !this.data.loading) {
      api.getCuratedPosts(this.contentId)
        .then(res => {
          const items = (res.data.items || []).slice(0, 3)
          const total = res.data.total || 0
          this.setData({ relatedPosts: items, relatedTotal: total })
        })
        .catch(() => {})
    }
  },

  onUnload() {
    this._stopPoll()
  },

  async fetchDetail(id) {
    this.setData({ loading: true, error: '' })
    try {
      const [res, postsRes] = await Promise.all([
        api.getCuratedDetail(id),
        api.getCuratedPosts(id).catch(() => ({ data: { items: [], total: 0 } })),
      ])
      const d = res.data || {}
      const platform = d.platform || ''

      // 解析 tags 字段（可能是 JSON 字符串）
      let parsedTags = []
      if (d.tags) {
        try {
          parsedTags = typeof d.tags === 'string' ? JSON.parse(d.tags) : d.tags
          if (!Array.isArray(parsedTags)) parsedTags = []
        } catch (e) {
          parsedTags = []
        }
      }

      // 清理 archived_html
      const archived_html = stripScript(d.archived_html || '')

      // AI 分析状态
      const analyzed = !!d.analyzed

      this.setData({
        loading: false,
        detail: {
          ...d,
          platformLabel: PLATFORM_MAP[platform] || platform || '网页',
          parsedTags,
          timeStr: formatTime(d.published_at || d.created_at),
          archived_html,
          analyzed,
        },
        relatedPosts: (postsRes.data.items || []).slice(0, 3),
        relatedTotal: postsRes.data.total || 0,
      })
    } catch (err) {
      this.setData({
        loading: false,
        error: typeof err === 'string' ? err : '加载失败，请重试',
      })
    }
  },

  onToggleView(e) {
    const mode = e.currentTarget.dataset.mode
    if (mode !== this.data.viewMode) {
      this.setData({ viewMode: mode })
    }
  },

  onCopyUrl() {
    const url = this.data.detail && this.data.detail.url
    if (!url) return
    wx.setClipboardData({
      data: url,
      success() {
        wx.showToast({ title: '链接已复制', icon: 'success' })
      },
    })
  },

  // ── AI 分析轮询 ─────────────────────────
  _startPoll() {
    this.setData({ polling: true, pollCount: 0 })
    this._doPoll()
  },

  _doPoll() {
    if (this.data.pollCount >= this.data.MAX_POLL) {
      this.setData({ polling: false })
      return
    }
    this._pollTimer = setTimeout(async () => {
      try {
        const res = await api.getCuratedDetail(this.contentId)
        const d = res.data || {}
        const analyzed = !!d.analyzed
        const archived_html = stripScript(d.archived_html || '')
        let parsedTags = this.data.detail.parsedTags
        if (d.tags) {
          try {
            parsedTags = typeof d.tags === 'string' ? JSON.parse(d.tags) : d.tags
            if (!Array.isArray(parsedTags)) parsedTags = []
          } catch (e) {}
        }
        this.setData({
          detail: {
            ...this.data.detail,
            ...d,
            analyzed,
            archived_html,
            parsedTags,
          },
          pollCount: this.data.pollCount + 1,
        })
        if (analyzed) {
          this.setData({ polling: false })
        } else {
          this._doPoll()
        }
      } catch (e) {
        this.setData({ polling: false })
      }
    }, 3000)
  },

  _stopPoll() {
    if (this._pollTimer) {
      clearTimeout(this._pollTimer)
      this._pollTimer = null
    }
  },

  // ── 用户触发 AI 分析 ─────────────────────────
  async onTriggerAnalyze() {
    if (this.data.triggerLoading || this.data.polling) return
    this.setData({ triggerLoading: true })
    try {
      await api.triggerCuratedAnalyze(this.contentId)
      this.setData({ triggerLoading: false })
      this._startPoll()
    } catch (e) {
      this.setData({ triggerLoading: false })
      this.fetchDetail(this.contentId)
    }
  },

  // ── 讨论区 ────────────────────────────────

  onGoForum() {
    const detail = this.data.detail
    if (!detail) return
    const rawTitle = '讨论：' + detail.title
    const prefillTitle = rawTitle.length > 46 ? rawTitle.slice(0, 46) : rawTitle
    wx.navigateTo({
      url: `/pages/forum-create/forum-create?sectionId=35&sectionName=${encodeURIComponent('综合讨论')}&prefillTitle=${encodeURIComponent(prefillTitle)}&curatedId=${detail.id}&curatedTitle=${encodeURIComponent(detail.title)}`
    })
  },

  onViewAllPosts() {
    wx.navigateTo({
      url: `/pages/forum-section/forum-section?id=35&name=${encodeURIComponent('综合讨论')}`
    })
  },

  onGoPost(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/forum-post/forum-post?id=${id}` })
  },

  // ── 重新分析（强制刷新）──────────────────────
  async onReanalyze() {
    if (this.data.reanalyzeLoading || this.data.polling) return
    wx.showModal({
      title: '重新生成解读',
      content: '将清除当前解读并重新分析，约需 15~30 秒，确定吗？',
      confirmText: '确定',
      cancelText: '取消',
      success: async ({ confirm }) => {
        if (!confirm) return
        this.setData({ reanalyzeLoading: true })
        try {
          await api.triggerCuratedAnalyze(this.contentId, true)
          this.setData({
            reanalyzeLoading: false,
            detail: {
              ...this.data.detail,
              analyzed: false,
              tech_points: '',
              plain_explain: '',
              race_impact: '',
            },
          })
          this._startPoll()
        } catch (e) {
          this.setData({ reanalyzeLoading: false })
          wx.showToast({ title: '触发失败', icon: 'none' })
        }
      },
    })
  },
})
