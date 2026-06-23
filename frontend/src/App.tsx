import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import { ConfirmProvider } from "./context/ConfirmContext";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Upload from "./pages/Upload";
import Analysis from "./pages/Analysis";
import Report from "./pages/Report";
import Admin from "./pages/Admin";
import History from "./pages/History";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ToastProvider>
          <ConfirmProvider>
            <BrowserRouter>
              <Routes>
                <Route element={<Layout />}>
                  <Route path="/admin" element={<Admin />} />
                  <Route path="/" element={<Landing />} />
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />
                  <Route
                    path="/upload"
                    element={
                      <ProtectedRoute>
                        <Upload />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/analysis/:id"
                    element={
                      <ProtectedRoute>
                        <Analysis />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/report/:id"
                    element={
                      <ProtectedRoute>
                        <Report />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/history"
                    element={
                      <ProtectedRoute>
                        <History />
                      </ProtectedRoute>
                    }
                  />
                  <Route path="*" element={<NotFound />} />
                </Route>
              </Routes>
            </BrowserRouter>
          </ConfirmProvider>
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
