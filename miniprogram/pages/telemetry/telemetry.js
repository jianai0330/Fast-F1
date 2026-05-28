import * as echarts from '../../components/ec-canvas/echarts'
const { api } = require('../../utils/api')

const CHANNELS = ['speed', 'throttle', 'brake', 'gear']
const MAX_CHART_POINTS = 420

const Y_CONFIGS = {
  speed:    { name: 'Speed (km/h)', min: 50,  max: 340 },
  throttle: { name: 'Throttle (%)', min: 0,   max: 105 },
  brake:    { name: 'Brake',        min: -0.1, max: 1.2 },
  gear:     { name: 'Gear',         min: 0,   max: 9   },
}

function buildOption(channel, telemetry, driverA, driverB, cornerLabels, cornerDistances) {
  const dataA = telemetry[driverA.code][channel]
  const dataB = telemetry[driverB.code][channel]
  const distA = telemetry[driverA.code].distance
  const distB = telemetry[driverB.code].distance
  const yc = Y_CONFIGS[channel]

  const markLines = cornerDistances.map((d, i) => ({
    xAxis: d,
    label: { show: true, formatter: cornerLabels[i], position: 'insideEndTop', fontSize: 9, color: '#aaa' }
  }))

  return {
    backgroundColor: '#1a1a1a',
    animation: false,
    grid: { top: 36, right: 16, bottom: 24, left: 54 },
    xAxis: {
      type: 'value', min: 0,
      axisLine: { lineStyle: { color: '#444' } },
      axisLabel: { show: false },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      name: yc.name,
      nameTextStyle: { color: '#888', fontSize: 9 },
      min: yc.min, max: yc.max,
      axisLine: { lineStyle: { color: '#444' } },
      axisLabel: { color: '#888', fontSize: 10 },
      splitLine: { lineStyle: { color: '#2a2a2a' } },
    },
    legend: {
      top: 4, right: 8,
      textStyle: { color: '#ccc', fontSize: 11 },
      data: [driverA.code, driverB.code],
    },
    series: [
      {
        name: driverA.code, type: 'line',
        data: distA.map((d, i) => [d, dataA[i]]),
        symbol: 'none',
        lineStyle: { color: driverA.color, width: 1.5 },
        markLine: {
          silent: true, symbol: 'none',
          lineStyle: { color: '#555', type: 'dashed', width: 0.8 },
          data: markLines,
        }
      },
      {
        name: driverB.code, type: 'line',
        data: distB.map((d, i) => [d, dataB[i]]),
        symbol: 'none',
        lineStyle: { color: driverB.color, width: 1.5 },
      }
    ],
  }
}

function buildSampleIndices(length, maxPoints = MAX_CHART_POINTS) {
  if (!length || length <= maxPoints) {
    return Array.from({ length }, (_, i) => i)
  }
  const indices = [0]
  const step = (length - 1) / (maxPoints - 1)
  let lastIndex = 0
  for (let i = 1; i < maxPoints - 1; i++) {
    const index = Math.round(i * step)
    if (index > lastIndex && index < length - 1) {
      indices.push(index)
      lastIndex = index
    }
  }
  if (indices[indices.length - 1] !== length - 1) {
    indices.push(length - 1)
  }
  return indices
}

function sampleSeries(values, indices) {
  return indices.map(index => values[index])
}

function downsampleDriverTelemetry(driverTelemetry) {
  const indices = buildSampleIndices((driverTelemetry.distance || []).length)
  const sampled = {
    distance: sampleSeries(driverTelemetry.distance || [], indices),
  }

  CHANNELS.forEach(channel => {
    sampled[channel] = sampleSeries(driverTelemetry[channel] || [], indices)
  })

  return sampled
}

function downsampleTelemetry(telemetry, driverCodes) {
  const sampled = {}
  driverCodes.forEach(code => {
    if (telemetry[code]) {
      sampled[code] = downsampleDriverTelemetry(telemetry[code])
    }
  })
  return sampled
}

