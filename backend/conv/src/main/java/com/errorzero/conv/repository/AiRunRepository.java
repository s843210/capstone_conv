package com.errorzero.conv.repository;

import com.errorzero.conv.domain.AiRun;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

public interface AiRunRepository extends JpaRepository<AiRun, Long> {

    Optional<AiRun> findByRunId(String runId);

    List<AiRun> findAllByTargetDateOrderByStartedAtDesc(LocalDate targetDate);

    List<AiRun> findTop20ByOrderByStartedAtDesc();
}
