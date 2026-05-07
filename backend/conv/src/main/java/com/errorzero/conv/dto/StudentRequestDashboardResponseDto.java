package com.errorzero.conv.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Getter
@AllArgsConstructor
public class StudentRequestDashboardResponseDto {
    private String studentId;
    private LocalDate salesDate;
    private String pluCode;
    private String productName;
    private int quantity;
    private LocalDateTime requestedAt;
}
