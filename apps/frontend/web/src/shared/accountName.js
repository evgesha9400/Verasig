const NAME_MAX_LENGTH = 80
const NAME_ALLOWED_CHARACTERS = /^[\p{L} .'-]+$/u

export function normalizeAccountName(value) {
  return (value || '').trim().replace(/\s+/g, ' ')
}

export function validateAccountName(value, label = 'Name') {
  const normalized = normalizeAccountName(value)
  if (!normalized) return `${label} is required.`
  if (!/\p{L}/u.test(normalized)) return `${label} must contain at least one letter.`
  if (normalized.length > NAME_MAX_LENGTH)
    return `${label} must be ${NAME_MAX_LENGTH} characters or fewer.`
  if (!NAME_ALLOWED_CHARACTERS.test(normalized))
    return `${label} may contain only letters, spaces, apostrophes, hyphens, and periods.`
  return null
}

export function splitFullName(fullName) {
  const normalizedFullName = normalizeAccountName(fullName)
  const [firstName, ...lastNameParts] = normalizedFullName.split(' ')
  const lastName = lastNameParts.join(' ')

  if (!normalizedFullName) return { error: 'Full name is required.' }
  if (!lastName) return { error: 'Use first and last name.' }

  const firstError = validateAccountName(firstName, 'First name')
  if (firstError) return { error: firstError }
  const lastError = validateAccountName(lastName, 'Last name')
  if (lastError) return { error: lastError }
  if (firstName.toLowerCase() === lastName.toLowerCase())
    return { error: 'First and last name must be different.' }

  return { firstName, lastName }
}
