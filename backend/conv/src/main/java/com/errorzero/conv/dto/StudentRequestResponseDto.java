package com.errorzero.conv.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;

import java.time.LocalDate;

@Getter
@Builder
@AllArgsConstructor
public class StudentRequestResponseDto {
    private String studentId;
    private LocalDate salesDate;
    private int itemCount;
    private int totalQuantity;
    private String message;
}
