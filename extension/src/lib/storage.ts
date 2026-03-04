/**
 * Chrome storage wrapper for vault state and user preferences.
 *
 * Uses chrome.storage.local for persistence across sessions.
 * NOTE: This does NOT store actual vault secrets — only the
 * `isUnlocked` boolean so the UI knows whether to show the
 * unlock prompt.
 */

const STORAGE_KEYS = {
  VAULT_UNLOCKED: "vault_is_unlocked",
  BACKEND_URL: "backend_url",
  USER_PREFERENCES: "user_preferences",
} as const;

export interface UserPreferences {
  autoInjectContext: boolean;
  showNotifications: boolean;
  defaultQuickAction: string | null;
}

const DEFAULT_PREFERENCES: UserPreferences = {
  autoInjectContext: true,
  showNotifications: true,
  defaultQuickAction: null,
};

/**
 * Get a value from chrome.storage.local.
 */
async function get<T>(key: string): Promise<T | undefined> {
  if (!chrome?.storage?.local) return undefined;
  const result = await chrome.storage.local.get(key);
  return result[key] as T | undefined;
}

/**
 * Set a value in chrome.storage.local.
 */
async function set(key: string, value: unknown): Promise<void> {
  if (!chrome?.storage?.local) return;
  await chrome.storage.local.set({ [key]: value });
}

// -- Vault state ----------------------------------------------------------

export async function getVaultUnlocked(): Promise<boolean> {
  return (await get<boolean>(STORAGE_KEYS.VAULT_UNLOCKED)) ?? false;
}

export async function setVaultUnlocked(unlocked: boolean): Promise<void> {
  await set(STORAGE_KEYS.VAULT_UNLOCKED, unlocked);
}

// -- Backend URL ----------------------------------------------------------

export async function getBackendUrl(): Promise<string> {
  return (await get<string>(STORAGE_KEYS.BACKEND_URL)) ?? "http://localhost:8000";
}

export async function setBackendUrl(url: string): Promise<void> {
  await set(STORAGE_KEYS.BACKEND_URL, url);
}

// -- User preferences -----------------------------------------------------

export async function getUserPreferences(): Promise<UserPreferences> {
  const stored = await get<UserPreferences>(STORAGE_KEYS.USER_PREFERENCES);
  return { ...DEFAULT_PREFERENCES, ...stored };
}

export async function setUserPreferences(
  prefs: Partial<UserPreferences>,
): Promise<void> {
  const current = await getUserPreferences();
  await set(STORAGE_KEYS.USER_PREFERENCES, { ...current, ...prefs });
}
