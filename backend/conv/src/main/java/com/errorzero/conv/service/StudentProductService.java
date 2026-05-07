package com.errorzero.conv.service;

import com.errorzero.conv.domain.Product;
import com.errorzero.conv.dto.StudentProductResponseDto;
import com.errorzero.conv.dto.StudentRequestCreateDto;
import com.errorzero.conv.dto.StudentRequestDashboardResponseDto;
import com.errorzero.conv.dto.StudentRequestResponseDto;
import com.errorzero.conv.repository.DailySalesRepository;
import com.errorzero.conv.repository.ProductRepository;
import com.errorzero.conv.repository.StudentProductRequestRepository;
import com.errorzero.conv.repository.StudentRequestDashboardProjection;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class StudentProductService {

    private static final int DEFAULT_DASHBOARD_LIMIT = 100;
    private static final int MAX_DASHBOARD_LIMIT = 500;

    private final DailySalesRepository dailySalesRepository;
    private final ProductRepository productRepository;
    private final StudentProductRequestRepository studentProductRequestRepository;

    @Transactional(readOnly = true)
    public List<StudentProductResponseDto> getStudentProducts(LocalDate salesDate, String category, String keyword) {
        String safeCategory = normalize(category);
        String safeKeyword = normalize(keyword);

        return findStudentProducts(safeCategory, safeKeyword)
                .stream()
                .map(this::toStudentProductResponse)
                .toList();
    }

    @Transactional(readOnly = true)
    public List<StudentRequestDashboardResponseDto> getDashboardRequests(int limit, String studentId) {
        int safeLimit = limit > 0 ? Math.min(limit, MAX_DASHBOARD_LIMIT) : DEFAULT_DASHBOARD_LIMIT;
        String safeStudentId = normalize(studentId);

        return studentProductRequestRepository.findDashboardRequests(safeLimit, safeStudentId)
                .stream()
                .map(this::toDashboardResponse)
                .toList();
    }

    @Transactional
    public StudentRequestResponseDto submitRequest(StudentRequestCreateDto request) {
        String studentId = request.getStudentId().trim();
        LocalDate salesDate = resolveSalesDate(request.getSalesDate());
        List<StudentRequestCreateDto.ItemDto> items = request.getItems();

        Set<String> pluCodes = normalizePluCodes(items);
        validateNoDuplicatePluCodes(items, pluCodes);
        validateActiveProducts(pluCodes);

        int totalQuantity = 0;
        for (StudentRequestCreateDto.ItemDto item : items) {
            String pluCode = item.getPluCode().trim();
            int quantity = item.getQuantity();
            studentProductRequestRepository.upsert(studentId, salesDate, pluCode, quantity);
            totalQuantity += quantity;
        }

        return StudentRequestResponseDto.builder()
                .studentId(studentId)
                .salesDate(salesDate)
                .itemCount(items.size())
                .totalQuantity(totalQuantity)
                .message("학생 상품 신청이 저장되었습니다.")
                .build();
    }

    @Transactional
    public void deleteRequest(String studentId, LocalDate salesDate, String pluCode) {
        String safeStudentId = normalize(studentId);
        String safePluCode = normalize(pluCode);

        if (safeStudentId == null) {
            throw new IllegalArgumentException("studentId는 필수입니다");
        }
        if (safePluCode == null) {
            throw new IllegalArgumentException("pluCode는 필수입니다");
        }

        studentProductRequestRepository.deleteRequest(
                safeStudentId,
                resolveSalesDate(salesDate),
                safePluCode
        );
    }

    private StudentProductResponseDto toStudentProductResponse(Product product) {
        return new StudentProductResponseDto(
                product.getPluCode(),
                product.getName(),
                product.getCategory()
        );
    }

    private List<Product> findStudentProducts(String category, String keyword) {
        if (category == null && keyword == null) {
            return productRepository.findAllByIsActiveTrueOrderByCategoryAscNameAsc();
        }

        if (keyword == null) {
            return productRepository.findAllByIsActiveTrueAndCategoryOrderByCategoryAscNameAsc(category);
        }

        if (category == null) {
            return productRepository.searchStudentProductsByKeyword(keyword);
        }

        return productRepository.searchStudentProductsByCategoryAndKeyword(category, keyword);
    }

    private StudentRequestDashboardResponseDto toDashboardResponse(StudentRequestDashboardProjection projection) {
        int quantity = projection.getQuantity() != null ? projection.getQuantity() : 0;
        return new StudentRequestDashboardResponseDto(
                projection.getStudentId(),
                projection.getSalesDate(),
                projection.getPluCode(),
                projection.getProductName(),
                quantity,
                projection.getRequestedAt()
        );
    }

    private Set<String> normalizePluCodes(List<StudentRequestCreateDto.ItemDto> items) {
        return items.stream()
                .map(StudentRequestCreateDto.ItemDto::getPluCode)
                .map(String::trim)
                .collect(Collectors.toCollection(LinkedHashSet::new));
    }

    private void validateNoDuplicatePluCodes(List<StudentRequestCreateDto.ItemDto> items, Set<String> uniquePluCodes) {
        if (items.size() != uniquePluCodes.size()) {
            throw new IllegalArgumentException("중복된 상품 신청이 포함되어 있습니다.");
        }
    }

    private void validateActiveProducts(Set<String> pluCodes) {
        Map<String, Product> productMap = productRepository.findAllByPluCodeInAndIsActiveTrue(pluCodes)
                .stream()
                .collect(Collectors.toMap(Product::getPluCode, Function.identity()));

        Set<String> missingPluCodes = new HashSet<>(pluCodes);
        missingPluCodes.removeAll(productMap.keySet());
        if (!missingPluCodes.isEmpty()) {
            throw new IllegalArgumentException("활성 상품이 아닌 PLU가 포함되어 있습니다: " + missingPluCodes);
        }
    }

    private String normalize(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }

    private LocalDate resolveSalesDate(LocalDate salesDate) {
        if (salesDate != null) {
            return salesDate;
        }

        return dailySalesRepository.findLatestSalesDate()
                .orElseThrow(() -> new IllegalStateException("신청 기준으로 사용할 daily_sales 데이터가 없습니다."));
    }
}
