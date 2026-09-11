import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { fetchUsage } from "../api/docs";
import { onUsageChanged } from "../api/client";

/**
 * Today's page usage + plan limits for the signed-in user.
 * Re-fetches whenever a conversion is queued (emitUsageChanged).
 */
export function useUsage() {
  const { user } = useAuth();
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!user) { setUsage(null); setLoading(false); return; }
    try { setUsage(await fetchUsage()); }
    catch { /* keep last known value; meter simply stays stale */ }
    finally { setLoading(false); }
  }, [user]);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => onUsageChanged(refresh), [refresh]);

  return { usage, loading, refresh };
}
