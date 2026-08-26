"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";

type RefreshOptions = {
  silent?: boolean;
};

export function useApiQuery<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(path));
  const requestId = useRef(0);

  const refresh = useCallback(async (options: RefreshOptions = {}) => {
    if (!path) {
      setData(null);
      setLoading(false);
      return;
    }
    const currentId = ++requestId.current;
    if (!options.silent) {
      setLoading(true);
    }
    setError(null);
    try {
      const response = await apiRequest<T>(path);
      if (currentId === requestId.current) {
        setData(response);
      }
    } catch (caught) {
      if (currentId === requestId.current) {
        setError(
          caught instanceof ApiError
            ? caught.message
            : "The API request failed."
        );
      }
    } finally {
      if (currentId === requestId.current) {
        setLoading(false);
      }
    }
  }, [path]);

  useEffect(() => {
    void refresh();
    return () => {
      requestId.current += 1;
    };
  }, [refresh]);

  return { data, error, loading, refresh, setData };
}

export function useApiMutation<TResponse, TPayload = unknown>(
  path: string,
  method: "POST" | "PATCH" | "PUT" | "DELETE" = "POST"
) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mutate = useCallback(
    async (payload?: TPayload): Promise<TResponse> => {
      setLoading(true);
      setError(null);
      try {
        return await apiRequest<TResponse>(path, {
          method,
          body: payload === undefined ? undefined : JSON.stringify(payload)
        });
      } catch (caught) {
        const message =
          caught instanceof ApiError
            ? caught.message
            : "The API request failed.";
        setError(message);
        throw caught;
      } finally {
        setLoading(false);
      }
    },
    [method, path]
  );

  return { mutate, loading, error, setError };
}
