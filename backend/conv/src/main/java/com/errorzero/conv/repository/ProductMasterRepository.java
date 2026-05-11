package com.errorzero.conv.repository;

import com.errorzero.conv.domain.ProductMaster;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Collection;
import java.util.List;

public interface ProductMasterRepository extends JpaRepository<ProductMaster, Long> {

    List<ProductMaster> findAllByPluCodeIn(Collection<String> pluCodes);

    @Modifying
    @Query(value = """
            INSERT INTO product_master (plu_code, product_name, category, source_file, updated_at)
            VALUES (:pluCode, :productName, :category, :sourceFile, CURRENT_TIMESTAMP)
            ON CONFLICT (plu_code) DO UPDATE
            SET product_name = EXCLUDED.product_name,
                category = EXCLUDED.category,
                source_file = EXCLUDED.source_file,
                updated_at = CURRENT_TIMESTAMP
            """, nativeQuery = true)
    int upsertMasterProduct(@Param("pluCode") String pluCode,
                            @Param("productName") String productName,
                            @Param("category") String category,
                            @Param("sourceFile") String sourceFile);
}
