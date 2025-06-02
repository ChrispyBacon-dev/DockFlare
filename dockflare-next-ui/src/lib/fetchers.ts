// src/lib/fetchers.ts
export const fetcher = async <T = unknown>(url: string): Promise<T> => {
  const res = await fetch(url);

  if (!res.ok) {
    const error = new Error('An error occurred while fetching the data.');
    
    try {
      const errorData = await res.json();
      // @ts-expect-error Custom properties for error info
      error.info = errorData;
      // @ts-expect-error Custom properties for error status
      error.status = res.status;
    } catch {
      // Error parsing error response body
    }
    throw error;
  }

  return res.json();
};