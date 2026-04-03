package com.errorzero.conv.repository;

import com.errorzero.conv.domain.Product;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

import java.util.List;

public interface ProductRepositoryCustom {
    long countActiveProducts();

    long countLowStockProducts(int threshold);

    Page<Product> findInventoryPage(String keyword, String category, String sort, Pageable pageable);

    List<String> findActiveCategories();
}
