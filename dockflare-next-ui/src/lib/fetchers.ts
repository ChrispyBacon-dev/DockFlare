// src/lib/fetchers.ts

export const fetcher = async <T = unknown>(url: string): Promise<T> => {
  const res = await fetch(url);

  if (!res.ok) {
    const error = new Error('An error occurred while fetching the data.');
    
    try {
      const errorData = await res.json();
      // @ts-expect-error (custom properties on Error object)
      error.info = errorData;
      // @ts-expect-error
      error.status = res.status;
    } catch (_e) {
      
    }
    throw error;
  }

  return res.json();
};