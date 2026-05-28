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

const QUICK_ACTIONS = [
  { key: 'standings', label: '看积分榜', hint: '车手与车队走势', type: 'switchTab', url: '/pages/standings/standings' },
  { key: 'news', label: '刷资讯', hint: '赛后热点与精选', type: 'switchTab', url: '/pages/news/news' },
  { key: 'glossary', label: '查术语', hint: '一键补知识点', type: 'switchTab', url: '/pages/glossary/glossary' },
  { key: 'forum', label: '进论坛', hint: '车迷讨论区', type: 'switchTab', url: '/pages/forum/forum' },
]

function extractPathBounds(pathD) {
  const nums = (pathD.match(/-?\d*\.?\d+/g) || []).map(Number)
  if (nums.length < 4) {
    return { minX: 0, minY: 0, width: 120, height: 70 }
  }
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  for (let i = 0; i < nums.length - 1; i += 2) {
    const x = nums[i]
    const y = nums[i + 1]
    if (Number.isNaN(x) || Number.isNaN(y)) continue
    if (x < minX) minX = x
    if (x > maxX) maxX = x
    if (y < minY) minY = y
    if (y > maxY) maxY = y
  }
  if (!Number.isFinite(minX) || !Number.isFinite(minY) || !Number.isFinite(maxX) || !Number.isFinite(maxY)) {
    return { minX: 0, minY: 0, width: 120, height: 70 }
  }
  const pad = 6
  return {
    minX: minX - pad,
    minY: minY - pad,
    width: Math.max(1, maxX - minX + pad * 2),
    height: Math.max(1, maxY - minY + pad * 2),
  }
}

function buildCircuitSvgDataUri(pathD, stroke = '#ff453a') {
  if (!pathD) return ''
  const box = extractPathBounds(pathD)
  const canvasWidth = 160
  const canvasHeight = 80
  const padding = 10
  const scale = Math.min(
    (canvasWidth - padding * 2) / box.width,
    (canvasHeight - padding * 2) / box.height
  )
  const offsetX = (canvasWidth - box.width * scale) / 2 - box.minX * scale
  const offsetY = (canvasHeight - box.height * scale) / 2 - box.minY * scale
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${canvasWidth} ${canvasHeight}" fill="none" preserveAspectRatio="xMidYMid meet"><g transform="translate(${offsetX} ${offsetY}) scale(${scale})"><path d="${pathD}" stroke="${stroke}" stroke-width="2.2" vector-effect="non-scaling-stroke" stroke-linecap="round" stroke-linejoin="round"/></g></svg>`
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
}

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
    latestRaceEntry: null,
    quickActions: QUICK_ACTIONS,
  },

  _timer: null,

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
      const events = res.data
        .filter(e => e.round > 0)
        .map(event => {
          const key = LOCATION_TO_CIRCUIT[event.location]
          const circuit = key ? CIRCUIT_PATHS[key] : null
          return {
            ...event,
            circuitSvg: circuit ? buildCircuitSvgDataUri(circuit.d) : '',
          }
        })
      this.setData({ events, loading: false })
      this._pickNextRace(events)
      this._buildSeasonSummary(events)
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
      latestRaceEntry: latestRace ? {
        round: latestRace.round,
        name: latestRace.name,
        location: latestRace.location,
        race_time_utc: latestRace.race_time_utc,
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

  onEventTap(e) {
    const event = e.currentTarget.dataset.event
    const raceTime = event.race_time_utc ? encodeURIComponent(event.race_time_utc) : ''
    wx.navigateTo({
      url: `/pages/event/event?round=${event.round}&name=${encodeURIComponent(event.name)}&year=${this.data.year}&race_time_utc=${raceTime}`
    })
  },

  onLatestRaceTap() {
    const entry = this.data.latestRaceEntry
    if (!entry) return
    const raceTime = entry.race_time_utc ? encodeURIComponent(entry.race_time_utc) : ''
    wx.navigateTo({
      url: `/pages/event/event?round=${entry.round}&name=${encodeURIComponent(entry.name)}&year=${this.data.year}&race_time_utc=${raceTime}`
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
