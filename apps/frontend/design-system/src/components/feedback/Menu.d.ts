import { ReactElement, ReactNode, ButtonHTMLAttributes, HTMLAttributes } from 'react'

export interface MenuProps extends HTMLAttributes<HTMLDivElement> {
  trigger: ReactElement | ((state: { open: boolean }) => ReactElement)
  label?: string
  align?: 'start' | 'end'
  side?: 'top' | 'bottom'
  children?: ReactNode
}

export interface MenuItemProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  tone?: 'danger'
  iconLeft?: ReactNode
  iconRight?: ReactNode
  children?: ReactNode
}

export function Menu(props: MenuProps): JSX.Element
export function MenuItem(props: MenuItemProps): JSX.Element
export function MenuSeparator(): JSX.Element
