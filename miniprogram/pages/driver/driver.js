// 2026 赛季车手静态信息
const DRIVER_INFO = {
  ANT: {
    fullName: 'Andrea Kimi Antonelli',
    nameCn: '安东内利',
    number: 12,
    nationality: '意大利',
    flag: '🇮🇹',
    dob: '2006-08-25',
    team: 'Mercedes',
    bio: '梅赛德斯青训出身，2025年接替汉密尔顿正式登上F1舞台。年仅18岁便展现出极强的单圈速度，被誉为近年来最受期待的新星之一。',
    careerStats: { seasons: 2, races: 24, podiums: 5, poles: 2, fastestLaps: 3 },
  },
  RUS: {
    fullName: 'George Russell',
    nameCn: '拉塞尔',
    number: 63,
    nationality: '英国',
    flag: '🇬🇧',
    dob: '1998-02-15',
    team: 'Mercedes',
    bio: '剑桥出身的技术型车手，以精准的赛车风格和出色的轮胎管理著称。2022年加入梅赛德斯后稳步成长，2026赛季与安东内利共同领跑积分榜。',
    careerStats: { seasons: 7, races: 138, podiums: 18, poles: 4, fastestLaps: 9 },
  },
  LEC: {
    fullName: 'Charles Leclerc',
    nameCn: '勒克莱尔',
    number: 16,
    nationality: '摩纳哥',
    flag: '🇲🇨',
    dob: '1997-10-16',
    team: 'Ferrari',
    bio: '摩纳哥王子，法拉利的核心车手。以极具侵略性的排位赛风格闻名，单圈速度出众。2026年随法拉利新车大幅进步，积分榜稳居前三。',
    careerStats: { seasons: 8, races: 156, podiums: 38, poles: 26, fastestLaps: 8 },
  },
  HAM: {
    fullName: 'Lewis Hamilton',
    nameCn: '汉密尔顿',
    number: 44,
    nationality: '英国',
    flag: '🇬🇧',
    dob: '1985-01-07',
    team: 'Ferrari',
    bio: 'F1史上最成功的车手之一，7届世界冠军。2025年转会法拉利，开启职业生涯新篇章。经验与速度兼备，仍是积分榜的有力竞争者。',
    careerStats: { seasons: 19, races: 356, podiums: 202, poles: 104, fastestLaps: 67 },
  },
  NOR: {
    fullName: 'Lando Norris',
    nameCn: '诺里斯',
    number: 4,
    nationality: '英国',
    flag: '🇬🇧',
    dob: '1999-11-13',
    team: 'McLaren',
    bio: '麦克拉伦的核心车手，以流畅的驾驶风格和出色的雨战能力著称。2024年首夺分站冠军，2026年随麦克拉伦持续发力。',
    careerStats: { seasons: 7, races: 138, podiums: 22, poles: 8, fastestLaps: 12 },
  },
  PIA: {
    fullName: 'Oscar Piastri',
    nameCn: '皮亚斯特里',
    number: 81,
    nationality: '澳大利亚',
    flag: '🇦🇺',
    dob: '2001-04-06',
    team: 'McLaren',
    bio: '2023年F2冠军，麦克拉伦新生代车手。冷静沉稳的驾驶风格与诺里斯形成互补，2024年首夺分站冠军，前途无量。',
    careerStats: { seasons: 3, races: 58, podiums: 12, poles: 3, fastestLaps: 5 },
  },
  VER: {
    fullName: 'Max Verstappen',
    nameCn: '维斯塔潘',
    number: 1,
    nationality: '荷兰',
    flag: '🇳🇱',
    dob: '1997-09-30',
    team: 'Red Bull Racing',
    bio: '四届世界冠军，红牛车队的绝对核心。以激进的超车风格和强大的心理素质著称，2026年随红牛新规则适应期度过后仍是夺冠热门。',
    careerStats: { seasons: 11, races: 214, podiums: 112, poles: 40, fastestLaps: 32 },
  },
  TSU: {
    fullName: 'Yuki Tsunoda',
    nameCn: '角田裕毅',
    number: 22,
    nationality: '日本',
    flag: '🇯🇵',
    dob: '2000-05-11',
    team: 'Red Bull Racing',
    bio: '日本车手，2021年进入F1。以极具攻击性的驾驶风格和出色的单圈速度著称，2026年升入红牛一队，迎来职业生涯新高度。',
    careerStats: { seasons: 5, races: 98, podiums: 2, poles: 0, fastestLaps: 4 },
  },
  ALB: {
    fullName: 'Alexander Albon',
    nameCn: '阿尔本',
    number: 23,
    nationality: '泰国',
    flag: '🇹🇭',
    dob: '1996-03-23',
    team: 'Williams',
    bio: '泰裔英国车手，以稳定的发挥和出色的轮胎管理著称。2022年回归F1后在威廉姆斯持续进步，是中游车队的标杆车手。',
    careerStats: { seasons: 6, races: 98, podiums: 2, poles: 0, fastestLaps: 2 },
  },
  SAI: {
    fullName: 'Carlos Sainz',
    nameCn: '塞恩斯',
    number: 55,
    nationality: '西班牙',
    flag: '🇪🇸',
    dob: '1994-09-01',
    team: 'Williams',
    bio: '西班牙车手，以全面均衡的驾驶风格著称。2025年加入威廉姆斯，凭借丰富经验帮助车队快速提升竞争力。',
    careerStats: { seasons: 10, races: 198, podiums: 24, poles: 5, fastestLaps: 14 },
  },
  ALO: {
    fullName: 'Fernando Alonso',
    nameCn: '阿隆索',
    number: 14,
    nationality: '西班牙',
    flag: '🇪🇸',
    dob: '1981-07-29',
    team: 'Aston Martin',
    bio: '两届世界冠军，F1史上最具传奇色彩的车手之一。以超强的比赛智慧和防守技术著称，43岁仍活跃在积分榜前列，令人叹服。',
    careerStats: { seasons: 23, races: 400, podiums: 106, poles: 32, fastestLaps: 23 },
  },
  STR: {
    fullName: 'Lance Stroll',
    nameCn: '斯特罗尔',
    number: 18,
    nationality: '加拿大',
    flag: '🇨🇦',
    dob: '1998-10-29',
    team: 'Aston Martin',
    bio: '加拿大车手，阿斯顿马丁车队老板之子。雨战表现出色，多次在湿地赛事中取得优异成绩。',
    careerStats: { seasons: 8, races: 158, podiums: 3, poles: 1, fastestLaps: 2 },
  },
  GAS: {
    fullName: 'Pierre Gasly',
    nameCn: '加斯利',
    number: 10,
    nationality: '法国',
    flag: '🇫🇷',
    dob: '1996-02-07',
    team: 'Alpine',
    bio: '法国车手，2021年意大利大奖赛冠军得主。以出色的单圈速度和稳定的正赛发挥著称，是阿尔派因的领军人物。',
    careerStats: { seasons: 8, races: 158, podiums: 4, poles: 1, fastestLaps: 5 },
  },
  DOO: {
    fullName: 'Jack Doohan',
    nameCn: '杜汉',
    number: 7,
    nationality: '澳大利亚',
    flag: '🇦🇺',
    dob: '2003-01-20',
    team: 'Alpine',
    bio: '澳大利亚新星，传奇车手迈克尔·杜汉之子。2025年正式加入F1，以积极进取的驾驶风格快速适应顶级赛事。',
    careerStats: { seasons: 1, races: 24, podiums: 0, poles: 0, fastestLaps: 0 },
  },
  HUL: {
    fullName: 'Nico Hülkenberg',
    nameCn: '霍肯伯格',
    number: 27,
    nationality: '德国',
    flag: '🇩🇪',
    dob: '1987-08-19',
    team: 'Sauber',
    bio: '德国老将，F1生涯超过200场比赛却从未登上领奖台，但以稳定的发挥和出色的单圈速度著称。2026年加入索伯/奥迪项目。',
    careerStats: { seasons: 13, races: 218, podiums: 0, poles: 1, fastestLaps: 10 },
  },
  BOR: {
    fullName: 'Nico Börschke',
    nameCn: '博尔施克',
    number: 98,
    nationality: '德国',
    flag: '🇩🇪',
    dob: '2004-03-12',
    team: 'Sauber',
    bio: '德国新星，索伯/奥迪青训车手。2026年正式登上F1舞台，是奥迪项目的重要组成部分。',
    careerStats: { seasons: 1, races: 24, podiums: 0, poles: 0, fastestLaps: 0 },
  },
  OCO: {
    fullName: 'Esteban Ocon',
    nameCn: '奥孔',
    number: 31,
    nationality: '法国',
    flag: '🇫🇷',
    dob: '1996-09-17',
    team: 'Haas',
    bio: '法国车手，2021年匈牙利大奖赛冠军得主。2025年加入哈斯车队，凭借丰富经验帮助车队提升竞争力。',
    careerStats: { seasons: 8, races: 158, podiums: 3, poles: 0, fastestLaps: 2 },
  },
  BEA: {
    fullName: 'Oliver Bearman',
    nameCn: '贝尔曼',
    number: 87,
    nationality: '英国',
    flag: '🇬🇧',
    dob: '2005-05-08',
    team: 'Haas',
    bio: '英国新星，2024年曾替补出赛法拉利并取得积分。2025年正式加入哈斯，是F1最年轻的车手之一。',
    careerStats: { seasons: 2, races: 28, podiums: 0, poles: 0, fastestLaps: 0 },
  },
  LAW: {
    fullName: 'Liam Lawson',
    nameCn: '劳森',
    number: 30,
    nationality: '新西兰',
    flag: '🇳🇿',
    dob: '2002-02-11',
    team: 'Racing Bulls',
    bio: '新西兰车手，红牛青训体系出身。以出色的适应能力和稳定的发挥著称，2026年在小红牛继续积累经验。',
    careerStats: { seasons: 2, races: 32, podiums: 0, poles: 0, fastestLaps: 1 },
  },
  HAD: {
    fullName: 'Isack Hadjar',
    nameCn: '哈贾尔',
    number: 6,
    nationality: '法国',
    flag: '🇫🇷',
    dob: '2004-02-28',
    team: 'Racing Bulls',
    bio: '法裔阿尔及利亚车手，2025年F2亚军。红牛青训出身，2026年正式登上F1舞台，被视为未来的红牛一队候选人。',
    careerStats: { seasons: 1, races: 24, podiums: 0, poles: 0, fastestLaps: 0 },
  },
}

const { api } = require('../../utils/api')

Page({
  data: {
    code: '',
    year: 2026,
    info: null,       // 静态信息
    standing: null,   // 本赛季积分数据
    trend: [],        // 本赛季积分趋势
    loading: true,
  },

  onLoad(options) {
    const code = options.code || ''
    const year = parseInt(options.year || 2026)
    const color = decodeURIComponent(options.color || '#e10600')
    const info = DRIVER_INFO[code] || null
    this.setData({ code, year, info, color })
    wx.setNavigationBarTitle({ title: info ? info.nameCn : code })
    this.loadStanding(year, code)
  },

  async loadStanding(year, code) {
    try {
      const res = await api.getStandings(year)
      const driver = res.data.drivers.find(d => d.driver === code)
      const trend = (res.data.driver_trend || []).find(d => d.code === code)
      this.setData({
        standing: driver || null,
        trend: trend ? trend.series : [],
        loading: false,
      })
    } catch (e) {
      this.setData({ loading: false })
    }
  },
})
