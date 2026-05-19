import StudentRequestPanel from "./StudentRequestPanel";

function StudentRequestPage() {
  return (
    <section className="requests-page">
      <StudentRequestPanel
        limit={500}
        title="학생 신청 목록"
        subtitle="최신순 최대 500건 자동 갱신"
        className="student-request-detail-panel"
      />
    </section>
  );
}

export default StudentRequestPage;
