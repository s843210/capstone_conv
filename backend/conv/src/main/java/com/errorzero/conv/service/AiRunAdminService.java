package com.errorzero.conv.service;

import com.errorzero.conv.domain.AiRun;
import com.errorzero.conv.dto.AiPredictionRequestDto;
import com.errorzero.conv.dto.AiRunResponseDto;
import com.errorzero.conv.repository.AiRunRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class AiRunAdminService {

    private static final String MODEL_NAME = "random_forest_monthly_v2";

    private final ObjectMapper objectMapper;
    private final AiPredictionService aiPredictionService;
    private final AiRunRepository aiRunRepository;

    @Value("${app.ai.base-url:http://127.0.0.1:8000}")
    private String aiBaseUrl;

    @Transactional
    public AiRunResponseDto runPredict(LocalDate targetDate, boolean onlyPositiveRecommendations) {
        LocalDateTime startedAt = LocalDateTime.now();
        Map<String, Object> requestPayload = buildPredictRequest(targetDate, onlyPositiveRecommendations);
        String requestJson = toJson(requestPayload);

        try {
            JsonNode response = callFastApi("/ai/predict", requestJson);
            JsonNode springPayload = response.path("spring_payload");
            if (springPayload.isMissingNode() || springPayload.isNull()) {
                throw new IllegalStateException("FastAPI response does not contain spring_payload.");
            }

            AiPredictionRequestDto predictionRequest =
                    objectMapper.treeToValue(springPayload, AiPredictionRequestDto.class);
            int savedCount = aiPredictionService.savePredictions(predictionRequest);

            AiRun savedRun = saveRun(
                    response,
                    requestJson,
                    startedAt,
                    LocalDateTime.now(),
                    savedCount,
                    null
            );

            return toResponse(savedRun, savedCount);
        } catch (Exception e) {
            log.error("AI predict run failed", e);
            AiRun failedRun = saveFailedRun(requestJson, startedAt, e);
            return toResponse(failedRun, 0);
        }
    }

    private Map<String, Object> buildPredictRequest(LocalDate targetDate, boolean onlyPositiveRecommendations) {
        Map<String, Object> policy = new LinkedHashMap<>();
        policy.put("exclude_uncategorized", true);
        policy.put("require_sales_history", true);
        policy.put("require_current_stock", true);
        policy.put("only_positive_recommendations", onlyPositiveRecommendations);

        Map<String, Object> payload = new LinkedHashMap<>();
        if (targetDate != null) {
            payload.put("target_date", targetDate.toString());
        }
        payload.put("mode", "db");
        payload.put("persist_to_spring", false);
        payload.put("recommendation_policy", policy);
        return payload;
    }

    private JsonNode callFastApi(String path, String requestJson) throws IOException, InterruptedException {
        String base = aiBaseUrl.endsWith("/") ? aiBaseUrl.substring(0, aiBaseUrl.length() - 1) : aiBaseUrl;
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(base + path))
                .timeout(Duration.ofMinutes(5))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(requestJson))
                .build();

        HttpResponse<String> response = HttpClient.newHttpClient()
                .send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new IllegalStateException("FastAPI request failed: status="
                    + response.statusCode() + ", body=" + response.body());
        }

        return objectMapper.readTree(response.body());
    }

    private AiRun saveRun(JsonNode response,
                          String requestJson,
                          LocalDateTime startedAt,
                          LocalDateTime endedAt,
                          int savedCount,
                          String errorMessage) {
        JsonNode csvOutputs = response.path("csv_outputs");
        String status = response.path("status").asText(errorMessage == null ? "SUCCESS" : "FAILED");
        String runId = response.path("run_id").asText("spring-" + System.currentTimeMillis());
        String targetDateText = response.path("target_date").asText(null);
        LocalDate targetDate = parseDate(targetDateText);

        AiRun run = AiRun.builder()
                .runId(runId)
                .runType("PREDICT")
                .modelName(response.path("model_name").asText(MODEL_NAME))
                .status(status)
                .targetDate(targetDate)
                .startedAt(startedAt)
                .endedAt(endedAt)
                .durationSeconds(response.path("duration_seconds").isNumber()
                        ? response.path("duration_seconds").asDouble()
                        : Duration.between(startedAt, endedAt).toMillis() / 1000.0)
                .rowCount(response.path("row_count").asInt(savedCount))
                .predictionCsv(csvOutputs.path("prediction_csv").asText(null))
                .recommendationCsv(csvOutputs.path("recommendation_csv").asText(null))
                .requestPayload(requestJson)
                .errorMessage(errorMessage)
                .build();
        return aiRunRepository.save(run);
    }

    private AiRun saveFailedRun(String requestJson, LocalDateTime startedAt, Exception e) {
        LocalDateTime endedAt = LocalDateTime.now();
        AiRun run = AiRun.builder()
                .runId("spring-failed-" + System.currentTimeMillis())
                .runType("PREDICT")
                .modelName(MODEL_NAME)
                .status("FAILED")
                .startedAt(startedAt)
                .endedAt(endedAt)
                .durationSeconds(Duration.between(startedAt, endedAt).toMillis() / 1000.0)
                .rowCount(0)
                .requestPayload(requestJson)
                .errorMessage(e.getMessage())
                .build();
        return aiRunRepository.save(run);
    }

    private AiRunResponseDto toResponse(AiRun run, int savedCount) {
        return AiRunResponseDto.builder()
                .runId(run.getRunId())
                .status(run.getStatus())
                .modelName(run.getModelName())
                .targetDate(run.getTargetDate())
                .rowCount(run.getRowCount() != null ? run.getRowCount() : 0)
                .savedCount(savedCount)
                .predictionCsv(run.getPredictionCsv())
                .recommendationCsv(run.getRecommendationCsv())
                .errorMessage(run.getErrorMessage())
                .build();
    }

    private LocalDate parseDate(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return LocalDate.parse(value);
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (IOException e) {
            throw new IllegalStateException("Failed to serialize AI request payload.", e);
        }
    }
}
