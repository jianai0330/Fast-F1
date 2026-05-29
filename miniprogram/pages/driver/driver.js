const { api } = require('../../utils/api')

const DRIVER_INFO = {
  ANT: {
    fullName: 'Andrea Kimi Antonelli',
    nameCn: '安东内利',
    number: 12,
    nationality: '意大利',
    flag: '🇮🇹',
    dob: '2006-08-25',
    bio: 'Bologna人，赛车手之子。7岁开始卡丁车，2019年加入梅赛德斯青训。2024年横扫F3、F2双料冠军，2025年以18岁之龄接替汉密尔顿出战F1，成为梅赛德斯史上最年轻正式车手。2026年赢得中国大奖赛，成为F1史上最年轻的分站冠军之一，并一度领跑车手积分榜。',
    careerStats: { seasons: 2, races: 24, podiums: 5, poles: 2, fastestLaps: 3 },
  },
  RUS: {
    fullName: 'George Russell',
    nameCn: '拉塞尔',
    number: 63,
    nationality: '英国',
    flag: '🇬🇧',
    dob: '1998-02-15',
    bio: 'Cambridgeshire人，2017年加入梅赛德斯青训。2018年F2冠军，2019年进入F1。在威廉姆斯三年间以弱旅之姿多次力压队友，2021年比利时大奖赛替补梅赛德斯即登领奖台。2022年正式加盟梅赛德斯，同年在巴西大奖赛首夺分站冠军。以精准的刹车点和出色的轮胎管理著称，是梅赛德斯技术反馈的核心支柱。',
    careerStats: { seasons: 7, races: 138, podiums: 18, poles: 4, fastestLaps: 9 },
  },
  LEC: {
    fullName: 'Charles Leclerc',
    nameCn: '勒克莱尔',
    number: 16,
    nationality: '摩纳哥',
    flag: '🇲🇨',
    dob: '1997-10-16',
    bio: '我男神',
    careerStats: { seasons: 8, races: 156, podiums: 38, poles: 26, fastestLaps: 8 },
  },
  HAM: {
    fullName: 'Lewis Hamilton',
    nameCn: '汉密尔顿',
    number: 44,
    nationality: '英国',
    flag: '🇬🇧',
    dob: '1985-01-07',
    bio: 'Stevenage人，F1史上最成功的车手。2008年首夺世界冠军，此后分别于2014、2015、2017、2018、2019、2020年六度称王，与舒马赫并列七冠纪录。持有F1最多胜场（105场）、最多杆位（104次）、最多领奖台（202次）等多项历史纪录。2025年以40岁高龄转会法拉利，开启职业生涯最后一段传奇旅程。',
    careerStats: { seasons: 19, races: 356, podiums: 202, poles: 104, fastestLaps: 67 },
  },
  NOR: {
    fullName: 'Lando Norris',
    nameCn: '诺里斯',
    number: 1,
    nationality: '英国',
    flag: '🇬🇧',
    dob: '1999-11-13',
    bio: 'Bristol人，2019年进入F1。2025年凭借赛季末段的强势发挥击败维斯塔潘，赢得个人首个F1世界冠军，成为麦克拉伦时隔26年再度捧杯。以流畅的高速弯角技术和出色的雨战能力著称，2026年以卫冕冠军身份使用 #1 号车，继续与麦克拉伦并肩作战。',
    careerStats: { seasons: 7, races: 138, podiums: 22, poles: 8, fastestLaps: 12 },
  },
  PIA: {
    fullName: 'Oscar Piastri',
    nameCn: '皮亚斯特里',
    number: 81,
    nationality: '澳大利亚',
    flag: '🇦🇺',
    dob: '2001-04-06',
    bio: 'Melbourne人，2021年F3冠军、2022年F2冠军，但因合同纠纷错过2023年F1席位，最终加盟麦克拉伦。2024年在匈牙利大奖赛首夺分站冠军，同年赢得阿塞拜疆大奖赛。以冷静沉稳的驾驶风格和极强的学习能力著称，被誉为麦克拉伦未来的核心。',
    careerStats: { seasons: 3, races: 58, podiums: 12, poles: 3, fastestLaps: 5 },
  },
  VER: {
    fullName: 'Max Verstappen',
    nameCn: '维斯塔潘',
    number: 3,
    nationality: '荷兰',
    flag: '🇳🇱',
    dob: '1997-09-30',
    bio: '汽车人。',
    careerStats: { seasons: 11, races: 214, podiums: 112, poles: 40, fastestLaps: 32 },
  },
  TSU: {
    fullName: 'Yuki Tsunoda',
    nameCn: '角田裕毅',
    number: 22,
    nationality: '日本',
    flag: '🇯🇵',
    dob: '2000-05-11',
    bio: 'Kanagawa人，本田青训出身。2021年进入F1，是近年来最受日本车迷关注的本土车手。以极具攻击性的驾驶风格和出色的单圈速度著称，但早期情绪管理是其短板。经过五年磨砺后于2026年升入红牛一队，与维斯塔潘搭档，迎来职业生涯最重要的挑战。',
    careerStats: { seasons: 5, races: 98, podiums: 2, poles: 0, fastestLaps: 4 },
  },
  ALB: {
    fullName: 'Alexander Albon',
    nameCn: '阿尔本',
    number: 23,
    nationality: '泰国',
    flag: '🇹🇭',
    dob: '1996-03-23',
    bio: 'Westminster人，父亲为英国赛车手，母亲为泰国人。2019年进入F1，同年升入红牛一队，但因表现不稳定于2020年底被降回小红牛，随后离队。2022年以威廉姆斯车手身份回归F1，凭借稳定的发挥和出色的轮胎管理重新赢得业界认可，成为中游车队的标杆车手。',
    careerStats: { seasons: 6, races: 98, podiums: 2, poles: 0, fastestLaps: 2 },
  },
  SAI: {
    fullName: 'Carlos Sainz',
    nameCn: '塞恩斯',
    number: 55,
    nationality: '西班牙',
    flag: '🇪🇸',
    dob: '1994-09-01',
    bio: '老公级别的',
    careerStats: { seasons: 10, races: 198, podiums: 24, poles: 5, fastestLaps: 14 },
  },
  ALO: {
    fullName: 'Fernando Alonso',
    nameCn: '阿隆索',
    number: 14,
    nationality: '西班牙',
    flag: '🇪🇸',
    dob: '1981-07-29',
    bio: 'Oviedo人，F1史上最具传奇色彩的车手之一。2005、2006年连续两届世界冠军，是打破舒马赫五连冠的第一人。职业生涯横跨23个赛季，32场分站冠军，106次领奖台。场外同样战绩辉煌：两夺勒芒24小时赛冠军、WEC年度冠军、印第安纳波利斯500英里赛亚军。以超强的比赛智慧、精妙的防守技术和永不言败的斗志著称。',
    careerStats: { seasons: 23, races: 400, podiums: 106, poles: 32, fastestLaps: 23 },
  },
  STR: {
    fullName: 'Lance Stroll',
    nameCn: '斯特罗尔',
    number: 18,
    nationality: '加拿大',
    flag: '🇨🇦',
    dob: '1998-10-29',
    bio: 'Montréal人，父亲为阿斯顿马丁车队老板劳伦斯·斯特罗尔。2017年进入F1，同年在阿塞拜疆大奖赛以18岁之龄登上领奖台，成为F1史上最年轻的领奖台车手之一。以雨战表现出色著称，2020年土耳其大奖赛在湿地条件下夺得杆位。',
    careerStats: { seasons: 8, races: 158, podiums: 3, poles: 1, fastestLaps: 2 },
  },
  GAS: {
    fullName: 'Pierre Gasly',
    nameCn: '加斯利',
    number: 10,
    nationality: '法国',
    flag: '🇫🇷',
    dob: '1996-02-07',
    bio: 'Rouen人，红牛青训出身。2017年进入F1，2018年升入红牛一队，但因表现不稳定被降回小红牛。2020年在意大利大奖赛以小红牛车手身份夺得分站冠军，成为当时最大冷门之一。2022年转会阿尔派因，成为车队领军人物，以出色的单圈速度和稳定的正赛发挥著称。',
    careerStats: { seasons: 8, races: 158, podiums: 4, poles: 1, fastestLaps: 5 },
  },
  DOO: {
    fullName: 'Jack Doohan',
    nameCn: '杜汉',
    number: 7,
    nationality: '澳大利亚',
    flag: '🇦🇺',
    dob: '2003-01-20',
    bio: 'Gold Coast人，摩托车传奇车手迈克尔·杜汉之子。2022年F3亚军，2023年F2亚军，2025年正式加入阿尔派因出战F1。以积极进取的驾驶风格和强大的心理素质著称，是阿尔派因重建计划的核心年轻力量。',
    careerStats: { seasons: 1, races: 24, podiums: 0, poles: 0, fastestLaps: 0 },
  },
  HUL: {
    fullName: '',
    nameCn: '',
    number: 27,
    nationality: '',
    flag: '',
    dob: '',
    bio: '',
    careerStats: {seasons: 13, races: 218, podiums: 0, poles: 1, fastestLaps: 10},
  },
  BOR: {
    fullName: '',
    nameCn: '',
    number: 5,
    nationality: '',
    flag: '',
    dob: '',
    bio: '',
    careerStats: {seasons: 1, races: 24, podiums: 0, poles: 0, fastestLaps: 0},
  },
  OCO: {
    fullName: '',
    nameCn: '',
    number: 31,
    nationality: '',
    flag: '',
    dob: '',
    bio: '',
    careerStats: {seasons: 8, races: 158, podiums: 3, poles: 0, fastestLaps: 2},
  },
  BEA: {
    fullName: '',
    nameCn: '',
    number: 87,
    nationality: '',
    flag: '',
    dob: '',
    bio: '',
    careerStats: {seasons: 2, races: 28, podiums: 0, poles: 0, fastestLaps: 0},
  },
  LAW: {
    fullName: '',
    nameCn: '',
    number: 30,
    nationality: '',
    flag: '',
    dob: '',
    bio: '',
    careerStats: {seasons: 2, races: 38, podiums: 0, poles: 0, fastestLaps: 1},
  },
  HAD: {
    fullName: '',
    nameCn: '',
    number: 6,
    nationality: '',
    flag: '',
    dob: '',
    bio: '',
    careerStats: {seasons: 1, races: 24, podiums: 0, poles: 0, fastestLaps: 0},
  },
  MAG: {
    fullName: '',
    nameCn: '',
    number: 20,
    nationality: '',
    flag: '',
    dob: '',
    bio: '',
    careerStats: {seasons: 10, races: 178, podiums: 1, poles: 0, fastestLaps: 2},
  },
  LIN: {
    fullName: '',
    nameCn: '',
    number: 8,
    nationality: '',
    flag: '',
    dob: '',
    bio: '',
    careerStats: {seasons: 1, races: 24, podiums: 0, poles: 0, fastestLaps: 0},
  },
  COL: {
    fullName: '',
    nameCn: '',
    number: 43,
    nationality: '',
    flag: '',
    dob: '',
    bio: '',
    careerStats: {seasons: 2, races: 30, podiums: 0, poles: 0, fastestLaps: 1},
  },
  BOT: {
    fullName: '',
    nameCn: '',
    number: 77,
    nationality: '',
    flag: '',
    dob: '',
    bio: '',
    careerStats: {seasons: 13, races: 258, podiums: 67, poles: 20, fastestLaps: 19},
  },
  PER: {
    fullName: '',
    nameCn: '',
    number: 11,
    nationality: '',
    flag: '',
    dob: '',
    bio: '',
    careerStats: {seasons: 15, races: 290, podiums: 38, poles: 3, fastestLaps: 14},
  },
}

