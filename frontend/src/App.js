import React, { useState, useEffect, useMemo, useCallback } from "react";
import "@/App.css";
import axios from "axios";
import { 
  Bell, Settings, LayoutDashboard, LogOut, Menu, X, Trash2, 
  AlertTriangle, Database, Mail, Activity, Bike, CheckCircle, 
  XCircle, Clock, MapPin, Info, Moon, Sun, Search, Star, 
  MessageSquare, CheckCircle2, RefreshCw, Loader2, Download
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

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
  if (!dateString) return "Unknown";
  
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return "Invalid date";
    
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    
    return `${day}/${month}/${year} ${hours}:${minutes}`;
  } catch {
    return "Invalid date";
  }
};

// Crash Alert Notification Component
function CrashNotification({ crashAlerts, onDismiss }) {
  if (crashAlerts.length === 0) return null;

  return (
    <div className="fixed top-20 right-6 z-50 space-y-3">
      {crashAlerts.map((crash, index) => (
        <div
          key={index}
          className="bg-red-600 text-white px-6 py-4 rounded-lg shadow-2xl border-2 border-red-700 animate-pulse"
        >
          <div className="flex items-center space-x-3">
            <AlertTriangle className="w-6 h-6" />
            <div className="flex-1">
              <div className="font-bold text-lg">CRASH DETECTED!</div>
              <div className="text-sm mt-1">{crash.device}</div>
              <div className="text-xs opacity-90 mt-1">{formatUKTimestamp(crash.timestamp)}</div>
            </div>
            <button
              onClick={() => onDismiss(crash.device)}
              className="text-white hover:text-gray-200 transition"
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
      
      const response = await api.post(endpoint, payload);
      
      if (response.data.user) {
        onLogin(response.data.user);
      }
    } catch (err) {
      setError(err.response?.data?.detail || (isRegister ? "Registration failed" : "Login failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 mb-4">
              <Bike className="w-16 h-16 text-gray-900" strokeWidth={1.5} />
            </div>
            <h1 className="text-2xl font-semibold text-gray-900 mb-2">Tracker Alerts System</h1>
            <p className="text-sm text-gray-600">{isRegister ? "Create your account" : "Sign in to access the dashboard"}</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
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
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
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
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
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
                className="text-sm text-gray-600 hover:text-gray-900 transition"
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

  const [gmailEmail, setGmailEmail] = useState("");
  const [gmailPassword, setGmailPassword] = useState("");
  const [gmailConnected, setGmailConnected] = useState(false);
  const [syncInterval, setSyncInterval] = useState(10);
  const [emailLimit, setEmailLimit] = useState(100);


  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("priority");
  const [filterDate, setFilterDate] = useState("");
  
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20); // Reduced for lazy loading
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 20,
    total: 0,
    total_pages: 0,
    has_next: false,
    has_prev: false
  });

  const [bikes, setBikes] = useState([]);
  const [loadingBikes, setLoadingBikes] = useState(false);
  const [bikeSearchQuery, setBikeSearchQuery] = useState("");
  const [selectedBikeId, setSelectedBikeId] = useState(null);
  const [showBikeHistory, setShowBikeHistory] = useState(false);

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
    // Reset to page 1 and reload when category changes
    setPage(1);
    if (selectedCategory !== "All") {
      loadAlerts(selectedCategory, 1, false);
    } else {
      loadAlerts(null, 1, false);
    }
  }, [selectedCategory]);

  useEffect(() => {
    // Auto-refresh alerts and statistics every 60 seconds (silent, no loading spinner)
    const interval = setInterval(() => {
      loadAlertsQuiet(selectedCategory !== "All" ? selectedCategory : null);
    }, 60000);
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [selectedCategory]);

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
      
      const url = `/alerts/list?${params.toString()}`;
      const response = await api.get(url);
      
      setAlerts(response.data.alerts);
      setStats(response.data.stats);
      setGmailConnected(response.data.connected);
      setGmailEmail(response.data.email || "");
      setHasMore(response.data.pagination?.has_next || false);
      setPagination(response.data.pagination || {
        page: 1,
        limit: limit,
        total: 0,
        total_pages: 0,
        has_next: false,
        has_prev: false
      });
      setPage(1); // Reset page to 1 to keep pagination state consistent
      
      groupAlertsByDevice(response.data.alerts);
    } catch (error) {
      console.error("Failed to quiet refresh alerts:", error);
    }
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
      
      if (filterDate) {
        params.append('start_date', filterDate);
        params.append('end_date', filterDate);
      }
      
      const url = `/alerts/list?${params.toString()}`;
      
      const response = await api.get(url);
      
      if (append) {
        setAlerts(prev => [...prev, ...response.data.alerts]);
      } else {
        setAlerts(response.data.alerts);
      }
      
      setStats(response.data.stats);
      setGmailConnected(response.data.connected);
      setGmailEmail(response.data.email || "");
      setHasMore(response.data.pagination?.has_next || false);
      setPagination(response.data.pagination || {
        page: pageNum,
        limit: limit,
        total: 0,
        total_pages: 0,
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
  
  const loadMoreAlerts = async () => {
    if (hasMore && !loadingMore) {
      setLoadingMore(true);
      const nextPage = page + 1;
      // Manually track page without triggering effects
      const success = await loadAlerts(selectedCategory !== "All" ? selectedCategory : null, nextPage, true);
      // Only update page state after successful load to track position
      if (success) {
        setPage(nextPage);
      } else {
        setLoadingMore(false); // Reset loading state on failure
      }
    }
  };

  const groupAlertsByDevice = (alertList) => {
    const grouped = {};
    
    alertList.forEach(alert => {
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
      
      // Add date filter
      if (filterDate) {
        params.append('start_date', filterDate);
        params.append('end_date', filterDate);
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
    <div className={`${sidebarOpen ? 'w-64' : 'w-0'} bg-white border-r border-gray-200 transition-all duration-300 overflow-hidden flex flex-col h-screen`}>
      <div className="p-6 flex-1">
        <div className="flex items-center space-x-3 mb-8">
          <Bike className="w-6 h-6 text-gray-900" />
          <div>
            <span className="text-sm font-semibold text-gray-900">Tracker System</span>
            <p className="text-xs text-gray-500">Dashboard</p>
          </div>
        </div>

        <nav className="space-y-1">
          <button
            onClick={() => setCurrentPage("dashboard")}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md text-sm transition ${
              currentPage === "dashboard"
                ? "bg-gray-900 text-white"
                : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <LayoutDashboard className="w-4 h-4" />
            <span className="font-medium">Bike Tracker</span>
          </button>

          <button
            onClick={() => setCurrentPage("bikes")}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md text-sm transition ${
              currentPage === "bikes"
                ? "bg-gray-900 text-white"
                : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <Bike className="w-4 h-4" />
            <span className="font-medium">Bikes</span>
          </button>

          <button
            onClick={() => setCurrentPage("admin")}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md text-sm transition ${
              currentPage === "admin"
                ? "bg-gray-900 text-white"
                : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <Activity className="w-4 h-4" />
            <span className="font-medium">Admin Dashboard</span>
          </button>

          <button
            onClick={() => setCurrentPage("settings")}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md text-sm transition ${
              currentPage === "settings"
                ? "bg-gray-900 text-white"
                : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <Settings className="w-4 h-4" />
            <span className="font-medium">Service Tracker</span>
          </button>
        </nav>
      </div>

      <div className="p-6 border-t border-gray-200">
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

  const Header = () => {
    const isAdmin = user && user.username === 'admin';
    
    return (
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1 hover:bg-gray-100 rounded transition"
            >
              {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            <div>
              <h1 className="text-xl font-semibold text-gray-900">
                {currentPage === "dashboard" && "Bike Tracker Dashboard"}
                {currentPage === "admin" && "System Dashboard"}
                {currentPage === "settings" && "Settings"}
              </h1>
              <p className="text-xs text-gray-500">
                {currentPage === "dashboard" && "Monitor your bike trackers and alerts by category"}
                {currentPage === "admin" && "Monitor system health and logs"}
                {currentPage === "settings" && "Configure Gmail integration"}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={toggleDarkMode}
              className="p-2 hover:bg-gray-100 rounded-md transition"
              title={darkMode ? "Light mode" : "Dark mode"}
            >
              {darkMode ? <Sun className="w-5 h-5 text-gray-600" /> : <Moon className="w-5 h-5 text-gray-600" />}
            </button>
            <button
              onClick={handleExportCSV}
              className="flex items-center space-x-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition text-sm"
            >
              <Download className="w-4 h-4" />
              <span>Export CSV</span>
            </button>
            <button
              onClick={handleRefreshAlerts}
              disabled={syncing}
              className="flex items-center space-x-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            >
              <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
              <span>Refresh Alerts</span>
            </button>
            <button
              onClick={handleSyncTodayEmails}
              disabled={syncing}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            >
              <Download className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
              <span>
                {syncing && syncProgress.total > 0 
                  ? `Syncing: ${syncProgress.processed}/${syncProgress.total} (${syncProgress.remaining} remaining)` 
                  : 'Update All Emails'}
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

    const openBikeHistory = (bikeId) => {
      setSelectedBikeId(bikeId);
      setShowBikeHistory(true);
    };

    if (loadingBikes) {
      return (
        <div className="flex items-center justify-center h-full">
          <Loader2 className="w-8 h-8 animate-spin text-gray-600" />
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
            <h1 className="text-2xl font-bold text-gray-900">Bikes</h1>
            <p className="text-sm text-gray-600 mt-1">View and manage your tracked bikes</p>
          </div>
        </div>

        {bikes.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-4">
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
          </div>
        )}

        {filteredBikes.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <Bike className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">
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
                onClick={() => openBikeHistory(bike.id)}
                className="bg-white rounded-lg border border-gray-200 p-6 hover:border-gray-400 cursor-pointer transition"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="p-3 bg-gray-900 rounded-lg">
                    <Bike className="w-6 h-6 text-white" />
                  </div>
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                    {bike.alert_count} alerts
                  </span>
                </div>
                
                <h3 className="text-lg font-bold text-gray-900 mb-2">{bike.tracker_name}</h3>
                
                {bike.device_serial && (
                  <p className="text-sm text-gray-600 mb-2">Serial: {bike.device_serial}</p>
                )}
                
                {bike.latest_alert_at && (
                  <p className="text-xs text-gray-500">
                    Last alert: {formatUKTimestamp(bike.latest_alert_at)}
                  </p>
                )}
                
                {bike.notes_count > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <span className="text-xs text-gray-600">
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

  const DashboardPage = () => {
    const getSeverityBadge = (severity) => {
      if (severity === "crash-detected" || severity === "heavy-impact") return "bg-red-100 text-red-700 border-red-200";
      if (severity === "high") return "bg-orange-100 text-orange-700 border-orange-200";
      return "bg-gray-100 text-gray-700 border-gray-200";
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
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600">Total Alerts</p>
              <AlertTriangle className="w-4 h-4 text-gray-400" />
            </div>
            <p className="text-2xl font-semibold text-gray-900">{stats.total}</p>
            <p className="text-xs text-gray-500 mt-1">Filtered alerts</p>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-4 cursor-pointer hover:border-orange-400 transition" onClick={() => setSelectedCategory("Over-turn")}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600">High Priority</p>
              <Info className="w-4 h-4 text-gray-400" />
            </div>
            <p className="text-2xl font-semibold text-gray-900">{stats.highPriority || 0}</p>
            <p className="text-xs text-gray-500 mt-1">Requires attention</p>
          </div>

          <div className="bg-white rounded-lg border border-red-200 p-4 cursor-pointer hover:border-red-400 transition" onClick={() => setSelectedCategory("Crash detect")}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600">Crash detect</p>
              <AlertTriangle className="w-4 h-4 text-red-600" />
            </div>
            <p className="text-2xl font-semibold text-red-700">
              {stats.heavyImpact || 0}
            </p>
            <p className="text-xs text-gray-500 mt-1">Over-turn + Heavy impact</p>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600">Acknowledged</p>
              <CheckCircle className="w-4 h-4 text-green-500" />
            </div>
            <p className="text-2xl font-semibold text-gray-900">0</p>
            <p className="text-xs text-gray-500 mt-1">Read alerts</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
          <div className="bg-white rounded-lg border border-red-200 p-4 cursor-pointer hover:border-red-400 transition" onClick={() => setSelectedCategory("Over-turn")}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600">Over-Turn</p>
              <AlertTriangle className="w-4 h-4 text-red-600" />
            </div>
            <p className="text-2xl font-semibold text-red-700">{stats.overTurn || 0}</p>
            <p className="text-xs text-gray-500 mt-1">Over-turn alerts</p>
          </div>

          <div className="bg-white rounded-lg border border-orange-200 p-4 cursor-pointer hover:border-orange-400 transition" onClick={() => setSelectedCategory("No Communication")}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600">No Communication</p>
              <XCircle className="w-4 h-4 text-orange-600" />
            </div>
            <p className="text-2xl font-semibold text-orange-700">{stats.noCommunication || 0}</p>
            <p className="text-xs text-gray-500 mt-1">Connection lost</p>
          </div>

          <div className="bg-white rounded-lg border border-purple-200 p-4 cursor-pointer hover:border-purple-400 transition" onClick={() => setSelectedCategory("Crash detect")}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600">Heavy Impact</p>
              <Activity className="w-4 h-4 text-purple-600" />
            </div>
            <p className="text-2xl font-semibold text-purple-700">{stats.heavyImpact || 0}</p>
            <p className="text-xs text-gray-500 mt-1">Impact detected</p>
          </div>
        </div>

        {!gmailConnected && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-sm text-yellow-800">
              Gmail not connected. Go to Settings to connect your account.
            </p>
          </div>
        )}

        <div className="bg-white rounded-lg border border-gray-200">
          <div className="border-b border-gray-200 px-6 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <label className="text-xs font-medium text-gray-600">Filter by Category:</label>
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
                  <label className="text-xs font-medium text-gray-600">Search Plate:</label>
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
                <div className="flex items-center space-x-2">
                  <label className="text-xs font-medium text-gray-600">Filter by Date:</label>
                  <input
                    type="date"
                    value={filterDate}
                    onChange={(e) => { setFilterDate(e.target.value); setPage(1); }}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-gray-900 focus:border-gray-900 outline-none"
                  />
                  {filterDate && (
                    <button
                      onClick={() => { setFilterDate(""); setPage(1); }}
                      className="text-xs text-gray-500 hover:text-gray-700 underline"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <label className="text-xs font-medium text-gray-600">Sort by:</label>
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
                <label className="flex items-center space-x-2 text-xs text-gray-600">
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
            <h3 className="text-sm font-semibold text-gray-900 mb-1">
              {selectedCategory === "All" ? "All Alerts" : `${selectedCategory} Alerts`}
            </h3>
            <p className="text-xs text-gray-500 mb-4">
              {selectedCategory === "All" 
                ? "Latest alerts from all devices" 
                : `Showing ${stats.total} ${selectedCategory} alert${stats.total !== 1 ? 's' : ''}`}
            </p>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-600">Device</th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-600">Type</th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-600">Category</th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-600">Message</th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-600">Severity</th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-600">Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {groupedAlerts.filter(group => 
                    !searchQuery || group.device.toLowerCase().includes(searchQuery.toLowerCase())
                  ).length === 0 ? (
                    <tr>
                      <td colSpan="6" className="text-center py-12 text-sm text-gray-500">
                        {searchQuery ? `No alerts found for "${searchQuery}"` : "No alerts available"}
                      </td>
                    </tr>
                  ) : (
                    groupedAlerts.filter(group => 
                      !searchQuery || group.device.toLowerCase().includes(searchQuery.toLowerCase())
                    ).map((group, idx) => (
                      <tr 
                        key={idx} 
                        className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition"
                        onClick={() => openAlertModal(group)}
                      >
                        <td className="py-3 px-4">
                          <div className="flex items-center space-x-3">
                            <Bike className="w-5 h-5 text-gray-700" strokeWidth={2} />
                            <span className="text-base font-bold text-gray-900">{group.device}</span>
                            <span className="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1.5 bg-gray-900 text-white text-xs font-medium rounded">
                              {getCountBadge(group.count)}
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-sm text-gray-700">{group.latestAlert.alert_type}</td>
                        <td className="py-3 px-4">
                          <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                            (group.severity === "crash-detected" || group.severity === "heavy-impact") ? "bg-red-100 text-red-700" :
                            group.severity === "high" ? "bg-orange-100 text-orange-700" :
                            "bg-blue-100 text-blue-700"
                          }`}>
                            {group.severity === "crash-detected" ? "Crash Detected" :
                             group.severity === "heavy-impact" ? "Crash detect" : 
                             group.severity === "high" ? "High Priority" : "Normal"}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-sm text-gray-600 truncate max-w-xs">
                          {group.latestAlert.location || "No location"}
                        </td>
                        <td className="py-3 px-4">
                          <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                            (group.severity === "crash-detected" || group.severity === "heavy-impact") ? "bg-red-100 text-red-700" :
                            group.severity === "high" ? "bg-orange-100 text-orange-700" :
                            "bg-gray-100 text-gray-700"
                          }`}>
                            {(group.severity === "crash-detected" || group.severity === "heavy-impact") ? "High" : 
                             group.severity === "high" ? "Medium" : "Low"}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-xs text-gray-500">
                          {formatUKTimestamp(group.latestAlert.alert_time)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            
            {/* Lazy loading: Load More button */}
            {hasMore && (
              <div className="px-6 py-4 border-t border-gray-200 flex flex-col items-center gap-3">
                <div className="text-sm text-gray-600">
                  <span>
                    Showing <span className="font-medium">{alerts.length}</span> of{' '}
                    <span className="font-medium">{pagination.total}</span> alerts
                  </span>
                </div>
                
                <button
                  onClick={loadMoreAlerts}
                  disabled={loadingMore}
                  className={`px-6 py-2.5 rounded-md text-sm font-medium transition ${
                    loadingMore
                      ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                      : 'bg-gray-900 text-white hover:bg-gray-800'
                  }`}
                >
                  {loadingMore ? 'Loading...' : 'Load More Alerts'}
                </button>
              </div>
            )}
            
            {/* Show total when no more to load */}
            {!hasMore && alerts.length > 0 && (
              <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-center">
                <div className="text-sm text-gray-600">
                  <span>
                    Showing all <span className="font-medium">{alerts.length}</span> alerts
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const AdminPage = () => {
    const [systemStatus, setSystemStatus] = useState(null);
    const [loadingStatus, setLoadingStatus] = useState(true);
    const [syncConfig, setSyncConfig] = useState({ sync_interval_minutes: 10, email_limit_per_sync: 100 });
    const [showSaveSuccess, setShowSaveSuccess] = useState(false);
    const [savingConfig, setSavingConfig] = useState(false);

    useEffect(() => {
      loadSystemStatus();
      loadSyncConfig();
      const interval = setInterval(loadSystemStatusQuiet, 60000); // Silent refresh every 60s
      return () => clearInterval(interval);
    }, []);

    const loadSystemStatus = async () => {
      try {
        const response = await api.get("/system/status");
        setSystemStatus(response.data);
      } catch (error) {
        console.error("Failed to load system status:", error);
      } finally {
        setLoadingStatus(false);
      }
    };

    const loadSystemStatusQuiet = async () => {
      try {
        // Silent refresh: updates data without loading spinner
        const response = await api.get("/system/status");
        setSystemStatus(response.data);
      } catch (error) {
        console.error("Failed to quiet refresh system status:", error);
      }
    };

    const loadSyncConfig = async () => {
      try {
        const response = await api.get("/sync/config");
        setSyncConfig(response.data);
        setSyncInterval(response.data.sync_interval_minutes);
        setEmailLimit(response.data.email_limit_per_sync);
      } catch (error) {
        console.error("Failed to load sync config:", error);
      }
    };

    const handleSaveSyncConfig = async () => {
      const intervalValue = parseInt(syncInterval);
      const limitValue = parseInt(emailLimit);

      if (!intervalValue || intervalValue < 1 || intervalValue > 1440) {
        alert("Sync interval must be between 1 and 1440 minutes");
        return;
      }

      if (!limitValue || limitValue < 1 || limitValue > 200) {
        alert("Email limit must be between 1 and 200");
        return;
      }

      setSavingConfig(true);
      try {
        await api.post("/sync/config", {
          sync_interval_minutes: intervalValue,
          email_limit_per_sync: limitValue
        });
        setShowSaveSuccess(true);
        setTimeout(() => setShowSaveSuccess(false), 3000);
      } catch (error) {
        console.error("Failed to save sync config:", error);
        const errorMsg = error.response?.data?.detail || "Failed to save configuration. Please try again.";
        alert(errorMsg);
      } finally {
        setSavingConfig(false);
      }
    };

    if (loadingStatus) {
      return (
        <div className="p-6 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-gray-600" />
        </div>
      );
    }

    return (
      <div className="p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-gray-600">System Status</p>
              <Activity className="w-4 h-4 text-gray-400" />
            </div>
            <div className="flex items-center space-x-2">
              {systemStatus?.system_healthy ? (
                <>
                  <CheckCircle className="w-5 h-5 text-green-500" />
                  <span className="text-lg font-semibold text-green-600">Online</span>
                </>
              ) : (
                <>
                  <XCircle className="w-5 h-5 text-red-500" />
                  <span className="text-lg font-semibold text-red-600">Error</span>
                </>
              )}
            </div>
            {systemStatus?.last_sync_at && (
              <p className="text-xs text-gray-500 mt-2">
                Last sync: {formatUKTimestamp(systemStatus.last_sync_at)}
              </p>
            )}
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-gray-600">Database</p>
              <Database className="w-4 h-4 text-gray-400" />
            </div>
            <div className="flex items-center space-x-2">
              {systemStatus?.database_connected ? (
                <>
                  <CheckCircle className="w-5 h-5 text-green-500" />
                  <span className="text-lg font-semibold text-green-600">Connected</span>
                </>
              ) : (
                <>
                  <XCircle className="w-5 h-5 text-red-500" />
                  <span className="text-lg font-semibold text-red-600">Disconnected</span>
                </>
              )}
            </div>
            <p className="text-xs text-gray-500 mt-1">Neon PostgreSQL</p>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-gray-600">Gmail Integration</p>
              <Mail className="w-4 h-4 text-gray-400" />
            </div>
            <div className="flex items-center space-x-2">
              {systemStatus?.gmail_connected ? (
                <>
                  <CheckCircle className="w-5 h-5 text-green-500" />
                  <span className="text-lg font-semibold text-green-600">Active</span>
                </>
              ) : (
                <>
                  <Clock className="w-5 h-5 text-yellow-500" />
                  <span className="text-lg font-semibold text-yellow-600">Inactive</span>
                </>
              )}
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {systemStatus?.gmail_email || "Not configured"}
            </p>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-gray-600">Total Alerts</p>
              <Activity className="w-4 h-4 text-gray-400" />
            </div>
            <p className="text-2xl font-semibold text-gray-900">{systemStatus?.total_alerts || 0}</p>
            <p className="text-xs text-gray-500 mt-1">In database</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-1">Last Sync Status</h3>
            <p className="text-xs text-gray-500 mb-4">Most recent email synchronization</p>
            {systemStatus?.last_sync_at ? (
              <div>
                <p className="text-sm font-medium text-gray-900">{formatUKTimestamp(systemStatus.last_sync_at)}</p>
                <p className="text-xs text-gray-500 mt-1">Last Email ID: {systemStatus.last_email_id || 'N/A'}</p>
              </div>
            ) : (
              <p className="text-sm text-gray-600">No sync history available</p>
            )}
          </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-1">Activity Summary</h3>
          <p className="text-xs text-gray-500 mb-4">Recent system activity</p>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Alerts (24h):</span>
              <span className="font-medium text-gray-900">{stats.total}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Total Devices:</span>
              <span className="font-medium text-gray-900">{groupedAlerts.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Unique Devices:</span>
              <span className="font-medium text-gray-900">{groupedAlerts.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Errors (1h):</span>
              <span className="font-medium text-red-600">0</span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Sync Configuration</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">
              Sync Interval (minutes)
            </label>
            <input
              type="number"
              value={syncInterval}
              disabled
              className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-100 text-gray-600 cursor-not-allowed text-sm"
              min="1"
            />
            <p className="text-xs text-gray-500 mt-1">Fixed at 5 minutes for optimal performance</p>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">
              Email Limit per Sync
            </label>
            <input
              type="number"
              value={emailLimit}
              disabled
              className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-100 text-gray-600 cursor-not-allowed text-sm"
              min="1"
              max="200"
            />
            <p className="text-xs text-gray-500 mt-1">Fixed at 30 emails per sync</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-red-200 p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-2">Danger Zone</h3>
        <p className="text-xs text-gray-500 mb-4">Irreversible actions - use with caution</p>
        <div className="flex items-center justify-between p-4 bg-red-50 border border-red-200 rounded-md">
          <div>
            <p className="text-sm font-medium text-red-900">Clear All History</p>
            <p className="text-xs text-red-700 mt-0.5">Deletes all alerts and resets sync checkpoint</p>
          </div>
          <button
            onClick={handleClearHistory}
            className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700 transition"
          >
            <Trash2 className="inline w-4 h-4 mr-1" />
            Clear All
          </button>
        </div>
      </div>
    </div>
    );
  };

  const SettingsPage = () => (
    <div className="p-6 space-y-6">
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Gmail Configuration</h3>
        
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
              <label className="block text-xs font-medium text-gray-700 mb-1.5">
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
              <label className="block text-xs font-medium text-gray-700 mb-1.5">
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
        setSelectedBikeId(response.data.bike_id);
        setShowBikeHistory(true);
        setShowModal(false);
      } catch (error) {
        console.error("Failed to open bike history:", error);
        alert("Failed to open bike history");
      }
    };

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" onClick={() => setShowModal(false)}>
        <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
          
          {/* Header com Device */}
          <div className="px-8 py-6 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="p-3 bg-gray-900 rounded-lg">
                  <Bike className="w-8 h-8 text-white" strokeWidth={2} />
                </div>
                <div>
                  <div className="flex items-center space-x-3">
                    <h2 
                      onClick={openBikeHistoryFromAlert}
                      className="text-2xl font-bold text-gray-900 cursor-pointer hover:text-gray-700 transition"
                    >
                      {selectedAlert.device}
                    </h2>
                    <span className="inline-flex items-center justify-center min-w-8 h-8 px-3 bg-gray-900 text-white text-base font-bold rounded-lg">
                      {selectedAlert.count}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">Motorcycle Alert Details (click name for history)</p>
                </div>
              </div>
              <button onClick={() => setShowModal(false)} className="p-2 hover:bg-gray-100 rounded-lg transition">
                <X className="w-6 h-6 text-gray-500" />
              </button>
            </div>
          </div>

          {/* Status Summary */}
          <div className="px-8 py-5 bg-gray-50 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-6">
                <div className="flex items-center space-x-2">
                  <Activity className="w-5 h-5 text-gray-600" />
                  <div>
                    <p className="text-xs font-medium text-gray-500">Total Alerts</p>
                    <p className="text-lg font-bold text-gray-900">{selectedAlert.count}</p>
                  </div>
                </div>
                <div className="h-12 w-px bg-gray-300"></div>
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="w-5 h-5 text-orange-600" />
                  <div>
                    <p className="text-xs font-medium text-gray-500">Priority Level</p>
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
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <Bell className="w-5 h-5 mr-2 text-gray-700" />
              Alert History
            </h3>
            <div className="space-y-4">
              {[...selectedAlert.alerts].sort((a, b) => new Date(b.alert_time) - new Date(a.alert_time)).map((alert, idx) => (
                <div key={idx} className="p-5 bg-white border-2 border-gray-200 rounded-xl hover:border-gray-300 transition space-y-4">
                  
                  {/* Alert Header */}
                  <div className="flex items-start justify-between pb-3 border-b border-gray-100">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-red-50 rounded-lg">
                        <AlertTriangle className="w-5 h-5 text-red-600" />
                      </div>
                      <div>
                        <h4 className="text-base font-bold text-gray-900">{alert.alert_type}</h4>
                        <div className="flex items-center space-x-2 mt-1">
                          <Clock className="w-3.5 h-3.5 text-gray-400" />
                          <p className="text-sm text-gray-500">{formatUKTimestamp(alert.alert_time)}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Alert Details Grid */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                      <MapPin className="w-5 h-5 text-blue-600 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-gray-600 mb-1">Location</p>
                        <p className="text-sm text-gray-900 break-words">{alert.location || "Unknown"}</p>
                      </div>
                    </div>
                    <div className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                      <MapPin className="w-5 h-5 text-green-600 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-gray-600 mb-1">Coordinates</p>
                        <p className="text-sm text-gray-900 font-mono">{alert.latitude}, {alert.longitude}</p>
                      </div>
                    </div>
                    <div className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                      <Database className="w-5 h-5 text-purple-600 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-gray-600 mb-1">Device Serial</p>
                        <p className="text-sm text-gray-900 font-mono">{alert.device_serial}</p>
                      </div>
                    </div>
                    <div className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                      <Info className="w-5 h-5 text-orange-600 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-gray-600 mb-1">Account</p>
                        <p className="text-sm text-gray-900">{alert.account_name || "Unknown"}</p>
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
          <div className="px-8 py-5 border-t border-gray-200 bg-gray-50 flex justify-between items-center">
            <button
              onClick={() => setShowModal(false)}
              className="px-5 py-2.5 border-2 border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-white transition"
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

  const BikeHistoryModal = () => {
    const [bikeHistory, setBikeHistory] = useState(null);
    const [loadingHistory, setLoadingHistory] = useState(false);
    const [newNote, setNewNote] = useState("");
    const [addingNote, setAddingNote] = useState(false);
    const [isTyping, setIsTyping] = useState(false);

    useEffect(() => {
      if (showBikeHistory && selectedBikeId) {
        loadBikeHistory();
      }
    }, [showBikeHistory, selectedBikeId]);

    // Auto-refresh bike history every 60 seconds (only if not typing)
    useEffect(() => {
      if (!showBikeHistory || !selectedBikeId) return;
      
      const interval = setInterval(() => {
        if (!isTyping && !addingNote) {
          loadBikeHistoryQuiet();
        }
      }, 60000);
      
      return () => clearInterval(interval);
    }, [showBikeHistory, selectedBikeId, isTyping, addingNote]);

    const loadBikeHistory = async () => {
      try {
        setLoadingHistory(true);
        const response = await api.get(`/bikes/${selectedBikeId}/history`);
        setBikeHistory(response.data);
      } catch (error) {
        console.error("Failed to load bike history:", error);
      } finally {
        setLoadingHistory(false);
      }
    };

    const loadBikeHistoryQuiet = async () => {
      try {
        // Silent refresh: updates history without loading spinner and without clearing note field
        const response = await api.get(`/bikes/${selectedBikeId}/history`);
        setBikeHistory(response.data);
      } catch (error) {
        console.error("Failed to quiet refresh bike history:", error);
      }
    };

    const handleAddNote = async () => {
      if (!newNote.trim()) return;
      
      try {
        setAddingNote(true);
        await api.post(`/bikes/${selectedBikeId}/notes`, { note: newNote });
        setNewNote("");
        await loadBikeHistory();
      } catch (error) {
        alert("Failed to add note");
      } finally {
        setAddingNote(false);
      }
    };

    if (!showBikeHistory || !selectedBikeId) return null;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" onClick={() => setShowBikeHistory(false)}>
        <div className="bg-white rounded-xl shadow-2xl max-w-5xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
          {loadingHistory ? (
            <div className="p-12 flex items-center justify-center">
              <Loader2 className="w-8 h-8 animate-spin text-gray-600" />
            </div>
          ) : bikeHistory ? (
            <>
              <div className="px-8 py-6 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="p-3 bg-gray-900 rounded-lg">
                      <Bike className="w-8 h-8 text-white" strokeWidth={2} />
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold text-gray-900">{bikeHistory.bike.tracker_name}</h2>
                      <p className="text-sm text-gray-500 mt-1">Bike History & Notes</p>
                    </div>
                  </div>
                  <button onClick={() => setShowBikeHistory(false)} className="p-2 hover:bg-gray-100 rounded-lg transition">
                    <X className="w-6 h-6 text-gray-500" />
                  </button>
                </div>
              </div>

              <div className="px-8 py-6">
                <div className="mb-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                    <MessageSquare className="w-5 h-5 mr-2 text-gray-700" />
                    Add Note
                  </h3>
                  <div className="flex space-x-3">
                    <textarea
                      value={newNote}
                      onChange={(e) => setNewNote(e.target.value)}
                      onFocus={() => setIsTyping(true)}
                      onBlur={() => setIsTyping(false)}
                      placeholder="Enter note (e.g., called client, no issues with bike)"
                      className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none resize-none"
                      rows="3"
                    />
                    <button
                      onClick={handleAddNote}
                      disabled={addingNote || !newNote.trim()}
                      className="px-6 py-3 bg-gray-900 text-white font-medium rounded-lg hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {addingNote ? <Loader2 className="w-5 h-5 animate-spin" /> : "Add"}
                    </button>
                  </div>
                </div>

                <div className="space-y-6">
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                    <Clock className="w-5 h-5 mr-2 text-gray-700" />
                    History Timeline
                  </h3>

                  {bikeHistory.notes.length === 0 && bikeHistory.alerts.length === 0 ? (
                    <p className="text-gray-500 text-center py-8">No history available</p>
                  ) : (
                    <div className="space-y-4">
                      {[...bikeHistory.notes.map(note => ({ ...note, type: 'note' })), 
                        ...bikeHistory.alerts.map(alert => ({ ...alert, type: 'alert' }))]
                        .sort((a, b) => new Date(b.created_at || b.alert_time) - new Date(a.created_at || a.alert_time))
                        .map((item, idx) => (
                          <div key={idx} className={`p-5 rounded-xl border-2 ${item.type === 'note' ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200'}`}>
                            <div className="flex items-start justify-between">
                              <div className="flex items-start space-x-3 flex-1">
                                <div className={`p-2 rounded-lg ${item.type === 'note' ? 'bg-blue-100' : 'bg-gray-200'}`}>
                                  {item.type === 'note' ? (
                                    <MessageSquare className="w-5 h-5 text-blue-600" />
                                  ) : (
                                    <AlertTriangle className="w-5 h-5 text-gray-600" />
                                  )}
                                </div>
                                <div className="flex-1">
                                  <div className="flex items-center justify-between">
                                    <h4 className="text-base font-bold text-gray-900">
                                      {item.type === 'note' ? 'Note' : item.alert_type}
                                    </h4>
                                    <span className="text-xs text-gray-500">
                                      {formatUKTimestamp(item.created_at || item.alert_time)}
                                    </span>
                                  </div>
                                  <p className="text-sm text-gray-700 mt-2">
                                    {item.type === 'note' ? item.note : (item.location || 'No location')}
                                  </p>
                                  {item.type === 'note' && item.author && (
                                    <p className="text-xs text-gray-500 mt-1">By: {item.author}</p>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="px-8 py-5 border-t border-gray-200 bg-gray-50">
                <button
                  onClick={() => setShowBikeHistory(false)}
                  className="px-5 py-2.5 border-2 border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-white transition"
                >
                  Close
                </button>
              </div>
            </>
          ) : null}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gray-50 flex overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 overflow-y-auto">
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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
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
