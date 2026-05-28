// 首页：赛历列表
const { api } = require('../../utils/api')
const CIRCUIT_PATHS = require('../../utils/circuit_paths')
const app = getApp()

// Location → circuit_paths key 映射
const LOCATION_TO_CIRCUIT = {
  'Melbourne':       'Melbourne',
  'Shanghai':        'Shanghai',
  'Suzuka':          'Suzuka',
  'Miami Gardens':   'Miami',
  'Montréal':        'Montreal',
  'Monte Carlo':     'Monaco',
  'Barcelona':       'Barcelona',
  'Spielberg':       'Red Bull Ring',
  'Silverstone':     'Silverstone',
  'Spa-Francorchamps': 'Spa',
  'Budapest':        'Hungaroring',
  'Zandvoort':       'Zandvoort',
  'Monza':           'Monza',
  'Madrid':          'Madrid',
  'Baku':            'Baku',
  'Marina Bay':      'Marina Bay',
  'Austin':          'COTA',
  'Mexico City':     'Mexico City',
  'São Paulo':       'Interlagos',
  'Las Vegas':       'Las Vegas',
  'Lusail':          'Lusail',
  'Yas Marina':      'Yas Marina',
}

// 把 SVG path d 字符串解析成 [[x,y], ...] 点数组（只处理 M/L/Z）
function parsePath(d) {
  const points = []
  const cmds = d.trim().split(/(?=[MLZmlz])/)
  for (const cmd of cmds) {
    const type = cmd[0]
    if (type === 'Z' || type === 'z') continue
    const nums = cmd.slice(1).trim().split(/[\s,]+/).map(Number)
    for (let i = 0; i < nums.length - 1; i += 2) {
      points.push([nums[i], nums[i + 1]])
    }
  }
  return points
}

// 把点数组缩放+平移到 canvas 的 w×h 范围内（含padding）
function fitPoints(points, w, h, pad) {
  if (!points.length) return []
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
  for (const [x, y] of points) {
    if (x < minX) minX = x; if (x > maxX) maxX = x
    if (y < minY) minY = y; if (y > maxY) maxY = y
  }
  const scaleX = (w - pad * 2) / (maxX - minX || 1)
  const scaleY = (h - pad * 2) / (maxY - minY || 1)
  const scale = Math.min(scaleX, scaleY)
  const offX = pad + ((w - pad * 2) - (maxX - minX) * scale) / 2
  const offY = pad + ((h - pad * 2) - (maxY - minY) * scale) / 2
  return points.map(([x, y]) => [
    offX + (x - minX) * scale,
    offY + (y - minY) * scale,
  ])
}

// UTC ISO 字符串 → 北京时间显示字符串（M月D日 HH:MM）
function toBeijingStr(utcIso) {
  const d = new Date(utcIso)
  const bj = new Date(d.getTime() + 8 * 3600 * 1000)
  const mo = bj.getUTCMonth() + 1
  const day = bj.getUTCDate()
  const h = String(bj.getUTCHours()).padStart(2, '0')
  const m = String(bj.getUTCMinutes()).padStart(2, '0')
  return `${mo}月${day}日 ${h}:${m}`
}

// 距目标时间的倒计时字符串
function calcCountdown(utcIso) {
  const diff = new Date(utcIso).getTime() - Date.now()
  if (diff <= 0) return '发车！'
  const d = Math.floor(diff / 86400000)
  const h = Math.floor((diff % 86400000) / 3600000)
  const m = Math.floor((diff % 3600000) / 60000)
  const s = Math.floor((diff % 60000) / 1000)
  const hh = String(h).padStart(2, '0')
  const mm = String(m).padStart(2, '0')
  const ss = String(s).padStart(2, '0')
  if (d > 0) return `${d}天 ${hh}:${mm}:${ss}`
  return `${hh}:${mm}:${ss}`
}

function formatRaceStatus(event) {
  if (!event || !event.race_time_utc) return '赛程待定'
  const raceTime = new Date(event.race_time_utc).getTime()
  return raceTime > Date.now() ? '即将开跑' : '已完赛'
}

const QUICK_ACTIONS = [
  { key: 'standings', label: '看积分榜', hint: '车手与车队走势', type: 'switchTab', url: '/pages/standings/standings' },
  { key: 'news', label: '刷资讯', hint: '赛后热点与精选', type: 'switchTab', url: '/pages/news/news' },
  { key: 'glossary', label: '查术语', hint: '一键补知识点', type: 'switchTab', url: '/pages/glossary/glossary' },
  { key: 'forum', label: '进论坛', hint: '车迷讨论区', type: 'switchTab', url: '/pages/forum/forum' },
]

