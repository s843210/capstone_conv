package com.errorzero.conv.domain;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "ai_prediction")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED) //개발자가 New porduct를 생성할떄 나오는 오류를 막아주는 역할
@AllArgsConstructor
@Builder
public class AiPrediction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "product_id", nullable = false)
    private Product product;

    @Column(name = "target_date", nullable = false)
    private LocalDate targetDate;

    @Column(name = "predicted_sales", nullable = false)
    private Integer predictedSales;

    @Column(name = "recommended_order", nullable = false)
    private Integer recommendedOrder;

    @Column(name = "confidence_score")
    private Double confidenceScore;

    @Column(name = "ai_insight", length = 255)
    private String aiInsight;

    @Column(name = "created_at")
    @CreationTimestamp
    private LocalDateTime createdAt;
}
