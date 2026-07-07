import { useEffect, useRef, useState } from 'react'

const CSS = `
.vrs-otp {
  display: flex;
  gap: 10px;
  justify-content: center;
}
.vrs-otp__input {
  width: 52px;
  height: 62px;
  text-align: center;
  font-family: var(--font-mono);
  font-size: var(--text-2xl);
  color: var(--text-strong);
  background: var(--surface-sunken);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  outline: none;
  transition:
    border-color var(--dur-fast) var(--ease-out),
    box-shadow var(--dur-fast) var(--ease-out),
    background var(--dur-fast) var(--ease-out);
}
.vrs-otp__input:focus-visible {
  border-color: var(--border-focus);
  box-shadow: var(--focus-ring);
  background: var(--surface-card);
}
.vrs-otp__input.is-filled {
  border-color: var(--border-strong);
}
.vrs-otp__input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
`

if (typeof document !== 'undefined' && !document.getElementById('vrs-otp-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-otp-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

function sanitize(raw, inputMode) {
  const text = String(raw || '')
  return inputMode === 'numeric' ? text.replace(/\D/g, '') : text
}

function charsFromValue(value, length, inputMode) {
  const chars = sanitize(value, inputMode).slice(0, length).split('')
  return Array.from({ length }, (_, index) => chars[index] || '')
}

export function OTPInput({
  length = 5,
  value = '',
  onChange,
  disabled = false,
  inputMode = 'numeric',
  className = '',
  ...rest
}) {
  const refs = useRef([])
  // Per-cell values are the source of truth so empty middle cells are never
  // collapsed by round-tripping through a single joined string.
  const [chars, setChars] = useState(() => charsFromValue(value, length, inputMode))

  // Re-seed cells only when the controlled value diverges from what we hold.
  useEffect(() => {
    if (sanitize(value, inputMode) !== chars.join('')) {
      setChars(charsFromValue(value, length, inputMode))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, length, inputMode])

  function emit(nextChars) {
    setChars(nextChars)
    onChange && onChange(nextChars.join(''))
  }

  function focusIndex(index) {
    const next = refs.current[index]
    if (next) next.focus()
  }

  function setDigit(index, rawValue) {
    const digits = sanitize(rawValue, inputMode).split('')
    if (digits.length > 1) {
      const next = [...chars]
      digits.slice(0, length - index).forEach((digit, offset) => {
        next[index + offset] = digit
      })
      emit(next)
      focusIndex(Math.min(index + digits.length, length - 1))
      return
    }

    const next = [...chars]
    next[index] = digits[0] || ''
    emit(next)
    if (digits[0] && index < length - 1) focusIndex(index + 1)
  }

  function onPaste(index, event) {
    const paste = event.clipboardData?.getData('text') || ''
    const pastedDigits = sanitize(paste, inputMode)
      .slice(0, length - index)
      .split('')
    if (pastedDigits.length === 0) return

    event.preventDefault()
    const next = [...chars]
    pastedDigits.forEach((digit, offset) => {
      next[index + offset] = digit
    })
    emit(next)
    focusIndex(Math.min(index + pastedDigits.length, length - 1))
  }

  function onKeyDown(index, event) {
    if (event.key !== 'Backspace' || chars[index]) return
    if (index === 0) return
    event.preventDefault()
    const next = [...chars]
    next[index - 1] = ''
    emit(next)
    focusIndex(index - 1)
  }

  return (
    <div className={['vrs-otp', className].filter(Boolean).join(' ')} {...rest}>
      {chars.map((digit, index) => (
        <input
          key={index}
          ref={(node) => {
            refs.current[index] = node
          }}
          aria-label={`Digit ${index + 1}`}
          className={['vrs-otp__input', digit ? 'is-filled' : '']
            .filter(Boolean)
            .join(' ')}
          disabled={disabled}
          inputMode={inputMode}
          maxLength={1}
          value={digit}
          onChange={(event) => setDigit(index, event.target.value)}
          onKeyDown={(event) => onKeyDown(index, event)}
          onPaste={(event) => onPaste(index, event)}
        />
      ))}
    </div>
  )
}
