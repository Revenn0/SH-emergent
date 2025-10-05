import React, { useState, useEffect } from "react";
import "@/App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API
});

function App() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [gmailEmail, setGmailEmail] = useState("");
  const [appPassword, setAppPassword] = useState("");
  const [connectLoading, setConnectLoading] = useState(false);

  const loadStats = async () => {
    try {
      const response = await api.get("/dashboard/stats");
      setStats(response.data);
      
      if (!response.data.connected) {
        setShowConnectModal(true);
      }
    } catch (error) {
      console.error("Failed to load stats:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleConnectGmail = async (e) => {
    e.preventDefault();
    setConnectLoading(true);
    
    try {
      await api.post("/gmail/connect", {
        email: gmailEmail,
        app_password: appPassword
      });
      
      setShowConnectModal(false);
      alert("Gmail conectado com sucesso!");
      loadStats();
    } catch (error) {
      alert(error.response?.data?.detail || "Falha ao conectar Gmail");
    } finally {
      setConnectLoading(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const response = await api.post("/gmail/sync");
      alert(`${response.data.categorized} emails categorizados!`);
      loadStats();
    } catch (error) {
      alert(error.response?.data?.detail || "Falha na sincronização");
    } finally {
      setSyncing(false);
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm("Desconectar Gmail?")) return;
    
    try {
      await api.delete("/gmail/disconnect");
      alert("Gmail desconectado");
      loadStats();
    } catch (error) {
      alert("Falha ao desconectar");
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const categoryColors = {
    Primary: "bg-blue-500",
    Social: "bg-green-500",
    Promotions: "bg-yellow-500",
    Updates: "bg-purple-500",
    Spam: "bg-red-500"
  };

  const categoryIcons = {
    Primary: "⭐",
    Social: "👥",
    Promotions: "🎁",
    Updates: "📬",
    Spam: "🚫"
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div className="flex items-center">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center mr-3">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <h1 className="text-2xl font-bold text-gray-900">Email Categorizer</h1>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className={`w-3 h-3 rounded-full mr-3 ${stats.connected ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`}></div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  {stats.connected ? 'Gmail Conectado' : 'Gmail Desconectado'}
                </h2>
                {stats.connected && (
                  <p className="text-sm text-gray-600">{stats.email}</p>
                )}
              </div>
            </div>
            <div className="flex gap-2">
              {stats.connected ? (
                <>
                  <button
                    onClick={handleSync}
                    disabled={syncing}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 flex items-center"
                  >
                    {syncing ? (
                      <>
                        <svg className="animate-spin h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Sincronizando...
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Sincronizar
                      </>
                    )}
                  </button>
                  <button
                    onClick={handleDisconnect}
                    className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition"
                  >
                    Desconectar
                  </button>
                </>
              ) : (
                <button
                  onClick={() => setShowConnectModal(true)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                >
                  Conectar Gmail
                </button>
              )}
            </div>
          </div>
          
          {stats.last_sync && (
            <p className="text-xs text-gray-500 mt-2">
              Última sincronização: {new Date(stats.last_sync).toLocaleString('pt-BR')}
            </p>
          )}
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
          <div className="bg-white rounded-xl shadow-sm p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Total de Emails</p>
                <p className="text-3xl font-bold text-gray-900">{stats.total_emails}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 19v-8.93a2 2 0 01.89-1.664l7-4.666a2 2 0 012.22 0l7 4.666A2 2 0 0121 10.07V19M3 19a2 2 0 002 2h14a2 2 0 002-2M3 19l6.75-4.5M21 19l-6.75-4.5M3 10l6.75 4.5M21 10l-6.75 4.5m0 0l-1.14.76a2 2 0 01-2.22 0l-1.14-.76" />
                </svg>
              </div>
            </div>
          </div>

          {Object.entries(stats.categories).map(([category, count]) => (
            <div key={category} className="bg-white rounded-xl shadow-sm p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 mb-1 flex items-center">
                    <span className="mr-2">{categoryIcons[category]}</span>
                    {category}
                  </p>
                  <p className="text-3xl font-bold text-gray-900">{count}</p>
                </div>
                <div className={`w-12 h-12 ${categoryColors[category]} opacity-20 rounded-full`}></div>
              </div>
            </div>
          ))}
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Emails Recentes</h2>
          <div className="space-y-3">
            {stats.recent_emails.length === 0 ? (
              <p className="text-gray-500 text-center py-8">Nenhum email categorizado ainda</p>
            ) : (
              stats.recent_emails.map((email, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`px-2 py-1 text-xs font-semibold text-white rounded ${categoryColors[email.category]}`}>
                          {categoryIcons[email.category]} {email.category}
                        </span>
                        <span className="text-xs text-gray-500">
                          {email.date ? new Date(email.date).toLocaleDateString('pt-BR') : ''}
                        </span>
                      </div>
                      <h3 className="text-sm font-semibold text-gray-900 truncate">{email.subject}</h3>
                      <p className="text-xs text-gray-600 truncate">{email.sender}</p>
                      <p className="text-xs text-gray-500 mt-1 truncate">{email.snippet}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </main>

      {showConnectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Conectar Gmail</h2>
            
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <p className="text-sm text-blue-900 font-semibold mb-2">📌 Como gerar uma senha de app:</p>
              <ol className="text-xs text-blue-800 space-y-1 list-decimal list-inside">
                <li>Acesse: myaccount.google.com/security</li>
                <li>Ative a verificação em 2 etapas</li>
                <li>Busque por "Senhas de app"</li>
                <li>Gere uma nova senha para "Mail"</li>
                <li>Cole a senha abaixo</li>
              </ol>
            </div>

            <form onSubmit={handleConnectGmail}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email do Gmail
                </label>
                <input
                  type="email"
                  value={gmailEmail}
                  onChange={(e) => setGmailEmail(e.target.value)}
                  placeholder="seu-email@gmail.com"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Senha de App
                </label>
                <input
                  type="password"
                  value={appPassword}
                  onChange={(e) => setAppPassword(e.target.value)}
                  placeholder="xxxx xxxx xxxx xxxx"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
              </div>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowConnectModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={connectLoading}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
                >
                  {connectLoading ? "Conectando..." : "Conectar"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
