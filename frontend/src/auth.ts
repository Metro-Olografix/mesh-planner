/**
 * Zitadel OIDC authentication using the PKCE flow via oidc-client-ts.
 *
 * Call initAuth() once before mounting the app. It fetches /api/config from
 * the backend so no VITE_* build args are needed.
 */
import { UserManager, WebStorageStateStore, type User } from 'oidc-client-ts'

let _userManager: UserManager | null = null

function getUserManager(): UserManager {
  if (!_userManager) throw new Error('Auth not initialized — call initAuth() first.')
  return _userManager
}

export async function initAuth(): Promise<void> {
  const res = await fetch('/api/config')
  if (!res.ok) throw new Error(`Failed to fetch auth config: ${res.status}`)
  const { zitadelAuthority, zitadelClientId } = await res.json()
  _userManager = new UserManager({
    authority: zitadelAuthority,
    client_id: zitadelClientId,
    redirect_uri: `${window.location.origin}/callback`,
    post_logout_redirect_uri: window.location.origin,
    response_type: 'code',
    scope: 'openid profile email',
    loadUserInfo: true,
    userStore: new WebStorageStateStore({ store: window.sessionStorage }),
    extraQueryParams: { audience: zitadelClientId },
  })
}

export async function getUser(): Promise<User | null> {
  return getUserManager().getUser()
}

export async function getAccessToken(): Promise<string | null> {
  const user = await getUserManager().getUser()
  return user?.access_token ?? null
}

export async function login(): Promise<void> {
  await getUserManager().signinRedirect()
}

export async function handleCallback(): Promise<User> {
  return getUserManager().signinRedirectCallback()
}

export async function logout(): Promise<void> {
  await getUserManager().signoutRedirect()
}
