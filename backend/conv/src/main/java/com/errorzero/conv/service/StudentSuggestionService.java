package com.errorzero.conv.service;

import com.errorzero.conv.domain.StudentSuggestion;
import com.errorzero.conv.dto.StudentSuggestionBulkDeleteDto;
import com.errorzero.conv.dto.StudentSuggestionBulkDeleteResponseDto;
import com.errorzero.conv.dto.StudentSuggestionCreateDto;
import com.errorzero.conv.dto.StudentSuggestionResponseDto;
import com.errorzero.conv.dto.StudentSuggestionUpdateDto;
import com.errorzero.conv.repository.StudentSuggestionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class StudentSuggestionService {

    private static final int DEFAULT_LIMIT = 100;
    private static final int MAX_LIMIT = 500;

    private final StudentSuggestionRepository studentSuggestionRepository;

    @Transactional(readOnly = true)
    public List<StudentSuggestionResponseDto> getSuggestions(int limit, String writer) {
        Pageable pageable = PageRequest.of(0, normalizeLimit(limit));
        String safeWriter = normalize(writer);
        List<StudentSuggestion> suggestions = safeWriter == null
                ? studentSuggestionRepository.findAllByOrderByUpdatedAtDesc(pageable)
                : studentSuggestionRepository.findAllByWriterOrderByUpdatedAtDesc(safeWriter, pageable);

        return suggestions.stream()
                .map(this::toResponse)
                .toList();
    }

    @Transactional
    public StudentSuggestionResponseDto createSuggestion(StudentSuggestionCreateDto request) {
        StudentSuggestion suggestion = StudentSuggestion.builder()
                .writer(required(request.getWriter(), "writer"))
                .title(required(request.getTitle(), "title"))
                .content(required(request.getContent(), "content"))
                .status("UNREAD")
                .build();

        return toResponse(studentSuggestionRepository.save(suggestion));
    }

    @Transactional
    public StudentSuggestionResponseDto updateSuggestion(Long id, StudentSuggestionUpdateDto request) {
        StudentSuggestion suggestion = findSuggestion(id);
        validateOwner(suggestion, request.getWriter());

        suggestion.setTitle(required(request.getTitle(), "title"));
        suggestion.setContent(required(request.getContent(), "content"));

        return toResponse(suggestion);
    }

    @Transactional
    public void deleteSuggestion(Long id, String writer) {
        StudentSuggestion suggestion = findSuggestion(id);
        validateOwner(suggestion, writer);
        studentSuggestionRepository.delete(suggestion);
    }

    @Transactional
    public StudentSuggestionBulkDeleteResponseDto deleteSuggestions(StudentSuggestionBulkDeleteDto request) {
        String writer = required(request.getWriter(), "writer");
        int removedCount = 0;
        int failedCount = 0;

        for (Long id : request.getIds()) {
            if (id == null) {
                failedCount++;
                continue;
            }

            try {
                StudentSuggestion suggestion = findSuggestion(id);
                validateOwner(suggestion, writer);
                studentSuggestionRepository.delete(suggestion);
                removedCount++;
            } catch (RuntimeException exc) {
                failedCount++;
            }
        }

        return new StudentSuggestionBulkDeleteResponseDto(removedCount, failedCount);
    }

    private StudentSuggestion findSuggestion(Long id) {
        return studentSuggestionRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("건의사항을 찾을 수 없습니다: " + id));
    }

    private void validateOwner(StudentSuggestion suggestion, String writer) {
        String safeWriter = required(writer, "writer");
        if (!suggestion.getWriter().equals(safeWriter)) {
            throw new IllegalArgumentException("작성자만 건의사항을 수정/삭제할 수 있습니다.");
        }
    }

    private StudentSuggestionResponseDto toResponse(StudentSuggestion suggestion) {
        return new StudentSuggestionResponseDto(
                suggestion.getId(),
                suggestion.getTitle(),
                suggestion.getContent(),
                suggestion.getWriter(),
                suggestion.getStatus(),
                suggestion.getCreatedAt(),
                suggestion.getUpdatedAt()
        );
    }

    private int normalizeLimit(int limit) {
        if (limit <= 0) {
            return DEFAULT_LIMIT;
        }
        return Math.min(limit, MAX_LIMIT);
    }

    private String normalize(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }

    private String required(String value, String fieldName) {
        String normalized = normalize(value);
        if (normalized == null) {
            throw new IllegalArgumentException(fieldName + "는 필수입니다");
        }
        return normalized;
    }
}
