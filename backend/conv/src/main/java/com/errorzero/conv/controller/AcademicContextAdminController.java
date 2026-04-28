package com.errorzero.conv.controller;

import com.errorzero.conv.config.WeatherProperties;
import com.errorzero.conv.domain.DailyContext;
import com.errorzero.conv.dto.AcademicContextBackfillResponseDto;
import com.errorzero.conv.dto.AcademicContextJobResponseDto;
import com.errorzero.conv.dto.AcademicContextUploadResponseDto;
import com.errorzero.conv.service.academic.AcademicContextService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/admin/context/academic")
@RequiredArgsConstructor
@Validated
@Tag(name = "Academic Context Admin API", description = "학사일정/유동인구 컨텍스트 업서트 API")
public class AcademicContextAdminController {

    private final AcademicContextService academicContextService;
    private final WeatherProperties weatherProperties;

    @Operation(summary = "학사일정/유동인구 CSV 업로드", description = "학사일정 CSV와 유동인구 CSV를 업로드해 규칙을 저장합니다.")
    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<AcademicContextUploadResponseDto> uploadAcademicSources(
            @RequestPart("academicFile") MultipartFile academicFile,
            @RequestPart(value = "headcountFile", required = false) MultipartFile headcountFile,
            @RequestParam(defaultValue = "false") boolean dryRun
    ) {
        AcademicContextUploadResponseDto response = academicContextService.uploadAcademicSources(academicFile, headcountFile, dryRun);
        return ResponseEntity.ok(response);
    }

    @Operation(summary = "단건 학사 컨텍스트 업서트", description = "targetDate 기준으로 academic_event와 building_headcount를 계산해 daily_context에 반영합니다.")
    @PostMapping
    public ResponseEntity<AcademicContextJobResponseDto> upsertAcademic(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate targetDate
    ) {
        String runId = UUID.randomUUID().toString();
        LocalDate effectiveTargetDate = targetDate != null
                ? targetDate
                : LocalDate.now(ZoneId.of(weatherProperties.getScheduleZone())).plusDays(1);

        DailyContext saved = academicContextService.upsertAcademicContext(effectiveTargetDate);
        return ResponseEntity.ok(AcademicContextJobResponseDto.builder()
                .runId(runId)
                .status("SUCCESS")
                .targetDate(saved.getTargetDate())
                .academicEvent(saved.getAcademicEvent())
                .buildingHeadcount(saved.getBuildingHeadcount())
                .updatedAt(saved.getUpdatedAt())
                .message("daily_context academic_event/building_headcount 업서트 완료")
                .build());
    }

    @Operation(summary = "학사 컨텍스트 기간 백필", description = "from~to 기간에 대해 academic_event/building_headcount를 계산해 daily_context에 반영합니다.")
    @PostMapping("/backfill")
    public ResponseEntity<AcademicContextBackfillResponseDto> backfillAcademic(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
            @RequestParam(defaultValue = "365") @Max(value = 3660, message = "maxDays는 3660 이하여야 합니다") int maxDays
    ) {
        if (from.isAfter(to)) {
            throw new IllegalArgumentException("from 날짜는 to 날짜보다 늦을 수 없습니다.");
        }

        long totalDays = from.datesUntil(to.plusDays(1)).count();
        if (totalDays > maxDays) {
            throw new IllegalArgumentException("요청 기간이 너무 깁니다. maxDays를 늘리거나 기간을 줄여주세요.");
        }

        String runId = UUID.randomUUID().toString();
        int successCount = 0;
        int failureCount = 0;
        List<String> errors = new ArrayList<>();

        LocalDate cursor = from;
        while (!cursor.isAfter(to)) {
            try {
                academicContextService.upsertAcademicContext(cursor);
                successCount++;
            } catch (Exception ex) {
                failureCount++;
                if (errors.size() < 20) {
                    errors.add(cursor + " => " + ex.getMessage());
                }
            }
            cursor = cursor.plusDays(1);
        }

        String status = failureCount == 0 ? "SUCCESS" : (successCount == 0 ? "FAILED" : "PARTIAL_SUCCESS");

        return ResponseEntity.ok(AcademicContextBackfillResponseDto.builder()
                .runId(runId)
                .status(status)
                .from(from)
                .to(to)
                .successCount(successCount)
                .failureCount(failureCount)
                .errors(errors)
                .build());
    }
}
