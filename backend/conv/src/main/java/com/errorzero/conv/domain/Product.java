package com.errorzero.conv.domain;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.ColumnDefault;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "product")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
public class Product {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "plu_code", nullable = false, unique = true, length = 50)
    private String pluCode;

    @Column(nullable = false, length = 255)
    private String name;

    @Builder.Default
    @Column(nullable = false, length = 100)
    private String category = "기타/미분류";

    @Column(name = "current_stock", nullable = false)
    @ColumnDefault("0")
    private Integer currentStock;

    @Column(name = "is_active")
    @ColumnDefault("true")
    private Boolean isActive;

    @Column(name = "updated_at")
    @UpdateTimestamp
    private LocalDateTime updatedAt;
}
