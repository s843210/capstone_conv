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

import java.time.LocalDateTime;

@Entity
@Table(name = "building_headcount_profile")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class BuildingHeadcountProfile {

    @Id
    private Short id;

    @Builder.Default
    @Column(name = "monday", nullable = false)
    private Integer monday = 20;

    @Builder.Default
    @Column(name = "tuesday", nullable = false)
    private Integer tuesday = 20;

    @Builder.Default
    @Column(name = "wednesday", nullable = false)
    private Integer wednesday = 20;

    @Builder.Default
    @Column(name = "thursday", nullable = false)
    private Integer thursday = 20;

    @Builder.Default
    @Column(name = "friday", nullable = false)
    private Integer friday = 20;

    @Builder.Default
    @Column(name = "default_count", nullable = false)
    private Integer defaultCount = 20;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    public static BuildingHeadcountProfile defaultProfile() {
        return BuildingHeadcountProfile.builder()
                .id((short) 1)
                .monday(20)
                .tuesday(20)
                .wednesday(20)
                .thursday(20)
                .friday(20)
                .defaultCount(20)
                .build();
    }

    @PrePersist
    @PreUpdate
    public void touchUpdatedAt() {
        this.updatedAt = LocalDateTime.now();
    }
}
