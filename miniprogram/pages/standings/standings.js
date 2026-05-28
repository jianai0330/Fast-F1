import * as echarts from '../../components/ec-canvas/echarts'
const { api } = require('../../utils/api')

function buildTrendOption(driverTrend) {
  if (!driverTrend || driverTrend.length === 0) return null

  const series = driverTrend.map(d => ({
    name: d.code,
    type: 'line',
    data: d.series,  // [[round, points], ...]
    symbol: 'circle',
    symbolSize: 5,
    lineStyle: { color: d.color, width: 2 },
    itemStyle: { color: d.color },
    encode: { x: 0, y: 1 },
  }))

  const maxRound = Math.max(...driverTrend.flatMap(d => d.series.map(p => p[0])))
  const maxPts = Math.max(...driverTrend.flatMap(d => d.series.map(p => p[1])))

  return {
    backgroundColor: '#1a1a1a',
    animation: false,
    grid: { top: 40, right: 16, bottom: 32, left: 44 },
    legend: {
      top: 4, right: 8,
      textStyle: { color: '#ccc', fontSize: 11 },
      data: driverTrend.map(d => d.code),
    },
    xAxis: {
      type: 'value',
      name: 'Round',
      nameTextStyle: { color: '#888', fontSize: 9 },
      min: 1, max: maxRound,
      minInterval: 1,
      axisLine: { lineStyle: { color: '#444' } },
      axisLabel: { color: '#888', fontSize: 9 },
      splitLine: { lineStyle: { color: '#2a2a2a' } },
    },
    yAxis: {
      type: 'value',
      name: 'Pts',
      nameTextStyle: { color: '#888', fontSize: 9 },
      min: 0,
      max: Math.ceil(maxPts * 1.1 / 10) * 10,
      axisLine: { lineStyle: { color: '#444' } },
      axisLabel: { color: '#888', fontSize: 9 },
      splitLine: { lineStyle: { color: '#2a2a2a' } },
    },
    series,
  }
}

Page({
  data: {
    year: 2026,
    loading: false,
    error: '',
    activeTab: 'driver',  // driver | constructor
    drivers: [],
    constructors: [],
    driverTrend: [],
    trendChartConfig: { lazyLoad: true },
  },

  _trendChart: null,

  onLoad(options) {
    const year = parseInt(options.year || 2026)
    this.setData({ year })
    this.loadStandings()
  },

  onShow() {
    wx.showTabBar({ animation: false })
    if (this.data.activeTab === 'driver' && this.data.driverTrend.length > 0) {
      wx.nextTick(() => this._ensureTrendChart())
    }
  },

  async loadStandings() {
    const hasData = this.data.drivers.length > 0
    if (!hasData) this.setData({ loading: true, error: '' })
    try {
      const res = await api.getStandings(this.data.year)
      const data = res.data
      this.setData({
        loading: false,
        drivers: data.drivers,
        constructors: data.constructors,
        driverTrend: data.driver_trend,
      }, () => {
        wx.nextTick(() => this._ensureTrendChart())
      })
    } catch (e) {
      this.setData({ loading: false, error: typeof e === 'string' ? e : '数据加载失败' })
    }
  },

  onTabChange(e) {
    const activeTab = e.currentTarget.dataset.tab
    this.setData({ activeTab })
    if (activeTab === 'driver' && this.data.driverTrend.length > 0) {
      wx.nextTick(() => this._ensureTrendChart())
    } else if (activeTab !== 'driver') {
      this._trendChart = null
    }
  },

  onDriverTap(e) {
    const { code, color, team, points, position, wins } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/driver/driver?code=${code}&color=${encodeURIComponent(color)}&team=${encodeURIComponent(team)}&points=${points}&position=${position}&wins=${wins}`
    })
  },

  _ensureTrendChart() {
    const trend = this.data.driverTrend
    if (!trend || trend.length === 0) return
    const option = buildTrendOption(trend)
    if (!option) return
    const ecCanvas = this.selectComponent('#ec-trend')
    if (!ecCanvas) return
    if (this._trendChart) {
      this._trendChart.setOption(option, true)
      return
    }
    ecCanvas.init((canvas, width, height, dpr) => {
      const chart = echarts.init(canvas, null, { width, height, devicePixelRatio: dpr })
      canvas.setChart(chart)
      this._trendChart = chart
      chart.setOption(option, true)
      return chart
    })
  },
})
