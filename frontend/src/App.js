import React, { useState, useEffect, useMemo, useCallback } from "react";
import "@/App.css";
import axios from "axios";
// Replaced legacy DatePicker with shadcn Calendar
import { 
  Bell, Settings, LayoutDashboard, LogOut, Menu, X, Trash2, 
  AlertTriangle, Database, Mail, Activity, Bike, CheckCircle, 
  XCircle, Clock, MapPin, Info, Moon, Sun, Search, Star, 
  MessageSquare, CheckCircle2, RefreshCw, Loader2, Download, Calendar as CalendarIcon
} from "lucide-react";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import { DateRangePicker } from "@/components/ui/date-range";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

console.log('BACKEND_URL:', BACKEND_URL);
console.log('API URL:', API);

const api = axios.create({
  baseURL: API,
  withCredentials: true
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/auth/refresh')) {
      originalRequest._retry = true;
      
      try {
        await axios.post(`${API}/auth/refresh`, {}, { withCredentials: true });
        return api(originalRequest);
      } catch (refreshError) {
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

const formatUKTimestamp = (dateString) => {
  if (!dateString) return "N/A";
  
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return dateString;
    
    return date.toLocaleString('en-GB', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  } catch {
    return dateString || "N/A";
  }
};

// Helper function to check if alert is within date range
const isAlertInDateRange = (alert, startDate, endDate) => {
  // Prefer backend-created timestamp if available
  const createdAt = alert.created_at || alert.createdAt || alert.createdAtISO;
  const source = createdAt || alert.alert_time;
  if (!source && !startDate && !endDate) return true;
  if (!startDate && !endDate) return true;
  
  try {
    // Get the alert date: use created_at (ISO from backend) when present, otherwise fall back to alert_time
    const alertDate = new Date(source);
    if (isNaN(alertDate.getTime())) return true;
    
    // Convert to date only for comparison
    const alertDateOnly = new Date(alertDate.getFullYear(), alertDate.getMonth(), alertDate.getDate());
    
    if (startDate) {
      const start = new Date(startDate);
      const startDateOnly = new Date(start.getFullYear(), start.getMonth(), start.getDate());
      if (alertDateOnly < startDateOnly) return false;
    }
    
    if (endDate) {
      const end = new Date(endDate);
      const endDateOnly = new Date(end.getFullYear(), end.getMonth(), end.getDate());
      if (alertDateOnly > endDateOnly) return false;
    }
    
    return true;
  } catch {
    return true;
  }
};

// Crash Alert Notification Component
function CrashNotification({ crashAlerts, onDismiss }) {
  if (crashAlerts.length === 0) return null;

  return (
    <div className="fixed top-20 right-6 z-50 space-y-3 max-w-md">
      {crashAlerts.map((crash, index) => (
        <div
          key={index}
          className="bg-red-50 dark:bg-red-900/20 border-2 border-red-500 dark:border-red-700 rounded-lg p-4 shadow-lg animate-pulse"
        >
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-3 flex-1">
              <div className="bg-red-600 rounded-full p-2">
                <AlertTriangle className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-bold text-red-900 dark:text-red-200">
                  🚨 CRASH DETECTED!
                </h3>
                <p className="text-sm font-semibold text-red-800 dark:text-red-300 mt-1">
                  Bike: {crash.device}
                </p>
                <p className="text-xs text-red-700 dark:text-red-400 mt-1">
                  {formatUKTimestamp(crash.timestamp)}
                </p>
                <p className="text-xs text-red-600 dark:text-red-500 mt-2">
                  Heavy Impact + Over-turn detected
                </p>
              </div>
            </div>
            <button
              onClick={() => onDismiss(crash.device)}
              className="ml-2 text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

function LoginPage({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const endpoint = isRegister ? "/auth/register" : "/auth/login";
      const payload = isRegister ? { username, email, password } : { username, password };
      
      console.log("Login request:", endpoint, payload);
      const response = await api.post(endpoint, payload);
      console.log("Login response:", response.data);
      
      if (response.data.user) {
        console.log("Calling onLogin with:", response.data.user);
        onLogin(response.data.user);
      } else {
        console.error("No user in response:", response.data);
        setError("Login response missing user data");
      }
    } catch (err) {
      console.error("Login error:", err);
      setError(err.response?.data?.detail || (isRegister ? "Registration failed" : "Login failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-8">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 mb-4">
              <Bike className="w-16 h-16 text-gray-900 dark:text-white" strokeWidth={1.5} />
            </div>
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-2">Tracker Alerts System</h1>
            <p className="text-sm text-gray-600 dark:text-gray-300">{isRegister ? "Create your account" : "Sign in to access the dashboard"}</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-1 focus:ring-gray-900 focus:border-gray-900 outline-none text-sm"
                placeholder="Enter username"
                required
              />
            </div>

            {isRegister && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-1 focus:ring-gray-900 focus:border-gray-900 outline-none text-sm"
                  placeholder="Enter email"
                  required
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-1 focus:ring-gray-900 focus:border-gray-900 outline-none text-sm"
                placeholder="Enter password"
                required
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-md text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gray-900 text-white py-2.5 rounded-md font-medium hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            >
              {loading ? (isRegister ? "Creating account..." : "Signing in...") : (isRegister ? "Create Account" : "Sign in")}
            </button>

            <div className="text-center mt-4">
              <button
                type="button"
                onClick={() => {
                  setIsRegister(!isRegister);
                  setError("");
                }}
                className="text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:text-white transition"
              >
                {isRegister ? "Already have an account? Sign in" : "Need an account? Register"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

function Dashboard({ user, onLogout }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [currentPage, setCurrentPage] = useState("dashboard");
  const [alerts, setAlerts] = useState([]);
  const [groupedAlerts, setGroupedAlerts] = useState([]);
  const [crashAlerts, setCrashAlerts] = useState([]); // Store crash detected alerts
  const [stats, setStats] = useState({
    total: 0,
    unread: 0,
    highPriority: 0,
    acknowledged: 0,
    categories: {}
  });
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncProgress, setSyncProgress] = useState({ total: 0, processed: 0, remaining: 0 });
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [showModal, setShowModal] = useState(false);
  
  // New: Bike history modal states
  const [selectedBike, setSelectedBike] = useState(null);
  const [showBikeHistoryModal, setShowBikeHistoryModal] = useState(false);
  const [bikeHistory, setBikeHistory] = useState({ alerts: [], notes: [] });
  const [loadingHistory, setLoadingHistory] = useState(false);

  const [gmailEmail, setGmailEmail] = useState("");
  const [gmailPassword, setGmailPassword] = useState("");
  const [gmailConnected, setGmailConnected] = useState(false);
  const [syncInterval, setSyncInterval] = useState(10);
  const [emailLimit, setEmailLimit] = useState(100);


  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [darkMode, setDarkMode] = useState(() => {
    // Initialize dark mode from localStorage
    return localStorage.getItem('darkMode') === 'true';
  });
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("priority");
  const [filterDate, setFilterDate] = useState("");
  const [bikesDisplayLimit, setBikesDisplayLimit] = useState(6);
  const [showAllBikes, setShowAllBikes] = useState(false);
  const [selectedSyncDate, setSelectedSyncDate] = useState(null);
  const [startDateInput, setStartDateInput] = useState("");
  const [endDateInput, setEndDateInput] = useState("");
  const [dateRange, setDateRange] = useState({ from: undefined, to: undefined });
  const [appliedStartDate, setAppliedStartDate] = useState("");
  const [appliedEndDate, setAppliedEndDate] = useState("");
  
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(5000); // Fetch all alerts per page to include the full dataset
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false); // deprecated; no longer used since we show all alerts
  const [pagination, setPagination] = useState({
    page: 1,
    limit: limit,
    total: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false
  });

  const [bikes, setBikes] = useState([]);
  const [loadingBikes, setLoadingBikes] = useState(false);
  const [bikeSearchQuery, setBikeSearchQuery] = useState("");
  const [selectedBikeId, setSelectedBikeId] = useState(null);

  useEffect(() => {
    loadAlerts();
    loadCategories();
    const savedDarkMode = localStorage.getItem("darkMode") === "true";
    setDarkMode(savedDarkMode);
    if (savedDarkMode) {
      document.documentElement.classList.add("dark");
    }
  }, []);

  useEffect(() => {
    // Reset to page 1 and reload when category or date filter changes
    setPage(1);
    if (selectedCategory !== "All") {
      loadAlerts(selectedCategory, 1, false);
    } else {
      loadAlerts(null, 1, false);
    }
  }, [selectedCategory, appliedStartDate, appliedEndDate]);

  useEffect(() => {
    if (alerts.length > 0) {
      groupAlertsByDevice(alerts);
    }
  }, [sortBy]);

  const loadCategories = async () => {
    try {
      const response = await api.get("/alerts/categories");
      setCategories(["All", ...response.data.categories]);
    } catch (error) {
      console.error("Failed to load categories:", error);
    }
  };

  const loadStatsOnly = async (category = null) => {
    try {
      const params = new URLSearchParams();
      if (category && category !== "All") {
        params.append('category', category);
      }
      
      const url = `/alerts/stats-only?${params.toString()}`;
      const response = await api.get(url);
      
      setStats(response.data.stats);
    } catch (error) {
      console.error("Failed to load stats:", error);
    }
  };

  const loadAlertsQuiet = async (category = null) => {
    try {
      // Silent refresh: updates alerts without showing loading spinner
      const params = new URLSearchParams();
      if (category && category !== "All") {
        params.append('category', category);
      }
      params.append('page', 1);
      params.append('limit', limit);
      
      // Date filtering will be done in frontend
      
      const url = `/alerts/list?${params.toString()}`;
      const response = await api.get(url);
      
      setAlerts(response.data.alerts);
      // Stats will be calculated in groupAlertsByDevice based on filtered data
      setGmailConnected(response.data.connected);
      setGmailEmail(response.data.email || "");
      setHasMore(false);
      setPagination(response.data.pagination || {
        page: 1,
        limit: limit,
        total: response.data.alerts?.length || 0,
        total_pages: 1,
        has_next: false,
        has_prev: false
      });
      setPage(1); // Reset page to 1 since we always show all
      
      groupAlertsByDevice(response.data.alerts);
    } catch (error) {
      console.error("Failed to quiet refresh alerts:", error);
    }
  };

  const handleApplyDateFilter = () => {
    setAppliedStartDate(startDateInput);
    setAppliedEndDate(endDateInput);
    setPage(1);
  };
  
  const handleClearDateFilter = () => {
    setStartDateInput("");
    setEndDateInput("");
    setAppliedStartDate("");
    setAppliedEndDate("");
    setPage(1);
  };
  const loadAlerts = async (category = null, pageNum = page, append = false) => {
    try {
      if (!append) {
        setLoading(true);
      }
      
      const params = new URLSearchParams();
      if (category && category !== "All") {
        params.append('category', category);
      }
      params.append('page', pageNum);
      params.append('limit', limit);
      
      // Date filtering will be done in frontend
      
      const url = `/alerts/list?${params.toString()}`;
      
      const response = await api.get(url);
      
      if (append) {
        setAlerts(prev => [...prev, ...response.data.alerts]);
      } else {
        setAlerts(response.data.alerts);
      }
      
      // Stats will be calculated in groupAlertsByDevice based on filtered data
      setGmailConnected(response.data.connected);
      setGmailEmail(response.data.email || "");
      setHasMore(false);
      setPagination({
        page: 1,
        limit: limit,
        total: append ? (alerts.length + response.data.alerts.length) : (response.data.alerts?.length || 0),
        total_pages: 1,
        has_next: false,
        has_prev: false
      });
      
      if (!append) {
        groupAlertsByDevice(response.data.alerts);
      } else {
        // Re-group with all alerts when appending
        groupAlertsByDevice([...alerts, ...response.data.alerts]);
      }
      
      return true; // Success indicator
    } catch (error) {
      console.error("Failed to load alerts:", error);
      return false; // Failure indicator
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };
  
  // Deprecated: We now fetch all alerts at once and do not paginate on the client
  const loadMoreAlerts = async () => {
    return;
  };

  const groupAlertsByDevice = (alertList) => {
    const grouped = {};
    
    // Filter alerts by date range if applied (FRONTEND FILTERING)
    const filteredAlerts = alertList.filter(alert => 
      isAlertInDateRange(alert, appliedStartDate, appliedEndDate)
    );
    
    filteredAlerts.forEach(alert => {
      const device = alert.tracker_name || "Unknown";
      if (!grouped[device]) {
        grouped[device] = {
          device: device,
          alerts: [],
          count: 0,
          latestAlert: alert,
          severity: "normal"
        };
      }
      grouped[device].alerts.push(alert);
      grouped[device].count++;
      
      // Update latestAlert to the most recent one
      if (new Date(alert.alert_time) > new Date(grouped[device].latestAlert.alert_time)) {
        grouped[device].latestAlert = alert;
      }
    });

    // Detect crash alerts and store them
    const crashDetected = [];
    
    Object.values(grouped).forEach(group => {
      const alertTypes = group.alerts.map(a => a.alert_type);
      
      // Count specific alert types
      const overTurnCount = alertTypes.filter(t => t === "Over-turn").length;
      const heavyImpactCount = alertTypes.filter(t => t === "Heavy Impact").length;
      
      // Crash detect ONLY when: 1 Over-turn + 1 Heavy Impact (not 2 Over-turn)
      const isCrashDetect = overTurnCount >= 1 && heavyImpactCount >= 1;
      
      if (isCrashDetect) {
        group.severity = "crash-detected";
        group.displayName = "Crash Detected";
        crashDetected.push({
          device: group.device,
          timestamp: group.latestAlert.created_at
        });
      } else if (overTurnCount > 0 || heavyImpactCount > 0) {
        group.severity = "high";
      } else {
        group.severity = "normal";
      }
    });
    
    // Update crash alerts if there are new ones
    if (crashDetected.length > 0) {
      setCrashAlerts(prev => {
        const existing = new Set(prev.map(a => a.device));
        const newCrashes = crashDetected.filter(c => !existing.has(c.device));
        return [...prev, ...newCrashes];
      });
    }

    const groupedArray = Object.values(grouped);
    
    // Apply sorting based on sortBy
    const sorted = groupedArray.sort((a, b) => {
      switch(sortBy) {
        case "priority":
          if ((a.severity === "crash-detected" || a.severity === "heavy-impact") && (b.severity !== "crash-detected" && b.severity !== "heavy-impact")) return -1;
          if ((b.severity === "crash-detected" || b.severity === "heavy-impact") && (a.severity !== "crash-detected" && a.severity !== "heavy-impact")) return 1;
          if (a.severity === "high" && b.severity === "normal") return -1;
          if (b.severity === "high" && a.severity === "normal") return 1;
          return b.count - a.count;
        
        case "newest":
          return new Date(b.latestAlert.alert_time) - new Date(a.latestAlert.alert_time);
        
        case "oldest":
          return new Date(a.latestAlert.alert_time) - new Date(b.latestAlert.alert_time);
        
        case "device":
          return a.device.localeCompare(b.device);
        
        case "alerts":
          return b.count - a.count;
        
        default:
          return 0;
      }
    });

    // Calculate stats based on filtered alerts
    const totalAlerts = filteredAlerts.length;
    const overTurnCount = filteredAlerts.filter(a => a.alert_type === "Over-turn").length;
    const heavyImpactCount = filteredAlerts.filter(a => a.alert_type === "Heavy Impact").length;
    const noCommunicationCount = filteredAlerts.filter(a => a.alert_type === "No Communication").length;
    const crashDetectedCount = groupedArray.filter(g => g.severity === "crash-detected").length;
    const highPriorityCount = overTurnCount + heavyImpactCount;
    
    // Update stats with filtered data
    setStats(prevStats => ({
      ...prevStats,
      total: totalAlerts,
      highPriority: highPriorityCount,
      overTurn: overTurnCount,
      heavyImpact: heavyImpactCount,
      noCommunication: noCommunicationCount,
      crashDetected: crashDetectedCount
    }));

    setGroupedAlerts(sorted);
  };

  const handleRefreshAlerts = async () => {
    setSyncing(true);
    try {
      // Trigger manual email sync first
      await api.post("/sync/manual");
      
      // Always refresh from page 1 to reset lazy loading state
      setPage(1);
      await loadAlerts(selectedCategory !== "All" ? selectedCategory : null, 1, false);
    } catch (error) {
      console.error("Failed to refresh alerts:", error);
    } finally {
      setSyncing(false);
    }
  };

  const handleSyncTodayEmails = async () => {
    setSyncing(true);
    setSyncProgress({ total: 0, processed: 0, remaining: 0 });
    
    try {
      let completed = false;
      let totalEmails = 0;
      
      while (!completed) {
        const response = await api.post("/sync/progressive");
        const data = response.data;
        
        totalEmails = data.total;
        setSyncProgress({
          total: data.total,
          processed: data.processed,
          remaining: data.remaining
        });
        
        completed = data.completed;
        
        // Small delay to prevent overwhelming the server
        if (!completed) {
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      }
      
      alert(`Sync completed! ${totalEmails} total emails checked`);
      
      // Refresh alerts list
      setPage(1);
      await loadAlerts(selectedCategory !== "All" ? selectedCategory : null, 1, false);
    } catch (error) {
      console.error("Failed to sync emails:", error);
      alert(error.response?.data?.detail || "Failed to sync emails");
    } finally {
      setSyncing(false);
      setSyncProgress({ total: 0, processed: 0, remaining: 0 });
    }
  };

  const handleConnectGmail = async (e) => {
    e.preventDefault();
    try {
      await api.post("/gmail/connect", {
        email: gmailEmail,
        app_password: gmailPassword
      });
      setGmailConnected(true);
      alert("Gmail connected successfully!");
    } catch (error) {
      alert(error.response?.data?.detail || "Failed to connect Gmail");
    }
  };

  const handleDeleteAlert = async (alertId) => {
    if (!window.confirm("Delete this alert?")) return;
    try {
      await api.delete(`/alerts/${alertId}`);
      await loadAlerts();
    } catch (error) {
      alert("Failed to delete alert");
    }
  };

  const handleAcknowledgeAlert = async (alertId) => {
    try {
      await api.post(`/alerts/${alertId}/acknowledge`, {
        acknowledged_by: user?.username || 'User'
      });
      await loadAlerts();
      setShowModal(false);
    } catch (error) {
      console.error("Failed to acknowledge alert:", error);
      alert("Failed to acknowledge alert");
    }
  };

  const handleClearHistory = async () => {
    if (!window.confirm("⚠️ Clear ALL history?\n\nThis will:\n- Delete all alerts\n- Reset sync checkpoint\n- Start from scratch\n\nThis cannot be undone!")) return;
    
    try {
      await api.delete("/alerts/clear-all/history");
      await loadAlerts();
      alert("✓ History cleared successfully! System reset.");
    } catch (error) {
      alert("Error clearing history");
    }
  };

  const handleExportCSV = async () => {
    try {
      const params = new URLSearchParams();
      if (selectedCategory && selectedCategory !== "All") {
        params.append('category', selectedCategory);
      }
      
      // Add date filter for export
      if (appliedStartDate) {
        params.append('start_date', appliedStartDate);
      }
      if (appliedEndDate) {
        params.append('end_date', appliedEndDate);
      }
      
      const url = `/alerts/export?${params.toString()}`;
      const response = await api.get(url, { responseType: 'blob' });
      
      // Create download link
      const blob = new Blob([response.data], { type: 'text/csv' });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `alerts_export_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error("Failed to export CSV:", error);
      alert("Failed to export alerts");
    }
  };

  const openAlertModal = (group) => {
    setSelectedAlert(group);
    setShowModal(true);
  };

  const dismissCrashAlert = (device) => {
    setCrashAlerts(prev => prev.filter(c => c.device !== device));
  };

  const Sidebar = () => (
    <div className={`${sidebarOpen ? 'w-64' : 'w-0'} bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 dark:border-gray-700 transition-all duration-300 overflow-hidden flex flex-col h-screen`}>
      <div className="p-6 flex-1">
        <div className="flex items-center space-x-3 mb-8">
          <Bike className="w-6 h-6 text-gray-900 dark:text-white dark:text-white" />
          <div>
            <span className="text-sm font-semibold text-gray-900 dark:text-white dark:text-white">Tracker System</span>
            <p className="text-xs text-gray-500 dark:text-gray-400 dark:text-gray-400">Dashboard</p>
          </div>
        </div>

        <nav className="space-y-1">
          <button
            onClick={() => setCurrentPage("dashboard")}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md text-sm transition ${
              currentPage === "dashboard"
                ? "bg-gray-900 text-white dark:bg-gray-700"
                : "text-gray-700 dark:text-gray-300 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-700"
            }`}
          >
            <LayoutDashboard className="w-4 h-4" />
            <span className="font-medium">Bike Tracker</span>
          </button>

          <button
            onClick={() => setCurrentPage("bikes")}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md text-sm transition ${
              currentPage === "bikes"
                ? "bg-gray-900 text-white dark:bg-gray-700"
                : "text-gray-700 dark:text-gray-300 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-700"
            }`}
          >
            <Bike className="w-4 h-4" />
            <span className="font-medium">Bikes</span>
          </button>

          {user && user.role === 'admin' && (
            <>
              <button
                onClick={() => setCurrentPage("admin")}
                className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md text-sm transition ${
                  currentPage === "admin"
                    ? "bg-gray-900 text-white dark:bg-gray-700"
                    : "text-gray-700 dark:text-gray-300 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-700"
                }`}
              >
                <Activity className="w-4 h-4" />
                <span className="font-medium">Admin Dashboard</span>
              </button>

              <button
                onClick={() => setCurrentPage("settings")}
                className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md text-sm transition ${
                  currentPage === "settings"
                    ? "bg-gray-900 text-white dark:bg-gray-700"
                    : "text-gray-700 dark:text-gray-300 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-700"
                }`}
              >
                <Settings className="w-4 h-4" />
                <span className="font-medium">Service Tracker</span>
              </button>
            </>
          )}
        </nav>
      </div>

      <div className="p-6 border-t border-gray-200 dark:border-gray-700 dark:border-gray-700 space-y-3">
        <button
          onClick={toggleDarkMode}
          className="w-full flex items-center space-x-3 px-3 py-2 rounded-md text-sm text-gray-700 dark:text-gray-300 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-700 transition"
          title={darkMode ? "Light mode" : "Dark mode"}
        >
          {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          <span className="font-medium">{darkMode ? "Light Mode" : "Dark Mode"}</span>
        </button>
        
        <button
          onClick={onLogout}
          className="w-full flex items-center space-x-3 px-3 py-2 rounded-md text-sm text-red-600 hover:bg-red-50 transition"
        >
          <LogOut className="w-4 h-4" />
          <span className="font-medium">Logout</span>
        </button>
      </div>
    </div>
  );

  const toggleDarkMode = () => {
    const newMode = !darkMode;
    setDarkMode(newMode);
    localStorage.setItem("darkMode", newMode);
    if (newMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  };
  
  // Apply dark mode on mount
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [darkMode]);
  
  // Function to open bike history modal
  const openBikeHistory = async (bikeId, trackerName) => {
    setSelectedBike({ id: bikeId, tracker_name: trackerName });
    setShowBikeHistoryModal(true);
    setLoadingHistory(true);
    
    try {
      const response = await api.get(`/bikes/${bikeId}/history`);
      setBikeHistory({
        alerts: response.data.alerts || [],
        notes: response.data.notes || []
      });
    } catch (error) {
      console.error("Failed to load bike history:", error);
      setBikeHistory({ alerts: [], notes: [] });
    } finally {
      setLoadingHistory(false);
    }
  };

  const Header = () => {
    const isAdmin = user && user.username === 'admin';
    
    return (
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 dark:border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-700 rounded transition"
            >
              {sidebarOpen ? <X className="w-5 h-5 text-gray-900 dark:text-white dark:text-white" /> : <Menu className="w-5 h-5 text-gray-900 dark:text-white dark:text-white" />}
            </button>
            <div>
              <h1 className="text-xl font-semibold text-gray-900 dark:text-white dark:text-white">
                {currentPage === "dashboard" && "Bike Tracker Dashboard"}
                {currentPage === "admin" && "System Dashboard"}
                {currentPage === "settings" && "Settings"}
              </h1>
              <p className="text-xs text-gray-500 dark:text-gray-400 dark:text-gray-400">
                {currentPage === "dashboard" && "Monitor your bike trackers and alerts by category"}
                {currentPage === "admin" && "Monitor system health and logs"}
                {currentPage === "settings" && "Configure Gmail integration"}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleSyncTodayEmails}
              disabled={syncing}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 dark:bg-blue-700 text-white rounded-md hover:bg-blue-700 dark:hover:bg-blue-600 transition disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            >
              <Download className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
              <span>
                {syncing && syncProgress.total > 0 
                  ? `Syncing: ${syncProgress.processed}/${syncProgress.total}` 
                  : 'Sync Emails'}
              </span>
            </button>
          </div>
        </div>
      </header>
    );
  };

  const loadBikes = useCallback(async () => {
    try {
      setLoadingBikes(true);
      const response = await api.get("/bikes/list");
      setBikes(response.data.bikes || []);
    } catch (error) {
      console.error("Failed to load bikes:", error);
    } finally {
      setLoadingBikes(false);
    }
  }, []);

  // Load bikes when navigating to bikes page
  useEffect(() => {
    if (currentPage === "bikes") {
      loadBikes();
    }
  }, [currentPage, loadBikes]);

  const BikesPage = () => {

    if (loadingBikes) {
      return (
        <div className="flex items-center justify-center h-full">
          <Loader2 className="w-8 h-8 animate-spin text-gray-600 dark:text-gray-300" />
        </div>
      );
    }

    const filteredBikes = bikes.filter(bike => 
      !bikeSearchQuery || 
      bike.tracker_name.toLowerCase().includes(bikeSearchQuery.toLowerCase()) ||
      (bike.device_serial && bike.device_serial.toLowerCase().includes(bikeSearchQuery.toLowerCase()))
    );

    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Bikes</h1>
            <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">View and manage your tracked bikes</p>
          </div>
        </div>

        {bikes.length > 0 && (
          <Card><CardContent className="p-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search by bike name or serial..."
                value={bikeSearchQuery}
                onChange={(e) => setBikeSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-gray-900 focus:border-transparent"
              />
            </div>
          </CardContent></Card>
        )}

        {filteredBikes.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-12 text-center">
            <Bike className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-300">
              {bikes.length === 0 
                ? "No bikes found. Bikes will appear here once you have tracker alerts."
                : "No bikes match your search."}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredBikes.map((bike) => (
              <div
                key={bike.id}
                onClick={() => openBikeHistory(bike.id, bike.tracker_name)}
                className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:border-gray-400 cursor-pointer transition"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="p-3 bg-gray-900 rounded-lg">
                    <Bike className="w-6 h-6 text-white" />
                  </div>
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                    {bike.alert_count} alerts
                  </span>
                </div>
                
                <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">{bike.tracker_name}</h3>
                
                {bike.device_serial && (
                  <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">Serial: {bike.device_serial}</p>
                )}
                
                {bike.latest_alert_at && (
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Last alert: {formatUKTimestamp(bike.latest_alert_at)}
                  </p>
                )}
                
                {bike.notes_count > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <span className="text-xs text-gray-600 dark:text-gray-300">
                      {bike.notes_count} note{bike.notes_count !== 1 ? 's' : ''}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  // Bike History Modal Component
  const BikeHistoryModal = () => {
    const [newNote, setNewNote] = useState("");
    const [addingNote, setAddingNote] = useState(false);
    const [editingNoteId, setEditingNoteId] = useState(null);
    const [editNoteText, setEditNoteText] = useState("");
    
    if (!showBikeHistoryModal || !selectedBike) return null;

    const handleAddNote = async () => {
      if (!newNote.trim()) return;
      
      setAddingNote(true);
      try {
        await api.post(`/bikes/${selectedBike.id}/notes`, { note: newNote });
        setNewNote("");
        // Reload history
        const response = await api.get(`/bikes/${selectedBike.id}/history`);
        setBikeHistory({
          alerts: response.data.alerts || [],
          notes: response.data.notes || []
        });
      } catch (error) {
        console.error("Failed to add note:", error);
        alert("Failed to add note");
      } finally {
        setAddingNote(false);
      }
    };
    
    const handleEditNote = async (noteId) => {
      if (!editNoteText.trim()) return;
      
      try {
        await api.put(`/bikes/notes/${noteId}`, { note: editNoteText });
        setEditingNoteId(null);
        setEditNoteText("");
        // Reload history
        const response = await api.get(`/bikes/${selectedBike.id}/history`);
        setBikeHistory({
          alerts: response.data.alerts || [],
          notes: response.data.notes || []
        });
      } catch (error) {
        console.error("Failed to edit note:", error);
        alert("Failed to edit note");
      }
    };
    
    const handleDeleteNote = async (noteId) => {
      if (!window.confirm("Are you sure you want to delete this note?")) return;
      
      try {
        await api.delete(`/bikes/notes/${noteId}`);
        // Reload history
        const response = await api.get(`/bikes/${selectedBike.id}/history`);
        setBikeHistory({
          alerts: response.data.alerts || [],
          notes: response.data.notes || []
        });
      } catch (error) {
        console.error("Failed to delete note:", error);
        alert("Failed to delete note");
      }
    };
    
    // Sort alerts by created_at DESC (newest first)
    const sortedAlerts = [...(bikeHistory.alerts || [])].sort((a, b) => 
      new Date(b.created_at) - new Date(a.created_at)
    );
    
    // Sort notes by created_at DESC (newest first)
    const sortedNotes = [...(bikeHistory.notes || [])].sort((a, b) => 
      new Date(b.created_at) - new Date(a.created_at)
    );

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                {selectedBike.tracker_name}
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Alert History (Newest First)</p>
            </div>
            <button
              onClick={() => {
                setShowBikeHistoryModal(false);
                setSelectedBike(null);
                setBikeHistory({ alerts: [], notes: [] });
              }}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
            >
              <X className="w-6 h-6 text-gray-600 dark:text-gray-400" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            {loadingHistory ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
              </div>
            ) : (
              <div className="space-y-6">
                {/* Add Note Section */}
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Add Note</h3>
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      value={newNote}
                      onChange={(e) => setNewNote(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleAddNote()}
                      placeholder="Type your note here..."
                      className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      disabled={addingNote}
                    />
                    <button
                      onClick={handleAddNote}
                      disabled={addingNote || !newNote.trim()}
                      className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                    >
                      {addingNote ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Add'}
                    </button>
                  </div>
                </div>
                
                {/* Notes Section - FIRST */}
                {sortedNotes && sortedNotes.length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                      Notes ({sortedNotes.length})
                    </h3>
                    <div className="space-y-2">
                      {sortedNotes.map((note, index) => (
                        <div
                          key={note.id || index}
                          className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-3 border border-yellow-200 dark:border-yellow-800"
                        >
                          {editingNoteId === note.id ? (
                            <div className="space-y-2">
                              <input
                                type="text"
                                value={editNoteText}
                                onChange={(e) => setEditNoteText(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                              />
                              <div className="flex space-x-2">
                                <button
                                  onClick={() => handleEditNote(note.id)}
                                  className="px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700"
                                >
                                  Save
                                </button>
                                <button
                                  onClick={() => {
                                    setEditingNoteId(null);
                                    setEditNoteText("");
                                  }}
                                  className="px-3 py-1 bg-gray-300 text-gray-700 rounded text-xs hover:bg-gray-400"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          ) : (
                            <>
                              <p className="text-sm text-gray-700 dark:text-gray-300">{note.note}</p>
                              <div className="flex items-center justify-between mt-2">
                                <div className="text-xs text-gray-500 dark:text-gray-400">
                                  <span className="font-medium">By: {note.created_by || user?.username || 'Unknown'}</span>
                                  <span className="mx-2">•</span>
                                  <span>{formatUKTimestamp(note.created_at)}</span>
                                </div>
                                <div className="flex space-x-2">
                                  <button
                                    onClick={() => {
                                      setEditingNoteId(note.id);
                                      setEditNoteText(note.note);
                                    }}
                                    className="text-blue-600 hover:text-blue-800 text-xs"
                                  >
                                    Edit
                                  </button>
                                  <button
                                    onClick={() => handleDeleteNote(note.id)}
                                    className="text-red-600 hover:text-red-800 text-xs"
                                  >
                                    Delete
                                  </button>
                                </div>
                              </div>
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Alerts Section - SECOND */}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                    Recent Alerts ({sortedAlerts.length})
                  </h3>
                  
                  {sortedAlerts.length === 0 ? (
                    <p className="text-gray-500 dark:text-gray-400 text-center py-8">No alerts found</p>
                  ) : (
                    <div className="space-y-3">
                      {sortedAlerts.map((alert, index) => (
                        <div
                          key={index}
                          className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                              {alert.alert_type}
                            </span>
                            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                              {formatUKTimestamp(alert.created_at)}
                            </span>
                          </div>
                          
                          {alert.alert_time && (
                            <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                              Alert Time: {alert.alert_time}
                            </div>
                          )}
                          
                          {alert.location && (
                            <div className="flex items-start space-x-2 text-sm text-gray-600 dark:text-gray-300">
                              <MapPin className="w-4 h-4 mt-0.5 flex-shrink-0" />
                              <span>{alert.location}</span>
                            </div>
                          )}
                          
                          {alert.notes && (
                            <div className="mt-2 text-sm text-gray-600 dark:text-gray-300 bg-yellow-50 dark:bg-yellow-900/20 p-2 rounded">
                              <strong>Notes:</strong> {alert.notes}
                            </div>
                          )}
                          
                          <div className="mt-2 flex items-center space-x-2">
                            <span className={`text-xs px-2 py-1 rounded ${
                              alert.acknowledged 
                                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                                : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                            }`}>
                              {alert.acknowledged ? '✓ Acknowledged' : 'Pending'}
                            </span>
                            {alert.status && (
                              <span className="text-xs text-gray-500 dark:text-gray-400">
                                Status: {alert.status}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const DashboardPage = () => {
    const getSeverityBadge = (severity) => {
      if (severity === "crash-detected" || severity === "heavy-impact") return "bg-red-100 text-red-700 border-red-200";
      if (severity === "high") return "bg-orange-100 text-orange-700 border-orange-200";
      return "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-700";
    };

    const getCountBadge = (count) => {
      if (count >= 100) return "99+";
      return count.toString();
    };

    const getTimeAgo = (dateString) => {
      if (!dateString) return "Never";
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);
      
      if (diffMins < 1) return "Just now";
      if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
      if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
      return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    };

    return (
      <div className="p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card><CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600 dark:text-gray-300">Total Alerts</p>
              <AlertTriangle className="w-4 h-4 text-gray-400" />
            </div>
            <p className="text-2xl font-semibold text-gray-900 dark:text-white">{stats.total}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Filtered alerts</p>
          </CardContent></Card>

          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 cursor-pointer hover:border-orange-400 transition" onClick={() => setSelectedCategory("Over-turn")}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600 dark:text-gray-300">High Priority</p>
              <Info className="w-4 h-4 text-gray-400" />
            </div>
            <p className="text-2xl font-semibold text-gray-900 dark:text-white">{stats.highPriority || 0}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Requires attention</p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg border border-red-200 p-4 cursor-pointer hover:border-red-400 transition" onClick={() => setSelectedCategory("Crash detect")}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600 dark:text-gray-300">Crash detect</p>
              <AlertTriangle className="w-4 h-4 text-red-600" />
            </div>
            <p className="text-2xl font-semibold text-red-700">
              {stats.heavyImpact || 0}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Over-turn + Heavy impact</p>
          </div>

          <Card><CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600 dark:text-gray-300">Acknowledged</p>
              <CheckCircle className="w-4 h-4 text-green-500" />
            </div>
            <p className="text-2xl font-semibold text-gray-900 dark:text-white">0</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Read alerts</p>
          </CardContent></Card>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-red-200 p-4 cursor-pointer hover:border-red-400 transition" onClick={() => setSelectedCategory("Over-turn")}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600 dark:text-gray-300">Over-Turn</p>
              <AlertTriangle className="w-4 h-4 text-red-600" />
            </div>
            <p className="text-2xl font-semibold text-red-700">{stats.overTurn || 0}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Over-turn alerts</p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg border border-orange-200 p-4 cursor-pointer hover:border-orange-400 transition" onClick={() => setSelectedCategory("No Communication")}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600 dark:text-gray-300">No Communication</p>
              <XCircle className="w-4 h-4 text-orange-600" />
            </div>
            <p className="text-2xl font-semibold text-orange-700">{stats.noCommunication || 0}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Connection lost</p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg border border-purple-200 p-4 cursor-pointer hover:border-purple-400 transition" onClick={() => setSelectedCategory("Crash detect")}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600 dark:text-gray-300">Heavy Impact</p>
              <Activity className="w-4 h-4 text-purple-600" />
            </div>
            <p className="text-2xl font-semibold text-purple-700">{stats.heavyImpact || 0}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Impact detected</p>
          </div>
        </div>

        {!gmailConnected && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-sm text-yellow-800">
              Gmail not connected. Go to Settings to connect your account.
            </p>
          </div>
        )}

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="border-b border-gray-200 dark:border-gray-700 px-6 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <label className="text-xs font-medium text-gray-600 dark:text-gray-300">Filter by Category:</label>
                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-gray-900 focus:border-gray-900 outline-none"
                  >
                    {categories.map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                  {selectedCategory !== "All" && (
                    <button
                      onClick={() => setSelectedCategory("All")}
                      className="text-xs text-blue-600 hover:text-blue-800"
                    >
                      Clear filter
                    </button>
                  )}
                </div>
                <div className="flex items-center space-x-2">
                  <label className="text-xs font-medium text-gray-600 dark:text-gray-300">Search Plate:</label>
                  <div className="relative">
                    <Search className="w-4 h-4 text-gray-400 absolute left-2.5 top-1/2 transform -translate-y-1/2" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search..."
                      className="pl-8 pr-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-gray-900 focus:border-gray-900 outline-none w-40"
                    />
                  </div>
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery("")}
                      className="text-xs text-blue-600 hover:text-blue-800"
                    >
                      Clear
                    </button>
                  )}
                </div>
                <div className="flex items-center space-x-3">
                  <label className="text-xs font-medium text-gray-600 dark:text-gray-300">Date Range:</label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <button className="inline-flex items-center gap-2 px-3 py-1.5 border rounded-md text-sm bg-white dark:bg-gray-800">
                        <CalendarIcon className="w-4 h-4 text-gray-500" />
                        {dateRange.from || dateRange.to
                          ? `${dateRange.from ? dateRange.from.toISOString().slice(0,10) : ''} – ${dateRange.to ? dateRange.to.toISOString().slice(0,10) : ''}`
                          : 'Select range'}
                      </button>
                    </PopoverTrigger>
                    <PopoverContent>
                      <DateRangePicker value={dateRange} onChange={(range) => setDateRange(range || { from: undefined, to: undefined })} />
                    </PopoverContent>
                  </Popover>
                  <button
                    onClick={() => {
                      setAppliedStartDate(dateRange.from ? dateRange.from.toISOString().slice(0,10) : "");
                      setAppliedEndDate(dateRange.to ? dateRange.to.toISOString().slice(0,10) : "");
                      setPage(1);
                    }}
                    disabled={!dateRange.from && !dateRange.to}
                    className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Apply
                  </button>
                  {(appliedStartDate || appliedEndDate) && (
                    <button
                      onClick={() => {
                        setDateRange({ from: undefined, to: undefined });
                        handleClearDateFilter();
                      }}
                      className="px-3 py-1.5 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 underline"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <label className="text-xs font-medium text-gray-600 dark:text-gray-300">Sort by:</label>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-gray-900 focus:border-gray-900 outline-none"
                  >
                    <option value="priority">Priority</option>
                    <option value="newest">Newest First</option>
                    <option value="oldest">Oldest First</option>
                    <option value="device">Device Name (A-Z)</option>
                    <option value="alerts">Alert Count</option>
                  </select>
                </div>
                <label className="flex items-center space-x-2 text-xs text-gray-600 dark:text-gray-300">
                  <input
                    type="checkbox"
                    checked={autoRefresh}
                    onChange={(e) => setAutoRefresh(e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  <span>Auto-refresh (30s)</span>
                </label>
              </div>
            </div>
          </div>

          <div className="p-6">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">
              {selectedCategory === "All" ? "All Alerts" : `${selectedCategory} Alerts`}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
              {selectedCategory === "All" 
                ? "Latest alerts from all devices" 
                : `Showing ${stats.total} ${selectedCategory} alert${stats.total !== 1 ? 's' : ''}`}
            </p>

            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Device</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Message</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Timestamp</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {groupedAlerts.filter(group => 
                    !searchQuery || group.device.toLowerCase().includes(searchQuery.toLowerCase())
                  ).length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-12 text-sm text-gray-500 dark:text-gray-400">
                        {searchQuery ? `No alerts found for "${searchQuery}"` : "No alerts available"}
                      </TableCell>
                    </TableRow>
                  ) : (
                    groupedAlerts.filter(group => 
                      !searchQuery || group.device.toLowerCase().includes(searchQuery.toLowerCase())
                    ).slice(0, showAllBikes ? undefined : bikesDisplayLimit).map((group, idx) => (
                      <TableRow 
                        key={idx} 
                        className="cursor-pointer"
                        onClick={() => openAlertModal(group)}
                      >
                        <TableCell>
                          <div className="flex items-center space-x-3">
                            <Bike className="w-5 h-5 text-gray-700 dark:text-gray-300" strokeWidth={2} />
                            <span className="text-base font-bold text-gray-900 dark:text-white">{group.device}</span>
                            <span className="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1.5 bg-gray-900 text-white text-xs font-medium rounded">
                              {getCountBadge(group.count)}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-gray-700 dark:text-gray-300">{group.latestAlert.alert_type}</TableCell>
                        <TableCell>
                          <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                            (group.severity === "crash-detected" || group.severity === "heavy-impact") ? "bg-red-100 text-red-700" :
                            group.severity === "high" ? "bg-orange-100 text-orange-700" :
                            "bg-blue-100 text-blue-700"
                          }`}>
                            {group.severity === "crash-detected" ? "Crash Detected" :
                             group.severity === "heavy-impact" ? "Crash detect" : 
                             group.severity === "high" ? "High Priority" : "Normal"}
                          </span>
                        </TableCell>
                        <TableCell className="text-sm text-gray-600 dark:text-gray-300 truncate max-w-xs">
                          {group.latestAlert.location || "No location"}
                        </TableCell>
                        <TableCell>
                          <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                            (group.severity === "crash-detected" || group.severity === "heavy-impact") ? "bg-red-100 text-red-700" :
                            group.severity === "high" ? "bg-orange-100 text-orange-700" :
                            "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                          }`}>
                            {(group.severity === "crash-detected" || group.severity === "heavy-impact") ? "High" : 
                             group.severity === "high" ? "Medium" : "Low"}
                          </span>
                        </TableCell>
                        <TableCell className="text-xs text-gray-500 dark:text-gray-400">
                          {formatUKTimestamp(group.latestAlert.alert_time)}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
            
            {/* Show More/Less bikes button */}
            {groupedAlerts.filter(group => 
              !searchQuery || group.device.toLowerCase().includes(searchQuery.toLowerCase())
            ).length > bikesDisplayLimit && (
              <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-center">
                <button
                  onClick={() => setShowAllBikes(!showAllBikes)}
                  className="px-6 py-2.5 rounded-md text-sm font-medium transition bg-blue-600 text-white hover:bg-blue-700"
                >
                  {showAllBikes ? 'Show Less' : `Show More (${groupedAlerts.filter(group => 
                    !searchQuery || group.device.toLowerCase().includes(searchQuery.toLowerCase())
                  ).length - bikesDisplayLimit} more bikes)`}
                </button>
              </div>
            )}
            
            {/* Lazy loading removed: always show all alerts */}
            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-center">
              {alerts.length > 0 && (
                <div className="text-sm text-gray-600 dark:text-gray-300">
                  <span>
                    Showing all <span className="font-medium">{alerts.length}</span> alerts
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const AdminPage = () => {
    const [users, setUsers] = useState([]);
    const [loadingUsers, setLoadingUsers] = useState(true);
    const [showUserModal, setShowUserModal] = useState(false);
    const [modalMode, setModalMode] = useState('create'); // 'create' or 'edit'
    const [selectedUser, setSelectedUser] = useState(null);
    const [formData, setFormData] = useState({ username: '', email: '', password: '', role: 'viewer' });
    const [savingUser, setSavingUser] = useState(false);

    useEffect(() => {
      loadUsers();
    }, []);

    const loadUsers = async () => {
      try {
        setLoadingUsers(true);
        const response = await api.get("/users/list");
        setUsers(response.data.users || []);
      } catch (error) {
        console.error("Failed to load users:", error);
      } finally {
        setLoadingUsers(false);
      }
    };

    const openCreateModal = () => {
      setModalMode('create');
      setFormData({ username: '', email: '', password: '', role: 'viewer' });
      setSelectedUser(null);
      setShowUserModal(true);
    };

    const openEditModal = (user) => {
      setModalMode('edit');
      setFormData({ 
        username: user.username, 
        email: user.email, 
        password: '', 
        role: user.role 
      });
      setSelectedUser(user);
      setShowUserModal(true);
    };

    const handleSaveUser = async () => {
      if (!formData.username || !formData.email) {
        alert("Username and email are required");
        return;
      }

      if (modalMode === 'create' && !formData.password) {
        alert("Password is required for new users");
        return;
      }

      setSavingUser(true);
      try {
        if (modalMode === 'create') {
          await api.post("/users/create", formData);
        } else {
          await api.put(`/users/${selectedUser.id}`, formData);
        }
        setShowUserModal(false);
        await loadUsers();
      } catch (error) {
        console.error("Failed to save user:", error);
        alert(error.response?.data?.detail || "Failed to save user");
      } finally {
        setSavingUser(false);
      }
    };

    const handleDeleteUser = async (userId, username) => {
      if (!window.confirm(`Are you sure you want to delete user "${username}"?`)) {
        return;
      }

      try {
        await api.delete(`/users/${userId}`);
        await loadUsers();
      } catch (error) {
        console.error("Failed to delete user:", error);
        alert(error.response?.data?.detail || "Failed to delete user");
      }
    };

    if (loadingUsers) {
      return (
        <div className="p-6 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-gray-600 dark:text-gray-300" />
        </div>
      );
    }

    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white dark:text-white">User Management</h1>
            <p className="text-sm text-gray-600 dark:text-gray-300 dark:text-gray-400 mt-1">Manage system users and permissions</p>
          </div>
          <button
            onClick={openCreateModal}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition flex items-center space-x-2"
          >
            <Bell className="w-4 h-4" />
            <span>Create User</span>
          </button>
        </div>

        <Card className="overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Username</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Created At</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">{user.username}</TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                      user.role === 'admin' 
                        ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' 
                        : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                    }`}>
                      {user.role}
                    </span>
                  </TableCell>
                  <TableCell>{formatUKTimestamp(user.created_at)}</TableCell>
                  <TableCell className="text-right space-x-2">
                    <button onClick={() => openEditModal(user)} className="text-blue-600 hover:text-blue-800">Edit</button>
                    <button onClick={() => handleDeleteUser(user.id, user.username)} className="text-red-600 hover:text-red-800">Delete</button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {users.length === 0 && (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              No users found
            </div>
          )}
        </Card>

        {/* User Modal */}
        {showUserModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg max-w-md w-full p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white dark:text-white">
                  {modalMode === 'create' ? 'Create User' : 'Edit User'}
                </h2>
                <button
                  onClick={() => setShowUserModal(false)}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-700 rounded-lg transition"
                >
                  <X className="w-5 h-5 text-gray-600 dark:text-gray-300 dark:text-gray-400" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 dark:text-gray-300 mb-2">
                    Username
                  </label>
                  <input
                    type="text"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
                    placeholder="Enter username"
                    disabled={modalMode === 'edit'}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 dark:text-gray-300 mb-2">
                    Email
                  </label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
                    placeholder="Enter email"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 dark:text-gray-300 mb-2">
                    Password {modalMode === 'edit' && '(leave blank to keep current)'}
                  </label>
                  <input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
                    placeholder="Enter password"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 dark:text-gray-300 mb-2">
                    Role
                  </label>
                  <select
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
                  >
                    <option value="viewer">Viewer</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end space-x-3 mt-6">
                <button
                  onClick={() => setShowUserModal(false)}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 dark:text-gray-300 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 dark:bg-gray-900 dark:hover:bg-gray-700 transition"
                  disabled={savingUser}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveUser}
                  disabled={savingUser}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition disabled:opacity-50 flex items-center space-x-2"
                >
                  {savingUser && <Loader2 className="w-4 h-4 animate-spin" />}
                  <span>{modalMode === 'create' ? 'Create' : 'Save'}</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  const SettingsPage = () => (
    <div className="p-6 space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Gmail Configuration</h3>
        
        {gmailConnected ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-green-50 border border-green-200 rounded-md">
              <div>
                <p className="text-sm font-medium text-green-900">Connected</p>
                <p className="text-xs text-green-700">{gmailEmail}</p>
              </div>
              <button
                onClick={() => {
                  if (window.confirm("Disconnect Gmail?")) {
                    api.delete("/gmail/disconnect");
                    setGmailConnected(false);
                    setGmailEmail("");
                  }
                }}
                className="px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-md transition"
              >
                Disconnect
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleConnectGmail} className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mb-4">
              <p className="text-xs text-blue-900 font-medium mb-2">How to generate Gmail App Password:</p>
              <ol className="text-xs text-blue-800 space-y-1 list-decimal list-inside">
                <li>Go to myaccount.google.com/security</li>
                <li>Enable 2-factor authentication</li>
                <li>Search for "App passwords"</li>
                <li>Generate a new password for "Mail"</li>
                <li>Paste the password below</li>
              </ol>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Gmail Address
              </label>
              <input
                type="email"
                value={gmailEmail}
                onChange={(e) => setGmailEmail(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-1 focus:ring-gray-900 focus:border-gray-900 outline-none text-sm"
                placeholder="your-email@gmail.com"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                App Password
              </label>
              <input
                type="password"
                value={gmailPassword}
                onChange={(e) => setGmailPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-1 focus:ring-gray-900 focus:border-gray-900 outline-none text-sm"
                placeholder="xxxx xxxx xxxx xxxx"
                required
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-gray-900 text-white rounded-md hover:bg-gray-800 transition text-sm"
            >
              Connect Gmail
            </button>
          </form>
        )}
      </div>
    </div>
  );

  const AlertModal = () => {
    if (!showModal || !selectedAlert) return null;

    const openBikeHistoryFromAlert = async () => {
      try {
        const response = await api.get(`/bikes/by-tracker/${encodeURIComponent(selectedAlert.device)}`);
        await openBikeHistory(response.data.bike_id, selectedAlert.device);
        setShowModal(false);
      } catch (error) {
        console.error("Failed to open bike history:", error);
        alert("Failed to open bike history");
      }
    };

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" onClick={() => setShowModal(false)}>
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
          
          {/* Header com Device */}
          <div className="px-8 py-6 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-gray-50 to-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="p-3 bg-gray-900 rounded-lg">
                  <Bike className="w-8 h-8 text-white" strokeWidth={2} />
                </div>
                <div>
                  <div className="flex items-center space-x-3">
                    <h2 
                      onClick={openBikeHistoryFromAlert}
                      className="text-2xl font-bold text-gray-900 dark:text-white cursor-pointer hover:text-gray-700 dark:text-gray-300 transition"
                    >
                      {selectedAlert.device}
                    </h2>
                    <span className="inline-flex items-center justify-center min-w-8 h-8 px-3 bg-gray-900 text-white text-base font-bold rounded-lg">
                      {selectedAlert.count}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Motorcycle Alert Details (click name for history)</p>
                </div>
              </div>
              <button onClick={() => setShowModal(false)} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 dark:bg-gray-700 rounded-lg transition">
                <X className="w-6 h-6 text-gray-500 dark:text-gray-400" />
              </button>
            </div>
          </div>

          {/* Status Summary */}
          <div className="px-8 py-5 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-6">
                <div className="flex items-center space-x-2">
                  <Activity className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                  <div>
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Total Alerts</p>
                    <p className="text-lg font-bold text-gray-900 dark:text-white">{selectedAlert.count}</p>
                  </div>
                </div>
                <div className="h-12 w-px bg-gray-300"></div>
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="w-5 h-5 text-orange-600" />
                  <div>
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Priority Level</p>
                    <div className={`mt-1 inline-flex px-3 py-1 rounded-md text-xs font-bold ${
                      (selectedAlert.severity === "crash-detected" || selectedAlert.severity === "heavy-impact") ? "bg-red-100 text-red-700" :
                      selectedAlert.severity === "high" ? "bg-orange-100 text-orange-700" :
                      "bg-blue-100 text-blue-700"
                    }`}>
                      {selectedAlert.severity === "crash-detected" ? "CRASH DETECTED" :
                       selectedAlert.severity === "heavy-impact" ? "HEAVY IMPACT" :
                       selectedAlert.severity === "high" ? "HIGH PRIORITY" : "NORMAL"}
                    </div>
                  </div>
                </div>
              </div>
              <button
                onClick={openBikeHistoryFromAlert}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition"
              >
                <MessageSquare className="w-4 h-4" />
                <span>Record Action</span>
              </button>
            </div>
          </div>

          {/* Alert List */}
          <div className="px-8 py-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
              <Bell className="w-5 h-5 mr-2 text-gray-700 dark:text-gray-300" />
              Alert History
            </h3>
            <div className="space-y-4">
              {[...selectedAlert.alerts].sort((a, b) => new Date(b.alert_time) - new Date(a.alert_time)).map((alert, idx) => (
                <div key={idx} className="p-5 bg-white border-2 border-gray-200 dark:border-gray-700 rounded-xl hover:border-gray-300 transition space-y-4">
                  
                  {/* Alert Header */}
                  <div className="flex items-start justify-between pb-3 border-b border-gray-100">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-red-50 rounded-lg">
                        <AlertTriangle className="w-5 h-5 text-red-600" />
                      </div>
                      <div>
                        <h4 className="text-base font-bold text-gray-900 dark:text-white">{alert.alert_type}</h4>
                        <div className="flex items-center space-x-2 mt-1">
                          <Clock className="w-3.5 h-3.5 text-gray-400" />
                          <p className="text-sm text-gray-500 dark:text-gray-400">{formatUKTimestamp(alert.alert_time)}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Alert Details Grid */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex items-start space-x-3 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                      <MapPin className="w-5 h-5 text-blue-600 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-gray-600 dark:text-gray-300 mb-1">Location</p>
                        <p className="text-sm text-gray-900 dark:text-white break-words">{alert.location || "Unknown"}</p>
                      </div>
                    </div>
                    <div className="flex items-start space-x-3 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                      <MapPin className="w-5 h-5 text-green-600 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-gray-600 dark:text-gray-300 mb-1">Coordinates</p>
                        <p className="text-sm text-gray-900 dark:text-white font-mono">{alert.latitude}, {alert.longitude}</p>
                      </div>
                    </div>
                    <div className="flex items-start space-x-3 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                      <Database className="w-5 h-5 text-purple-600 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-gray-600 dark:text-gray-300 mb-1">Device Serial</p>
                        <p className="text-sm text-gray-900 dark:text-white font-mono">{alert.device_serial}</p>
                      </div>
                    </div>
                    <div className="flex items-start space-x-3 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                      <Info className="w-5 h-5 text-orange-600 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-gray-600 dark:text-gray-300 mb-1">Account</p>
                        <p className="text-sm text-gray-900 dark:text-white">{alert.account_name || "Unknown"}</p>
                      </div>
                    </div>
                  </div>

                  {/* Map Link */}
                  {alert.latitude && alert.longitude && (
                    <div className="pt-3 border-t border-gray-100">
                      <a 
                        href={`https://www.google.com/maps?q=${alert.latitude},${alert.longitude}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition"
                      >
                        <MapPin className="w-4 h-4" />
                        <span>View Location on Google Maps</span>
                      </a>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Footer Actions */}
          <div className="px-8 py-5 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 flex justify-between items-center">
            <button
              onClick={() => setShowModal(false)}
              className="px-5 py-2.5 border-2 border-gray-300 text-gray-700 dark:text-gray-300 font-medium rounded-lg hover:bg-white transition"
            >
              Close
            </button>
            <div className="flex items-center space-x-3">
              <button
                onClick={() => handleAcknowledgeAlert(selectedAlert.latestAlert.id)}
                className="flex items-center space-x-2 px-5 py-2.5 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition"
              >
                <CheckCircle className="w-4 h-4" />
                <span>Acknowledge</span>
              </button>
              <button
                onClick={() => {
                  handleDeleteAlert(selectedAlert.latestAlert.id);
                  setShowModal(false);
                }}
                className="flex items-center space-x-2 px-5 py-2.5 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 transition"
              >
                <Trash2 className="w-4 h-4" />
                <span>Delete Alert</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };


  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gray-50 dark:bg-gray-900 dark:bg-gray-900 flex overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-900 dark:bg-gray-900">
          {currentPage === "dashboard" && <DashboardPage />}
          {currentPage === "bikes" && <BikesPage />}
          {currentPage === "admin" && <AdminPage />}
          {currentPage === "settings" && <SettingsPage />}
        </main>
      </div>
      <CrashNotification crashAlerts={crashAlerts} onDismiss={dismissCrashAlert} />
      <AlertModal />
      <BikeHistoryModal />
    </div>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await api.get("/auth/me");
        setUser(response.data);
      } catch (error) {
      }
      setLoading(false);
    };
    checkAuth();
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
  };

  const handleLogout = async () => {
    try {
      await api.post("/auth/logout");
    } catch (error) {
    }
    setUser(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  return user ? (
    <Dashboard user={user} onLogout={handleLogout} />
  ) : (
    <LoginPage onLogin={handleLogin} />
  );
}

export default App;
