package com.errorzero.conv.repository;

import com.errorzero.conv.domain.DailySales;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDate;
import java.util.Collection;
import java.util.List;
import java.util.Optional;

public interface DailySalesRepository extends JpaRepository<DailySales, Long> {

    @Query("select d.pluCode from DailySales d where d.salesDate = :salesDate and d.pluCode in :pluCodes")
    List<String> findExistingPluCodes(@Param("salesDate") LocalDate salesDate, @Param("pluCodes") Collection<String> pluCodes);

    @Query("select max(d.salesDate) from DailySales d")
    Optional<LocalDate> findLatestSalesDate();

    @Query(value = """
            SELECT
                p.plu_code AS "pluCode",
                p.name AS name,
                p.category AS category
            FROM daily_sales d
            JOIN product p ON p.plu_code = d.plu_code
            WHERE d.sales_date = :salesDate
              AND p.is_active = true
              AND (
                    (:category IS NOT NULL AND p.category = :category)
                    OR (:keyword IS NOT NULL AND p.name ILIKE CONCAT('%', :keyword, '%'))
              )
            GROUP BY p.plu_code, p.name, p.category
            ORDER BY p.name ASC
            """, nativeQuery = true)
    List<StudentProductCandidateProjection> findStudentProductCandidates(
            @Param("salesDate") LocalDate salesDate,
            @Param("category") String category,
            @Param("keyword") String keyword
    );

    @Query(value = """
            SELECT
                p.plu_code AS "pluCode",
                p.name AS name,
                COALESCE(p.current_stock, 0) AS "currentStock",
                COALESCE(SUM(d.sales_qty), 0) AS "salesQty"
            FROM daily_sales d
            JOIN product p ON p.plu_code = d.plu_code
            WHERE d.updated_at = (
                    SELECT MAX(latest.updated_at)
                    FROM daily_sales latest
                  )
              AND p.is_active = true
              AND d.sales_qty > 0
            GROUP BY p.plu_code, p.name, p.current_stock
            ORDER BY COALESCE(SUM(d.sales_qty), 0) DESC, p.name ASC
            LIMIT :limit
            """, nativeQuery = true)
    List<TopSalesProductProjection> findTopSellingProductsByLatestUpload(
            @Param("limit") int limit
    );

    @Modifying
    @Query(value = """
            INSERT INTO daily_sales (sales_date, plu_code, sales_qty, updated_at)
            VALUES (:salesDate, :pluCode, :salesQty, CURRENT_TIMESTAMP)
            ON CONFLICT (sales_date, plu_code)
            DO UPDATE SET
                sales_qty = EXCLUDED.sales_qty,
                updated_at = CURRENT_TIMESTAMP
            """, nativeQuery = true)
    int upsert(@Param("salesDate") LocalDate salesDate,
               @Param("pluCode") String pluCode,
               @Param("salesQty") int salesQty);
}