const DIMS = [
  { key: 'speed',   label: '单圈速度' },
  { key: 'consist', label: '稳定性'   },
  { key: 'defend',  label: '防守'     },
  { key: 'wet',     label: '雨战'     },
  { key: 'mental',  label: '心理素质' },
]

function calcAge(dob) {
  const birth = new Date(dob)
  const now = new Date()
  let age = now.getFullYear() - birth.getFullYear()
  const m = now.getMonth() - birth.getMonth()
  if (m < 0 || (m === 0 && now.getDate() < birth.getDate())) age--
  return age
}

Page({
  data: {
    code: '',
    color: '#e10600',
    info: null,
    season: null,
    trend: [],
    // 评分
    ratingDims: DIMS.map(d => ({ ...d, val: 0 })),
    ratingReady: false,
    ratingSubmitted: false,
    communityAvg: '0.0',
    communityCount: 0,
    communityDims: [],
    myScoreText: '',
    // 评论
    comments: [],
    commentsPage: 1,
    commentsHasMore: false,
    commentsLoading: false,
    commentDraft: '',
    hasUser: false,
    openid: '',
  },

  onLoad(options) {
    const code = options.code
    const color = decodeURIComponent(options.color || '#e10600')
    const team = decodeURIComponent(options.team || '')
    const points = parseFloat(options.points || 0)
    const position = parseInt(options.position || 0)
    const wins = parseInt(options.wins || 0)

    const raw = DRIVER_INFO[code]
    const info = raw ? { ...raw, age: calcAge(raw.dob), team } : null

    this.setData({ code, color, info, season: { position, points, wins } })
    wx.setNavigationBarTitle({ title: info ? info.nameCn : code })
    this.loadTrend()
    this._loadRating(code)
    this._initUser()
    this._loadComments(code, 1)
  },

  onShow() {
    // 从注册页返回后刷新登录状态
    this._initUser()
  },

  async loadTrend() {
    try {
      const res = await api.getStandings(2026)
      const driverTrend = res.data.driver_trend || []
      const mine = driverTrend.find(d => d.code === this.data.code)
      if (mine) {
        const trendMax = Math.max(...mine.series.map(p => p[1]), 1)
        this.setData({ trend: mine.series, trendMax })
      }
    } catch (e) {}
  },

  // ── 评分逻辑 ──────────────────────────────────────

  // 获取持久设备 ID（由 app.js 在 onLaunch 中生成），确保评分/评论不因重编译丢失
  _getPersistentUid() {
    const app = getApp()
    return app.globalData.deviceId || wx.getStorageSync('f1_device_id') || ''
  },

  _ratingKey(code) { return `f1_rating_${code}` },

  async _loadRating(code) {
    const uid = wx.getStorageSync('f1_openid') || this._getPersistentUid()
    try {
      const res = await api.getDriverRating(code, uid)
      const { aggregate, mine } = res.data
      this._renderCommunity(aggregate, mine)
      if (mine) {
        const dims = this.data.ratingDims.map(d => ({ ...d, val: mine[d.key] || 0 }))
        this.setData({ ratingDims: dims, ratingReady: true })
      }
    } catch (e) {
      // 离线回退：只恢复本人评分状态，不伪造社区数据
      const myRaw = wx.getStorageSync(this._ratingKey(code))
      if (myRaw) {
        const dims = this.data.ratingDims.map(d => ({ ...d, val: myRaw[d.key] || 0 }))
        this.setData({
          ratingDims: dims,
          ratingReady: true,
          ratingSubmitted: true,
          myScoreText: DIMS.map(d => `${d.label} ${myRaw[d.key]}`).join('  '),
        })
      }
    }
  },

  onStarTap(e) {
    const { dim, val } = e.currentTarget.dataset
    const dims = this.data.ratingDims.map((d, i) => i === dim ? { ...d, val } : d)
    const ready = dims.every(d => d.val > 0)
    this.setData({ ratingDims: dims, ratingReady: ready })
  },

  async onRatingSubmit() {
    if (!this.data.ratingReady) return
    const { code } = this.data
    const uid = wx.getStorageSync('f1_openid') || this._getPersistentUid()
    const scores = {}
    this.data.ratingDims.forEach(d => { scores[d.key] = d.val })
    try {
      const res = await api.postDriverRating(code, uid, scores)
      const { aggregate, mine } = res.data
      this._renderCommunity(aggregate, mine)
      wx.setStorageSync(this._ratingKey(code), mine)
      wx.showToast({ title: '评分成功 🏁', icon: 'none', duration: 1500 })
    } catch (e) {
      wx.showToast({ title: typeof e === 'string' ? e : '提交失败', icon: 'none', duration: 2000 })
    }
  },

  _renderCommunity(agg, mine) {
    // agg 格式：{ count, avgs: { speed, consist, defend, wet, mental } }
    const count = (agg && agg.count) || 0
    const avgs = (agg && agg.avgs) || {}
    const dimAvgs = DIMS.map(d => {
      const avg = parseFloat(avgs[d.key] || 0).toFixed(1)
      return { ...d, avg, pct: Math.round((avg / 5) * 100) }
    })
    const total = dimAvgs.reduce((s, d) => s + parseFloat(d.avg), 0)
    const communityAvg = count > 0 ? (total / DIMS.length).toFixed(1) : '0.0'
    const myScoreText = mine
      ? DIMS.map(d => `${d.label} ${mine[d.key]}`).join('  ')
      : ''
    this.setData({
      ratingSubmitted: !!mine,
      communityAvg,
      communityCount: count,
      communityDims: dimAvgs,
      myScoreText,
    })
  },

  // ── 评论逻辑 ──────────────────────────────────────

  _initUser() {
    const openid = wx.getStorageSync('f1_openid') || ''
    this.setData({ hasUser: !!openid, openid })
  },

  async _loadComments(code, page) {
    this.setData({ commentsLoading: true })
    try {
      const res = await api.getDriverComments(code, page)
      const list = res.data.comments || []
      const comments = page === 1 ? list : [...this.data.comments, ...list]
      this.setData({
        comments,
        commentsPage: page,
        commentsHasMore: list.length === 20,
        commentsLoading: false,
      })
    } catch (e) {
      this.setData({ commentsLoading: false })
    }
  },

  onCommentInput(e) {
    this.setData({ commentDraft: e.detail.value })
  },

  async onCommentSend() {
    const content = this.data.commentDraft.trim()
    if (!content) return
    const { code, openid } = this.data
    try {
      await api.postDriverComment(code, openid, content)
      this.setData({ commentDraft: '' })
      await this._loadComments(code, 1)
    } catch (e) {
      wx.showToast({ title: typeof e === 'string' ? e : '发送失败', icon: 'none', duration: 2000 })
    }
  },

  async onCommentLike(e) {
    const { id, idx } = e.currentTarget.dataset
    try {
      const res = await api.likeDriverComment(id)
      const comments = [...this.data.comments]
      comments[idx] = { ...comments[idx], likes: res.data.likes }
      this.setData({ comments })
    } catch (e) {}
  },

  onLoadMoreComments() {
    this._loadComments(this.data.code, this.data.commentsPage + 1)
  },

  onGoRegister() {
    wx.navigateTo({ url: '/pages/forum-register/forum-register' })
  },
})
