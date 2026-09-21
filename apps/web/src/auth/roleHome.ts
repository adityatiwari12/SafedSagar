import { UserRole } from '../api/authApi'

/** Where a user lands after login/register, or is redirected when they
 * hit a route their role can't use. */
export function roleHomePath(role: UserRole): string {
  switch (role) {
    case 'user':
    case 'facilitator':
    case 'regulatory_expert':
    case 'admin':
      return '/dashboard'
    default:
      return '/placeholder'
  }
}
