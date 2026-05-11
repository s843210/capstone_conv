package com.errorzero.conv.repository;

import com.errorzero.conv.domain.Product;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Collection;
import java.util.List;
import java.util.Optional;

public interface ProductRepository extends JpaRepository<Product, Long>, ProductRepositoryCustom {

    Optional<Product> findByPluCode(String pluCode);

    List<Product> findAllByIsActiveTrue();

    Page<Product> findAllByIsActiveTrueOrderByCurrentStockAsc(Pageable pageable);

    List<Product> findAllByIsActiveTrueAndCurrentStockLessThanOrderByCurrentStockAsc(int currentStock, Pageable pageable);

    List<Product> findAllByPluCodeInAndIsActiveTrue(Collection<String> pluCodes);

    @Modifying
    @Query("""
            UPDATE Product p
            SET p.currentStock = :currentStock,
                p.updatedAt = CURRENT_TIMESTAMP
            WHERE p.pluCode = :pluCode
              AND p.isActive = true
            """)
    int updateCurrentStockByPluCode(@Param("pluCode") String pluCode,
                                    @Param("currentStock") int currentStock);

    @Modifying
    @Query(value = """
            INSERT INTO product (plu_code, name, category, current_stock, is_active, updated_at)
            VALUES (:pluCode, :name, :category, :currentStock, true, CURRENT_TIMESTAMP)
            ON CONFLICT (plu_code) DO UPDATE
            SET name = EXCLUDED.name,
                category = EXCLUDED.category,
                current_stock = EXCLUDED.current_stock,
                is_active = true,
                updated_at = CURRENT_TIMESTAMP
            """, nativeQuery = true)
    int upsertFromInventory(@Param("pluCode") String pluCode,
                            @Param("name") String name,
                            @Param("category") String category,
                            @Param("currentStock") int currentStock);

    List<Product> findAllByIsActiveTrueOrderByCategoryAscNameAsc();

    List<Product> findAllByIsActiveTrueAndCategoryOrderByCategoryAscNameAsc(String category);

    @Query("""
            SELECT p
            FROM Product p
            WHERE p.isActive = true
              AND (
                    LOWER(p.name) LIKE LOWER(CONCAT('%', :keyword, '%'))
                    OR LOWER(p.pluCode) LIKE LOWER(CONCAT('%', :keyword, '%'))
              )
            ORDER BY p.category ASC, p.name ASC
            """)
    List<Product> searchStudentProductsByKeyword(@Param("keyword") String keyword);

    @Query("""
            SELECT p
            FROM Product p
            WHERE p.isActive = true
              AND p.category = :category
              AND (
                    LOWER(p.name) LIKE LOWER(CONCAT('%', :keyword, '%'))
                    OR LOWER(p.pluCode) LIKE LOWER(CONCAT('%', :keyword, '%'))
              )
            ORDER BY p.category ASC, p.name ASC
            """)
    List<Product> searchStudentProductsByCategoryAndKeyword(@Param("category") String category,
                                                            @Param("keyword") String keyword);
}
