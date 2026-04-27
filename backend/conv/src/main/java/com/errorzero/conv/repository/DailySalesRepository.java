package com.errorzero.conv.repository;

import com.errorzero.conv.domain.DailySales;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDate;
import java.util.Collection;
import java.util.List;

public interface DailySalesRepository extends JpaRepository<DailySales, Long> {

    @Query("select d.pluCode from DailySales d where d.salesDate = :salesDate and d.pluCode in :pluCodes")
    List<String> findExistingPluCodes(@Param("salesDate") LocalDate salesDate, @Param("pluCodes") Collection<String> pluCodes);

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
