package com.errorzero.conv.service;

import com.errorzero.conv.domain.Product;
import com.errorzero.conv.dto.StudentProductResponseDto;
import com.errorzero.conv.dto.StudentRequestCreateDto;
import com.errorzero.conv.dto.StudentRequestResponseDto;
import com.errorzero.conv.repository.DailySalesRepository;
import com.errorzero.conv.repository.ProductRepository;
import com.errorzero.conv.repository.StudentProductRequestRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyCollection;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class StudentProductServiceTest {

    @Mock
    private DailySalesRepository dailySalesRepository;

    @Mock
    private ProductRepository productRepository;

    @Mock
    private StudentProductRequestRepository studentProductRequestRepository;

    private StudentProductService studentProductService;

    @BeforeEach
    void setUp() {
        studentProductService = new StudentProductService(
                dailySalesRepository,
                productRepository,
                studentProductRequestRepository
        );
    }

    @Test
    void getStudentProducts_withoutFilters_returnsActiveProducts() {
        LocalDate salesDate = LocalDate.of(2026, 4, 24);
        Product product = Product.builder()
                .pluCode("8809962586353")
                .name("대정)참치마요삼각김밥2편")
                .category("주먹밥")
                .currentStock(10)
                .isActive(true)
                .build();
        when(productRepository.findAllByIsActiveTrueOrderByCategoryAscNameAsc()).thenReturn(List.of(product));

        List<StudentProductResponseDto> result = studentProductService.getStudentProducts(salesDate, "", "");

        assertThat(result).hasSize(1);
        assertThat(result.get(0).getPluCode()).isEqualTo("8809962586353");
        assertThat(result.get(0).getName()).isEqualTo("대정)참치마요삼각김밥2편");
        assertThat(result.get(0).getCategory()).isEqualTo("주먹밥");
        assertThat(result.get(0).getStock()).isEqualTo(10);
    }

    @Test
    void submitRequest_validItems_upsertsRequest() {
        LocalDate salesDate = LocalDate.of(2026, 4, 24);
        StudentRequestCreateDto request = request("20240001", salesDate, item("8809962586353", 2));
        Product product = Product.builder()
                .pluCode("8809962586353")
                .name("대정)참치마요삼각김밥2편")
                .category("주먹밥")
                .currentStock(10)
                .isActive(true)
                .build();

        when(productRepository.findAllByPluCodeInAndIsActiveTrue(anyCollection())).thenReturn(List.of(product));
        when(studentProductRequestRepository.upsert("20240001", salesDate, "8809962586353", 2))
                .thenReturn(1);

        StudentRequestResponseDto response = studentProductService.submitRequest("20240001", request);

        assertThat(response.getStudentId()).isEqualTo("20240001");
        assertThat(response.getItemCount()).isEqualTo(1);
        assertThat(response.getTotalQuantity()).isEqualTo(2);
        verify(studentProductRequestRepository).upsert("20240001", salesDate, "8809962586353", 2);
    }

    @Test
    void submitRequest_usesAuthenticatedStudentIdOverPayload() {
        LocalDate salesDate = LocalDate.of(2026, 4, 24);
        StudentRequestCreateDto request = request("spoof-student", salesDate, item("8809962586353", 2));
        Product product = Product.builder()
                .pluCode("8809962586353")
                .name("대정)참치마요삼각김밥2편")
                .category("주먹밥")
                .currentStock(10)
                .isActive(true)
                .build();

        when(productRepository.findAllByPluCodeInAndIsActiveTrue(anyCollection())).thenReturn(List.of(product));
        when(studentProductRequestRepository.upsert("20240001", salesDate, "8809962586353", 2))
                .thenReturn(1);

        StudentRequestResponseDto response = studentProductService.submitRequest("20240001", request);

        assertThat(response.getStudentId()).isEqualTo("20240001");
        verify(studentProductRequestRepository).upsert("20240001", salesDate, "8809962586353", 2);
    }

    @Test
    void submitRequest_duplicatePluCode_rejectsRequest() {
        LocalDate salesDate = LocalDate.of(2026, 4, 24);
        StudentRequestCreateDto request = request(
                "20240001",
                salesDate,
                item("8809962586353", 1),
                item(" 8809962586353 ", 2)
        );

        assertThatThrownBy(() -> studentProductService.submitRequest("20240001", request))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("중복된 상품");

        verify(studentProductRequestRepository, never())
                .upsert("20240001", salesDate, "8809962586353", 1);
    }

    @Test
    void submitRequest_inactiveProduct_rejectsRequest() {
        LocalDate salesDate = LocalDate.of(2026, 4, 24);
        StudentRequestCreateDto request = request("20240001", salesDate, item("8809962586353", 2));

        when(productRepository.findAllByPluCodeInAndIsActiveTrue(anyCollection())).thenReturn(List.of());

        assertThatThrownBy(() -> studentProductService.submitRequest("20240001", request))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("활성 상품");
    }

    private StudentRequestCreateDto request(String studentId,
                                            LocalDate salesDate,
                                            StudentRequestCreateDto.ItemDto... items) {
        StudentRequestCreateDto request = new StudentRequestCreateDto();
        request.setStudentId(studentId);
        request.setSalesDate(salesDate);
        request.setItems(List.of(items));
        return request;
    }

    private StudentRequestCreateDto.ItemDto item(String pluCode, int quantity) {
        StudentRequestCreateDto.ItemDto item = new StudentRequestCreateDto.ItemDto();
        item.setPluCode(pluCode);
        item.setQuantity(quantity);
        return item;
    }

}
