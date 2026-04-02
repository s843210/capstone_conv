import { useState } from "react";
import LoginPage from "./LoginPage";
import DashboardPage from "./DashboardPage";

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const handleLogin = ({ id, password }) => {
    if (id.trim() && password.trim()) {
      setIsLoggedIn(true);
    }
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
  };

  return (
    <>
      {isLoggedIn ? (
        <DashboardPage onLogout={handleLogout} />
      ) : (
        <LoginPage onLogin={handleLogin} />
      )}
    </>
  );
}

export default App;
