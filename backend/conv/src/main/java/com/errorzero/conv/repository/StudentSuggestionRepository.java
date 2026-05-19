package com.errorzero.conv.repository;

import com.errorzero.conv.domain.StudentSuggestion;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface StudentSuggestionRepository extends JpaRepository<StudentSuggestion, Long> {

    List<StudentSuggestion> findAllByOrderByUpdatedAtDesc(Pageable pageable);

    List<StudentSuggestion> findAllByWriterOrderByUpdatedAtDesc(String writer, Pageable pageable);
}
