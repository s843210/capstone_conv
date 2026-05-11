package com.errorzero.conv.domain;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(
        name = "inventory_snapshot",
        uniqueConstraints = @UniqueConstraint(
                name = "uq_inventory_snapshot_date_product",
                columnNames = {"snapshot_date", "product_id"}
        )
)
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
public class InventorySnapshot {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "snapshot_date", nullable = false)
    private LocalDate snapshotDate;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "product_id", nullable = false)
    private Product product;

    @Column(name = "plu_code", nullable = false, length = 50)
    private String pluCode;

    @Column(name = "current_stock", nullable = false)
    private Integer currentStock;

    @Column(name = "uploaded_at", nullable = false)
    private LocalDateTime uploadedAt;
}