Page({
  data: {
    year: 2026, round: null,
    d1: 'ALB', d2: 'ALO', session: 'Q',
    loading: false, error: '',
    driverA: null, driverB: null,
    gap: '', note: '',
    cornerLabels: [], cornerDistances: [],
    activeChart: 'speed',
    // lazyLoad=true：ec-canvas 不自动 init，由页面在数据就绪后手动触发
    ecConfig: { lazyLoad: true },
    // 悬浮查词
    termSheetVisible: false,
    termQuery: '',
    termResults: [],
    popularTerms: [],
    selectedTerm: null,
    allTerms: [],
    termsLoading: false,
    termsLoaded: false,
    fabX: 280,
    fabY: 500,
  },

  _chart: null,
  _telemetryCache: null,

  onLoad(options) {
    this.setData({
      year:    parseInt(options.year || 2026),
      round:   parseInt(options.round),
      d1:      options.d1 || 'ALB',
      d2:      options.d2 || 'ALO',
      session: options.session || 'Q',
    })
    this.loadTelemetry()
  },

  async loadTelemetry() {
    const { year, round, d1, d2, session } = this.data
    this.setData({ loading: true, error: '' })
    try {
      const res = await api.getTelemetry(year, round, d1, d2, session)
      const data = res.data
      this._telemetryCache = downsampleTelemetry(data.telemetry, [data.driver_a.code, data.driver_b.code])
      // 所有数据在同一个 setData 里更新，setData 回调时 wx:else 已渲染
      this.setData({
        loading: false,
        driverA: data.driver_a, driverB: data.driver_b,
        gap: data.gap, note: res.note || '',
        cornerLabels: data.corner_labels,
        cornerDistances: data.corner_distances,
        activeChart: 'speed',
      }, () => {
        // wx.nextTick 确保 ec-canvas 组件 DOM 完全就绪
        wx.nextTick(() => this._initChart())
      })
    } catch (e) {
      this.setData({ loading: false, error: typeof e === 'string' ? e : '数据加载失败' })
    }
  },

  // 手动初始化 canvas，避免 onInit 时序问题
  _initChart() {
    const ecCanvas = this.selectComponent('#ec-main')
    if (!ecCanvas) return
    ecCanvas.init((canvas, width, height, dpr) => {
      const chart = echarts.init(canvas, null, { width, height, devicePixelRatio: dpr })
      canvas.setChart(chart)
      this._chart = chart
      this._drawChart('speed')
      return chart
    })
  },

  _drawChart(channel) {
    const { driverA, driverB, cornerLabels, cornerDistances } = this.data
    const telemetry = this._telemetryCache
    if (!telemetry || !driverA || !driverB || !this._chart) return
    const option = buildOption(channel, telemetry, driverA, driverB, cornerLabels, cornerDistances)
    this._chart.setOption(option, true)
  },

  onChartTabChange(e) {
    const channel = e.currentTarget.dataset.chart
    if (channel === this.data.activeChart) return
    this.setData({ activeChart: channel })
    this._drawChart(channel)
  },

  onGoAnalysis() {
    const { year, round, d1, d2, session } = this.data
    wx.navigateTo({
      url: `/pages/analysis/analysis?year=${year}&round=${round}&d1=${d1}&d2=${d2}&session=${session}`
    })
  },

  // ── 悬浮查词 ──────────────────────────────────────
  async loadTermsData() {
    if (this.data.termsLoading || this.data.termsLoaded) return
    this.setData({ termsLoading: true })
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
        }),
        termsLoading: false,
        termsLoaded: true,
      })
      if (this.data.termQuery) {
        this._filterTerms(this.data.termQuery)
      }
    } catch(e) {
      console.error('loadTermsData', e)
      this.setData({ termsLoading: false })
    }
  },

  onTermFabTap() {
    this.setData({ termSheetVisible: true })
    this.loadTermsData()
  },

  closeTermSheet() {
    this.setData({ termSheetVisible: false, termQuery: '', termResults: [], selectedTerm: null })
  },

  onTermSearch(e) {
    const query = e.detail.value.toLowerCase().trim()
    this.setData({ termQuery: query })
    if (!query) {
      this.setData({ termResults: [] })
      return
    }
    if (!this.data.termsLoaded) {
      this.loadTermsData()
      return
    }
    this._filterTerms(query)
  },

  _filterTerms(query) {
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
