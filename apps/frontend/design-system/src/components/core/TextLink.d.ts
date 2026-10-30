import { ReactNode, AnchorHTMLAttributes, ButtonHTMLAttributes } from 'react'

/**
 * Inline text link / link-styled action. Renders <a> when `href` is set, else <button>.
 *
 * @startingPoint section="Core" subtitle="Text link — azure default, accent emphasis" viewport="700x120"
 */
export interface TextLinkProps {
  /** Color role. @default "link" (azure); "accent" for brand-lime emphasis. */
  tone?: 'link' | 'accent'
  /** Render element. Inferred as "a" when `href` is set, otherwise "button". */
  as?: 'a' | 'button'
  /** Destination when rendered as a link. */
  href?: string
  children?: ReactNode
}

export function TextLink(
  props: TextLinkProps &
    Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'href'> &
    ButtonHTMLAttributes<HTMLButtonElement>
): JSX.Element
