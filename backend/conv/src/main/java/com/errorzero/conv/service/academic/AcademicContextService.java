package com.errorzero.conv.service.academic;

import com.errorzero.conv.domain.AcademicEventRule;
import com.errorzero.conv.domain.BuildingHeadcountProfile;
import com.errorzero.conv.domain.DailyContext;
import com.errorzero.conv.dto.AcademicContextUploadResponseDto;
import com.errorzero.conv.repository.AcademicEventRuleRepository;
import com.errorzero.conv.repository.BuildingHeadcountProfileRepository;
import com.errorzero.conv.repository.DailyContextRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Service
@RequiredArgsConstructor
public class AcademicContextService {

    private static final short PROFILE_ID = 1;
    private static final int DEFAULT_HEADCOUNT = 20;
    private static final Pattern DATE_YYYY_MM_DD = Pattern.compile("(20\\d{2})[-./](0[1-9]|1[0-2])[-./]([0-2]\\d|3[01])");
    private static final Pattern DATE_YY_MM_DD = Pattern.compile("(?<!\\d)(\\d{2})[-./](0[1-9]|1[0-2])[-./]([0-2]\\d|3[01])(?!\\d)");

    private static final List<Charset> CSV_CHARSETS = List.of(
            StandardCharsets.UTF_8,
            Charset.forName("MS949"),
            Charset.forName("EUC-KR")
    );

    private static final Map<Integer, Integer> EVENT_PRIORITY = Map.of(
            0, 1,
            1, 2,
            4, 3,
            3, 4,
            2, 5
    );

    private final DailyContextRepository dailyContextRepository;
    private final AcademicEventRuleRepository academicEventRuleRepository;
    private final BuildingHeadcountProfileRepository buildingHeadcountProfileRepository;

    @Transactional
    public AcademicContextUploadResponseDto uploadAcademicSources(MultipartFile academicFile,
                                                                  MultipartFile headcountFile,
                                                                  boolean dryRun) {
        if (academicFile == null || academicFile.isEmpty()) {
            throw new IllegalArgumentException("학사일정 CSV(academicFile)는 필수입니다.");
        }

        String runId = UUID.randomUUID().toString();

        ParseResult parseResult = parseAcademicRules(academicFile);
        BuildingHeadcountProfile profile = parseHeadcountProfile(headcountFile);

        if (!dryRun) {
            academicEventRuleRepository.deleteAllInBatch();
            if (!parseResult.rules.isEmpty()) {
                academicEventRuleRepository.saveAll(parseResult.rules);
            }
            buildingHeadcountProfileRepository.save(profile);
        }

        LocalDate minDate = parseResult.rules.stream()
                .map(AcademicEventRule::getStartDate)
                .min(LocalDate::compareTo)
                .orElse(null);
        LocalDate maxDate = parseResult.rules.stream()
                .map(AcademicEventRule::getEndDate)
                .max(LocalDate::compareTo)
                .orElse(null);

        return AcademicContextUploadResponseDto.builder()
                .runId(runId)
                .dryRun(dryRun)
                .parsedRuleRows(parseResult.parsedRows)
                .savedRuleRows(dryRun ? 0 : parseResult.rules.size())
                .invalidRuleRows(parseResult.invalidRows)
                .ignoredRuleRows(parseResult.ignoredRows)
                .monday(profile.getMonday())
                .tuesday(profile.getTuesday())
                .wednesday(profile.getWednesday())
                .thursday(profile.getThursday())
                .friday(profile.getFriday())
                .defaultCount(profile.getDefaultCount())
                .minRuleDate(minDate)
                .maxRuleDate(maxDate)
                .invalidSamples(parseResult.invalidSamples)
                .message(dryRun
                        ? "DRY RUN 완료: 학사일정/유동인구 파싱 결과만 확인했습니다."
                        : "학사일정 규칙 + 요일 유동인구 프로필 저장 완료")
                .build();
    }

