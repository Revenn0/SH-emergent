import React, { useState, useEffect, useMemo, useCallback } from "react";
import "@/App.css";
import axios from "axios";
import { 
  Bell, Settings, LayoutDashboard, LogOut, Menu, X, Trash2, 
  AlertTriangle, Database, Mail, Activity, Bike, CheckCircle, 
  XCircle, Clock, MapPin, Info, Moon, Sun, Search, Star, UserPlus, 
  MessageSquare, CheckCircle2
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API
});

function LoginPage({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await api.post("/auth/login", { username, password });
      if (response.data.success) {
        onLogin(response.data.user);
      } else {
        setError("Invalid credentials");
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed");
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
            <p className="text-sm text-gray-600">Sign in to access the dashboard</p>
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
              {loading ? "Signing in..." : "Sign in"}
            </button>

            <div className="mt-6 pt-6 border-t border-gray-200 text-center">
              <p className="text-xs text-gray-500 mb-1">Demo Credentials:</p>
              <p className="text-xs text-gray-600">Username: admin</p>
              <p className="text-xs text-gray-600">Password: admin</p>
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
  const [stats, setStats] = useState({
    total: 0,
    unread: 0,
    highPriority: 0,
    acknowledged: 0,
    categories: {}
  });
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
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
    if (selectedCategory !== "All") {
      loadAlerts(selectedCategory);
    } else {
      loadAlerts();
    }
  }, [selectedCategory]);

  useEffect(() => {
    let interval;
    if (autoRefresh && gmailConnected) {
      interval = setInterval(() => {
        loadAlerts(selectedCategory !== "All" ? selectedCategory : null);
      }, 30000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh, gmailConnected, selectedCategory]);

  const loadCategories = async () => {
    try {
      const response = await api.get("/alerts/categories");
      setCategories(["All", ...response.data.categories]);
    } catch (error) {
      console.error("Failed to load categories:", error);
    }
  };

  const loadAlerts = async (category = null) => {
    try {
      const url = category && category !== "All" 
        ? `/alerts/list?category=${encodeURIComponent(category)}`
        : "/alerts/list";
      
      const response = await api.get(url);
      setAlerts(response.data.alerts);
      setStats(response.data.stats);
      setGmailConnected(response.data.connected);
      setGmailEmail(response.data.email || "");
      
      groupAlertsByDevice(response.data.alerts);
    } catch (error) {
      console.error("Failed to load alerts:", error);
    } finally {
      setLoading(false);
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
    });

    Object.values(grouped).forEach(group => {
      const alertTypes = new Set(group.alerts.map(a => a.alert_type));
      
      const hasLightSensor = alertTypes.has("Light Sensor");
      const hasOverTurn = alertTypes.has("Over-turn");
      const hasHeavyImpact = Array.from(alertTypes).some(t => t && t.includes("Heavy Impact"));
      const hasNoCommunication = Array.from(alertTypes).some(t => t && t.includes("No Communication"));
      
      if (hasLightSensor && hasOverTurn) {
        group.severity = "heavy-impact";
        group.displayName = "Heavy Impact";
      } else if (hasOverTurn || hasHeavyImpact || hasNoCommunication) {
        group.severity = "high";
      } else {
        group.severity = "normal";
      }
    });

    setGroupedAlerts(Object.values(grouped).sort((a, b) => {
      if (a.severity === "heavy-impact" && b.severity !== "heavy-impact") return -1;
      if (b.severity === "heavy-impact" && a.severity !== "heavy-impact") return 1;
      if (a.severity === "high" && b.severity === "normal") return -1;
      if (b.severity === "high" && a.severity === "normal") return 1;
      return b.count - a.count;
    }));
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      await api.post("/alerts/sync", { limit: emailLimit });
      await loadAlerts();
      alert("Sync completed!");
    } catch (error) {
      alert(error.response?.data?.detail || "Sync failed");
    } finally {
      setSyncing(false);
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

  const handleClearHistory = async () => {
    if (!window.confirm("⚠️ Limpar TODO o histórico?\n\nIsto irá:\n- Deletar todos os alertas\n- Resetar checkpoint de sincronização\n- Começar do zero\n\nNão pode ser desfeito!")) return;
    
    try {
      await api.delete("/alerts/clear-all/history");
      await loadAlerts();
      alert("✓ Histórico limpo com sucesso! Sistema resetado.");
    } catch (error) {
      alert("Erro ao limpar histórico");
    }
  };

  const openAlertModal = (group) => {
    setSelectedAlert(group);
    setShowModal(true);
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

  const Header = () => (
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
            onClick={handleSync}
            disabled={syncing || !gmailConnected}
            className="flex items-center space-x-2 px-4 py-2 bg-gray-900 text-white rounded-md hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed text-sm"
          >
            <Activity className="w-4 h-4" />
            <span>{syncing ? "Syncing..." : "Refresh Alerts"}</span>
          </button>
        </div>
      </div>
    </header>
  );

  const DashboardPage = () => {
    const getSeverityBadge = (severity) => {
      if (severity === "heavy-impact") return "bg-red-100 text-red-700 border-red-200";
      if (severity === "high") return "bg-orange-100 text-orange-700 border-orange-200";
      return "bg-gray-100 text-gray-700 border-gray-200";
    };

    const getCountBadge = (count) => {
      if (count >= 3) return "3+";
      return count.toString();
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

          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600">Unread</p>
              <Info className="w-4 h-4 text-gray-400" />
            </div>
            <p className="text-2xl font-semibold text-gray-900">{stats.unread || 0}</p>
            <p className="text-xs text-gray-500 mt-1">Requires attention</p>
          </div>

          <div className="bg-white rounded-lg border border-red-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600">Heavy Impact</p>
              <AlertTriangle className="w-4 h-4 text-red-600" />
            </div>
            <p className="text-2xl font-semibold text-red-700">
              {stats.heavyImpact || 0}
            </p>
            <p className="text-xs text-gray-500 mt-1">Light Sensor + Over-turn</p>
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
          <div className="bg-white rounded-lg border border-red-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600">Over-Turn</p>
              <AlertTriangle className="w-4 h-4 text-red-600" />
            </div>
            <p className="text-2xl font-semibold text-red-700">{stats.overTurn || 0}</p>
            <p className="text-xs text-gray-500 mt-1">Over-turn alerts</p>
          </div>

          <div className="bg-white rounded-lg border border-orange-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600">No Communication</p>
              <XCircle className="w-4 h-4 text-orange-600" />
            </div>
            <p className="text-2xl font-semibold text-orange-700">{stats.noCommunication || 0}</p>
            <p className="text-xs text-gray-500 mt-1">Connection lost</p>
          </div>

          <div className="bg-white rounded-lg border border-purple-200 p-4">
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
              </div>
              <div className="flex items-center space-x-2">
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
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-600">Status</th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-600">Device</th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-600">Type</th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-600">Category</th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-600">Message</th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-600">Severity</th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-600">Timestamp</th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-600">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {groupedAlerts.filter(group => 
                    !searchQuery || group.device.toLowerCase().includes(searchQuery.toLowerCase())
                  ).length === 0 ? (
                    <tr>
                      <td colSpan="8" className="text-center py-12 text-sm text-gray-500">
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
                          <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border ${getSeverityBadge(group.severity)}`}>
                            {group.severity === "heavy-impact" ? "Critical" : "Active"}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center space-x-2">
                            <span className="text-sm font-semibold text-gray-900">{group.device}</span>
                            <span className="inline-flex items-center justify-center w-5 h-5 bg-gray-900 text-white text-xs font-bold rounded">
                              {getCountBadge(group.count)}
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-sm text-gray-700">{group.latestAlert.alert_type}</td>
                        <td className="py-3 px-4">
                          <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                            group.severity === "heavy-impact" ? "bg-red-100 text-red-700" :
                            group.severity === "high" ? "bg-orange-100 text-orange-700" :
                            "bg-blue-100 text-blue-700"
                          }`}>
                            {group.severity === "heavy-impact" ? "Heavy Impact" : 
                             group.severity === "high" ? "High Priority" : "Normal"}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-sm text-gray-600 truncate max-w-xs">
                          {group.latestAlert.location || "No location"}
                        </td>
                        <td className="py-3 px-4">
                          <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                            group.severity === "heavy-impact" ? "bg-red-100 text-red-700" :
                            group.severity === "high" ? "bg-orange-100 text-orange-700" :
                            "bg-gray-100 text-gray-700"
                          }`}>
                            {group.severity === "heavy-impact" ? "High" : 
                             group.severity === "high" ? "Medium" : "Low"}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-xs text-gray-500">
                          {group.latestAlert.alert_time || "Unknown"}
                        </td>
                        <td className="py-3 px-4">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteAlert(group.latestAlert.id);
                            }}
                            className="p-1 text-red-600 hover:bg-red-50 rounded transition"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const AdminPage = () => (
    <div className="p-6 space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-gray-600">System Status</p>
            <Activity className="w-4 h-4 text-gray-400" />
          </div>
          <div className="flex items-center space-x-2">
            <XCircle className="w-5 h-5 text-red-500" />
            <span className="text-lg font-semibold text-red-600">Error</span>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-gray-600">Database</p>
            <Database className="w-4 h-4 text-gray-400" />
          </div>
          <div className="flex items-center space-x-2">
            <CheckCircle className="w-5 h-5 text-green-500" />
            <span className="text-lg font-semibold text-green-600">Connected</span>
          </div>
          <p className="text-xs text-gray-500 mt-1">Neon PostgreSQL</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-gray-600">Gmail Integration</p>
            <Mail className="w-4 h-4 text-gray-400" />
          </div>
          <div className="flex items-center space-x-2">
            {gmailConnected ? (
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
          <p className="text-xs text-gray-500 mt-1">{gmailConnected ? "Connected" : "Token expired or missing"}</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-gray-600">Total Alerts</p>
            <Activity className="w-4 h-4 text-gray-400" />
          </div>
          <p className="text-2xl font-semibold text-gray-900">{stats.total}</p>
          <p className="text-xs text-gray-500 mt-1">0 unread</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-1">Last Sync Status</h3>
          <p className="text-xs text-gray-500 mb-4">Most recent email synchronization</p>
          <p className="text-sm text-gray-600">No sync history available</p>
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
              onChange={(e) => setSyncInterval(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-1 focus:ring-gray-900 focus:border-gray-900 outline-none text-sm"
              min="1"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">
              Email Limit per Sync
            </label>
            <input
              type="number"
              value={emailLimit}
              onChange={(e) => setEmailLimit(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-1 focus:ring-gray-900 focus:border-gray-900 outline-none text-sm"
              min="1"
              max="200"
            />
          </div>
        </div>
        <button className="mt-4 px-4 py-2 bg-gray-900 text-white rounded-md hover:bg-gray-800 transition text-sm">
          Save Configuration
        </button>
      </div>

      <div className="bg-white rounded-lg border border-red-200 p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-2">Danger Zone</h3>
        <p className="text-xs text-gray-500 mb-4">Ações irreversíveis - use com cuidado</p>
        <div className="flex items-center justify-between p-4 bg-red-50 border border-red-200 rounded-md">
          <div>
            <p className="text-sm font-medium text-red-900">Limpar Todo Histórico</p>
            <p className="text-xs text-red-700 mt-0.5">Deleta todos os alertas e reseta checkpoint de sincronização</p>
          </div>
          <button
            onClick={handleClearHistory}
            className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700 transition"
          >
            <Trash2 className="inline w-4 h-4 mr-1" />
            Limpar Tudo
          </button>
        </div>
      </div>
    </div>
  );

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

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" onClick={() => setShowModal(false)}>
        <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">Alert Details</h2>
                <p className="text-sm text-gray-500 mt-1">Device: {selectedAlert.device}</p>
              </div>
              <button onClick={() => setShowModal(false)} className="p-2 hover:bg-gray-100 rounded-lg transition">
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          <div className="p-6 space-y-6">
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div>
                <p className="text-xs text-gray-600 mb-1">Alert Count</p>
                <p className="text-2xl font-bold text-gray-900">{selectedAlert.count}</p>
              </div>
              <div className={`px-4 py-2 rounded-lg ${
                selectedAlert.severity === "heavy-impact" ? "bg-red-100 text-red-700" :
                selectedAlert.severity === "high" ? "bg-orange-100 text-orange-700" :
                "bg-blue-100 text-blue-700"
              }`}>
                <p className="text-xs font-medium">
                  {selectedAlert.severity === "heavy-impact" ? "HEAVY IMPACT" :
                   selectedAlert.severity === "high" ? "HIGH PRIORITY" : "NORMAL"}
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {selectedAlert.alerts.map((alert, idx) => (
                <div key={idx} className="p-4 border border-gray-200 rounded-lg space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold text-gray-900">{alert.alert_type}</h3>
                      <p className="text-xs text-gray-500 mt-1">{alert.alert_time}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-xs text-gray-600 mb-1">Location</p>
                      <p className="text-gray-900">{alert.location || "Unknown"}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-600 mb-1">Coordinates</p>
                      <p className="text-gray-900">{alert.latitude}, {alert.longitude}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-600 mb-1">Device Serial</p>
                      <p className="text-gray-900">{alert.device_serial}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-600 mb-1">Account</p>
                      <p className="text-gray-900">{alert.account_name || "Unknown"}</p>
                    </div>
                  </div>

                  {alert.latitude && alert.longitude && (
                    <div className="flex items-center space-x-2 text-xs text-blue-600">
                      <MapPin className="w-3 h-3" />
                      <a 
                        href={`https://www.google.com/maps?q=${alert.latitude},${alert.longitude}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:underline"
                      >
                        View on Google Maps
                      </a>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="p-6 border-t border-gray-200 flex justify-end space-x-3">
            <button
              onClick={() => setShowModal(false)}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition text-sm"
            >
              Close
            </button>
            <button
              onClick={() => {
                handleDeleteAlert(selectedAlert.latestAlert.id);
                setShowModal(false);
              }}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition text-sm"
            >
              Delete Alert
            </button>
          </div>
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
    <div className="min-h-screen bg-gray-50 flex">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto">
          {currentPage === "dashboard" && <DashboardPage />}
          {currentPage === "admin" && <AdminPage />}
          {currentPage === "settings" && <SettingsPage />}
        </main>
      </div>
      <AlertModal />
    </div>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }
    setLoading(false);
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem("user", JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem("user");
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
