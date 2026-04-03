package com.errorzero.conv.repository;

import com.errorzero.conv.domain.AiPrediction;
import com.errorzero.conv.domain.Product;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Collection;
import java.time.LocalDate;
import java.util.List;

public interface AiPredictionRepository extends JpaRepository<AiPrediction, Long> {

    List<AiPrediction> findAllByTargetDate(LocalDate targetDate);

    List<AiPrediction> findAllByProductAndTargetDate(Product product, LocalDate targetDate);

    List<AiPrediction> findAllByProduct(Product product);

    List<AiPrediction> findAllByTargetDateAndProductIn(LocalDate targetDate, Collection<Product> products);
}
