import { useState } from "react";
import "./LoginPage.css";

function LoginPage({ onLogin }) {
  const [form, setForm] = useState({
    id: "",
    password: "",
  });
  const [error, setError] = useState("");

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (error) setError("");
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!form.id.trim()) {
      setError("아이디를 입력해주세요.");
      return;
    }

    if (!form.password.trim()) {
      setError("비밀번호를 입력해주세요.");
      return;
    }

    onLogin(form);
  };

  return (
    <div className="login-page">
      <div className="login-overlay" />

      <div className="login-top-logo">
        <span className="logo-dot" aria-hidden="true" />
        <div>
          <strong>COOPSKET</strong>
          <p>IT Convenience Store</p>
        </div>
      </div>

      <div className="login-shell">
        <section className="login-hero">
          <h1>수요예측 및 발주 추천 시스템</h1>
          <p>
            재고, 수요 예측, 발주 추천 정보를 한눈에 확인합니다.
          </p>

          <ul className="feature-list">
            <li>
              <span className="feature-icon feature-icon-forecast" aria-hidden="true" />
              <div>
                <strong>수요 예측 기반 운영</strong>
                <small>AI 예측 결과를 바탕으로 발주 판단을 지원합니다.</small>
              </div>
            </li>
            <li>
              <span className="feature-icon feature-icon-stock" aria-hidden="true" />
              <div>
                <strong>실시간 재고 가시화</strong>
                <small>부족 재고와 위험 품목을 빠르게 파악할 수 있습니다.</small>
              </div>
            </li>
            <li>
              <span className="feature-icon feature-icon-order" aria-hidden="true" />
              <div>
                <strong>발주 의사결정 최적화</strong>
                <small>추천 수량과 근거를 함께 확인해 의사결정을 돕습니다.</small>
              </div>
            </li>
          </ul>
        </section>

        <section className="login-form-wrap">
          <div className="login-box-header">
            <h2>로그인</h2>
            <p>관리자 계정으로 접속해 대시보드를 확인하세요.</p>
          </div>

          <form className="login-form" onSubmit={handleSubmit}>
            <label htmlFor="id">아이디</label>
            <input
              id="id"
              name="id"
              type="text"
              className="login-input"
              placeholder="아이디를 입력하세요"
              value={form.id}
              onChange={handleChange}
            />

            <label htmlFor="password">비밀번호</label>
            <input
              id="password"
              name="password"
              type="password"
              className="login-input"
              placeholder="비밀번호를 입력하세요"
              value={form.password}
              onChange={handleChange}
            />

            {error && <p className="login-error">{error}</p>}

            <button type="submit" className="login-button">
              로그인
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}

export default LoginPage;
