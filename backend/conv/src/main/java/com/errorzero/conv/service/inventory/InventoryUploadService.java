package com.errorzero.conv.service.inventory;

import com.errorzero.conv.domain.Product;
import com.errorzero.conv.domain.ProductMaster;
import com.errorzero.conv.dto.InventoryUploadResponseDto;
import com.errorzero.conv.repository.InventorySnapshotRepository;
import com.errorzero.conv.repository.ProductMasterRepository;
import com.errorzero.conv.repository.ProductRepository;
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
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class InventoryUploadService {

    private static final String UNCLASSIFIED_CATEGORY = "\uBBF8\uBD84\uB958";
    private static final String HEADER_PLU = "PLU\uCF54\uB4DC";
    private static final String HEADER_BARCODE = "\uBC14\uCF54\uB4DC";
    private static final String HEADER_PRODUCT_NAME = "\uC0C1\uD488\uBA85";
    private static final String HEADER_PRODUCT = "\uC0C1\uD488";
    private static final String HEADER_CURRENT_STOCK = "\uD604\uC7AC\uACE0";
    private static final String TOTAL_LABEL = "\uD569\uACC4";

    private static final List<Charset> CSV_CHARSETS = List.of(
            StandardCharsets.UTF_8,
            Charset.forName("MS949"),
            Charset.forName("EUC-KR")
    );

    private final ProductRepository productRepository;
    private final ProductMasterRepository productMasterRepository;
    private final InventorySnapshotRepository inventorySnapshotRepository;

    @Transactional
    public InventoryUploadResponseDto upload(MultipartFile file, boolean dryRun) {
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("Inventory file is required.");
        }

        String runId = UUID.randomUUID().toString();
        String fileName = Objects.requireNonNullElse(file.getOriginalFilename(), "");
        LocalDate snapshotDate = LocalDate.now();

        ParseResult parsed = parseInventoryRows(file);
        Map<String, InventoryRow> uniqueRowsByPlu = new LinkedHashMap<>();
        int duplicatePluCount = 0;
        int negativeStockNormalizedCount = 0;

        for (InventoryRow row : parsed.rows()) {
            int safeStock = row.currentStock();
            if (safeStock < 0) {
                safeStock = 0;
                negativeStockNormalizedCount++;
            }

            InventoryRow safeRow = new InventoryRow(row.pluCode(), row.productName(), safeStock);
            if (uniqueRowsByPlu.put(safeRow.pluCode(), safeRow) != null) {
                duplicatePluCount++;
            }
        }

        Map<String, Product> existingProductByPlu = findActiveProductMap(uniqueRowsByPlu.keySet());
        Map<String, ProductMaster> masterByPlu = findProductMasterMap(uniqueRowsByPlu.keySet());

        int matchedCount = existingProductByPlu.size();
        int createdOrUpdatedProductCount = 0;
        int snapshotUpsertedCount = 0;
        int masterMatchedCount = 0;
        int masterUnmatchedCount = 0;
        int nameMismatchCount = 0;
        List<String> nameMismatchSamples = new ArrayList<>();

        for (InventoryRow row : uniqueRowsByPlu.values()) {
            ProductMaster master = masterByPlu.get(row.pluCode());
            String category = UNCLASSIFIED_CATEGORY;
            if (master != null) {
                masterMatchedCount++;
                category = master.getCategory();
            } else {
                masterUnmatchedCount++;
            }

            Product existingProduct = existingProductByPlu.get(row.pluCode());
            if (existingProduct != null && !sameName(existingProduct.getName(), row.productName())) {
                nameMismatchCount++;
                addSample(
                        nameMismatchSamples,
                        row.pluCode() + " / DB=" + existingProduct.getName() + " / FILE=" + row.productName()
                );
            }

            if (!dryRun) {
                createdOrUpdatedProductCount += productRepository.upsertFromInventory(
                        row.pluCode(),
                        row.productName(),
                        category,
                        row.currentStock()
                );
            }
        }

        if (!dryRun) {
            Map<String, Product> savedProductByPlu = findActiveProductMap(uniqueRowsByPlu.keySet());
            for (InventoryRow row : uniqueRowsByPlu.values()) {
                Product product = savedProductByPlu.get(row.pluCode());
                if (product == null) {
                    continue;
                }
                snapshotUpsertedCount += inventorySnapshotRepository.upsertSnapshot(
                        snapshotDate,
                        product.getId(),
                        row.pluCode(),
                        row.currentStock()
                );
            }
        }

        log.info(
                "Inventory upload complete: runId={}, dryRun={}, rawRows={}, parsedRows={}, productUpserts={}, snapshotUpserts={}, masterMatched={}",
                runId,
                dryRun,
                parsed.rawRowCount(),
                uniqueRowsByPlu.size(),
                createdOrUpdatedProductCount,
                snapshotUpsertedCount,
                masterMatchedCount
        );

        return InventoryUploadResponseDto.builder()
                .runId(runId)
                .dryRun(dryRun)
                .fileName(fileName)
                .rawRowCount(parsed.rawRowCount())
                .parsedRowCount(uniqueRowsByPlu.size())
                .duplicatePluCount(duplicatePluCount)
                .negativeStockNormalizedCount(negativeStockNormalizedCount)
                .matchedCount(matchedCount)
                .createdOrUpdatedProductCount(createdOrUpdatedProductCount)
                .masterMatchedCount(masterMatchedCount)
                .masterUnmatchedCount(masterUnmatchedCount)
                .snapshotUpsertedCount(snapshotUpsertedCount)
                .updatedCount(createdOrUpdatedProductCount)
                .skippedCount(0)
                .nameMismatchCount(nameMismatchCount)
                .skippedSamples(List.of())
                .nameMismatchSamples(nameMismatchSamples)
                .message(dryRun
                        ? "DRY RUN complete. Inventory rows were parsed but not saved."
                        : "Inventory upload complete. Product stock and inventory snapshot were saved.")
                .build();
    }

    private ParseResult parseInventoryRows(MultipartFile file) {
        String fileName = Objects.requireNonNullElse(file.getOriginalFilename(), "").toLowerCase();
        if (fileName.endsWith(".xlsx") || fileName.endsWith(".xlsm") || fileName.endsWith(".xls")) {
            return parseExcel(file);
        }
        if (fileName.endsWith(".csv")) {
            return parseCsv(file);
        }
        throw new IllegalArgumentException("Unsupported inventory file format: " + file.getOriginalFilename());
    }

    private ParseResult parseExcel(MultipartFile file) {
        List<InventoryRow> rows = new ArrayList<>();
        DataFormatter formatter = new DataFormatter();
        int rawRowCount = 0;

        try (Workbook workbook = WorkbookFactory.create(file.getInputStream())) {
            Sheet sheet = workbook.getSheetAt(0);
            int headerRowIndex = findHeaderRow(sheet, formatter);
            if (headerRowIndex < 0) {
                throw new IllegalArgumentException("Cannot find inventory headers: PLU code, product name, current stock.");
            }

            Row header = sheet.getRow(headerRowIndex);
            int pluCol = findColumnIndex(header, formatter, HEADER_PLU, "PLU", HEADER_BARCODE);
            int nameCol = findColumnIndex(header, formatter, HEADER_PRODUCT_NAME, HEADER_PRODUCT);
            int stockCol = findColumnIndex(header, formatter, HEADER_CURRENT_STOCK);

            if (pluCol < 0 || nameCol < 0 || stockCol < 0) {
                throw new IllegalArgumentException("Inventory file must contain PLU code, product name, and current stock columns.");
            }

            for (int i = headerRowIndex + 1; i <= sheet.getLastRowNum(); i++) {
                Row row = sheet.getRow(i);
                if (row == null) {
                    continue;
                }
                rawRowCount++;

                String pluCode = normalizePluCode(formatter.formatCellValue(row.getCell(pluCol)));
                String productName = cleanCell(formatter.formatCellValue(row.getCell(nameCol)));
                Integer currentStock = parseQuantity(row.getCell(stockCol), formatter);

                addInventoryRow(rows, pluCode, productName, currentStock);
            }
        } catch (IOException e) {
            throw new IllegalStateException("Failed to parse inventory Excel file: " + file.getOriginalFilename(), e);
        }

        return new ParseResult(rawRowCount, rows);
    }

    private ParseResult parseCsv(MultipartFile file) {
        List<String[]> table = readCsvWithFallback(file);
        int headerRowIndex = findHeaderIndex(table);
        if (headerRowIndex < 0) {
            throw new IllegalArgumentException("Cannot find inventory CSV headers: PLU code, product name, current stock.");
        }

        String[] header = table.get(headerRowIndex);
        int pluCol = findColumnIndex(header, HEADER_PLU, "PLU", HEADER_BARCODE);
        int nameCol = findColumnIndex(header, HEADER_PRODUCT_NAME, HEADER_PRODUCT);
        int stockCol = findColumnIndex(header, HEADER_CURRENT_STOCK);

        if (pluCol < 0 || nameCol < 0 || stockCol < 0) {
            throw new IllegalArgumentException("Inventory CSV must contain PLU code, product name, and current stock columns.");
        }

        List<InventoryRow> rows = new ArrayList<>();
        int rawRowCount = 0;
        for (int i = headerRowIndex + 1; i < table.size(); i++) {
            String[] row = table.get(i);
            rawRowCount++;
            String pluCode = normalizePluCode(valueAt(row, pluCol));
            String productName = valueAt(row, nameCol);
            Integer currentStock = parseQuantity(valueAt(row, stockCol));
            addInventoryRow(rows, pluCode, productName, currentStock);
        }
        return new ParseResult(rawRowCount, rows);
    }

    private void addInventoryRow(List<InventoryRow> rows, String pluCode, String productName, Integer currentStock) {
        if (pluCode.isBlank() || productName.isBlank() || currentStock == null) {
            return;
        }
        if (TOTAL_LABEL.equals(productName.trim())) {
            return;
        }
        rows.add(new InventoryRow(pluCode, productName, currentStock));
    }

    private int findHeaderRow(Sheet sheet, DataFormatter formatter) {
        int max = Math.min(sheet.getLastRowNum(), 80);
        for (int i = 0; i <= max; i++) {
            Row row = sheet.getRow(i);
            if (row == null) {
                continue;
            }
            if (findColumnIndex(row, formatter, HEADER_PLU, "PLU", HEADER_BARCODE) >= 0
                    && findColumnIndex(row, formatter, HEADER_PRODUCT_NAME, HEADER_PRODUCT) >= 0
                    && findColumnIndex(row, formatter, HEADER_CURRENT_STOCK) >= 0) {
                return i;
            }
        }
        return -1;
    }

    private int findHeaderIndex(List<String[]> rows) {
        for (int i = 0; i < Math.min(rows.size(), 80); i++) {
            String[] row = rows.get(i);
            if (findColumnIndex(row, HEADER_PLU, "PLU", HEADER_BARCODE) >= 0
                    && findColumnIndex(row, HEADER_PRODUCT_NAME, HEADER_PRODUCT) >= 0
                    && findColumnIndex(row, HEADER_CURRENT_STOCK) >= 0) {
                return i;
            }
        }
        return -1;
    }

    private int findColumnIndex(Row row, DataFormatter formatter, String... keywords) {
        if (row == null) {
            return -1;
        }
        for (Cell cell : row) {
            String normalizedValue = normalizeHeader(formatter.formatCellValue(cell));
            for (String keyword : keywords) {
                if (normalizedValue.contains(normalizeHeader(keyword))) {
                    return cell.getColumnIndex();
                }
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

    private Map<String, Product> findActiveProductMap(Collection<String> pluCodes) {
        if (pluCodes.isEmpty()) {
            return new HashMap<>();
        }
        return productRepository.findAllByPluCodeInAndIsActiveTrue(pluCodes)
                .stream()
                .collect(Collectors.toMap(Product::getPluCode, Function.identity(), (left, right) -> left));
    }

    private Map<String, ProductMaster> findProductMasterMap(Collection<String> pluCodes) {
        if (pluCodes.isEmpty()) {
            return new HashMap<>();
        }
        return productMasterRepository.findAllByPluCodeIn(pluCodes)
                .stream()
                .collect(Collectors.toMap(ProductMaster::getPluCode, Function.identity(), (left, right) -> left));
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
            throw new IllegalStateException("Failed to read inventory CSV: " + file.getOriginalFilename(), e);
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
        String value = cleanCell(raw).replace(",", "").trim();
        if (value.isBlank()) {
            return null;
        }
        try {
            return new BigDecimal(value).setScale(0, java.math.RoundingMode.HALF_UP).intValue();
        } catch (NumberFormatException ignored) {
            return null;
        }
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

    private boolean sameName(String left, String right) {
        return normalizeName(left).equals(normalizeName(right));
    }

    private String normalizeName(String value) {
        return cleanCell(value).replaceAll("\\s+", "").toLowerCase();
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

    private record InventoryRow(String pluCode, String productName, int currentStock) {
    }

    private record ParseResult(int rawRowCount, List<InventoryRow> rows) {
    }
}
