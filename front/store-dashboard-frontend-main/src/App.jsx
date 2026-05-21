import { useEffect, useState } from "react";
import LoginPage from "./LoginPage";
import DashboardPage from "./DashboardPage";
import { clearAuthToken, fetchCurrentUser, getAuthToken, loginAdmin, setAuthToken } from "./api/api";

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [isLoginLoading, setIsLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const restoreSession = async () => {
      if (!getAuthToken()) {
        setIsCheckingAuth(false);
        return;
      }

      try {
        await fetchCurrentUser();
        if (!cancelled) {
          setIsLoggedIn(true);
        }
      } catch {
        clearAuthToken();
        if (!cancelled) {
          setIsLoggedIn(false);
        }
      } finally {
        if (!cancelled) {
          setIsCheckingAuth(false);
        }
      }
    };

    restoreSession();

    return () => {
      cancelled = true;
    };
  }, []);

  const handleLogin = async ({ id, password }) => {
    setIsLoginLoading(true);
    setLoginError("");

    try {
      const response = await loginAdmin({ id, password });
      setAuthToken(response.accessToken);
      setIsLoggedIn(true);
    } catch (error) {
      clearAuthToken();
      setLoginError(error.message || "로그인에 실패했습니다.");
    } finally {
      setIsLoginLoading(false);
    }
  };

  const handleLogout = () => {
    clearAuthToken();
    setIsLoggedIn(false);
  };

  if (isCheckingAuth) {
    return null;
  }

  return (
    <>
      {isLoggedIn ? (
        <DashboardPage onLogout={handleLogout} />
      ) : (
        <LoginPage onLogin={handleLogin} isLoading={isLoginLoading} serverError={loginError} />
      )}
    </>
  );
}

export default App;