Page({
  data: {
    year: 2026,
    events: [],
    loading: true,
    error: '',
    // 倒计时
    nextRace: null,
    countdown: '',
    seasonSummary: null,
    latestRace: null,
    quickActions: QUICK_ACTIONS,
  },

  _timer: null,
  _drawnCircuitSignature: '',

  onLoad() {
    this.loadEvents()
  },

  onShow() {
    wx.showTabBar({ animation: false })
    this._startCountdown()
  },

  onHide() {
    this._stopCountdown()
  },

  onUnload() {
    this._stopCountdown()
  },

  async loadEvents() {
    this.setData({ loading: true, error: '' })
    try {
      const res = await api.getEvents(this.data.year)
      const events = res.data.filter(e => e.round > 0)
      this.setData({ events, loading: false })
      this._pickNextRace(events)
      this._buildSeasonSummary(events)
      wx.nextTick(() => this._drawAllCircuits(events))
    } catch (e) {
      this.setData({ loading: false, error: e })
    }
  },

  _pickNextRace(events) {
    const now = Date.now()
    const next = events.find(e => e.race_time_utc && new Date(e.race_time_utc).getTime() > now)
    if (!next) { this.setData({ nextRace: null }); return }
    const shortName = next.name.replace(' Grand Prix', ' GP')
    this.setData({
      nextRace: {
        ...next,
        shortName,
        race_time_bj: toBeijingStr(next.race_time_utc),
      },
      countdown: calcCountdown(next.race_time_utc),
    })
    // 数据就绪后确保计时器已启动
    this._startCountdown()
  },

  _buildSeasonSummary(events) {
    const now = Date.now()
    const completedEvents = events.filter(e => e.race_time_utc && new Date(e.race_time_utc).getTime() <= now)
    const upcomingEvents = events.filter(e => e.race_time_utc && new Date(e.race_time_utc).getTime() > now)
    const latestRace = completedEvents.length ? completedEvents[completedEvents.length - 1] : null

    this.setData({
      seasonSummary: {
        total: events.length,
        completed: completedEvents.length,
        upcoming: upcomingEvents.length,
      },
      latestRace: latestRace ? {
        round: latestRace.round,
        name: latestRace.name,
        location: latestRace.location,
        status: formatRaceStatus(latestRace),
      } : null,
    })
  },

  _startCountdown() {
    this._stopCountdown()
    if (!this.data.nextRace) return
    this._timer = setInterval(() => {
      const next = this.data.nextRace
      if (!next) return
      const cd = calcCountdown(next.race_time_utc)
      this.setData({ countdown: cd })
      // 发车后重选下一场
      if (cd === '发车！') {
        this._stopCountdown()
        setTimeout(() => this._pickNextRace(this.data.events), 3000)
      }
    }, 1000)
  },

  _stopCountdown() {
    if (this._timer) { clearInterval(this._timer); this._timer = null }
  },

  _drawAllCircuits(events) {
    const signature = events.map(event => `${event.round}:${event.location}`).join('|')
    if (signature && signature === this._drawnCircuitSignature) return
    this._drawnCircuitSignature = signature

    events.forEach((event, idx) => {
      const key = LOCATION_TO_CIRCUIT[event.location]
      const circuit = key ? CIRCUIT_PATHS[key] : null
      if (!circuit) return
      const canvasId = `circuit-${idx}`
      const query = wx.createSelectorQuery().in(this)
      query.select(`#${canvasId}`)
        .fields({ node: true, size: true })
        .exec(res => {
          if (!res[0]?.node) return
          const canvas = res[0].node
          const w = res[0].width
          const h = res[0].height
          const dpr = wx.getWindowInfo().pixelRatio
          canvas.width = w * dpr
          canvas.height = h * dpr
          const ctx = canvas.getContext('2d')
          ctx.scale(dpr, dpr)
          ctx.clearRect(0, 0, w, h)

          const points = fitPoints(parsePath(circuit.d), w, h, 3)
          if (!points.length) return

          ctx.beginPath()
          ctx.moveTo(points[0][0], points[0][1])
          for (let i = 1; i < points.length; i++) {
            ctx.lineTo(points[i][0], points[i][1])
          }
          ctx.closePath()
          ctx.strokeStyle = '#e10600'
          ctx.lineWidth = 1.5
          ctx.lineJoin = 'round'
          ctx.lineCap = 'round'
          ctx.stroke()
        })
    })
  },

  onEventTap(e) {
    const event = e.currentTarget.dataset.event
    const raceTime = event.race_time_utc ? encodeURIComponent(event.race_time_utc) : ''
    wx.navigateTo({
      url: `/pages/event/event?round=${event.round}&name=${encodeURIComponent(event.name)}&year=${this.data.year}&race_time_utc=${raceTime}`
    })
  },

  onQuickActionTap(e) {
    const { url, type } = e.currentTarget.dataset
    if (!url) return
    if (type === 'switchTab') {
      wx.switchTab({ url })
      return
    }
    wx.navigateTo({ url })
  },
})
