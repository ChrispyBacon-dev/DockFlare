// src/lib/fetchers.ts

export const fetcher = async <T = unknown>(url: string): Promise<T> => {
  const res = await fetch(url);

  if (!res.ok) {
    const error = new Error('An error occurred while fetching the data.');
    
    try {
      const errorData = await res.json();
      // @ts-expect-error (custom properties on Error object)
      error.info = errorData;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      error.status = res.status;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (_e) {
      
    }
    throw error;
  }

  return res.json();
};