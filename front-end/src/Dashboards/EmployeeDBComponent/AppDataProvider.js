// AppDataProvider.js — shared app/website usage data with auto-refresh
import React, {
  createContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  useRef,
} from "react";
import { api } from "../../api/client";
import {
  endOfWeek,
  format,
  isWithinInterval,
  startOfWeek,
} from "date-fns";
import { useSession } from "../../context/SessionContext";

const AppDataContext = createContext();

/** API sends calendar dates as YYYY-MM-DD; avoid `new Date("2026-04-03")` (UTC) shifting the local day. */
function rowToYmd(row) {
  if (row?.date == null) return "";
  const s = String(row.date);
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  return format(new Date(s), "yyyy-MM-dd");
}

function ymdToLocalNoon(ymd) {
  const p = ymd.split("-").map((x) => parseInt(x, 10));
  if (p.length !== 3 || Number.isNaN(p[0])) return new Date(0);
  return new Date(p[0], p[1] - 1, p[2], 12, 0, 0);
}

export function applyDateFilter(data, dateFilter, startDate, endDate) {
  const now = new Date();
  const todayYmd = format(now, "yyyy-MM-dd");
  const yYesterday = new Date(now);
  yYesterday.setDate(yYesterday.getDate() - 1);
  const yesterdayYmd = format(yYesterday, "yyyy-MM-dd");

  if (dateFilter === "Custom") {
    const a = (startDate || "").slice(0, 10);
    const b = (endDate || "").slice(0, 10);
    return data.filter((row) => {
      const ymd = rowToYmd(row);
      if (!ymd) return false;
      return ymd >= a && ymd <= b;
    });
  }

  return data.filter((row) => {
    const ymd = rowToYmd(row);
    if (!ymd) return false;

    switch (dateFilter) {
      case "Today":
        return ymd === todayYmd;
      case "Yesterday":
        return ymd === yesterdayYmd;
      case "This Week": {
        const d = ymdToLocalNoon(ymd);
        return isWithinInterval(d, {
          start: startOfWeek(now, { weekStartsOn: 0 }),
          end: endOfWeek(now, { weekStartsOn: 0 }),
        });
      }
      default:
        return true;
    }
  });
}

const AppDataProviderInner = ({ children }) => {
  const {
    user,
    authenticated,
    loading: sessionLoading,
    refreshSession,
  } = useSession();
  const today = new Date();
  const [dateFilter, setDateFilter] = useState("Today");
  const [startDate, setStartDate] = useState(format(today, "yyyy-MM-dd"));
  const [endDate, setEndDate] = useState(format(today, "yyyy-MM-dd"));
  const [fetchedData, setFetchedData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const fetchInFlight = useRef(false);

  /** Latest request inputs — avoids putting them in fetchData deps (which retriggered the load effect in a loop). */
  const fetchInputRef = useRef({});
  fetchInputRef.current = {
    dateFilter,
    startDate,
    endDate,
    authenticated,
    userId: user?.id ?? null,
  };

  const fetchData = useCallback(async (opts = {}) => {
    const { silent } = opts;
    const p = fetchInputRef.current;
    if (!p.authenticated || !p.userId) {
      if (!silent) setLoading(false);
      setFetchedData([]);
      return;
    }

    if (fetchInFlight.current) {
      return;
    }
    fetchInFlight.current = true;

    if (!silent) setLoading(true);

    const formData = new FormData();
    if (p.dateFilter === "Custom") {
      formData.append("startDate", p.startDate);
      formData.append("endDate", p.endDate);
    }

    try {
      const response = await api.post("/api/appdata/", formData);
      const rows = Array.isArray(response.data) ? response.data : [];
      setFetchedData(rows);
      setLastUpdated(new Date());
    } catch (error) {
      if (error.response?.status === 401) {
        await refreshSession({ quiet: true });
      }
      console.error("Error fetching data:", error);
    } finally {
      fetchInFlight.current = false;
      if (!silent) setLoading(false);
    }
  }, [refreshSession]);

  /** Manual / explicit refresh (shows loading). No background polling. */
  const refetch = useCallback(() => fetchData({ silent: false }), [fetchData]);

  useEffect(() => {
    if (sessionLoading) return;
    if (!authenticated || !user?.id) {
      setFetchedData([]);
      setLoading(false);
      return;
    }
    fetchData({ silent: false });
  }, [sessionLoading, authenticated, user?.id, fetchData]);

  const handleDateFilterChange = useCallback((event) => {
    setDateFilter(event.target.value);
  }, []);

  const applyDateFilterAction = useCallback(() => {
    fetchData({ silent: false });
  }, [fetchData]);

  useEffect(() => {
    setFilteredData(
      applyDateFilter(fetchedData, dateFilter, startDate, endDate)
    );
  }, [dateFilter, startDate, endDate, fetchedData]);

  const value = useMemo(
    () => ({
      dateFilter,
      setDateFilter,
      startDate,
      setStartDate,
      endDate,
      setEndDate,
      fetchedData,
      filteredData,
      loading,
      lastUpdated,
      handleDateFilterChange,
      applyDateFilter: applyDateFilterAction,
      refetch,
    }),
    [
      dateFilter,
      startDate,
      endDate,
      fetchedData,
      filteredData,
      loading,
      lastUpdated,
      applyDateFilterAction,
      handleDateFilterChange,
      refetch,
    ]
  );

  return (
    <AppDataContext.Provider value={value}>{children}</AppDataContext.Provider>
  );
};

/** Outer shell so AppDataProvider can use useSession (must be inside SessionProvider). */
const AppDataProvider = ({ children }) => {
  return <AppDataProviderInner>{children}</AppDataProviderInner>;
};

export { AppDataProvider, AppDataContext };
