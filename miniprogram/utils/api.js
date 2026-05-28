const app = getApp()

// 各接口缓存 TTL（毫秒）
const CACHE_TTL = {
  '/standings':   30 * 60 * 1000,
  '/events':      60 * 60 * 1000,
  '/qualifying':  10 * 60 * 1000,
  '/laptimes':    10 * 60 * 1000,
  '/telemetry':   10 * 60 * 1000,
  '/analysis':    30 * 60 * 1000,
  '/circuit':     60 * 60 * 1000,
  '/news':         5 * 60 * 1000,
  '/news_detail':  5 * 60 * 1000,
  '/terms':       30 * 60 * 1000,  // 词典 30 分钟
}

function cacheKey(path, params) {
  const q = Object.entries(params)
    .filter(([, v]) => v !== null && v !== undefined)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${k}=${v}`)
    .join('&')
  return `f1cache:${path}?${q}`
}

function cacheGet(key, ttl) {
  try {
    const raw = wx.getStorageSync(key)
    if (raw && raw.ts && raw.data && Date.now() - raw.ts < ttl) {
      return raw.data
    }
  } catch (e) {}
  return null
}

function cacheSet(key, data) {
  try {
    wx.setStorageSync(key, { ts: Date.now(), data })
  } catch (e) {}
}

/**
 * 封装 wx.request，返回 Promise（GET），超时 20s，失败自动重试一次
 */
function _doRequest(fullUrl, method, data, headers) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: fullUrl,
      method,
      data,
      header: headers,
      timeout: 20000,
      success(res) {
        if (res.data && res.data.status === 'ok') {
          resolve(res.data)
        } else {
          reject(res.data?.note || '请求失败')
        }
      },
      fail(err) {
        reject(err.errMsg || '网络错误')
      }
    })
  })
}

function request(path, params = {}, headers = {}) {
  const url = app.globalData.BASE_URL + path
  const query = Object.entries(params)
    .filter(([, v]) => v !== null && v !== undefined)
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
    .join('&')
  const fullUrl = query ? `${url}?${query}` : url
  return _doRequest(fullUrl, 'GET', undefined, headers)
    .catch(() => _doRequest(fullUrl, 'GET', undefined, headers))
}

/**
 * POST 请求封装
 */
function post(path, data = {}, headers = {}) {
  const url = app.globalData.BASE_URL + path
  return _doRequest(url, 'POST', data, { 'content-type': 'application/json', ...headers })
    .catch(() => _doRequest(url, 'POST', data, { 'content-type': 'application/json', ...headers }))
}

/** 管理员 Token（与后端 ADMIN_TOKEN 一致） */
const ADMIN_TOKEN = 'f1admin2026'
const adminHeader = () => ({ 'X-Admin-Token': ADMIN_TOKEN })

/**
 * 带本地缓存的请求：命中缓存直接返回，同时后台静默刷新
 * @param {string} cacheKeyStr  缓存 key（唯一标识这条请求）
 * @param {string} ttlKey       CACHE_TTL 里的 key
 * @param {string} path         实际请求路径
 * @param {object} params       请求参数
 */
function cachedRequest(cacheKeyStr, ttlKey, path, params = {}) {
  // 兼容旧调用：cachedRequest(path, params)
  if (typeof ttlKey === 'object') {
    params = ttlKey
    path = cacheKeyStr
    ttlKey = cacheKeyStr
  }
  const ttl = CACHE_TTL[ttlKey]
  if (!ttl) return request(path, params)

  const key = `f1cache:${cacheKeyStr}`
  const cached = cacheGet(key, ttl)

  if (cached) {
    request(path, params).then(res => cacheSet(key, res)).catch(() => {})
    return Promise.resolve(cached)
  }

  return request(path, params).then(res => {
    cacheSet(key, res)
    return res
  })
}

// 各接口封装
const api = {
  // ── 原有接口 ────────────────────────────────────
  getEvents: (year = 2026) =>
    cachedRequest(`/events:${year}`, '/events', '/events', { year }),

  getQualifying: (year, round_num) =>
    cachedRequest(`/qualifying:${year}:${round_num}`, '/qualifying', '/qualifying', { year, round_num }),

  getLaptimes: (year, round_num, session = 'R') =>
    cachedRequest(`/laptimes:${year}:${round_num}:${session}`, '/laptimes', '/laptimes', { year, round_num, session }),

  getTelemetry: (year, round_num, d1, d2, session = 'Q') =>
    cachedRequest(`/telemetry:${year}:${round_num}:${d1}:${d2}:${session}`, '/telemetry', '/telemetry', { year, round_num, d1, d2, session }),

  getStandings: (year = 2026) =>
    cachedRequest(`/standings:${year}`, '/standings', '/standings', { year }),

  getAnalysis: (year, round_num, d1, d2, session = 'Q', force = false) => {
    if (force) {
      // 强制刷新：跳过本地缓存，直接请求后端（带 force=true）
      const key = `f1cache:/analysis:${year}:${round_num}:${d1}:${d2}:${session}`
      try { wx.removeStorageSync(key) } catch (e) {}
      return request('/analysis', { year, round_num, d1, d2, session, force: 1 })
    }
    return cachedRequest(`/analysis:${year}:${round_num}:${d1}:${d2}:${session}`, '/analysis', '/analysis', { year, round_num, d1, d2, session })
  },

  getCircuit: (year, round_num) =>
    cachedRequest(`/circuit:${year}:${round_num}`, '/circuit', `/events/${round_num}/circuit`, { year }),

  // ── 资讯 ────────────────────────────────────────
  getNews: (page = 1, team = null, keyword = null, language = 'all') =>
    cachedRequest(`/news:${page}:${team || ''}:${keyword || ''}:${language}`, '/news', '/news',
      { ...(team ? { team } : {}), page, ...(keyword ? { keyword } : {}), language }),

  getNewsDetail: (id) =>
    request(`/news/${id}`),

  getTeamsByNews: (news_id) =>
    request(`/news/${news_id}/teams`),

  // ── 热门推荐 ──────────────────────────────────
  getHotPosts: (limit = 5) =>
    request('/hot/posts', { limit }),

  getHotNews: (limit = 3) =>
    request('/hot/news', { limit }),

  // ── 论坛：用户 ──────────────────────────────────
  registerUser: (code, nickname) =>
    post('/forum/users/register', { code, nickname }),

  getMe: (openid) =>
    request('/forum/users/me', { openid }),

  // ── 论坛：分区 ──────────────────────────────────
  getForumSections: () =>
    request('/forum/sections'),

  // ── 论坛：帖子 ──────────────────────────────────
  getForumPosts: (section_id, page = 1, sort = 'latest') =>
    request('/forum/posts', { section_id, page, sort }),

  getForumPost: (id) =>
    request(`/forum/posts/${id}`),

  createPost: (section_id, title, content, openid, news_id = null, curated_id = null) =>
    post('/forum/posts', { section_id, title, content, openid, ...(news_id ? { news_id } : {}), ...(curated_id ? { curated_id } : {}) }),

  deletePost: (post_id, openid) => {
    const url = getApp().globalData.BASE_URL + `/forum/posts/${post_id}`
    return new Promise((resolve, reject) => {
      wx.request({
        url, method: 'DELETE',
        data: JSON.stringify({ openid }),
        header: { 'content-type': 'application/json' },
        success(res) {
          res.data?.status === 'ok' ? resolve(res.data) : reject(res.data?.note || '请求失败')
        },
        fail(err) { reject(err.errMsg || '网络错误') }
      })
    })
  },

  likePost: (post_id, openid, type) =>
    post(`/forum/posts/${post_id}/like`, { openid, type }),

  getLike: (post_id, openid) =>
    request(`/forum/posts/${post_id}/like`, { openid }),

  getNewsPosts: (news_id) =>
    request(`/news/${news_id}/posts`),

  getCuratedPosts: (curated_id) =>
    request(`/curated/${curated_id}/posts`),

  triggerAnalyzePublic: (news_id, force = false) =>
    post(`/news/${news_id}/analyze-public${force ? '?force=true' : ''}`, {}),

  // ── 论坛：评论 ──────────────────────────────────
  getForumComments: (post_id) =>
    request(`/forum/posts/${post_id}/comments`),

  createComment: (post_id, content, openid) =>
    post(`/forum/posts/${post_id}/comments`, { content, openid }),

  // ── 管理后台 ─────────────────────────────────────
  adminGetPosts: () =>
    request('/admin/posts', {}, adminHeader()),

  adminApprovePost: (id) =>
    post(`/admin/posts/${id}/approve`, {}, adminHeader()),

  adminRejectPost: (id) =>
    post(`/admin/posts/${id}/reject`, {}, adminHeader()),

  adminGetComments: () =>
    request('/admin/comments', {}, adminHeader()),

  adminApproveComment: (id) =>
    post(`/admin/comments/${id}/approve`, {}, adminHeader()),

  adminRejectComment: (id) =>
    post(`/admin/comments/${id}/reject`, {}, adminHeader()),

  adminCrawl: () =>
    post('/admin/crawl', {}, adminHeader()),

  adminCrawlOnly: () =>
    post('/admin/crawl-only', {}, adminHeader()),

  adminAnalyzeOne: (news_id) =>
    post(`/admin/analyze-one/${news_id}`, {}, adminHeader()),

  triggerAnalyze: (news_id) =>
    post(`/news/${news_id}/analyze-public`, {}),

  // ── 术语库 ───────────────────────────────────────
  getTerms: (category, level) =>
    cachedRequest(`/terms:${category || ''}:${level || ''}`, '/terms', '/terms', { category, level }),

  getTerm: (slug) =>
    cachedRequest(`/term:${slug}`, '/terms', `/terms/${slug}`, {}),

  getTermsByNews: (news_id) =>
    cachedRequest(`/terms_news:${news_id}`, '/terms', `/terms/news/${news_id}`, {}),

  submitTerm: (body) =>
    post('/terms/submit', body),

  // ── 管理员：术语审核 ──────────────────────────
  adminGetTerms: () =>
    request('/admin/terms', {}, adminHeader()),

  adminApproveTerm: (id) =>
    post(`/admin/terms/${id}/approve`, {}, adminHeader()),

  adminRejectTerm: (id) =>
    post(`/admin/terms/${id}/reject`, {}, adminHeader()),

  // ── 精选内容 ──────────────────────────────────
  getCuratedList: (page = 1, tag, keyword, platform) =>
    request('/curated/list', { page, page_size: 20, ...(tag ? { tag } : {}), ...(keyword ? { keyword } : {}), ...(platform ? { platform } : {}) }),

  getCuratedDetail: (id) =>
    request(`/curated/${id}`),

  submitCurated: (data) =>
    post('/curated/submit', data),

  submitCuratedManual: (data) =>
    post('/curated/submit-manual', data),

  // ── 车手评论 ──────────────────────────────────
  getDriverComments: (code, page = 1) =>
    request(`/driver/${code}/comments`, { page }),

  postDriverComment: (code, openid, content) =>
    post(`/driver/${code}/comments`, { openid, content }),

  likeDriverComment: (id) =>
    post(`/driver/comments/${id}/like`, {}),

  // ── 车手评分 ──────────────────────────────────
  getDriverRating: (code, openid = '') =>
    request(`/driver/${code}/rating`, openid ? { openid } : {}),

  postDriverRating: (code, openid, scores) =>
    post(`/driver/${code}/rating`, { openid, ...scores }),

  triggerCuratedAnalyze: (id, force = false) =>
    post(`/curated/${id}/analyze${force ? '?force=true' : ''}`, {}),

  // ── 术语热度 ──────────────────────────────────
  getTermsHot: () =>
    request('/terms/hot'),

  getTermsPopular: () =>
    request('/terms/popular'),

  getTermsByScene: (scene) =>
    cachedRequest(`/terms:scene:${scene}`, '/terms', '/terms', { scene }),

  // ── 匿名聊天室 ──────────────────────────────────
  getChatMessages: (sinceId) =>
    request('/chat/messages', { since_id: sinceId }),

  sendChatMessage: (nickname, content) =>
    post('/chat/send', { nickname, content }),

  getChatNickname: () =>
    request('/chat/random-nickname'),
}

module.exports = { api }
