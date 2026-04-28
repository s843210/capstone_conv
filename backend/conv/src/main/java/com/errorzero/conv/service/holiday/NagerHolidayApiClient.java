package com.errorzero.conv.service.holiday;

import com.errorzero.conv.config.HolidayProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.time.LocalDate;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Component
@RequiredArgsConstructor
public class NagerHolidayApiClient implements HolidayApiClient {

    private static final ParameterizedTypeReference<List<Map<String, Object>>> HOLIDAY_LIST_TYPE =
            new ParameterizedTypeReference<>() {};

    private final RestClient holidayRestClient;
    private final HolidayProperties holidayProperties;

    private final Map<String, Set<LocalDate>> yearlyCache = new ConcurrentHashMap<>();

    @Override
    public boolean isPublicHoliday(LocalDate date) {
        if (!holidayProperties.isApiEnabled()) {
            return false;
        }

        int year = date.getYear();
        String countryCode = holidayProperties.getCountryCode().toUpperCase();
        String cacheKey = countryCode + "-" + year;

        Set<LocalDate> holidays = yearlyCache.computeIfAbsent(cacheKey, key -> fetchYearHolidaysWithRetry(year, countryCode));
        return holidays.contains(date);
    }

    private Set<LocalDate> fetchYearHolidaysWithRetry(int year, String countryCode) {
        int maxAttempts = Math.max(holidayProperties.getRetryCount(), 1);
        long backoffMs = Math.max(holidayProperties.getRetryBackoffMillis(), 100L);

        RuntimeException lastEx = null;

        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                return fetchYearHolidays(year, countryCode);
            } catch (RuntimeException ex) {
                lastEx = ex;
                log.warn("공휴일 API 조회 실패: year={}, countryCode={}, attempt={}/{}, reason={}",
                        year, countryCode, attempt, maxAttempts, ex.getMessage());

                if (attempt < maxAttempts) {
                    sleep(backoffMs * (1L << (attempt - 1)));
                }
            }
        }

        throw new IllegalStateException("공휴일 API 조회 재시도 실패: year=" + year + ", countryCode=" + countryCode, lastEx);
    }

    private Set<LocalDate> fetchYearHolidays(int year, String countryCode) {
        List<Map<String, Object>> response = holidayRestClient.get()
                .uri(uriBuilder -> uriBuilder
                        .path(holidayProperties.getPublicHolidayPath())
                        .build(year, countryCode))
                .retrieve()
                .body(HOLIDAY_LIST_TYPE);

        if (response == null || response.isEmpty()) {
            return Collections.emptySet();
        }

        return response.stream()
                .map(item -> item.get("date"))
                .filter(String.class::isInstance)
                .map(String.class::cast)
                .map(LocalDate::parse)
                .collect(Collectors.toUnmodifiableSet());
    }

    public void clearCache() {
        yearlyCache.clear();
    }

    private void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("공휴일 API 재시도 대기 중 인터럽트 발생", e);
        }
    }
}
