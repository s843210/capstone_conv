package com.errorzero.conv.repository;

import java.time.LocalDate;
import java.time.LocalDateTime;

public interface StudentRequestDashboardProjection {
    String getStudentId();

    LocalDate getSalesDate();

    String getPluCode();

    String getProductName();

    Integer getQuantity();

    LocalDateTime getRequestedAt();
}
