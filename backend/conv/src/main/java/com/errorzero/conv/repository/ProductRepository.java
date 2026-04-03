package com.errorzero.conv.repository;

import com.errorzero.conv.domain.Product;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Collection;
import java.util.List;
import java.util.Optional;

public interface ProductRepository extends JpaRepository<Product, Long>, ProductRepositoryCustom {

    Optional<Product> findByPluCode(String pluCode);

    List<Product> findAllByIsActiveTrue();

    Page<Product> findAllByIsActiveTrueOrderByCurrentStockAsc(Pageable pageable);

    List<Product> findAllByIsActiveTrueAndCurrentStockLessThanOrderByCurrentStockAsc(int currentStock, Pageable pageable);

    List<Product> findAllByPluCodeInAndIsActiveTrue(Collection<String> pluCodes);
}
