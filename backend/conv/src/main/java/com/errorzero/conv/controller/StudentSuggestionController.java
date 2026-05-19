package com.errorzero.conv.controller;

import com.errorzero.conv.dto.StudentSuggestionBulkDeleteDto;
import com.errorzero.conv.dto.StudentSuggestionBulkDeleteResponseDto;
import com.errorzero.conv.dto.StudentSuggestionCreateDto;
import com.errorzero.conv.dto.StudentSuggestionResponseDto;
import com.errorzero.conv.dto.StudentSuggestionUpdateDto;
import com.errorzero.conv.service.StudentSuggestionService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/student/suggestions")
@RequiredArgsConstructor
@Validated
@Tag(name = "Student Suggestion API", description = "학생 앱 건의사항 등록/조회/수정/삭제 API")
public class StudentSuggestionController {

    private final StudentSuggestionService studentSuggestionService;

    @Operation(summary = "건의사항 목록 조회", description = "학생 앱/대시보드에서 사용할 건의사항 목록을 최신순으로 조회합니다.")
    @GetMapping
    public ResponseEntity<List<StudentSuggestionResponseDto>> getSuggestions(
            @RequestParam(defaultValue = "100") @Min(1) @Max(500) int limit,
            @RequestParam(defaultValue = "") String writer
    ) {
        return ResponseEntity.ok(studentSuggestionService.getSuggestions(limit, writer));
    }

    @Operation(summary = "건의사항 등록", description = "학생이 작성한 건의사항을 저장합니다.")
    @PostMapping
    public ResponseEntity<StudentSuggestionResponseDto> createSuggestion(
            @Valid @RequestBody StudentSuggestionCreateDto request
    ) {
        return ResponseEntity.ok(studentSuggestionService.createSuggestion(request));
    }

    @Operation(summary = "건의사항 수정", description = "작성자 본인의 건의사항 제목/내용을 수정합니다.")
    @PutMapping("/{id}")
    public ResponseEntity<StudentSuggestionResponseDto> updateSuggestion(
            @PathVariable Long id,
            @Valid @RequestBody StudentSuggestionUpdateDto request
    ) {
        return ResponseEntity.ok(studentSuggestionService.updateSuggestion(id, request));
    }

    @Operation(summary = "건의사항 삭제", description = "작성자 본인의 건의사항을 삭제합니다.")
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteSuggestion(
            @PathVariable Long id,
            @RequestParam @NotBlank(message = "writer는 필수입니다") String writer
    ) {
        studentSuggestionService.deleteSuggestion(id, writer);
        return ResponseEntity.noContent().build();
    }

    @Operation(summary = "건의사항 일괄 삭제", description = "작성자 본인의 건의사항 여러 개를 삭제합니다.")
    @DeleteMapping("/bulk")
    public ResponseEntity<StudentSuggestionBulkDeleteResponseDto> deleteSuggestions(
            @Valid @RequestBody StudentSuggestionBulkDeleteDto request
    ) {
        return ResponseEntity.ok(studentSuggestionService.deleteSuggestions(request));
    }
}
