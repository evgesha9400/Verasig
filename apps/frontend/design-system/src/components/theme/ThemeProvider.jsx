import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from 'react'

export const THEME_STORAGE_KEY = 'vrs-theme-1'

const THEMES = {
  dark: {
    accent: '#B9EE2E',
    hover: '#CBF457',
    press: '#8FB81E',
    text: '#CBF457',
    quiet: 'rgba(185,238,46,0.12)',
    glow: 'rgba(185,238,46,0.28)',
    verified: '#B9EE2E'
  },
  light: {
    accent: '#5197FF',
    hover: '#82B6FF',
    press: '#2F6FE0',
    text: '#2F6FE0',
    quiet: 'rgba(81,151,255,0.12)',
    glow: 'rgba(81,151,255,0.28)',
    verified: '#5197FF'
  }
}

const ThemeContext = createContext(null)

function readStoredTheme() {
  if (typeof localStorage === 'undefined') return 'dark'
  try {
    const theme = localStorage.getItem(THEME_STORAGE_KEY)
    return theme === 'light' || theme === 'dark' ? theme : 'dark'
  } catch {
    return 'dark'
  }
}

function writeStoredTheme(theme) {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme)
  } catch {
    /* storage can be unavailable in private contexts */
  }
}

function applyTheme(theme) {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  const tokens = THEMES[theme] || THEMES.dark

  root.setAttribute('data-theme', theme)
  root.style.setProperty('--accent', tokens.accent)
  root.style.setProperty('--accent-hover', tokens.hover)
  root.style.setProperty('--accent-press', tokens.press)
  root.style.setProperty('--accent-text', tokens.text)
  root.style.setProperty('--accent-quiet', tokens.quiet)
  root.style.setProperty('--signal-400', tokens.hover)
  root.style.setProperty('--signal-500', tokens.accent)
  root.style.setProperty('--signal-600', tokens.press)
  root.style.setProperty('--signal-glow', tokens.glow)
  root.style.setProperty('--verified-500', tokens.verified)
}

function useStoredThemeState() {
  const [theme, setThemeState] = useState(readStoredTheme)

  const setTheme = useCallback((nextTheme) => {
    if (nextTheme !== 'light' && nextTheme !== 'dark') return
    setThemeState(nextTheme)
  }, [])

  useEffect(() => {
    applyTheme(theme)
    writeStoredTheme(theme)
  }, [theme])

  return useMemo(() => [theme, setTheme], [theme, setTheme])
}

export function ThemeProvider({ initialTheme, children }) {
  const themeState = useStoredThemeState()
  const setTheme = themeState[1]

  useEffect(() => {
    if (!initialTheme) return
    setTheme(initialTheme)
  }, [initialTheme, setTheme])

  return <ThemeContext.Provider value={themeState}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a <ThemeProvider>')
  }
  return context
}
