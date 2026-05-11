package com.errorzero.conv.repository;

import com.errorzero.conv.domain.InventorySnapshot;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDate;

public interface InventorySnapshotRepository extends JpaRepository<InventorySnapshot, Long> {

    @Modifying
    @Query(value = """
            INSERT INTO inventory_snapshot (snapshot_date, product_id, plu_code, current_stock, uploaded_at)
            VALUES (:snapshotDate, :productId, :pluCode, :currentStock, CURRENT_TIMESTAMP)
            ON CONFLICT (snapshot_date, product_id) DO UPDATE
            SET plu_code = EXCLUDED.plu_code,
                current_stock = EXCLUDED.current_stock,
                uploaded_at = CURRENT_TIMESTAMP
            """, nativeQuery = true)
    int upsertSnapshot(@Param("snapshotDate") LocalDate snapshotDate,
                       @Param("productId") Long productId,
                       @Param("pluCode") String pluCode,
                       @Param("currentStock") int currentStock);
}