    @Transactional
    public DailyContext upsertAcademicContext(LocalDate targetDate) {
        DailyContext context = dailyContextRepository.findById(targetDate)
                .orElseGet(() -> DailyContext.createDefault(targetDate));

        int academicEvent = resolveAcademicEvent(targetDate);
        int buildingHeadcount = resolveBuildingHeadcount(targetDate, academicEvent);

        context.setAcademicEvent(academicEvent);
        context.setBuildingHeadcount(buildingHeadcount);

        if (context.getPrecipitationMm() == null) {
            context.setPrecipitationMm(0.0);
        }
        if (context.getIsRain() == null) {
            context.setIsRain((short) 0);
        }
        if (context.getIsHoliday() == null) {
            context.setIsHoliday((short) 0);
        }

        return dailyContextRepository.save(context);
    }

    @Transactional(readOnly = true)
    public int resolveAcademicEvent(LocalDate targetDate) {
        List<AcademicEventRule> rules = new ArrayList<>(academicEventRuleRepository
                .findAllByStartDateLessThanEqualAndEndDateGreaterThanEqual(targetDate, targetDate));

        if (rules.isEmpty()) {
            return 0;
        }

        rules.sort(Comparator
                .comparingInt((AcademicEventRule r) -> EVENT_PRIORITY.getOrDefault(r.getEventCode(), 0)).reversed()
                .thenComparingLong(r -> r.getEndDate().toEpochDay() - r.getStartDate().toEpochDay())
                .thenComparing(AcademicEventRule::getStartDate, Comparator.reverseOrder()));

        return rules.get(0).getEventCode();
    }

    @Transactional(readOnly = true)
    public int resolveBuildingHeadcount(LocalDate targetDate, int academicEvent) {
        BuildingHeadcountProfile profile = loadProfileOrDefault();

        if (academicEvent != 1) {
            return safeCount(profile.getDefaultCount(), DEFAULT_HEADCOUNT);
        }

        DayOfWeek day = targetDate.getDayOfWeek();
        return switch (day) {
            case MONDAY -> safeCount(profile.getMonday(), DEFAULT_HEADCOUNT);
            case TUESDAY -> safeCount(profile.getTuesday(), DEFAULT_HEADCOUNT);
            case WEDNESDAY -> safeCount(profile.getWednesday(), DEFAULT_HEADCOUNT);
            case THURSDAY -> safeCount(profile.getThursday(), DEFAULT_HEADCOUNT);
            case FRIDAY -> safeCount(profile.getFriday(), DEFAULT_HEADCOUNT);
            default -> safeCount(profile.getDefaultCount(), DEFAULT_HEADCOUNT);
        };
    }

    private BuildingHeadcountProfile loadProfileOrDefault() {
        return buildingHeadcountProfileRepository.findById(PROFILE_ID)
                .orElseGet(BuildingHeadcountProfile::defaultProfile);
    }

    private int safeCount(Integer value, int fallback) {
        if (value == null || value < 0) {
            return fallback;
        }
        return value;
    }

    private ParseResult parseAcademicRules(MultipartFile file) {
        List<String[]> table = readCsvWithFallback(file);
        if (table.isEmpty()) {
            throw new IllegalArgumentException("학사일정 CSV가 비어 있습니다.");
        }

        int headerIndex = findHeaderIndex(table,
                List.of("start_date", "date", "시작", "날짜", "event", "구분", "event_code", "코드"));
        if (headerIndex < 0) {
            throw new IllegalArgumentException("학사일정 CSV 헤더를 찾지 못했습니다. 예: start_date,end_date,event_code");
        }

        String[] header = table.get(headerIndex);
        ColumnMapping mapping = mapAcademicColumns(header);

        if (!mapping.isUsable()) {
            throw new IllegalArgumentException("학사일정 CSV는 date 또는 start_date/end_date와 event_code(또는 event_name)가 필요합니다.");
        }

        ParseResult result = new ParseResult();

        for (int i = headerIndex + 1; i < table.size(); i++) {
            String[] row = table.get(i);

            String rawDate = valueAt(row, mapping.dateIdx);
            String rawStart = valueAt(row, mapping.startIdx);
            String rawEnd = valueAt(row, mapping.endIdx);
            String rawEventCode = valueAt(row, mapping.eventCodeIdx);
            String rawEventName = valueAt(row, mapping.eventNameIdx);

            if (isAllBlank(rawDate, rawStart, rawEnd, rawEventCode, rawEventName)) {
                result.ignoredRows++;
                continue;
            }

            LocalDate startDate;
            LocalDate endDate;

            if (!rawDate.isBlank()) {
                LocalDate date = parseDate(rawDate);
                if (date == null) {
                    result.invalidRows++;
                    addInvalidSample(result, "row " + (i + 1) + ": invalid date=" + rawDate);
                    continue;
                }
                startDate = date;
                endDate = date;
            } else {
                startDate = parseDate(rawStart);
                endDate = parseDate(rawEnd);
                if (startDate == null || endDate == null) {
                    result.invalidRows++;
                    addInvalidSample(result, "row " + (i + 1) + ": invalid range=" + rawStart + "~" + rawEnd);
                    continue;
                }
            }

            if (startDate.isAfter(endDate)) {
                result.invalidRows++;
                addInvalidSample(result, "row " + (i + 1) + ": start_date > end_date");
                continue;
            }

            Integer eventCode = parseEventCode(rawEventCode, rawEventName);
            if (eventCode == null) {
                result.invalidRows++;
                addInvalidSample(result, "row " + (i + 1) + ": invalid event=" + rawEventCode + "/" + rawEventName);
                continue;
            }

            AcademicEventRule rule = AcademicEventRule.builder()
                    .eventCode(eventCode)
                    .startDate(startDate)
                    .endDate(endDate)
                    .eventName(rawEventName.isBlank() ? null : rawEventName)
                    .build();
            result.rules.add(rule);
            result.parsedRows++;
        }

        return result;
    }

