package com.errorzero.conv.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDate;
import java.util.List;

@Getter
@Setter
@NoArgsConstructor
public class StudentRequestCreateDto {

    private String studentId;

    private LocalDate salesDate;

    @Valid
    @NotEmpty(message = "신청 상품은 최소 1개 이상 필요합니다")
    private List<ItemDto> items;

    @Getter
    @Setter
    @NoArgsConstructor
    public static class ItemDto {

        @NotBlank(message = "pluCode는 필수입니다")
        private String pluCode;

        @NotNull(message = "quantity는 필수입니다")
        @Min(value = 1, message = "quantity는 1 이상이어야 합니다")
        private Integer quantity;
    }
}
