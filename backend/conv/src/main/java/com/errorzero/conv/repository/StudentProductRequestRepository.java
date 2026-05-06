package com.errorzero.conv.repository;

import com.errorzero.conv.domain.StudentProductRequest;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDate;
import java.util.List;

public interface StudentProductRequestRepository extends JpaRepository<StudentProductRequest, Long> {

    @Modifying
    @Query(value = """
            INSERT INTO student_product_request (student_id, sales_date, plu_code, quantity, created_at, updated_at)
            VALUES (:studentId, :salesDate, :pluCode, :quantity, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (student_id, sales_date, plu_code)
            DO UPDATE SET
                quantity = EXCLUDED.quantity,
                updated_at = CURRENT_TIMESTAMP
            """, nativeQuery = true)
    int upsert(@Param("studentId") String studentId,
               @Param("salesDate") LocalDate salesDate,
               @Param("pluCode") String pluCode,
               @Param("quantity") int quantity);

    @Query(value = """
            SELECT
                r.student_id AS "studentId",
                p.name AS "productName",
                r.quantity AS quantity,
                r.updated_at AS "requestedAt"
            FROM student_product_request r
            JOIN product p ON p.plu_code = r.plu_code
            ORDER BY r.updated_at DESC, r.id DESC
            LIMIT :limit
            """, nativeQuery = true)
    List<StudentRequestDashboardProjection> findDashboardRequests(@Param("limit") int limit);
}
