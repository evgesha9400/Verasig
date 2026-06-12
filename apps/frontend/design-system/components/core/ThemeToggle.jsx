import { Icon } from '../../icons/Icon.jsx'
import { SegmentedControl } from './SegmentedControl.jsx'

const DEFAULT_OPTIONS = [
  { value: 'light', label: 'Light', icon: <Icon name="sun" size={15} /> },
  { value: 'dark', label: 'Dark', icon: <Icon name="moon" size={15} /> }
]

export function ThemeToggle({
  value,
  onChange,
  options = DEFAULT_OPTIONS,
  label = 'Theme',
  className = '',
  ...rest
}) {
  return (
    <SegmentedControl
      className={className}
      label={label}
      value={value}
      onChange={onChange}
      options={options}
      iconOnly
      {...rest}
    />
  )
}
