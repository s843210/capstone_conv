package com.errorzero.conv.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "daily_context")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DailyContext {

    @Id
    @Column(name = "target_date", nullable = false)
    private LocalDate targetDate;

    @Column(name = "avg_temp_c")
    private Double avgTempC;

    @Builder.Default
    @Column(name = "precipitation_mm", nullable = false)
    private Double precipitationMm = 0.0;

    @Builder.Default
    @Column(name = "is_rain", nullable = false)
    private Short isRain = 0;

    @Builder.Default
    @Column(name = "is_holiday", nullable = false)
    private Short isHoliday = 0;

    @Builder.Default
    @Column(name = "academic_event", nullable = false)
    private Integer academicEvent = 0;

    @Builder.Default
    @Column(name = "building_headcount", nullable = false)
    private Integer buildingHeadcount = 0;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    public static DailyContext createDefault(LocalDate targetDate) {
        return DailyContext.builder()
                .targetDate(targetDate)
                .avgTempC(null)
                .precipitationMm(0.0)
                .isRain((short) 0)
                .isHoliday((short) 0)
                .academicEvent(0)
                .buildingHeadcount(0)
                .build();
    }

    @PrePersist
    @PreUpdate
    public void touchUpdatedAt() {
        this.updatedAt = LocalDateTime.now();
    }
}
