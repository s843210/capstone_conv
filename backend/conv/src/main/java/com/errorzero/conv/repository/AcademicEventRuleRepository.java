package com.errorzero.conv.repository;

import com.errorzero.conv.domain.AcademicEventRule;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;
import java.util.List;

public interface AcademicEventRuleRepository extends JpaRepository<AcademicEventRule, Long> {

    List<AcademicEventRule> findAllByStartDateLessThanEqualAndEndDateGreaterThanEqual(LocalDate startDate, LocalDate endDate);
}
