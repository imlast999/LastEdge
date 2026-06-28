import Constants from "expo-constants";

function readEnv(key: "apiUrl" | "apiSecret"): string {
  if (key === "apiUrl") {
    return (
      process.env.EXPO_PUBLIC_API_URL ??
      (Constants.expoConfig?.extra?.apiUrl as string | undefined) ??
      ""
    );
  }
  return (
    process.env.EXPO_PUBLIC_API_SECRET ??
    (Constants.expoConfig?.extra?.apiSecret as string | undefined) ??
    ""
  );
}

export function getApiUrl(): string {
  return readEnv("apiUrl").replace(/\/$/, "");
}

export function getApiSecret(): string {
  return readEnv("apiSecret");
}

export function hasApiSecret(): boolean {
  return getApiSecret().length > 0;
}

export function maskSecret(secret: string): string {
  if (!secret) return "—";
  if (secret.length <= 8) return "••••••••";
  return `${secret.slice(0, 4)}••••${secret.slice(-4)}`;
}

export function getAppVersion(): string {
  return Constants.expoConfig?.version ?? "1.0.0";
}
