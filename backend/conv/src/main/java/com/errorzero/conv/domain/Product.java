package com.errorzero.conv.domain;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.ColumnDefault;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "product")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)  //개발자가 New porduct를 생성할떄 나오는 오류를 막아주는 역할
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

    @Column(length = 100)
    @ColumnDefault("'기타/미분류'")
    private String category;

    @Column(name = "current_stock")
    @ColumnDefault("0")
    private Integer currentStock;

    @Column(name = "is_active")
    @ColumnDefault("true")
    private Boolean isActive;

    @Column(name = "updated_at")
    @UpdateTimestamp
    private LocalDateTime updatedAt;
}
