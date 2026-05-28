import * as echarts from '../../components/ec-canvas/echarts'
const { api } = require('../../utils/api')

// 轮胎颜色映射
const COMPOUND_COLOR = {
  SOFT:    '#e8002d',
  MEDIUM:  '#ffd700',
  HARD:    '#cccccc',
  INTER:   '#39b54a',
  WET:     '#0067ff',
  UNKNOWN: '#666666',
}

// 车手固定颜色表（按车手三字码绑定，不随排名变动）
// 2026赛季车手颜色（按车队绑定）
const DRIVER_COLOR_MAP = {
  // Red Bull
  VER: '#3671c6', HAD: '#3671c6',
  // McLaren
  NOR: '#ff8000', PIA: '#ff8000',
  // Ferrari
  LEC: '#e8002d', HAM: '#e8002d',
  // Mercedes
  RUS: '#27f4d2', ANT: '#27f4d2',
  // Aston Martin
  ALO: '#358c75', STR: '#358c75',
  // Alpine
  GAS: '#0093cc', DOO: '#0093cc',
  // RB (Racing Bulls)
  TSU: '#6692ff', LAW: '#6692ff',
  // Williams
  ALB: '#64c4ff', SAI: '#64c4ff',
  // Kick Sauber
  BOT: '#c92d4b', BOR: '#c92d4b',
  // Haas
  OCO: '#b6babd', BEA: '#b6babd',
}
const FALLBACK_COLORS = [
  '#e10600','#ff8700','#00d2be','#0090ff','#006f62',
  '#2293d1','#5e8faa','#fe86bc','#469bff','#37bedd',
]

function getDriverColor(code, fallbackIndex) {
  return DRIVER_COLOR_MAP[code] || FALLBACK_COLORS[fallbackIndex % FALLBACK_COLORS.length]
}

// 按最终排名对车手排序，构建带颜色的车手列表
function buildDriverList(laptimes) {
  const driversData = laptimes.drivers
  return Object.keys(driversData)
    .filter(code => driversData[code].laps && driversData[code].laps.length > 2)
    .sort((a, b) => {
      const posA = driversData[a].summary?.final_position || 99
      const posB = driversData[b].summary?.final_position || 99
      return posA - posB
    })
    .map((code, i) => ({
      code,
      color: getDriverColor(code, i),   // 固定颜色，不随索引漂移
      team: driversData[code].team || '',
      rank: driversData[code].summary?.final_position || (i + 1),
      summary: driversData[code].summary || null,
    }))
}

