// src/lib/api.ts
import { 
  DockFlareFullOverview, 
  RuleValue,
  ManualRulePayload, // Assuming this will be defined in types/dockflare.ts
  AccessPolicyPayload // Assuming this will be defined in types/dockflare.ts
} from "./types";

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

export async function forceDeleteRuleApi(ruleKey: string): Promise<{ status: string; message: string; details?: Record<string, unknown> }> {
  const encodedRuleKey = encodeURIComponent(ruleKey);
  const response = await fetch(`${API_BASE_URL}/rules/${encodedRuleKey}/force-delete`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    let errorMessage = `Failed to force delete rule. Status: ${response.status}`;
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

export async function updateAccessPolicyApi(
  ruleKey: string, 
  payload: AccessPolicyPayload
): Promise<{ status: string; message: string; rule?: RuleValue }> {
  const encodedRuleKey = encodeURIComponent(ruleKey);
  const response = await fetch(`${API_BASE_URL}/rules/${encodedRuleKey}/access-policy`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorMessage = `Failed to update access policy. Status: ${response.status}`;
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

export async function revertAccessPolicyApi(
  ruleKey: string
): Promise<{ status: string; message: string; rule?: RuleValue }> {
  const encodedRuleKey = encodeURIComponent(ruleKey);
  const response = await fetch(`${API_BASE_URL}/rules/${encodedRuleKey}/access-policy/revert-to-labels`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    let errorMessage = `Failed to revert access policy. Status: ${response.status}`;
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

export async function addManualRuleApi(
  payload: ManualRulePayload
): Promise<{ status: string; message: string; rule_key?: string; rule?: RuleValue }> {
  const response = await fetch(`${API_BASE_URL}/rules/manual`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorMessage = `Failed to add manual rule. Status: ${response.status}`;
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