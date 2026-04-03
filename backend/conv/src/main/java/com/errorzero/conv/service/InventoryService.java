package com.errorzero.conv.service;

import com.errorzero.conv.domain.Product;
import com.errorzero.conv.dto.InventoryResponseDto;
import com.errorzero.conv.repository.ProductRepository;
import com.errorzero.conv.util.StockCalculator;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class InventoryService {

    private static final int DEFAULT_PAGE_SIZE = 30;
    private static final int MAX_PAGE_SIZE = 100;
    private static final String SORT_STOCK_ASC = "stock_asc";
    private static final String SORT_STOCK_DESC = "stock_desc";

    private final ProductRepository productRepository;

    public InventoryResponseDto getInventoryPage(int page, int size, String query, String category, String sort) {
        int safePage = Math.max(page, 0);
        int safeSize = size > 0 ? Math.min(size, MAX_PAGE_SIZE) : DEFAULT_PAGE_SIZE;
        String safeSort = normalizeSort(sort);

        Pageable pageable = PageRequest.of(safePage, safeSize);
        Page<Product> productPage = productRepository.findInventoryPage(query, category, safeSort, pageable);

        List<InventoryResponseDto.ItemDto> itemDtos = productPage.getContent().stream()
                .map(p -> new InventoryResponseDto.ItemDto(
                        p.getPluCode(),
                        p.getName(),
                        p.getCurrentStock(),
                        StockCalculator.calculateRecommendedStock(p.getCurrentStock())
                ))
                .collect(Collectors.toList());

        return InventoryResponseDto.builder()
                .items(itemDtos)
                .hasNext(productPage.hasNext())
                .currentPage(productPage.getNumber())
                .totalElements(productPage.getTotalElements())
                .build();
    }

    public List<String> getActiveCategories() {
        return productRepository.findActiveCategories();
    }

    private String normalizeSort(String sort) {
        if (SORT_STOCK_DESC.equalsIgnoreCase(sort)) {
            return SORT_STOCK_DESC;
        }
        return SORT_STOCK_ASC;
    }
}
