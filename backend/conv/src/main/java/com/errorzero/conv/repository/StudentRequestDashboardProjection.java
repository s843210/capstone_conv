package com.errorzero.conv.repository;

import java.time.LocalDateTime;

public interface StudentRequestDashboardProjection {
    String getStudentId();

    String getProductName();

    Integer getQuantity();

    LocalDateTime getRequestedAt();
}