    private BuildingHeadcountProfile parseHeadcountProfile(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            return loadProfileOrDefault();
        }

        List<String[]> table = readCsvWithFallback(file);
        if (table.isEmpty()) {
            return loadProfileOrDefault();
        }

        Map<String, Integer> counts = new HashMap<>();

        // 패턴1: 헤더(월,화,수,목,금) + 첫 데이터 행
        for (int i = 0; i < Math.min(table.size(), 5); i++) {
            String[] row = table.get(i);
            Map<String, Integer> headerIndex = headerToIndex(row);
            if (headerIndex.size() >= 5 && i + 1 < table.size()) {
                String[] valueRow = table.get(i + 1);
                putCount(counts, "mon", parsePositiveInt(valueAt(valueRow, headerIndex.get("mon"))));
                putCount(counts, "tue", parsePositiveInt(valueAt(valueRow, headerIndex.get("tue"))));
                putCount(counts, "wed", parsePositiveInt(valueAt(valueRow, headerIndex.get("wed"))));
                putCount(counts, "thu", parsePositiveInt(valueAt(valueRow, headerIndex.get("thu"))));
                putCount(counts, "fri", parsePositiveInt(valueAt(valueRow, headerIndex.get("fri"))));
                break;
            }
        }

        // 패턴2: day,count 형태
        if (counts.size() < 5) {
            for (String[] row : table) {
                if (row.length < 2) {
                    continue;
                }
                String key = normalizeDayKey(row[0]);
                if (key == null) {
                    continue;
                }
                Integer value = parsePositiveInt(valueAt(row, 1));
                putCount(counts, key, value);
            }
        }

        BuildingHeadcountProfile base = loadProfileOrDefault();
        base.setId(PROFILE_ID);
        base.setMonday(safeCount(counts.get("mon"), safeCount(base.getMonday(), DEFAULT_HEADCOUNT)));
        base.setTuesday(safeCount(counts.get("tue"), safeCount(base.getTuesday(), DEFAULT_HEADCOUNT)));
        base.setWednesday(safeCount(counts.get("wed"), safeCount(base.getWednesday(), DEFAULT_HEADCOUNT)));
        base.setThursday(safeCount(counts.get("thu"), safeCount(base.getThursday(), DEFAULT_HEADCOUNT)));
        base.setFriday(safeCount(counts.get("fri"), safeCount(base.getFriday(), DEFAULT_HEADCOUNT)));
        base.setDefaultCount(DEFAULT_HEADCOUNT);

