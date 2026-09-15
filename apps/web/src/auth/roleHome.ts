import { UserRole } from '../api/authApi'

/** Where a user lands after login/register, or is redirected when they
 * hit a route their role can't use. */
export function roleHomePath(role: UserRole): string {
  switch (role) {
    case 'user':
      return '/ask'
    case 'facilitator':
    case 'regulatory_expert':
      return '/cases'
    case 'admin':
      return '/admin'
    default:
      return '/placeholder'
  }
}
