package com.errorzero.conv.repository;

import com.errorzero.conv.domain.DailyContext;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;

public interface DailyContextRepository extends JpaRepository<DailyContext, LocalDate> {
}
