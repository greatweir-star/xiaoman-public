import { writeFile, readFile, mkdir } from "fs/promises";
import { dirname } from "path";

export const DATA_DIR = "./data";

async function ensureDir(path: string): Promise<void> {
  try {
    await mkdir(dirname(path), { recursive: true });
  } catch {
    // ignore
  }
}

export async function readJson<T>(path: string): Promise<T | null> {
  try {
    const data = await readFile(`${DATA_DIR}/${path}`, "utf-8");
    return JSON.parse(data) as T;
  } catch {
    return null;
  }
}

export async function writeJson(path: string, data: unknown): Promise<void> {
  const fullPath = `${DATA_DIR}/${path}`;
  await ensureDir(fullPath);
  await writeFile(fullPath, JSON.stringify(data, null, 2), "utf-8");
}

export async function getUserProfile(userId: string): Promise<any> {
  return readJson<any>(`users/${userId}.json`) || {};
}

export async function updateUserProfile(
  userId: string,
  key: string,
  value: string
): Promise<void> {
  const profile = (await readJson<any>(`users/${userId}.json`)) || {};
  profile[key] = { value, updated_at: Date.now() };
  await writeJson(`users/${userId}.json`, profile);
}

export async function updateMemory(
  userId: string,
  namespace: string,
  key: string,
  value: string
): Promise<void> {
  const data = (await readJson<any>(`memory/${userId}/${namespace}.json`)) || {};
  data[key] = { value, updated_at: Date.now() };
  await writeJson(`memory/${userId}/${namespace}.json`, data);
}
