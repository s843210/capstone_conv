package com.errorzero.conv.service.inventory;

import com.errorzero.conv.dto.ProductMasterUploadResponseDto;
import com.errorzero.conv.repository.ProductMasterRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
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
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class ProductMasterUploadService {

    private static final List<Charset> CSV_CHARSETS = List.of(
            StandardCharsets.UTF_8,
            Charset.forName("MS949"),
            Charset.forName("EUC-KR")
    );

    private final ProductMasterRepository productMasterRepository;

    @Transactional
    public ProductMasterUploadResponseDto upload(List<MultipartFile> files, boolean dryRun) {
        if (files == null || files.isEmpty()) {
            throw new IllegalArgumentException("At least one product master CSV file is required.");
        }

        String runId = UUID.randomUUID().toString();
        Map<String, MasterRow> uniqueRowsByPlu = new LinkedHashMap<>();
        List<String> duplicateSamples = new ArrayList<>();
        List<String> fileSamples = new ArrayList<>();
        int rawRowCount = 0;
        int duplicatePluCount = 0;
        int fileCount = 0;

        for (MultipartFile file : files) {
            if (file == null || file.isEmpty()) {
                continue;
            }
            String fileName = cleanFileName(Objects.requireNonNullElse(file.getOriginalFilename(), ""));
            if (!fileName.toLowerCase().endsWith(".csv")) {
                continue;
            }

            fileCount++;
            addSample(fileSamples, fileName);
            ParseResult parsed = parseMasterRows(file, fileName);
            rawRowCount += parsed.rawRowCount();

            for (MasterRow row : parsed.rows()) {
                MasterRow previous = uniqueRowsByPlu.put(row.pluCode(), row);
                if (previous != null) {
                    duplicatePluCount++;
                    addSample(duplicateSamples, row.pluCode() + " / " + previous.sourceFile() + " -> " + row.sourceFile());
                }
            }
        }

        if (fileCount == 0) {
            throw new IllegalArgumentException("Only CSV files can be uploaded as product master files.");
        }

        int upsertedCount = 0;
        if (!dryRun) {
            for (MasterRow row : uniqueRowsByPlu.values()) {
                upsertedCount += productMasterRepository.upsertMasterProduct(
                        row.pluCode(),
                        row.productName(),
                        row.category(),
                        row.sourceFile()
                );
            }
        }

        log.info("Product master upload complete: runId={}, dryRun={}, files={}, parsed={}, upserted={}",
                runId, dryRun, fileCount, uniqueRowsByPlu.size(), upsertedCount);

        return ProductMasterUploadResponseDto.builder()
                .runId(runId)
                .dryRun(dryRun)
                .fileCount(fileCount)
                .rawRowCount(rawRowCount)
                .parsedRowCount(uniqueRowsByPlu.size())
                .duplicatePluCount(duplicatePluCount)
                .upsertedCount(upsertedCount)
                .duplicateSamples(duplicateSamples)
                .fileSamples(fileSamples)
                .message(dryRun
                        ? "DRY RUN complete. Product master rows were parsed but not saved."
                        : "Product master upload complete.")
                .build();
    }

    private ParseResult parseMasterRows(MultipartFile file, String fileName) {
        List<String[]> table = readCsvWithFallback(file);
        int headerRowIndex = findHeaderIndex(table);
        if (headerRowIndex < 0) {
            throw new IllegalArgumentException("Cannot find PLU and product name headers in " + fileName);
        }

        String[] header = table.get(headerRowIndex);
        int pluCol = findColumnIndex(header, "PLU코드", "PLU", "바코드");
        int nameCol = findColumnIndex(header, "상품명", "상품");
        if (pluCol < 0 || nameCol < 0) {
            throw new IllegalArgumentException("Product master CSV must contain PLU code and product name columns: " + fileName);
        }

        String category = categoryFromFileName(fileName);
        List<MasterRow> rows = new ArrayList<>();
        int rawRowCount = 0;

        for (int i = headerRowIndex + 1; i < table.size(); i++) {
            rawRowCount++;
            String[] row = table.get(i);
            String pluCode = normalizePluCode(valueAt(row, pluCol));
            String productName = valueAt(row, nameCol);
            if (pluCode.isBlank() || productName.isBlank()) {
                continue;
            }
            rows.add(new MasterRow(pluCode, productName, category, fileName));
        }

        return new ParseResult(rawRowCount, rows);
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
                if (findHeaderIndex(parsed) >= 0) {
                    return parsed;
                }
            }

            return best;
        } catch (IOException e) {
            throw new IllegalStateException("Failed to read product master CSV: " + file.getOriginalFilename(), e);
        }
    }

    private List<String[]> parseCsv(byte[] bytes, Charset charset) throws IOException {
        List<String[]> rows = new ArrayList<>();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(new ByteArrayInputStream(bytes), charset))) {
            String line;
            while ((line = reader.readLine()) != null) {
                rows.add(splitCsvLine(line.replace("\uFEFF", "")));
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

    private int findHeaderIndex(List<String[]> rows) {
        for (int i = 0; i < Math.min(rows.size(), 80); i++) {
            String[] row = rows.get(i);
            if (findColumnIndex(row, "PLU코드", "PLU", "바코드") >= 0
                    && findColumnIndex(row, "상품명", "상품") >= 0) {
                return i;
            }
        }
        return -1;
    }

    private int findColumnIndex(String[] row, String... keywords) {
        for (int i = 0; i < row.length; i++) {
            String normalizedValue = normalizeHeader(row[i]);
            for (String keyword : keywords) {
                if (normalizedValue.contains(normalizeHeader(keyword))) {
                    return i;
                }
            }
        }
        return -1;
    }

    private String valueAt(String[] row, int idx) {
        if (idx < 0 || idx >= row.length) {
            return "";
        }
        return cleanCell(row[idx]);
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

    private String categoryFromFileName(String fileName) {
        String clean = cleanFileName(fileName);
        int dotIndex = clean.lastIndexOf('.');
        return dotIndex > 0 ? clean.substring(0, dotIndex) : clean;
    }

    private String cleanFileName(String fileName) {
        String clean = cleanCell(fileName).replace('\\', '/');
        int slashIndex = clean.lastIndexOf('/');
        return slashIndex >= 0 ? clean.substring(slashIndex + 1) : clean;
    }

    private String normalizeHeader(String value) {
        return cleanCell(value)
                .replace("\\n", "")
                .replace("\n", "")
                .replace(" ", "")
                .toLowerCase();
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

    private void addSample(List<String> samples, String value) {
        if (samples.size() < 20) {
            samples.add(value);
        }
    }

    private record MasterRow(String pluCode, String productName, String category, String sourceFile) {
    }

    private record ParseResult(int rawRowCount, List<MasterRow> rows) {
    }
}
