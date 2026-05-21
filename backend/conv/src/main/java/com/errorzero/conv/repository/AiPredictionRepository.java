package com.errorzero.conv.repository;

import com.errorzero.conv.domain.AiPrediction;
import com.errorzero.conv.domain.Product;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.Collection;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

public interface AiPredictionRepository extends JpaRepository<AiPrediction, Long> {

    List<AiPrediction> findAllByTargetDate(LocalDate targetDate);

    List<AiPrediction> findAllByProductAndTargetDate(Product product, LocalDate targetDate);

    List<AiPrediction> findAllByProduct(Product product);

    List<AiPrediction> findAllByTargetDateAndProductIn(LocalDate targetDate, Collection<Product> products);

    @Query("SELECT MAX(a.targetDate) FROM AiPrediction a")
    Optional<LocalDate> findLatestTargetDate();

    @Query("SELECT MAX(a.targetDate) FROM AiPrediction a WHERE a.recommendedOrder > 1")
    Optional<LocalDate> findLatestRecommendedTargetDate();

    List<AiPrediction> findAllByTargetDateAndRecommendedOrderGreaterThanOrderByRecommendedOrderDesc(
            LocalDate targetDate,
            int recommendedOrder
    );
}
