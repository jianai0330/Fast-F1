const BASE_URL = 'http://localhost:8000'

App({
  globalData: {
    BASE_URL,
    currentYear: 2026,
  },

  onLaunch() {
    console.log('F1 Data App launched')
  },
})
