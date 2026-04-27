package com.errorzero.conv.service.sales;

import com.errorzero.conv.dto.SalesUploadResponseDto;
import com.errorzero.conv.repository.DailySalesRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.CellType;
import org.apache.poi.ss.usermodel.DataFormatter;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.ss.usermodel.WorkbookFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.math.BigDecimal;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class SalesUploadService {

    private static final Pattern DATE_YYYYMMDD = Pattern.compile("(20\\d{2})(0[1-9]|1[0-2])([0-2]\\d|3[01])");
    private static final Pattern DATE_YYMMDD = Pattern.compile("(?<!\\d)(\\d{2})(0[1-9]|1[0-2])([0-2]\\d|3[01])(?!\\d)");
    private static final Pattern MM_DD = Pattern.compile("(0[1-9]|1[0-2])[-/.](0[1-9]|[12]\\d|3[01])");
    private static final Pattern LIKELY_CATEGORY_PATTERN = Pattern.compile(".*\\((대|중|소|RTD|펫)\\)$");

    private static final List<Charset> CSV_CHARSETS = List.of(
            StandardCharsets.UTF_8,
            Charset.forName("MS949"),
            Charset.forName("EUC-KR")
    );

    private final DailySalesRepository dailySalesRepository;

    @Transactional
    public SalesUploadResponseDto upload(List<MultipartFile> salesFiles,
                                         List<MultipartFile> masterFiles,
                                         LocalDate overrideSalesDate,
                                         boolean dryRun) {
        if (salesFiles == null || salesFiles.isEmpty()) {
            throw new IllegalArgumentException("판매 파일(salesFiles)은 최소 1개 이상 필요합니다.");
        }
        if (masterFiles == null || masterFiles.isEmpty()) {
            throw new IllegalArgumentException("분류 마스터 파일(masterFiles)은 최소 1개 이상 필요합니다.");
        }

        String runId = UUID.randomUUID().toString();
        Map<String, String> masterMap = buildMasterNameToPluMap(masterFiles);
        if (masterMap.isEmpty()) {
            throw new IllegalArgumentException("마스터 파일에서 상품명/PLU 매핑을 찾지 못했습니다.");
        }

        UploadStats stats = new UploadStats();
        Map<SalesKey, Integer> mergedDailySales = new LinkedHashMap<>();

        for (MultipartFile salesFile : salesFiles) {
            if (salesFile == null || salesFile.isEmpty()) {
                continue;
            }

            LocalDate salesDate = resolveSalesDate(overrideSalesDate, salesFile.getOriginalFilename());
            List<SalesRow> rows = parseSalesRows(salesFile);

            for (SalesRow row : rows) {
                stats.rawRowCount++;

                String normalizedName = normalizeName(row.productName());
                String pluCode = masterMap.get(normalizedName);
                if (pluCode == null || pluCode.isBlank()) {
                    if (!isLikelyAggregateRow(row.productName())) {
                        stats.unmatchedRowCount++;
                        if (stats.unmatchedSamples.size() < 20) {
                            stats.unmatchedSamples.add(row.productName());
                        }
                    }
                    continue;
                }

                stats.matchedRowCount++;
                SalesKey key = new SalesKey(salesDate, pluCode);
                mergedDailySales.merge(key, Math.max(row.salesQty(), 0), Integer::sum);
            }
        }

        if (mergedDailySales.isEmpty()) {
            return SalesUploadResponseDto.builder()
                    .runId(runId)
                    .dryRun(dryRun)
                    .salesFileCount(salesFiles.size())
                    .masterFileCount(masterFiles.size())
                    .rawRowCount(stats.rawRowCount)
                    .matchedRowCount(stats.matchedRowCount)
                    .unmatchedRowCount(stats.unmatchedRowCount)
                    .uniqueDailySalesCount(0)
                    .insertedCount(0)
                    .updatedCount(0)
                    .upsertedCount(0)
                    .minSalesDate(null)
                    .maxSalesDate(null)
                    .unmatchedSamples(stats.unmatchedSamples)
                    .message("매칭된 판매 데이터가 없어 daily_sales 적재를 수행하지 않았습니다.")
                    .build();
        }

        List<LocalDate> dates = mergedDailySales.keySet().stream()
                .map(SalesKey::salesDate)
                .distinct()
                .sorted()
                .toList();

        LocalDate minDate = dates.get(0);
        LocalDate maxDate = dates.get(dates.size() - 1);

        int insertedCount = 0;
        int updatedCount = 0;

        if (!dryRun) {
            Map<LocalDate, Set<String>> plusByDate = groupPluCodesByDate(mergedDailySales.keySet());
            Map<SalesKey, Boolean> existingMap = new HashMap<>();

            for (Map.Entry<LocalDate, Set<String>> entry : plusByDate.entrySet()) {
                LocalDate date = entry.getKey();
                Set<String> pluCodes = entry.getValue();
                List<String> existing = dailySalesRepository.findExistingPluCodes(date, pluCodes);
                Set<String> existingSet = new HashSet<>(existing);
                for (String pluCode : pluCodes) {
                    existingMap.put(new SalesKey(date, pluCode), existingSet.contains(pluCode));
                }
            }

            for (Map.Entry<SalesKey, Integer> entry : mergedDailySales.entrySet()) {
                SalesKey key = entry.getKey();
                dailySalesRepository.upsert(key.salesDate(), key.pluCode(), entry.getValue());
                if (Boolean.TRUE.equals(existingMap.get(key))) {
                    updatedCount++;
                } else {
                    insertedCount++;
                }
            }
        }

        int uniqueCount = mergedDailySales.size();
        String message = dryRun
                ? "DRY RUN 완료: DB 저장 없이 변환/매칭 결과만 계산했습니다."
                : "daily_sales 업서트 완료";

        log.info("판매 적재 완료: runId={}, dryRun={}, rawRows={}, matchedRows={}, unmatchedRows={}, uniqueRows={}, inserted={}, updated={}",
                runId,
                dryRun,
                stats.rawRowCount,
                stats.matchedRowCount,
                stats.unmatchedRowCount,
                uniqueCount,
                insertedCount,
                updatedCount);

        return SalesUploadResponseDto.builder()
                .runId(runId)
                .dryRun(dryRun)
                .salesFileCount(salesFiles.size())
                .masterFileCount(masterFiles.size())
                .rawRowCount(stats.rawRowCount)
                .matchedRowCount(stats.matchedRowCount)
                .unmatchedRowCount(stats.unmatchedRowCount)
                .uniqueDailySalesCount(uniqueCount)
                .insertedCount(insertedCount)
                .updatedCount(updatedCount)
                .upsertedCount(dryRun ? 0 : (insertedCount + updatedCount))
                .minSalesDate(minDate)
                .maxSalesDate(maxDate)
                .unmatchedSamples(stats.unmatchedSamples)
                .message(message)
                .build();
    }

    private Map<LocalDate, Set<String>> groupPluCodesByDate(Collection<SalesKey> keys) {
        Map<LocalDate, Set<String>> result = new LinkedHashMap<>();
        for (SalesKey key : keys) {
            result.computeIfAbsent(key.salesDate(), k -> new LinkedHashSet<>()).add(key.pluCode());
        }
        return result;
    }

    private Map<String, String> buildMasterNameToPluMap(List<MultipartFile> masterFiles) {
        Map<String, String> map = new LinkedHashMap<>();

        for (MultipartFile file : masterFiles) {
            if (file == null || file.isEmpty()) {
                continue;
            }
            String name = Objects.requireNonNullElse(file.getOriginalFilename(), "").toLowerCase();
            if (!name.endsWith(".csv")) {
                continue;
            }

            List<String[]> rows = readCsvWithFallback(file);
            int headerIndex = findHeaderIndex(rows, "PLU코드", "상품명");
            if (headerIndex < 0) {
                continue;
            }

            String[] header = rows.get(headerIndex);
            int pluIdx = findColumnIndex(header, "PLU코드");
            int productIdx = findColumnIndex(header, "상품명");
            if (pluIdx < 0 || productIdx < 0) {
                continue;
            }

            for (int i = headerIndex + 1; i < rows.size(); i++) {
                String[] row = rows.get(i);
                if (row.length <= Math.max(pluIdx, productIdx)) {
                    continue;
                }

                String plu = normalizePluCode(valueAt(row, pluIdx));
                String productName = valueAt(row, productIdx).trim();
                if (plu.isBlank() || productName.isBlank()) {
                    continue;
                }

                map.putIfAbsent(normalizeName(productName), plu);
            }
        }

        return map;
    }

    private List<SalesRow> parseSalesRows(MultipartFile salesFile) {
        String fileName = Objects.requireNonNullElse(salesFile.getOriginalFilename(), "").toLowerCase();
        if (fileName.endsWith(".xlsx") || fileName.endsWith(".xlsm") || fileName.endsWith(".xls")) {
            return parseSalesFromExcel(salesFile);
        }
        if (fileName.endsWith(".csv")) {
            return parseSalesFromCsv(salesFile);
        }

        throw new IllegalArgumentException("지원하지 않는 판매 파일 형식입니다: " + salesFile.getOriginalFilename());
    }

    private List<SalesRow> parseSalesFromExcel(MultipartFile file) {
        List<SalesRow> rows = new ArrayList<>();
        DataFormatter formatter = new DataFormatter();

        try (Workbook workbook = WorkbookFactory.create(file.getInputStream())) {
            Sheet sheet = workbook.getSheetAt(0);
            int headerRowIndex = findHeaderRow(sheet, formatter, "카테고리/상품", 40);
            if (headerRowIndex < 0) {
                throw new IllegalArgumentException("판매 파일 헤더(카테고리/상품)를 찾지 못했습니다: " + file.getOriginalFilename());
            }

            Row headerRow = sheet.getRow(headerRowIndex);
            int productCol = findColumnIndex(headerRow, formatter, "카테고리/상품");
            if (productCol < 0) {
                throw new IllegalArgumentException("상품명 컬럼을 찾지 못했습니다: " + file.getOriginalFilename());
            }

            int salesCol = findSalesColumn(sheet, headerRowIndex, formatter);
            if (salesCol < 0) {
                throw new IllegalArgumentException("판매량 컬럼을 찾지 못했습니다: " + file.getOriginalFilename());
            }

            int startRow = headerRowIndex + 2;
            int lastRow = sheet.getLastRowNum();
            for (int i = startRow; i <= lastRow; i++) {
                Row row = sheet.getRow(i);
                if (row == null) {
                    continue;
                }

                String productName = cleanCell(formatter.formatCellValue(row.getCell(productCol)));
                if (productName.isBlank()) {
                    continue;
                }

                Integer qty = parseQuantity(row.getCell(salesCol), formatter);
                if (qty == null) {
                    continue;
                }

                rows.add(new SalesRow(productName, Math.max(qty, 0)));
            }
        } catch (IOException e) {
            throw new IllegalStateException("판매 엑셀 파싱 실패: " + file.getOriginalFilename(), e);
        }

        return rows;
    }

    private List<SalesRow> parseSalesFromCsv(MultipartFile file) {
        List<String[]> table = readCsvWithFallback(file);
        int headerRowIndex = findHeaderIndex(table, "카테고리/상품");
        if (headerRowIndex < 0) {
            throw new IllegalArgumentException("판매 CSV 헤더(카테고리/상품)를 찾지 못했습니다: " + file.getOriginalFilename());
        }

        String[] header = table.get(headerRowIndex);
        int productCol = findColumnIndex(header, "카테고리/상품");
        if (productCol < 0) {
            throw new IllegalArgumentException("상품명 컬럼을 찾지 못했습니다: " + file.getOriginalFilename());
        }

        int salesCol = -1;
        if (headerRowIndex + 1 < table.size()) {
            salesCol = findDateColumn(table.get(headerRowIndex + 1));
        }
        if (salesCol < 0) {
            salesCol = findColumnIndex(header, "매출\n합계");
        }
        if (salesCol < 0) {
            salesCol = 2;
        }

        List<SalesRow> rows = new ArrayList<>();
        for (int i = headerRowIndex + 2; i < table.size(); i++) {
            String[] row = table.get(i);
            if (row.length <= Math.max(productCol, salesCol)) {
                continue;
            }
            String productName = valueAt(row, productCol).trim();
            if (productName.isBlank()) {
                continue;
            }

            Integer qty = parseQuantity(valueAt(row, salesCol));
            if (qty == null) {
                continue;
            }

            rows.add(new SalesRow(productName, Math.max(qty, 0)));
        }

        return rows;
    }

    private int findHeaderRow(Sheet sheet, DataFormatter formatter, String keyword, int maxScanRows) {
        int max = Math.min(sheet.getLastRowNum(), maxScanRows);
        for (int r = 0; r <= max; r++) {
            Row row = sheet.getRow(r);
            if (row == null) {
                continue;
            }
            for (Cell cell : row) {
                String value = cleanCell(formatter.formatCellValue(cell));
                if (value.contains(keyword)) {
                    return r;
                }
            }
        }
        return -1;
    }

    private int findSalesColumn(Sheet sheet, int headerRowIndex, DataFormatter formatter) {
        Row subHeader = sheet.getRow(headerRowIndex + 1);
        if (subHeader != null) {
            int byDate = findDateColumn(subHeader, formatter);
            if (byDate >= 0) {
                return byDate;
            }
        }

        Row header = sheet.getRow(headerRowIndex);
        int byName = findColumnIndex(header, formatter, "매출\n합계");
        if (byName >= 0) {
            return byName;
        }

        byName = findColumnIndex(header, formatter, "매출합계");
        if (byName >= 0) {
            return byName;
        }

        return 2;
    }

    private int findDateColumn(Row row, DataFormatter formatter) {
        for (Cell cell : row) {
            String value = cleanCell(formatter.formatCellValue(cell));
            if (MM_DD.matcher(value).matches()) {
                return cell.getColumnIndex();
            }
        }
        return -1;
    }

    private int findDateColumn(String[] row) {
        for (int i = 0; i < row.length; i++) {
            if (MM_DD.matcher(cleanCell(row[i])).matches()) {
                return i;
            }
        }
        return -1;
    }

    private int findColumnIndex(Row row, DataFormatter formatter, String keyword) {
        if (row == null) {
            return -1;
        }
        String normalizedKeyword = normalizeHeader(keyword);
        for (Cell cell : row) {
            String value = normalizeHeader(formatter.formatCellValue(cell));
            if (value.contains(normalizedKeyword)) {
                return cell.getColumnIndex();
            }
        }
        return -1;
    }

    private int findHeaderIndex(List<String[]> rows, String... keywords) {
        for (int i = 0; i < rows.size(); i++) {
            String joined = String.join("|", rows.get(i));
            boolean allMatched = true;
            for (String keyword : keywords) {
                if (!joined.contains(keyword)) {
                    allMatched = false;
                    break;
                }
            }
            if (allMatched) {
                return i;
            }
        }
        return -1;
    }

    private int findColumnIndex(String[] row, String keyword) {
        String normalizedKeyword = normalizeHeader(keyword);
        for (int i = 0; i < row.length; i++) {
            if (normalizeHeader(row[i]).contains(normalizedKeyword)) {
                return i;
            }
        }
        return -1;
    }

    private String normalizeHeader(String value) {
        return cleanCell(value)
                .replace("\\n", "")
                .replace("\n", "")
                .replace(" ", "");
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

                int headerIndex = findHeaderIndex(parsed, "PLU코드", "상품명");
                if (headerIndex >= 0) {
                    return parsed;
                }

                int salesHeaderIndex = findHeaderIndex(parsed, "카테고리/상품");
                if (salesHeaderIndex >= 0) {
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
                String normalized = line;
                if (!rows.isEmpty()) {
                    normalized = normalized.replace("\uFEFF", "");
                }
                rows.add(splitCsvLine(normalized));
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

    private Integer parseQuantity(Cell cell, DataFormatter formatter) {
        if (cell == null || cell.getCellType() == CellType.BLANK) {
            return null;
        }

        if (cell.getCellType() == CellType.NUMERIC) {
            return (int) Math.round(cell.getNumericCellValue());
        }

        return parseQuantity(formatter.formatCellValue(cell));
    }

    private Integer parseQuantity(String raw) {
        String value = cleanCell(raw)
                .replace(",", "")
                .replace("원", "")
                .trim();
        if (value.isBlank()) {
            return null;
        }

        try {
            return new BigDecimal(value).setScale(0, java.math.RoundingMode.HALF_UP).intValue();
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private LocalDate resolveSalesDate(LocalDate overrideDate, String fileName) {
        if (overrideDate != null) {
            return overrideDate;
        }

        if (fileName == null || fileName.isBlank()) {
            throw new IllegalArgumentException("salesDate 파라미터 또는 파일명 날짜가 필요합니다.");
        }

        Matcher m8 = DATE_YYYYMMDD.matcher(fileName);
        if (m8.find()) {
            return toDate(m8.group(1), m8.group(2), m8.group(3), fileName);
        }

        Matcher m6 = DATE_YYMMDD.matcher(fileName);
        if (m6.find()) {
            String yyyy = "20" + m6.group(1);
            return toDate(yyyy, m6.group(2), m6.group(3), fileName);
        }

        throw new IllegalArgumentException("파일명에서 sales_date를 추출하지 못했습니다: " + fileName + " (예: 260423판매현황.xlsx)");
    }

    private LocalDate toDate(String yyyy, String mm, String dd, String source) {
        try {
            return LocalDate.of(Integer.parseInt(yyyy), Integer.parseInt(mm), Integer.parseInt(dd));
        } catch (Exception e) {
            throw new IllegalArgumentException("유효하지 않은 날짜 형식입니다: " + source);
        }
    }

    private String normalizeName(String raw) {
        return cleanCell(raw)
                .replaceAll("\\s+", "")
                .toLowerCase();
    }

    private String normalizePluCode(String raw) {
        String value = cleanCell(raw).replace(",", "");
        if (value.isBlank()) {
            return "";
        }

        if (value.contains("e") || value.contains("E") || value.contains(".")) {
            try {
                BigDecimal number = new BigDecimal(value);
                String plain = number.stripTrailingZeros().toPlainString();
                int dotIndex = plain.indexOf('.');
                return dotIndex >= 0 ? plain.substring(0, dotIndex) : plain;
            } catch (NumberFormatException ignored) {
                return value;
            }
        }

        return value;
    }

    private String cleanCell(String raw) {
        if (raw == null) {
            return "";
        }
        return raw
                .replace("\uFEFF", "")
                .replace("\u00A0", " ")
                .trim();
    }

    private boolean isLikelyAggregateRow(String name) {
        String value = cleanCell(name);
        if (value.isBlank()) {
            return true;
        }

        if (LIKELY_CATEGORY_PATTERN.matcher(value).matches()) {
            return true;
        }

        // 분류 라인으로 자주 등장하는 패턴들을 노이즈로 제외
        if (value.endsWith("류") || value.endsWith("식품") || value.endsWith("음료") || value.endsWith("과자") || value.endsWith("제품")) {
            return true;
        }

        return value.length() <= 2;
    }

    private record SalesRow(String productName, int salesQty) {
    }

    private record SalesKey(LocalDate salesDate, String pluCode) {
    }

    private static class UploadStats {
        int rawRowCount = 0;
        int matchedRowCount = 0;
        int unmatchedRowCount = 0;
        List<String> unmatchedSamples = new ArrayList<>();
    }
}