// 构建名次变化折线图 option
function buildPositionOption(laptimes, selectedCodes) {
  const driversData = laptimes.drivers
  const allDrivers = buildDriverList(laptimes)
  const selected = new Set(selectedCodes)

  // 收集所选车手的实际名次范围（整数）
  let posMin = 20, posMax = 1
  allDrivers
    .filter(({ code }) => selected.has(code))
    .forEach(({ code }) => {
      driversData[code].laps
        .filter(l => l.position > 0)
        .forEach(l => {
          if (l.position < posMin) posMin = l.position
          if (l.position > posMax) posMax = l.position
        })
    })
  // 上下各留1格 padding，min/max 保持整数，interval:1 才能正常工作
  const yMin = Math.max(1, posMin - 1)
  const yMax = Math.min(22, posMax + 1)

  const series = allDrivers
    .filter(({ code }) => selected.has(code))
    .map(({ code, color }) => {
      const laps = driversData[code].laps
      // forward fill：position=0(NaN) 用前一圈值填充，保证线不断
      let lastPos = 0
      const filledLaps = laps.map(l => {
        if (l.position > 0) { lastPos = l.position; return l }
        if (lastPos > 0) return { ...l, position: lastPos }
        return l  // 开头就是0，跳过
      }).filter(l => l.position > 0)
      const validLaps = filledLaps
      const data = validLaps.map(l => ({ value: [l.lap, l.position], compound: l.compound, pit_in: l.pit_in }))
      // 末尾标签：显示 车手码+名次，贴在线右端
      const lastLap = validLaps[validLaps.length - 1]
      const endPos = lastLap ? lastLap.position : null
      return {
        name: code,
        type: 'line',
        data,
        symbol: 'none',
        lineStyle: { color, width: 2.5, opacity: 0.95 },
        itemStyle: { color },
        emphasis: { lineStyle: { width: 4 } },
        // 线条末端标签
        endLabel: {
          show: true,
          formatter: endPos ? `${code}\nP${endPos}` : code,
          color,
          fontSize: 9,
          fontWeight: 'bold',
          lineHeight: 12,
          align: 'left',
          padding: [0, 0, 0, 4],
        },
        // 进站圈空心圆点
        markPoint: {
          symbol: 'circle',
          symbolSize: 7,
          data: filledLaps
            .filter(l => l.pit_in && l.position > 0)
            .map(l => ({ coord: [l.lap, l.position], itemStyle: { color: 'transparent', borderColor: color, borderWidth: 1.5 } })),
          label: { show: false },
        },
      }
    })

  const totalLaps = Math.max(
    ...allDrivers
      .filter(({ code }) => selected.has(code))
      .map(({ code }) => Math.max(...driversData[code].laps.map(l => l.lap), 0)),
    1
  )

  return {
    backgroundColor: '#111111',
    animation: false,
    // 右侧留出 endLabel 的空间（约52px）
    grid: { top: 10, right: 52, bottom: 26, left: 30 },
    legend: { show: false },
    xAxis: {
      type: 'value',
      min: 1,
      max: totalLaps,
      minInterval: 1,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#444', fontSize: 9, formatter: val => `L${val}` },
      splitLine: { lineStyle: { color: '#1c1c1c' } },
    },
    yAxis: {
      type: 'value',
      min: yMin,
      max: yMax,
      inverse: true,
      interval: 1,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        show: true,
        color: '#555',
        fontSize: 9,
        formatter: val => `P${val}`,
      },
      splitLine: {
        show: true,
        lineStyle: { color: '#1c1c1c', type: 'dashed' },
      },
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: '#1e1e1e',
      borderColor: '#333',
      textStyle: { color: '#eee', fontSize: 11 },
      formatter: (params) => {
        if (!params.data?.value) return ''
        const [lap, pos] = params.data.value
        const pit = params.data.pit_in ? '  🔧进站' : ''
        return `${params.seriesName}  Lap ${lap}\nP${pos}${pit}`
      },
    },
    series,
  }
}

