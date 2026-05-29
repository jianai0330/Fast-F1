const app = getApp()

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
  '/terms':       30 * 60 * 1000,
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

function getMemoryCache(key) {
  return app.globalData[key] || null
}

function setMemoryCache(key, data) {
  app.globalData[key] = data
}

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

function post(path, data = {}, headers = {}) {
  const url = app.globalData.BASE_URL + path
  return _doRequest(url, 'POST', data, { 'content-type': 'application/json', ...headers })
    .catch(() => _doRequest(url, 'POST', data, { 'content-type': 'application/json', ...headers }))
}

const ADMIN_TOKEN = 'f1admin2026'
const adminHeader = () => ({ 'X-Admin-Token': ADMIN_TOKEN })

function cachedRequest(cacheKeyStr, ttlKey, path, params = {}) {
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

function cachedCatalogRequest(memoryKey, cacheKeyStr, ttlKey, path, params = {}) {
  const ttl = CACHE_TTL[ttlKey]
  const memoryCached = getMemoryCache(memoryKey)
  if (memoryCached) {
    return Promise.resolve(memoryCached)
  }

  const key = `f1cache:${cacheKeyStr}`
  const storageCached = ttl ? cacheGet(key, ttl) : null
  if (storageCached) {
    setMemoryCache(memoryKey, storageCached)
    request(path, params).then(res => {
      cacheSet(key, res)
      setMemoryCache(memoryKey, res)
    }).catch(() => {})
    return Promise.resolve(storageCached)
  }

  return request(path, params).then(res => {
    if (ttl) cacheSet(key, res)
    setMemoryCache(memoryKey, res)
    return res
  })
}

const api = {
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
      const key = `f1cache:/analysis:${year}:${round_num}:${d1}:${d2}:${session}`
      try { wx.removeStorageSync(key) } catch (e) {}
      return request('/analysis', { year, round_num, d1, d2, session, force: 1 })
    }
    return cachedRequest(`/analysis:${year}:${round_num}:${d1}:${d2}:${session}`, '/analysis', '/analysis', { year, round_num, d1, d2, session })
  },

  getCircuit: (year, round_num) =>
    cachedRequest(`/circuit:${year}:${round_num}`, '/circuit', `/events/${round_num}/circuit`, { year }),

  getNews: (page = 1, team = null, keyword = null, language = 'all') =>
    cachedRequest(`/news:${page}:${team || ''}:${keyword || ''}:${language}`, '/news', '/news',
      { ...(team ? { team } : {}), page, ...(keyword ? { keyword } : {}), language }),

  getNewsDetail: (id) => request(`/news/${id}`),

  getTeamsByNews: (news_id) => request(`/news/${news_id}/teams`),

  getRelatedNews: (news_id, limit = 5) => request(`/news/${news_id}/related`, { limit }),

  getHotPosts: (limit = 5) => request('/hot/posts', { limit }),

  getHotNews: (limit = 3) => request('/hot/news', { limit }),

  registerUser: (code, nickname) => post('/forum/users/register', { code, nickname }),

  updateNickname: (openid, nickname) => post('/forum/users/update-nickname', { openid, nickname }),

  getMe: (openid) => request('/forum/users/me', { openid }),

  getForumSections: () => request('/forum/sections'),

  getForumPosts: (section_id, page = 1, sort = 'latest') =>
    request('/forum/posts', { section_id, page, sort }),

  getForumPost: (id) => request(`/forum/posts/${id}`),

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

  likePost: (post_id, openid, type) => post(`/forum/posts/${post_id}/like`, { openid, type }),

  getLike: (post_id, openid) => request(`/forum/posts/${post_id}/like`, { openid }),

  getNewsPosts: (news_id) => request(`/news/${news_id}/posts`),

  getCuratedPosts: (curated_id) => request(`/curated/${curated_id}/posts`),

  triggerAnalyzePublic: (news_id, force = false) =>
    post(`/news/${news_id}/analyze-public${force ? '?force=true' : ''}`, {}),

  getForumComments: (post_id, openid) =>
    request(`/forum/posts/${post_id}/comments`, { openid }),

  createComment: (post_id, content, openid, parent_id) =>
    post(`/forum/posts/${post_id}/comments`, { content, openid, parent_id }),

  commentLike: (comment_id, openid) =>
    post(`/forum/comments/${comment_id}/like`, { openid }),

  getCommentLike: (comment_id, openid) =>
    request(`/forum/comments/${comment_id}/like`, { openid }),

  adminGetPosts: () => request('/admin/posts', {}, adminHeader()),

  adminApprovePost: (id) => post(`/admin/posts/${id}/approve`, {}, adminHeader()),

  adminRejectPost: (id) => post(`/admin/posts/${id}/reject`, {}, adminHeader()),

  adminGetComments: () => request('/admin/comments', {}, adminHeader()),

  adminApproveComment: (id) => post(`/admin/comments/${id}/approve`, {}, adminHeader()),

  adminRejectComment: (id) => post(`/admin/comments/${id}/reject`, {}, adminHeader()),

  adminCrawl: () => post('/admin/crawl', {}, adminHeader()),

  adminCrawlOnly: () => post('/admin/crawl-only', {}, adminHeader()),

  adminAnalyzeOne: (news_id) => post(`/admin/analyze-one/${news_id}`, {}, adminHeader()),

  triggerAnalyze: (news_id) => post(`/news/${news_id}/analyze-public`, {}),

  getTermsCatalog: () =>
    cachedCatalogRequest('termsCatalog', '/terms::', '/terms', '/terms', {}),

  getTerms: (category, level) =>
    (!category && !level)
      ? api.getTermsCatalog()
      : cachedRequest(`/terms:${category || ''}:${level || ''}`, '/terms', '/terms', { category, level }),

  getTerm: (slug) => cachedRequest(`/term:${slug}`, '/terms', `/terms/${slug}`, {}),

  getTermsByNews: (news_id) => cachedRequest(`/terms_news:${news_id}`, '/terms', `/terms/news/${news_id}`, {}),

  submitTerm: (body) => post('/terms/submit', body),

  adminGetTerms: () => request('/admin/terms', {}, adminHeader()),

  adminApproveTerm: (id) => post(`/admin/terms/${id}/approve`, {}, adminHeader()),

  adminRejectTerm: (id) => post(`/admin/terms/${id}/reject`, {}, adminHeader()),

  getCuratedList: (page = 1, tag, keyword, platform) =>
    request('/curated/list', { page, page_size: 20, ...(tag ? { tag } : {}), ...(keyword ? { keyword } : {}), ...(platform ? { platform } : {}) }),

  getCuratedDetail: (id) => request(`/curated/${id}`),

  submitCurated: (data) => post('/curated/submit', data),

  submitCuratedManual: (data) => post('/curated/submit-manual', data),

  getDriverComments: (code, page = 1) => request(`/driver/${code}/comments`, { page }),

  postDriverComment: (code, openid, content) => post(`/driver/${code}/comments`, { openid, content }),

  likeDriverComment: (id) => post(`/driver/comments/${id}/like`, {}),

  getDriverRating: (code, openid = '') => request(`/driver/${code}/rating`, openid ? { openid } : {}),

  postDriverRating: (code, openid, scores) => post(`/driver/${code}/rating`, { openid, ...scores }),

  triggerCuratedAnalyze: (id, force = false) => post(`/curated/${id}/analyze${force ? '?force=true' : ''}`, {}),

  getTermsHot: () => request('/terms/hot'),

  getTermsPopular: () => request('/terms/popular'),

  getTermsByScene: (scene) => cachedRequest(`/terms:scene:${scene}`, '/terms', '/terms', { scene }),

  getChatMessages: (sinceId) => request('/chat/messages', { since_id: sinceId }),

  sendChatMessage: (nickname, content) => post('/chat/send', { nickname, content }),

  getChatNickname: () => request('/chat/random-nickname'),

  getAnalysisFeedback: (cache_key, openid) =>
    request(`/analysis/feedback/${cache_key}`, { openid }),

  submitAnalysisFeedback: (cache_key, analysis_type, openid, rating) =>
    post('/analysis/feedback', { cache_key, analysis_type, openid, rating }),
}

module.exports = { api }
