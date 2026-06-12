import { SegmentedControlOption } from './SegmentedControl'

export interface ThemeToggleProps {
  value: string
  onChange?: (value: string) => void
  options?: SegmentedControlOption[]
  label?: string
  className?: string
}

export function ThemeToggle(props: ThemeToggleProps): JSX.Element
