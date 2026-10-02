import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { Contract, Vendor } from "./types";

export function useFetch<T>(path: string | null, params?: Record<string, unknown>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const key = JSON.stringify(params ?? {});
  const reload = useCallback(() => {
    if (!path) return;
    setLoading(true);
    api
      .get<T>(path, JSON.parse(key))
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [path, key]);
  useEffect(reload, [reload]);
  return { data, error, loading, reload, setData };
}

export function useReferenceData() {
  const vendors = useFetch<Vendor[]>("/vendors");
  const contracts = useFetch<Contract[]>("/contracts");
  return { vendors: vendors.data ?? [], contracts: contracts.data ?? [], reloadVendors: vendors.reload };
}