Page({
  data: {
    year: 2026,
    round: null,
    name: '',
    raceTimeUtc: '',   // 正赛时间（UTC ISO），用于判断是否已发生
    raceHappened: true, // 默认 true，收到时间后再判断
    activeTab: 'circuit',
    // 赛道信息
    circuit: null,
    circuitLoading: false,
    // 排位赛
    qualifying: null,
    qualiLoading: false,
    // 遥测车手选择
    driverList: [],
    driverListFull: [],
    d1Index: 0,
    d2Index: 1,
    d1: 'ALB',
    d2: 'ALO',
    telSession: 'Q',
    // 正赛
    raceReady: false,
    raceLoading: false,
    raceError: '',
    raceChartConfig: { lazyLoad: true },
    // 车手选择器 + 数据卡片
    raceDrivers: [],      // [{code, color, team, rank, summary, selected}]
    raceSelected: [],     // 当前选中 code 列表
    raceCards: [],        // 下半数据卡片，按 raceSelected 筛选
    // 悬浮查词
    termSheetVisible: false,
    termQuery: '',
    termResults: [],
    popularTerms: [],
    selectedTerm: null,
    allTerms: [],
    fabX: 280,
    fabY: 500,
  },

  _raceChart: null,
  _laptimesCache: null,

  onLoad(options) {
    const round = parseInt(options.round)
    const name = decodeURIComponent(options.name)
    const year = parseInt(options.year || 2026)
    const raceTimeUtc = options.race_time_utc ? decodeURIComponent(options.race_time_utc) : ''
    const raceHappened = raceTimeUtc ? new Date(raceTimeUtc).getTime() < Date.now() : true
    this.setData({ round, name, year, raceTimeUtc, raceHappened })
    wx.setNavigationBarTitle({ title: name })
    this.loadCircuit(year, round)
    this.loadTermsData()
  },

  onTabChange(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab })
    if (tab !== 'race') this._raceChart = null
    if (tab === 'circuit' && !this.data.circuit) this.loadCircuit()
    if (!this.data.raceHappened) return  // 未发生的赛事，不请求数据
    if (tab === 'qualifying' && !this.data.qualifying) this.loadQualifying()
    if (tab === 'race') {
      if (!this.data.raceReady) this.loadLaptimes()
      else wx.nextTick(() => this._ensureRaceChart())
    }
  },

  async loadCircuit(year, round) {
    year = year || this.data.year
    round = round || this.data.round
    this.setData({ circuitLoading: true })
    try {
      const res = await api.getCircuit(year, round)
      this.setData({ circuit: res.data, circuitLoading: false })
    } catch (e) {
      this.setData({ circuitLoading: false })
    }
  },

  async loadQualifying() {
    this.setData({ qualiLoading: true })
    try {
      const res = await api.getQualifying(this.data.year, this.data.round)
      const results = res.data.results || []
      const driverList = results.map(r => r.driver)
      const driverListFull = results.map(r => `${r.driver}  ${r.team}`)
      this.setData({
        qualifying: res.data,
        qualiLoading: false,
        driverList,
        driverListFull,
        d1Index: 0,
        d2Index: 1,
        d1: driverList[0] || 'ALB',
        d2: driverList[1] || 'ALO',
      })
    } catch (e) {
      const msg = typeof e === 'string' ? e : '排位赛数据加载失败'
      this.setData({ qualiLoading: false })
      wx.showToast({ title: msg, icon: 'none' })
    }
  },

  async loadLaptimes() {
    this.setData({ raceLoading: true, raceError: '' })
    try {
      const res = await api.getLaptimes(this.data.year, this.data.round, 'R')
      this._laptimesCache = res.data
      const drivers = buildDriverList(res.data)
      // 默认选前3名（按最终排名）
      const raceSelected = drivers.slice(0, 3).map(d => d.code)
      const raceDrivers = drivers.map(d => ({ ...d, selected: raceSelected.includes(d.code) }))
      const raceCards = this._buildCards(res.data, raceSelected)
      this.setData({
        raceReady: true,
        raceLoading: false,
        raceDrivers,
        raceSelected,
        raceCards,
      }, () => {
        wx.nextTick(() => this._ensureRaceChart())
      })
    } catch (e) {
      this.setData({ raceLoading: false, raceError: typeof e === 'string' ? e : '正赛数据加载失败' })
    }
  },

  // 构建数据卡片列表
  _buildCards(laptimes, selectedCodes) {
    const driversData = laptimes.drivers
    const allDrivers = buildDriverList(laptimes)
    return allDrivers
      .filter(({ code }) => selectedCodes.includes(code))
      .map(({ code, color, summary }) => {
        const stints = (summary?.stints || []).map(st => ({
          compound: st.compound,
          laps: st.laps,
          color: COMPOUND_COLOR[st.compound] || COMPOUND_COLOR.UNKNOWN,
          pct: 0,  // 占比，下面算
        }))
        const totalLaps = summary?.total_laps || 1
        stints.forEach(st => { st.pct = Math.round(st.laps / totalLaps * 100) })
        return {
          code,
          color,
          pos: summary?.final_position || '--',
          bestLap: summary?.best_lap_fmt || '--',
          pitCount: summary?.pit_count ?? '--',
          totalLaps: summary?.total_laps || '--',
          stints,
        }
      })
      .sort((a, b) => (a.pos || 99) - (b.pos || 99))
  },

  _ensureRaceChart() {
    if (this.data.activeTab !== 'race' || !this._laptimesCache) return
    const ecCanvas = this.selectComponent('#ec-race')
    if (!ecCanvas) return
    if (this._raceChart) {
      this._raceChart.setOption(buildPositionOption(this._laptimesCache, this.data.raceSelected), true)
      return
    }
    ecCanvas.init((canvas, width, height, dpr) => {
      const chart = echarts.init(canvas, null, { width, height, devicePixelRatio: dpr })
      canvas.setChart(chart)
      this._raceChart = chart
      chart.setOption(buildPositionOption(this._laptimesCache, this.data.raceSelected), true)
      return chart
    })
  },

  onRaceDriverTap(e) {
    const code = e.currentTarget.dataset.code
    let selected = [...this.data.raceSelected]
    const idx = selected.indexOf(code)
    if (idx >= 0) {
      if (selected.length <= 1) return
      selected.splice(idx, 1)
    } else {
      selected.push(code)
    }
    const raceDrivers = this.data.raceDrivers.map(d => ({ ...d, selected: selected.includes(d.code) }))
    const raceCards = this._buildCards(this._laptimesCache, selected)
    this.setData({ raceSelected: selected, raceDrivers, raceCards })
    if (this._laptimesCache) this._ensureRaceChart()
  },

  onD1Pick(e) {
    const idx = parseInt(e.detail.value)
    this.setData({ d1Index: idx, d1: this.data.driverList[idx] })
  },

  onD2Pick(e) {
    const idx = parseInt(e.detail.value)
    this.setData({ d2Index: idx, d2: this.data.driverList[idx] })
  },

  onGoTelemetry() {
    const { year, round, d1, d2, telSession } = this.data
    wx.navigateTo({ url: `/pages/telemetry/telemetry?year=${year}&round=${round}&d1=${d1}&d2=${d2}&session=${telSession}` })
  },

  onGoAnalysis() {
    const { year, round, d1, d2, telSession } = this.data
    wx.navigateTo({ url: `/pages/analysis/analysis?year=${year}&round=${round}&d1=${d1}&d2=${d2}&session=${telSession}` })
  },

  // ── 悬浮查词 ──────────────────────────────────────
  async loadTermsData() {
    try {
      const [termsRes, popularRes] = await Promise.all([
        api.getTerms(),
        api.getTermsPopular()
      ])
      this.setData({
        allTerms: termsRes.data || [],
        popularTerms: (popularRes.data || []).map(slug => {
          const t = (termsRes.data || []).find(t => t.slug === slug)
          return t || { slug, name_zh: slug }
        })
      })
    } catch(e) { console.error('loadTermsData', e) }
  },

  onTermFabTap() {
    this.setData({ termSheetVisible: true })
  },

  closeTermSheet() {
    this.setData({ termSheetVisible: false, termQuery: '', termResults: [], selectedTerm: null })
  },

  onTermSearch(e) {
    const query = e.detail.value.toLowerCase().trim()
    this.setData({ termQuery: query })
    if (!query) { this.setData({ termResults: [] }); return }

    const results = this.data.allTerms.filter(t => {
      const searchFields = `${t.name_zh} ${t.name_en} ${t.aliases || ''}`.toLowerCase()
      return searchFields.includes(query)
    }).slice(0, 5)

    this.setData({ termResults: results })
  },

  onTermResultTap(e) {
    const slug = e.currentTarget.dataset.slug
    this.closeTermSheet()
    wx.navigateTo({ url: `/pages/term/term?slug=${slug}` })
  },

  goTermDetail() {
    if (this.data.selectedTerm) {
      this.closeTermSheet()
      wx.navigateTo({ url: `/pages/term/term?slug=${this.data.selectedTerm.slug}` })
    }
  },
})
