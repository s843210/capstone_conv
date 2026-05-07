import StudentRequestPanel from "./StudentRequestPanel";

function StudentRequestPage() {
  return (
    <section className="student-request-page">
      <div className="page-section-header">
        <div>
          <h2>학생 신청 현황</h2>
          <p>학생 앱에서 접수된 상품 요청을 최신순으로 확인합니다.</p>
        </div>
      </div>
      <StudentRequestPanel
        limit={500}
        title="전체 신청 목록"
        subtitle="최신순 최대 500개 자동 갱신"
        className="student-request-detail-panel"
      />
    </section>
  );
}

export default StudentRequestPage;
