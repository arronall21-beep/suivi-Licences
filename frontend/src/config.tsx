import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "./api";
import { setCurrency } from "./format";
import { Spinner } from "./components/ui";
import { brand } from "./theme";
import type { AppConfig } from "./types";

interface ConfigCtx {
  config: AppConfig;
  reload: () => Promise<void>;
}

const DEFAULT: AppConfig = {
  org_name: brand.defaultOrganization,
  app_name: brand.defaultApplication,
  currency: "XOF",
  currency_label: "FCFA",
  timezone: "Africa/Porto-Novo",
  critical_days: 30,
  alert_days: 90,
  alert_thresholds: [90, 60, 30, 7],
  version: "",
};

const Ctx = createContext<ConfigCtx>({ config: DEFAULT, reload: async () => {} });

/** Charge la configuration (organisation, devise, seuils) une fois l'utilisateur connecté. */
export function ConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<AppConfig | null>(null);

  const reload = useCallback(async () => {
    try {
      const c = await api.get<AppConfig>("/config");
      setCurrency(c.currency);
      document.title = `${c.app_name} — ${c.org_name}`;
      setConfig(c);
    } catch {
      setConfig(DEFAULT);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  if (!config) return <Spinner />;
  return <Ctx.Provider value={{ config, reload }}>{children}</Ctx.Provider>;
}

export const useConfig = () => useContext(Ctx);