        return base;
    }

    private void putCount(Map<String, Integer> counts, String key, Integer value) {
        if (value == null) {
            return;
        }
        counts.put(key, value);
    }

    private Integer parseEventCode(String rawCode, String rawName) {
        if (rawCode != null && !rawCode.isBlank()) {
            try {
                int parsed = Integer.parseInt(rawCode.trim());
                if (parsed >= 0 && parsed <= 4) {
                    return parsed;
                }
            } catch (NumberFormatException ignored) {
                // name 기반 파싱 시도
            }
        }

        String value = normalizeText(rawName);
        if (value == null || value.isBlank()) {
            return null;
        }

        if (value.contains("시험")) {
            return 2;
        }
        if (value.contains("축제")) {
            return 3;
        }
        if (value.contains("계절")) {
            return 4;
        }
        if (value.contains("학기중") || value.contains("개강") || value.contains("기말")) {
            return 1;
        }
        if (value.contains("비학기") || value.contains("방학")) {
            return 0;
        }

        return null;
    }

    private Integer parsePositiveInt(String raw) {
        String value = normalizeText(raw);
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            int parsed = Integer.parseInt(value.replace(",", ""));
            return Math.max(parsed, 0);
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private LocalDate parseDate(String raw) {
        String value = normalizeText(raw);
        if (value == null || value.isBlank()) {
            return null;
        }

        List<DateTimeFormatter> formatters = List.of(
                DateTimeFormatter.ISO_LOCAL_DATE,
                DateTimeFormatter.ofPattern("yyyy.M.d"),
                DateTimeFormatter.ofPattern("yyyy/M/d"),
                DateTimeFormatter.ofPattern("yyyy-M-d"),
                DateTimeFormatter.ofPattern("yy.M.d"),
                DateTimeFormatter.ofPattern("yy/M/d"),
                DateTimeFormatter.ofPattern("yy-M-d")
        );

        for (DateTimeFormatter formatter : formatters) {
            try {
                return LocalDate.parse(value, formatter.withLocale(Locale.KOREAN));
            } catch (DateTimeParseException ignored) {
                // next
            }
        }

        Matcher m1 = DATE_YYYY_MM_DD.matcher(value);
        if (m1.find()) {
            return LocalDate.of(Integer.parseInt(m1.group(1)), Integer.parseInt(m1.group(2)), Integer.parseInt(m1.group(3)));
        }

        Matcher m2 = DATE_YY_MM_DD.matcher(value);
        if (m2.find()) {
            return LocalDate.of(Integer.parseInt("20" + m2.group(1)), Integer.parseInt(m2.group(2)), Integer.parseInt(m2.group(3)));
        }

        return null;
    }

    private ColumnMapping mapAcademicColumns(String[] header) {
        int dateIdx = -1;
        int startIdx = -1;
        int endIdx = -1;
        int eventCodeIdx = -1;
        int eventNameIdx = -1;

        for (int i = 0; i < header.length; i++) {
            String h = normalizeHeader(header[i]);

            if (dateIdx < 0 && (equalsAny(h, "date", "날짜", "일자", "targetdate"))) {
                dateIdx = i;
            }
            if (startIdx < 0 && (equalsAny(h, "startdate", "시작일", "시작", "from", "개강", "개강일"))) {
                startIdx = i;
            }
            if (endIdx < 0 && (equalsAny(h, "enddate", "종료일", "종료", "to", "기말", "기말일", "종강", "종강일"))) {
                endIdx = i;
            }
            if (eventCodeIdx < 0 && (equalsAny(h, "eventcode", "코드", "이벤트코드", "academicevent"))) {
                eventCodeIdx = i;
            }
            if (eventNameIdx < 0 && (equalsAny(h, "eventname", "event", "구분", "학사일정", "이벤트"))) {
                eventNameIdx = i;
            }
        }

        return new ColumnMapping(dateIdx, startIdx, endIdx, eventCodeIdx, eventNameIdx);
    }

    private Map<String, Integer> headerToIndex(String[] header) {
        Map<String, Integer> map = new HashMap<>();
        for (int i = 0; i < header.length; i++) {
            String key = normalizeDayKey(header[i]);
            if (key != null) {
                map.put(key, i);
            }
        }
        return map;
    }

    private String normalizeDayKey(String raw) {
        String h = normalizeHeader(raw);
        return switch (h) {
            case "월", "월요일", "mon", "monday" -> "mon";
            case "화", "화요일", "tue", "tuesday" -> "tue";
            case "수", "수요일", "wed", "wednesday" -> "wed";
            case "목", "목요일", "thu", "thursday" -> "thu";
            case "금", "금요일", "fri", "friday" -> "fri";
            default -> null;
        };
    }

    private int findHeaderIndex(List<String[]> rows, List<String> keywords) {
        for (int i = 0; i < rows.size(); i++) {
            String joined = normalizeHeader(String.join("|", rows.get(i)));
            for (String keyword : keywords) {
                if (joined.contains(normalizeHeader(keyword))) {
                    return i;
                }
            }
        }
        return -1;
    }

    private List<String[]> readCsvWithFallback(MultipartFile file) {
        try {
            byte[] bytes = file.getBytes();
            List<String[]> best = List.of();

            for (Charset charset : CSV_CHARSETS) {
                List<String[]> parsed = parseCsv(bytes, charset);
                if (parsed.isEmpty()) {
                    continue;
                }
                best = parsed;
                int headerIdx = findHeaderIndex(parsed, List.of("date", "start_date", "시작일", "학사일정", "월", "monday"));
                if (headerIdx >= 0) {
                    return parsed;
                }
            }

            return best;
        } catch (IOException e) {
            throw new IllegalStateException("CSV 파일 읽기 실패: " + file.getOriginalFilename(), e);
        }
    }

    private List<String[]> parseCsv(byte[] bytes, Charset charset) throws IOException {
        List<String[]> rows = new ArrayList<>();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(new ByteArrayInputStream(bytes), charset))) {
            String line;
            while ((line = reader.readLine()) != null) {
                rows.add(splitCsvLine(line));
            }
        }
        return rows;
    }

    private String[] splitCsvLine(String line) {
        List<String> cols = new ArrayList<>();
        StringBuilder token = new StringBuilder();
        boolean inQuotes = false;

        for (int i = 0; i < line.length(); i++) {
            char ch = line.charAt(i);
            if (ch == '"') {
                if (inQuotes && i + 1 < line.length() && line.charAt(i + 1) == '"') {
                    token.append('"');
                    i++;
                } else {
                    inQuotes = !inQuotes;
                }
                continue;
            }

            if (ch == ',' && !inQuotes) {
                cols.add(cleanCell(token.toString()));
                token.setLength(0);
            } else {
                token.append(ch);
            }
        }
        cols.add(cleanCell(token.toString()));

        return cols.toArray(String[]::new);
    }

    private String valueAt(String[] row, int idx) {
        if (idx < 0 || idx >= row.length) {
            return "";
        }
        return cleanCell(row[idx]);
    }

    private boolean isAllBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return false;
            }
        }
        return true;
    }

    private void addInvalidSample(ParseResult result, String message) {
        if (result.invalidSamples.size() < 20) {
            result.invalidSamples.add(message);
        }
    }

    private boolean equalsAny(String value, String... candidates) {
        for (String candidate : candidates) {
            if (value.equals(normalizeHeader(candidate))) {
                return true;
            }
        }
        return false;
    }

    private String normalizeHeader(String raw) {
        return normalizeText(raw)
                .replace("_", "")
                .replace("-", "")
                .replace(" ", "")
                .toLowerCase(Locale.ROOT);
    }

    private String normalizeText(String raw) {
        if (raw == null) {
            return "";
        }
        return cleanCell(raw)
                .replace("\\n", "")
                .replace("\n", "")
                .replace("\uFEFF", "")
                .replace("\u00A0", " ")
                .trim();
    }

    private String cleanCell(String raw) {
        return raw == null ? "" : raw.trim();
    }

    private static class ParseResult {
        final List<AcademicEventRule> rules = new ArrayList<>();
        int parsedRows = 0;
        int invalidRows = 0;
        int ignoredRows = 0;
        final List<String> invalidSamples = new ArrayList<>();
    }

    private record ColumnMapping(int dateIdx, int startIdx, int endIdx, int eventCodeIdx, int eventNameIdx) {
        boolean isUsable() {
            boolean hasDateOrRange = dateIdx >= 0 || (startIdx >= 0 && endIdx >= 0);
            boolean hasEvent = eventCodeIdx >= 0 || eventNameIdx >= 0;
            return hasDateOrRange && hasEvent;
        }
    }
}
