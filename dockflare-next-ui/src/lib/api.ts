// src/lib/api.ts
import { DockFlareFullOverview } from "./types";

const API_BASE_URL = "/api/v2";

export async function getDockFlareFullOverview(): Promise<DockFlareFullOverview> {
  try {
    const response = await fetch(`${API_BASE_URL}/overview`);

    if (!response.ok) {
      const errorBody = await response.text();
      console.error(`API Error ${response.status}: ${response.statusText}`, errorBody);
      throw new Error(`Failed to fetch DockFlare overview. Status: ${response.status}`);
    }
    const data: DockFlareFullOverview = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching DockFlare overview:", error);
    throw error;
  }
}

export async function deleteManualRuleApi(ruleKey: string): Promise<{ status: string; message: string }> {
  const encodedRuleKey = encodeURIComponent(ruleKey);
  const response = await fetch(`${API_BASE_URL}/rules/manual/${encodedRuleKey}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    let errorMessage = `Failed to delete rule. Status: ${response.status}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.message || errorMessage;
    } catch {
      // Error parsing error response body, use default message
    }
    throw new Error(errorMessage);
  }
  return response.json();
}