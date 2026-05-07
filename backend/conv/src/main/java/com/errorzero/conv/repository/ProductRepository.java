package com.errorzero.conv.repository;

import com.errorzero.conv.domain.Product;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
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
