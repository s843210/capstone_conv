package com.errorzero.conv.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.time.LocalDateTime;

@Getter
@AllArgsConstructor
public class StudentSuggestionResponseDto {
    private Long id;
    private String title;
    private String content;
    private String writer;
    private String status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
