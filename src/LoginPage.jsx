import { useState } from "react";
import "./LoginPage.css";

function LoginPage({ onLogin }) {
  // 아이디와 비밀번호 입력값을 저장하는 state
  const [form, setForm] = useState({
    id: "",
    password: "",
  });

  // 에러 메시지를 저장하는 state
  const [error, setError] = useState("");

  // input에 입력할 때 실행되는 함수
  const handleChange = (e) => {
    const { name, value } = e.target;

    // 입력한 값을 form state에 반영
    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));

    // 에러 메시지가 떠 있는 상태에서 다시 입력하면 에러 초기화
    if (error) {
      setError("");
    }
  };

  // 로그인 버튼 눌렀을 때 실행되는 함수
  const handleSubmit = (e) => {
    e.preventDefault(); // 추가: form 기본 새로고침 동작 막기

    // 아이디가 비어있으면 에러 메시지 출력
    if (!form.id.trim()) {
      setError("아이디를 입력해주세요.");
      return;
    }

    // 비밀번호가 비어있으면 에러 메시지 출력
    if (!form.password.trim()) {
      setError("비밀번호를 입력해주세요.");
      return;
    }

    // 상위 컴포넌트(App)로 입력값 전달
    onLogin(form);
  };

  return (
    <div className="login-page">
      {/* 전체 로그인 화면 레이아웃 */}
      <div className="login-layout">

        {/* 왼쪽 소개 영역 */}
        <section className="login-brand-panel">
          <p className="login-badge">Smart Store Dashboard</p>
          <h1 className="login-brand-title">스마트 편의점 운영 시스템</h1>
          <p className="login-brand-text">
            대학 내 편의점 운영자와 관리자가 재고 현황, 예측 수요,
            발주 추천 정보를 한눈에 확인할 수 있는 운영 대시보드입니다.
          </p>

          {/* 서비스 핵심 기능 소개 */}
          <ul className="login-feature-list">
            <li>실시간 재고 상태 확인</li>
            <li>AI 기반 수요 예측 정보 제공</li>
            <li>발주 판단을 돕는 추천 정보 제공</li>
          </ul>
        </section>

        {/* 수정: 기존 단순 로그인 박스를 관리자용 카드 형태로 확장 */}
        <section className="login-box">
          <div className="login-box-header">
            <p className="login-role">운영자 · 관리자 전용</p>
            <h2 className="login-title">로그인</h2>
            <p className="login-text">
              승인된 계정으로 접속해 운영 정보를 확인하세요.
            </p>
          </div>

          {/* 로그인 form */}
          <form className="login-form" onSubmit={handleSubmit}>
            <label className="login-label" htmlFor="id">
              아이디
            </label>
            <input
              id="id"
              name="id"
              type="text"
              className="login-input"
              placeholder="아이디를 입력하세요"
              value={form.id}
              onChange={handleChange}
            />

            <label className="login-label" htmlFor="password">
              비밀번호
            </label>
            <input
              id="password"
              name="password"
              type="password"
              className="login-input"
              placeholder="비밀번호를 입력하세요"
              value={form.password}
              onChange={handleChange}
            />

            {/* 에러가 있을 때만 메시지 표시 */}
            {error && <p className="login-error">{error}</p>}

            <button type="submit" className="login-button">
              로그인
            </button>
          </form>

          {/* 하단 안내 문구 */}
          <p className="login-help">
            ※ 본 페이지는 편의점 운영 담당자 전용입니다.
          </p>
        </section>
      </div>
    </div>
  );
}

export default LoginPage;