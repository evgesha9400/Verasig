import { ReactNode } from 'react'

export const THEME_STORAGE_KEY: 'vrs-theme-1'

export interface ThemeProviderProps {
  initialTheme?: 'light' | 'dark'
  children?: ReactNode
}

export function ThemeProvider(props: ThemeProviderProps): JSX.Element
export function useTheme(): ['light' | 'dark', (theme: 'light' | 'dark') => void]
