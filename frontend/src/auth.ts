/**
 * Zitadel OIDC authentication using the PKCE flow via oidc-client-ts.
 */
import { UserManager, WebStorageStateStore, type User } from 'oidc-client-ts'

const userManager = new UserManager({
  authority: import.meta.env.VITE_ZITADEL_AUTHORITY,
  client_id: import.meta.env.VITE_ZITADEL_CLIENT_ID,
  redirect_uri: `${window.location.origin}/callback`,
  post_logout_redirect_uri: window.location.origin,
  response_type: 'code',
  scope: 'openid profile email',
  // Fetch the UserInfo endpoint after login so profile claims
  // (preferred_username, name, email) are populated in user.profile.
  // Zitadel does not embed profile claims in the ID token by default.
  loadUserInfo: true,
  userStore: new WebStorageStateStore({ store: window.sessionStorage }),
  // Zitadel requires audience to match client_id
  extraQueryParams: { audience: import.meta.env.VITE_ZITADEL_CLIENT_ID },
})

export async function getUser(): Promise<User | null> {
  return userManager.getUser()
}

export async function getAccessToken(): Promise<string | null> {
  const user = await userManager.getUser()
  return user?.access_token ?? null
}

export async function login(): Promise<void> {
  await userManager.signinRedirect()
}

export async function handleCallback(): Promise<User> {
  return userManager.signinRedirectCallback()
}

export async function logout(): Promise<void> {
  await userManager.signoutRedirect()
}

export { userManager }
