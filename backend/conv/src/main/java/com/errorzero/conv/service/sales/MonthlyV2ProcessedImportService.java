package com.errorzero.conv.service.sales;

import com.errorzero.conv.dto.MonthlyV2ProcessedImportResponseDto;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class MonthlyV2ProcessedImportService {

    private static final int BATCH_SIZE = 2_000;

    private static final String DAILY_SALES_SQL = """
            INSERT INTO daily_sales (sales_date, plu_code, sales_qty, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (sales_date, plu_code)
            DO UPDATE SET
                sales_qty = EXCLUDED.sales_qty,
                updated_at = CURRENT_TIMESTAMP
            """;

    private static final String PRODUCT_SQL = """
            INSERT INTO product (plu_code, name, category, current_stock, is_active, updated_at)
            VALUES (?, ?, ?, 0, false, CURRENT_TIMESTAMP)
            ON CONFLICT (plu_code) DO UPDATE
            SET name = EXCLUDED.name,
                category = EXCLUDED.category,
                updated_at = CURRENT_TIMESTAMP
            """;

    private static final String DAILY_CONTEXT_SQL = """
            INSERT INTO daily_context (
                target_date,
                avg_temp_c,
                precipitation_mm,
                is_rain,
                is_holiday,
                academic_event,
                building_headcount,
                is_start_semester,
                is_end_semester,
                is_exam,
                is_vacation,
                is_festival,
                is_holiday_or_no_class,
                class_count,
                monday_class_count,
                tuesday_class_count,
                wednesday_class_count,
                thursday_class_count,
                friday_class_count,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (target_date) DO UPDATE SET
                avg_temp_c = EXCLUDED.avg_temp_c,
                precipitation_mm = EXCLUDED.precipitation_mm,
                is_rain = EXCLUDED.is_rain,
                is_holiday = EXCLUDED.is_holiday,
                academic_event = EXCLUDED.academic_event,
                building_headcount = EXCLUDED.building_headcount,
                is_start_semester = EXCLUDED.is_start_semester,
                is_end_semester = EXCLUDED.is_end_semester,
                is_exam = EXCLUDED.is_exam,
                is_vacation = EXCLUDED.is_vacation,
                is_festival = EXCLUDED.is_festival,
                is_holiday_or_no_class = EXCLUDED.is_holiday_or_no_class,
                class_count = EXCLUDED.class_count,
                monday_class_count = EXCLUDED.monday_class_count,
                tuesday_class_count = EXCLUDED.tuesday_class_count,
                wednesday_class_count = EXCLUDED.wednesday_class_count,
                thursday_class_count = EXCLUDED.thursday_class_count,
                friday_class_count = EXCLUDED.friday_class_count,
                updated_at = CURRENT_TIMESTAMP
            """;

    private final JdbcTemplate jdbcTemplate;

    @Value("${app.sales.monthly-v2-processed-path:../../Ai/data/processed/monthly_sales_with_calendar_timetable_weather_v2.csv}")
    private String defaultSourcePath;

    @Transactional
    public MonthlyV2ProcessedImportResponseDto importFromConfiguredPath(String overridePath, boolean dryRun) {
        String runId = UUID.randomUUID().toString();
        Path sourcePath = resolveSourcePath(overridePath);
        if (!Files.exists(sourcePath)) {
            throw new IllegalArgumentException("monthly_v2 processed CSV를 찾을 수 없습니다: " + sourcePath);
        }

        ImportStats stats = new ImportStats(runId, dryRun, sourcePath.toString());
        Map<String, ProductImportRow> productsByPlu = new LinkedHashMap<>();
        Map<LocalDate, ContextImportRow> contextsByDate = new LinkedHashMap<>();
        List<DailySalesImportRow> salesBatch = new ArrayList<>(BATCH_SIZE);

        try (BufferedReader reader = Files.newBufferedReader(sourcePath, StandardCharsets.UTF_8)) {
            String headerLine = reader.readLine();
            if (headerLine == null || headerLine.isBlank()) {
                throw new IllegalArgumentException("monthly_v2 processed CSV가 비어 있습니다: " + sourcePath);
            }

            Map<String, Integer> header = buildHeaderIndex(splitCsvLine(headerLine));
            validateHeader(header);

            String line;
            while ((line = reader.readLine()) != null) {
                if (line.isBlank()) {
                    continue;
                }

                try {
                    String[] row = splitCsvLine(line);
                    ParsedRow parsed = parseRow(row, header);
                    stats.accept(parsed);

                    productsByPlu.putIfAbsent(
                            parsed.pluCode(),
                            new ProductImportRow(parsed.pluCode(), parsed.productName(), parsed.productCategory())
                    );
                    contextsByDate.putIfAbsent(parsed.date(), parsed.context());

                    if (!dryRun) {
                        salesBatch.add(new DailySalesImportRow(parsed.date(), parsed.pluCode(), parsed.salesQty()));
                        if (salesBatch.size() >= BATCH_SIZE) {
                            flushDailySales(salesBatch);
                            salesBatch.clear();
                        }
                    }
                } catch (RuntimeException exc) {
                    stats.reject(line, exc.getMessage());
                }
            }

            if (!dryRun && !salesBatch.isEmpty()) {
                flushDailySales(salesBatch);
                salesBatch.clear();
            }
            if (!dryRun) {
                flushProducts(new ArrayList<>(productsByPlu.values()));
                flushContexts(new ArrayList<>(contextsByDate.values()));
            }
        } catch (IOException exc) {
            throw new IllegalStateException("monthly_v2 processed CSV 읽기 실패: " + sourcePath, exc);
        }

        log.info(
                "monthly_v2 processed import 완료: runId={}, dryRun={}, parsedRows={}, invalidRows={}, products={}, contexts={}",
                runId,
                dryRun,
                stats.parsedRows,
                stats.invalidRows,
                productsByPlu.size(),
                contextsByDate.size()
        );

        return MonthlyV2ProcessedImportResponseDto.builder()
                .runId(runId)
                .dryRun(dryRun)
                .sourcePath(sourcePath.toString())
                .parsedRows(stats.parsedRows)
                .dailySalesUpsertedRows(dryRun ? 0 : stats.parsedRows)
                .productUpsertedRows(dryRun ? 0 : productsByPlu.size())
                .contextUpsertedRows(dryRun ? 0 : contextsByDate.size())
                .invalidRows(stats.invalidRows)
                .minDate(stats.minDate)
                .maxDate(stats.maxDate)
                .uniquePluCount(productsByPlu.size())
                .invalidSamples(stats.invalidSamples)
                .message(dryRun
                        ? "DRY RUN 완료: DB 저장 없이 monthly_v2 processed CSV를 검증했습니다."
                        : "monthly_v2 processed CSV DB bulk import 완료")
                .build();
    }

    private Path resolveSourcePath(String overridePath) {
        String rawPath = (overridePath == null || overridePath.isBlank()) ? defaultSourcePath : overridePath;
        return Paths.get(rawPath).toAbsolutePath().normalize();
    }

    private void validateHeader(Map<String, Integer> header) {
        List<String> required = List.of(
                "date",
                "plu_code",
                "product_name",
                "product_category",
                "sales_qty",
                "is_start_semester",
                "is_end_semester",
                "is_exam",
                "is_vacation",
                "is_festival",
                "is_holiday_or_no_class",
                "class_count",
                "monday_class_count",
                "tuesday_class_count",
                "wednesday_class_count",
                "thursday_class_count",
                "friday_class_count",
                "avg_temp",
                "rainfall"
        );
        List<String> missing = required.stream()
                .filter(column -> !header.containsKey(column))
                .toList();
        if (!missing.isEmpty()) {
            throw new IllegalArgumentException("monthly_v2 processed CSV 필수 컬럼 누락: " + missing);
        }
    }

    private ParsedRow parseRow(String[] row, Map<String, Integer> header) {
        LocalDate date = LocalDate.parse(value(row, header, "date"));
        String pluCode = value(row, header, "plu_code");
        String productName = value(row, header, "product_name");
        String productCategory = value(row, header, "product_category");
        if (pluCode.isBlank() || productName.isBlank()) {
            throw new IllegalArgumentException("plu_code/product_name 누락");
        }

        int salesQty = nonNegativeInt(value(row, header, "sales_qty"));
        double avgTemp = doubleValue(value(row, header, "avg_temp"));
        double rainfall = Math.max(0.0, doubleValue(value(row, header, "rainfall")));
        short isHolidayOrNoClass = binary(value(row, header, "is_holiday_or_no_class"));
        short isVacation = binary(value(row, header, "is_vacation"));
        short isExam = binary(value(row, header, "is_exam"));
        short isFestival = binary(value(row, header, "is_festival"));

        ContextImportRow context = new ContextImportRow(
                date,
                avgTemp,
                rainfall,
                rainfall > 0 ? (short) 1 : (short) 0,
                isHolidayOrNoClass,
                academicEvent(isVacation, isExam, isFestival),
                nonNegativeInt(value(row, header, "class_count")),
                binary(value(row, header, "is_start_semester")),
                binary(value(row, header, "is_end_semester")),
                isExam,
                isVacation,
                isFestival,
                isHolidayOrNoClass,
                nonNegativeInt(value(row, header, "class_count")),
                nonNegativeInt(value(row, header, "monday_class_count")),
                nonNegativeInt(value(row, header, "tuesday_class_count")),
                nonNegativeInt(value(row, header, "wednesday_class_count")),
                nonNegativeInt(value(row, header, "thursday_class_count")),
                nonNegativeInt(value(row, header, "friday_class_count"))
        );

        return new ParsedRow(date, pluCode, productName, productCategory, salesQty, context);
    }

    private short academicEvent(short isVacation, short isExam, short isFestival) {
        if (isExam == 1) {
            return 2;
        }
        if (isFestival == 1) {
            return 3;
        }
        if (isVacation == 1) {
            return 4;
        }
        return 1;
    }

    private void flushDailySales(List<DailySalesImportRow> rows) {
        jdbcTemplate.batchUpdate(DAILY_SALES_SQL, rows, rows.size(), this::bindDailySales);
    }

    private void flushProducts(List<ProductImportRow> rows) {
        jdbcTemplate.batchUpdate(PRODUCT_SQL, rows, BATCH_SIZE, this::bindProduct);
    }

    private void flushContexts(List<ContextImportRow> rows) {
        jdbcTemplate.batchUpdate(DAILY_CONTEXT_SQL, rows, BATCH_SIZE, this::bindContext);
    }

    private void bindDailySales(PreparedStatement ps, DailySalesImportRow row) throws SQLException {
        ps.setObject(1, row.date());
        ps.setString(2, row.pluCode());
        ps.setInt(3, row.salesQty());
    }

    private void bindProduct(PreparedStatement ps, ProductImportRow row) throws SQLException {
        ps.setString(1, row.pluCode());
        ps.setString(2, row.productName());
        ps.setString(3, row.productCategory().isBlank() ? "미분류" : row.productCategory());
    }

    private void bindContext(PreparedStatement ps, ContextImportRow row) throws SQLException {
        ps.setObject(1, row.date());
        ps.setDouble(2, row.avgTempC());
        ps.setDouble(3, row.precipitationMm());
        ps.setShort(4, row.isRain());
        ps.setShort(5, row.isHoliday());
        ps.setInt(6, row.academicEvent());
        ps.setInt(7, row.buildingHeadcount());
        ps.setShort(8, row.isStartSemester());
        ps.setShort(9, row.isEndSemester());
        ps.setShort(10, row.isExam());
        ps.setShort(11, row.isVacation());
        ps.setShort(12, row.isFestival());
        ps.setShort(13, row.isHolidayOrNoClass());
        ps.setInt(14, row.classCount());
        ps.setInt(15, row.mondayClassCount());
        ps.setInt(16, row.tuesdayClassCount());
        ps.setInt(17, row.wednesdayClassCount());
        ps.setInt(18, row.thursdayClassCount());
        ps.setInt(19, row.fridayClassCount());
    }

    private Map<String, Integer> buildHeaderIndex(String[] header) {
        Map<String, Integer> index = new HashMap<>();
        for (int i = 0; i < header.length; i++) {
            index.put(normalizeHeader(header[i]), i);
        }
        return index;
    }

    private String value(String[] row, Map<String, Integer> header, String column) {
        Integer idx = header.get(column);
        if (idx == null || idx < 0 || idx >= row.length) {
            return "";
        }
        return Objects.requireNonNullElse(row[idx], "").trim();
    }

    private String normalizeHeader(String value) {
        return Objects.requireNonNullElse(value, "").replace("\uFEFF", "").trim();
    }

    private int nonNegativeInt(String value) {
        if (value == null || value.isBlank()) {
            return 0;
        }
        try {
            return Math.max(0, (int) Math.round(Double.parseDouble(value.replace(",", "").trim())));
        } catch (NumberFormatException exc) {
            throw new IllegalArgumentException("숫자 파싱 실패: " + value);
        }
    }

    private double doubleValue(String value) {
        if (value == null || value.isBlank()) {
            return 0.0;
        }
        try {
            return Double.parseDouble(value.replace(",", "").trim());
        } catch (NumberFormatException exc) {
            throw new IllegalArgumentException("실수 파싱 실패: " + value);
        }
    }

    private short binary(String value) {
        return nonNegativeInt(value) > 0 ? (short) 1 : (short) 0;
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
                cols.add(token.toString().trim());
                token.setLength(0);
            } else {
                token.append(ch);
            }
        }
        cols.add(token.toString().trim());
        return cols.toArray(String[]::new);
    }

    private record DailySalesImportRow(LocalDate date, String pluCode, int salesQty) {
    }

    private record ProductImportRow(String pluCode, String productName, String productCategory) {
    }

    private record ContextImportRow(
            LocalDate date,
            double avgTempC,
            double precipitationMm,
            short isRain,
            short isHoliday,
            int academicEvent,
            int buildingHeadcount,
            short isStartSemester,
            short isEndSemester,
            short isExam,
            short isVacation,
            short isFestival,
            short isHolidayOrNoClass,
            int classCount,
            int mondayClassCount,
            int tuesdayClassCount,
            int wednesdayClassCount,
            int thursdayClassCount,
            int fridayClassCount
    ) {
    }

    private record ParsedRow(
            LocalDate date,
            String pluCode,
            String productName,
            String productCategory,
            int salesQty,
            ContextImportRow context
    ) {
    }

    private static final class ImportStats {
        private final String runId;
        private final boolean dryRun;
        private final String sourcePath;
        private long parsedRows;
        private int invalidRows;
        private LocalDate minDate;
        private LocalDate maxDate;
        private final List<String> invalidSamples = new ArrayList<>();

        private ImportStats(String runId, boolean dryRun, String sourcePath) {
            this.runId = runId;
            this.dryRun = dryRun;
            this.sourcePath = sourcePath;
        }

        private void accept(ParsedRow row) {
            parsedRows++;
            if (minDate == null || row.date().isBefore(minDate)) {
                minDate = row.date();
            }
            if (maxDate == null || row.date().isAfter(maxDate)) {
                maxDate = row.date();
            }
        }

        private void reject(String line, String reason) {
            invalidRows++;
            if (invalidSamples.size() < 20) {
                invalidSamples.add(reason + " | " + line);
            }
        }
    }
}
