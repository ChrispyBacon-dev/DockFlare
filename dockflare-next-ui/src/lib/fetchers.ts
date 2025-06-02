// src/lib/fetchers.ts

// Generic fetcher function for SWR (template maybe need to adjust in the future...)
export const fetcher = async <T = any>(url: string): Promise<T> => {
  const res = await fetch(url);

  if (!res.ok) {
    const error = new Error('An error occurred while fetching the data.');
    
    try {
      const errorData = await res.json();
      // @ts-ignore (custom properties on Error object)
      error.info = errorData;
      // @ts-ignore
      error.status = res.status;
    } catch (e) {
      
    }
    throw error;
  }

  return res.json();
};